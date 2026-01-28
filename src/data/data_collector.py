from datetime import datetime, timedelta
import pandas as pd
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.database import get_database
from vnpy.trader.object import HistoryRequest
from vnpy_ctp import CtpGateway


class DataCollector:
    """数据采集模块"""
    
    def __init__(self, main_engine):
        self.main_engine = main_engine
        self.database = get_database()
        self.subscribed_symbols = set()
        
    def subscribe_market_data(self, symbols):
        """订阅市场数据"""
        for symbol in symbols:
            if symbol not in self.subscribed_symbols:
                contract = self.main_engine.get_contract(symbol)
                if contract:
                    self.main_engine.subscribe(contract.vt_symbol, contract.gateway_name)
                    self.subscribed_symbols.add(symbol)
                    print(f"已订阅 {symbol}")
                else:
                    print(f"找不到合约信息: {symbol}")
                    
    def load_history_data(self, symbol, exchange, start_date, end_date, interval=Interval.MINUTE):
        """加载历史数据"""
        # 将字符串日期转换为datetime对象
        if isinstance(start_date, str):
            start = datetime.strptime(start_date, "%Y-%m-%d")
        else:
            start = start_date
            
        if isinstance(end_date, str):
            end = datetime.strptime(end_date, "%Y-%m-%d")
        else:
            end = end_date
        
        # 创建历史数据请求
        req = HistoryRequest(
            symbol=symbol,
            exchange=exchange,
            start=start,
            end=end,
            interval=interval
        )
        
        # 从数据库获取历史数据
        bars = self.database.load_bar_data(req)
        
        if not bars:
            # 如果数据库中没有数据，尝试从接口获取
            print(f"数据库中没有 {symbol} 的历史数据，尝试从接口获取...")
            bars = self.main_engine.get_history_data(req)
        
        if bars:
            # 将数据转换为DataFrame格式
            data = []
            for bar in bars:
                data.append({
                    'datetime': bar.datetime,
                    'open': bar.open_price,
                    'high': bar.high_price,
                    'low': bar.low_price,
                    'close': bar.close_price,
                    'volume': bar.volume,
                    'turnover': bar.turnover,
                    'open_interest': bar.open_interest
                })
            
            df = pd.DataFrame(data)
            df.set_index('datetime', inplace=True)
            return df
        else:
            print(f"无法获取 {symbol} 的历史数据")
            return pd.DataFrame()

    def save_tick_data(self, tick):
        """保存实时tick数据到数据库"""
        self.database.save_tick_data([tick])
        
    def get_available_contracts(self, underlying_symbol=None):
        """获取可用的合约列表"""
        all_contracts = self.main_engine.get_all_contracts()
        if underlying_symbol:
            # 过滤特定标的的合约
            filtered = [c for c in all_contracts if c.symbol.startswith(underlying_symbol)]
        else:
            filtered = all_contracts
            
        return filtered