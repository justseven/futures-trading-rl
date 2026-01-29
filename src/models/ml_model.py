import joblib
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import Sequential, Model, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input, concatenate, GRU, Conv1D, MaxPooling1D, Flatten, TimeDistributed
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from sklearn.ensemble import RandomForestRegressor
from sklearn.svm import SVR
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import os
from typing import Tuple, Optional
from sklearn.preprocessing import MinMaxScaler


class PricePredictionModel:
    """
    期货价格预测模型
    """
    
    def __init__(self, model_type='lstm', sequence_length=60, n_features=10):
        self.model_type = model_type
        self.sequence_length = sequence_length
        self.n_features = n_features
        self.model = None
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.target_scaler = MinMaxScaler(feature_range=(0, 1))
        
    def _build_lstm_model(self) -> Sequential:
        """
        构建LSTM模型，用于预测30分钟后的价格
        """
        model = Sequential([
            Input(shape=(self.sequence_length, self.n_features)),  # 使用Input层作为第一层
            LSTM(units=50, return_sequences=True),
            Dropout(0.2),
            LSTM(units=50, return_sequences=True),
            Dropout(0.2),
            LSTM(units=50, return_sequences=False),
            Dropout(0.2),
            Dense(units=25),
            Dense(units=1)
        ])
        
        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='mean_squared_error',
            metrics=['mae']
        )
        
        return model
    
    def _build_gru_model(self) -> Sequential:
        """
        构建GRU模型
        """
        model = Sequential([
            Input(shape=(self.sequence_length, self.n_features)),  # 使用Input层作为第一层
            GRU(units=50, return_sequences=True),
            Dropout(0.2),
            GRU(units=50, return_sequences=True),
            Dropout(0.2),
            GRU(units=50, return_sequences=False),
            Dropout(0.2),
            Dense(units=25),
            Dense(units=1)
        ])
        
        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='mean_squared_error',
            metrics=['mae']
        )
        
        return model
    
    def _build_cnn_lstm_model(self) -> Sequential:
        """
        构建CNN-LSTM混合模型
        """
        model = Sequential([
            Input(shape=(self.sequence_length, self.n_features)),  # 使用Input层作为第一层
            Conv1D(filters=64, kernel_size=3, activation='relu'),
            MaxPooling1D(pool_size=2),
            LSTM(units=50, return_sequences=True),
            Dropout(0.2),
            LSTM(units=50, return_sequences=False),
            Dropout(0.2),
            Dense(units=25),
            Dense(units=1)
        ])
        
        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='mean_squared_error',
            metrics=['mae']
        )
        
        return model
    
    def build_model(self):
        """
        根据指定类型构建模型
        """
        if self.model_type == 'lstm':
            self.model = self._build_lstm_model()
        elif self.model_type == 'gru':
            self.model = self._build_gru_model()
        elif self.model_type == 'cnn-lstm':
            self.model = self._build_cnn_lstm_model()
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")
    
    def prepare_data_for_30min_prediction(self, df: pd.DataFrame, prediction_horizon: int = 30) -> Tuple[np.ndarray, np.ndarray]:
        """
        准备数据用于30分钟后价格预测
        """
        # 选择用于训练的特征列
        feature_columns = ['open', 'high', 'low', 'close', 'volume']
        
        # 添加技术指标
        df = self.add_technical_indicators(df)
        
        # 选择所有特征
        all_feature_cols = feature_columns + [col for col in df.columns if col not in feature_columns and col not in ['datetime']]
        features = df[all_feature_cols].values
        
        # 标准化特征 - 只有在scaler未被拟合时才进行fit_transform
        if hasattr(self.scaler, 'n_samples_seen_') and self.scaler.n_samples_seen_ > 0:
            scaled_features = self.scaler.transform(features)
        else:
            scaled_features = self.scaler.fit_transform(features)
        
        # 标准化目标变量（收盘价）
        target_values = df[['close']].values
        if hasattr(self.target_scaler, 'n_samples_seen_') and self.target_scaler.n_samples_seen_ > 0:
            scaled_target = self.target_scaler.transform(target_values)
        else:
            scaled_target = self.target_scaler.fit_transform(target_values)
        
        # 准备序列数据，目标是30个时间步长后的价格
        X, y = [], []
        for i in range(self.sequence_length, len(scaled_features) - prediction_horizon + 1):
            X.append(scaled_features[i - self.sequence_length:i])
            y.append(scaled_target[i + prediction_horizon - 1, 0])  # 30分钟后收盘价
        
        X, y = np.array(X), np.array(y)
        
        return X, y
    
    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        添加技术指标作为额外特征
        """
        # 移动平均线
        df['ma_5'] = df['close'].rolling(window=5).mean()
        df['ma_10'] = df['close'].rolling(window=10).mean()
        df['ma_20'] = df['close'].rolling(window=20).mean()
        
        # 相对强弱指数
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 布林带
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        df['bb_width'] = df['bb_upper'] - df['bb_lower']
        df['bb_position'] = (df['close'] - df['bb_lower']) / df['bb_width']
        
        # 价格变化率
        df['pct_change'] = df['close'].pct_change()
        
        # 成交量移动平均
        df['vol_ma'] = df['volume'].rolling(window=10).mean()
        
        # 最高价与最低价之差
        df['hl_diff'] = df['high'] - df['low']
        
        # 填充NaN值
        df = df.fillna(method='bfill').fillna(method='ffill')
        
        return df
    
    def train(self, X: np.ndarray, y: np.ndarray, validation_split: float = 0.2, epochs: int = 100, batch_size: int = 32):
        """
        训练模型
        """
        if self.model is None:
            self.build_model()
        
        # 确保在训练前已经拟合了scaler
        # 注意：X和y应该已经在prepare_data_for_30min_prediction中被正确标准化
        
        # 定义回调函数
        early_stopping = EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True)
        reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.2, patience=5, min_lr=0.0001)
        
        # 训练模型
        history = self.model.fit(
            X, y,
            validation_split=validation_split,
            epochs=epochs,
            batch_size=batch_size,
            callbacks=[early_stopping, reduce_lr],
            verbose=1
        )
        
        return history
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        预测
        """
        if self.model is None:
            raise ValueError("Model not built yet. Call build_model() or load_model() first.")
        
        predictions = self.model.predict(X)
        # 反标准化预测结果
        predictions = self.target_scaler.inverse_transform(predictions.reshape(-1, 1))
        return predictions.flatten()
    
    def save_model(self, filepath: str):
        """
        保存模型
        """
        if self.model is None:
            raise ValueError("No model to save. Train or load a model first.")
        
        # 保存模型架构和权重
        self.model.save(filepath)
        
        # 保存缩放器
        scaler_filepath = filepath.replace('.keras', '_scaler.pkl')
        joblib.dump(self.scaler, scaler_filepath)
        
        target_scaler_filepath = filepath.replace('.keras', '_target_scaler.pkl')
        joblib.dump(self.target_scaler, target_scaler_filepath)
    
    def load_model(self, filepath: str):
        """
        加载模型
        """
        # 加载模型
        self.model = load_model(filepath)
        
        # 加载缩放器
        scaler_filepath = filepath.replace('.keras', '_scaler.pkl')
        if os.path.exists(scaler_filepath):
            self.scaler = joblib.load(scaler_filepath)
        
        target_scaler_filepath = filepath.replace('.keras', '_target_scaler.pkl')
        if os.path.exists(target_scaler_filepath):
            self.target_scaler = joblib.load(target_scaler_filepath)