import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from .ml_model import PricePredictionModel
from src.data.data_processor import DataProcessor


class ModelTrainerAndBacktester:
    """模型训练和回测验证类"""
    
    def __init__(self):
        self.data_processor = DataProcessor()
        
    def load_contract_data(self, contract_dir, contract_pattern):
        """
        加载指定合约的数据
        :param contract_dir: 合约数据目录
        :param contract_pattern: 合约名称模式，如 'SHFE.rb2602'
        :return: DataFrame格式的数据
        """
        # 查找匹配的CSV文件
        files = []
        for file in os.listdir(contract_dir):
            if contract_pattern in file and file.endswith('.csv'):
                files.append(file)
        
        if not files:
            print(f"在目录 {contract_dir} 中找不到匹配 {contract_pattern} 的文件")
            return pd.DataFrame()
            
        # 选择最新的数据文件
        latest_file = max(files, key=lambda x: os.path.getctime(os.path.join(contract_dir, x)))
        file_path = os.path.join(contract_dir, latest_file)
        
        print(f"加载数据文件: {file_path}")
        df = pd.read_csv(file_path)
        
        # 转换时间列为datetime格式
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
        
        return df
    
    def convert_to_standard_format(self, df):
        """
        将数据转换为标准格式，适配data_processor
        :param df: 原始数据
        :return: 标准格式的DataFrame
        """
        # 找到第一个合约的列名模式（如SHFE.rb2602）
        contract_prefix = None
        for col in df.columns:
            if '.close' in col:
                contract_prefix = col.split('.close')[0]
                break
        
        if not contract_prefix:
            print("无法找到有效的合约前缀")
            return df
        
        # 创建标准格式的数据框
        standard_df = pd.DataFrame()
        standard_df['open'] = df[f'{contract_prefix}.open']
        standard_df['high'] = df[f'{contract_prefix}.high']
        standard_df['low'] = df[f'{contract_prefix}.low']
        standard_df['close'] = df[f'{contract_prefix}.close']
        standard_df['volume'] = df[f'{contract_prefix}.volume']
        
        return standard_df
    
    def prepare_training_data(self, df, target_col='SHFE.rb2602.close', sequence_length=60):
        """
        准备训练数据
        :param df: 原始数据
        :param target_col: 目标列名
        :param sequence_length: 序列长度
        :return: 特征X和标签y
        """
        # 将数据转换为标准格式
        standard_df = self.convert_to_standard_format(df)
        
        # 进行特征工程
        processed_df = self.data_processor.feature_engineering(standard_df)
        
        # 获取目标列数据（使用原始列名）
        target_series = df[target_col].fillna(method='ffill').fillna(method='bfill')
        
        # 标准化数据
        normalized_df = self.data_processor.normalize_data(processed_df)
        
        # 提取特征和目标值
        feature_values = normalized_df.values
        target_values = target_series.values
        
        # 创建序列数据
        X, y = [], []
        for i in range(sequence_length, len(feature_values)):
            X.append(feature_values[i-sequence_length:i])
            y.append(target_values[i])
            
        return np.array(X), np.array(y)
    
    def train_model(self, symbol, contract_dir, contract_pattern, model_type='lstm'):
        """训练预测模型"""
        print(f"开始训练 {symbol} 的预测模型...")
        
        # 1. 获取历史数据
        print("正在加载数据...")
        df = self.load_contract_data(contract_dir, contract_pattern)
        
        if df.empty:
            print(f"无法获取 {symbol} 的历史数据，训练终止")
            return False
        
        print(f"获取到 {len(df)} 行数据")
        
        # 2. 数据预处理和特征工程
        print("正在进行数据预处理和特征工程...")
        
        # 3. 准备训练数据
        print("正在准备训练数据...")
        sequence_length = 60
        X, y = self.prepare_training_data(df, f'{contract_pattern}.close', sequence_length)
        
        if len(X) == 0:
            print("没有足够的数据用于训练")
            return False
            
        # 4. 分割训练/测试集 (80% 训练, 20% 测试)
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        print(f"训练集大小: {len(X_train)}, 测试集大小: {len(X_test)}")
        
        # 5. 创建并训练模型
        print("正在创建和训练模型...")
        model = PricePredictionModel(
            model_type=model_type,
            sequence_length=sequence_length,
            n_features=X.shape[2] if len(X.shape) > 2 else 1
        )
        
        # 训练模型
        history = model.train(
            X_train=X_train,
            y_train=y_train,
            X_val=X_test,
            y_val=y_test,
            epochs=50,
            batch_size=32
        )
        
        # 6. 评估模型
        print("正在评估模型...")
        evaluation = model.evaluate(X_test, y_test)
        print(f"模型评估结果: {evaluation}")
        
        # 7. 保存模型
        model_dir = "models"
        os.makedirs(model_dir, exist_ok=True)
        symbol_safe = symbol.replace('.', '_').replace('@', '_')
        model_path = os.path.join(model_dir, f"{symbol_safe}_{contract_pattern}_prediction_model.h5")
        model.save_model(model_path)
        
        print(f"模型已保存至: {model_path}")
        return model, history, model_path
    
    def backtest_model(self, model, X_test, y_test, threshold=0.01):
        """
        回测模型表现
        :param model: 训练好的模型
        :param X_test: 测试特征
        :param y_test: 测试标签
        :param threshold: 交易阈值
        :return: 回测结果
        """
        print("开始回测模型表现...")
        
        # 预测价格
        predictions = model.predict(X_test)
        
        # 计算收益率
        returns_actual = np.diff(y_test) / y_test[:-1]
        returns_predicted = np.diff(predictions.flatten()) / predictions.flatten()[:-1]
        
        # 计算交易信号
        signals = np.where(np.abs((predictions.flatten() - y_test) / y_test) > threshold, 
                          np.sign(predictions.flatten() - y_test), 0)
        
        # 计算策略收益
        strategy_returns = returns_actual * signals[:-1]  # 对齐维度
        
        # 计算指标
        total_return = np.sum(strategy_returns)
        annualized_return = total_return * 252  # 假设252个交易日
        volatility = np.std(strategy_returns) * np.sqrt(252)
        
        if volatility != 0:
            sharpe_ratio = annualized_return / volatility
        else:
            sharpe_ratio = 0
            
        win_rate = np.sum(strategy_returns > 0) / len(strategy_returns)
        
        # 计算最大回撤
        cumulative_returns = np.cumprod(1 + strategy_returns)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = np.min(drawdown)
        
        # 输出回测结果
        backtest_result = {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'max_drawdown': max_drawdown,
            'predictions': predictions,
            'signals': signals,
            'strategy_returns': strategy_returns
        }
        
        print(f"回测结果:")
        print(f"- 总收益率: {backtest_result['total_return']:.2%}")
        print(f"- 年化收益率: {backtest_result['annualized_return']:.2%}")
        print(f"- 波动率: {backtest_result['volatility']:.2%}")
        print(f"- 夏普比率: {backtest_result['sharpe_ratio']:.2f}")
        print(f"- 胜率: {backtest_result['win_rate']:.2%}")
        print(f"- 最大回撤: {backtest_result['max_drawdown']:.2%}")
        
        return backtest_result


