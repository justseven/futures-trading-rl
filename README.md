# 期货散户交易系统

这是一个基于VNPy的期货自动化交易系统，具有AI预测功能。

## 功能特点

- 自动收集期货市场数据
- 基于深度学习的价格预测模型
- 风险管理和回测功能
- 实时交易执行

## 系统要求

- Python 3.7+
- Windows/Linux/macOS

## 安装步骤

1. 克隆项目到本地
2. 创建虚拟环境：
   ```
   python -m venv venv
   ```
3. 激活虚拟环境：
   - Windows: `venv\Scripts\activate`
   - Linux/macOS: `source venv/bin/activate`
4. 安装依赖：
   ```
   pip install -r requirements.txt
   ```
5. 配置CTP/SimNow连接信息

## 配置SimNow仿真账户

要使用仿真交易功能，您需要：

1. 访问 http://www.simnow.com.cn 注册SimNow仿真账户
2. 在 `settings/simnow_setting.json` 中填写您的账户信息：
   ```json
   {
     "用户名": "您的用户名",
     "密码": "您的密码",
     "经纪商代码": "9999",
     "交易服务器": "tcp://180.168.146.187:10202",
     "行情服务器": "tcp://180.168.146.187:10212",
     "产品信息": "simnow_client_test",
     "授权编码": "0000000000000000",
     "账户编号": "您的账户编号"
   }
   ```

## 运行系统

激活虚拟环境后，运行：

```
python run_ctp_trading.py
```

系统将自动启动综合交易系统，包括数据收集、模型训练和实时交易功能。

## 注意事项

- 本系统仅供学习和研究使用，请勿用于实盘交易
- 仿真交易与实盘交易存在差异
- 使用前请充分了解期货交易的风险
- 请遵守相关法律法规
