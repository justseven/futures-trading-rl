import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import create_qapp
from vnpy_ctp import CtpGateway
from vnpy_ctastrategy import CtaStrategyApp
from src.strategies.predictive_trading_strategy import PredictiveTradingStrategy
from src.strategies.simple_test_strategy import SimpleTestStrategy  # 新增导入
from src.data.data_processor import DataProcessor
from src.models.ml_model import PricePredictionModel
import os
import json
import sys
import signal
import threading
import time
from datetime import datetime

# 添加src目录到Python路径，确保能够找到自定义模块
current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)

# 添加项目根目录和src目录到sys.path
sys.path.insert(0, parent_dir)
sys.path.insert(0, os.path.join(parent_dir, 'src'))

# 导入自定义模块 - 使用绝对导入
try:
    from data.data_collector import DataCollector
    from data.data_processor import DataProcessor
    from models.ml_model import PricePredictionModel
    from models.train_and_backtest import ModelTrainerAndBacktester
    from strategies.predictive_trading_strategy import PredictiveTradingStrategy
    from risk_management.risk_manager import RiskManager
except ImportError as e:
    print(f"导入模块失败: {e}")
    # 如果上面的导入失败，尝试另一种导入方式
    sys.path.insert(0, parent_dir)
    from data.data_collector import DataCollector
    from data.data_processor import DataProcessor
    from models.ml_model import PricePredictionModel
    from models.train_and_backtest import ModelTrainerAndBacktester
    from strategies.predictive_trading_strategy import PredictiveTradingStrategy
    from risk_management.risk_manager import RiskManager


