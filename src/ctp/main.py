import signal
import sys
import json
import os
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.object import LogData
from vnpy_ctp import CtpGateway
from vnpy_ctastrategy import CtaStrategyApp


# 全局变量，用于在信号处理器中访问main_engine
main_engine_global = None


def signal_handler(sig, frame):
    """处理中断信号的函数"""
    global main_engine_global
    
    print('\n正在安全关闭交易系统...')
    
    # 关闭主引擎
    if main_engine_global:
        main_engine_global.close()
    
    sys.exit(0)


def main():
    global main_engine_global
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    main_engine_global = main_engine  # 存储全局引用以便信号处理器使用

    # 添加 CTP 网关
    main_engine.add_gateway(CtpGateway)

    # 添加 CTA 模块
    main_engine.add_app(CtaStrategyApp)

    # 查找配置文件
    script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # 尝试多个可能的配置文件路径
    config_paths = [
        os.path.join(script_dir, "settings", "simnow_setting_one.json"),
        os.path.join(script_dir, "settings", "simnow_setting_two.json"),
        os.path.join(script_dir, "settings", "ctp_setting.json"),
        os.path.join(script_dir, "settings", "simnow_setting_template.json")
    ]
    
    config_to_use = None
    config_path_used = None
    
    for config_path in config_paths:
        print(f"检查配置文件: {config_path}")
        if os.path.exists(config_path):
            config_path_used = config_path
            print(f"✅ 找到配置文件: {config_path}")
            
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    ctp_setting = json.load(f)
                
                # 检查配置是否包含占位符
                if ("<YOUR_USER_ID>" in str(ctp_setting) or 
                    "<YOUR_PASSWORD>" in str(ctp_setting)):
                    print(f"⚠️  配置文件 {config_path} 仍包含占位符")
                    print("   请编辑配置文件并填入您的真实账户信息")
                    continue
                
                print(f"CTP配置加载成功: {ctp_setting}")
                
                # 检查CTP配置是否完整
                ctp_required_fields = ["用户名", "密码", "经纪商代码", "交易服务器", "行情服务器", "AppID", "授权编码"]
                ctp_missing_fields = []
                for field in ctp_required_fields:
                    value = ctp_setting.get(field)
                    if not value or (isinstance(value, str) and value.strip() == ""):
                        ctp_missing_fields.append(field)
                
                if not ctp_missing_fields:
                    print("CTP配置完整，将使用此配置")
                    config_to_use = ctp_setting
                    break
                else:
                    print(f"CTP配置文件不完整，缺少字段: {ctp_missing_fields}")
                    
            except json.JSONDecodeError:
                print(f"❌ 配置文件 {config_path} 格式错误")
            except Exception as e:
                print(f"❌ 读取配置文件 {config_path} 时出错: {e}")
    
    if config_to_use is None:
        print("❌ 未找到有效的配置文件")
        print("💡 请按以下步骤操作:")
        print("   1. 访问 https://www.simnow.com.cn/ 注册模拟交易账户")
        print("   2. 运行 python setup_env.py 进行配置")
        print("   3. 确保配置文件中没有占位符 <YOUR_USER_ID> 或 <YOUR_PASSWORD>")
        return
    
    print(f"\n正在连接到CTP...")
    print("请确保您在交易时间内运行此程序")
    
    try:
        # 连接到CTP
        main_engine.connect(config_to_use, "CTP")
        
        print("✅ CTP连接请求已提交")
        print("等待连接建立...")
        
        # 等待连接建立
        import time
        for i in range(20):
            time.sleep(1)
            print(".", end="", flush=True)
        
        print("\n连接建立完成")
        
        # 尝试获取账户信息以验证连接
        accounts = main_engine.get_all_accounts()
        if len(accounts) > 0:
            print(f"✅ 连接成功! 找到 {len(accounts)} 个账户信息")
        else:
            print("⚠️  未获取到账户信息，连接可能存在问题")
        
    except Exception as e:
        print(f"❌ CTP连接失败: {e}")
        print("\n常见问题排查:")
        print("- 确认账户信息正确无误")
        print("- 确认网络连接正常")
        print("- 确认当前时间在交易时间内")
        print("- 确认账户状态正常")
        print("- 确认AppID和授权编码与开户期货公司匹配")
        print("- 部分期货公司可能需要特定的产品名称字段")
        print("- 确认账户是否在期货公司系统中处于正常状态")
        print("- 尝试在交易时间内连接（避开结算时间）")
        return

    try:
        # 保持程序运行直到收到中断信号
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('\n检测到键盘中断，正在安全关闭...')
        if main_engine_global:
            main_engine_global.close()
        sys.exit(0)


if __name__ == "__main__":
    main()