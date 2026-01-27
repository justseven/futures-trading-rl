# 期货行情预测与交易系统

这是一个基于强化学习技术的期货行情预测与交易系统，使用vnpy框架接入行情与交易接口，结合Stable-Baselines3构建强化学习模型，在自定义Gym环境中训练交易策略，并支持回测与实时模拟交易。

## 项目概述

本项目旨在利用强化学习技术对期货行情进行建模与交易策略训练，结合真实行情数据和模拟环境实现交易决策优化。

- 目标用户: 量化交易研究人员、算法交易开发者、期货市场分析人员
- 核心功能: 从历史K线数据中提取有效特征进行趋势预测，构建适合期货交易的强化学习环境，实现回测与实盘交易的一致性

## 系统功能

- **数据获取**: 通过[data/getKLine.py](file:///f:/期货行情预测/data/getKLine.py)获取K线数据
- **指标计算**: 在[indicators.py](file:///f:/期货行情预测/indicators.py)中实现技术指标（如MA、RSI等）
- **强化学习环境**: [env_trade.py](file:///f:/期货行情预测/env_trade.py)封装符合gymnasium规范的交易环境
- **策略训练**: [train_trade.py](file:///f:/期货行情预测/train_trade.py)使用PPO等算法训练交易模型
- **回测系统**: [backtest_trade.py](file:///f:/期货行情预测/backtest_trade.py)执行离线策略回测
- **实时交易**: [real_time_trade.py](file:///f:/期货行情预测/real_time_trade.py)与[sim_real_time_trade.py](file:///f:/期货行情预测/sim_real_time_trade.py)支持实时或模拟交易
- **CTP交易接口**: 通过[ctp_engine.py](file:///f:/期货行情预测/ctp_engine.py)连接国内期货市场交易通道
- **账户管理**: [account.py](file:///f:/期货行情预测/account.py)处理资金、持仓等账户状态
- **入场规则**: [entry_rules.py](file:///f:/期货行情预测/entry_rules.py)定义基础交易信号逻辑

## 技术架构

- **机器学习框架**: PyTorch + Stable-Baselines3
- **数据处理**: numpy, pandas
- **可视化**: matplotlib, tensorboard
- **交易框架**: vnpy
- **环境**: gymnasium (替代原gym)

## 安装与运行

1. 克隆项目:
   ```bash
   git clone https://github.com/yourusername/futures-prediction.git
   ```

2. 安装依赖:
   ```bash
   pip install -r requirements.txt
   ```

3. 运行训练:
   ```bash
   python train_trade.py
   ```

4. 运行回测:
   ```bash
   python backtest_trade.py
   ```

5. 连接到CTP:
   ```bash
   python ctp_engine.py
   ```

## CTP连接配置

项目中包含了CTP连接配置的详细说明，请参阅[CTP_CONNECTION_GUIDE.md](file:///f:/期货行情预测/CTP_CONNECTION_GUIDE.md)。

## 文件结构

```
.
├── data
│   └── getKLine.py
├── account.py
├── backtest_trade.py
├── ctp_engine.py
├── entry_rules.py
├── env_trade.py
├── indicators.py
├── real_time_trade.py
├── sim_real_time_trade.py
├── test_ctp_connection.py
├── train_trade.py
├── CTP_CONNECTION_GUIDE.md
├── connect_ctp.py
├── debug_ctp_connection.py
├── fixed_ctp_connection.py
├── final_ctp_connection.py
├── corrected_ctp_config.py
├── complete_ctp_config.py
└── README.md
```

## 注意事项

- 生产部署时需保护API密钥与交易密码
- CTP账户信息应加密存储
- 建议先使用模拟账户测试所有功能