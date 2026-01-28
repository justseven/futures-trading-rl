import numpy as np
from collections import deque

class FeaturePipeline:
    """
    用最近 N 根 bar 生成模型特征
    """

    def __init__(self, window: int = 30):
        self.window = window
        self.close_buffer = deque(maxlen=window)

    def update(self, bar):
        self.close_buffer.append(bar.close_price)

        if len(self.close_buffer) < self.window:
            return None

        prices = np.array(self.close_buffer)
        returns = np.diff(prices) / prices[:-1]

        # (1, timesteps, feature_dim)
        features = returns.reshape(1, -1, 1)
        return features
