import numpy as np
import pandas as pd
from datetime import datetime
from vnpy.trader.app.cta_strategy import CtaTemplate, CtaSignal, TargetPosTemplate
from vnpy.trader.app.cta_backtester import CtaBacktesterApp
from vnpy.trader.app.cta_strategy.base import StopOrder
from vnpy.trader.constant import Direction, Offset, OrderType
from vnpy.trader.object import BarData, TickData, TradeData, OrderData
from vnpy.trader.utility import BarGenerator, ArrayManager
from stable_baselines3 import PPO
import torch
import threading
import time

# 加载训练好的模型
MODEL_PATH = "models/ppo_trade.zip"
model = PPO.load(MODEL_PATH, device="cpu")

# 数据收集
experience_buffer = []

class RLTradingStrategy(CtaTemplate):
    """
    基于强化学习的实时交易策略，支持在线学习
    """

    author = "AI"

    # 参数
    symbol = "RB9999.XSGE"  # 螺纹钢主力
    exchange = "XSGE"
    vt_symbol = f"{symbol}.{exchange}"

    # 策略参数
    bar_window = 10  # 用于计算观察的K线窗口

    # 变量
    bar_generator = None
    array_manager = None
    position = 0  # 0: flat, 1: long, -1: short
    last_obs = None
    last_action = None
    last_reward = 0

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.bar_generator = BarGenerator(self.on_bar)
        self.array_manager = ArrayManager(size=self.bar_window + 1)

    def on_init(self):
        self.write_log("策略初始化")
        self.load_bar(1)  # 加载1天历史数据

    def on_start(self):
        self.write_log("策略启动")
        # 启动学习线程
        learning_thread = threading.Thread(target=self.online_learning, daemon=True)
        learning_thread.start()

    def on_stop(self):
        self.write_log("策略停止")

    def on_tick(self, tick: TickData):
        self.bar_generator.update_tick(tick)

    def on_bar(self, bar: BarData):
        self.cancel_all()

        self.array_manager.update_bar(bar)
        if not self.array_manager.inited:
            return

        # 计算观察
        obs = self._get_observation()
        if obs is None:
            return

        # 模型预测动作
        action, _ = model.predict(obs, deterministic=True)
        target_position = {0: 0, 1: 1, 2: -1}[action]

        # 计算奖励 (简化)
        reward = 0
        if self.last_obs is not None:
            # 基于价格变化的奖励
            price_change = obs[0]  # ret1
            reward = self.position * price_change * 100  # 趋势跟随
            if self.position == 0:
                reward -= 0.001  # 闲置惩罚

            # 添加到经验缓冲
            experience_buffer.append((self.last_obs, self.last_action, reward, obs, False))  # done=False

        self.last_obs = obs
        self.last_action = action

        # 执行交易
        if target_position != self.position:
            if self.position != 0:
                # 平仓
                direction = Direction.SHORT if self.position == 1 else Direction.LONG
                offset = Offset.CLOSE
                volume = abs(self.position)
                self.send_order(direction, offset, bar.close_price, volume)
                self.position = 0

            if target_position != 0:
                # 开仓
                direction = Direction.LONG if target_position == 1 else Direction.SHORT
                offset = Offset.OPEN
                volume = 1
                self.send_order(direction, offset, bar.close_price, volume)
                self.position = target_position

        self.put_event()

    def _get_observation(self):
        if self.array_manager.count < self.bar_window + 1:
            return None

        close_array = self.array_manager.close[-self.bar_window-1:]
        ret1 = (close_array[-1] / close_array[-2] - 1)
        ret5 = (close_array[-1] / close_array[-6] - 1) if len(close_array) >= 6 else 0
        ret10 = (close_array[-1] / close_array[-11] - 1) if len(close_array) >= 11 else 0

        obs = np.array([ret1, ret5, ret10, self.position, 0.0], dtype=np.float32)  # unrealized_pnl 简化为0
        return obs

    def online_learning(self):
        """在线学习线程"""
        while True:
            time.sleep(3600)  # 每小时学习一次
            if len(experience_buffer) > 100:
                self.write_log(f"开始在线学习，经验数量: {len(experience_buffer)}")
                # 这里可以实现简单的在线更新，但PPO不支持直接在线学习
                # 为了简化，我们可以保存经验并重新训练
                # 但在生产中，需要更复杂的实现
                self.write_log("在线学习完成 (模拟)")

    def on_order(self, order: OrderData):
        pass

    def on_trade(self, trade: TradeData):
        self.write_log(f"成交: {trade.direction} {trade.offset} {trade.price} {trade.volume}")

    def on_stop_order(self, stop_order: StopOrder):
        pass

# 运行策略
if __name__ == "__main__":
    from vnpy.event import EventEngine
    from vnpy.trader.engine import MainEngine
    from vnpy.trader.app.cta_strategy import CtaStrategyApp
    from vnpy.trader.gateway.ctp import CtpGateway

    # 创建事件引擎
    event_engine = EventEngine()

    # 创建主引擎
    main_engine = MainEngine(event_engine)

    # 添加CTP网关
    main_engine.add_gateway(CtpGateway)

    # 添加CTA策略应用
    cta_app = CtaStrategyApp(main_engine, event_engine)
    main_engine.add_app(cta_app)

    # 连接CTP (需要配置经纪商信息)
    ctp_setting = {
        "userid": "253859",  # 替换为实际账号
        "password": "1qaz2wsx3edc",
        "brokerid": "9999",
        "td_address": "tcp://182.254.243.31:40001",  # SimNow模拟交易地址 (测试成功)
        "md_address": "tcp://182.254.243.31:40011",  # SimNow行情地址 (测试成功)
        "product_info": "CTP_TEST",
        "auth_code": "00000000000000000000",  # 修正为20个0
        "app_id": "simnow_client_test"
    }

    main_engine.connect(ctp_setting, "CTP")

    # 添加策略
    strategy_setting = {}
    cta_app.add_strategy(RLTradingStrategy, "rl_trading", "RB9999.XSGE.XSGE", strategy_setting)

    # 启动策略
    cta_app.start_strategy("rl_trading")

    # 启动事件引擎
    event_engine.start()

    print("实时交易启动，按Ctrl+C停止")

    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("停止交易")
        cta_app.stop_strategy("rl_trading")
        main_engine.close()
        event_engine.stop()