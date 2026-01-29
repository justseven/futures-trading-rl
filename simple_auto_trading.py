# smart_auto_trading.py
# ===============================
# vn.py 4.x compatible
# ===============================

import os
import time
import traceback
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import tensorflow as tf
from tensorflow.keras.models import load_model

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_ctp import CtpGateway
from vnpy_ctastrategy import CtaStrategyApp, CtaTemplate


# ==========================================================
# CTA 策略（最小可运行版本）
# ==========================================================
class HybridTrendScalpStrategy(CtaTemplate):
    author = "justseven"

    fixed_size = 1
    max_daily_loss = 3000

    def on_init(self):
        self.write_log("HybridTrendScalpStrategy 初始化完成")

    def on_bar(self, bar):
        # 示例：不自动交易，只验证系统链路
        pass


# ==========================================================
# 主系统
# ==========================================================
class SmartAutoTradingSystem:

    def __init__(self):
        self.event_engine = None
        self.main_engine = None
        self.cta_engine = None

        self.model = None
        self.scaler = MinMaxScaler()

        self.model_path = os.path.join(
            "models",
            "SHFE_rb2605_prediction_model.keras"
        )

        # 从配置文件加载CTP设置，而不是硬编码
        self.ctp_setting = self._load_ctp_setting()

    def _load_ctp_setting(self):
        """从配置文件加载CTP设置"""
        import json
        from pathlib import Path
        
        # 尝试从多个可能的位置加载配置
        config_paths = [
            "settings/simnow_setting_one.json",
            "settings/simnow_setting_two.json",
            "settings/ctp_setting.json"
        ]
        
        for config_path in config_paths:
            path = Path(config_path)
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        
        # 如果没有找到配置文件，则返回模板配置
        return {
            "用户名": "<YOUR_USER_ID>",
            "密码": "<YOUR_PASSWORD>",
            "经纪商代码": "9999",
            "交易服务器": "tcp://182.254.243.31:30001", 
            "行情服务器": "tcp://182.254.243.31:30011",  
            "AppID": "simnow_client_test",
            "授权编码": "0000000000000000", 
            "产品名称": "simnow_client_test",
            "柜台环境": "实盘"
        }

    # ------------------------------------------------------
    # 模型加载 / 训练（简化但正确）
    # ------------------------------------------------------
    def init_model(self):
        print("🔄 初始化预测模型...")

        if os.path.exists(self.model_path):
            print(f"✅ 加载已有模型: {self.model_path}")
            self.model = load_model(self.model_path)
            return

        print("⚠️ 未找到模型，创建新模型")

        # dummy 数据（只为保证流程正确）
        x = np.random.rand(1000, 10)
        y = np.random.rand(1000, 1)

        self.scaler.fit(x)
        x = self.scaler.transform(x)

        model = tf.keras.Sequential([
            tf.keras.layers.Dense(32, activation="relu"),
            tf.keras.layers.Dense(1)
        ])

        model.compile(optimizer="adam", loss="mse")
        model.fit(x, y, epochs=3, batch_size=32, verbose=1)

        os.makedirs("models", exist_ok=True)
        model.save(self.model_path)

        self.model = model
        print(f"✅ 模型已保存: {self.model_path}")

    # ------------------------------------------------------
    # vn.py 初始化（关键）
    # ------------------------------------------------------
    def init_vnpy(self):
        print("🔄 初始化 vn.py 引擎")

        self.event_engine = EventEngine()
        self.main_engine = MainEngine(self.event_engine)

        self.main_engine.add_gateway(CtpGateway)

        # 🔥 这是最关键的一行
        self.main_engine.add_app(CtaStrategyApp)

        self.cta_engine = self.main_engine.get_engine("cta_strategy")
        if self.cta_engine is None:
            raise RuntimeError("CTA 引擎初始化失败")

        print("✅ CTA 引擎初始化成功")

    # ------------------------------------------------------
    # 连接 CTP
    # ------------------------------------------------------
    def connect_ctp(self):
        print("🔄 连接 CTP...")
        self.main_engine.connect(self.ctp_setting, "CTP")

    # ------------------------------------------------------
    # 启动策略
    # ------------------------------------------------------
    def start_strategy(self):
        print("🚀 启动 CTA 策略")

        self.cta_engine.add_strategy(
            HybridTrendScalpStrategy,
            "hybrid_trend_scalp",
            "rb2605.SHFE",
            {}
        )

        self.cta_engine.init_strategy("hybrid_trend_scalp")
        self.cta_engine.start_strategy("hybrid_trend_scalp")

        print("✅ CTA 策略已启动")

    # ------------------------------------------------------
    # 主入口
    # ------------------------------------------------------
    def run(self):
        try:
            print("期货智能自动交易系统")
            print("=" * 50)

            self.init_model()
            self.init_vnpy()
            self.connect_ctp()

            # 等待 CTP 完成登录
            time.sleep(5)

            self.start_strategy()

            print("✅ 系统启动完成，进入事件循环")
            while True:
                time.sleep(1)

        except Exception as e:
            print("❌ 系统异常退出")
            traceback.print_exc()


# ==========================================================
# main
# ==========================================================
if __name__ == "__main__":
    system = SmartAutoTradingSystem()
    system.run()
