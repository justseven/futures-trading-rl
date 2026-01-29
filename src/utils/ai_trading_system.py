import signal
import sys
import os
import json
from pathlib import Path
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# 将项目根目录添加到 sys.path 以支持模块导入
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# 模块导入修正为绝对路径风格（根据实际目录结构调整）
try:
    from src.models.ml_model import PricePredictionModel
except ImportError as e:
    print("无法导入 PricePredictionModel，请检查 src/models/ml_model.py 是否存在")
    raise e

try:
    from src.data.data_processor import DataProcessor
except ImportError as e:
    print("无法导入 DataProcessor，请检查 src/data/data_processor.py 是否存在")
    raise e

try:
    from src.data.data_collector import DataCollector
except ImportError as e:
    print("无法导入 DataCollector，请检查 src/data/data_collector.py 是否存在")
    raise e

try:
    from src.risk_management.risk_manager import RiskManager
except ImportError as e:
    print("无法导入 RiskManager，请检查 src/risk_management/risk_manager.py 是否存在")
    raise e

try:
    from src.strategies.predictive_trading_strategy import PredictiveTradingStrategy
except ImportError as e:
    print("无法导入 PredictiveTradingStrategy，请检查 src/strategies/predictive_trading_strategy.py 是否存在")
    raise e

# VNPy 相关导入保持不变
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp
from vnpy_ctp import CtpGateway
from vnpy_ctastrategy import CtaStrategyApp


# 全局变量用于存储系统实例，以便信号处理器可以访问
g_system_instance = None


def signal_handler(sig, frame):
    """处理中断信号的函数"""
    global g_system_instance
    
    print('\n正在安全关闭AI交易系统...')
    
    # 如果有系统实例，尝试清理资源
    if g_system_instance and hasattr(g_system_instance, 'main_engine'):
        try:
            # 断开网关连接
            g_system_instance.main_engine.close()
        except Exception as e:
            print(f"关闭过程中发生错误: {e}")
    
    sys.exit(0)


