#!/usr/bin/env python3
"""
修复的CTP连接脚本
根据错误信息，vnpy_ctp期望使用中文键名
"""

import sys
import os
import time
import socket
from typing import Dict, Any

# 将项目根目录添加到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_server_connection(host: str, port: int, timeout: int = 5) -> bool:
    """
    测试服务器连接
    
    Args:
        host: 服务器主机名或IP
        port: 服务器端口
        timeout: 超时时间
        
    Returns:
        bool: 连接是否成功
    """
    try:
        print(f"正在测试 {host}:{port}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✓ {host}:{port} 连接正常")
            return True
        else:
            print(f"✗ {host}:{port} 连接失败")
            return False
    except Exception as e:
        print(f"✗ {host}:{port} 连接失败: {e}")
        return False


def check_network_connectivity():
    """检查网络连通性"""
    print("\n网络连通性检查:")
    print("-" * 30)
    
    # 测试DNS解析
    try:
        import socket
        ip = socket.gethostbyname('www.baidu.com')
        print(f"DNS解析: ✓ (www.baidu.com -> {ip})")
    except:
        print("DNS解析: ✗ 失败")

    # 测试互联网连接
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(('www.baidu.com', 80))
        sock.close()
        print("互联网连接: ✓ 正常")
    except:
        print("互联网连接: ✗ 失败")


def check_dependencies():
    """检查依赖项"""
    print("\n检查依赖项:")
    print("-" * 30)
    
    # 检查vnpy_ctp是否存在
    try:
        import vnpy_ctp
        print("✓ vnpy_ctp 已安装")
    except ImportError:
        print("✗ vnpy_ctp 未安装")
        print("请使用以下命令安装: pip install vnpy_ctp")
        return False
    
    # 检查vnpy模块
    try:
        from vnpy.event import EventEngine
        print("✓ vnpy.event 已导入")
    except ImportError as e:
        print(f"✗ vnpy.event 导入失败: {e}")
        return False
    
    try:
        from vnpy.trader.engine import MainEngine
        print("✓ vnpy.trader.engine 已导入")
    except ImportError as e:
        print(f"✗ vnpy.trader.engine 导入失败: {e}")
        return False
    
    try:
        from vnpy_ctp import CtpGateway
        print("✓ vnpy_ctp.CtpGateway 已导入")
    except ImportError as e:
        print(f"✗ vnpy_ctp.CtpGateway 导入失败: {e}")
        return False
    
    return True


def fixed_ctp_connection(config: Dict[str, Any]):
    """修复的CTP连接"""
    print(f"\n正在连接CTP服务器...")
    print(f"交易服务器: {config['tdAddress']}")
    print(f"行情服务器: {config['mdAddress']}")
    print(f"用户ID: {config['用户名']}")
    print(f"经纪商: {config['经纪商代码']}")
    
    # 分别测试交易和行情服务器地址
    td_parts = config['tdAddress'].replace('tcp://', '').split(':')
    md_parts = config['mdAddress'].replace('tcp://', '').split(':')
    
    td_host, td_port = td_parts[0], int(td_parts[1])
    md_host, md_port = md_parts[0], int(md_parts[1])
    
    print("\n服务器连通性测试:")
    td_success = test_server_connection(td_host, td_port)
    md_success = test_server_connection(md_host, md_port)
    
    if not (td_success and md_success):
        print("\n服务器连通性存在问题，连接可能会失败")
        return False
    
    # 尝试建立CTP连接
    try:
        print("\n正在导入CTP引擎...")
        from vnpy.event import EventEngine
        from vnpy.trader.engine import MainEngine
        from vnpy_ctp import CtpGateway
        
        # 创建事件引擎和主引擎
        event_engine = EventEngine()
        main_engine = MainEngine(event_engine)
        
        # 添加CTP网关
        main_engine.add_gateway(CtpGateway)
        
        print("正在连接CTP SimNow仿真环境...")
        print("注意：此过程可能需要一些时间...")
        
        # 连接CTP
        main_engine.connect(config, "CTP")
        
        # 等待连接建立
        timeout = 30  # 增加超时时间
        start_time = time.time()
        
        print("等待连接响应...")
        
        while time.time() - start_time < timeout:
            try:
                # 获取CTP网关
                gateway = main_engine.get_gateway("CTP")
                
                # 检查是否有任何连接状态属性
                if hasattr(gateway, 'td_api'):
                    if hasattr(gateway.td_api, 'connection_status'):
                        if gateway.td_api.connection_status:
                            print("✓ 交易API连接成功")
                            print("✓ CTP连接成功!")
                            # 关闭连接
                            main_engine.close()
                            print("连接已关闭")
                            return True
                    if hasattr(gateway.td_api, 'login_status'):
                        if gateway.td_api.login_status:
                            print("✓ 交易API登录成功")
                            print("✓ CTP连接成功!")
                            # 关闭连接
                            main_engine.close()
                            print("连接已关闭")
                            return True
                            
                if hasattr(gateway, 'md_api'):
                    if hasattr(gateway.md_api, 'connection_status'):
                        if gateway.md_api.connection_status:
                            print("✓ 行情API连接成功")
                            
                time.sleep(1)
            except Exception as e:
                print(f"检查连接状态时出现错误: {e}")
                break
        else:
            print(f"连接超时({timeout}秒)")
        
        # 关闭连接
        try:
            main_engine.close()
            print("连接已关闭")
        except:
            pass
        
        print("\n✗ CTP连接失败!")
        return False
        
    except Exception as e:
        print(f"\n✗ CTP连接过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("修复版CTP期货交易连接工具")
    print("当前时间:", time.strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)
    
    # 检查依赖
    if not check_dependencies():
        print("\n由于缺少依赖，程序退出")
        return
    
    # 检查网络连通性
    check_network_connectivity()
    
    # 使用已验证的账户信息
    print("\n请输入您的SimNow账户信息:")
    userid = input("用户ID: ").strip()
    password = input("密码: ").strip()
    
    # 使用正确的中文键名
    config = {
        "用户名": userid,
        "密码": password,
        "经纪商代码": "9999",
        "行情服务器": "tcp://182.254.243.31:40001",  # SimNow模拟交易地址
        "交易服务器": "tcp://182.254.243.31:40011",  # SimNow行情地址
        "产品名称": "CTP_SIMNOW",
        "授权码": "0000000000000000",  # SimNow认证码
        "应用ID": "simnow_client_test"
    }
    
    # 执行连接
    result = fixed_ctp_connection(config)
    
    if result:
        print("\n恭喜！CTP连接成功！")
    else:
        print("\n连接失败，请检查您的账户信息和网络连接。")
    
    print("\n" + "=" * 60)
    print("CTP连接测试完成")
    print("\n注意事项:")
    print("1. 如果连接失败，请确认您的账户信息正确且处于交易时段")
    print("2. CTP使用专用端口，可能被企业防火墙阻止")
    print("3. 建议在交易时间内进行连接测试")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
    except Exception as e:
        print(f"\n程序执行出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n程序结束")