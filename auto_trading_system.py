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
from vnpy.trader.ui import create_qapp
from vnpy_ctp import CtpGateway
from vnpy_ctastrategy import CtaStrategyApp
from src.market_data.market_data_service import MarketDataService
from src.models.ml_model import PricePredictionModel
from src.strategies.predictive_trading_strategy import PredictiveTradingStrategy
from src.data.data_processor import DataProcessor


class AutoTradingSystem:
    """自动交易系统"""
    
    def __init__(self):
        # 初始化引擎
        self.event_engine = EventEngine()
        self.main_engine = MainEngine(self.event_engine)
        
        # 添加CTP网关
        self.main_engine.add_gateway(CtpGateway)
        
        # 添加CTA策略应用
        self.main_engine.add_app(CtaStrategyApp)
        
        # 初始化行情服务
        self.market_service = MarketDataService(self.main_engine, self.event_engine)
        
        # 初始化数据处理器
        self.data_processor = DataProcessor()
        
        # 当前交易状态
        self.is_trading_active = False
        self.active_contracts = ["rb2602", "cu2602", "ni2602"]  # 默认活跃合约列表
        
        # 注册信号处理器，用于优雅退出
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
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
        config_path = "settings/simnow_setting.json"
        
        if not os.path.exists(config_path):
            print(f"配置文件不存在: {config_path}")
            print("请先配置SimNow仿真账户信息")
            return False
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                setting = json.load(f)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return False
        
        print("正在连接CTP网关...")
        self.main_engine.connect(setting, "CTP")
        
        # 等待连接建立
        for i in range(10):
            time.sleep(1)
            print(".", end="", flush=True)
            
        print("\nCTP网关连接完成")
        return True
    
    def subscribe_market_data(self, symbols):
        """订阅市场数据"""
        print(f"正在订阅合约行情: {symbols}")
        
        success_count = 0
        for symbol in symbols:
            success = self.market_service.subscribe(symbol)
            if success:
                print(f"✓ 成功订阅 {symbol}")
                success_count += 1
            else:
                print(f"✗ 订阅 {symbol} 失败")
        
        print(f"成功订阅 {success_count}/{len(symbols)} 个合约")
        return success_count > 0
    
    def get_latest_market_data(self, symbol):
        """获取最新的市场数据"""
        return self.market_service.get_current_tick(symbol)
    
    def predict_trend_with_model(self, symbol, ticks_history):
        """使用模型预测价格趋势"""
        try:
            # 如果有足够的历史数据，尝试使用已训练的模型
            model_path = f"models/{symbol.replace('.', '_')}_prediction_model.h5"
            
            if os.path.exists(model_path):
                # 加载已训练的模型
                model = PricePredictionModel(model_type='lstm', sequence_length=60, n_features=10)
                model.load_model(model_path)
                
                # 准备特征数据
                if len(ticks_history) >= 60:
                    # 使用最后60个tick数据进行预测
                    recent_ticks = ticks_history[-60:]
                    prices = [tick.last_price for tick in recent_ticks]
                    
                    # 预处理数据
                    df = pd.DataFrame({'close': prices})
                    df = self.data_processor.feature_engineering(df)
                    
                    # 准备输入数据
                    features = df.values[-60:]  # 取最后60个数据点
                    features = features.reshape(1, features.shape[0], features.shape[1])
                    
                    # 预测
                    prediction = model.predict(features)
                    
                    # 根据预测值判断趋势
                    current_price = ticks_history[-1].last_price
                    predicted_trend = "上涨" if prediction[0][0] > current_price else "下跌"
                    
                    return {
                        'direction': predicted_trend,
                        'predicted_price': prediction[0][0],
                        'confidence': abs(prediction[0][0] - current_price) / current_price  # 计算置信度
                    }
            else:
                # 如果模型不存在，使用简单技术指标预测
                if len(ticks_history) >= 20:
                    recent_prices = [tick.last_price for tick in ticks_history[-20:]]
                    ma_short = np.mean(recent_prices[-5:])
                    ma_long = np.mean(recent_prices[-20:])
                    
                    if ma_short > ma_long:
                        return {
                            'direction': '上涨',
                            'predicted_price': recent_prices[-1] * 1.001,  # 简单预测上涨0.1%
                            'confidence': 0.5
                        }
                    else:
                        return {
                            'direction': '下跌',
                            'predicted_price': recent_prices[-1] * 0.999,  # 简单预测下跌0.1%
                            'confidence': 0.5
                        }
                        
        except Exception as e:
            print(f"预测趋势时出错: {e}")
            
        # 默认返回中性预测
        return {
            'direction': '横盘',
            'predicted_price': 0,
            'confidence': 0
        }
    
    def execute_trade_based_on_prediction(self, symbol, prediction):
        """根据预测结果执行交易"""
        if prediction['confidence'] < 0.005:  # 置信度太低，不交易
            print(f"预测置信度太低({prediction['confidence']:.3f})，跳过交易")
            return False
            
        # 获取当前tick数据
        current_tick = self.get_latest_market_data(symbol)
        if not current_tick:
            print(f"无法获取 {symbol} 的当前行情，无法交易")
            return False
            
        # 获取CTA策略引擎
        cta_engine = self.main_engine.get_engine("CtaStrategy")
        
        # 生成策略名称
        strategy_name = f"AutoTrade_{symbol}_{int(time.time())}"
        
        # 交易参数
        fixed_size = 1  # 固定手数
        price_offset = 1  # 价格偏移
        
        try:
            # 根据预测方向执行交易
            if prediction['direction'] == '上涨':
                # 买入开多
                print(f"执行买入开多操作 - 合约: {symbol}, 价格: {current_tick.ask_price_1}")
                order_id = self.main_engine.send_order(
                    symbol=symbol,
                    exchange=current_tick.exchange,
                    direction='long',
                    type='limit',
                    volume=fixed_size,
                    price=current_tick.ask_price_1 + price_offset,
                    offset='open'
                )
            elif prediction['direction'] == '下跌':
                # 卖出开空
                print(f"执行卖出开空操作 - 合约: {symbol}, 价格: {current_tick.bid_price_1}")
                order_id = self.main_engine.send_order(
                    symbol=symbol,
                    exchange=current_tick.exchange,
                    direction='short',
                    type='limit',
                    volume=fixed_size,
                    price=current_tick.bid_price_1 - price_offset,
                    offset='open'
                )
            else:
                print("预测为横盘，暂不交易")
                return False
                
            if order_id:
                print(f"订单已发送: {order_id}")
                return True
            else:
                print("订单发送失败")
                return False
                
        except Exception as e:
            print(f"执行交易时出错: {e}")
            return False
    
    def run_auto_trading_cycle(self, symbols):
        """运行自动交易循环"""
        print("开始自动交易循环...")
        
        # 订阅市场数据
        if not self.subscribe_market_data(symbols):
            print("订阅市场数据失败，退出")
            return
            
        # 存储每个合约的tick历史
        ticks_history = {symbol: [] for symbol in symbols}
        
        try:
            while True:
                # 检查是否在交易时间内
                if not self.is_trading_time():
                    print("当前非交易时间，暂停自动交易...")
                    time.sleep(60)  # 等待1分钟再检查
                    continue
                
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 检查市场数据并准备预测...")
                
                for symbol in symbols:
                    # 获取最新tick数据
                    tick = self.get_latest_market_data(symbol)
                    
                    if tick:
                        # 添加到历史数据
                        ticks_history[symbol].append(tick)
                        
                        # 保持最多200条历史数据
                        if len(ticks_history[symbol]) > 200:
                            ticks_history[symbol] = ticks_history[symbol][-200:]
                            
                        print(f"{symbol} - 当前价格: {tick.last_price}, 涨跌: {tick.last_price - tick.pre_close:.2f}")
                        
                        # 当有足够数据时进行预测
                        if len(ticks_history[symbol]) >= 20:
                            # 预测价格趋势
                            prediction = self.predict_trend_with_model(symbol, ticks_history[symbol])
                            
                            print(f"预测结果 - 方向: {prediction['direction']}, "
                                  f"预测价格: {prediction['predicted_price']:.2f}, "
                                  f"置信度: {prediction['confidence']:.3f}")
                            
                            # 根据预测执行交易
                            if prediction['confidence'] > 0.005:  # 只有在置信度较高时才交易
                                trade_success = self.execute_trade_based_on_prediction(symbol, prediction)
                                
                                if trade_success:
                                    print(f"交易执行成功 - {symbol}")
                                else:
                                    print(f"交易执行失败 - {symbol}")
                
                # 等待一段时间再进行下一轮
                time.sleep(10)  # 等待10秒
                
        except KeyboardInterrupt:
            print("\n接收到中断信号，正在停止自动交易...")
        except Exception as e:
            print(f"自动交易过程中出现错误: {e}")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """关闭系统"""
        print("正在关闭自动交易系统...")
        
        # 关闭连接
        try:
            self.main_engine.close()
            print("系统已安全退出")
        except Exception as e:
            print(f"关闭系统时出错: {e}")


def main():
    """主函数"""
    print("期货自动交易系统")
    print("=" * 50)
    
    # 创建自动交易系统
    auto_trading_system = AutoTradingSystem()
    
    # 连接到期货公司
    if not auto_trading_system.connect_to_broker():
        print("连接期货公司失败，程序退出")
        return
    
    # 定义要交易的合约
    contracts_to_trade = ["rb2602", "cu2602", "ni2602"]  # 螺纹钢、沪铜、沪镍
    
    # 运行自动交易循环
    auto_trading_system.run_auto_trading_cycle(contracts_to_trade)


if __name__ == "__main__":
    main()