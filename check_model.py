import os

print("当前工作目录:", os.getcwd())
model_path = "./models/SHFE_rb_SHFE.rb2605_prediction_model.h5"
print("检查模型路径:", model_path)
print("模型文件是否存在:", os.path.exists(model_path))
print("当前models目录下的所有文件:")
for file in os.listdir("./models"):
    print(f"  - {file}")

# 检查rb2605变量的值
contract_to_trade = "rb2605"
exchange = "SHFE"
constructed_path = f"./models/SHFE_rb_{exchange}.{contract_to_trade}_prediction_model.h5"
print(f"\n构造的路径: {constructed_path}")
print(f"构造路径是否存在: {os.path.exists(constructed_path)}")