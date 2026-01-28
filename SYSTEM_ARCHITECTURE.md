# 量化交易系统架构设计文档

## 1. 系统概述

本系统是一个基于VNPy框架的期货量化交易系统，具备以下核心功能：
- 连接CTP接口进行仿真/实盘交易
- 利用历史数据训练价格预测模型
- 基于机器学习模型预测结果执行交易策略
- 完整的风险管理和回测功能

## 2. 系统架构图

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   数据采集层     │    │   数据处理层     │    │   模型训练层     │
│                 │    │                 │    │                 │
│ • CTP数据接口    │───▶│ • 数据清洗      │───▶│ • 特征工程      │
│ • 行情数据存储   │    │ • 数据标准化    │    │ • 模型训练      │
│ • 交易数据记录   │    │ • 数据预处理    │    │ • 模型评估      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                       │
         ▼                        ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   策略执行层     │    │   风险管理层     │    │   模型预测层     │
│                 │    │                 │    │                 │
│ • 策略信号处理   │◀───│ • 风险控制      │    │ • 模型推理      │
│ • 订单管理      │    │ • 资金管理      │    │ • 预测结果处理  │
│ • 仓位管理      │    │ • 异常检测      │    │ • 结果可视化    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                       │
         └────────────────────────┼───────────────────────┘
                                  ▼
                        ┌─────────────────┐
                        │   回测分析层     │
                        │                 │
                        │ • 策略回测      │
                        │ • 性能评估      │
                        │ • 参数优化      │
                        └─────────────────┘
```

## 3. 核心模块设计

### 3.1 数据采集与管理模块 (`data_collector.py`)

负责从CTP接口获取实时行情数据，同时管理历史数据。

```python
from datetime import datetime, timedelta
import pandas as pd
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.database import database_manager
from vnpy_ctp import CtpGateway


class DataCollector:
    """数据采集模块"""
    
    def __init__(self, main_engine):
        self.main_engine = main_engine
        self.database = database_manager
        
    def subscribe_market_data(self, symbols):
        """订阅市场数据"""
        pass
        
    def load_history_data(self, symbol, start_date, end_date, interval=Interval.MINUTE):
        """加载历史数据"""
        pass
        
    def save_tick_data(self, tick):
        """保存实时tick数据"""
        pass
```

### 3.2 数据预处理模块 (`data_processor.py`)

对原始数据进行清洗、标准化和特征工程。

```python
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from ta import add_all_ta_features
from ta.utils import dropna


class DataProcessor:
    """数据预处理模块"""
    
    def __init__(self):
        self.scaler = StandardScaler()
        
    def clean_data(self, df):
        """数据清洗"""
        df = dropna(df)
        # 移除异常值
        return df
        
    def feature_engineering(self, df):
        """特征工程"""
        df = add_all_ta_features(
            df, open="open", high="high", low="low", close="close", volume="volume"
        )
        return df
        
    def normalize_data(self, df):
        """数据标准化"""
        scaled_data = self.scaler.fit_transform(df)
        return pd.DataFrame(scaled_data, columns=df.columns, index=df.index)
```

### 3.3 模型训练模块 (`ml_model.py`)

包含多种机器学习模型，用于价格趋势预测。

```python
import joblib
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error


