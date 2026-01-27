import os
import pandas as pd
import torch

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv

from env_trade import FuturesTradeEnv

DATA_PATH = "data/kline.csv"
MODEL_DIR = "models"
TOTAL_TIMESTEPS = 300_000
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

def load_data():
    df = pd.read_csv(DATA_PATH)
    return df[["open", "high", "low", "close"]].dropna().reset_index(drop=True)


def make_env(df):
    return FuturesTradeEnv(df)


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)

    df = load_data()
    env = DummyVecEnv([lambda: make_env(df)])

    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        gamma=0.99,
        device=device,   # ✅ 核心
    )
    model.learn(total_timesteps=TOTAL_TIMESTEPS)
    model.save(f"{MODEL_DIR}/ppo_trade")

    print("模型训练完成并已保存")


if __name__ == "__main__":
    main()
