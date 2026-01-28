from abc import ABC, abstractmethod
import numpy as np

class BaseModel(ABC):

    @abstractmethod
    def predict(self, features: np.ndarray) -> float:
        """
        返回标准化信号：
        -1.0 ~ +1.0
        """
        pass