class PricePredictionModel:
    """价格预测模型"""
    
    def __init__(self, model_type='lstm'):
        self.model_type = model_type
        self.model = None
        
    def build_lstm_model(self, input_shape):
        """构建LSTM模型"""
        model = Sequential([
            LSTM(50, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            LSTM(50, return_sequences=False),
            Dropout(0.2),
            Dense(25),
            Dense(1)
        ])
        model.compile(optimizer='adam', loss='mean_squared_error')
        return model
        
    def train(self, X_train, y_train, X_test, y_test):
        """训练模型"""
        if self.model_type == 'lstm':
            self.model = self.build_lstm_model((X_train.shape[1], X_train.shape[2]))
            self.model.fit(X_train, y_train, batch_size=32, epochs=50, validation_data=(X_test, y_test))
        elif self.model_type == 'random_forest':
            self.model = RandomForestRegressor(n_estimators=100)
            self.model.fit(X_train, y_train)
            
    def predict(self, X):
        """预测"""
        return self.model.predict(X)
        
    def save_model(self, filepath):
        """保存模型"""
        joblib.dump(self.model, filepath)
        
    def load_model(self, filepath):
        """加载模型"""
        self.model = joblib.load(filepath)
```

### 3.4 交易策略模块 (`predictive_trading_strategy.py`)

基于模型预测结果执行交易策略。

```python
from vnpy_ctastrategy import CtaTemplate
from vnpy.trader.object import TickData, BarData, TradeData, OrderData
from vnpy.trader.constant import Direction, Offset, OrderType
import numpy as np


class PredictiveTradingStrategy(CtaTemplate):
    """基于预测模型的交易策略"""
    
    author = "AI Trader"
    
    # 参数定义
    prediction_threshold = 0.02  # 预测阈值
    fixed_size = 1               # 固定手数
    trailing_percent = 0.01      # 跟踪止损百分比
    
    # 变量定义
    prediction_value = 0.0
    last_price = 0.0
    
    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        
        self.model = None
        self.position_manager = PositionManager()
        self.risk_manager = RiskManager()
        
    def on_init(self):
        """策略初始化"""
        self.write_log("策略初始化")
        # 加载预测模型
        from ml_model import PricePredictionModel
        self.model = PricePredictionModel(model_type='lstm')
        self.model.load_model('models/lstm_prediction_model.pkl')
        
        self.load_bar(10)  # 加载最近10根K线数据
        
    def on_start(self):
        """策略启动"""
        self.write_log("策略启动")
        
    def on_stop(self):
        """策略停止"""
        self.write_log("策略停止")
        
    def on_tick(self, tick: TickData):
        """行情推送"""
        self.last_price = tick.last_price
        
        # 获取预测值
        if self.model:
            features = self.prepare_features(tick)
            self.prediction_value = self.model.predict(features)[0]
            
            # 根据预测值执行交易决策
            self.execute_trading_logic()
            
    def prepare_features(self, tick):
        """准备预测所需特征"""
        # 实现特征提取逻辑
        pass
        
    def execute_trading_logic(self):
        """执行交易逻辑"""
        if self.prediction_value > self.prediction_threshold:
            # 预测上涨，开多仓
            if self.pos == 0:
                self.buy(self.bar.close_price + 5, self.fixed_size)
            elif self.pos < 0:
                self.cover(self.bar.close_price + 5, abs(self.pos))  # 先平空仓
                self.buy(self.bar.close_price + 5, self.fixed_size)  # 再开多仓
                
        elif self.prediction_value < -self.prediction_threshold:
            # 预测下跌，开空仓
            if self.pos == 0:
                self.short(self.bar.close_price - 5, self.fixed_size)
            elif self.pos > 0:
                self.sell(self.bar.close_price - 5, self.pos)  # 先平多仓
                self.short(self.bar.close_price - 5, self.fixed_size)  # 再开空仓
```

### 3.5 风险管理模块 (`risk_manager.py`)

控制交易风险，包括资金管理、止损等功能。

```python
from vnpy.trader.object import OrderData, TradeData
from typing import Dict


class RiskManager:
    """风险管理模块"""
    
    def __init__(self, capital_limit=100000, max_position_ratio=0.1):
        self.capital_limit = capital_limit
        self.max_position_ratio = max_position_ratio
        self.current_positions = {}
        self.daily_loss_limit = capital_limit * 0.02  # 每日亏损上限2%
        self.daily_loss = 0
        
    def check_order(self, order: OrderData) -> bool:
        """检查订单是否符合风险控制"""
        # 检查资金是否充足
        required_capital = order.volume * order.price
        if required_capital > self.capital_limit * self.max_position_ratio:
            return False
            
        # 检查当日亏损是否超过限制
        if self.daily_loss > self.daily_loss_limit:
            return False
            
        return True
        
    def update_trade(self, trade: TradeData):
        """更新成交信息"""
        if trade.direction == Direction.LONG:
            self.current_positions[trade.vt_symbol] = self.current_positions.get(trade.vt_symbol, 0) + trade.volume
        else:
            self.current_positions[trade.vt_symbol] = self.current_positions.get(trade.vt_symbol, 0) - trade.volume
            
        # 更新盈亏
        if trade.offset == Offset.CLOSE:
            self.daily_loss -= trade.price * trade.volume
        else:
            self.daily_loss += trade.price * trade.volume
```

### 3.6 回测分析模块 (`backtesting_module.py`)

提供策略回测和性能分析功能。

```python
from vnpy.trader.optimize import OptimizationSetting
from vnpy_ctastrategy.backtesting import BacktestingEngine
import matplotlib.pyplot as plt


class BacktestingModule:
    """回测分析模块"""
    
    def __init__(self):
        self.engine = BacktestingEngine()
        
    def run_backtest(self, strategy_class, setting, vt_symbol, interval, 
                     start, end, rate, slippage, size, pricetick, capital=1000000):
        """运行回测"""
        self.engine.set_parameters(
            vt_symbol=vt_symbol,
            interval=interval,
            start=start,
            end=end,
            rate=rate,
            slippage=slippage,
            size=size,
            pricetick=pricetick,
            capital=capital,
        )
        
        self.engine.add_strategy(strategy_class, setting)
        self.engine.run_backtesting()
        df = self.engine.calculate_result()
        return df
        
    def optimize_parameters(self, strategy_class, setting: OptimizationSetting, 
                           vt_symbol, interval, start, end, rate, slippage, size, pricetick):
        """参数优化"""
        self.engine.set_parameters(
            vt_symbol=vt_symbol,
            interval=interval,
            start=start,
            end=end,
            rate=rate,
            slippage=slippage,
            size=size,
            pricetick=pricetick,
        )
        
        self.engine.add_strategy(strategy_class, {})
        result = self.engine.run_optimization(setting)
        return result
        
    def plot_results(self, df):
        """绘制回测结果图表"""
        fig, axes = plt.subplots(3, 1, figsize=(15, 10))
        
        # 净值曲线
        axes[0].plot(df['balance'], label='Balance')
        axes[0].set_title('Account Balance')
        axes[0].legend()
        
        # 累计收益率
        returns = df['net_pnl'].dropna() / df['balance'].shift(1).dropna()
        cumulative_returns = (1 + returns).cumprod()
        axes[1].plot(cumulative_returns, label='Cumulative Returns')
        axes[1].set_title('Cumulative Returns')
        axes[1].legend()
        
        # 回撤
        running_max = df['balance'].rolling(min_periods=1, window=len(df)).max()
        drawdown = (df['balance'] - running_max) / running_max
        axes[2].plot(drawdown, label='Drawdown', color='red')
        axes[2].set_title('Drawdown')
        axes[2].legend()
        
        plt.tight_layout()
        plt.show()
```

## 4. 系统启动模块 (`ai_trading_system.py`)

整合所有模块，提供统一入口。

```python
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp
from vnpy_ctp import CtpGateway
from vnpy_ctastrategy import CtaStrategyApp
from data_collector import DataCollector
from ml_model import PricePredictionModel
from backtesting_module import BacktestingModule
import sys
import os


class AITradingSystem:
    """AI量化交易系统主类"""
    
    def __init__(self):
        self.event_engine = EventEngine()
        self.main_engine = MainEngine(self.event_engine)
        self.data_collector = DataCollector(self.main_engine)
        self.backtesting_module = BacktestingModule()
        
    def connect_gateway(self, gateway_name, setting):
        """连接交易网关"""
        if gateway_name.lower() == 'ctp':
            self.main_engine.add_gateway(CtpGateway)
            self.main_engine.connect(setting, "CTP")
        # 可扩展其他网关如：SimNow, Femas等
        
    def train_model(self, symbol, start_date, end_date):
        """训练预测模型"""
        # 1. 获取历史数据
        data = self.data_collector.load_history_data(symbol, start_date, end_date)
        
        # 2. 数据预处理
        from data_processor import DataProcessor
        processor = DataProcessor()
        processed_data = processor.clean_data(data)
        features = processor.feature_engineering(processed_data)
        normalized_data = processor.normalize_data(features)
        
        # 3. 构建训练集
        X, y = self.prepare_training_data(normalized_data)
        
        # 4. 分割训练/测试集
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        # 5. 训练模型
        model = PricePredictionModel(model_type='lstm')
        model.train(X_train, y_train, X_test, y_test)
        
        # 6. 保存模型
        model.save_model(f'models/{symbol}_prediction_model.pkl')
        
    def prepare_training_data(self, data):
        """准备训练数据"""
        # 实现数据转换逻辑，将时间序列数据转换为监督学习格式
        pass
        
    def start_trading(self, strategy_class, setting):
        """启动实盘交易"""
        cta_engine = self.main_engine.get_engine("CtaStrategy")
        cta_engine.add_strategy(strategy_class, setting)
        cta_engine.start_strategy(strategy_class.__name__)
        
    def run_ui(self):
        """运行UI界面"""
        qapp = create_qapp()
        main_window = MainWindow(self.main_engine, self.event_engine)
        main_window.showMaximized()
        qapp.exec_()
        
    def run_backtesting(self, strategy_class, setting, **kwargs):
        """运行回测"""
        return self.backtesting_module.run_backtest(strategy_class, setting, **kwargs)


def main():
    """系统主入口"""
    system = AITradingSystem()
    
    # 选择运行模式
    mode = input("请选择运行模式 (1: 实盘交易, 2: 回测, 3: 模型训练): ")
    
    if mode == "1":
        # 连接到CTP网关
        from settings.ctp_setting import SETTING
        system.connect_gateway("ctp", SETTING)
        
        # 启动交易策略
        from predictive_trading_strategy import PredictiveTradingStrategy
        system.start_trading(PredictiveTradingStrategy, {"prediction_threshold": 0.02})
        
        # 启动UI
        system.run_ui()
        
    elif mode == "2":
        # 运行回测
        from predictive_trading_strategy import PredictiveTradingStrategy
        result = system.run_backtesting(
            strategy_class=PredictiveTradingStrategy,
            setting={"prediction_threshold": 0.02},
            vt_symbol="rb2105.SHFE",
            interval="1m",
            start="2021-01-01",
            end="2021-06-01",
            rate=0.00005,
            slippage=1,
            size=10,
            pricetick=1,
            capital=1000000
        )
        print(result)
        
    elif mode == "3":
        # 训练模型
        system.train_model(
            symbol="rb2105.SHFE",
            start_date="2020-01-01",
            end_date="2021-01-01"
        )
        print("模型训练完成")


if __name__ == "__main__":
    main()
```

## 5. 系统配置文件

### 5.1 环境配置 (`config.py`)

```python
import os

# 项目路径配置
PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(PROJECT_PATH, "data")
MODEL_PATH = os.path.join(PROJECT_PATH, "models")
LOG_PATH = os.path.join(PROJECT_PATH, "logs")

# 数据库配置
DATABASE_CONFIG = {
    "database.name": "sqlite",
    "database.database": "database.db",
    "database.host": "",
    "database.port": 0,
    "database.username": "",
    "database.password": ""
}

# 模型配置
MODEL_CONFIG = {
    "sequence_length": 60,  # 输入序列长度
    "features_count": 30,   # 特征数量
    "prediction_horizon": 5, # 预测未来几步
    "model_type": "lstm",
    "epochs": 100,
    "batch_size": 32
}

# 风险管理配置
RISK_CONFIG = {
    "max_daily_loss_rate": 0.02,  # 最大日亏损率
    "max_position_ratio": 0.1,    # 最大仓位比例
    "max_single_trade_ratio": 0.05  # 单次交易最大资金比例
}
```

### 5.2 依赖文件 (`requirements.txt`)

```
vnpy>=3.0.0
vnpy_ctp>=3.0.0
vnpy_ctastrategy>=3.0.0
pandas>=1.3.0
numpy>=1.20.0
scikit-learn>=1.0.0
tensorflow>=2.6.0
matplotlib>=3.4.0
ta>=0.7.0
joblib>=1.1.0
seaborn>=0.11.0
```

## 6. 部署和运维

### 6.1 系统监控 (`monitor.py`)

```python
import psutil
import time
from datetime import datetime
import smtplib
from email.mime.text import MIMEText


class SystemMonitor:
    """系统监控模块"""
    
    def __init__(self, alert_email=None):
        self.alert_email = alert_email
        
    def check_resources(self):
        """检查系统资源"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage('/').percent
        
        if cpu_percent > 90 or memory_percent > 90 or disk_percent > 90:
            self.send_alert(f"系统资源告警: CPU={cpu_percent}%, Memory={memory_percent}%, Disk={disk_percent}%")
            
    def send_alert(self, message):
        """发送告警邮件"""
        if self.alert_email:
            msg = MIMEText(message)
            msg['Subject'] = '量化系统告警'
            msg['From'] = 'system@quant.com'
            msg['To'] = self.alert_email
            
            # 发送邮件
            # 实现邮件发送逻辑
            pass
```

### 6.2 自动重启脚本 (`restart_script.py`)

```python
import subprocess
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def monitor_and_restart():
    """监控并重启系统"""
    while True:
        try:
            # 检查进程是否存活
            result = subprocess.run(['pgrep', '-f', 'ai_trading_system'], capture_output=True, text=True)
            if result.returncode != 0:
                # 如果进程不存在，重新启动
                logging.info("系统进程未运行，正在重启...")
                subprocess.Popen(['python', 'ai_trading_system.py'])
                logging.info("系统已重启")
            else:
                logging.info("系统运行正常")
                
        except Exception as e:
            logging.error(f"监控出错: {e}")
            
        time.sleep(60)  # 每分钟检查一次


if __name__ == "__main__":
    monitor_and_restart()
```

## 7. 安全考虑

1. **敏感信息保护**：将API密钥、账户密码等敏感信息存储在加密环境中
2. **访问控制**：限制对系统的访问权限
3. **审计日志**：记录所有关键操作
4. **异常处理**：完善的异常处理机制

## 8. 性能优化

1. **数据缓存**：使用Redis缓存常用数据
2. **异步处理**：对非关键路径的操作采用异步处理
3. **模型压缩**：对ML模型进行量化和压缩以提高推理速度
4. **数据库优化**：对数据库查询进行索引优化

这个设计提供了完整的量化交易系统架构，包括数据采集、模型训练、预测、交易执行、风险管理、回测分析等功能模块，支持仿真和实盘两种环境。系统具有良好的扩展性和安全性，可以根据实际需要进行调整和优化。