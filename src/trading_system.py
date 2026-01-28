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
    """综合交易系统"""
    
    def __init__(self):
        # 初始化引擎
        self.event_engine = EventEngine()
        self.main_engine = MainEngine(self.event_engine)
        
        # 添加CTP网关
        self.main_engine.add_gateway(CtpGateway)
        
        # 添加CTA策略应用
        self.main_engine.add_app(CtaStrategyApp)
        
        # 初始化各模块
        self.data_collector = DataCollector(self.main_engine)
        self.data_processor = DataProcessor()
        self.risk_manager = RiskManager()
        self.trainer_backtester = ModelTrainerAndBacktester()
        
        # 存储交易历史
        self.trade_history = []
        
    def train_models_from_data_directory(self, data_dir="data", model_save_dir="models"):
        """根据data目录下的历史数据训练模型"""
        print("开始从data目录训练模型...")
        
        # 获取data目录下的所有子目录（代表不同的合约数据）
        for item in os.listdir(data_dir):
            item_path = os.path.join(data_dir, item)
            
            if os.path.isdir(item_path):
                # 尝试提取合约代码
                # 例如: rb_1min_2026_01_01_2026_01_26
                if "rb_" in item:
                    symbol = "rb"  # 螺纹钢
                    contract_pattern = "SHFE.rb*"  # 根据实际数据格式调整
                elif "沪铜" in item:
                    symbol = "cu"  # 沪铜
                    contract_pattern = "SHFE.cu*"
                elif "沪镍" in item:
                    symbol = "ni"  # 沪镍
                    contract_pattern = "SHFE.ni*"
                else:
                    continue  # 跳过不支持的合约
                
                print(f"正在训练 {symbol} 合约的模型...")
                
                try:
                    # 训练模型
                    model, history, model_path = self.trainer_backtester.train_model(
                        symbol=symbol,
                        contract_dir=item_path,
                        contract_pattern=contract_pattern.split('*')[0],  # 去掉通配符
                        model_type='lstm'
                    )
                    
                    print(f"{symbol} 模型训练完成，保存至: {model_path}")
                except Exception as e:
                    print(f"训练 {symbol} 模型时出错: {e}")
                    continue
    
    def connect_ctp(self, config_path="settings/simnow_setting.json"):
        """连接CTP"""
        print("正在连接CTP...")
        
        # 获取项目根目录，确保使用绝对路径
        current_dir = os.path.dirname(os.path.abspath(__file__))  # src目录
        project_root = os.path.dirname(current_dir)  # 项目根目录
        full_config_path = os.path.join(project_root, config_path)
        
        # 添加调试信息
        print(f"检查配置文件路径: {full_config_path}")
        print(f"当前工作目录: {os.getcwd()}")
        print(f"项目根目录: {project_root}")
        print(f"配置文件是否存在: {os.path.exists(full_config_path)}")
        
        if not os.path.exists(full_config_path):
            print(f"配置文件不存在: {full_config_path}")
            print("提示: 请先创建配置文件，配置SimNow或实盘账户信息")
            return False
            
        try:
            with open(full_config_path, 'r', encoding='utf-8') as f:
                setting = json.load(f)
                
            # 检查必要字段是否存在
            required_fields = ['用户名', '密码', '经纪商代码', '交易服务器', '行情服务器']
            missing_fields = []
            
            for field in required_fields:
                value = setting.get(field)
                # 检查字段是否为空或包含占位符文本
                if not value or not str(value).strip() or '请在此处填写' in str(value) or '您的' in str(value):
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"配置文件缺少必要字段或字段值未填写: {missing_fields}")
                print("提示: 请填写完整的账户信息")
                return False
            
            self.main_engine.connect(setting, "CTP")
            print("CTP连接请求已发送")
            
            # 等待连接结果
            import time
            max_wait_time = 10  # 减少等待时间
            connected = False
            
            for i in range(max_wait_time):
                time.sleep(1)
                print(f"等待连接结果... {i+1}/{max_wait_time}")
                
                # 尝试获取合约信息判断连接状态
                try:
                    contracts = self.main_engine.get_all_contracts()
                    if len(contracts) > 0:
                        print(f"✅ 行情连接成功！已获取到 {len(contracts)} 个合约信息")
                        # 注意：这通常只代表行情服务器连接正常，交易功能需进一步验证
                        connected = True
                        break
                except Exception:
                    pass
            
            if not connected:
                print("⚠️ CTP连接超时")
                print("提示: 请检查SimNow账户配置、网络连接，并确认交易/行情服务器地址是否正确")
                
            return connected
        except Exception as e:
            print(f"连接CTP时出错: {e}")
            return False
    
    def load_and_run_strategy(self, symbol, model_path=None):
        """加载并运行预测交易策略"""
        print(f"正在为 {symbol} 加载并运行交易策略...")
        
        # 构造合约符号
        if symbol == "rb":
            vt_symbol = "rb2602.SHFE"  # 螺纹钢主力合约
        elif symbol == "cu":
            vt_symbol = "cu2602.SHFE"  # 沪铜主力合约
        elif symbol == "ni":
            vt_symbol = "ni2602.SHFE"  # 沪镍主力合约
        else:
            print(f"不支持的合约符号: {symbol}")
            return False
        
        # 获取CTA策略引擎
        cta_engine = self.main_engine.get_engine("CtaStrategy")
        
        # 策略名称
        strategy_name = f"SimpleTestStrategy_{vt_symbol.replace('.', '_')}"
        
        # 策略设置
        setting = {
            "fixed_size": 1
        }
        
        try:
            # 先订阅行情，确保合约存在
            from vnpy.trader.object import SubscribeRequest
            from vnpy.trader.constant import Exchange
            
            exchange_map = {
                "SHFE": Exchange.SHFE,
                "DCE": Exchange.DCE,
                "CZCE": Exchange.CZCE,
                "CFFEX": Exchange.CFFEX,
                "INE": Exchange.INE
            }
            
            symbol_part, exchange_part = vt_symbol.split('.')
            exchange = exchange_map.get(exchange_part, Exchange.SHFE)
            
            req = SubscribeRequest(
                symbol=symbol_part,
                exchange=exchange
            )
            
            self.main_engine.subscribe(req, "CTP")
            print(f"已订阅 {vt_symbol} 行情")
            
            print(f"尝试添加策略类 {SimpleTestStrategy.__name__} 到CTA引擎...")
            
            # 添加策略
            cta_engine.add_strategy(
                SimpleTestStrategy,  # 使用简单测试策略
                strategy_name,       # 策略名称
                vt_symbol,           # 合约
                setting              # 设置
            )
            
            print(f"策略 {strategy_name} 添加成功")
            
            # 异步初始化策略（不等待完成）
            print(f"开始异步初始化策略 {strategy_name}...")
            cta_engine.init_strategy(strategy_name)
            
            # 不等待初始化完成，直接返回成功
            print(f"策略 {strategy_name} 已提交初始化请求，将在后台完成")
            print(f"策略 {strategy_name} 已添加并订阅 {vt_symbol}")
            return True
        except Exception as e:
            import traceback
            print(f"加载和运行策略时出错: {e}")
            print(f"详细错误信息: {traceback.format_exc()}")
            return False
    
    def calculate_performance(self):
        """计算收益率等绩效指标"""
        print("正在计算绩效指标...")
        
        # 获取账户信息
        accounts = self.main_engine.get_all_accounts()
        positions = self.main_engine.get_all_positions()
        trades = self.main_engine.get_all_trades()
        
        print(f"账户数量: {len(accounts)}")
        print(f"持仓数量: {len(positions)}")
        print(f"成交数量: {len(trades)}")
        
        if trades:
            # 计算总盈亏
            total_pnl = sum(trade.turnover * trade.direction.value for trade in trades)
            print(f"总盈亏: {total_pnl}")
        
        # TODO: 添加更详细的绩效分析
        print("绩效计算完成")
    
    def run_full_process(self):
        """运行完整流程"""
        print("开始运行完整交易流程...")
        
        # 1. 从data目录训练模型
        print("\n1. 训练模型...")
        self.train_models_from_data_directory()
        
        # 2. 连接CTP
        print("\n2. 连接CTP...")
        ctp_connected = self.connect_ctp()
        
        if ctp_connected:
            # 3. 加载并运行策略
            print("\n3. 加载并运行交易策略...")
            symbols = ["rb", "cu", "ni"]  # 支持的合约
            for symbol in symbols:
                self.load_and_run_strategy(symbol)
        else:
            print("\n3. CTP连接失败，跳过策略执行，系统将继续提供回测等功能...")
        
        # 4. 提供其他功能
        print("\n4. 系统其他功能...")
        print("系统已准备好，可执行以下操作:")
        print("- 模型训练和回测")
        print("- 历史数据分析")
        print("- 风险管理计算")
        
        if ctp_connected:
            print("- 实时交易执行")
            print("- 行情监控")
        
        print("\n系统运行完成。")
        
        if not ctp_connected:
            print("\n注意: 系统检测到未配置真实交易账户，仅执行了模型训练等功能。")
            print("如需进行实盘或仿真交易，请按以下步骤操作：")
            print("1. 访问 http://www.simnow.com.cn 注册SimNow仿真账户")
            print("2. 在 settings/simnow_setting.json 中填写您的账户信息")
            print("3. 重新运行程序")
        
        # 关闭所有引擎
        self.main_engine.close()


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