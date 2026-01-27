#!/usr/bin/env python3
"""
CTP连接测试脚本
测试CTP交易和行情服务器连接
"""

import socket
import time
import struct

def test_ctp_connection(host, port, timeout=5):
    """
    测试CTP服务器连接
    """
    try:
        print(f"正在连接到 {host}:{port}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        start_time = time.time()
        sock.connect((host, port))
        connect_time = time.time() - start_time
        print(f"连接成功，耗时: {connect_time:.2f}秒")
        sock.close()
        return True, connect_time
    except socket.timeout:
        print(f"连接超时 ({timeout}s)")
        return False, None
    except socket.error as e:
        print(f"连接失败: {e}")
        return False, None
    except Exception as e:
        print(f"未知错误: {e}")
        return False, None

def test_ctp_servers():
    """
    测试常见的CTP服务器地址
    """
    # 常见的CTP服务器配置
    servers = [
        {
            "name": "SimNow模拟交易",
            "td_host": "182.254.243.31",
            "td_port": 40001,
            "md_host": "182.254.243.31",
            "md_port": 40011
        },
        {
            "name": "SimNow模拟交易(备用)",
            "td_host": "180.168.146.187",
            "td_port": 10201,
            "md_host": "180.168.146.187",
            "md_port": 10211
        },
        {
            "name": "上期所模拟",
            "td_host": "218.202.237.33",
            "td_port": 10203,
            "md_host": "218.202.237.33",
            "md_port": 10212
        }
    ]

    print("CTP连接测试开始")
    print("=" * 50)

    for server in servers:
        print(f"\n测试服务器: {server['name']}")
        print("-" * 30)

        # 测试交易服务器
        success, connect_time = test_ctp_connection(server['td_host'], server['td_port'])
        if success:
            print("交易服务器 (TD): ✓ 连接成功")
        else:
            print("交易服务器 (TD): ✗ 连接失败")

        # 测试行情服务器
        success, connect_time = test_ctp_connection(server['md_host'], server['md_port'])
        if success:
            print("行情服务器 (MD): ✓ 连接成功")
        else:
            print("行情服务器 (MD): ✗ 连接失败")
    print("\n" + "=" * 50)
    print("CTP连接测试完成")

def test_network_connectivity():
    """
    测试基本网络连通性
    """
    print("\n网络连通性测试:")
    print("-" * 20)

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

if __name__ == "__main__":
    print("CTP期货交易连接测试工具")
    print("当前时间:", time.strftime("%Y-%m-%d %H:%M:%S"))

    # 测试网络连通性
    test_network_connectivity()

    # 测试CTP服务器
    test_ctp_servers()

    print("\n注意事项:")
    print("1. 如果所有连接都失败，可能是网络或防火墙问题")
    print("2. CTP使用专用端口，可能被企业防火墙阻止")
    print("3. 实盘交易需要真实的CTP账号和密码")
    print("4. 建议使用SimNow模拟账户进行测试")