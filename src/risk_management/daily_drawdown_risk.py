from datetime import date


class DailyDrawdownRisk:
    """
    日内最大回撤熔断（实盘硬风控）
    """

    def __init__(self, max_daily_loss: float):
        self.max_daily_loss = max_daily_loss

        self.trading_enabled = True
        self.day_start_balance = None
        self.current_day = date.today()

    def update_account(self, account):
        """
        每次收到账户回报时调用
        """
        today = date.today()

        # 新交易日，重置
        if today != self.current_day:
            self.current_day = today
            self.day_start_balance = account.balance
            self.trading_enabled = True

        # 首次初始化
        if self.day_start_balance is None:
            self.day_start_balance = account.balance
            return

        # 检查回撤
        drawdown = self.day_start_balance - account.balance
        if drawdown >= self.max_daily_loss:
            self.trading_enabled = False

    def allow_trade(self) -> bool:
        return self.trading_enabled
