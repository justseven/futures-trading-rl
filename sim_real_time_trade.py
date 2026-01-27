import numpy as np
import pandas as pd
from datetime import datetime
import time
from stable_baselines3 import PPO

# 加载训练好的模型
MODEL_PATH = "models/ppo_trade.zip"
model = PPO.load(MODEL_PATH, device="cpu")
print("模型加载成功")

# 模拟账户
class SimAccount:
    def __init__(self):
        self.cash = 1_000_000.0
        self.position = 0
        self.entry_price = 0.0

    def open_long(self, price):
        if self.position == 0:
            self.position = 1
            self.entry_price = price

    def open_short(self, price):
        if self.position == 0:
            self.position = -1
            self.entry_price = price

    def close(self, price):
        if self.position != 0:
            pnl = (price - self.entry_price) * self.position
            self.cash += pnl
            self.position = 0
            return pnl
        return 0

    def equity(self, price):
        return self.cash + self.position * (price - self.entry_price)

# 模拟K线数据
kline_data = pd.read_csv("data/kline.csv")
print(f"加载数据完成，共 {len(kline_data)} 条记录")

class SimTradingStrategy:
    def __init__(self):
        self.account = SimAccount()
        self.bar_window = 10
        self.close_prices = []
        self.position = 0
        self.last_obs = None
        self.last_action = None
        self.experience_buffer = []

    def run_simulation(self):
        print("开始模拟实时交易...")
        for idx, row in kline_data.iterrows():
            price = row['close']
            self.close_prices.append(price)
            if len(self.close_prices) > self.bar_window:
                self.close_prices.pop(0)

            if len(self.close_prices) >= self.bar_window:
                obs = self._get_observation(price)
                if obs is not None:
                    # 计算奖励
                    reward = 0
                    if self.last_obs is not None:
                        ret1 = (price / self.last_obs[0] - 1) if self.last_obs[0] != 0 else 0
                        reward = self.position * ret1 * 100  # 趋势跟随
                        if self.position == 0:
                            reward -= 0.001  # 闲置惩罚

                        # 添加经验
                        self.experience_buffer.append((self.last_obs, self.last_action, reward, obs, False))

                    # 模型预测
                    action, _ = model.predict(obs, deterministic=True)
                    action = action.item()  # 转换为int
                    target_position = {0: 0, 1: 1, 2: -1}[action]

                    # 执行交易
                    if target_position != self.position:
                        if self.position != 0:
                            pnl = self.account.close(price)
                            print(f"平仓: 价格{price:.2f}, 盈亏{pnl:.2f}")
                        if target_position != 0:
                            if target_position == 1:
                                self.account.open_long(price)
                                print(f"开多: 价格{price:.2f}")
                            else:
                                self.account.open_short(price)
                                print(f"开空: 价格{price:.2f}")
                        self.position = target_position

                    self.last_obs = obs
                    self.last_action = action

                    # 打印状态
                    equity = self.account.equity(price)
                    print(f"时间: {row['datetime']}, 价格: {price:.2f}, 仓位: {self.position}, 权益: {equity:.2f}")

                    # 在线学习 (模拟)
                    if len(self.experience_buffer) > 100:
                        print("模拟在线学习...")
                        # 这里可以实现真正的学习
                        self.experience_buffer = self.experience_buffer[-50:]  # 保留最近经验

            time.sleep(0.01)  # 模拟实时

        print("模拟结束")
        final_equity = self.account.equity(price)
        print(f"最终权益: {final_equity:.2f}, 总回报: {(final_equity / 1_000_000 - 1) * 100:.2f}%")

    def _get_observation(self, current_price):
        if len(self.close_prices) < self.bar_window:
            return None

        close_array = np.array(self.close_prices[-self.bar_window:])
        ret1 = (close_array[-1] / close_array[-2] - 1) if len(close_array) >= 2 else 0
        ret5 = (close_array[-1] / close_array[-6] - 1) if len(close_array) >= 6 else 0
        ret10 = (close_array[-1] / close_array[-11] - 1) if len(close_array) >= 11 else 0

        obs = np.array([ret1, ret5, ret10, self.position, 0.0], dtype=np.float32)
        return obs

if __name__ == "__main__":
    strategy = SimTradingStrategy()
    strategy.run_simulation()