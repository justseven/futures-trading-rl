from vnpy_ctastrategy import CtaTemplate
from data.features.feature_pipeline import FeaturePipeline
from models.lstm_model import LSTMTrendModel
from risk.risk_manager import RiskManager

class ModelCtaStrategy(CtaTemplate):

    author = "justseven"

    fixed_size = 1
    signal_threshold = 0.6

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        self.feature_pipeline = FeaturePipeline(window=30)

        self.model = LSTMTrendModel(
            model_path=setting["model_path"],
            scaler_path=setting.get("scaler_path")
        )

        self.risk = RiskManager(
            max_pos=setting.get("max_pos", 1),
            max_daily_loss=setting.get("max_daily_loss", 5000)
        )

    def on_init(self):
        self.write_log("模型策略初始化完成")
        self.load_bar(30)

    def on_bar(self, bar):
        features = self.feature_pipeline.update(bar)
        if features is None:
            return

        if not self.risk.check(self):
            return

        signal = self.model.predict(features)

        if signal > self.signal_threshold and self.pos <= 0:
            self.buy(bar.close_price, self.fixed_size)

        elif signal < -self.signal_threshold and self.pos >= 0:
            self.short(bar.close_price, self.fixed_size)

    def on_stop(self):
        self.write_log("策略停止")