class AITradingSystem:
    """AI量化交易系统主类"""
    
    def __init__(self):
        self.event_engine = EventEngine()
        self.main_engine = MainEngine(self.event_engine)
        self.data_collector = DataCollector(self.main_engine)
        self.risk_manager = RiskManager()
        self.data_processor = DataProcessor()
        
        # 注册风险检查器
        self.main_engine.event_engine.register('event_order', self.risk_check_event)
        
        # 从配置文件加载CTP设置
        self.ctp_setting = self._load_ctp_setting()
    
    def _load_ctp_setting(self):
        """从配置文件加载CTP设置"""
        from pathlib import Path
        
        # 尝试从多个可能的位置加载配置
        config_paths = [
            "settings/simnow_setting_one.json",
            "settings/simnow_setting_two.json",
            "settings/simnow_setting_template.json",
            "settings/ctp_setting.json"
        ]
        
        for config_path in config_paths:
            path = Path(config_path)
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    
                    # 验证配置是否包含占位符
                    if ("<YOUR_USER_ID>" in str(config) or 
                        "<YOUR_PASSWORD>" in str(config)):
                        print(f"⚠️  警告: 配置文件 {config_path} 仍包含占位符")
                        print("   请编辑配置文件并填入您的真实账户信息")
                        continue
                    
                    return config
                except Exception as e:
                    print(f"加载配置文件 {config_path} 时出错: {e}")
                    continue
        
        print("❌ 未找到有效配置文件，请运行 setup_env.py 进行初始化")
        return None

    def risk_check_event(self, event):
        """风险检查事件处理器"""
        order = event.data
        if hasattr(order, 'vt_orderid'):  # 确保是订单对象
            # 检查订单是否符合风险管理规则
            is_valid = self.risk_manager.check_order(order)
            if not is_valid:
                self.main_engine.cancel_order(order)
                print(f"订单因风险控制被取消: {order.vt_orderid}")
    
    def connect_gateway(self, gateway_name, setting):
        """连接交易网关"""
        if gateway_name.lower() == 'ctp' and setting:
            self.main_engine.add_gateway(CtpGateway)
            self.main_engine.connect(setting, "CTP")
        # 可扩展其他网关如：SimNow, Femas等
        
    def train_model(self, symbol, exchange, start_date, end_date, model_type='lstm'):
        """训练预测模型"""
        try:
            print(f"开始训练 {symbol} 合约的 {model_type} 模型...")
            
            # 1. 获取历史数据
            data = self.data_collector.load_history_data(symbol, start_date, end_date)
            
            if data is None or len(data) == 0:
                print(f"❌ 无法获取 {symbol} 的历史数据")
                return False
            
            # 2. 数据预处理
            processed_data = self.data_processor.clean_data(data)
            features = self.data_processor.feature_engineering(processed_data)
            normalized_data = self.data_processor.normalize_data(features)
            
            # 3. 构建训练集
            X, y = self.prepare_training_data(normalized_data)
            
            if len(X) == 0:
                print(f"❌ 无法为 {symbol} 准备训练数据")
                return False
            
            # 4. 分割训练/测试集
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]
            
            # 5. 训练模型
            model = PricePredictionModel(model_type=model_type)
            model.train(X_train, y_train, X_test, y_test)
            
            # 6. 保存模型
            model_path = os.path.join('models', f'{exchange.value}_{symbol}_prediction_model.keras')
            model.save(model_path)
            
            print(f"✅ {symbol} 的预测模型训练完成，已保存至 {model_path}")
            return True
            
        except Exception as e:
            print(f"❌ 训练模型时出现错误: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    def start_trading(self, strategy_setting):
        """启动实盘交易"""
        cta_engine = self.main_engine.get_engine("CtaStrategy")
        if cta_engine:
            # 使用策略类而不是字符串
            strategy_class = PredictiveTradingStrategy
            strategy_name = f"predictive_strategy_{strategy_setting['vt_symbol'][:10]}_{int(datetime.now().timestamp())}"
            
            cta_engine.add_strategy(
                class_=strategy_class,
                strategy_name=strategy_name,
                vt_symbol=strategy_setting["vt_symbol"],
                setting={
                    "prediction_threshold": strategy_setting["prediction_threshold"],
                    "fixed_size": strategy_setting["fixed_size"],
                    "trailing_percent": strategy_setting["trailing_percent"]
                }
            )
            
            cta_engine.start_strategy(strategy_name)
            print(f"✅ 策略 {strategy_name} 已启动")
        else:
            print("❌ 无法获取CTA策略引擎")
        
    def run_ui(self):
        """运行UI界面"""
        qapp = create_qapp()
        main_window = MainWindow(self.main_engine, self.event_engine)
        main_window.showMaximized()
        qapp.exec_()
        
    def backtest_strategy(self, strategy_class, setting, vt_symbol, interval, start, end, 
                         rate, slippage, size, pricetick, capital=1000000):
        """运行回测（简化版）"""
        print("注意：完整回测功能需要使用vnpy的回测模块")
        print(f"将在 {start} 到 {end} 时间段内对 {vt_symbol} 进行回测")
        print(f"初始资金: {capital}")


def main():
    """系统主入口"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    global g_system_instance
    system = AITradingSystem()
    g_system_instance = system  # 将系统实例赋值给全局变量，以便信号处理器可以访问
    
    # 创建必要的目录
    os.makedirs("models", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    print("="*60)
    print("AI量化交易系统")
    print("="*60)
    print("1. 实盘交易")
    print("2. 模型训练")
    print("3. 策略回测")
    print("4. 连接CTP仿真环境")
    print("5. 连接CTP实盘环境")
    print("="*60)
    
    mode = input("请选择运行模式 (1-5): ").strip()
    
    if mode in ["1", "4", "5"]:
        # 连接到CTP网关
        print("\n正在加载CTP设置...")
        try:
            with open("settings/ctp_setting.json", "r", encoding="utf-8") as f:
                ctp_setting = json.load(f)
        except FileNotFoundError:
            print("错误: 未找到 settings/ctp_setting.json 配置文件")
            return
            
        if mode == "5":
            print("警告：您选择了实盘环境，请确认设置正确！")
            confirm = input("确认继续? (y/N): ")
            if confirm.lower() != 'y':
                print("操作已取消")
                return
        
        system.connect_gateway("ctp", ctp_setting)
        
        # 启动交易策略
        strategy_setting = {
            "vt_symbol": input("请输入交易合约 (例如 rb2105.SHFE): ").strip(),
            "prediction_threshold": float(input("请输入预测阈值 (默认0.01): ") or "0.01"),
            "fixed_size": int(input("请输入固定手数 (默认1): ") or "1"),
            "trailing_percent": float(input("请输入跟踪止损百分比 (默认0.8): ") or "0.8")
        }
        
        system.start_trading(strategy_setting)
        
        # 启动UI
        print("\n启动交易界面...")
        system.run_ui()
        
    elif mode == "2":
        # 模型训练
        symbol = input("请输入要训练的合约符号 (例如 rb2105): ").strip()
        exchange_str = input("请输入交易所 (例如 SHFE): ").strip()
        start_date = input("请输入开始日期 (YYYY-MM-DD): ").strip()
        end_date = input("请输入结束日期 (YYYY-MM-DD): ").strip()
        model_type = input("请选择模型类型 (lstm/cnn-lstm/random_forest/svm，默认lstm): ") or "lstm"
        
        from vnpy.trader.constant import Exchange
        exchange_map = {
            'SHFE': Exchange.SHFE,
            'DCE': Exchange.DCE,
            'CZCE': Exchange.CZCE,
            'INE': Exchange.INE,
            'GFEX': Exchange.GFEX
        }
        exchange = exchange_map.get(exchange_str.upper(), Exchange.SHFE)
        
        success = system.train_model(
            symbol=symbol,
            exchange=exchange,
            start_date=start_date,
            end_date=end_date,
            model_type=model_type
        )
        
        if success:
            print(f"\n{symbol} 的预测模型训练完成！")
        else:
            print(f"\n{symbol} 的预测模型训练失败！")
    
    elif mode == "3":
        # 策略回测
        print("策略回测功能开发中...")
        # 此处可集成vnpy的回测功能
    else:
        print("无效的选择")


if __name__ == "__main__":
    main()