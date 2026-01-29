from vnpy_ctastrategy import CtaTemplate
from vnpy.trader.utility import BarGenerator, ArrayManager
import time


class ScalpingOrderflowStrategy(CtaTemplate):
    """
    剥头皮 + 盘口过滤（实盘版）
    """

    author = "justseven"

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

    # ===== 变量 =====
    last_trade_time = 0
    trade_count = 0
    entry_price = 0
    last_tick_time = 0

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        self.bg = BarGenerator(self.on_bar)
        self.am = ArrayManager(50)

        self.last_tick = None

    def on_init(self):
        self.write_log("盘口过滤剥头皮策略初始化")
        self.load_bar(50)

    # ===== Tick：记录盘口 =====
    def on_tick(self, tick):
        self.last_tick = tick
        self.last_tick_time = time.time()
        self.bg.update_tick(tick)

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
            if ema_fast > ema_slow and self.check_orderflow("long"):
                self.buy(price, self.fixed_size)
                self.entry_price = price
                self.last_trade_time = time.time()
                self.trade_count += 1

            elif ema_fast < ema_slow and self.check_orderflow("short"):
                self.short(price, self.fixed_size)
                self.entry_price = price
                self.last_trade_time = time.time()
                self.trade_count += 1

        # ===== 平仓 =====
        elif self.pos > 0:
            if price >= self.entry_price + self.take_profit_tick * tick:
                self.sell(price, abs(self.pos))
            elif price <= self.entry_price - self.stop_loss_tick * tick:
                self.sell(price, abs(self.pos))

        elif self.pos < 0:
            if price <= self.entry_price - self.take_profit_tick * tick:
                self.cover(price, abs(self.pos))
            elif price >= self.entry_price + self.stop_loss_tick * tick:
                self.cover(price, abs(self.pos))
