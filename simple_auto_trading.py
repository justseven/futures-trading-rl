import os
import sys
import json
import time
import signal
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_ctp import CtpGateway
from src.market_data.market_data_service import MarketDataService
from src.models.ml_model import PricePredictionModel
from src.data.data_processor import DataProcessor


class SimpleAutoTrading:
    """简化版自动交易系统"""
    
    def __init__(self):
        # 初始化引擎
        self.event_engine = EventEngine()
        self.main_engine = MainEngine(self.event_engine)
        
        # 添加CTP网关
        self.main_engine.add_gateway(CtpGateway)
        
        # 初始化行情服务
        self.market_service = MarketDataService(self.main_engine, self.event_engine)
        
        # 初始化数据处理器
        self.data_processor = DataProcessor()
        
        # 当前交易状态
        self.is_trading_active = False
        self.contract_to_trade = "rb2602"  # 默认交易螺纹钢主力合约
        
        # 注册信号处理器，用于优雅退出
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # 存储价格历史
        self.price_history = []
        self.max_history_len = 100  # 最大历史数据长度
        
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
    
    def connect_to_broker(self):
        """连接到期货公司"""
        config_path = "settings/simnow_setting_template.json"
        
        if not os.path.exists(config_path):
            print(f"❌ 配置文件不存在: {config_path}")
            print("💡 请按以下步骤创建配置文件:")
            print("   1. 访问 https://www.simnow.com.cn/ 注册模拟交易账户")
            print("   2. 复制模板文件: cp settings/simnow_setting_template.json settings/simnow_setting_one.json")
            print("   3. 编辑 settings/simnow_setting_one.json 文件，填入您的账户信息")
            return False
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
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
                    return True
            except Exception:
                pass
        else:
            print(f"\n⚠️ CTP连接超时")
            print("提示: 请检查SimNow账户配置、网络连接，并确认交易/行情服务器地址是否正确")
            return False
    
    def subscribe_market_data(self, symbol):
        """订阅市场数据"""
        print(f"正在订阅合约行情: {symbol}")
        
        success = self.market_service.subscribe(symbol)
        if success:
            print(f"✓ 成功订阅 {symbol}")
            
            # 注册回调函数，用于实时接收行情
            def print_tick(tick):
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
                
                print(f"[{tick.datetime.strftime('%H:%M:%S')}] {tick.vt_symbol}: "
                      f"最新价 {tick.last_price:.2f}, "
                      f"买一价 {tick.bid_price_1:.2f}, "
                      f"卖一价 {tick.ask_price_1:.2f}")
            
            # 为合约注册回调函数
            self.market_service.register_tick_callback(
                symbol, 
                self.market_service._infer_exchange_from_symbol(symbol), 
                print_tick
            )
            
            return True
        else:
            print(f"✗ 订阅 {symbol} 失败")
            return False
    
    def predict_trend_with_model(self):
        """使用模型预测价格趋势"""
        if len(self.price_history) < 20:  # 需要至少20个数据点才能预测
            print("数据不足，无法进行预测")
            return None
            
        try:
            # 尝试加载已训练的模型
            model_path = f"models/{self.contract_to_trade.replace('.', '_')}_prediction_model.h5"
            
            if os.path.exists(model_path):
                # 加载已训练的模型
                model = PricePredictionModel(model_type='lstm', sequence_length=20, n_features=4)
                model.load_model(model_path)
                
                # 准备特征数据
                recent_data = self.price_history[-20:]
                prices = [item['price'] for item in recent_data]
                bid_prices = [item['bid_price_1'] for item in recent_data]
                ask_prices = [item['ask_price_1'] for item in recent_data]
                
                # 构建特征矩阵
                features = np.column_stack([prices, bid_prices, ask_prices, 
                                          [abs(b-a) for b,a in zip(bid_prices, ask_prices)]])
                
                # 预处理数据
                df = pd.DataFrame(features, columns=['close', 'bid', 'ask', 'spread'])
                df = self.data_processor.feature_engineering(df)
                
                # 准备输入数据
                input_data = df.values[-20:]  # 取最后20个数据点
                input_data = input_data.reshape(1, input_data.shape[0], input_data.shape[1])
                
                # 预测
                prediction = model.predict(input_data)
                
                # 获取当前价格
                current_price = self.price_history[-1]['price']
                
                # 判断趋势
                trend = "上涨" if prediction[0][0] > current_price else "下跌"
                confidence = abs(prediction[0][0] - current_price) / current_price  # 计算置信度
                
                return {
                    'direction': trend,
                    'predicted_price': float(prediction[0][0]),
                    'current_price': current_price,
                    'confidence': float(confidence)
                }
            else:
                # 如果模型不存在，使用简单技术指标预测
                recent_prices = [item['price'] for item in self.price_history[-20:]]
                
                # 计算短期和长期均线
                short_ma = np.mean(recent_prices[-5:])
                long_ma = np.mean(recent_prices[-20:])
                
                current_price = recent_prices[-1]
                
                if short_ma > long_ma:
                    trend = "上涨"
                    predicted_price = current_price * 1.001  # 预测上涨0.1%
                else:
                    trend = "下跌"
                    predicted_price = current_price * 0.999  # 预测下跌0.1%
                
                return {
                    'direction': trend,
                    'predicted_price': predicted_price,
                    'current_price': current_price,
                    'confidence': 0.5
                }
                
        except Exception as e:
            print(f"预测趋势时出错: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def execute_trade_based_on_prediction(self, prediction):
        """根据预测结果执行交易"""
        if not prediction or prediction['confidence'] < 0.001:  # 置信度太低，不交易
            print(f"预测置信度太低({prediction['confidence']:.3f} < 0.001)，跳过交易")
            return False
            
        # 获取最新的tick数据
        current_tick = self.market_service.get_current_tick(self.contract_to_trade)
        if not current_tick:
            print(f"无法获取 {self.contract_to_trade} 的当前行情，无法交易")
            return False
            
        # 确定交易方向和价格
        fixed_size = 1  # 固定手数
        price_offset = 1  # 价格偏移
        
        try:
            if prediction['direction'] == '上涨':
                # 买入开多
                order_id = self.main_engine.send_order(
                    symbol=self.contract_to_trade,
                    exchange=current_tick.exchange,
                    direction="LONG",  # 买入
                    offset="OPEN",     # 开仓
                    price=current_tick.ask_price_1 + price_offset,  # 买一价+1
                    volume=fixed_size
                )
                print(f"提交买入开多订单 - 合约: {self.contract_to_trade}, "
                      f"价格: {current_tick.ask_price_1 + price_offset}, 数量: {fixed_size}")
            elif prediction['direction'] == '下跌':
                # 卖出开空
                order_id = self.main_engine.send_order(
                    symbol=self.contract_to_trade,
                    exchange=current_tick.exchange,
                    direction="SHORT",  # 卖出
                    offset="OPEN",      # 开仓
                    price=current_tick.bid_price_1 - price_offset,  # 卖一价-1
                    volume=fixed_size
                )
                print(f"提交卖出开空订单 - 合约: {self.contract_to_trade}, "
                      f"价格: {current_tick.bid_price_1 - price_offset}, 数量: {fixed_size}")
            else:
                print("预测为横盘或无方向，暂不交易")
                return False
                
            if order_id:
                print(f"订单已提交，订单ID: {order_id}")
                return True
            else:
                print("订单提交失败")
                return False
                
        except Exception as e:
            print(f"执行交易时出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_auto_trading(self):
        """运行自动交易"""
        print("开始自动交易...")
        
        # 检查是否在交易时间内
        if not self.is_trading_time():
            print("当前非交易时间，系统将在交易时间开始时自动运行")
            while not self.is_trading_time():
                print(f"当前时间 {datetime.now().strftime('%H:%M:%S')} 非交易时间，等待中...")
                time.sleep(60)  # 等待1分钟再检查
        
        print(f"当前时间 {datetime.now().strftime('%H:%M:%S')} 在交易时间内，开始运行")
        
        # 订阅市场数据
        if not self.subscribe_market_data(self.contract_to_trade):
            print("订阅市场数据失败，退出")
            return
            
        try:
            # 每隔一定时间获取一次预测并交易
            while True:
                # 检查是否仍在交易时间内
                if not self.is_trading_time():
                    print("当前已过交易时间，暂停自动交易...")
                    while not self.is_trading_time():
                        print(f"当前时间 {datetime.now().strftime('%H:%M:%S')} 非交易时间，等待中...")
                        time.sleep(60)  # 等待1分钟再检查
                    print(f"当前时间 {datetime.now().strftime('%H:%M:%S')} 再次进入交易时间")
                
                # 获取预测
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 正在获取价格趋势预测...")
                prediction = self.predict_trend_with_model()
                
                if prediction:
                    print(f"预测结果 - 方向: {prediction['direction']}, "
                          f"当前价格: {prediction['current_price']:.2f}, "
                          f"预测价格: {prediction['predicted_price']:.2f}, "
                          f"置信度: {prediction['confidence']:.3f}")
                    
                    # 根据预测执行交易
                    trade_success = self.execute_trade_based_on_prediction(prediction)
                    
                    if trade_success:
                        print("交易执行成功")
                    else:
                        print("交易执行失败或因置信度过低跳过")
                else:
                    print("预测失败，跳过本次交易")
                
                # 等待一段时间再进行下一次预测
                print("等待30秒后进行下一次预测...")
                time.sleep(30)
                
        except KeyboardInterrupt:
            print("\n接收到中断信号，正在停止自动交易...")
        except Exception as e:
            print(f"自动交易过程中出现错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.shutdown()
    
    def shutdown(self):
        """关闭系统"""
        print("\n正在关闭自动交易系统...")
        
        # 关闭连接
        try:
            self.main_engine.close()
            print("系统已安全退出")
        except Exception as e:
            print(f"关闭系统时出错: {e}")


def main():
    """主函数"""
    print("期货自动交易系统 - 简化版")
    print("=" * 50)
    print("功能:")
    print("1. 检测当前是否在交易时间内")
    print("2. 获取期货合约实时行情")
    print("3. 使用机器学习模型预测价格趋势")
    print("4. 根据预测结果自动执行交易")
    print("=" * 50)
    
    # 创建自动交易系统
    auto_trading = SimpleAutoTrading()
    
    # 连接到期货公司
    if not auto_trading.connect_to_broker():
        print("连接期货公司失败，程序退出")
        return
    
    # 运行自动交易
    auto_trading.run_auto_trading()


if __name__ == "__main__":
    main()