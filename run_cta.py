from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_ctp import CtpGateway
from vnpy_ctastrategy import CtaEngine
from strategies.model_cta_strategy import ModelCtaStrategy

def main():
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)

    main_engine.add_gateway(CtpGateway)
    cta_engine = main_engine.add_app(CtaEngine)

    main_engine.connect(
        {
            "用户名": "xxx",
            "密码": "xxx",
            "经纪商代码": "9999",
            "交易服务器": "...",
            "行情服务器": "...",
            "产品名称": "simnow_client_test",
            "授权编码": "0000000000000000",
        },
        "CTP"
    )

    cta_engine.add_strategy(
        ModelCtaStrategy,
        "rb_model_strategy",
        "rb2405.SHFE",
        {
            "model_path": "models/registry/rb_lstm.h5",
            "max_pos": 1,
            "max_daily_loss": 3000
        }
    )

    cta_engine.init_strategy("rb_model_strategy")
    cta_engine.start_strategy("rb_model_strategy")

if __name__ == "__main__":
    main()
