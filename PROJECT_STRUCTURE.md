# 期货智能交易系统 - 项目结构

## 项目概览

这是一个基于机器学习算法的期货行情预测与智能交易系统，能够预测期货价格走势并自动执行交易策略。

## 当前目录结构

```
futures-trading-rl/
├── README.md                 # 项目说明文档
├── PROJECT_STRUCTURE.md      # 项目结构说明（本文档）
├── SYSTEM_ARCHITECTURE.md    # 系统架构设计文档
├── CLEANUP_LOG.md           # 清理和重构日志
├── requirements.txt         # 项目依赖
├── run_system.py            # 系统统一入口
├── setup_env.py             # 环境初始化脚本
├── smart_auto_trading.py    # 主交易程序
├── auto_trading_system.py   # 自动交易系统
├── trading_system.py        # 综合交易系统
├── train_rb2605_model.py    # 模型训练脚本
├── simple_auto_trading.py   # 简化版自动交易系统
├── data/                    # 历史数据目录
│   ├── rb_1min_*           # 螺纹钢1分钟K线数据
│   ├── 沪铜_1min_*         # 沪铜1分钟K线数据
│   └── 沪镍_1min_*         # 沪镍1分钟K线数据
├── models/                  # 训练好的模型目录
│   └── *_prediction_model* # 预测模型文件
├── settings/                # 交易配置目录
│   ├── simnow_setting_one.json    # SimNow配置文件1
│   ├── simnow_setting_two.json    # SimNow配置文件2
│   └── simnow_setting_template.json # SimNow配置模板
├── src/                     # 源代码主目录
│   ├── account/             # 账户管理模块
│   │   └── account.py       # 账户管理实现
│   ├── ctp/                 # CTP接口模块
│   │   ├── main.py          # CTP主入口
│   │   └── run.py           # CTP运行脚本
│   ├── data/                # 数据处理模块
│   │   ├── data_collector.py # 数据收集器
│   │   ├── data_processor.py # 数据处理器
│   │   └── features/         # 特征工程
│   │       └── feature_pipeline.py # 特征管道
│   ├── market_data/         # 行情数据模块
│   │   └── market_data_service.py # 行情数据服务
│   ├── models/              # 机器学习模型模块
│   │   ├── base_model.py    # 基础模型类
│   │   ├── lstm_model.py    # LSTM模型
│   │   ├── ml_model.py      # 机器学习模型
│   │   └── train_and_backtest.py # 训练和回测
│   ├── risk_management/     # 风险管理模块
│   │   ├── daily_drawdown_risk.py # 日回撤风险管理
│   │   └── risk_manager.py  # 风险管理器
│   ├── strategies/          # 交易策略模块
│   │   ├── hybrid_trend_scalp_strategy.py # 趋势+剥头皮策略
│   │   ├── model_cta_strategy.py # 模型CTA策略
│   │   ├── predictive_trading_strategy.py # 预测交易策略
│   │   ├── scalping_orderflow_strategy.py # 订单流剥头皮策略
│   │   └── simple_test_strategy.py # 简单测试策略
│   ├── trading/             # 交易模块
│   │   └── contract_specs.py # 合约规格定义
│   ├── utils/               # 工具模块
│   │   ├── ai_trading_system.py # AI交易系统
│   │   └── config.py        # 配置管理
│   └── trading_system.py    # 交易系统主类
├── logs/                    # 日志目录
└── venv/                    # Python虚拟环境目录
```

## 主要模块说明

### 1. 核心交易模块
- **smart_auto_trading.py**: 主要的自动交易系统，集成了预测模型和交易执行
- **auto_trading_system.py**: 自动交易系统，专注于多合约交易
- **trading_system.py**: 综合交易系统，包含模型训练和策略执行

### 2. 机器学习模块 (src/models/)
- **ml_model.py**: 机器学习模型定义和训练
- **lstm_model.py**: LSTM神经网络模型
- **train_and_backtest.py**: 模型训练和回测功能

### 3. 风险管理模块 (src/risk_management/)
- **risk_manager.py**: 综合风险管理器
- **daily_drawdown_risk.py**: 日回撤风险控制

### 4. 交易策略模块 (src/strategies/)
- **predictive_trading_strategy.py**: 基于预测的交易策略
- **hybrid_trend_scalp_strategy.py**: 趋势+剥头皮混合策略

### 5. 数据处理模块 (src/data/)
- **data_collector.py**: 历史数据收集
- **data_processor.py**: 数据预处理和特征工程

## 系统运行入口

### 1. 统一入口
```bash
python run_system.py <command>
```

支持的命令:
- `setup`: 环境初始化
- `training`: 模型训练
- `trading`: 智能交易系统
- `backtesting`: 回测系统
- `comprehensive`: 综合交易系统
- `ai_system`: AI交易系统

### 2. 直接运行
各个模块也可以单独运行:
```bash
python smart_auto_trading.py  # 运行主交易系统
python train_rb2605_model.py  # 训练模型
python setup_env.py           # 初始化环境
```

## 配置文件说明

- **settings/simnow_setting_template.json**: SimNow账户配置模板
- **settings/simnow_setting_one.json**: SimNow账户配置文件1
- **settings/simnow_setting_two.json**: SimNow账户配置文件2

## 模型文件说明

- **models/** 目录存放训练好的预测模型
- 模型文件格式: `{交易所}_{合约}_prediction_model.{扩展名}`
- 包括LSTM、随机森林、SVM等多种模型类型