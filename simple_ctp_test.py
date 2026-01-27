import time
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_ctp import CtpGateway


def test_ctp_connection():
    """测试CTP连接"""
    print("正在初始化CTP连接...")
    
    # CTP连接配置
    config = {
        "userid": "253859",  # 替换为实际账号
        "password": "1qaz@WSX3edc",
        "brokerid": "9999",
        "td_address": "tcp://182.254.243.31:40001",  # SimNow模拟交易地址
        "md_address": "tcp://182.254.243.31:40011",  # SimNow行情地址
        "product_info": "CTP_TEST",
        "auth_code": "00000000000000000000",
        "app_id": "simnow_client_test"
    }

    # 创建事件引擎和主引擎
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    
    # 添加CTP网关
    main_engine.add_gateway(CtpGateway)
    
    print("正在连接CTP SimNow仿真环境...")
    
    try:
        # 连接CTP
        main_engine.connect(config, "CTP")
        
        # 等待连接建立
        timeout = 10  # 设置较短的超时时间
        start_time = time.time()
        
        # 检查连接状态
        while time.time() - start_time < timeout:
            # 尝试获取网关并检查连接状态
            gateway = main_engine.get_gateway("CTP")
            if hasattr(gateway, 'td_connected') and gateway.td_connected:
                print("CTP连接成功")
                break
            elif hasattr(gateway, 'td_login_status') and gateway.td_login_status:
                print("CTP登录成功")
                break
            time.sleep(1)
        else:
            print(f"CTP连接超时({timeout}秒)")
            
        # 关闭连接
        main_engine.close()
        print("连接已关闭")
        
    except Exception as e:
        print(f"CTP连接失败: {e}")
        # 关闭连接
        try:
            main_engine.close()
        except:
            pass


if __name__ == "__main__":
    print("=" * 50)
    print("简化版CTP连接测试")
    print("=" * 50)
    
    test_ctp_connection()
    
    print("测试完成")