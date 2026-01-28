import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from ta import add_all_ta_features
from ta.utils import dropna
from sklearn.decomposition import PCA
import talib


class DataProcessor:
    """数据预处理模块"""
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.pca = None
        
    def clean_data(self, df):
        """数据清洗"""
        df = dropna(df)
        
        # 处理异常值 - 使用IQR方法
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            if col in df.columns:
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                df = df[(df[col] >= lower_bound) & (df[col] <= upper_bound)]
        
        return df
        
    def feature_engineering(self, df):
        """特征工程 - 添加技术指标"""
        if df.empty:
            return df
            
        # 添加基础技术指标
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close']/df['close'].shift(1))
        
        # 添加移动平均线
        df['ma_5'] = df['close'].rolling(window=5).mean()
        df['ma_10'] = df['close'].rolling(window=10).mean()
        df['ma_20'] = df['close'].rolling(window=20).mean()
        df['ma_60'] = df['close'].rolling(window=60).mean()
        
        # 添加RSI
        df['rsi'] = self._calculate_rsi(df['close'])
        
        # 添加布林带
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = self._calculate_bollinger_bands(df['close'])
        
        # 添加MACD
        df['macd'], df['signal'], df['histogram'] = self._calculate_macd(df['close'])
        
        # 添加ATR（平均真实波幅）
        df['atr'] = self._calculate_atr(df['high'], df['low'], df['close'])
        
        # 添加成交量相关指标
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        # 添加波动率
        df['volatility'] = df['returns'].rolling(window=20).std()
        
        # 删除包含NaN的行
        df.dropna(inplace=True)
        
        return df
    
    def _calculate_rsi(self, prices, period=14):
        """计算RSI指标"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_bollinger_bands(self, prices, period=20, std_dev=2):
        """计算布林带"""
        ma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper_band = ma + (std * std_dev)
        lower_band = ma - (std * std_dev)
        return upper_band, ma, lower_band
    
    def _calculate_macd(self, prices, fast=12, slow=26, signal_period=9):
        """计算MACD"""
        exp1 = prices.ewm(span=fast, adjust=False).mean()
        exp2 = prices.ewm(span=slow, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=signal_period, adjust=False).mean()
        histogram = macd - signal
        return macd, signal, histogram
    
    def _calculate_atr(self, high, low, close, period=14):
        """计算ATR"""
        high_low = high - low
        high_close = np.abs(high - close.shift())
        low_close = np.abs(low - close.shift())
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        atr = true_range.rolling(window=period).mean()
        return atr
        
    def normalize_data(self, df, method='standardization'):
        """数据标准化或归一化"""
        # 选择数值列进行标准化
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if method == 'standardization':
            # Z-score标准化
            df_scaled = df.copy()
            df_scaled[numeric_cols] = self.scaler.fit_transform(df[numeric_cols])
        elif method == 'minmax':
            # Min-Max归一化
            scaler = MinMaxScaler()
            df_scaled = df.copy()
            df_scaled[numeric_cols] = scaler.fit_transform(df[numeric_cols])
        else:
            df_scaled = df.copy()
        
        return df_scaled
        
    def create_sequences(self, data, seq_length, target_col='close'):
        """创建时间序列样本"""
        xs, ys = [], []
        for i in range(seq_length, len(data)):
            x = data.iloc[i-seq_length:i][[col for col in data.columns if col != target_col]].values
            y = data.iloc[i][target_col]
            xs.append(x)
            ys.append(y)
        return np.array(xs), np.array(ys)
        
    def reduce_dimensions(self, data, n_components=0.95):
        """降维处理"""
        self.pca = PCA(n_components=n_components)
        reduced_data = self.pca.fit_transform(data)
        print(f"PCA保留了 {self.pca.explained_variance_ratio_.sum():.2%} 的方差")
        return reduced_data
        
    def prepare_supervised_data(self, df, target_col='close', lookback=60):
        """准备监督学习数据"""
        # 获取所有数值列
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        values = df[numeric_cols].values
        
        # 创建监督学习数据集
        X, y = [], []
        for i in range(lookback, len(values)):
            X.append(values[i-lookback:i])
            y.append(values[i, numeric_cols.index(target_col)])  # 目标是收盘价
            
        return np.array(X), np.array(y)