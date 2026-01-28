#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
项目初始化脚本
帮助用户设置SimNow账户配置并准备运行环境
"""

import os
import json
import shutil
from pathlib import Path

def main():
    print("=" * 60)
    print("期货智能交易系统 - 环境初始化脚本")
    print("=" * 60)
    
    # 检查settings目录是否存在
    settings_dir = Path("settings")
    if not settings_dir.exists():
        print("创建settings目录...")
        settings_dir.mkdir(parents=True, exist_ok=True)
    
    # 检查模板配置文件是否存在
    template_path = settings_dir / "simnow_setting_template.json"
    if not template_path.exists():
        print("创建SimNow配置模板...")
        template_config = {
            "用户名": "<YOUR_USER_ID>",  
            "密码": "<YOUR_PASSWORD>",
            "经纪商代码": "9999",
            "交易服务器": "tcp://182.254.243.31:30001", 
            "行情服务器": "tcp://182.254.243.31:30011",  
            "AppID": "simnow_client_test",
            "授权编码": "0000000000000000", 
            "产品名称": "simnow_client_test",
            "柜台环境": "实盘"
        }
        
        with open(template_path, 'w', encoding='utf-8') as f:
            json.dump(template_config, f, indent=4, ensure_ascii=False)
        
        print(f"✅ 已创建模板配置文件: {template_path}")
    
    # 检查用户配置文件是否存在
    user_config_path = settings_dir / "simnow_setting_one.json"
    if user_config_path.exists():
        print(f"✅ 检测到用户配置文件: {user_config_path}")
        
        # 验证配置文件是否包含占位符
        with open(user_config_path, 'r', encoding='utf-8') as f:
            user_config = json.load(f)
        
        if ("<YOUR_USER_ID>" in str(user_config) or 
            "<YOUR_PASSWORD>" in str(user_config)):
            print("⚠️  警告: 您的配置文件似乎仍包含占位符 (<YOUR_USER_ID> 或 <YOUR_PASSWORD>)")
            print("   请编辑配置文件并填入您的真实账户信息")
        else:
            print("✅ 用户配置文件看起来已正确配置")
    else:
        print("📝 现在我们将帮助您创建个人配置文件...")
        print("   首先，请访问 https://www.simnow.com.cn/ 注册您的模拟交易账户")
        
        user_id = input("   请输入您的SimNow用户ID (或按Enter跳过): ").strip()
        if user_id:
            password = input("   请输入您的SimNow密码: ").strip()
            
            if user_id and password:
                # 从模板创建用户配置
                user_config = {
                    "用户名": user_id,
                    "密码": password,
                    "经纪商代码": "9999",
                    "交易服务器": "tcp://182.254.243.31:30001", 
                    "行情服务器": "tcp://182.254.243.31:30011",  
                    "AppID": "simnow_client_test",
                    "授权编码": "0000000000000000", 
                    "产品名称": "simnow_client_test",
                    "柜台环境": "实盘"
                }
                
                with open(user_config_path, 'w', encoding='utf-8') as f:
                    json.dump(user_config, f, indent=4, ensure_ascii=False)
                
                print(f"✅ 已创建用户配置文件: {user_config_path}")
            else:
                print("   ❌ 未输入有效的账户信息，跳过配置文件创建")
                print(f"   💡 请手动复制模板文件: cp {template_path} {user_config_path}")
                print("   💡 然后编辑该文件并填入您的账户信息")
        else:
            print(f"   💡 请手动复制模板文件: cp {template_path} {user_config_path}")
            print("   💡 然后编辑该文件并填入您的账户信息")
    
    # 检查models目录
    models_dir = Path("models")
    if not models_dir.exists():
        print("创建models目录...")
        models_dir.mkdir(parents=True, exist_ok=True)
    
    # 检查data目录
    data_dir = Path("data")
    if not data_dir.exists():
        print("创建data目录...")
        data_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "=" * 60)
    print("环境初始化完成!")
    print("=" * 60)
    print("接下来您可以:")
    print("1. 训练模型: python train_rb2605_model.py")
    print("2. 运行智能交易系统: python smart_auto_trading.py")
    print("\n⚠️  安全提醒:")
    print("- 请确保您的 .gitignore 文件正确配置，避免提交敏感信息")
    print("- 不要在公共仓库中分享包含真实凭证的配置文件")
    print("- 定期更换您的交易账户密码")
    print("=" * 60)

if __name__ == "__main__":
    main()