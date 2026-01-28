import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

# 添加src目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.models.ml_model import PricePredictionModel


def load_data(data_dir, contract_pattern):
    """
    从指定目录加载数据
    """
    csv_files = []
    for file in Path(data_dir).glob("*.csv"):
        if contract_pattern.lower() in file.name.lower():
            csv_files.append(str(file))
    
    if not csv_files:
        print(f"在目录 {data_dir} 中未找到包含 '{contract_pattern}' 的CSV文件")
        return None
    
    print(f"找到 {len(csv_files)} 个匹配的文件: {csv_files}")
    
    all_data = []
    for file_path in csv_files:
        try:
            df = pd.read_csv(file_path)
            print(f"读取文件: {file_path}, 形状: {df.shape}")
            
            # 重命名列以匹配期望的格式
            column_mapping = {
                f'{contract_pattern}.open': 'open',
                f'{contract_pattern}.high': 'high',
                f'{contract_pattern}.low': 'low',
                f'{contract_pattern}.close': 'close',
                f'{contract_pattern}.volume': 'volume'
            }
            
            # 检查哪些列存在于DataFrame中
            existing_mapping = {k: v for k, v in column_mapping.items() if k in df.columns}
            
            if not existing_mapping:
                print(f"警告: 文件 {file_path} 缺少必要的列: {list(column_mapping.keys())}")
                continue
            
            # 重命名列
            df.rename(columns=existing_mapping, inplace=True)
            
            # 确保日期时间列是正确的格式
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.sort_values('datetime', inplace=True)
            
            all_data.append(df)
        except Exception as e:
            print(f"读取文件 {file_path} 时出错: {e}")
    
    if not all_data:
        return None
    
    # 合并所有数据
    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df.sort_values('datetime', inplace=True)
    combined_df.reset_index(drop=True, inplace=True)
    
    print(f"合并后数据形状: {combined_df.shape}")
    print(f"数据时间范围: {combined_df['datetime'].min()} 到 {combined_df['datetime'].max()}")
    
    return combined_df


def main():
    # 创建模型实例 - 预测30分钟后的价格
    model_instance = PricePredictionModel(
        model_type='lstm',
        sequence_length=60,  # 使用60个时间步长的历史数据
        n_features=20  # 根据实际数据的特征数调整
    )
    
    # 定义数据目录和合约模式
    data_dir = "./data/rb_1min_2026_01_01_2026_01_26"
    contract_pattern = "SHFE.rb2605"
    
    # 加载数据
    print("正在加载数据...")
    df = load_data(data_dir, contract_pattern)
    
    if df is None or df.empty:
        print("无法加载数据，程序退出")
        return
    
    # 准备用于30分钟预测的数据
    print("正在准备训练数据...")
    X, y = model_instance.prepare_data_for_30min_prediction(df, prediction_horizon=30)
    
    print(f"训练数据形状: X={X.shape}, y={y.shape}")
    
    if len(X) == 0:
        print("没有足够的数据用于训练，请确保有足够的历史数据")
        return
    
    # 分割训练和测试数据
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    print(f"训练集形状: X={X_train.shape}, y={y_train.shape}")
    print(f"测试集形状: X={X_test.shape}, y={y_test.shape}")
    
    # 训练模型
    print("开始训练模型...")
    history = model_instance.train(
        X=X_train,
        y=y_train,
        validation_split=0.2,
        epochs=100,
        batch_size=32
    )
    
    # 评估模型
    print("评估模型...")
    train_score = model_instance.model.evaluate(X_train, y=y_train, verbose=0)
    test_score = model_instance.model.evaluate(X_test, y=y_test, verbose=0)
    print(f"训练集损失: {train_score}")
    print(f"测试集损失: {test_score}")
    
    # 创建模型保存目录
    model_dir = "./models"
    os.makedirs(model_dir, exist_ok=True)
    
    # 保存模型
    model_path = os.path.join(model_dir, f"SHFE_rb_{contract_pattern}_prediction_model.keras")
    print(f"正在保存模型到 {model_path}...")
    model_instance.save_model(model_path)
    
    print(f"模型训练完成并已保存到 {model_path}")
    
    # 显示最后几个epoch的损失
    if 'loss' in history.history and len(history.history['loss']) > 0:
        last_epochs = min(5, len(history.history['loss']))
        print(f"\n最后 {last_epochs} 个epoch的训练损失:")
        for i in range(-last_epochs, 0):
            epoch_num = len(history.history['loss']) + i + 1
            val_loss = history.history['val_loss'][i] if 'val_loss' in history.history else 'N/A'
            print(f"Epoch {epoch_num}: loss={history.history['loss'][i]:.6f}, val_loss={val_loss}")


if __name__ == "__main__":
    main()