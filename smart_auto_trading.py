import os
import sys
import json
import time
import signal
import random
from datetime import datetime, timedelta

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import create_qapp
from vnpy_ctp import CtpGateway
from vnpy.trader.constant import Exchange
from src.market_data.market_data_service import MarketDataService


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
        
        # 当前交易状态
        self.is_trading_active = False
        self.contract_to_trade = "sc2701"  # 修改为使用sc2701合约
        self.exchange = "INE"  # 修改为INE能源交易中心
        
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
    
    def connect_to_broker(self):
        """连接到期货公司"""
        # 只在交易时间连接
        if not self.is_trading_time():
            print("当前非交易时间，等待进入交易时间...")
            while not self.is_trading_time():
                print(f"当前时间 {datetime.now().strftime('%H:%M:%S')} 非交易时间，等待中...")
                time.sleep(60)  # 等待1分钟再检查
            print(f"当前时间 {datetime.now().strftime('%H:%M:%S')} 进入交易时间")
        
        config_path = "settings/simnow_setting_one.json"
        
        # 获取项目根目录，确保使用绝对路径
        current_dir = os.path.dirname(os.path.abspath(__file__))  # 当前文件目录
        full_config_path = os.path.join(current_dir, config_path)
        
        if not os.path.exists(full_config_path):
            print(f"配置文件不存在: {full_config_path}")
            print("请先配置SimNow账户信息")
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
            print("当前非交易时间，系统将在非交易模式下运行")
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
            self.contract_to_trade, 
            exchange, 
            print_tick
        )
        
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
    
    def shutdown(self):
        """关闭系统"""
        print("\n正在关闭智能自动交易系统...")
        
        # 关闭连接
        try:
            self.main_engine.close()
            print("系统已安全退出")
        except Exception as e:
            print(f"关闭系统时出错: {e}")


def main():
    """主函数"""
    print("期货智能自动交易系统")
    print("=" * 50)
    print("功能:")
    print("1. 检测当前是否在交易时间内")
    print("2. 获取期货合约信息")
    print("3. 使用sc2701.INE合约进行行情监测")
    print("4. 实时监控行情数据")
    print("=" * 50)
    
    # 创建智能自动交易系统
    smart_trading = SmartAutoTrading()
    
    # 运行自动交易
    smart_trading.run_auto_trading()


if __name__ == "__main__":
    main()