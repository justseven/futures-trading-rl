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
├── data/                     # 历史数据存储
│   ├── rb_1min_*           # 螺纹钢1分钟K线数据
│   ├── 沪铜_1min_*         # 沪铜1分钟K线数据
│   └── 沪镍_1min_*         # 沪镍1分钟K线数据
├── models/                   # 训练好的模型
│   └── SHFE_rb_*_prediction_model.keras
├── src/                      # 源代码
│   ├── market_data/          # 行情数据服务
│   ├── models/               # 机器学习模型
│   ├── risk_management/      # 风险管理模块
│   └── trading/              # 交易相关模块
│       └── contract_specs.py # 合约规格配置
├── settings/                 # 交易配置
│   ├── simnow_setting_one.json    # SimNow实盘交易配置（用户创建）
│   ├── simnow_setting_two.json    # SimNow测试配置（用户创建）
│   └── simnow_setting_template.json # SimNow配置模板
├── smart_auto_trading.py     # 主交易程序
├── setup_env.py              # 环境初始化脚本
├── train_rb2605_model.py     # 模型训练脚本
└── README.md
```

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

4. **手动配置（可选）**  
   如果您选择手动配置，请按以下步骤操作：
   - 访问 https://www.simnow.com.cn/
   - 注册模拟交易账户
   - 运行环境初始化脚本：`python setup_env.py`
   - 脚本将引导您完成账户配置
   
   或者手动操作：
   1. 复制模板文件: `cp settings/simnow_setting_template.json settings/simnow_setting_one.json`
   2. 编辑 `settings/simnow_setting_one.json`，填入您的真实账户信息

5. **数据准备**  
   - 确保 `data/` 目录下有对应品种的历史数据
   - 数据格式：CSV，包含时间、开盘价、最高价、最低价、收盘价、成交量

## 使用方法

1. **训练模型**
   ```bash
   python train_rb2605_model.py
   ```

2. **运行智能交易系统**
   ```bash
   python smart_auto_trading.py
   ```

3. **系统运行注意事项**
   - 确保在交易时间内运行
   - 账户资金充足以覆盖保证金需求
   - 系统会根据预测结果和成本分析自动执行交易

## 安全提醒

- **请确保您的 `.gitignore` 文件已正确配置，避免提交包含敏感信息的配置文件**
- **不要在公共仓库中分享包含真实凭证的配置文件**
- 定期更换您的交易账户密码
- 仅在可信的网络环境中运行交易系统

## 风险提示

1. 期货交易具有高风险，请合理控制仓位
2. 本系统仅供学习交流使用，实盘交易需谨慎
3. 市场行情瞬息万变，模型预测结果仅供参考
4. 请确保遵守当地法律法规

## 技术栈

- Python 3.8+
- TensorFlow/Keras - 深度学习框架
- vn.py - 量化交易开发框架
- Pandas/Numpy - 数据处理
- Scikit-learn - 机器学习库

## 维护与更新

- 定期更新模型以适应市场变化
- 监控交易表现并调整策略参数
- 根据实际交易结果优化风险控制机制

## 参考资料

- SimNow模拟交易平台: https://www.simnow.com.cn/
- vn.py官方文档: https://www.vnpy.com/
- TensorFlow官方文档: https://www.tensorflow.org/