class RiskManager:

    def __init__(
        self,
        max_pos: int = 1,
        max_daily_loss: float = 5000
    ):
        self.max_pos = max_pos
        self.max_daily_loss = max_daily_loss
        self.trading_enabled = True

    def check(self, strategy) -> bool:
        if not self.trading_enabled:
            return False

        if abs(strategy.pos) >= self.max_pos:
            return False

        if strategy.cta_engine.get_account().balance - \
           strategy.cta_engine.get_account().available > self.max_daily_loss:
            self.trading_enabled = False
            return False

        return True