def main():
    """主函数"""
    trainer = ModelTrainerAndBacktester()
    
    # 创建必要的目录
    os.makedirs("models", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    print("="*60)
    print("期货合约价格预测模型训练与回测系统")
    print("="*60)
    
    # 选择要训练的合约
    print("可用合约:")
    print("1. 螺纹钢(rb) - SHFE.rb2602")
    print("2. 沪铜(cu) - SHFE.cu2602") 
    print("3. 沪镍(ni) - SHFE.ni2602")
    
    choice = input("请选择合约 (1-3, 默认为1): ").strip()
    
    if choice == "2":
        symbol = "SHFE.cu"
        contract_dir = "./data/沪铜_1min_2026_01_01_2026_01_26"
        contract_pattern = "SHFE.cu2602"
    elif choice == "3":
        symbol = "SHFE.ni"
        contract_dir = "./data/沪镍_1min_2026_01_01_2026_01_26"
        contract_pattern = "SHFE.ni2602"
    else:
        symbol = "SHFE.rb"
        contract_dir = "./data/rb_1min_2026_01_01_2026_01_26"
        contract_pattern = "SHFE.rb2602"
    
    model_type = input("请选择模型类型 (lstm/cnn-lstm/random_forest/svm，默认lstm): ").strip() or "lstm"
    
    # 训练模型
    result = trainer.train_model(
        symbol=symbol,
        contract_dir=contract_dir,
        contract_pattern=contract_pattern,
        model_type=model_type
    )
    
    if isinstance(result, tuple) and len(result) == 3:
        model, history, model_path = result
        print(f"\n{symbol} 的预测模型训练完成！")
        
        # 重新加载数据用于回测
        print(f"\n使用测试数据进行回测验证...")
        df = trainer.load_contract_data(contract_dir, contract_pattern)
        
        if not df.empty:
            # 准备测试数据
            sequence_length = 60
            X, y = trainer.prepare_training_data(df, f'{contract_pattern}.close', sequence_length)
            
            # 分割数据
            split_idx = int(len(X) * 0.8)
            X_test, y_test = X[split_idx:], y[split_idx:]
            
            if len(X_test) > 0:
                # 执行回测
                backtest_result = trainer.backtest_model(model, X_test, y_test)
                
                print(f"\n回测完成！")
            else:
                print("测试集为空，无法进行回测")
        else:
            print("加载数据失败，跳过回测")
    else:
        print(f"\n{symbol} 的预测模型训练失败！")


if __name__ == "__main__":
    main()