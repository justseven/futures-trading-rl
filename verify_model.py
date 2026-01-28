import os
import sys
import numpy as np

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models.ml_model import PricePredictionModel


def verify_model():
    """验证训练好的模型是否可以正常加载和使用"""
    print("="*60)
    print("验证rb2605.SHFE合约预测模型")
    print("="*60)
    
    # 检查模型文件是否存在
    model_path = "./models/SHFE_rb_SHFE.rb2605_prediction_model.h5"
    
    if not os.path.exists(model_path):
        print(f"❌ 模型文件不存在: {model_path}")
        return False
    
    print(f"✅ 模型文件存在: {model_path}")
    
    try:
        # 尝试加载模型
        print("\n🔄 正在加载模型...")
        model = PricePredictionModel()
        model.load_model(model_path)
        print("✅ 模型加载成功！")
        
        # 检查模型基本信息
        if hasattr(model, 'model') and model.model:
            print(f"✅ 模型结构信息:")
            print(f"   - 输入形状: {model.model.input_shape}")
            print(f"   - 输出形状: {model.model.output_shape}")
            print(f"   - 模型层数: {len(model.model.layers)}")
        else:
            print("⚠️ 未能获取模型结构信息")
        
        # 尝试使用符合模型期望形状的随机数据进行预测
        print("\n🔄 正在验证模型预测功能...")
        
        # 获取正确的输入形状（去掉批次维度）
        input_shape = model.model.input_shape[1:]  # 去掉第一个维度（批次大小）
        print(f"   - 期望输入形状: {input_shape}")
        
        # 创建符合模型输入要求的示例数据
        sample_input = np.random.random((1,) + input_shape)  # 添加批次维度
        
        try:
            prediction = model.predict(sample_input)
            print(f"✅ 预测功能正常！")
            print(f"   - 输入形状: {sample_input.shape}")
            print(f"   - 预测输出形状: {prediction.shape}")
            print(f"   - 预测值范围: [{np.min(prediction):.4f}, {np.max(prediction):.4f}]")
            
            return True
        except Exception as e:
            print(f"❌ 预测功能验证失败: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("模型验证工具")
    print("-" * 30)
    
    success = verify_model()
    
    if success:
        print("\n🎉 模型验证通过！")
        print("💡 模型可以正常使用，可用于:")
        print("   - 实时价格预测")
        print("   - 回测验证")
        print("   - 交易策略集成")
    else:
        print("\n❌ 模型验证失败！")
        print("💡 请检查模型文件是否完整或重新训练模型")


if __name__ == "__main__":
    main()