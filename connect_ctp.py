#!/usr/bin/env python3
"""
CTP连接工具
此脚本提供多种CTP连接方式和功能
"""

import sys
import os
import time
import socket
from typing import Dict, Any

# 将项目根目录添加到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


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




def interactive_config_input():
    """交互式输入CTP配置"""
    print("\n请输入CTP连接配置:")
    
    config = {}
    config["userid"] = input("用户ID: ").strip()
    config["password"] = input("密码: ").strip()
    config["brokerid"] = input("经纪商ID (默认9999): ").strip() or "9999"
    
    td_addr = input(f"交易服务器地址 (默认 tcp://182.254.243.31:40001): ").strip()
    config["td_address"] = td_addr if td_addr else "tcp://182.254.243.31:40001"
    
    md_addr = input(f"行情服务器地址 (默认 tcp://182.254.243.31:40011): ").strip()
    config["md_address"] = md_addr if md_addr else "tcp://182.254.243.31:40011"
    
    config["product_info"] = input("产品信息 (默认 CTP_TEST): ").strip() or "CTP_TEST"
    config["auth_code"] = input("授权码 (默认 00000000000000000000): ").strip() or "00000000000000000000"
    config["app_id"] = input("App ID (默认 simnow_client_test): ").strip() or "simnow_client_test"
    
    return config


def main():
    """主函数"""
    print("=" * 60)
    print("CTP期货交易连接工具")
    print("当前时间:", time.strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)
    
    # 检查依赖
    if not check_dependencies():
        print("\n由于缺少依赖，程序退出")
        return
    
    # 检查网络连通性
    check_network_connectivity()
    
    print("\n请选择连接方式:")
    print("1. 仅测试服务器连通性")
    print("2. 使用自定义配置连接")
    
    choice = input("\n请输入选择 (1-2): ").strip()
    
    if choice == "1":
        # 仅测试服务器连通性
        print("\n正在进行服务器连通性测试...")
        
        # 测试几个常用的SimNow服务器
        servers = [
            {"name": "SimNow主站", "td_host": "182.254.243.31", "td_port": 40001, "md_port": 40011},
            {"name": "SimNow备用", "td_host": "180.168.146.187", "td_port": 10201, "md_port": 10211},
        ]
        
        for server in servers:
            print(f"\n{server['name']}:")
            print("-" * 20)
            test_server_connection(server['td_host'], server['td_port'])
            test_server_connection(server['td_host'], server['md_port'])
    elif choice == "2":
        # 交互式输入配置
        config = interactive_config_input()
        
        print(f"\n正在连接CTP服务器...")
        print(f"交易服务器: {config['td_address']}")
        print(f"行情服务器: {config['md_address']}")
        print(f"用户ID: {config['userid']}")
        print(f"经纪商: {config['brokerid']}")
        
        # 分别测试交易和行情服务器地址
        td_parts = config['td_address'].replace('tcp://', '').split(':')
        md_parts = config['md_address'].replace('tcp://', '').split(':')
        
        td_host, td_port = td_parts[0], int(td_parts[1])
        md_host, md_port = md_parts[0], int(md_parts[1])
        
        print("\n服务器连通性测试:")
        td_success = test_server_connection(td_host, td_port)
        md_success = test_server_connection(md_host, md_port)
        
        if not (td_success and md_success):
            print("\n服务器连通性存在问题，连接可能会失败")
        else:
            # 尝试建立CTP连接
            try:
                print("\n正在导入CTP引擎...")
                from ctp_engine import CTPEngine
                
                engine = CTPEngine(config)
                success = engine.connect()
                if success:
                    print("\n✓ CTP连接成功!")
                    # 获取账户信息
                    balance = engine.get_balance()
                    print(f"账户余额: {balance}")
                    
                    # 断开连接
                    engine.disconnect()
                else:
                    print("\n✗ CTP连接失败!")
                
                return success
            except Exception as e:
                print(f"\n✗ CTP连接过程中出现错误: {e}")
                import traceback
                traceback.print_exc()
                return False
        # 仅测试服务器连通性
        print("\n正在进行服务器连通性测试...")
        
        # 测试几个常用的SimNow服务器
        servers = [
            {"name": "SimNow主站", "td_host": "182.254.243.31", "td_port": 40001, "md_port": 40011},
            {"name": "SimNow备用", "td_host": "180.168.146.187", "td_port": 10201, "md_port": 10211},
        ]
        
        for server in servers:
            print(f"\n{server['name']}:")
            print("-" * 20)
            test_server_connection(server['td_host'], server['td_port'])
            test_server_connection(server['td_host'], server['md_port'])
    else:
        print("无效选择，退出程序")
        return
    
    print("\n" + "=" * 60)
    print("CTP连接测试完成")
    print("\n注意事项:")
    print("1. 如果所有连接都失败，可能是网络或防火墙问题")
    print("2. CTP使用专用端口，可能被企业防火墙阻止")
    print("3. 实盘交易需要真实的CTP账号和密码")
    print("4. 建议先用SimNow模拟账户进行测试")


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