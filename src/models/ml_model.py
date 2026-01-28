import joblib
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential, Model
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input, concatenate, GRU, Conv1D, MaxPooling1D, Flatten, TimeDistributed
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from sklearn.ensemble import RandomForestRegressor
from sklearn.svm import SVR
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import os
from typing import Tuple, Optional


class PricePredictionModel:
    """价格预测模型"""
    
    def __init__(self, model_type='lstm', sequence_length=60, n_features=10):
        self.model_type = model_type
        self.sequence_length = sequence_length
        self.n_features = n_features
        self.model = None
        self._build_model()
        
    def _build_model(self):
        """构建模型"""
        if self.model_type == 'lstm':
            self.model = self._build_lstm_model()
        elif self.model_type == 'cnn-lstm':
            self.model = self._build_cnn_lstm_model()
        elif self.model_type == 'hybrid':
            self.model = self._build_hybrid_model()
        elif self.model_type == 'random_forest':
            self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        elif self.model_type == 'svm':
            self.model = SVR(kernel='rbf', C=1.0, gamma='scale')
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")
            
    def _build_lstm_model(self):
        """构建LSTM模型"""
        model = Sequential([
            LSTM(50, return_sequences=True, input_shape=(self.sequence_length, self.n_features)),
            Dropout(0.2),
            LSTM(50, return_sequences=False),
            Dropout(0.2),
            Dense(25),
            Dense(1)
        ])
        model.compile(optimizer=Adam(learning_rate=0.001), loss='mse', metrics=['mae'])
        return model
        
    def _build_cnn_lstm_model(self):
        """构建CNN-LSTM混合模型"""
        model = Sequential([
            TimeDistributed(Conv1D(filters=64, kernel_size=1, activation='relu'), 
                          input_shape=(self.sequence_length, self.n_features, 1)),
            TimeDistributed(MaxPooling1D(pool_size=2)),
            TimeDistributed(Flatten()),
            LSTM(50, return_sequences=True),
            Dropout(0.2),
            LSTM(50, return_sequences=False),
            Dropout(0.2),
            Dense(25),
            Dense(1)
        ])
        model.compile(optimizer=Adam(learning_rate=0.001), loss='mse', metrics=['mae'])
        return model
        
    def _build_hybrid_model(self):
        """构建更复杂的混合模型"""
        # LSTM分支
        lstm_input = Input(shape=(self.sequence_length, self.n_features), name='lstm_input')
        lstm_branch = LSTM(50, return_sequences=True)(lstm_input)
        lstm_branch = Dropout(0.2)(lstm_branch)
        lstm_branch = LSTM(50, return_sequences=False)(lstm_branch)
        lstm_branch = Dense(25, activation='relu')(lstm_branch)
        
        # CNN分支
        cnn_input = Input(shape=(self.sequence_length, self.n_features), name='cnn_input')
        cnn_branch = Conv1D(filters=64, kernel_size=3, activation='relu')(cnn_input)
        cnn_branch = MaxPooling1D(pool_size=2)(cnn_branch)
        cnn_branch = Flatten()(cnn_branch)
        cnn_branch = Dense(50, activation='relu')(cnn_branch)
        
        # 合并两个分支
        merged = concatenate([lstm_branch, cnn_branch])
        merged = Dense(50, activation='relu')(merged)
        merged = Dropout(0.2)(merged)
        output = Dense(1, name='output')(merged)
        
        model = Model(inputs=[lstm_input, cnn_input], outputs=output)
        model.compile(optimizer=Adam(learning_rate=0.001), loss='mse', metrics=['mae'])
        return model
        
    def train(self, X_train, y_train, X_val=None, y_val=None, epochs=100, batch_size=32):
        """训练模型"""
        if self.model_type in ['lstm', 'cnn-lstm']:
            # 对于神经网络模型
            callbacks = [
                EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True),
                ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=1e-7)
            ]
            
            validation_data = (X_val, y_val) if X_val is not None and y_val is not None else None
            
            history = self.model.fit(
                X_train, y_train,
                batch_size=batch_size,
                epochs=epochs,
                validation_data=validation_data,
                callbacks=callbacks,
                verbose=1
            )
            return history
        else:
            # 对于传统机器学习模型
            # 需要展平输入数据 (samples, timesteps, features) -> (samples, timesteps*features)
            X_train_flat = X_train.reshape(X_train.shape[0], -1)
            self.model.fit(X_train_flat, y_train)
            
    def predict(self, X):
        """预测"""
        if self.model_type in ['random_forest', 'svm']:
            X_flat = X.reshape(X.shape[0], -1)
            return self.model.predict(X_flat)
        else:
            return self.model.predict(X)
        
    def evaluate(self, X_test, y_test) -> dict:
        """评估模型性能"""
        predictions = self.predict(X_test)
        
        mse = mean_squared_error(y_test, predictions)
        mae = mean_absolute_error(y_test, predictions)
        r2 = r2_score(y_test, predictions)
        
        # 计算方向准确性 (预测涨跌方向正确的比例)
        actual_changes = np.diff(y_test.flatten())
        predicted_changes = np.diff(predictions.flatten())
        direction_accuracy = np.mean(np.sign(actual_changes) == np.sign(predicted_changes))
        
        return {
            'mse': mse,
            'mae': mae,
            'rmse': np.sqrt(mse),
            'r2': r2,
            'direction_accuracy': direction_accuracy
        }
        
    def save_model(self, filepath: str):
        """保存模型"""
        # 确保目录存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        if self.model_type in ['lstm', 'cnn-lstm', 'hybrid']:
            self.model.save(filepath)
        else:
            joblib.dump(self.model, filepath)
        
    def load_model(self, filepath: str):
        """加载模型"""
        if self.model_type in ['lstm', 'cnn-lstm', 'hybrid']:
            self.model = tf.keras.models.load_model(filepath)
        else:
            self.model = joblib.load(filepath)


