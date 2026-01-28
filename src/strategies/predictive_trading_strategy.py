from vnpy_ctastrategy import CtaTemplate
from vnpy.trader.object import TickData, BarData, TradeData, OrderData
from vnpy.trader.constant import Direction, Offset, OrderType
import numpy as np
from datetime import datetime, timedelta
import os
import logging
from src.models.ml_model import PricePredictionModel
from src.data.data_processor import DataProcessor


class PredictiveTradingStrategy(CtaTemplate):
    """基于预测模型的交易策略"""
    
    author = "AI Trader"
    
    # 策略参数
    prediction_threshold = 0.01          # 预测阈值，当预测涨跌幅超过此值时考虑交易
    fixed_size = 1                       # 固定交易手数
    trailing_percent = 0.8               # 跟踪止损百分比
    risk_reward_ratio = 2.0              # 风险收益比
    max_position_percent = 0.2           # 最大仓位占比
    model_update_interval = 3600         # 模型更新间隔（秒）
    
    # 策略变量
    prediction_value = 0.0               # 模型预测值
    last_price = 0.0                     # 最新价格
    highest_price = 0.0                  # 最高价格（用于跟踪止盈）
    lowest_price = 0.0                   # 最低价格（用于跟踪止损）
    entry_price = 0.0                    # 入场价格
    prediction_datetime = None           # 预测时间
    last_model_update = None             # 上次模型更新时间
    
    # 参数列表
    parameters = [
        "prediction_threshold", 
        "fixed_size", 
        "trailing_percent",
        "risk_reward_ratio",
        "max_position_percent"
    ]
    
    # 变量列表
    variables = [
        "prediction_value", 
        "last_price", 
        "pos",
        "entry_price"
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        
        self.model = None
        self.data_processor = DataProcessor()
        self.price_history = []  # 保存价格历史用于预测
        self.window_size = 60    # 用于预测的历史窗口大小
        self.min_history_size = 100  # 最小历史数据量
        
        # 初始化模型
        self.init_model()
        
        # 设置日志
        self.logger = logging.getLogger(f"strategy.{strategy_name}")

    def init_model(self):
        """初始化预测模型"""
        try:
            model_path = f"../models/{self.vt_symbol.replace('.', '_')}_prediction_model.h5"
            if os.path.exists(model_path):
                self.model = PricePredictionModel(model_type='lstm', sequence_length=self.window_size, n_features=10)
                self.model.load_model(model_path)
                self.write_log(f"成功加载模型: {model_path}")
            else:
                self.write_log(f"模型文件不存在: {model_path}，将使用随机预测直到模型训练完成")
                # 初始化一个默认模型
                self.model = PricePredictionModel(model_type='lstm', sequence_length=self.window_size, n_features=10)
                # 这里我们可以训练一个简单的模型或使用随机权重
        except Exception as e:
            self.write_log(f"初始化模型失败: {e}")
            # 创建一个基本的模型实例，即使无法加载预训练模型
            try:
                self.model = PricePredictionModel(model_type='lstm', sequence_length=self.window_size, n_features=10)
            except Exception:
                self.write_log("无法创建模型实例，将仅基于技术指标进行交易")
                self.model = None

    def on_init(self):
        """策略初始化"""
        self.write_log("策略初始化")
        
        # 立即完成初始化，不等待历史数据加载
        self.write_log("策略初始化完成（快速模式）")

    def on_start(self):
        """策略启动"""
        self.write_log("策略启动")

    def on_stop(self):
        """策略停止"""
        self.write_log("策略停止")

    def on_tick(self, tick: TickData):
        """行情推送"""
        self.last_price = tick.last_price
        
        # 更新价格历史
        if len(self.price_history) >= self.window_size:
            self.price_history.pop(0)
        self.price_history.append(tick.last_price)
        
        # 每隔一段时间进行预测
        if len(self.price_history) >= self.window_size and \
           (self.prediction_datetime is None or 
            (tick.datetime - self.prediction_datetime).seconds >= 60):  # 每分钟预测一次
            
            self.generate_prediction()
            self.execute_trading_logic()

    def on_bar(self, bar: BarData):
        """K线推送"""
        # 更新价格历史
        if len(self.price_history) >= self.window_size:
            self.price_history.pop(0)
        self.price_history.append(bar.close_price)
        
        # 每根K线更新一次预测
        if len(self.price_history) >= self.window_size:
            self.generate_prediction()
            self.execute_trading_logic()

    def generate_prediction(self):
        """生成预测"""
        if not self.model or len(self.price_history) < self.window_size:
            return
            
        try:
            # 准备预测数据
            # 这里我们简化处理，实际应用中可能需要更多特征
            hist_array = np.array(self.price_history)
            
            # 创建并使用新的scaler实例进行标准化
            from sklearn.preprocessing import MinMaxScaler
            scaler = MinMaxScaler()
            scaled_hist = scaler.fit_transform(hist_array.reshape(-1, 1))
            
            # 重塑为模型输入格式
            X = scaled_hist.reshape(1, self.window_size, 1)
            
            # 预测
            prediction = self.model.predict(X)
            
            # 反归一化
            pred_rescaled = scaler.inverse_transform(prediction.reshape(-1, 1))
            self.prediction_value = pred_rescaled[0, 0]
            
            self.prediction_datetime = datetime.now()
            
            self.write_log(f"预测值: {self.prediction_value:.2f}, 当前价格: {self.last_price:.2f}")
        except Exception as e:
            self.write_log(f"预测失败: {e}")

    def execute_trading_logic(self):
        """执行交易逻辑"""
        if not self.prediction_value or self.last_price == 0:
            return
            
        # 计算预期收益率
        expected_return = (self.prediction_value - self.last_price) / self.last_price
        
        # 计算实际下单手数（考虑最大仓位限制）
        # 获取账户资金
        gateway_name = self.vt_symbol.split('.')[1]  # 从vt_symbol中提取网关名
        account = self.get_account(gateway_name)
        if account:
            account_balance = account.balance
        else:
            # 如果无法获取账户信息，使用默认值
            account_balance = 1000000  # 默认100万
            
        # 获取合约乘数
        contract = self.get_contract(self.vt_symbol)
        contract_size = contract.size if contract else 10  # 默认10
        
        max_allowable_size = int((account_balance * self.max_position_percent) / 
                                (self.last_price * contract_size))
        actual_size = min(self.fixed_size, max_allowable_size, 10)  # 限制最大下单量
        
        # 根据预测值执行交易决策
        if abs(expected_return) > self.prediction_threshold:
            # 预测方向性交易
            if expected_return > self.prediction_threshold and self.pos == 0:
                # 预测上涨且幅度超过阈值，开多仓
                self.buy(self.last_price + 1, actual_size)
                self.entry_price = self.last_price
                self.write_log(f"预测上涨 {expected_return:.2%}，开多仓: {actual_size}手")
            elif expected_return > self.prediction_threshold and self.pos < 0:
                # 预测上涨，平空仓再开多仓
                self.cover(self.last_price + 1, abs(self.pos))
                self.buy(self.last_price + 1, actual_size)
                self.entry_price = self.last_price
                self.write_log(f"预测上涨 {expected_return:.2%}，平空开多: {actual_size}手")
            elif expected_return < -self.prediction_threshold and self.pos == 0:
                # 预测下跌且幅度超过阈值，开空仓
                self.short(self.last_price - 1, actual_size)
                self.entry_price = self.last_price
                self.write_log(f"预测下跌 {expected_return:.2%}，开空仓: {actual_size}手")
            elif expected_return < -self.prediction_threshold and self.pos > 0:
                # 预测下跌，平多仓再开空仓
                self.sell(self.last_price - 1, self.pos)
                self.short(self.last_price - 1, actual_size)
                self.entry_price = self.last_price
                self.write_log(f"预测下跌 {expected_return:.2%}，平多开空: {actual_size}手")
        
        # 更新跟踪止损/止盈
        self.update_trailing_stop()

    def update_trailing_stop(self):
        """更新跟踪止损"""
        if self.pos > 0:  # 持有多头仓位
            # 更新最高价
            if self.last_price > self.highest_price:
                self.highest_price = self.last_price
            
            # 计算跟踪止损价（价格上涨后回调一定百分比则卖出）
            trailing_stop = self.highest_price * (1 - self.trailing_percent / 100)
            if self.last_price < trailing_stop and self.pos > 0:
                self.sell(self.last_price - 1, abs(self.pos))
                self.write_log(f"多头跟踪止损触发，平仓价格: {self.last_price:.2f}")
                
        elif self.pos < 0:  # 持有空头仓位
            # 更新最低价
            if self.last_price < self.lowest_price:
                self.lowest_price = self.last_price
            
            # 计算跟踪止损价（价格下跌后反弹一定百分比则买平）
            trailing_stop = self.lowest_price * (1 + self.trailing_percent / 100)
            if self.last_price > trailing_stop and self.pos < 0:
                self.cover(self.last_price + 1, abs(self.pos))
                self.write_log(f"空头跟踪止损触发，买平价格: {self.last_price:.2f}")

    def on_order(self, order: OrderData):
        """委托推送"""
        if order.is_active():
            self.write_log(f"委托状态: {order.vt_orderid}, 状态: {order.status}, 价格: {order.price}, 数量: {order.volume}")
        else:
            self.write_log(f"委托完成: {order.vt_orderid}, 状态: {order.status}")

    def on_trade(self, trade: TradeData):
        """成交推送"""
        self.write_log(f"成交信息: {trade.vt_symbol}, 方向: {trade.direction}, "
                      f"开平: {trade.offset}, 价格: {trade.price}, 数量: {trade.volume}")
        
        # 成交后重置相关变量
        if trade.direction == Direction.LONG and trade.offset == Offset.OPEN:
            # 开多成交
            self.entry_price = trade.price
            self.highest_price = trade.price
            self.lowest_price = trade.price
        elif trade.direction == Direction.SHORT and trade.offset == Offset.OPEN:
            # 开空成交
            self.entry_price = trade.price
            self.highest_price = trade.price
            self.lowest_price = trade.price

    def get_account_balance(self):
        """获取账户余额"""
        gateway_name = self.vt_symbol.split('.')[1]  # 从vt_symbol中提取网关名
        account = self.get_account(gateway_name)
        return account.balance if account else 1000000  # 默认100万

    def get_contract_size(self):
        """获取合约乘数"""
        contract = self.get_contract(self.vt_symbol)
        return contract.size if contract else 10  # 默认10

    def update_model_if_needed(self):
        """根据需要更新模型"""
        now = datetime.now()
        if (self.last_model_update is None or 
            (now - self.last_model_update).seconds >= self.model_update_interval):
            
            # 尝试加载新模型
            model_path = f"../models/{self.vt_symbol.replace('.', '_')}_prediction_model.h5"
            if os.path.exists(model_path):
                try:
                    new_model = PricePredictionModel(model_type='lstm', sequence_length=self.window_size, n_features=10)
                    new_model.load_model(model_path)
                    self.model = new_model
                    self.last_model_update = now
                    self.write_log(f"模型已更新: {model_path}")
                except Exception as e:
                    self.write_log(f"更新模型失败: {e}")
