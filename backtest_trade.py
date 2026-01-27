import numpy as np
import pandas as pd

from env_trade import FuturesTradeEnv

DATA_PATH = "data/kline.csv"


def main():
    print("加载数据...")
    df = pd.read_csv(DATA_PATH)
    df = df[["open", "high", "low", "close"]].dropna().reset_index(drop=True)

    env = FuturesTradeEnv(df)
    obs = env.reset()[0]

    done = False
    equity_curve = []

    while not done:
        action = env.action_space.sample()  # 随机策略回测
        obs, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated
        equity_curve.append(info["equity"])

    equity_curve = np.array(equity_curve)

    print("\n===== 回测完成 =====")
    print("initial_cash:", 1_000_000)
    print("final_equity:", equity_curve[-1])
    print("total_return:", (equity_curve[-1] / 1_000_000) - 1)

    np.save("reports/equity_curve.npy", equity_curve)
    print("权益曲线已保存至 reports/equity_curve.npy")


if __name__ == "__main__":
    main()
