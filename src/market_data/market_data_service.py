"""
行情数据服务模块
用于订阅和获取期货市场的实时行情数据
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Callable, Optional

from vnpy.event import Event, EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.event import (
    EVENT_TICK, EVENT_CONTRACT, EVENT_LOG
)
from vnpy.trader.object import TickData, ContractData, SubscribeRequest, HistoryRequest
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.utility import load_json, save_json


class MarketDataService:
    """
    行情数据服务类
    提供行情订阅、获取实时tick数据和历史数据等功能
    """
    
    def __init__(self, main_engine: MainEngine, event_engine: EventEngine):
        """"""
        self.main_engine = main_engine
        self.event_engine = event_engine
        
        # 存储已订阅的合约
        self.subscribed_symbols: set = set()
        
        # 存储最新的tick数据
        self.tick_data: Dict[str, TickData] = {}
        
        # 存储合约信息
        self.contracts: Dict[str, ContractData] = {}
        
        # 回调函数字典
        self.tick_callbacks: Dict[str, List[Callable]] = {}
        
        self._register_event_handlers()
    
    def _register_event_handlers(self):
        """注册事件处理器"""
        self.event_engine.register(EVENT_TICK, self._on_tick)
        self.event_engine.register(EVENT_CONTRACT, self._on_contract)
        self.event_engine.register(EVENT_LOG, self._on_log)
    
    def _on_tick(self, event: Event):
        """处理tick数据事件"""
        tick: TickData = event.data
        
        # 更新最新tick数据
        self.tick_data[tick.vt_symbol] = tick
        
        # 调用注册的回调函数
        if tick.vt_symbol in self.tick_callbacks:
            for callback in self.tick_callbacks[tick.vt_symbol]:
                try:
                    callback(tick)
                except Exception as e:
                    print(f"执行tick回调函数出错: {e}")
    
    def _on_contract(self, event: Event):
        """处理合约信息事件"""
        contract: ContractData = event.data
        # 保存合约信息到内部字典，不打印
        self.contracts[contract.vt_symbol] = contract
    
    def _on_log(self, event: Event):
        """处理日志事件"""
        log = event.data
        print(f"日志: {log.msg}")
    
    def subscribe(self, symbol: str, exchange: Exchange = None) -> bool:
        """
        订阅合约行情
        
        :param symbol: 合约代码，如 'rb2105' 或 'cu2105'
        :param exchange: 交易所代码，默认为None，系统会自动推断
        :return: 订阅是否成功
        """
        # 如果exchange未指定，尝试从symbol推断
        if exchange is None:
            exchange = self._infer_exchange_from_symbol(symbol)
        
        # 构建vt_symbol
        vt_symbol = f"{symbol}.{exchange.value}"
        
        # 如果已订阅，直接返回
        if vt_symbol in self.subscribed_symbols:
            print(f"合约 {vt_symbol} 已经订阅")
            return True
        
        # 创建订阅请求
        req = SubscribeRequest(
            symbol=symbol,
            exchange=exchange
        )
        
        # 发送订阅请求
        try:
            self.main_engine.subscribe(req, "CTP")
            self.subscribed_symbols.add(vt_symbol)
            print(f"正在订阅合约: {vt_symbol}")
            return True
        except Exception as e:
            print(f"订阅合约 {vt_symbol} 失败: {e}")
            return False
    
    def _infer_exchange_from_symbol(self, symbol: str) -> Exchange:
        """
        根据合约代码推断交易所
        """
        # 根据合约代码前缀判断交易所
        if symbol.startswith(('IF', 'IH', 'IC', 'T', 'TF')):
            return Exchange.CFFEX
        elif symbol.startswith(('SR', 'CF', 'TA', 'MA', 'RM', 'ZC', 'FG', 'IO')):
            return Exchange.CZCE
        elif symbol.startswith(('sc', 'lu', 'nr', 'fu', 'ru', 'bu', 'sp')):
            return Exchange.INE
        else:
            # 默认返回SHFE（上海期货交易所）
            return Exchange.SHFE
    
    def get_current_tick(self, symbol: str, exchange: Exchange = None) -> Optional[TickData]:
        """
        获取指定合约的最新tick数据
        
        :param symbol: 合约代码
        :param exchange: 交易所代码
        :return: TickData对象或None
        """
        if exchange is None:
            exchange = self._infer_exchange_from_symbol(symbol)
        
        vt_symbol = f"{symbol}.{exchange.value}"
        
        return self.tick_data.get(vt_symbol, None)
    
    def get_multiple_ticks(self, symbols_exchanges: List[tuple]) -> Dict[str, TickData]:
        """
        批量获取多个合约的tick数据
        
        :param symbols_exchanges: 合约和交易所的元组列表，如 [('rb2105', Exchange.SHFE), ('cu2105', Exchange.SHFE)]
        :return: 合约代码到TickData的映射
        """
        result = {}
        
        for symbol, exchange in symbols_exchanges:
            tick = self.get_current_tick(symbol, exchange)
            if tick:
                result[f"{symbol}.{exchange.value}"] = tick
        
        return result
    
    def register_tick_callback(self, symbol: str, exchange: Exchange, callback: Callable[[TickData], None]):
        """
        为指定合约注册tick数据回调函数
        
        :param symbol: 合约代码
        :param exchange: 交易所代码
        :param callback: 回调函数，接收TickData参数
        """
        vt_symbol = f"{symbol}.{exchange.value}"
        
        if vt_symbol not in self.tick_callbacks:
            self.tick_callbacks[vt_symbol] = []
        
        self.tick_callbacks[vt_symbol].append(callback)
        print(f"已为合约 {vt_symbol} 注册回调函数")
    
    def unsubscribe(self, symbol: str, exchange: Exchange = None):
        """
        取消订阅合约行情
        注意：VNPy中取消订阅功能可能不直接支持，这里只是标记为未订阅
        """
        if exchange is None:
            exchange = self._infer_exchange_from_symbol(symbol)
        
        vt_symbol = f"{symbol}.{exchange.value}"
        
        if vt_symbol in self.subscribed_symbols:
            self.subscribed_symbols.remove(vt_symbol)
            print(f"已取消订阅合约: {vt_symbol}")
    
    def get_all_subscribed(self) -> set:
        """获取所有已订阅的合约"""
        return self.subscribed_symbols.copy()
    
    def fetch_history_data(
        self, 
        symbol: str, 
        exchange: Exchange, 
        start_date: datetime, 
        end_date: datetime, 
        interval: Interval = Interval.MINUTE
    ) -> List:
        """
        获取历史数据
        
        :param symbol: 合约代码
        :param exchange: 交易所代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :param interval: K线周期
        :return: 历史数据列表
        """
        req = HistoryRequest(
            symbol=symbol,
            exchange=exchange,
            start=start_date,
            end=end_date,
            interval=interval
        )
        
        try:
            # 尝试通过数据服务获取历史数据
            # 这里需要有支持历史数据下载的gateway，如RQData等
            data = self.main_engine.query_history(req, "CTP")
            if data:
                print(f"获取到 {len(data)} 条历史数据")
                return data
            else:
                print("未能获取历史数据，请确认是否配置了支持历史数据查询的gateway")
                return []
        except Exception as e:
            print(f"获取历史数据失败: {e}")
            return []
    
    def get_contract_info(self, symbol: str, exchange: Exchange = None) -> Optional[ContractData]:
        """
        获取合约详细信息
        
        :param symbol: 合约代码
        :param exchange: 交易所代码
        :return: 合约信息或None
        """
        if exchange is None:
            exchange = self._infer_exchange_from_symbol(symbol)
        
        vt_symbol = f"{symbol}.{exchange.value}"
        
        # 获取合约信息
        contract = self.main_engine.get_contract(vt_symbol)
        return contract
    
    def get_contract_by_symbol(self, symbol: str) -> Optional[ContractData]:
        """
        根据合约符号获取合约信息
        :param symbol: 合约符号，如 'rb2602.SHFE'
        :return: ContractData对象或None
        """
        return self.contracts.get(symbol, None)
    
    def get_all_contracts_count(self) -> int:
        """
        获取合约总数
        :return: 合约总数
        """
        return len(self.contracts)


def run_market_data_demo():
    """
    演示行情数据服务功能
    """
    from vnpy.event import EventEngine
    from vnpy.trader.engine import MainEngine
    from vnpy_ctp import CtpGateway
    
    # 创建引擎
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    main_engine.add_gateway(CtpGateway)
    
    # 连接CTP
    script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    setting_path = os.path.join(script_dir, "settings", "simnow_setting_template.json")

    if not os.path.exists(setting_path):
        print(f"❌ 配置文件不存在: {setting_path}")
        print("💡 请按以下步骤创建配置文件:")
        print("   1. 访问 https://www.simnow.com.cn/ 注册模拟交易账户")
        print("   2. 复制模板文件: cp settings/simnow_setting_template.json settings/simnow_setting_one.json")
        print("   3. 编辑 settings/simnow_setting_one.json 文件，填入您的账户信息")
        return
    
    try:
        with open(setting_path, 'r', encoding='utf-8') as f:
            setting = json.load(f)
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        return
    
    print("正在连接CTP网关...")
    main_engine.connect(setting, "CTP")
    
    # 等待连接
    import time
    time.sleep(5)  # 等待连接
    
    # 创建行情数据服务
    market_service = MarketDataService(main_engine, event_engine)
    
    # 订阅螺纹钢主力合约
    rb_symbol = "rb2602"  # 示例：螺纹钢26年2月合约
    success = market_service.subscribe(rb_symbol, Exchange.SHFE)
    
    if success:
        print(f"已订阅 {rb_symbol} 合约")
        
        # 注册回调函数
        def print_tick(tick: TickData):
            print(f"[{tick.datetime}] {tick.vt_symbol}: 买一价 {tick.bid_price_1}, "
                  f"卖一价 {tick.ask_price_1}, 最新价 {tick.last_price}")
        
        market_service.register_tick_callback(rb_symbol, Exchange.SHFE, print_tick)
        
        # 等待一段时间收集数据
        print("等待接收tick数据，按Ctrl+C停止...")
        try:
            while True:
                time.sleep(1)
                # 可以随时获取当前tick数据
                current_tick = market_service.get_current_tick(rb_symbol, Exchange.SHFE)
                if current_tick:
                    print(f"当前最新价格: {current_tick.last_price}")
        except KeyboardInterrupt:
            print("\n停止接收数据")
    
    # 关闭连接
    main_engine.close()


if __name__ == "__main__":
    run_market_data_demo()