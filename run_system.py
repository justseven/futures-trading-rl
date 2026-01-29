#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
期货智能交易系统统一入口
提供命令行界面来运行系统的不同功能模块
"""

import os
import sys
import argparse
from pathlib import Path

def run_setup():
    """运行环境设置"""
    print("🔍 正在运行环境设置...")
    from setup_env import main as setup_main
    setup_main()

def run_training():
    """运行模型训练"""
    print("🏋️  正在运行模型训练...")
    import subprocess
    result = subprocess.run([sys.executable, "train_rb2605_model.py"], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ 训练失败: {result.stderr}")
    else:
        print("✅ 模型训练完成")

def run_trading():
    """运行智能交易"""
    print("💼 正在启动智能交易系统...")
    from smart_auto_trading import main as trading_main
    trading_main()

def run_backtesting():
    """运行回测"""
    print("📊 正在运行回测...")
    from complete_backtesting import main as backtest_main
    backtest_main()

def run_comprehensive():
    """运行综合交易系统"""
    print("🔄 正在启动综合交易系统...")
    from src.trading_system import main as comprehensive_main
    comprehensive_main()

def run_ai_system():
    """运行AI交易系统"""
    print("🤖 正在启动AI交易系统...")
    from src.utils.ai_trading_system import main as ai_main
    ai_main()

def list_commands():
    """列出所有可用命令"""
    print("\n📋 可用命令:")
    print("  setup        - 运行环境初始化设置")
    print("  training     - 运行模型训练")
    print("  trading      - 运行智能交易系统")
    print("  backtesting  - 运行回测系统")
    print("  comprehensive - 运行综合交易系统")
    print("  ai_system    - 运行AI交易系统")
    print("  all_commands - 显示所有命令")
    print("  help         - 显示帮助信息")

def show_help():
    """显示帮助信息"""
    print("\n🎯 期货智能交易系统 - 统一入口")
    print("\n用法: python run_system.py <command>")
    print("\n示例:")
    print("  python run_system.py setup         # 初始化环境")
    print("  python run_system.py trading       # 启动交易系统")
    print("  python run_system.py training      # 训练模型")
    print("  python run_system.py backtesting   # 运行回测")

def main():
    parser = argparse.ArgumentParser(description='期货智能交易系统统一入口')
    parser.add_argument('command', nargs='?', default='help', 
                        help='要执行的命令 (setup, training, trading, backtesting, comprehensive, ai_system, all_commands, help)')
    
    args = parser.parse_args()
    
    # 检查必要目录
    required_dirs = ['settings', 'models', 'data', 'logs']
    for dir_name in required_dirs:
        Path(dir_name).mkdir(exist_ok=True)
    
    # 根据命令执行相应功能
    if args.command == 'setup':
        run_setup()
    elif args.command == 'training':
        run_training()
    elif args.command == 'trading':
        run_trading()
    elif args.command == 'backtesting':
        run_backtesting()
    elif args.command == 'comprehensive':
        run_comprehensive()
    elif args.command == 'ai_system':
        run_ai_system()
    elif args.command == 'all_commands':
        list_commands()
    elif args.command == 'help':
        show_help()
    else:
        print(f"❌ 未知命令: {args.command}")
        show_help()
        return

if __name__ == "__main__":
    main()