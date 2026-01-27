"""
CTP交易引擎 - 基于vnpy_ctp的SimNow仿真环境连接和交易
"""

import time
import threading
from typing import Dict, Any
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_ctp import CtpGateway
from vnpy.trader.constant import Direction, Offset, OrderType
from vnpy.trader.object import OrderRequest, SubscribeRequest


class CTPEngine:
    """
    CTP交易引擎，负责连接SimNow仿真环境并执行交易
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化CTP引擎

        Args:
            config: CTP连接配置
        """
        self.config = config
        self.event_engine = EventEngine()
        self.main_engine = MainEngine(self.event_engine)

        # 添加CTP网关
        self.main_engine.add_gateway(CtpGateway)

        # 连接状态
        self.connected = False
        self.symbol = "RB9999.XSGE"  # 螺纹钢主力合约
        self.vt_symbol = f"{self.symbol}.XSGE"

        # 持仓信息
        self.position = 0  # 正数表示多头，负数表示空头
        self.last_price = 0.0

        # 订单管理
        self.order_count = 0
        self.active_orders = {}

    def connect(self) -> bool:
        """
        连接CTP仿真环境

        Returns:
            bool: 连接是否成功
        """
        try:
            print("正在连接CTP SimNow仿真环境...")
            self.main_engine.connect(self.config, "CTP")

            # 等待连接建立
            timeout = 30
            start_time = time.time()
            while time.time() - start_time < timeout:
                # 检查连接状态 - 需要根据实际API调整
                gateway = self.main_engine.get_gateway("CTP")
                if hasattr(gateway, 'td_api') and hasattr(gateway.td_api, 'login_status'):
                    if gateway.td_api.login_status:
                        self.connected = True
                        print("CTP连接成功")
                        return True
                time.sleep(1)

            print("CTP连接超时")
            return False

        except Exception as e:
            print(f"CTP连接失败: {e}")
            return False

    def disconnect(self):
        """断开CTP连接"""
        try:
            self.main_engine.close()
            self.connected = False
            print("CTP连接已断开")
        except Exception as e:
            print(f"断开CTP连接时出错: {e}")

    def subscribe_market_data(self, symbol: str = None):
        """
        订阅行情数据

        Args:
            symbol: 合约代码，默认使用配置的合约
        """
        if symbol is None:
            symbol = self.symbol

        try:
            req = SubscribeRequest(symbol=symbol, exchange="XSGE")
            self.main_engine.subscribe(req, "CTP")
            print(f"已订阅行情: {symbol}")
        except Exception as e:
            print(f"订阅行情失败: {e}")

    def send_order(self, direction: Direction, offset: Offset, price: float, volume: int) -> str:
        """
        发送订单

        Args:
            direction: 买卖方向
            offset: 开平仓
            price: 价格
            volume: 数量

        Returns:
            str: 订单ID
        """
        if not self.connected:
            print("CTP未连接，无法下单")
            return None

        try:
            self.order_count += 1
            order_id = f"order_{self.order_count}"

            req = OrderRequest(
                symbol=self.symbol,
                exchange="XSGE",
                direction=direction,
                offset=offset,
                type=OrderType.LIMIT,
                price=price,
                volume=volume,
                reference=order_id
            )

            vt_order_id = self.main_engine.send_order(req, "CTP")
            if vt_order_id:
                self.active_orders[vt_order_id] = req
                print(f"订单已发送: {direction} {offset} {volume}手 {self.symbol}@{price}")
                return vt_order_id
            else:
                print("订单发送失败")
                return None

        except Exception as e:
            print(f"发送订单失败: {e}")
            return None

    def cancel_order(self, order_id: str) -> bool:
        """
        撤销订单

        Args:
            order_id: 订单ID

        Returns:
            bool: 是否成功
        """
        try:
            self.main_engine.cancel_order(order_id, "CTP")
            print(f"订单撤销请求已发送: {order_id}")
            return True
        except Exception as e:
            print(f"撤销订单失败: {e}")
            return False

    def get_position(self) -> int:
        """
        获取当前持仓

        Returns:
            int: 持仓数量（正数多头，负数空头）
        """
        return self.position

    def get_balance(self) -> float:
        """
        获取账户余额

        Returns:
            float: 账户余额
        """
        try:
            account = self.main_engine.get_account("CTP")
            if account:
                return account.balance
            return 0.0
        except:
            return 0.0

    def open_long(self, price: float, volume: int = 1) -> str:
        """
        开多仓

        Args:
            price: 开仓价格
            volume: 手数

        Returns:
            str: 订单ID
        """
        if self.position != 0:
            print("已有持仓，无法开仓")
            return None

        order_id = self.send_order(Direction.LONG, Offset.OPEN, price, volume)
        if order_id:
            self.position = volume
        return order_id

    def open_short(self, price: float, volume: int = 1) -> str:
        """
        开空仓

        Args:
            price: 开仓价格
            volume: 手数

        Returns:
            str: 订单ID
        """
        if self.position != 0:
            print("已有持仓，无法开仓")
            return None

        order_id = self.send_order(Direction.SHORT, Offset.OPEN, price, volume)
        if order_id:
            self.position = -volume
        return order_id

    def close_position(self, price: float) -> str:
        """
        平仓

        Args:
            price: 平仓价格

        Returns:
            str: 订单ID
        """
        if self.position == 0:
            print("无持仓，无需平仓")
            return None

        if self.position > 0:
            # 平多仓
            direction = Direction.SHORT
            offset = Offset.CLOSE
        else:
            # 平空仓
            direction = Direction.LONG
            offset = Offset.CLOSE

        volume = abs(self.position)
        order_id = self.send_order(direction, offset, price, volume)
        if order_id:
            self.position = 0
        return order_id

    def start(self):
        """启动引擎"""
        self.event_engine.start()
        print("CTP引擎已启动")

    def stop(self):
        """停止引擎"""
        self.event_engine.stop()
        print("CTP引擎已停止")


# 从real_time_trade.py导入配置，使用正确的中文键名和可能有效的认证参数
CTP_CONFIG = {
    "用户名": "253859",  # 替换为实际账号
    "密码": "1qaz@WSX3edc",
    "经纪商代码": "9999",
    "交易服务器": "tcp://182.254.243.31:30011",  # SimNow模拟交易地址
    "行情服务器": "tcp://182.254.243.31:30001",  # SimNow行情地址
    "产品名称": "simnow",  # 更改产品名称为simnow
    "授权编码": "0000000000000000",  # SimNow认证码
    "应用ID": "simnow_client_test",
    "柜台环境": "实盘"  # 设置为实盘
}


def create_ctp_engine() -> CTPEngine:
    """
    创建CTP引擎实例

    Returns:
        CTPEngine: CTP引擎实例
    """
    return CTPEngine(CTP_CONFIG)


# 测试函数
def test_ctp_connection():
    """测试CTP连接"""
    engine = create_ctp_engine()

    # 连接CTP
    if engine.connect():
        print("CTP连接测试成功")

        # 订阅行情
        engine.subscribe_market_data()

        # 启动引擎
        engine.start()

        try:
            # 等待一段时间
            time.sleep(10)

            # 查询账户信息
            balance = engine.get_balance()
            print(f"账户余额: {balance}")

        finally:
            # 停止引擎
            engine.stop()
            engine.disconnect()

    else:
        print("CTP连接测试失败")


if __name__ == "__main__":
    test_ctp_connection()