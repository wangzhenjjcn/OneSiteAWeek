#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pornhub采集工具 - 交互式运行脚本
"""

import os
import sys

def show_usage():
    """显示使用说明"""
    print("""
🎯 Pornhub视频采集工具 - 使用指南

📖 运行方式:

1. 交互式运行（推荐新手）:
   python run.py

2. 命令行运行:
   python app.py [起始页] [最大页数]
   
   示例:
   python app.py 1 5    # 采集第1-5页
   python app.py 3      # 从第3页开始采集所有页面
   python app.py        # 从第1页开始采集所有页面

💡 配置说明:

- 修改 config.py 调整代理、线程数等设置
- requests模式更稳定（默认）
- Selenium模式可获取动态内容但需要Chrome

⚠️ 注意事项:

- 确保代理设置正确（如果需要）
- 首次运行建议限制页数进行测试
- 可随时按Ctrl+C中断采集
""")

def get_user_input():
    """获取用户输入"""
    try:
        print("🚀 Pornhub视频采集工具")
        print("=" * 50)
        
        # 获取起始页
        start_page_input = input("请输入起始页数 (默认: 1): ").strip()
        start_page = int(start_page_input) if start_page_input else 1
        
        # 获取最大页数
        max_pages_input = input("请输入最大页数 (默认: 3, 输入0表示无限制): ").strip()
        if max_pages_input == '0':
            max_pages = None
        elif max_pages_input:
            max_pages = int(max_pages_input)
        else:
            max_pages = 3
        
        # 确认配置
        print(f"\n📊 配置确认:")
        print(f"  - 起始页: {start_page}")
        print(f"  - 最大页数: {max_pages or '无限制'}")
        
        confirm = input("\n确认开始采集? (y/N): ").lower()
        if confirm not in ['y', 'yes', '是']:
            print("❌ 用户取消操作")
            return None, None
        
        return start_page, max_pages
        
    except ValueError:
        print("❌ 输入格式错误")
        return None, None
    except KeyboardInterrupt:
        print("\n❌ 用户取消操作")
        return None, None

def main():
    """主函数"""
    # 检查是否为交互式运行
    if len(sys.argv) > 1:
        # 有命令行参数，显示帮助信息
        if sys.argv[1] in ['-h', '--help', 'help']:
            show_usage()
            return
        
        # 直接运行主程序
        print("🔄 运行主程序...")
        os.system(f"python app.py {' '.join(sys.argv[1:])}")
        return
    
    # 交互式运行
    show_usage()
    
    start_page, max_pages = get_user_input()
    if start_page is None:
        return
    
    # 构建命令
    cmd_args = [str(start_page)]
    if max_pages is not None:
        cmd_args.append(str(max_pages))
    
    cmd = f"python app.py {' '.join(cmd_args)}"
    
    print(f"\n🔄 执行命令: {cmd}")
    print("⏳ 开始采集...")
    
    # 运行主程序
    try:
        exit_code = os.system(cmd)
        if exit_code == 0:
            print("\n🎉 采集完成！")
        else:
            print(f"\n⚠️ 程序退出，代码: {exit_code}")
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断采集")

if __name__ == "__main__":
    main() 