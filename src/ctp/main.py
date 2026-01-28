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

    # 只使用CTP配置文件
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ctp_config_path = os.path.join(script_dir, "settings", "simnow_setting.json")
    
    print(f"当前工作目录: {os.getcwd()}")
    print(f"脚本所在目录: {script_dir}")
    print(f"检查CTP配置文件是否存在: {ctp_config_path}")
    print(f"CTP配置文件存在: {os.path.exists(ctp_config_path)}")
    
    # 检查CTP配置文件是否存在且完整
    config_to_use = None
    config_type = "期货公司CTP仿真环境"
    
    if os.path.exists(ctp_config_path):
        print("检测到CTP配置文件")
        try:
            with open(ctp_config_path, 'r', encoding='utf-8') as f:
                ctp_setting = json.load(f)
            
            print(f"CTP配置加载成功: {ctp_setting}")
            
            # 检查CTP配置是否完整
            ctp_required_fields = ["用户名", "密码", "经纪商代码", "交易服务器", "行情服务器", "AppID", "授权编码"]
            ctp_missing_fields = []
            for field in ctp_required_fields:
                value = ctp_setting.get(field)
                if not value or (isinstance(value, str) and value.strip() == ""):
                    ctp_missing_fields.append(field)
            
            if not ctp_missing_fields:
                print("CTP配置完整，将使用CTP配置")
                config_to_use = ctp_setting
            else:
                print(f"CTP配置文件不完整，缺少字段: {ctp_missing_fields}")
        except Exception as e:
            print(f"加载CTP配置文件时出错: {e}")
    else:
        print("未找到CTP配置文件")
    
    if config_to_use is None:
        print("错误：CTP配置文件不存在或不完整，无法连接")
        return

    print(f"使用{config_type}配置")
    print(f"账户ID: {config_to_use.get('用户名', 'N/A')}")
    print(f"BrokerID: {config_to_use.get('经纪商代码', 'N/A')}")
    print(f"交易服务器: {config_to_use.get('交易服务器', 'N/A')}")
    print(f"行情服务器: {config_to_use.get('行情服务器', 'N/A')}")
    print(f"AppID: {config_to_use.get('AppID', 'N/A')}")
    print(f"产品名称: {config_to_use.get('产品名称', 'N/A')}")
    print(f"授权编码: {config_to_use.get('授权编码', 'N/A')}")
    
    # 连接到CTP环境
    print("开始连接CTP...")
    main_engine.connect(config_to_use, "CTP")
    
    print(f"已发送连接请求至{config_type}，请等待连接结果...")
    
    # 等待连接结果
    import time
    max_wait_time = 120  # 增加等待时间至120秒，给足时间让连接建立
    wait_count = 0
    connected = False
    
    # 尝试检测连接状态
    while wait_count < max_wait_time:
        time.sleep(1)
        wait_count += 1
        print(f"连接中... {wait_count}/{max_wait_time}秒")
        
        # 在这里我们可以尝试获取一些信息来判断连接状态
        # 检查是否有错误日志
        # 注意：vnpy内部有连接状态检查，但我们可以通过尝试获取合约等方式间接判断
        contracts = main_engine.get_all_contracts()
        if contracts:
            print(f"成功获取到 {len(contracts)} 个合约信息，连接可能已建立")
            connected = True
            break
    
    if connected:
        print("CTP连接成功！")
        print("vn.py 4.x CTA 引擎启动完成")
        print("按 Ctrl+C 可安全退出程序")
    else:
        print(f"连接超时({max_wait_time}秒)，请检查配置信息或网络连接")
        print("注意：错误代码4097通常表示认证失败，请确认：")
        print("- 用户名、密码是否正确")
        print("- AppID和授权编码是否正确且未过期")
        print("- 经纪商代码是否正确")
        print("- 交易服务器和行情服务器地址是否正确")
        print("- 是否已向期货公司申请开通CTP交易权限")
        print("")
        print("特别提醒：")
        print("- 如果您使用的是SimNow仿真账户，请确保AppID为'simnow_client_test'")
        print("- 如果您使用的是期货公司仿真账户，请确认AppID和授权编码与开户期货公司匹配")
        print("- 部分期货公司可能需要特定的产品名称字段")
        print("- 确认账户是否在期货公司系统中处于正常状态")
        print("- 尝试在交易时间内连接（避开结算时间）")

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