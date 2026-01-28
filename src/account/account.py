"""
账户模块
用于管理交易账户信息，包括初始资金、仓位、盈亏等信息
"""
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class PositionDirection(Enum):
    """持仓方向枚举"""
    LONG = "多"
    SHORT = "空"


@dataclass
class Position:
    """持仓信息"""
    symbol: str  # 合约代码
    direction: PositionDirection  # 持仓方向
    volume: int  # 持仓数量
    price: float  # 开仓均价
    pnl: float = 0.0  # 持仓盈亏
    frozen: int = 0  # 冻结数量

    def update_pnl(self, current_price: float) -> float:
        """更新持仓盈亏"""
        if self.direction == PositionDirection.LONG:
            self.pnl = (current_price - self.price) * self.volume
        else:
            self.pnl = (self.price - current_price) * self.volume
        return self.pnl


@dataclass
class AccountInfo:
    """账户信息"""
    account_id: str  # 账户ID
    initial_capital: float  # 初始资金
    balance: float  # 当前余额
    available: float  # 可用资金
    frozen: float  # 冻结资金
    margin: float  # 保证金
    commission: float = 0.0  # 手续费
    timestamp: str = ""  # 更新时间

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class AccountManager:
    """账户管理器"""

    def __init__(self, account_id: str, initial_capital: float):
        """
        初始化账户管理器
        
        :param account_id: 账户ID
        :param initial_capital: 初始资金
        """
        self.account_id = account_id
        self.initial_capital = initial_capital
        self.balance = initial_capital  # 当前余额
        self.available = initial_capital  # 可用资金
        self.frozen = 0.0  # 冻结资金
        self.margin = 0.0  # 保证金
        self.commission = 0.0  # 总手续费
        self.positions: Dict[str, Position] = {}  # 持仓信息
        self.trade_records: List[Dict] = []  # 交易记录
        self.order_records: List[Dict] = []  # 委托记录
        self.update_time = datetime.now()

    def get_account_info(self) -> AccountInfo:
        """获取账户信息"""
        return AccountInfo(
            account_id=self.account_id,
            initial_capital=self.initial_capital,
            balance=self.balance,
            available=self.available,
            frozen=self.frozen,
            margin=self.margin,
            commission=self.commission
        )

    def update_balance(self, amount: float):
        """更新账户余额"""
        self.balance += amount
        self.available += amount

    def calculate_position_pnl(self, symbol: str, current_price: float) -> float:
        """计算指定合约的持仓盈亏"""
        position_key = f"{symbol}_{PositionDirection.LONG.value}"
        if position_key in self.positions:
            return self.positions[position_key].update_pnl(current_price)
        
        position_key = f"{symbol}_{PositionDirection.SHORT.value}"
        if position_key in self.positions:
            return self.positions[position_key].update_pnl(current_price)
        
        return 0.0

    def calculate_total_pnl(self, market_prices: Dict[str, float]) -> float:
        """计算总浮动盈亏"""
        total_pnl = 0.0
        for position in self.positions.values():
            symbol = position.symbol
            if symbol in market_prices:
                total_pnl += position.update_pnl(market_prices[symbol])
        return total_pnl

    def calculate_total_value(self, market_prices: Dict[str, float]) -> float:
        """计算账户总价值（余额+浮动盈亏）"""
        total_pnl = self.calculate_total_pnl(market_prices)
        return self.balance + total_pnl

    def update_position(self, symbol: str, direction: PositionDirection, volume: int, 
                       price: float, offset_flag: str = "开仓"):
        """
        更新持仓信息
        
        :param symbol: 合约代码
        :param direction: 持仓方向
        :param volume: 数量
        :param price: 价格
        :param offset_flag: 开平标志
        """
        position_key = f"{symbol}_{direction.value}"
        
        if offset_flag == "开仓":
            # 开仓
            if position_key in self.positions:
                # 已有持仓，更新平均价格和数量
                old_pos = self.positions[position_key]
                total_volume = old_pos.volume + volume
                total_cost = old_pos.price * old_pos.volume + price * volume
                avg_price = total_cost / total_volume
                old_pos.volume = total_volume
                old_pos.price = avg_price
            else:
                # 新建持仓
                self.positions[position_key] = Position(
                    symbol=symbol,
                    direction=direction,
                    volume=volume,
                    price=price
                )
        else:
            # 平仓
            if position_key in self.positions:
                pos = self.positions[position_key]
                if pos.volume >= volume:
                    pos.volume -= volume
                    if pos.volume == 0:
                        del self.positions[position_key]
        
        # 更新账户资金
        if offset_flag == "开仓":
            # 开仓会占用保证金
            margin_required = price * volume * 0.1  # 简化的保证金计算
            self.margin += margin_required
            self.available -= margin_required
        else:
            # 平仓释放保证金
            margin_released = price * volume * 0.1
            self.margin -= margin_released
            self.available += margin_released

    def record_trade(self, symbol: str, direction: str, volume: int, price: float, 
                     trade_time: str, commission: float = 0.0):
        """记录成交信息"""
        trade_record = {
            "symbol": symbol,
            "direction": direction,
            "volume": volume,
            "price": price,
            "trade_time": trade_time,
            "commission": commission
        }
        self.trade_records.append(trade_record)
        
        # 更新手续费
        self.commission += commission
        
        # 更新可用资金
        self.available -= commission

    def record_order(self, symbol: str, direction: str, volume: int, price: float, 
                     status: str, order_time: str, order_id: str = ""):
        """记录委托信息"""
        order_record = {
            "order_id": order_id,
            "symbol": symbol,
            "direction": direction,
            "volume": volume,
            "price": price,
            "status": status,
            "order_time": order_time
        }
        self.order_records.append(order_record)

    def get_position(self, symbol: str, direction: PositionDirection) -> Optional[Position]:
        """获取指定合约和方向的持仓"""
        position_key = f"{symbol}_{direction.value}"
        return self.positions.get(position_key)

    def get_all_positions(self) -> Dict[str, Position]:
        """获取所有持仓"""
        return self.positions

    def get_position_by_symbol(self, symbol: str) -> List[Position]:
        """获取指定合约的所有持仓（多空）"""
        result = []
        for key, position in self.positions.items():
            if position.symbol == symbol:
                result.append(position)
        return result

    def calculate_position_pnl_by_symbol(self, symbol: str, current_price: float) -> float:
        """计算指定合约的总盈亏（多空合并）"""
        positions = self.get_position_by_symbol(symbol)
        total_pnl = 0.0
        for pos in positions:
            total_pnl += pos.update_pnl(current_price)
        return total_pnl

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "account_id": self.account_id,
            "initial_capital": self.initial_capital,
            "balance": self.balance,
            "available": self.available,
            "frozen": self.frozen,
            "margin": self.margin,
            "commission": self.commission,
            "positions": {k: asdict(v) for k, v in self.positions.items()},
            "update_time": self.update_time.isoformat(),
            "trade_records_count": len(self.trade_records),
            "order_records_count": len(self.order_records)
        }

    def save_to_file(self, filepath: str):
        """保存账户信息到文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str):
        """从文件加载账户信息"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 创建账户实例
        account = cls(
            account_id=data["account_id"],
            initial_capital=data["initial_capital"]
        )
        
        # 恢复账户状态
        account.balance = data["balance"]
        account.available = data["available"]
        account.frozen = data["frozen"]
        account.margin = data["margin"]
        account.commission = data["commission"]
        account.update_time = datetime.fromisoformat(data["update_time"])
        
        # 恢复持仓信息
        for key, pos_data in data["positions"].items():
            direction_enum = PositionDirection(pos_data["direction"])
            position = Position(
                symbol=pos_data["symbol"],
                direction=direction_enum,
                volume=pos_data["volume"],
                price=pos_data["price"],
                pnl=pos_data["pnl"],
                frozen=pos_data["frozen"]
            )
            account.positions[key] = position
        
        return account

    def get_performance_metrics(self, market_prices: Dict[str, float]) -> Dict:
        """获取绩效指标"""
        total_pnl = self.calculate_total_pnl(market_prices)
        total_value = self.calculate_total_value(market_prices)
        
        # 计算收益率
        if self.initial_capital != 0:
            return_rate = (total_value - self.initial_capital) / self.initial_capital * 100
        else:
            return_rate = 0.0
        
        # 持仓详情
        position_details = []
        for pos in self.positions.values():
            current_price = market_prices.get(pos.symbol, pos.price)
            position_details.append({
                "symbol": pos.symbol,
                "direction": pos.direction.value,
                "volume": pos.volume,
                "avg_price": pos.price,
                "current_price": current_price,
                "pnl": pos.update_pnl(current_price),
                "pnl_rate": ((current_price - pos.price) / pos.price * 100) if pos.price != 0 else 0
            })
        
        return {
            "account_id": self.account_id,
            "initial_capital": self.initial_capital,
            "current_balance": self.balance,
            "total_value": total_value,
            "total_pnl": total_pnl,
            "return_rate": return_rate,
            "margin": self.margin,
            "available": self.available,
            "commission": self.commission,
            "position_count": len(self.positions),
            "position_details": position_details
        }


# 示例使用
if __name__ == "__main__":
    # 创建账户
    account = AccountManager("test_account", 100000.0)
    
    # 添加持仓
    account.update_position("rb2602", PositionDirection.LONG, 2, 4000.0, "开仓")
    
    # 记录成交
    account.record_trade("rb2602", "BUY", 2, 4000.0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 10.0)
    
    # 市场价格
    market_prices = {"rb2602": 4050.0}
    
    # 获取绩效指标
    metrics = account.get_performance_metrics(market_prices)
    print("账户绩效指标:", json.dumps(metrics, ensure_ascii=False, indent=2))
    
    # 保存到文件
    account.save_to_file("test_account.json")
    print("账户信息已保存到 test_account.json")
    
    # 从文件加载
    loaded_account = AccountManager.load_from_file("test_account.json")
    print(f"从文件加载的账户ID: {loaded_account.account_id}")