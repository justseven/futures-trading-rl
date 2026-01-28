import os
import sys
import json
import time
import signal
import random
from datetime import datetime, timedelta
import numpy as np

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import create_qapp
from vnpy_ctp import CtpGateway
from vnpy.trader.constant import Exchange, Direction, Offset, OrderType, Status
from vnpy.trader.object import OrderRequest, TickData
from src.market_data.market_data_service import MarketDataService
from src.models.ml_model import PricePredictionModel
from src.risk_management.risk_manager import RiskManager
from src.trading.contract_specs import get_contract_spec


class SmartAutoTrading:
    """智能自动交易系统"""
    
    def __init__(self):
        # 初始化引擎
        self.event_engine = EventEngine()
        self.main_engine = MainEngine(self.event_engine)
        
        # 添加CTP网关
        self.main_engine.add_gateway(CtpGateway)
        
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
        
        # 存储价格历史
        self.price_history = []
        self.max_history_len = 100  # 最大历史数据长度
        
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
        
        # 控制输出频率
        self.last_output_time = 0
        self.output_interval = 0.5  # 0.5秒输出一次行情
        
        # 控制预测频率
        self.last_prediction_time = 0
        self.prediction_interval = 10  # 每10秒预测一次
    
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
        if current_weekday == 5 or current_weekday == 6:
            return False
            
        # 定义交易时间段 (实际期货市场交易时间)
        trading_times = [
            # 上期所/INE 原油等品种夜盘
            (datetime.strptime("21:00", "%H:%M").time(), datetime.strptime("23:59", "%H:%M").time()),
            # 凌晨夜盘 (跨天)
            (datetime.strptime("00:00", "%H:%M").time(), datetime.strptime("01:00", "%H:%M").time()),
            # 日盘上午
            (datetime.strptime("09:00", "%H:%M").time(), datetime.strptime("10:15", "%H:%M").time()),
            (datetime.strptime("10:30", "%H:%M").time(), datetime.strptime("11:30", "%H:%M").time()),
            # 日盘下午
            (datetime.strptime("13:30", "%H:%M").time(), datetime.strptime("15:00", "%H:%M").time()),
        ]
        
        # 特殊情况：周五夜盘延长到周六凌晨，则周六凌晨不交易
        if current_weekday == 5:  # Saturday
            # 排除周六凌晨的交易时段
            trading_times = [t for t in trading_times if t[0].hour != 0]
        
        # 检查当前时间是否在任一交易时间段内
        for start, end in trading_times:
            if start <= end:
                # 同一天的时间段
                if start <= current_time <= end:
                    return True
            else:
                # 跨天的时间段 (目前按实际规则已拆分处理)
                if current_time >= start or current_time <= end:
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

    def initialize_prediction_model(self):
        """初始化预测模型 - 不存在则训练新模型"""
        import os
        
        # 获取项目根目录的绝对路径
        project_root = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(project_root, "models", f"SHFE_rb_{self.exchange}.{self.contract_to_trade}_prediction_model.keras")
        
        print(f"🔍 检查模型路径: {model_path}")
        
        if os.path.exists(model_path):
            print(f"✅ 模型文件存在: {model_path}")
            try:
                # 加载现有模型
                self.model = PricePredictionModel()
                self.model.load_model(model_path)
                print("✅ 预测模型加载成功！")
            except Exception as e:
                print(f"❌ 加载模型时发生错误: {e}")
                print("💡 正在训练新模型...")
                self.train_new_model()
        else:
            print(f"⚠️ 模型文件不存在: {model_path}")
            print("💡 正在训练新模型...")
            self.train_new_model()
    
    def train_new_model(self):
        """训练新的预测模型"""
        try:
            import tensorflow as tf
            import os
            
            # 配置GPU使用
            configure_gpu()
            
            # 获取项目根目录的绝对路径
            project_root = os.path.dirname(os.path.abspath(__file__))
            model_path = os.path.join(project_root, "models", f"SHFE_rb_{self.exchange}.{self.contract_to_trade}_prediction_model.keras")
            
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
            
            # 训练模型 - 在GPU上下文中执行
            with tf.device('/GPU:0' if tf.config.experimental.list_physical_devices('GPU') else '/CPU:0'):
                result = trainer.train_model(
                    symbol=symbol,
                    contract_dir=contract_dir,
                    contract_pattern=contract_pattern,
                    model_type='lstm'
                )
            
            if isinstance(result, tuple) and len(result) == 3:
                self.model, history, model_path = result
                print(f"✅ {self.contract_to_trade}.{self.exchange} 的预测模型训练完成！")
                
                # 重新加载模型以确保可用
                self.model = PricePredictionModel()
                self.model.load_model(model_path)
            else:
                print(f"❌ {self.contract_to_trade}.{self.exchange} 的预测模型训练失败！")
                print("💡 使用默认模型...")
                self.model = PricePredictionModel(
                    model_type='lstm',
                    sequence_length=60,
                    n_features=22  # 根据我们验证的模型输入特征数量
                )
        except Exception as e:
            print(f"❌ 训练模型时发生错误: {e}")
            import traceback
            traceback.print_exc()
            print("💡 使用默认模型...")
            self.model = PricePredictionModel(
                model_type='lstm',
                sequence_length=60,
                n_features=22  # 根据我们验证的模型输入特征数量
            )

    def prepare_features(self):
        """准备预测所需的特征数据"""
        if len(self.price_history) < self.window_size:
            return None
            
        # 提取最近window_size个价格数据
        recent_prices = [item['price'] for item in self.price_history[-self.window_size:]]
        
        # 创建技术指标作为特征
        features = self.calculate_technical_indicators(recent_prices)
        
        # 标准化数据
        from sklearn.preprocessing import MinMaxScaler
        scaler = MinMaxScaler()
        scaled_features = scaler.fit_transform(features)
        
        # 重塑为模型输入格式
        X = scaled_features.reshape(1, self.window_size, self.feature_count)
        
        return X

    def calculate_technical_indicators(self, prices):
        """计算技术指标作为特征"""
        prices = np.array(prices)
        features = np.zeros((len(prices), self.feature_count))
        
        # 价格本身作为第一个特征
        features[:, 0] = prices
        
        # 移动平均线
        if len(prices) >= 5:
            ma5 = np.convolve(prices, np.ones(5)/5, mode='valid')
            features[len(prices)-len(ma5):, 1] = ma5
        if len(prices) >= 10:
            ma10 = np.convolve(prices, np.ones(10)/10, mode='valid')
            features[len(prices)-len(ma10):, 2] = ma10
        if len(prices) >= 20:
            ma20 = np.convolve(prices, np.ones(20)/20, mode='valid')
            features[len(prices)-len(ma20):, 3] = ma20
            
        # 价格变化率
        if len(prices) > 1:
            returns = np.diff(prices, prepend=prices[0])
            features[:, 4] = returns
            
        # 波动率
        if len(prices) >= 10:
            volatility = []
            for i in range(len(prices)):
                start_idx = max(0, i - 9)
                window = prices[start_idx:i+1]
                vol = np.std(window) if len(window) > 1 else 0
                volatility.append(vol)
            features[:, 5] = volatility
            
        # RSI
        features[:, 6] = self.calculate_rsi(prices)
        
        # MACD相关
        features[:, 7], features[:, 8] = self.calculate_macd(prices)
        
        # 布林带
        features[:, 9] = self.calculate_bollinger_bands(prices)
        
        return features

    def calculate_rsi(self, prices, period=14):
        """计算RSI指标"""
        if len(prices) < period + 1:
            return [50.0] * len(prices)
            
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gains = [np.mean(gains[:period])]
        avg_losses = [np.mean(losses[:period])]
        
        for i in range(period, len(gains)):
            avg_gains.append((avg_gains[-1] * (period - 1) + gains[i]) / period)
            avg_losses.append((avg_losses[-1] * (period - 1) + losses[i]) / period)
        
        rs = [g/l if l != 0 else 100 for g, l in zip(avg_gains, avg_losses)]
        rsi = [100 - (100 / (1 + r)) for r in rs]
        
        # 填充前面的值
        result = [50.0] * period
        result.extend(rsi)
        
        return result[:len(prices)]

    def calculate_macd(self, prices, fast=12, slow=26, signal=9):
        """计算MACD指标"""
        if len(prices) < slow:
            return [0.0] * len(prices), [0.0] * len(prices)
        
        exp1 = [prices[0]]
        exp2 = [prices[0]]
        
        k1 = 2 / (fast + 1)
        k2 = 2 / (slow + 1)
        
        for i in range(1, len(prices)):
            exp1.append(exp1[-1] + k1 * (prices[i] - exp1[-1]))
            exp2.append(exp2[-1] + k2 * (prices[i] - exp2[-1]))
        
        macd_line = [e1 - e2 for e1, e2 in zip(exp1, exp2)]
        
        signal_line = [macd_line[0]]
        k3 = 2 / (signal + 1)
        
        for i in range(1, len(macd_line)):
            signal_line.append(signal_line[-1] + k3 * (macd_line[i] - signal_line[-1]))
        
        histogram = [m - s for m, s in zip(macd_line, signal_line)]
        
        return macd_line, histogram

    def calculate_bollinger_bands(self, prices, period=20, std_dev=2):
        """计算布林带"""
        if len(prices) < period:
            return [0.0] * len(prices)
            
        bb_values = []
        for i in range(len(prices)):
            start_idx = max(0, i - period + 1)
            window = prices[start_idx:i+1]
            
            ma = np.mean(window)
            std = np.std(window)
            
            upper_band = ma + std_dev * std
            lower_band = ma - std_dev * std
            
            # 归一化布林带值
            if upper_band != lower_band:
                bb_value = (prices[i] - lower_band) / (upper_band - lower_band)
            else:
                bb_value = 0.5
                
            bb_values.append(bb_value)
        
        return bb_values

    def generate_prediction(self):
        """生成价格预测"""
        if not self.model:
            print("⚠️ 预测模型未初始化")
            return
            
        features = self.prepare_features()
        if features is None:
            print("⚠️ 特征数据不足，无法进行预测")
            return
            
        try:
            # 进行预测
            prediction = self.model.predict(features)
            
            # 反归一化
            # 这里简化处理，实际应用中可能需要单独的反归一化方法
            self.prediction_value = float(prediction[0]) if isinstance(prediction, np.ndarray) else float(prediction)
            
            self.prediction_datetime = datetime.now()
            
            print(f"📈 预测值(30分钟后): {self.prediction_value:.4f}, 当前价格: {self.last_price:.2f}")
        except Exception as e:
            print(f"❌ 预测失败: {e}")

    def execute_trading_logic(self):
        """执行基于预测结果的交易逻辑"""
        if not self.prediction_value or self.last_price == 0 or not self.model:
            return
            
        # 计算预期收益率 - 基于30分钟后的预测
        expected_return = (self.prediction_value - self.last_price) / self.last_price
        
        # 根据预测值执行交易决策
        if abs(expected_return) > self.prediction_threshold:
            print(f"📊 预期30分钟后收益率: {expected_return:.2%}, 阈值: {self.prediction_threshold:.2%}")
            
            # 风险管理检查 - 使用当前持仓
            if not self.check_risk_limits():
                print("⚠️ 风险管理检查未通过，暂停交易")
                return
                
            # 获取合约信息
            contract = self.main_engine.get_contract(f"{self.contract_to_trade}.{self.exchange}")
            if not contract:
                print(f"❌ 无法获取合约信息: {self.contract_to_trade}.{self.exchange}")
                return
                
            contract_size = contract.size if contract else self.contract_spec['size']
            position_limit = min(self.max_position_size, int(self.account_balance * 0.1 / (self.last_price * contract_size)))
            
            # 根据预测值执行交易决策
            if expected_return > self.prediction_threshold:
                # 预测上涨，考虑做多
                if self.current_position < position_limit:
                    # 计算目标仓位
                    target_volume = min(position_limit - self.current_position, 1)  # 每次最多增加1手
                    
                    # 检查交易是否盈利（扣除手续费和保证金）
                    if self.is_profitable_trade(expected_return, self.last_price, target_volume, Direction.LONG):
                        order_req = OrderRequest(
                            symbol=self.contract_to_trade,
                            exchange=getattr(Exchange, self.exchange),
                            direction=Direction.LONG,
                            offset=Offset.OPEN,
                            price=self.last_price + 1,  # 买价挂单
                            volume=target_volume,
                            order_type=OrderType.LIMIT
                        )
                        
                        order_id = self.main_engine.send_order(order_req, "CTP")
                        if order_id:
                            print(f"📈 下单做多: {target_volume}手, 价格: {self.last_price + 1:.2f}, 预期30分钟后收益: {expected_return:.2%}")
                            
                            # 记录活跃订单
                            self.active_orders[order_id] = {
                                'direction': Direction.LONG,
                                'volume': target_volume,
                                'price': self.last_price + 1,
                                'status': 'submitted'
                            }
                        else:
                            print("❌ 下单失败")
                    else:
                        print("❌ 交易无利可图，跳过此次交易机会")
                        
            elif expected_return < -self.prediction_threshold:
                # 预测下跌，考虑做空
                if self.current_position > -position_limit:
                    # 计算目标仓位
                    target_volume = min(position_limit + self.current_position, 1)  # 每次最多增加1手空头
                    
                    # 检查交易是否盈利（扣除手续费和保证金）
                    if self.is_profitable_trade(-expected_return, self.last_price, target_volume, Direction.SHORT):
                        order_req = OrderRequest(
                            symbol=self.contract_to_trade,
                            exchange=getattr(Exchange, self.exchange),
                            direction=Direction.SHORT,
                            offset=Offset.OPEN,
                            price=self.last_price - 1,  # 卖价挂单
                            volume=target_volume,
                            order_type=OrderType.LIMIT
                        )
                        
                        order_id = self.main_engine.send_order(order_req, "CTP")
                        if order_id:
                            print(f"📉 下单做空: {target_volume}手, 价格: {self.last_price - 1:.2f}, 预期30分钟后收益: {abs(expected_return):.2%}")
                            
                            # 记录活跃订单
                            self.active_orders[order_id] = {
                                'direction': Direction.SHORT,
                                'volume': target_volume,
                                'price': self.last_price - 1,
                                'status': 'submitted'
                            }
                        else:
                            print("❌ 下单失败")
                    else:
                        print("❌ 交易无利可图，跳过此次交易机会")
    
    def check_risk_limits(self):
        """检查风险限制"""
        # 检查当前持仓是否超过最大限制
        if abs(self.current_position) >= self.risk_manager.max_pos:
            return False
            
        # 检查当日盈亏是否超过限制
        if self.daily_pnl < -self.risk_manager.max_daily_loss:
            self.risk_manager.trading_enabled = False
            return False
            
        return self.risk_manager.trading_enabled
    
    def connect_to_broker(self):
        """连接到期货公司"""
        # 只在交易时间连接
        if not self.is_trading_time():
            print("当前非交易时间，等待进入交易时间...")
            while not self.is_trading_time():
                print(f"当前时间 {datetime.now().strftime('%H:%M:%S')} 非交易时间，等待中...")
                time.sleep(60)  # 等待1分钟再检查
            print(f"当前时间 {datetime.now().strftime('%H:%M:%S')} 进入交易时间")
        
        # 检查配置文件是否存在，不存在则提示用户创建
        config_path = "settings/simnow_setting_one.json"
        
        # 获取项目根目录，确保使用绝对路径
        current_dir = os.path.dirname(os.path.abspath(__file__))  # 当前文件目录
        full_config_path = os.path.join(current_dir, "..", "..", config_path)  # 从smart_auto_trading.py回到项目根目录
        
        if not os.path.exists(full_config_path):
            print(f"❌ 配置文件不存在: {full_config_path}")
            print("💡 请按以下步骤创建配置文件:")
            print("   1. 访问 https://www.simnow.com.cn/ 注册模拟交易账户")
            print("   2. 复制模板文件: cp settings/simnow_setting_template.json settings/simnow_setting_one.json")
            print("   3. 编辑 settings/simnow_setting_one.json 文件，填入您的账户信息")
            print("   4. 重新运行程序")
            return False
        
        try:
            with open(full_config_path, 'r', encoding='utf-8') as f:
                setting = json.load(f)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return False
        
        print(f"正在连接CTP网关，使用配置文件: {config_path}...")
        self.main_engine.connect(setting, "CTP")
        
        # 等待连接建立
        print("等待连接建立", end="")
        for i in range(30):  # 增加等待时间至30秒
            time.sleep(1)
            print(".", end="", flush=True)
            
            # 检查是否已连接到交易和行情服务器
            # 尝试获取合约信息判断连接状态
            try:
                contracts = self.main_engine.get_all_contracts()
                if len(contracts) > 0:
                    print(f"\n✅ 行情连接成功！已获取到 {len(contracts)} 个合约信息")
                    
                    # 获取账户信息
                    account = self.main_engine.get_account("CTP")
                    if account:
                        self.account_balance = account.balance
                        print(f"💰 账户余额: {self.account_balance:.2f}")
        
                    # 获取持仓信息
                    position = self.main_engine.get_position(f"{self.contract_to_trade}.{self.exchange}")
                    if position:
                        self.current_position = position.volume
                        self.current_position_avg_price = position.price
                        print(f"📊 当前持仓: {self.current_position}手, 持仓均价: {self.current_position_avg_price:.2f}")
                    else:
                        self.current_position = 0
                        self.current_position_avg_price = 0
                        
                    return True
            except Exception:
                pass
        else:
            print(f"\n⚠️ CTP连接超时")
            print("提示: 请检查SimNow账户配置、网络连接，并确认交易/行情服务器地址是否正确")
            return False
    
    def run_auto_trading(self):
        """运行自动交易"""
        print("开始智能自动交易...")
        
        # 检查是否在交易时间内
        if not self.is_trading_time():
            print("当前为非交易时间，使用配置文件: settings/simnow_setting_two.json")
            print("系统将尝试连接服务器以获取数据...")
        else:
            print(f"当前时间 {datetime.now().strftime('%H:%M:%S')} 在交易时间内")
            print("使用配置文件: settings/simnow_setting_one.json")
        
        # 连接到期货公司
        if not self.connect_to_broker():
            print("连接期货公司失败，退出")
            return
        
        # 获取合约信息
        print("正在获取合约信息...")
        all_contracts = self.main_engine.get_all_contracts()
        print(f"共获取到 {len(all_contracts)} 个合约信息")
        
        if len(all_contracts) == 0:
            print("未能获取到任何合约信息，程序退出")
            return
        
        # 检查是否在交易时间内（再次确认）
        if not self.is_trading_time():
            print("当前为非交易时间，系统将在非交易模式下运行")
            print("注意：在非交易时间，系统将只监控行情，不执行任何交易操作")
            
            # 在非交易时间，只进行行情监控
            print(f"当前时间为非交易时间，系统将监控行情数据： {self.contract_to_trade}.{self.exchange}")
            print("要执行交易操作，请在交易时间运行程序")
        
        # 直接使用预设的合约而不是随机选择
        print(f"选择合约进行行情监测: {self.contract_to_trade}.{self.exchange}")
        
        # 获取交易所枚举
        from vnpy.trader.constant import Exchange
        exchange_map = {
            'SHFE': Exchange.SHFE,
            'CZCE': Exchange.CZCE,
            'DCE': Exchange.DCE,
            'CFFEX': Exchange.CFFEX,
            'INE': Exchange.INE
        }
        exchange = exchange_map.get(self.exchange, Exchange.SHFE)
        
        # 订阅该合约的行情
        print(f"正在订阅合约行情: {self.contract_to_trade}.{self.exchange}")
        success = self.market_service.subscribe(self.contract_to_trade, exchange)
        if not success:
            print(f"订阅 {self.contract_to_trade}.{self.exchange} 失败")
            return
        else:
            print(f"成功订阅 {self.contract_to_trade}.{self.exchange}")
        
        # 记录最后一次系统状态更新时间
        last_status_update = time.time()
        last_prediction_time = time.time()
        
        # 注册回调函数，用于实时接收行情
        def print_tick(tick):
            # 更新最新价格
            self.last_price = tick.last_price
            
            # 保存价格到历史记录
            self.price_history.append({
                'price': tick.last_price,
                'datetime': tick.datetime,
                'bid_price_1': tick.bid_price_1,
                'ask_price_1': tick.ask_price_1
            })
            
            # 限制历史数据长度
            if len(self.price_history) > self.max_history_len:
                self.price_history = self.price_history[-self.max_history_len:]
            
            # 每0.5秒输出一次行情，避免刷屏
            current_time = time.time()
            if current_time - self.last_output_time >= self.output_interval:
                print(f"[{tick.datetime.strftime('%H:%M:%S')}] {tick.vt_symbol}: "
                      f"最新价 {tick.last_price:.2f}, "
                      f"买一价 {tick.bid_price_1:.2f}, "
                      f"卖一价 {tick.ask_price_1:.2f}")
                self.last_output_time = current_time
            
            # 每隔一段时间生成预测
            if len(self.price_history) >= self.window_size:
                if current_time - last_prediction_time >= self.prediction_interval:
                    print(f"🔄 执行预测和交易逻辑检查...")
                    self.generate_prediction()
                    self.execute_trading_logic()
                    last_prediction_time = current_time
                else:
                    # 即使不执行预测，也输出系统状态
                    if current_time - last_status_update >= 2:  # 每2秒输出一次状态
                        print(f"🔄 系统运行中... 当前价格: {tick.last_price:.2f}, "
                              f"持仓: {self.current_position}, "
                              f"历史数据: {len(self.price_history)}/{self.window_size}")
                        last_status_update = current_time

        # 为合约注册回调函数
        self.market_service.register_tick_callback(
            self.contract_to_trade, 
            exchange, 
            print_tick
        )
        
        # 导入事件类型常量
        from vnpy.trader.event import EVENT_ORDER, EVENT_TRADE, EVENT_POSITION
        
        # 注册事件监听器
        self.event_engine.register(EVENT_ORDER, self.on_order_update)
        self.event_engine.register(EVENT_TRADE, self.on_trade_fill)
        self.event_engine.register(EVENT_POSITION, self.on_position_update)
        
        try:
            # 持续监控市场数据
            print("正在持续监控市场数据，按 Ctrl+C 退出...")
            while True:
                # 检查是否仍在交易时间内
                if not self.is_trading_time():
                    print("当前已过交易时间，进入非交易模式（仅监控行情）...")
                    while not self.is_trading_time():
                        print(f"当前时间 {datetime.now().strftime('%H:%M:%S')} 非交易时间，仅监控行情...")
                        time.sleep(60)  # 等待1分钟再检查
                    print(f"当前时间 {datetime.now().strftime('%H:%M:%S')} 再次进入交易时间")
                
                # 每秒检查一次系统状态，即使没有新的tick数据
                current_time = time.time()
                if current_time - last_status_update >= 5:  # 每5秒输出一次状态
                    print(f"🔄 系统运行中... 当前价格: {self.last_price:.2f}, "
                          f"持仓: {self.current_position}, "
                          f"历史数据: {len(self.price_history)}/{self.window_size}")
                    last_status_update = current_time
                
                # 每30秒检查一次市场数据
                for _ in range(30):  # 分解大延时，使中断响应更灵敏
                    if not self.is_trading_time():
                        break
                    time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n接收到中断信号，正在停止自动交易...")
        except Exception as e:
            print(f"自动交易过程中出现错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.shutdown()
    
    def on_tick(self, tick: TickData):
        """
        行情TICK回调函数
        作为类方法，避免局部函数可能引起的引用或属性错误。
        """
        try:
            # 更新最新价格
            self.last_price = tick.last_price

            # 保存价格到历史记录
            self.price_history.append({
                'price': tick.last_price,
                'datetime': tick.datetime,
                'bid_price_1': tick.bid_price_1,
                'ask_price_1': tick.ask_price_1
            })

            # 限制历史数据长度
            if len(self.price_history) > self.max_history_len:
                self.price_history = self.price_history[-self.max_history_len:]

            # 每0.5秒输出一次行情，避免刷屏
            current_time = time.time()
            if current_time - self.last_output_time >= self.output_interval:
                # 增强的实时行情显示，包含更多市场信息
                print(f"\n📊 [行情更新] {tick.datetime.strftime('%Y-%m-%d %H:%M:%S')} | "
                      f"{tick.vt_symbol} | "
                      f"最新价: {tick.last_price:.2f} | "
                      f"买一: {tick.bid_price_1:.2f} ({tick.bid_volume_1}) | "
                      f"卖一: {tick.ask_price_1:.2f} ({tick.ask_volume_1}) | "
                      f"成交量: {tick.volume} (累计: {tick.trading_volume}) | "
                      f"持仓量: {tick.open_interest}")
                self.last_output_time = current_time

            # 每隔一段时间生成预测
            if len(self.price_history) >= self.window_size:
                if current_time - self.last_prediction_time >= self.prediction_interval:
                    self.generate_prediction()
                    self.execute_trading_logic()
                    self.last_prediction_time = current_time

        except AttributeError as e:
            print(f"处理tick数据时发生属性错误: {e}")
        except Exception as e:
            print(f"处理tick数据时发生未知错误: {e}")
            
    def on_order_update(self, event):
        """处理订单状态更新"""
        order = event.data
        if order.vt_orderid in self.active_orders:
            print(f"📋 订单状态更新: {order.vt_orderid}, 状态: {order.status.name}, 已成交: {order.traded}/{order.volume}")
            
            if order.status == Status.ALLTRADED:
                # 订单全部成交，移除活跃订单
                del self.active_orders[order.vt_orderid]
                print(f"✅ 订单 {order.vt_orderid} 已全部成交")
            elif order.status in [Status.REJECTED, Status.CANCELLED]:
                # 订单被拒或撤销，移除活跃订单
                del self.active_orders[order.vt_orderid]
                print(f"❌ 订单 {order.vt_orderid} 已{order.status.name}")
    
    def on_trade_fill(self, event):
        """处理成交回报"""
        trade = event.data
        if trade.vt_symbol == f"{self.contract_to_trade}.{self.exchange}":
            print(f"💼 成交回报: {trade.direction.name} {trade.offset.name} {trade.volume}手 @ {trade.price:.2f}")
            
            # 更新持仓
            self.update_position(trade.direction, trade.volume, trade.price)
            
            # 更新当前总持仓
            if trade.direction == Direction.LONG:
                if trade.offset == Offset.OPEN:
                    self.current_position += trade.volume
                else:
                    self.current_position -= trade.volume
            elif trade.direction == Direction.SHORT:
                if trade.offset == Offset.OPEN:
                    self.current_position -= trade.volume
                else:
                    self.current_position += trade.volume
                    
            print(f"📊 当前持仓: {self.current_position}手")
    
    def on_position_update(self, event):
        """处理持仓更新"""
        position = event.data
        if position.vt_symbol == f"{self.contract_to_trade}.{self.exchange}":
            print(f"📈 持仓更新: 方向 {position.direction.name}, 数量 {position.volume}, 均价 {position.price:.2f}")
            # 更新本地持仓信息
            if position.direction == Direction.LONG:
                self.position_details['long']['volume'] = position.volume
                self.position_details['long']['avg_price'] = position.price
            elif position.direction == Direction.SHORT:
                self.position_details['short']['volume'] = position.volume
                self.position_details['short']['avg_price'] = position.price

    def update_position(self, direction, volume, price):
        """更新持仓信息"""
        if direction == Direction.LONG:
            # 多头持仓
            old_volume = self.position_details['long']['volume']
            old_avg_price = self.position_details['long']['avg_price']
            
            new_volume = old_volume + volume
            if new_volume > 0:
                new_avg_price = (old_volume * old_avg_price + volume * price) / new_volume
                self.position_details['long']['volume'] = new_volume
                self.position_details['long']['avg_price'] = new_avg_price
            else:
                # 清空多头持仓
                self.position_details['long']['volume'] = 0
                self.position_details['long']['avg_price'] = 0
        elif direction == Direction.SHORT:
            # 空头持仓
            old_volume = self.position_details['short']['volume']
            old_avg_price = self.position_details['short']['avg_price']
            
            new_volume = old_volume + volume
            if new_volume > 0:
                new_avg_price = (old_volume * old_avg_price + volume * price) / new_volume
                self.position_details['short']['volume'] = new_volume
                self.position_details['short']['avg_price'] = new_avg_price
            else:
                # 清空空头持仓
                self.position_details['short']['volume'] = 0
                self.position_details['short']['avg_price'] = 0

    def calculate_pnl(self, exit_price):
        """计算盈亏"""
        long_pnl = 0
        short_pnl = 0
        
        contract = self.main_engine.get_contract(f"{self.contract_to_trade}.{self.exchange}")
        contract_size = contract.size if contract else self.contract_spec['size']
        
        if self.position_details['long']['volume'] > 0:
            long_pnl = (exit_price - self.position_details['long']['avg_price']) * \
                       self.position_details['long']['volume'] * contract_size
        
        if self.position_details['short']['volume'] > 0:
            short_pnl = (self.position_details['short']['avg_price'] - exit_price) * \
                        self.position_details['short']['volume'] * contract_size
        
        return long_pnl + short_pnl
    
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
    
    # 检查当前时间是否在交易时间内
    if not trader.is_trading_time():
        print("❌ 当前时间不在交易时间内，程序退出")
        return
    
    print(f"当前时间 {datetime.now().strftime('%H:%M:%S')} 在交易时间内")
    
    # 配置TensorFlow使用GPU（如果可用）
    configure_gpu()
    
    # 首先初始化和训练预测模型 - 必须在连接CTP之前完成
    print("🔄 开始初始化预测模型...")
    trader.initialize_prediction_model()
    
    # 确保模型已加载或训练完成后再继续
    print("✅ 预测模型已准备就绪，现在开始连接CTP网关...")
    
    # 连接到期货公司并启动自动交易
    print("🔄 开始连接CTP网关...")
    print("🔄 开始订阅合约行情...")
    print("🔄 开始启动事件引擎...")
    
    # 直接运行自动交易，其中包含了连接网关、订阅行情和启动事件引擎
    trader.run_auto_trading()


def configure_gpu():
    """配置TensorFlow使用GPU（如果可用）"""
    try:
        import tensorflow as tf
        
        # 检查是否有可用的GPU
        gpus = tf.config.experimental.list_physical_devices('GPU')
        if gpus:
            print(f"✅ 检测到 {len(gpus)} 个GPU设备: {[gpu.name for gpu in gpus]}")
            
            # 启用内存增长，防止占用所有GPU内存
            for gpu in gpus:
                tf.config.experimental.set_memory_growth(gpu, True)
            
            # 设置使用第一个GPU
            tf.config.experimental.set_visible_devices(gpus[0], 'GPU')
            
            # 验证GPU是否可用
            logical_gpus = tf.config.experimental.list_logical_devices('GPU')
            print(f"✅ {len(logical_gpus)} 个逻辑GPU设备已准备就绪")
            
            print("✅ GPU配置完成，将用于模型训练和预测")
            
            # 返回GPU设备信息以便在训练时使用
            return gpus[0]
        else:
            print("⚠️ 未检测到GPU，将使用CPU进行模型训练")
            # 尝试列出所有物理设备
            devices = tf.config.experimental.list_physical_devices()
            gpu_devices = [device for device in devices if device.device_type == 'GPU']
            cpu_devices = [device for device in devices if device.device_type == 'CPU']
            print(f"系统检测到: {len(cpu_devices)} 个CPU设备, {len(gpu_devices)} 个GPU设备")
            
            return None
            
    except ImportError:
        print("⚠️ TensorFlow未安装，无法配置GPU加速")
        return None
    except Exception as e:
        print(f"⚠️ GPU配置失败: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()