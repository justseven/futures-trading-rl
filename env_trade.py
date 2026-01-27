import gymnasium as gym
import numpy as np
from gymnasium import spaces
from account import Account


class FuturesTradeEnv(gym.Env):
    """
    PPO-friendly, learnable trading environment (v3)
    """

    metadata = {"render.modes": ["human"]}

    def __init__(self, df):
        super().__init__()

        self.df = df.reset_index(drop=True)
        self.n_steps = len(df)

        # ===== Trading parameters =====
        self.initial_cash = 1_000_000
        self.fee_rate = 0.0002
        self.reward_scale = 200.0
        self.idle_penalty = 0.001

        # ===== Action space =====
        # 0: flat, 1: long, 2: short
        self.action_space = spaces.Discrete(3)

        # ===== Observation space =====
        # [ret1, ret5, ret10, position, unrealized_pnl]
        self.observation_space = spaces.Box(
            low=-10, high=10, shape=(5,), dtype=np.float32
        )

        self.reset()

    def reset(self, seed=None, options=None):
        self.step_idx = 10
        self.account = Account(cash=self.initial_cash)
        self.position = 0
        self.entry_price = 0.0

        self.prev_equity = self.initial_cash
        return self._get_obs(), {}

    def _get_obs(self):
        price = self.df.loc[self.step_idx, "close"]

        ret1 = (price / self.df.loc[self.step_idx - 1, "close"] - 1)
        ret5 = (price / self.df.loc[self.step_idx - 5, "close"] - 1)
        ret10 = (price / self.df.loc[self.step_idx - 10, "close"] - 1)

        unrealized = self.position * (price - self.entry_price)

        obs = np.array(
            [ret1, ret5, ret10, self.position, unrealized / self.initial_cash],
            dtype=np.float32,
        )
        return obs

    def step(self, action):
        done = False
        price = self.df.loc[self.step_idx, "close"]

        # ===== Execute action =====
        target_position = {0: 0, 1: 1, 2: -1}[action]

        # Transaction cost
        cost = 0.0
        if target_position != self.position:
            cost = self.fee_rate * price * abs(target_position - self.position)

            if self.position != 0:
                self.account.cash += self.position * (price - self.entry_price)

            self.position = target_position
            self.entry_price = price

        # ===== Mark-to-market =====
        equity = self.account.cash + self.position * (price - self.entry_price)
        delta_equity = equity - self.prev_equity
        self.prev_equity = equity

        # ===== Reward shaping (核心) =====
        # 1. scaled PnL
        reward = self.reward_scale * (delta_equity / self.initial_cash)

        # 2. direction alignment bonus (trend following)
        ret1 = (price / self.df.loc[self.step_idx - 1, "close"] - 1)
        reward += 10.0 * self.position * ret1

        # 3. transaction cost penalty
        reward -= cost / self.initial_cash * self.reward_scale

        # 4. idle penalty (防摆烂)
        if self.position == 0:
            reward -= self.idle_penalty

        # ===== Step forward =====
        self.step_idx += 1
        if self.step_idx >= self.n_steps - 1:
            terminated = True
        else:
            terminated = False
        truncated = False

        return self._get_obs(), float(reward), terminated, truncated, {"equity": equity}

    def render(self, mode="human"):
        pass
