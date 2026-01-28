"""
期货合约规格配置
包含各品种的保证金比例、手续费等信息
参考SimNow模拟交易数据
"""
CONTRACT_SPECS = {
    "rb2605": {  # 螺纹钢
        "exchange": "SHFE",
        "name": "螺纹钢",
        "size": 10,  # 每手吨数
        "price_tick": 1,  # 最小变动价位
        "margin_ratio": 0.09,  # 保证金比例 9%
        "commission_open": 0.0001,  # 开仓手续费率
        "commission_close": 0.0001,  # 平仓手续费率
        "commission_close_today": 0.0001  # 平今仓手续费率
    },
    "cu2605": {  # 沪铜
        "exchange": "SHFE",
        "name": "阴极铜",
        "size": 5,  # 每手吨数
        "price_tick": 10,  # 最小变动价位
        "margin_ratio": 0.12,  # 保证金比例 12%
        "commission_open": 0.00005,  # 开仓手续费率
        "commission_close": 0.00005,  # 平仓手续费率
        "commission_close_today": 0.00005  # 平今仓手续费率
    },
    "ni2605": {  # 沪镍
        "exchange": "SHFE",
        "name": "镍",
        "size": 1,  # 每手吨数
        "price_tick": 10,  # 最小变动价位
        "margin_ratio": 0.12,  # 保证金比例 12%
        "commission_open": 3.0,  # 开仓手续费（元/手）
        "commission_close": 3.0,  # 平仓手续费（元/手）
        "commission_close_today": 6.0  # 平今仓手续费（元/手）
    },
    "SR309": {  # 白糖
        "exchange": "CZCE",
        "name": "白糖",
        "size": 10,  # 每手吨数
        "price_tick": 1,  # 最小变动价位
        "margin_ratio": 0.05,  # 保证金比例 5%
        "commission_open": 3.0,  # 开仓手续费（元/手）
        "commission_close": 3.0,  # 平仓手续费（元/手）
        "commission_close_today": 3.0  # 平今仓手续费（元/手）
    },
    "IF2606": {  # 沪深300股指期货
        "exchange": "CFFEX",
        "name": "沪深300股指",
        "size": 300,  # 每点价值
        "price_tick": 0.2,  # 最小变动价位
        "margin_ratio": 0.1,  # 保证金比例 10%
        "commission_open": 0.0,  # 开仓手续费（元/手）
        "commission_close": 23.0,  # 平仓手续费（元/手）
        "commission_close_today": 23.0  # 平今仓手续费（元/手）
    }
}

def get_contract_spec(symbol):
    """
    根据合约代码获取合约规格
    :param symbol: 合约代码，如 rb2605
    :return: 合约规格字典
    """
    # 匹配前两位字符，例如 rb、cu、ni 等
    for key, spec in CONTRACT_SPECS.items():
        if key.startswith(symbol[:2]):
            return spec
            
    # 如果没找到特定规格，返回默认规格（螺纹钢）
    return CONTRACT_SPECS.get("rb2605", {
        "exchange": "SHFE",
        "name": "商品期货",
        "size": 10,
        "price_tick": 1,
        "margin_ratio": 0.1,
        "commission_open": 0.0001,
        "commission_close": 0.0001,
        "commission_close_today": 0.0001
    })