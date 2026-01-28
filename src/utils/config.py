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
    "sequence_length": 60,           # 输入序列长度
    "features_count": 20,            # 特征数量
    "prediction_horizon": 5,         # 预测未来几步
    "model_type": "lstm",            # 默认模型类型
    "epochs": 100,                   # 训练轮数
    "batch_size": 32,                # 批次大小
    "learning_rate": 0.001,          # 学习率
    "validation_split": 0.2          # 验证集比例
}

# 风险管理配置
RISK_CONFIG = {
    "max_daily_loss_rate": 0.02,     # 最大日亏损率
    "max_position_ratio": 0.1,       # 最大仓位比例
    "max_single_trade_ratio": 0.05,  # 单次交易最大资金比例
    "max_drawdown": 0.15,            # 最大回撤
    "max_leverage": 10,              # 最大杠杆
    "stop_loss_pct": 0.05,           # 止损比例
    "take_profit_pct": 0.1           # 止盈比例
}

# 交易策略配置
STRATEGY_CONFIG = {
    "prediction_threshold": 0.01,    # 预测阈值
    "fixed_size": 1,                 # 固定手数
    "trailing_percent": 0.8,         # 跟踪止损百分比
    "risk_reward_ratio": 2.0,        # 风险收益比
    "max_position_percent": 0.2,     # 最大仓位占比
    "min_volatility": 0.01,          # 最小波动率阈值
    "max_volatility": 0.05           # 最大波动率阈值
}

# 数据配置
DATA_CONFIG = {
    "default_interval": "1m",        # 默认数据周期
    "history_days": 365,             # 历史数据天数
    "min_data_points": 1000,         # 最少数据点数
    "resample_rules": {              # 重采样规则
        "1m": "1T",
        "5m": "5T",
        "15m": "15T",
        "30m": "30T",
        "1h": "1H",
        "1d": "1D"
    }
}

# 回测配置
BACKTEST_CONFIG = {
    "initial_capital": 100000,       # 初始资金
    "slippage": 1,                   # 滑点
    "rate": 0.00005,                 # 手续费率
    "size": 10,                      # 合约乘数
    "pricetick": 1,                  # 最小价格变动
    "use_commission": True,          # 是否使用手续费
    "use_slippage": True,            # 是否使用滑点
    "use_liquidity": True            # 是否考虑流动性
}

# 系统配置
SYSTEM_CONFIG = {
    "enable_logging": True,          # 启用日志
    "log_level": "INFO",             # 日志级别
    "enable_monitoring": True,       # 启用监控
    "monitor_interval": 60,          # 监控间隔(秒)
    "backup_enabled": True,          # 启用备份
    "backup_interval": 3600,         # 备份间隔(秒)
    "max_workers": 4                 # 最大工作线程数
}