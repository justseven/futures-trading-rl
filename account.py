class Account:
    """
    极简但稳定的交易账户
    """

    def __init__(self, cash=1_000_000.0):
        self.initial_cash = cash
        self.reset()

    def reset(self):
        self.initial_cash = 1_000_000.0
        self.cash = self.initial_cash
        self.position = 0       # 0=空仓, 1=多头
        self.entry_price = None
        self.trade_count = 0

    def open_long(self, price: float):
        if self.position == 0:
            self.position = 1
            self.entry_price = price
            self.trade_count += 1

    def close_long(self, price: float) -> float:
        if self.position == 1:
            pnl = price - self.entry_price
            self.cash += pnl
            self.position = 0
            self.entry_price = None
            return pnl
        return 0.0

    def total_equity(self) -> float:
        return self.cash
