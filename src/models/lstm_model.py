import numpy as np
from tensorflow.keras.models import load_model
from models.base_model import BaseModel

class LSTMTrendModel(BaseModel):

    def __init__(self, model_path: str, scaler_path: str = None):
        self.model = load_model(model_path)
        self.scaler = None

        if scaler_path:
            import joblib
            self.scaler = joblib.load(scaler_path)

    def predict(self, features: np.ndarray) -> float:
        """
        features shape: (1, timesteps, feature_dim)
        """
        if self.scaler:
            features = self.scaler.transform(
                features.reshape(features.shape[0], -1)
            ).reshape(features.shape)

        prob = self.model.predict(features, verbose=0)[0][0]

        # 映射到 [-1, 1]
        return float(prob * 2 - 1)
