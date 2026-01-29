import os
import sys
import json
import time
import signal
import random
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import create_qapp
from vnpy_ctp import CtpGateway
from vnpy.trader.constant import Exchange, Direction, Offset, OrderType, Status
from vnpy.trader.object import OrderRequest, TickData, AccountData, PositionData, SubscribeRequest
from vnpy_ctastrategy import CtaStrategyApp
from vnpy_ctastrategy.base import EVENT_CTA_LOG
from src.market_data.market_data_service import MarketDataService
from src.models.ml_model import PricePredictionModel
from src.risk_management.risk_manager import RiskManager
from src.trading.contract_specs import get_contract_spec
from src.account.account import AccountManager, PositionDirection  # 导入账户管理器和持仓方向枚举
from src.strategies.hybrid_trend_scalp_strategy import HybridTrendScalpStrategy  # 导入新策略

# 导入用于训练的必要库
class SmartAutoTrading:
    """智能自动交易系统"""
    
    def __init__(self):
        # 初始化引擎
        self.event_engine = EventEngine()
        self.main_engine = MainEngine(self.event_engine)
        
        # 添加CTP网关
        self.main_engine.add_gateway(CtpGateway)
        
        # 添加CTA策略应用（关键步骤 - 必须在连接CTP前完成）
        self.main_engine.add_app(CtaStrategyApp)
        # 获取CTA策略引擎实例
        self.cta_engine = self.main_engine.get_engine("CtaStrategy")
        
        # 初始化行情服务
        self.market_service = MarketDataService(self.main_engine, self.event_engine)
        
        # 初始化预测模型
        self.model = None
        self.window_size = 60
        self.feature_count = 10
        
        # 初始化风险管理器
        self.risk_manager = RiskManager(max_pos=5, max_daily_loss=10000)
        
        # 当前交易状态
        self.is_trading_active = False
        self.contract_to_trade = "rb2605"  # 合约代码
        self.exchange = "SHFE"  # 上海期货交易所
        self.current_position = 0  # 持仓数量
        self.current_position_avg_price = 0  # 持仓均价
        self.account_balance = 0  # 账户余额
        self.daily_pnl = 0  # 当日盈亏
        self.last_price = 0  # 最新价格
        
        # 预测相关参数
        self.prediction_threshold = 0.005  # 预测阈值，当预测涨跌幅超过此值时考虑交易
        self.price_history = []
        self.max_history_len = 200  # 最大历史数据长度
        self.prediction_value = 0  # 预测值
        self.prediction_datetime = None  # 预测时间
        
        # 风险管理参数
        self.max_position_size = 10  # 最大持仓量
        self.max_loss_per_trade = 0.02  # 每笔交易最大亏损比例
        self.stop_loss_pct = 0.03  # 止损百分比
        self.take_profit_pct = 0.06  # 止盈百分比
        
        # 注册信号处理器，用于优雅退出
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # 初始化持仓信息
        self.current_position = 0
        
        # 初始化订单信息
        self.active_orders = {}  # 存储活跃订单
        self.position_details = {
            'long': {'volume': 0, 'avg_price': 0},
            'short': {'volume': 0, 'avg_price': 0}
        }
        
        # 初始化账户资产信息
        self.initial_capital = 100000  # 初始资金
        self.current_capital = self.initial_capital
        self.daily_pnl = 0  # 当日盈亏
        
        # 合约规格信息
        self.contract_spec = get_contract_spec(self.contract_to_trade)
        
        # 最后输出时间
        self.last_output_time = time.time()
        
        # 记录上次账户状态，用于比较是否发生变化
        self.last_account_status = {
            'balance': 0,
            'position': 0,
            'available': 0
        }
        
        # 记录最新行情数据
        self.last_market_data = None
        
        # 控制预测频率
        self.last_prediction_time = 0
        self.prediction_interval = 10  # 每10秒预测一次
        
        # 账户管理器
        self.account_manager = None  # 初始化为空，连接后设置
        
        # 从配置文件加载CTP设置
        self.ctp_setting = self._load_ctp_setting()

    def identify_target_product_from_data(self):
        """从data目录中识别要交易的目标产品"""
        data_dir = "data"
        if not os.path.exists(data_dir):
            print(f"⚠️ {data_dir} 目录不存在，使用默认产品 rb")
            return "rb"  # 默认使用螺纹钢
        
        # 获取data目录中的所有文件和子目录
        items = os.listdir(data_dir)
        
        # 查找包含商品代码的目录或文件
        for item in items:
            # 示例：寻找包含螺纹钢数据的目录，如 "rb_1min_2026_01_01_2026_01_26"
            if os.path.isdir(os.path.join(data_dir, item)) and '_' in item:
                product_code = item.split('_')[0].lower()
                print(f"✅ 从数据目录识别出目标产品: {product_code}")
                return product_code
            # 或者查找zip文件
            elif item.endswith('.zip'):
                product_code = item.split('_')[0].lower()
                print(f"✅ 从数据文件识别出目标产品: {product_code}")
                return product_code
        
        print(f"⚠️ 无法从 {data_dir} 识别目标产品，使用默认产品 rb")
        return "rb"

    def find_contract_by_product(self, all_contracts, product_code):
        """根据产品代码查找对应的合约"""
        # 首先尝试精确匹配产品代码
        for contract in all_contracts:
            if contract.symbol.lower().startswith(product_code):
                return contract
        
        # 如果找不到，打印一些可用的合约供参考
        print(f"⚠️ 未找到产品代码为 '{product_code}' 的合约，以下是部分可用合约:")
        for i, contract in enumerate(all_contracts[:10]):  # 只显示前10个
            print(f"   - {contract.symbol} @ {contract.exchange}")
        
        return None

    def check_market_data_availability(self, product_code):
        """检测data目录中的期货合约是否能获取到行情"""
        print(f"🔍 检测 {product_code} 合约的行情可用性...")
        
        # 获取所有合约信息
        all_contracts = self.main_engine.get_all_contracts()
        
        # 根据产品代码筛选相关合约
        relevant_contracts = [c for c in all_contracts if c.symbol.lower().startswith(product_code)]
        
        if not relevant_contracts:
            print(f"❌ 未找到 {product_code} 相关的合约")
            # 尝试一些常见的期货品种作为备选
            alternative_products = ['cu', 'al', 'zn', 'au', 'ag', 'fu', 'ru', 'pb', 'ni', 'sn']
            print("🔄 尝试常见期货品种作为备选...")
            for alt_product in alternative_products:
                alt_contracts = [c for c in all_contracts if c.symbol.lower().startswith(alt_product)]
                if alt_contracts:
                    print(f"✅ 找到 {alt_product} 相关合约，使用该品种")
                    relevant_contracts = alt_contracts
                    product_code = alt_product
                    break
        
        if not relevant_contracts:
            print("❌ 没有任何可用的合约，返回None")
            return None
        
        print(f"📊 找到 {len(relevant_contracts)} 个 {product_code} 相关合约")
        
        # 按合约到期时间排序（通常是近月合约优先）
        sorted_contracts = sorted(relevant_contracts, key=lambda x: x.symbol)
        
        # 检测行情可用性
        for i, contract in enumerate(sorted_contracts):
            print(f"   检测合约: {contract.vt_symbol}")
            
            # 订阅合约行情
            try:
                # 使用SubscribeRequest来订阅
                from vnpy.trader.object import SubscribeRequest
                req = SubscribeRequest(
                    symbol=contract.symbol,
                    exchange=contract.exchange
                )
                self.main_engine.subscribe(req, contract.gateway_name)
                
                # 等待一小段时间，看是否能收到行情
                print(f"   🔄 订阅 {contract.vt_symbol} 行情...")
                
                # 检查是否有行情数据
                initial_time = time.time()
                timeout = 5  # 5秒超时
                
                while time.time() - initial_time < timeout:
                    # 检查是否已经有tick数据
                    tick = self.main_engine.get_tick(contract.vt_symbol)
                    if tick and tick.datetime and (time.time() - tick.datetime.timestamp()) < 60:
                        print(f"✅ {contract.vt_symbol} 行情可用!")
                        return contract  # 返回第一个可用的合约
                    time.sleep(0.5)  # 短暂等待
                
                print(f"   ⏳ {contract.vt_symbol} 暂无行情数据")
                
            except Exception as e:
                print(f"   ❌ 订阅 {contract.vt_symbol} 时出错: {e}")
        
        print(f"⚠️ 未找到 {product_code} 产品的可用行情合约")
        return None

    def connect_to_broker(self):
        """连接到期货公司"""
        try:
            print("尝试连接到期货公司...")
            
            # 使用CTP网关连接
            self.main_engine.connect(self.ctp_setting, "CTP")
            print("✅ 连接成功!")
            
            # 等待连接建立
            time.sleep(3)
            
            # 获取账户信息
            account_id = self.ctp_setting.get("用户名", "unknown")
            print("✅ 连接完成")
            
            # 等待合约信息加载
            print("⏳ 等待合约信息加载...")
            time.sleep(10)  # 增加等待时间以便合约信息加载
            
            # 获取并保存所有合约信息
            print("🔄 获取所有合约信息...")
            all_contracts = self.main_engine.get_all_contracts()
            
            # 保存合约信息到文件
            self.save_contracts_to_file(all_contracts)
            
            # 从data目录中确定要交易的商品类型
            target_product = self.identify_target_product_from_data()
            
            # 检测该产品的合约是否能获取到行情
            target_contract = self.check_market_data_availability(target_product)
            
            if target_contract:
                vt_symbol = target_contract.vt_symbol
                print(f"✅ 成功获取合约行情: {target_contract.symbol} @ {target_contract.exchange}")
            else:
                print(f"❌ 未能获取 {target_product} 合约行情，尝试查找其他合约")
                # 如果无法获取行情，尝试使用第一个可用的合约
                target_contract = self.find_contract_by_product(all_contracts, target_product)
                
                if target_contract:
                    vt_symbol = target_contract.vt_symbol
                    print(f"✅ 使用合约: {target_contract.symbol} @ {target_contract.exchange}")
                else:
                    print("⚠️ 没有找到任何合约，使用默认值继续运行")
                    # 如果还是找不到，使用第一个SHFE合约
                    shfe_contracts = [c for c in all_contracts if c.exchange.value == 'SHFE']
                    if shfe_contracts:
                        target_contract = shfe_contracts[0]
                        vt_symbol = target_contract.vt_symbol
                        print(f"✅ 使用第一个SHFE合约: {target_contract.symbol} @ {target_contract.exchange}")
                    else:
                        print("❌ 无法找到任何SHFE合约，使用默认值")
                        return False
            
            # 设置要交易的合约
            self.contract_to_trade = target_contract.symbol
            self.exchange = target_contract.exchange.value
            
            print(f"🔄 开始订阅合约行情: {vt_symbol}")
            
            # 订阅行情
            try:
                from vnpy.trader.object import SubscribeRequest
                
                # 使用SubscribeRequest来订阅
                req = SubscribeRequest(
                    symbol=target_contract.symbol,
                    exchange=target_contract.exchange
                )
                
                # 订阅行情
                self.main_engine.subscribe(req, target_contract.gateway_name)
                
                # 添加事件监听器来捕获tick数据
                # 在vnpy中，EVENT_TICK通常在 trader.constants.EVENT_TICK 中
                from vnpy.trader.event import EVENT_TICK
                self.event_engine.register(EVENT_TICK, self.on_tick)
                
                print(f"✅ 成功订阅合约行情: {vt_symbol}")
                print(f"✅ 已注册tick事件监听器")
            except ImportError:
                # 如果EVENT_TICK导入失败，尝试另一种方式
                try:
                    from vnpy.event import EVENT_TIMER
                    # 注册一个定时器事件来定期获取tick数据
                    self.event_engine.register(EVENT_TIMER, self.fetch_tick_data)
                    print(f"✅ 成功订阅合约行情: {vt_symbol}")
                    print(f"⚠️ 无法注册tick事件监听器，将使用定时器获取数据")
                except ImportError:
                    print(f"✅ 成功订阅合约行情: {vt_symbol}")
                    print(f"⚠️ 无法注册任何数据获取方式，请手动检查数据更新")
            except Exception as e:
                print(f"❌ 订阅合约行情失败: {e}")
                import traceback
                traceback.print_exc()
                return False
            
            # 初始化账户管理器
            self.account_manager = AccountManager(
                account_id=account_id, 
                initial_capital=self.initial_capital
            )
            
            # 初始化预测模型 - 检查是否存在预训练模型，如果没有则训练新模型
            print("🔍 初始化预测模型...")
            self.initialize_prediction_model()
            
            # 添加混合AI趋势+剥头皮策略
            strategy_setting = {
                "take_profit_tick": 2,
                "stop_loss_tick": 3,
                "fixed_size": 1,
                "cooldown_seconds": 10,
                "max_trades_per_day": 20,
                "order_imbalance_ratio": 1.5,
                "max_spread_tick": 2,
                "model_prediction_threshold": 0.005,
                "vt_symbol": vt_symbol  # 添加vt_symbol到设置中
            }
            
            # 使用正确的策略名称
            strategy_name = f"hybrid_trend_scalp_{self.contract_to_trade.lower()}"
            
            # 添加策略实例 - 使用正确的方法签名
            # 先注册策略类
            try:
                self.cta_engine.add_strategy_class(HybridTrendScalpStrategy)
            except AttributeError:
                # 如果add_strategy_class不存在，直接添加策略实例
                pass
            
            # 添加策略实例 - 使用正确的方法签名
            # 根据vnpy的API，正确的参数顺序是：class, name, vt_symbol, setting
            self.cta_engine.add_strategy(
                HybridTrendScalpStrategy,
                strategy_name,
                vt_symbol,
                strategy_setting
            )
            
            print(f"✅ 策略 {strategy_name} 已添加到引擎")
            
            # 初始化策略
            self.cta_engine.init_strategy(strategy_name)
            print(f"✅ 策略 {strategy_name} 初始化完成")
            
            # 等待一段时间让策略加载完成
            import time as time_module
            time_module.sleep(1)
            
            # 检查策略是否已成功添加
            if hasattr(self.cta_engine, 'strategies') and strategy_name in self.cta_engine.strategies:
                # 启动策略
                self.cta_engine.start_strategy(strategy_name)
                print(f"🚀 策略 {strategy_name} 已启动")
            else:
                print(f"⚠️ 策略 {strategy_name} 未能成功加载到引擎中")
                print(f"   可用策略: {list(self.cta_engine.strategies.keys()) if hasattr(self.cta_engine, 'strategies') else 'N/A'}")
            
            # 显示初始账户信息
            print("账户信息初始化完成:")
            self.display_account_info()
            
            return True
        except Exception as e:
            print(f"❌ 连接期货公司失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def train_model_for_contract(self, symbol):
        """为指定合约训练模型"""
        print(f"🚀 开始为 {symbol} 训练模型...")
        
        try:
            # 创建FuturesTradingEnv环境
            env = FuturesTradingEnv(symbol=symbol)
            
            # 创建PPO模型
            model = PPO('MlpPolicy', env, verbose=1, tensorboard_log="./ppo_tensorboard_{}".format(symbol))
            
            # 训练模型
            print(f"📊 正在训练 {symbol} 模型...")
            model.learn(total_timesteps=10000)  # 可根据需要调整训练步数
            
            # 确保模型目录存在
            model_dir = "models"
            os.makedirs(model_dir, exist_ok=True)
            
            # 保存模型
            model_path = f"{model_dir}/{symbol}_ppo_model.zip"
            model.save(model_path)
            print(f"💾 模型已保存至: {model_path}")
            
        except Exception as e:
            print(f"❌ 训练模型时出错: {e}")
            import traceback
            traceback.print_exc()

    def load_and_trade(self, symbol, model_path):
        """加载模型并开始交易"""
        print(f"🎯 加载模型并开始 {symbol} 交易...")
        
        try:
            # 加载预训练模型
            model = PPO.load(model_path)
            print(f"✅ 模型加载成功: {model_path}")
            
            # 创建交易环境
            env = FuturesTradingEnv(symbol=symbol)
            
            # 开始交易
            obs = env.reset()
            for i in range(1000):  # 可根据需要调整交易步数
                action, _states = model.predict(obs)
                obs, rewards, done, info = env.step(action)
                
                if done:
                    obs = env.reset()
                    
                # 可在此处添加实际交易逻辑
                
                if i % 100 == 0:
                    print(f"📊 已执行 {i} 步交易")
                    
        except Exception as e:
            print(f"❌ 加载模型或交易时出错: {e}")
            import traceback
            traceback.print_exc()

    def save_contracts_to_file(self, contracts):
        """保存合约信息到文件，只保留最新的文件"""
        import json
        from datetime import datetime
        import os
        from pathlib import Path
        
        try:
            # 准备合约数据
            contract_data = []
            for contract in contracts:
                # 获取合约的属性，如果不存在则设为默认值
                contract_info = {
                    "symbol": getattr(contract, 'symbol', ''),
                    "exchange": getattr(contract, 'exchange', '').value if hasattr(contract, 'exchange') and hasattr(getattr(contract, 'exchange'), 'value') else '',
                    "vt_symbol": getattr(contract, 'vt_symbol', ''),
                    "name": getattr(contract, 'name', ''),
                    "size": getattr(contract, 'size', 0),
                    "pricetick": getattr(contract, 'pricetick', 0.0),
                    "gateway_name": getattr(contract, 'gateway_name', '')
                }
                
                # 尝试获取 product_class 属性
                if hasattr(contract, 'product_class'):
                    contract_info["product_class"] = contract.product_class.value if contract.product_class else ""
                else:
                    contract_info["product_class"] = ""
                    
                contract_data.append(contract_info)
            
            # 使用固定文件名，覆盖之前的文件
            json_filename = f"contracts_latest.json"
            txt_filename = f"contracts_latest.txt"
            
            # 确保使用项目目录下的data文件夹
            project_root = Path(__file__).resolve().parent
            data_folder = project_root / "data"
            
            # 确保data目录存在
            data_folder.mkdir(parents=True, exist_ok=True)
            
            # 删除旧的合约文件（如果有）
            old_json_files = list(data_folder.glob("contracts_*.json"))
            old_txt_files = list(data_folder.glob("contracts_*.txt"))
            
            for old_file in old_json_files + old_txt_files:
                if old_file.name != json_filename and old_file.name != txt_filename:
                    try:
                        old_file.unlink()  # 删除旧文件
                        print(f"🗑️ 删除旧合约文件: {old_file.name}")
                    except Exception as e:
                        print(f"❌ 删除旧文件失败 {old_file.name}: {e}")
            
            # JSON文件路径
            json_filepath = data_folder / json_filename
            
            # 保存到JSON文件
            with open(json_filepath, 'w', encoding='utf-8') as f:
                json.dump(contract_data, f, ensure_ascii=False, indent=2)
            
            print(f"📋 合约信息已保存到: {json_filepath}")
            print(f"📊 共保存了 {len(contract_data)} 个合约信息")
            
            # TXT文件路径
            txt_filepath = data_folder / txt_filename
            
            with open(txt_filepath, 'w', encoding='utf-8') as f:
                f.write(f"Futures Contracts List - Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*80 + "\n")
                for i, contract in enumerate(contracts, 1):
                    exchange_val = getattr(contract, 'exchange', '')
                    exchange_str = exchange_val.value if hasattr(exchange_val, 'value') else str(exchange_val)
                    f.write(f"{i:3d}. {getattr(contract, 'vt_symbol', ''):<20} {getattr(contract, 'name', ''):<30} Exchange: {exchange_str}\n")
                    if i % 50 == 0:  # 每50个合约换一次行，方便查看
                        f.write("-" * 80 + "\n")
            
            print(f"📋 合约列表已保存到: {txt_filepath}")
            
        except Exception as e:
            print(f"❌ 保存合约信息时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def _load_ctp_setting(self):
        """从配置文件加载CTP设置"""
        import json
        import os
        from pathlib import Path
        
        # 获取当前脚本所在的目录
        script_dir = Path(__file__).parent if '__file__' in globals() else Path.cwd()
        
        # 尝试从多个可能的位置加载配置
        config_paths = [
            script_dir / "settings" / "simnow_setting_one.json",
            script_dir / "settings" / "simnow_setting_two.json",
            script_dir / "settings" / "simnow_setting_template.json",
            script_dir / "settings" / "ctp_setting.json",
            # 也检查绝对路径
            Path("settings/simnow_setting_one.json"),
            Path("settings/simnow_setting_two.json"),
            Path("settings/ctp_setting.json")
        ]
        
        for config_path in config_paths:
            path = Path(config_path)
            if not path.is_absolute():
                path = script_dir / path
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
                    
                    print(f"✅ 成功加载配置文件: {config_path}")
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
        now = datetime.now()
        current_time = now.time()
        current_weekday = now.weekday()  # Monday is 0 and Sunday is 6
        
        # 周末休市 (周六和周日)
        if current_weekday >= 5:  # 5代表周六，6代表周日
            return False
        
        # 定义交易时间段 (根据SimNow平台和中国期货市场实际交易时间)
        trading_times = [
            # 日盘
            (datetime.strptime("09:00", "%H:%M").time(), datetime.strptime("10:15", "%H:%M").time()),
            (datetime.strptime("10:30", "%H:%M").time(), datetime.strptime("11:30", "%H:%M").time()),
            (datetime.strptime("13:30", "%H:%M").time(), datetime.strptime("15:00", "%H:%M").time()),
            # 夜盘 (如适用)
            (datetime.strptime("21:00", "%H:%M").time(), datetime.strptime("23:59", "%H:%M").time()),
            (datetime.strptime("00:00", "%H:%M").time(), datetime.strptime("02:30", "%H:%M").time()),
        ]
        
        # 检查当前时间是否在任意一个交易时间段内
        for start, end in trading_times:
            if start <= current_time <= end:
                return True
        
        return False

    def calculate_required_margin(self, price, volume):
        """计算所需保证金"""
        contract_size = self.contract_spec['size']
        margin_ratio = self.contract_spec['margin_ratio']
        return price * contract_size * volume * margin_ratio

    def calculate_commission(self, price, volume, direction, offset):
        """计算手续费"""
        commission_open = self.contract_spec['commission_open']
        commission_close = self.contract_spec['commission_close']
        commission_close_today = self.contract_spec['commission_close_today']
        
        # 根据不同类型的手续费计算
        if offset == Offset.OPEN:
            commission_rate = commission_open
        elif direction == Direction.SHORT and offset == Offset.CLOSE_TODAY:
            commission_rate = commission_close_today
        elif offset == Offset.CLOSE_TODAY:
            commission_rate = commission_close_today
        else:
            commission_rate = commission_close
            
        contract_size = self.contract_spec['size']
        
        # 如果手续费是固定金额，则按手数计算；如果是比率，则按价值计算
        if isinstance(commission_rate, (int, float)) and commission_rate > 1:
            # 固定手续费（元/手）
            return commission_rate * volume
        else:
            # 按比率计算
            return price * contract_size * volume * commission_rate

    def calculate_potential_profit(self, entry_price, exit_price, volume, direction):
        """计算潜在利润"""
        contract_size = self.contract_spec['size']
        if direction == Direction.LONG:
            return (exit_price - entry_price) * contract_size * volume
        else:
            return (entry_price - exit_price) * contract_size * volume

    def is_profitable_trade(self, expected_return, entry_price, volume, direction):
        """判断交易是否盈利（扣除手续费和保证金影响）"""
        # 预计退出价格
        expected_exit_price = entry_price * (1 + expected_return) if direction == Direction.LONG \
                              else entry_price * (1 - expected_return)
        
        # 计算潜在利润
        potential_profit = self.calculate_potential_profit(entry_price, expected_exit_price, volume, direction)
        
        # 计算手续费（开仓+平仓）
        open_commission = self.calculate_commission(entry_price, volume, direction, Offset.OPEN)
        close_commission = self.calculate_commission(expected_exit_price, volume, direction, Offset.CLOSE)
        total_commission = open_commission + close_commission
        
        # 计算净收益
        net_profit = potential_profit - total_commission
        
        # 计算保证金要求
        required_margin = self.calculate_required_margin(entry_price, volume)
        
        # 检查是否满足盈利条件（净收益大于手续费的一定比例）
        min_net_profit = total_commission * 0.5  # 净利润至少是手续费的一半
        
        print(f"📊 交易分析: 预期收益率 {expected_return:.2%}, "
              f"潜在利润 {potential_profit:.2f}, "
              f"手续费 {total_commission:.2f}, "
              f"净收益 {net_profit:.2f}, "
              f"所需保证金 {required_margin:.2f}")
              
        return net_profit > min_net_profit and self.current_capital >= required_margin

    def get_model_path(self):
        """获取模型保存路径"""
        import os
        
        # 获取项目根目录的绝对路径
        project_root = os.path.dirname(os.path.abspath(__file__))
        
        # 确保models目录存在
        models_dir = os.path.join(project_root, "models")
        if not os.path.exists(models_dir):
            os.makedirs(models_dir)
            print(f"📁 创建模型目录: {models_dir}")
    
        # 构建模型文件路径 - 修正文件名格式
        model_filename = f"{self.exchange}_{self.contract_to_trade}_prediction_model.keras"
        model_path = os.path.join(models_dir, model_filename)
        
        return model_path

    def initialize_prediction_model(self):
        """初始化预测模型 - 不存在则训练新模型"""
        import os
        
        # 使用统一的方法获取模型路径
        model_path = self.get_model_path()
        
        print(f"🔍 检查模型路径: {model_path}")
        
        if os.path.exists(model_path):
            print(f"✅ 模型文件存在: {model_path}")
            try:
                # 加载现有模型
                self.model = PricePredictionModel()
                self.model.load_model(model_path)
                
                # 确保scaler已正确加载
                scaler_path = model_path.replace('.keras', '_scaler.pkl')
                target_scaler_path = model_path.replace('.keras', '_target_scaler.pkl')
                
                if os.path.exists(scaler_path) and os.path.exists(target_scaler_path):
                    print("✅ Scalers已加载")
                else:
                    print("⚠️ Scalers未找到，使用默认scaler")
                
                print("✅ 预测模型加载成功！")
            except Exception as e:
                print(f"❌ 加载模型时发生错误: {e}")
                print("💡 正在训练新模型...")
                self.train_new_model(model_path)
        else:
            print(f"⚠️ 模型文件不存在: {model_path}")
            print("💡 正在训练新模型...")
            self.train_new_model(model_path)

    def train_new_model(self, model_path):
        """训练新的预测模型
        Args:
            model_path (str): 模型保存路径
        """
        try:
            import tensorflow as tf
            import os
            
            # 配置GPU使用
            self.configure_gpu()
            
            # 确保目录存在
            model_dir = os.path.dirname(model_path)
            if not os.path.exists(model_dir):
                os.makedirs(model_dir)
            
            # 获取项目根目录
            project_root = os.path.dirname(os.path.abspath(__file__))

            # 如果模型文件存在，直接加载并返回
            if os.path.exists(model_path):
                print(f"✅ 发现已训练的模型文件: {model_path}")
                self.model = PricePredictionModel()
                self.model.load_model(model_path)
                print("✅ 已加载现有模型！")
                return
            
            # 导入训练模块
            from src.models.train_and_backtest import ModelTrainerAndBacktester
            
            # 创建训练器实例
            trainer = ModelTrainerAndBacktester()
            
            # 定义合约信息
            symbol = f"{self.exchange}.{self.contract_to_trade[:2]}"

            # 确定数据目录 - 根据合约代码确定合适的数据目录
            if self.contract_to_trade.startswith('rb'):
                contract_dir = os.path.join(project_root, "data", "rb_1min_2026_01_01_2026_01_26")
                contract_pattern = f"{self.exchange}.{self.contract_to_trade}"
            elif self.contract_to_trade.startswith('cu'):
                contract_dir = os.path.join(project_root, "data", "沪铜_1min_2026_01_01_2026_01_26")
                contract_pattern = f"{self.exchange}.{self.contract_to_trade}"
            elif self.contract_to_trade.startswith('ni'):
                contract_dir = os.path.join(project_root, "data", "沪镍_1min_2026_01_01_2026_01_26")
                contract_pattern = f"{self.exchange}.{self.contract_to_trade}"
            else:
                # 默认使用螺纹钢数据
                contract_dir = os.path.join(project_root, "data", "rb_1min_2026_01_01_2026_01_26")
                contract_pattern = f"{self.exchange}.{self.contract_to_trade}"
                
            # 检查目录是否存在，不存在则使用默认模型
            if not os.path.exists(contract_dir):
                print(f"⚠️ 数据目录不存在: {contract_dir}")
                print("💡 使用默认模型...")
                self.model = PricePredictionModel(
                    model_type='lstm',
                    sequence_length=60,
                    n_features=22  # 修正为正确的特征数量
                )
                return
            
            print(f"🔄 开始训练 {self.contract_to_trade}.{self.exchange} 的预测模型...")
            
            # 训练模型 - 修正调用方式
            result = trainer.train_model(
                symbol=symbol,
                contract_dir=contract_dir,
                contract_pattern=contract_pattern
            )
            
            if isinstance(result, tuple) and len(result) == 3:
                model, history, trained_model_path = result
                self.model = model
                
                # 使用传入的model_path保存模型
                self.model.save_model(model_path)
                print(f"✅ {self.contract_to_trade}.{self.exchange} 的预测模型训练完成并保存至: {model_path}")
            else:
                print(f"⚠️ {self.contract_to_trade}.{self.exchange} 的预测模型训练失败，使用默认模型")
                self.model = PricePredictionModel(
                    model_type='lstm',
                    sequence_length=60,
                    n_features=22
                )
                # 即使使用默认模型也尝试保存
                try:
                    self.model.save_model(model_path)
                    print(f"✅ 默认模型已保存至: {model_path}")
                except:
                    print(f"❌ 无法保存默认模型至: {model_path}")
                
        except Exception as e:
            print(f"⚠️ 训练模型时发生错误: {e}")
            import traceback
            traceback.print_exc()
            print("💡 使用默认模型...")
            self.model = PricePredictionModel(
                model_type='lstm',
                sequence_length=60,
                n_features=22
            )

    def check_risk_controls(self):
        """检查风险控制"""
        # 检查是否允许交易
        if not self.risk_manager.trading_enabled:
            return False
        
        # 检查当前持仓是否达到上限
        if abs(self.current_position) >= self.risk_manager.max_pos:
            return False
            
        # 检查当日盈亏是否超过限制
        if self.daily_pnl < -self.risk_manager.max_daily_loss:
            self.risk_manager.trading_enabled = False
            return False
            
        return self.risk_manager.trading_enabled
    
    def run_auto_trading_cycle(self, contracts_to_trade):
        """运行自动交易循环"""
        print(f"开始自动交易循环，关注合约: {contracts_to_trade}")
        
        try:
            while self.is_trading_active:
                # 检查是否在交易时间内
                if not self.is_trading_time():
                    print("非交易时间，暂停交易...")
                    time.sleep(60)  # 等待一分钟再检查
                    continue
                
                # 获取最新市场数据
                for contract in contracts_to_trade:
                    # 获取合约的最新价格
                    tick = self.main_engine.get_tick(f"{contract}.{self.exchange}")
                    if tick:
                        # 更新价格历史
                        self.update_price_history(contract, tick.last_price)
                        
                        # 检查是否满足交易条件
                        if self.should_trade(contract, tick.last_price):
                            # 检查风险控制
                            if self.check_risk_controls():
                                # 执行交易
                                self.execute_trade(contract, tick.last_price)
                
                # 每隔一段时间休息
                time.sleep(5)
                
        except KeyboardInterrupt:
            print("\n交易循环被用户中断")
        except Exception as e:
            print(f"自动交易过程中出现错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.shutdown()
    
    def fetch_tick_data(self, event):
        """定时获取tick数据"""
        if hasattr(self, 'contract_to_trade') and hasattr(self, 'exchange'):
            vt_symbol = f"{self.contract_to_trade}.{self.exchange}"
            tick = self.main_engine.get_tick(vt_symbol)
            
            if tick:
                # 更新最新行情数据
                self.last_market_data = tick
                
                # 将价格数据添加到历史记录
                price_data = {
                    'price': tick.last_price,
                    'datetime': tick.datetime,
                    'volume': tick.volume,
                    'ask_price_1': tick.ask_price_1,
                    'bid_price_1': tick.bid_price_1
                }
                
                self.price_history.append(price_data)
                
                # 限制历史数据的最大数量
                if len(self.price_history) > self.max_history_len:
                    self.price_history = self.price_history[-self.max_history_len:]
    
    def on_tick(self, event):
        """处理tick数据"""
        tick = event.data
        if tick:
            # 更新最新行情数据
            self.last_market_data = tick
            
            # 将价格数据添加到历史记录
            price_data = {
                'price': tick.last_price,
                'datetime': tick.datetime,
                'volume': tick.volume,
                'ask_price_1': tick.ask_price_1,
                'bid_price_1': tick.bid_price_1
            }
            
            self.price_history.append(price_data)
            
            # 限制历史数据的最大数量
            if len(self.price_history) > self.max_history_len:
                self.price_history = self.price_history[-self.max_history_len:]
    
    def should_display_account_info(self):
        """判断是否需要显示账户信息"""
        # 如果是首次运行，显示账户信息
        if self.last_account_status['balance'] == 0:
            return True
        
        # 检查账户状态是否发生变化
        if not self.account_manager:
            return False
        
        current_metrics = self.account_manager.get_performance_metrics({})
        return (
            current_metrics['current_balance'] != self.last_account_status['balance'] or
            current_metrics['position_count'] != self.last_account_status['position'] or
            current_metrics['available'] != self.last_account_status['available']
        )
    
    def update_last_account_status(self):
        """更新最后账户状态"""
        if not self.account_manager:
            return
        
        current_metrics = self.account_manager.get_performance_metrics({})
        self.last_account_status['balance'] = current_metrics['current_balance']
        self.last_account_status['position'] = current_metrics['position_count']
        self.last_account_status['available'] = current_metrics['available']

    def display_account_info(self):
        """显示账户信息概览"""
        if not self.account_manager:
            print("⚠️ 账户管理器未初始化")
            return

        # 获取绩效指标
        market_prices = {f"{self.contract_to_trade}.{self.exchange}": self.last_price}
        metrics = self.account_manager.get_performance_metrics(market_prices)
        
        print("\n" + "="*60)
        print("📈 账户信息概览")
        print("="*60)
        print(f"📊 账户ID: {metrics['account_id']}")
        print(f"💰 初始资金: {metrics['initial_capital']:,.2f}")
        print(f"💵 当前余额: {metrics['current_balance']:,.2f}")
        print(f"🏦 账户总价值: {metrics['total_value']:,.2f}")
        print(f"📈 总盈亏: {metrics['total_pnl']:,.2f} ({metrics['return_rate']:+.2f}%)")
        print(f"🔒 保证金: {metrics['margin']:,.2f}")
        print(f"💳 可用资金: {metrics['available']:,.2f}")
        print(f"💸 总手续费: {metrics['commission']:,.2f}")
        print(f"📊 持仓数量: {metrics['position_count']} 个")
        
        if metrics['position_details']:
            print("\n持仓详情:")
            print("-" * 80)
            for pos in metrics['position_details']:
                print(f"  合约: {pos['symbol']:<15} "
                      f"方向: {pos['direction']:<2} "
                      f"数量: {pos['volume']:>3}手 "
                      f"均价: {pos['avg_price']:>8.2f} "
                      f"当前价: {pos['current_price']:>8.2f} "
                      f"盈亏: {pos['pnl']:>8.2f} ({pos['pnl_rate']:+.2f}%)")
        print("="*60 + "\n")

    def display_trade_decision_info(self):
        """显示交易决策信息"""
        # 检查是否满足交易条件
        if len(self.price_history) >= self.window_size and self.model and self.prediction_datetime:
            try:
                # 准备特征数据
                features = self.prepare_features()
                if features is not None:
                    # 使用模型进行预测
                    prediction = self.model.predict(features)
                    if prediction is not None:
                        pred_value = prediction[0] if isinstance(prediction, (list, np.ndarray)) else prediction
                        
                        # 获取最新价格
                        latest_price = self.price_history[-1]['price'] if self.price_history else 0
                        avg_price = sum([p['price'] for p in self.price_history[-10:]]) / min(10, len(self.price_history)) if self.price_history else 0
                        
                        # 检查是否达到交易阈值
                        if abs(pred_value) > self.prediction_threshold:
                            direction_str = "📈做多" if pred_value > 0 else "📉做空"
                            confidence = "高" if abs(pred_value) > self.prediction_threshold * 1.5 else "中"
                            
                            # 检查风险管理条件
                            risk_ok = self.risk_manager.can_trade(self.current_position, latest_price)
                            
                            print(f"💡 交易信号: {self.prediction_datetime.strftime('%H:%M:%S')} | "
                                  f"信号: {direction_str} | "
                                  f"置信度: {confidence} | "
                                  f"最新价: {latest_price:.2f} | "
                                  f"均价: {avg_price:.2f} | "
                                  f"风控检查: {'✅通过' if risk_ok else '❌未通过'}")
                        else:
                            print(f"💤 无交易信号: {self.prediction_datetime.strftime('%H:%M:%S')} | "
                                  f"预测值未达阈值 | "
                                  f"当前预测: {pred_value:.4f} | "
                                  f"阈值: ±{self.prediction_threshold:.4f}")
            except Exception as e:
                print(f"⚠️ 交易决策过程出错: {e}")
        else:
            print(f"💤 等待数据: 需要至少{self.window_size}个数据点进行预测，当前: {len(self.price_history)}")
    
    def run_auto_trading(self):
        """运行自动交易系统的主要流程"""
        try:
            # 连接期货公司
            self.connect_to_broker()
            
            # 检查event_engine是否已经启动，如果没有则启动
            if not self.event_engine._thread.is_alive():
                print("🔄 正在启动自动交易系统...")
                self.event_engine.start()
                print("✅ 事件引擎已启动")
            else:
                print("🔄 事件引擎已在运行...")
            
            print("🚀 自动交易系统已启动，等待交易信号...")
            
            # 保持程序运行
            while True:
                time.sleep(1)  # 每秒检查一次
                
                # 每隔一段时间输出账户信息 - 只有在账户状态发生变化时才显示
                if self.should_display_account_info():
                    self.display_account_info()
                    self.update_last_account_status()
                
                # 显示最新的市场行情
                self.display_market_info()
                
                # 主动获取并更新tick数据
                self.update_tick_data_regularly()
                
                # 显示预测信息
                self.display_prediction_info()
                
                # 显示交易决策信息
                self.display_trade_decision_info()
                
                # 检查是否在交易时间外，如果不是交易时间则退出
                if not self.is_trading_time():
                    print("⚠️ 当前时间不在交易时间内，程序将在收盘后自动退出")
                    
                    # 计算到下一个交易时段的时间
                    next_trading_start = self.get_next_trading_start()
                    if next_trading_start:
                        sleep_time = (next_trading_start - datetime.now()).total_seconds()
                        if sleep_time > 0:
                            print(f"⏳ 等待下一个交易时段开始: {next_trading_start.strftime('%Y-%m-%d %H:%M:%S')}")
                            time.sleep(min(sleep_time, 3600))  # 最多睡眠1小时，然后重新检查
                            
        except KeyboardInterrupt:
            print("\n用户请求停止交易系统...")
        except Exception as e:
            print(f"❌ 自动交易过程中出现错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.shutdown()

    def get_next_trading_start(self):
        """获取下一个交易开始时间"""
        now = datetime.now()
        current_time = now.time()
        current_weekday = now.weekday()
        
        # 定义交易时间段 (根据SimNow平台和中国期货市场实际交易时间)
        trading_times = [
            # 日盘
            (datetime.strptime("09:00", "%H:%M").time(), datetime.strptime("10:15", "%H:%M").time()),
            (datetime.strptime("10:30", "%H:%M").time(), datetime.strptime("11:30", "%H:%M").time()),
            (datetime.strptime("13:30", "%H:%M").time(), datetime.strptime("15:00", "%H:%M").time()),
            # 夜盘
            (datetime.strptime("21:00", "%H:%M").time(), datetime.strptime("23:59", "%H:%M").time()),
            (datetime.strptime("00:00", "%H:%M").time(), datetime.strptime("02:30", "%H:%M").time()),
        ]
        
        # 如果是周六日，跳转到下周一
        if current_weekday >= 5:
            days_ahead = 7 - current_weekday
            next_monday = now.replace(hour=trading_times[0][0].hour, minute=trading_times[0][0].minute, second=0, microsecond=0) + timedelta(days=days_ahead)
            return next_monday
        
        # 查找下一个交易时段
        for start, end in trading_times:
            if current_time < start:
                return now.replace(hour=start.hour, minute=start.minute, second=0, microsecond=0)
        
        # 如果当天没有更多交易时段，则找下一天的首个交易时段
        tomorrow = now + timedelta(days=1)
        
        # 检查下一天是否是周末
        next_weekday = tomorrow.weekday()
        if next_weekday >= 5:  # 如果是周末，跳到下周一
            days_ahead = 7 - tomorrow.weekday()
            next_monday = tomorrow.replace(hour=trading_times[0][0].hour, minute=trading_times[0][0].minute, second=0, microsecond=0) + timedelta(days=(days_ahead if days_ahead != 7 else 1))
            return next_monday
        else:
            # 下一天的首个交易时段
            next_start = tomorrow.replace(hour=trading_times[0][0].hour, 
                                        minute=trading_times[0][0].minute, 
                                        second=0, 
                                        microsecond=0)
            return next_start

    def display_market_info(self):
        """显示最新的市场行情信息"""
        if self.last_market_data:
            tick = self.last_market_data
            print(f"📊 [{self.contract_to_trade}.{self.exchange}] 行情: {tick.datetime.strftime('%H:%M:%S')} | "
                  f"最新价: {tick.last_price:.2f} | "
                  f"买一: {tick.bid_price_1:.2f}({tick.bid_volume_1}) | "
                  f"卖一: {tick.ask_price_1:.2f}({tick.ask_volume_1}) | "
                  f"涨跌: {tick.last_price - tick.pre_close:.2f}({((tick.last_price - tick.pre_close)/tick.pre_close)*100:.2f}%)")
        else:
            print(f"📊 [{self.contract_to_trade}.{self.exchange}] 行情: 等待数据...")
    
    def display_prediction_info(self):
        """显示预测信息"""
        # 如果有价格历史记录，尝试进行预测
        if len(self.price_history) >= self.window_size and self.model:
            try:
                # 准备特征数据
                features = self.prepare_features()
                if features is not None:
                    # 使用模型进行预测
                    prediction = self.model.predict(features)
                    if prediction is not None:
                        self.prediction_value = prediction[0] if isinstance(prediction, (list, np.ndarray)) else prediction
                        self.prediction_datetime = datetime.now()
                        
                        direction = "📈上涨" if self.prediction_value > 0 else "📉下跌"
                        trend_strength = "强" if abs(self.prediction_value) > self.prediction_threshold * 2 else "弱"
                        
                        print(f"🔮 AI预测: {self.prediction_datetime.strftime('%H:%M:%S')} | "
                              f"方向: {direction} | "
                              f"强度: {trend_strength} | "
                              f"幅度: {self.prediction_value:.4f} | "
                              f"阈值: ±{self.prediction_threshold:.4f}")
            except Exception as e:
                print(f"⚠️ 预测过程出错: {e}")
        elif self.prediction_datetime:
            # 如果已经有预测信息，显示最后一次的预测
            direction = "📈上涨" if self.prediction_value > 0 else "📉下跌"
            trend_strength = "强" if abs(self.prediction_value) > self.prediction_threshold * 2 else "弱"
            
            print(f"🔮 AI预测: {self.prediction_datetime.strftime('%H:%M:%S')} | "
                  f"方向: {direction} | "
                  f"强度: {trend_strength} | "
                  f"幅度: {self.prediction_value:.4f} | "
                  f"阈值: ±{self.prediction_threshold:.4f}")

    def calculate_technical_indicators(self, prices):
        """计算技术指标"""
        import numpy as np
        
        # 确保prices是numpy数组
        prices = np.array(prices, dtype=np.float64)
        
        # 计算各种技术指标
        if len(prices) >= 5:
            sma_short = np.mean(prices[-5:])
        else:
            sma_short = np.nan
            
        if len(prices) >= 20:
            sma_long = np.mean(prices[-20:])
        else:
            sma_long = np.nan
            
        # RSI计算
        if len(prices) >= 14:
            deltas = np.diff(prices[-15:])  # 需要15个价格来计算14个差值
            seed = deltas[:14]
            up = seed[seed >= 0].sum() / 14
            down = -seed[seed < 0].sum() / 14
            if down != 0:
                rs = up / down
                rsi = 100.0 - (100.0 / (1.0 + rs))
            else:
                rsi = 100.0
        else:
            rsi = np.nan
            
        # 布林带计算
        if len(prices) >= 20:
            bb_middle = sma_long
            std = prices[-20:].std()
            bb_upper = bb_middle + 2 * std
            bb_lower = bb_middle - 2 * std
        else:
            bb_middle = np.nan
            bb_upper = np.nan
            bb_lower = np.nan
        
        # 返回特征向量
        features = np.array([
            prices[-1] if len(prices) > 0 else np.nan,  # 当前价格
            sma_short,
            sma_long,
            rsi,
            bb_upper,
            bb_middle,
            bb_lower,
            (prices[-1] - sma_short) / sma_short if sma_short and sma_short != 0 else np.nan,  # 价格与短期均线偏离
            (prices[-1] - sma_long) / sma_long if sma_long and sma_long != 0 else np.nan,  # 价格与长期均线偏离
            (bb_upper - bb_lower) / bb_middle if bb_middle and bb_middle != 0 else np.nan  # 布林带宽度
        ]).reshape(-1, 10)
        
        # 用0填充NaN值
        features = np.nan_to_num(features, nan=0.0)
        
        return features

    def prepare_features(self):
        """准备预测所需的特征数据"""
        if len(self.price_history) < self.window_size:
            return None
            
        # 提取最近window_size个价格数据及相关信息
        window_data = self.price_history[-self.window_size:]
        
        # 提取各项价格数据
        prices = [item['price'] for item in window_data]
        volumes = [item['volume'] for item in window_data]
        ask_prices = [item['ask_price_1'] for item in window_data]
        bid_prices = [item['bid_price_1'] for item in window_data]
        
        # 为每个时间点计算技术指标
        feature_sequence = []
        for i in range(len(prices)):
            # 提取截至当前时间点的数据段（从开始到当前位置）
            current_prices = prices[:i+1] if i < len(prices)-1 else prices
            if len(current_prices) < 5:  # 确保有足够的数据来计算指标
                current_prices = prices[:5] if len(prices) >= 5 else prices
            
            # 计算技术指标
            indicators = self.calculate_single_bar_technical_indicators(current_prices)
            feature_sequence.append(indicators[0])  # 取第一个（也是唯一一个）指标数组
        
        # 转换为numpy数组
        features = np.array(feature_sequence)
        
        # 检查features的形状
        if len(features.shape) == 1:
            # 如果是一维数组，重塑为二维
            features = features.reshape(1, -1)
        
        # 确保特征数量为17 - 模型期望的特征数
        expected_features = 17
        actual_features = features.shape[1] if len(features.shape) > 1 else features.shape[0]
        
        if actual_features != expected_features:
            print(f"⚠️ 特征数量不匹配: 期望 {expected_features}, 实际 {actual_features}")
            
            # 如果特征数量不匹配，调整特征矩阵
            if actual_features < expected_features:
                # 如果特征数量不足，用0填充
                missing_features = expected_features - actual_features
                padding = np.zeros((features.shape[0], missing_features))
                features = np.hstack([features, padding])
            elif actual_features > expected_features:
                # 如果特征数量过多，截取前面的部分
                features = features[:, :expected_features]
        
        if features.shape != (self.window_size, expected_features):
            print(f"⚠️ 特征形状不匹配: 期望 ({self.window_size}, {expected_features}), 实际 {features.shape}")
            
            # 如果时间步长不匹配，填充或截取
            if features.shape[0] < self.window_size:
                # 填充缺失的时间步
                missing_steps = self.window_size - features.shape[0]
                padding = np.zeros((missing_steps, features.shape[1]))
                features = np.vstack([padding, features])
            elif features.shape[0] > self.window_size:
                # 截取多余的时间步
                features = features[-self.window_size:, :]
        
        # 标准化数据 - 使用模型内置的scaler
        if hasattr(self.model, 'scaler') and hasattr(self.model.scaler, 'n_samples_seen_') and self.model.scaler.n_samples_seen_ > 0:
            # 如果模型的scaler已经被拟合过，使用transform
            try:
                # reshape为2D用于标准化 (samples*time_steps, features)
                original_shape = features.shape
                features_2d = features.reshape(-1, expected_features)
                scaled_features = self.model.scaler.transform(features_2d)
                # 重新调整回3D形状
                features = scaled_features.reshape(original_shape)
            except ValueError:
                # 如果特征数量不匹配，重新拟合
                features_2d = features.reshape(-1, expected_features)
                scaled_features = self.model.scaler.fit_transform(features_2d)
                features = scaled_features.reshape(original_shape)
        else:
            # 如果模型的scaler未被拟合，使用模型的scaler进行拟合
            original_shape = features.shape
            features_2d = features.reshape(-1, expected_features)
            scaled_features = self.model.scaler.fit_transform(features_2d)
            features = scaled_features.reshape(original_shape)
        
        # 重塑为模型输入格式 (batch_size, timesteps, features)
        X = features.reshape(1, self.window_size, expected_features)
        
        return X

    def calculate_single_bar_technical_indicators(self, prices):
        """计算单个时间点的技术指标"""
        import numpy as np
        
        # 确保prices是numpy数组
        prices = np.array(prices, dtype=np.float64)
        
        # 获取当前价格
        current_price = prices[-1]
        
        # 计算各种技术指标
        if len(prices) >= 5:
            sma_short = np.mean(prices[-5:])
        else:
            sma_short = current_price
            
        if len(prices) >= 20:
            sma_long = np.mean(prices[-20:])
        else:
            sma_long = current_price
            
        # RSI计算
        if len(prices) >= 14:
            deltas = np.diff(prices[-15:]) if len(prices) >= 15 else np.diff(prices)
            if len(deltas) >= 14:
                seed = deltas[:14]
                up = seed[seed >= 0].sum() / 14
                down = -seed[seed < 0].sum() / 14
                if down != 0:
                    rs = up / down
                    rsi = 100.0 - (100.0 / (1.0 + rs))
                else:
                    rsi = 100.0
            else:
                rsi = 50  # 默认中间值
        else:
            rsi = 50  # 默认中间值
            
        # 布林带计算
        if len(prices) >= 20:
            bb_middle = sma_long
            std = prices[-20:].std()
            bb_upper = bb_middle + 2 * std
            bb_lower = bb_middle - 2 * std
        else:
            bb_middle = sma_long
            bb_upper = bb_middle + 0.02 * bb_middle  # 假设2%的波动
            bb_lower = bb_middle - 0.02 * bb_middle
            
        # 返回特征向量
        features = np.array([
            current_price,  # 当前价格
            sma_short if sma_short else current_price,
            sma_long if sma_long else current_price,
            rsi,
            bb_upper if bb_upper else current_price * 1.02,
            bb_middle if bb_middle else current_price,
            bb_lower if bb_lower else current_price * 0.98,
            (current_price - sma_short) / sma_short if sma_short and sma_short != 0 else 0,  # 价格与短期均线偏离
            (current_price - sma_long) / sma_long if sma_long and sma_long != 0 else 0,  # 价格与长期均线偏离
            (bb_upper - bb_lower) / bb_middle if bb_middle and bb_middle != 0 else 0.04  # 布林带宽度
        ])
        
        # 用0填充NaN值
        features = np.nan_to_num(features, nan=0.0)
        
        return features

    def shutdown(self):
        """关闭系统"""
        print("\n正在关闭智能自动交易系统...")
        
        # 关闭连接
        try:
            self.main_engine.close()
            print("系统已安全退出")
        except Exception as e:
            print(f"关闭系统时出错: {e}")

    def configure_gpu(self):
        """
        Configure GPU support for TensorFlow
        """
        print("🔄 检测GPU支持...")
        
        try:
            import tensorflow as tf
            print(f"✅ TensorFlow {tf.__version__} 已安装")
            
            # Check if CUDA is available
            cuda_available = tf.test.is_built_with_cuda()
            gpu_available = tf.config.list_physical_devices('GPU')
            
            if cuda_available and gpu_available:
                print("✅ 检测到GPU并已启用CUDA支持")
                print(f"✅ 可用GPU数量: {len(gpu_available)}")
                
                # Enable memory growth for GPU
                for gpu in gpu_available:
                    try:
                        tf.config.experimental.set_memory_growth(gpu, True)
                        print(f"✅ 已为 {gpu} 启用内存增长")
                    except RuntimeError as e:
                        print(f"⚠️ 无法为GPU设置内存增长: {e}")
                        
                return True
            else:
                print("❌ TensorFlow未检测到GPU支持")
                print(f"   - CUDA构建: {cuda_available}")
                print(f"   - GPU设备: {len(gpu_available) if gpu_available else 0}")
                
                print("\n💡 提示: 要使用GPU，请确保:")
                print("   1. 安装了支持GPU的TensorFlow版本 (tensorflow >= 2.10)")
                print("   2. 系统安装了匹配的CUDA和cuDNN库")
                print("   3. GPU驱动程序版本兼容")
                print("   当前系统有RTX 3070，理论上支持GPU加速")
                
                return False
                
        except ImportError:
            print("⚠️ TensorFlow未安装，将使用默认设置")
            return False
        except Exception as e:
            print(f"⚠️ GPU配置过程中出现错误: {e}")
            return False

    def update_tick_data_regularly(self):
        """主动获取并更新tick数据"""
        if hasattr(self, 'contract_to_trade') and hasattr(self, 'exchange'):
            vt_symbol = f"{self.contract_to_trade}.{self.exchange}"
            tick = self.main_engine.get_tick(vt_symbol)
            
            if tick:
                # 更新最新行情数据
                self.last_market_data = tick
                
                # 将价格数据添加到历史记录
                price_data = {
                    'price': tick.last_price,
                    'datetime': tick.datetime,
                    'volume': tick.volume,
                    'ask_price_1': tick.ask_price_1,
                    'bid_price_1': tick.bid_price_1
                }
                
                # 检查是否已有相同时间戳的数据，避免重复
                if not self.price_history or self.price_history[-1]['datetime'] != tick.datetime:
                    self.price_history.append(price_data)
                    
                    # 限制历史数据的最大数量
                    if len(self.price_history) > self.max_history_len:
                        self.price_history = self.price_history[-self.max_history_len:]

def main():
    """主函数"""
    print("期货智能自动交易系统")
    print("=" * 50)
    print("功能:")
    print("1. 检测当前是否在交易时间内")
    print("2. 获取期货合约信息")
    print("3. 使用rb2605.SHFE合约进行行情监测")
    print("4. 实时监控行情数据")
    print("5. 集成预测模型进行价格预测")
    print("6. 基于预测结果执行交易决策")
    print("7. 实施风险管理措施")
    print("=" * 50)
    
    print("开始智能自动交易...")
    
    # 初始化交易系统
    trader = SmartAutoTrading()
    
    # 检查是否在交易时间内
    if trader.is_trading_time():
        print(f"当前时间 {datetime.now().strftime('%H:%M:%S')} 在交易时间内")
    else:
        print(f"当前时间 {datetime.now().strftime('%H:%M:%S')} 不在交易时间内")
    
    # 初始化预测模型
    trader.initialize_prediction_model()
    
    # 连接CTP网关
    print("✅ 预测模型已准备就绪，现在开始连接CTP网关...")
    
    try:
        trader.run_auto_trading()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        trader.shutdown()
    except Exception as e:
        print(f"程序执行过程中出现错误: {e}")
        trader.shutdown()


if __name__ == "__main__":
    main()