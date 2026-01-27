import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

try:
    from jqdatasdk import *
    JQDATA_AVAILABLE = True
    print("jqdatasdk 已安装，尝试连接...")
except ImportError:
    print("错误：未安装jqdatasdk包，请先运行: pip install jqdatasdk")
    exit(1)


def get_futures_data():
    """
    使用jqdatasdk获取期货数据
    """
    try:
        # =========================
        # 1. 登录（替换为你的账号）
        # =========================
        auth("13852000611", "1qaz2WSX")
        count=get_query_count()
        print(f"查询次数: {count}")
        # =========================
        # 2. 参数配置
        # =========================
        SYMBOL = "RB9999.XSGE"      # 螺纹钢主力连续
        START = "2024-10-12"        # 开始日期
        END = "2025-10-19"          # 结束日期
        FREQ = "1m"                 # 1分钟K线
        
        # =========================
        # 3. 获取K线数据
        # =========================
        df = get_price(
            security=SYMBOL,
            start_date=START,
            end_date=END,
            frequency=FREQ,
            fields=["open", "high", "low", "close", "volume"],
            skip_paused=True,
            fq="pre"
        )
        
        if df.empty:
            print("错误：获取到的数据为空，请检查合约代码和日期范围")
            return None
        
        # =========================
        # 4. 整理为标准格式
        # =========================
        df = df.reset_index()
        df.rename(columns={"index": "datetime"}, inplace=True)
        
        df = df[["datetime", "open", "high", "low", "close", "volume"]]
        df.sort_values("datetime", inplace=True)
        
        print(f"成功获取 {len(df)} 条真实数据")
        return df
        
    except Exception as e:
        print(f"错误：jqdatasdk获取数据失败: {e}")
        print("请检查：")
        print("1. 账户权限是否已开通")
        print("2. 用户名密码是否正确")
        print("3. 网络连接是否正常")
        return None


if __name__ == "__main__":
    # 获取数据
    df = get_futures_data()
    
    if df is not None:
        # =========================
        # 5. 保存为 CSV
        # =========================
        df.to_csv("futures_kline.csv", index=False)
        
        print("K线数据下载完成：futures_kline.csv")
        print(df.head())
    else:
        print("无法获取数据，程序退出")
        exit(1)
