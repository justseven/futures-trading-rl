# 期货行情预测与智能交易系统

这是一个基于机器学习算法的期货行情预测与智能交易系统，能够预测期货价格走势并自动执行交易策略。

## 功能特性

1. **数据获取与处理**  
   - 从SimNow模拟交易环境获取实时行情数据
   - 支持多种期货品种（螺纹钢rb、阴极铜cu、镍ni等）
   - 实现K线数据存储和处理

2. **价格预测模型**  
   - 基于LSTM神经网络的时序预测模型
   - 使用60个时间步长的历史数据预测30分钟后的价格
   - 技术指标增强：RSI、MACD、布林带、移动平均线等
   - 支持多模型训练（LSTM、GRU、CNN-LSTM）

3. **智能交易策略**  
   - 基于预测结果的自动化交易执行
   - 实时行情监控与交易信号生成
   - 支持多品种期货交易

4. **风险管理**  
   - 保证金计算与风险控制
   - 手续费计算与盈利评估
   - 最大持仓限制
   - 止损止盈机制

5. **系统集成**  
   - 与vn.py交易框架集成
   - SimNow模拟交易环境支持
   - 自动化模型训练与部署

## 新增功能：手续费和保证金计算

系统现在能够：

- **保证金计算**：根据合约规格计算所需保证金，确保账户资金充足
- **手续费计算**：精确计算开仓和平仓手续费，区分不同合约品种的费率
- **盈利能力评估**：综合考虑价格变动、手续费和保证金要求，仅在预测有利可图时执行交易
- **套利机会识别**：基于预测结果和成本计算，发现真正的套利机会

## 系统架构

```
├── README.md                 # 项目说明文档
├── PROJECT_STRUCTURE.md      # 项目结构说明
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
│   ├── ctp/                 # CTP接口模块
│   ├── data/                # 数据处理模块
│   ├── market_data/         # 行情数据模块
│   ├── models/              # 机器学习模型模块
│   ├── risk_management/     # 风险管理模块
│   ├── strategies/          # 交易策略模块
│   ├── trading/             # 交易模块
│   └── utils/               # 工具模块
├── logs/                    # 日志目录
└── venv/                    # Python虚拟环境目录
```

## 安全说明

⚠️ **重要**：为保护您的账户安全，本系统不再使用硬编码的账户信息。所有敏感信息（如用户名、密码）都必须通过配置文件管理。

## 安装与配置

1. **Python环境**  
   - Python 3.8+
   - 使用虚拟环境推荐

2. **依赖安装**
   ```bash
   pip install -r requirements.txt
   ```

3. **环境初始化**  
   运行环境初始化脚本，自动创建目录结构并引导您配置SimNow账户：
   ```bash
   python setup_env.py
   ```

4. **系统运行**  
   使用统一入口运行不同功能：
   ```bash
   # 查看所有命令
   python run_system.py all_commands
   
   # 初始化环境
   python run_system.py setup
   
   # 运行智能交易系统
   python run_system.py trading
   
   # 训练模型
   python run_system.py training
   
   # 运行回测
   python run_system.py backtesting
   ```

## 使用方法

### 1. 环境初始化
```bash
python run_system.py setup
```

### 2. 模型训练
```bash
python run_system.py training
```

### 3. 运行交易系统
```bash
python run_system.py trading
```

### 4. 运行回测
```bash
python run_system.py backtesting
```

## 重构和改进

### 1. 安全性改进
- 移除了所有硬编码的账户信息
- 改为从配置文件动态加载账户信息
- 添加了占位符检测，防止意外使用模板值

### 2. 代码结构改进
- 统一了配置文件加载逻辑
- 改进了错误处理机制
- 增强了系统健壮性

### 3. 用户体验改进
- 创建了统一的系统入口(run_system.py)
- 改进了命令行交互
- 增加了更多有用的提示信息

### 4. 项目结构优化
- 删除了无关的C++ API文件
- 移除了测试和临时文件
- 添加了清晰的项目结构文档

## 注意事项

1. **交易时间**：系统仅在期货交易时间内运行（日盘和夜盘）
2. **资金管理**：合理设置投资金额，控制风险
3. **网络连接**：确保稳定网络连接，避免交易中断
4. **模型更新**：定期更新预测模型以适应市场变化

## 风险提示

期货交易具有高风险，请在使用本系统前充分了解相关风险，并仅投入您能承受损失的资金。

## 许可证

本项目仅供学习和研究使用，不得用于商业目的。