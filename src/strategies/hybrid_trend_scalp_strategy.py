from vnpy_ctastrategy import CtaTemplate
from vnpy.trader.utility import BarGenerator, ArrayManager
from vnpy.trader.constant import Interval
import time
import numpy as np
from src.models.ml_model import PricePredictionModel
import os


class HybridTrendScalpStrategy(CtaTemplate):
    """
    AI趋势 + 剥头皮策略
    使用AI模型判断趋势方向，剥头皮策略寻找入场时机
    """

    author = "AI Trader"

    # ===== 参数 =====
    fast_window = 5
    slow_window = 20

    take_profit_tick = 2
    stop_loss_tick = 3
    fixed_size = 1

    cooldown_seconds = 10
    max_trades_per_day = 50

    order_imbalance_ratio = 1.5
    max_spread_tick = 2

    # AI模型相关参数
    model_prediction_threshold = 0.005  # 预测阈值，当AI预测涨跌幅超过此值时才考虑交易

    # ===== 变量 =====
    last_trade_time = 0
    trade_count = 0
    entry_price = 0
    last_tick_time = 0

    # AI模型相关变量
    ai_model = None
    trend_direction = 0  # 0表示无明显趋势，1表示多头，-1表示空头
    prediction_confidence = 0  # 预测置信度

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # 创建多周期BarGenerator
        self.bg = BarGenerator(self.on_bar, 1, self.on_1min_bar)  # 1分钟K线
        self.bg_5min = BarGenerator(self.on_bar, 5, self.on_5min_bar, Interval.MINUTE)  # 5分钟K线
        self.bg_15min = BarGenerator(self.on_bar, 15, self.on_15min_bar, Interval.MINUTE)  # 15分钟K线
        
        self.am = ArrayManager(100)  # 增加ArrayManager容量以提供更多数据给AI模型
        self.am_5min = ArrayManager(100)
        self.am_15min = ArrayManager(100)

        self.last_tick = None

        # 初始化AI模型
        self.initialize_ai_model()

    def initialize_ai_model(self):
        """初始化AI预测模型"""
        try:
            # 获取项目根目录的绝对路径
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            model_path = os.path.join(project_root, "models", f"SHFE_rb_SHFE.rb2605_prediction_model.keras")
            
            if os.path.exists(model_path):
                self.ai_model = PricePredictionModel()
                self.ai_model.load_model(model_path)
                self.write_log(f"✅ AI预测模型加载成功: {model_path}")
            else:
                self.write_log(f"⚠️ AI模型文件不存在: {model_path}，将使用基础趋势判断")
        except Exception as e:
            self.write_log(f"❌ 加载AI模型时发生错误: {e}")

    def on_init(self):
        self.write_log("AI趋势+剥头皮策略初始化")
        self.load_bar(100)  # 加载更多历史数据以供AI模型使用

    # ===== Tick：记录盘口 =====
    def on_tick(self, tick):
        self.last_tick = tick
        self.last_tick_time = time.time()
        self.bg.update_tick(tick)

        # 使用AI模型预测趋势
        if self.ai_model and self.am.inited:
            self.update_trend_with_ai(tick)

    def update_trend_with_ai(self, tick):
        """使用AI模型更新趋势方向"""
        try:
            # 使用历史数据进行预测
            if len(self.am.close) > 60:  # 确保有足够的数据进行预测
                # 获取最近60个收盘价作为输入
                recent_prices = self.am.close[-60:].tolist()
                
                # 进行预测
                prediction = self.ai_model.predict([recent_prices])
                
                # 更新趋势方向和置信度
                if prediction[0] > self.model_prediction_threshold:
                    self.trend_direction = 1  # 看涨
                    self.prediction_confidence = prediction[0]
                elif prediction[0] < -self.model_prediction_threshold:
                    self.trend_direction = -1  # 看跌
                    self.prediction_confidence = abs(prediction[0])
                else:
                    self.trend_direction = 0  # 无明确趋势
                    self.prediction_confidence = 0

                self.write_log(f"AI预测: 方向{'看涨' if self.trend_direction == 1 else '看跌' if self.trend_direction == -1 else '无趋势'}, "
                              f"置信度: {self.prediction_confidence:.4f}, 预测值: {prediction[0]:.4f}")
        except Exception as e:
            self.write_log(f"❌ AI模型预测时发生错误: {e}")

    def check_orderflow(self, direction: str) -> bool:
        """
        direction: "long" / "short"
        """
        if not self.last_tick:
            return False

        tick = self.last_tick
        contract = self.cta_engine.main_engine.get_contract(self.vt_symbol)
        pricetick = contract.pricetick

        # 1️⃣ 价差过滤
        spread = tick.ask_price_1 - tick.bid_price_1
        if spread > self.max_spread_tick * pricetick:
            return False

        # 2️⃣ 买卖盘不平衡
        if direction == "long":
            if tick.bid_volume_1 < tick.ask_volume_1 * self.order_imbalance_ratio:
                return False
        else:
            if tick.ask_volume_1 < tick.bid_volume_1 * self.order_imbalance_ratio:
                return False

        # 3️⃣ 最近是否活跃（2 秒内有 Tick）
        if time.time() - self.last_tick_time > 2:
            return False

        return True

    # ===== Bar：交易决策 =====
    def on_bar(self, bar):
        """1分钟K线回调"""
        self.am.update_bar(bar)
        self.bg_5min.update_bar(bar)  # 更新5分钟K线
        self.bg_15min.update_bar(bar)  # 更新15分钟K线

    def on_1min_bar(self, bar):
        """1分钟K线回调，用于高频交易决策"""
        self.am.update_bar(bar)
        if not self.am.inited:
            return

        if self.trade_count >= self.max_trades_per_day:
            return

        if time.time() - self.last_trade_time < self.cooldown_seconds:
            return

        ema_fast = self.am.ema(self.fast_window)
        ema_slow = self.am.ema(self.slow_window)

        price = bar.close_price
        contract = self.cta_engine.main_engine.get_contract(self.vt_symbol)
        tick = contract.pricetick

        # ===== 开仓 =====
        if self.pos == 0:
            # AI模型判断趋势方向，剥头皮策略寻找入场时机
            if (self.trend_direction == 1 and ema_fast > ema_slow and self.check_orderflow("long")):
                self.buy(price, self.fixed_size)
                self.entry_price = price
                self.last_trade_time = time.time()
                self.trade_count += 1
                self.write_log(f"📈 AI+剥头皮多头入场: 价格 {price}, AI置信度 {self.prediction_confidence:.4f}")

            elif (self.trend_direction == -1 and ema_fast < ema_slow and self.check_orderflow("short")):
                self.short(price, self.fixed_size)
                self.entry_price = price
                self.last_trade_time = time.time()
                self.trade_count += 1
                self.write_log(f"📉 AI+剥头皮空头入场: 价格 {price}, AI置信度 {self.prediction_confidence:.4f}")

        # ===== 平仓 =====
        elif self.pos > 0:
            if price >= self.entry_price + self.take_profit_tick * tick:
                self.sell(price, abs(self.pos))
                self.write_log(f"✅ 多头止盈: 价格 {price}, 盈利 {(price - self.entry_price)/tick:.1f} ticks")
            elif price <= self.entry_price - self.stop_loss_tick * tick:
                self.sell(price, abs(self.pos))
                self.write_log(f"❌ 多头止损: 价格 {price}, 亏损 {(self.entry_price - price)/tick:.1f} ticks")

        elif self.pos < 0:
            if price <= self.entry_price - self.take_profit_tick * tick:
                self.cover(price, abs(self.pos))
                self.write_log(f"✅ 空头止盈: 价格 {price}, 盈利 {(self.entry_price - price)/tick:.1f} ticks")
            elif price >= self.entry_price + self.stop_loss_tick * tick:
                self.cover(price, abs(self.pos))
                self.write_log(f"❌ 空头止损: 价格 {price}, 亏损 {(price - self.entry_price)/tick:.1f} ticks")

    def on_5min_bar(self, bar):
        """5分钟K线回调，用于中期趋势判断"""
        self.am_5min.update_bar(bar)
        if not self.am_5min.inited:
            return

        ema_fast = self.am_5min.ema(self.fast_window)
        ema_slow = self.am_5min.ema(self.slow_window)

        price = bar.close_price
        contract = self.cta_engine.main_engine.get_contract(self.vt_symbol)
        tick = contract.pricetick

        # 可以在此处添加5分钟级别的交易逻辑
        # 这里只是示例，可以根据需要调整
        self.write_log(f"📊 5分钟K线更新: {bar.datetime}, 收盘价: {price}, 趋势: {'上涨' if ema_fast > ema_slow else '下跌'}")

    def on_15min_bar(self, bar):
        """15分钟K线回调，用于长期趋势判断"""
        self.am_15min.update_bar(bar)
        if not self.am_15min.inited:
            return

        ema_fast = self.am_15min.ema(self.fast_window)
        ema_slow = self.am_15min.ema(self.slow_window)

        price = bar.close_price
        contract = self.cta_engine.main_engine.get_contract(self.vt_symbol)
        tick = contract.pricetick

        # 可以在此处添加15分钟级别的交易逻辑
        # 这里只是示例，可以根据需要调整
        self.write_log(f"📈 15分钟K线更新: {bar.datetime}, 收盘价: {price}, 趋势: {'上涨' if ema_fast > ema_slow else '下跌'}")

    def on_order(self, order):
        """委托推送"""
        pass

    def on_trade(self, trade):
        """成交推送"""
        self.write_log(f"成交记录: {trade.direction.value} {trade.offset.value} "
                      f"{trade.volume}手 @ {trade.price}, 成交时间: {trade.datetime}")

        # 更新持仓后显示账户信息
        self.display_account_info()

    def display_account_info(self):
        """显示账户信息"""
        # 获取当前持仓和账户信息
        pos = self.get_position(self.vt_symbol)
        if pos:
            self.write_log(f"📊 当前持仓: {pos.volume}, 方向: {pos.direction}, 均价: {pos.price}")
        else:
            self.write_log("📊 当前无持仓")