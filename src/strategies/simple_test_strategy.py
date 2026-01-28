from vnpy_ctastrategy import CtaTemplate
from vnpy.trader.object import TickData, BarData
from vnpy.trader.constant import Direction


class SimpleTestStrategy(CtaTemplate):
    """简单测试策略"""
    
    author = "AI Trader"
    
    # 策略参数
    fixed_size = 1
    
    # 参数列表
    parameters = ["fixed_size"]
    
    # 变量列表
    variables = ["pos"]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        
        self.pos = 0  # 持仓
        self.last_price = 0  # 最新价格

    def on_init(self):
        """策略初始化"""
        self.write_log("简单测试策略初始化")

    def on_start(self):
        """策略启动"""
        self.write_log("简单测试策略启动")

    def on_stop(self):
        """策略停止"""
        self.write_log("简单测试策略停止")

    def on_tick(self, tick: TickData):
        """行情推送"""
        self.last_price = tick.last_price
        # 简单的测试逻辑，不执行复杂的操作

    def on_bar(self, bar: BarData):
        """K线推送"""
        # 简单的测试逻辑，不执行复杂的操作
        pass

    def on_order(self, order):
        """委托推送"""
        pass

    def on_trade(self, trade):
        """成交推送"""
        self.write_log(f"成交信息: {trade.direction}, 价格: {trade.price}, 数量: {trade.volume}")