class ComprehensiveTradingSystem:
    """综合期货交易系统"""
    
    def __init__(self):
        # 初始化引擎
        self.event_engine = EventEngine()
        self.main_engine = MainEngine(self.event_engine)
        
        # 添加CTP网关
        self.main_engine.add_gateway(CtpGateway)
        
        # 添加CTA策略应用（关键步骤 - 必须在连接CTP前完成）
        self.main_engine.add_app(CtaStrategyApp)
        
        # 获取CTA策略引擎实例
        self.cta_engine = self.main_engine.get_engine("cta_strategy")
        
        # 初始化行情服务
        self.market_service = MarketDataService(self.main_engine, self.event_engine)
        
        # 初始化数据处理器
        self.data_processor = DataProcessor()
        
        # 初始化预测模型
        self.model = None
        self.window_size = 60
        self.feature_count = 10
        
        # 初始化风险管理器
        self.risk_manager = DailyDrawdownRisk(max_drawdown=0.05)  # 5%最大回撤
        
        # 当前交易状态
        self.is_trading_active = False
        self.active_contracts = ["rb2605", "cu2605", "ni2605"]  # 支持的合约列表
        
        # 账户和资金管理
        self.account_manager = None
        self.initial_capital = 1000000  # 初始资金
        self.current_capital = self.initial_capital
        
        # 注册信号处理器，用于优雅退出
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # 存储价格历史
        self.price_history = {}
        for contract in self.active_contracts:
            self.price_history[contract] = []
        
        self.max_history_len = 100  # 最大历史数据长度
        
        # 从配置文件加载CTP设置
        self.ctp_setting = self._load_ctp_setting()
        
    def _load_ctp_setting(self):
        """从配置文件加载CTP设置"""
        import json
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
    
    def signal_handler(self, signum, frame):
        """信号处理，用于优雅退出"""
        print(f"\n接收到信号 {signum}，正在安全退出...")
        self.shutdown()
        sys.exit(0)
    
    def is_trading_time(self):
        """检查当前是否在交易时间内"""
        now = datetime.now().time()
        
        # 定义交易时间段 (模拟期货交易时间)
        trading_times = [
            # 白天盘
            (datetime.strptime("09:00", "%H:%M").time(), datetime.strptime("10:15", "%H:%M").time()),
            (datetime.strptime("10:30", "%H:%M").time(), datetime.strptime("11:30", "%H:%M").time()),
            (datetime.strptime("13:30", "%H:%M").time(), datetime.strptime("15:00", "%H:%M").time()),
            # 夜盘
            (datetime.strptime("21:00", "%H:%M").time(), datetime.strptime("23:59", "%H:%M").time()),
            (datetime.strptime("00:00", "%H:%M").time(), datetime.strptime("02:30", "%H:%M").time()),
        ]
        
        # 检查当前时间是否在任一交易时间段内
        for start, end in trading_times:
            if start <= end:
                # 同一天的时间段
                if start <= now <= end:
                    return True
            else:
                # 跨天的时间段 (如 23:59 - 02:30)
                if now >= start or now <= end:
                    return True
                    
        return False
    
    def init_model(self):
        """初始化模型"""
        print("正在初始化预测模型...")
        
        model_path = os.path.join("models", f"SHFE_{self.active_contracts[0]}_prediction_model.keras")
        
        if os.path.exists(model_path):
            try:
                from tensorflow.keras.models import load_model
                self.model = load_model(model_path)
                print(f"✅ 模型加载成功: {model_path}")
            except Exception as e:
                print(f"❌ 模型加载失败: {e}")
                self.model = None
        else:
            print(f"⚠️  模型文件不存在: {model_path}, 将在需要时训练新模型")
    
    def connect_ctp(self):
        """连接到CTP"""
        if not self.ctp_setting:
            print("❌ 未找到有效的CTP配置，跳过连接")
            return False
            
        try:
            print("正在连接到CTP网关...")
            login_result = self.main_engine.connect(self.ctp_setting, "CTP")
            print("✅ CTP网关连接请求已提交")
            
            # 等待连接建立
            for i in range(20):  # 增加等待时间
                time.sleep(1)
                print(".", end="", flush=True)
            
            print("\nCTP连接过程完成")
            
            # 验证是否成功连接
            # 获取账户信息验证连接状态
            accounts = self.main_engine.get_all_accounts()
            if len(accounts) > 0:
                print("✅ CTP连接成功")
                return True
            else:
                print("⚠️  CTP连接可能存在问题，未获取到账户信息")
                return False
                
        except Exception as e:
            print(f"❌ CTP连接失败: {e}")
            return False
    
    def load_and_run_strategy(self, symbol):
        """加载并运行交易策略"""
        if not self.ctp_setting:
            print("❌ 未找到有效的CTP配置，跳过策略执行")
            return False
            
        try:
            # 确保策略引擎已就绪
            if not self.cta_engine:
                print("❌ CTA策略引擎未就绪")
                return False
            
            print(f"正在为合约 {symbol} 加载和运行策略...")
            
            # 获取合约详细信息
            contract = self.main_engine.get_contract(f"{symbol}.SHFE")
            if not contract:
                print(f"❌ 无法获取合约信息: {symbol}")
                return False
            
            # 添加策略实例
            strategy_setting = {
                "vt_symbol": f"{symbol}.SHFE",
                " classname": "PredictiveTradingStrategy",
                "prediction_threshold": 0.005,
                "fixed_size": 1,
                "trailing_percent": 0.8
            }
            
            # 使用唯一策略名称
            strategy_name = f"predictive_strategy_{symbol}_{int(time.time())}"
            
            # 添加策略
            try:
                self.cta_engine.add_strategy(
                    class_=PredictiveTradingStrategy,
                    strategy_name=strategy_name,
                    vt_symbol=f"{symbol}.SHFE",
                    setting={
                        "prediction_threshold": 0.005,
                        "fixed_size": 1,
                        "trailing_percent": 0.8
                    }
                )
                
                # 启动策略
                self.cta_engine.start_strategy(strategy_name)
                print(f"✅ 策略 {strategy_name} 已启动")
                
            except Exception as e:
                print(f"❌ 添加策略失败: {e}")
                import traceback
                traceback.print_exc()
                
        except Exception as e:
            print(f"❌ 运行策略时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def train_models_from_data_directory(self):
        """从data目录训练模型"""
        print("正在从data目录训练模型...")
        
        # 检查data目录是否存在
        if not os.path.exists("data"):
            print("❌ data目录不存在，跳过模型训练")
            return
        
        # 遍历data目录下的CSV文件
        import glob
        csv_files = glob.glob("data/*.csv")
        
        if not csv_files:
            print("❌ 未找到CSV数据文件，跳过模型训练")
            return
        
        print(f"找到 {len(csv_files)} 个数据文件")
        
        for csv_file in csv_files:
            print(f"正在处理 {csv_file}...")
            
            try:
                # 从文件名提取合约代码
                import re
                match = re.search(r'([a-zA-Z]+)\d+', os.path.basename(csv_file))
                if match:
                    contract_code = match.group(1)
                else:
                    print(f"⚠️  无法从文件名 {csv_file} 提取合约代码，跳过")
                    continue
                
                # 加载数据
                data = pd.read_csv(csv_file)
                
                # 确保数据有足够的列
                required_columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
                if not all(col in data.columns for col in required_columns):
                    print(f"⚠️  数据文件 {csv_file} 缺少必要列，跳过")
                    continue
                
                # 设置日期时间为索引
                data['datetime'] = pd.to_datetime(data['datetime'])
                data.set_index('datetime', inplace=True)
                
                # 初始化并训练模型
                model = PricePredictionModel(model_type='lstm', window_size=60)
                
                # 准备训练数据
                processed_data = self.data_processor.process(data)
                
                if processed_data is not None and len(processed_data) > 100:  # 确保有足够的数据
                    print(f"开始训练 {contract_code} 的预测模型...")
                    model.train(processed_data, epochs=50)  # 减少训练轮次以加快速度
                    
                    # 保存模型
                    model_path = os.path.join("models", f"SHFE_{contract_code}_prediction_model.keras")
                    model.save(model_path)
                    print(f"✅ 模型已保存至 {model_path}")
                else:
                    print(f"⚠️  数据不足，跳过 {contract_code} 的模型训练")
                    
            except Exception as e:
                print(f"❌ 处理文件 {csv_file} 时出错: {e}")
                import traceback
                traceback.print_exc()
    
    def shutdown(self):
        """关闭系统"""
        print("正在关闭综合交易系统...")
        
        # 关闭CTA策略引擎
        if self.cta_engine:
            try:
                # 停止所有策略
                running_strategies = self.cta_engine.get_all_strategy_status()
                for strategy_name in running_strategies.keys():
                    self.cta_engine.stop_strategy(strategy_name)
            except Exception as e:
                print(f"停止策略时出错: {e}")
        
        # 关闭主引擎
        try:
            self.main_engine.close()
            print("系统已安全退出")
        except Exception as e:
            print(f"关闭系统时出错: {e}")


def main():
    """主函数"""
    print("期货散户交易系统 - 完整流程")
    print("=" * 50)
    
    # 创建综合交易系统
    trading_system = ComprehensiveTradingSystem()
    
    # 运行完整流程
    trading_system.run_full_process()


if __name__ == "__main__":
    main()