import signal
import sys
import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# 将项目根目录添加到 sys.path 以支持模块导入
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# 模块导入修正为绝对路径风格（根据实际目录结构调整）
try:
    from models.ml_model import PricePredictionModel
except ImportError as e:
    print("无法导入 PricePredictionModel，请检查 models/ml_model.py 是否存在")
    raise e

try:
    from data.data_processor import DataProcessor
except ImportError as e:
    print("无法导入 DataProcessor，请检查 data/data_processor.py 是否存在")
    raise e

try:
    from data.data_collector import DataCollector
except ImportError as e:
    print("无法导入 DataCollector，请检查 data/data_collector.py 是否存在")
    raise e

try:
    from risk.risk_manager import RiskManager
except ImportError as e:
    print("无法导入 RiskManager，请检查 risk/risk_manager.py 是否存在")
    raise e

try:
    from strategies.predictive_trading_strategy import PredictiveTradingStrategy
except ImportError as e:
    print("无法导入 PredictiveTradingStrategy，请检查 strategies/predictive_trading_strategy.py 是否存在")
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
        
    def risk_check_event(self, event):
        """风险检查事件处理"""
        order = event.data
        if hasattr(order, 'vt_orderid'):  # 确保是订单对象
            # 检查订单是否符合风险管理规则
            is_valid = self.risk_manager.check_order(order)
            if not is_valid:
                self.main_engine.cancel_order(order)
                print(f"订单因风险控制被取消: {order.vt_orderid}")
    
    def connect_gateway(self, gateway_name, setting):
        """连接交易网关"""
        if gateway_name.lower() == 'ctp':
            self.main_engine.add_gateway(CtpGateway)
            self.main_engine.connect(setting, "CTP")
            print(f"已连接到CTP网关")
        # 可扩展其他网关如：SimNow, Femas等
        
    def train_model(self, symbol, exchange, start_date, end_date, model_type='lstm'):
        """训练预测模型"""
        print(f"开始训练 {symbol} 的预测模型...")
        
        # 1. 获取历史数据
        print("正在获取历史数据...")
        data = self.data_collector.load_history_data(
            symbol=symbol,
            exchange=exchange,
            start_date=start_date,
            end_date=end_date
        )
        
        if data.empty:
            print(f"无法获取 {symbol} 的历史数据，训练终止")
            return False
        
        print(f"获取到 {len(data)} 条历史数据")
        
        # 2. 数据预处理
        print("正在进行数据预处理...")
        cleaned_data = self.data_processor.clean_data(data)
        engineered_data = self.data_processor.feature_engineering(cleaned_data)
        processed_data = self.data_processor.normalize_data(engineered_data)
        
        # 3. 准备训练数据
        print("正在准备训练数据...")
        sequence_length = 60
        X, y = self.data_processor.prepare_supervised_data(processed_data, lookback=sequence_length)
        
        if len(X) == 0:
            print("没有足够的数据用于训练")
            return False
            
        # 4. 分割训练/测试集 (80% 训练, 20% 测试)
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        print(f"训练集大小: {len(X_train)}, 测试集大小: {len(X_test)}")
        
        # 5. 创建并训练模型
        print("正在创建和训练模型...")
        model = PricePredictionModel(
            model_type=model_type,
            sequence_length=sequence_length,
            n_features=X.shape[2] if len(X.shape) > 2 else 1
        )
        
        # 训练模型
        history = model.train(
            X_train=X_train,
            y_train=y_train,
            X_val=X_test,
            y_val=y_test,
            epochs=50,
            batch_size=32
        )
        
        # 6. 评估模型
        print("正在评估模型...")
        evaluation = model.evaluate(X_test, y_test)
        print(f"模型评估结果: {evaluation}")
        
        # 7. 保存模型
        model_dir = "models"
        os.makedirs(model_dir, exist_ok=True)
        symbol_safe = symbol.replace('.', '_')
        model_path = os.path.join(model_dir, f"{symbol_safe}_prediction_model.h5")
        model.save_model(model_path)
        
        print(f"模型已保存至: {model_path}")
        return True
        
    def start_trading(self, strategy_setting):
        """启动实盘交易"""
        cta_engine = self.main_engine.get_engine("CtaStrategy")
        
        # 添加策略
        cta_engine.add_strategy(
            PredictiveTradingStrategy, 
            {
                "class_name": "PredictiveTradingStrategy",
                "author": "AI Trader",
                "vt_symbol": strategy_setting["vt_symbol"],
                "setting": {
                    "prediction_threshold": strategy_setting.get("prediction_threshold", 0.01),
                    "fixed_size": strategy_setting.get("fixed_size", 1),
                    "trailing_percent": strategy_setting.get("trailing_percent", 0.8)
                }
            }
        )
        
        # 启动策略
        strategy_name = f"PredictiveStrategy_{strategy_setting['vt_symbol'].replace('.', '_')}"
        cta_engine.init_strategy(strategy_name)
        cta_engine.start_strategy(strategy_name)
        
        print(f"策略 {strategy_name} 已启动")
        
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