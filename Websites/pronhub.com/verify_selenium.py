#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Selenium功能验证脚本
"""

from app import PornhubScraper
from config import SELENIUM_CONFIG

def verify_selenium_integration():
    """验证Selenium集成"""
    print("=== Selenium集成验证 ===")
    
    # 检查配置
    print("1. 检查Selenium配置...")
    config_items = [
        ('use_selenium', '是否使用Selenium'),
        ('headless', '无头模式'),
        ('disable_images', '禁用图片'),
        ('disable_javascript', '禁用JavaScript'),
        ('window_size', '窗口大小'),
        ('page_load_timeout', '页面加载超时'),
        ('implicit_wait', '隐式等待'),
        ('explicit_wait', '显式等待'),
    ]
    
    for key, description in config_items:
        value = SELENIUM_CONFIG.get(key, 'N/A')
        print(f"  {description}: {value}")
    
    # 检查类方法
    print("\n2. 检查Selenium方法...")
    scraper = PornhubScraper()
    
    selenium_methods = [
        'init_selenium_driver',
        'get_page_selenium',
        'get_page_requests',
        'close_driver'
    ]
    
    all_methods_exist = True
    for method_name in selenium_methods:
        if hasattr(scraper, method_name):
            print(f"  ✓ 方法 {method_name} 存在")
        else:
            print(f"  ✗ 方法 {method_name} 不存在")
            all_methods_exist = False
    
    # 检查属性
    print("\n3. 检查Selenium属性...")
    selenium_attrs = [
        'use_selenium',
        'driver'
    ]
    
    all_attrs_exist = True
    for attr_name in selenium_attrs:
        if hasattr(scraper, attr_name):
            print(f"  ✓ 属性 {attr_name} 存在")
        else:
            print(f"  ✗ 属性 {attr_name} 不存在")
            all_attrs_exist = False
    
    return all_methods_exist and all_attrs_exist

def verify_selenium_config():
    """验证Selenium配置"""
    print("\n=== Selenium配置验证 ===")
    
    # 检查必要的配置项
    required_configs = ['use_selenium', 'headless', 'disable_images']
    
    all_configs_valid = True
    for config_key in required_configs:
        if config_key in SELENIUM_CONFIG:
            print(f"  ✓ 配置项 {config_key} 存在")
        else:
            print(f"  ✗ 配置项 {config_key} 缺失")
            all_configs_valid = False
    
    return all_configs_valid

def explain_selenium_benefits():
    """解释Selenium的优势"""
    print("\n=== Selenium优势说明 ===")
    
    print("Selenium vs Requests:")
    print("  🔧 JavaScript支持:")
    print("    Selenium: ✓ 完全支持动态内容")
    print("    Requests: ✗ 只能获取静态HTML")
    
    print("  🛡️  反检测能力:")
    print("    Selenium: ✓ 模拟真实浏览器行为")
    print("    Requests: ✗ 容易被检测为机器人")
    
    print("  📊 内容处理:")
    print("    Selenium: ✓ 可以处理复杂交互")
    print("    Requests: ✗ 无法处理JavaScript渲染")
    
    print("  ⚡ 性能对比:")
    print("    Selenium: 较慢但功能强大")
    print("    Requests: 较快但功能有限")
    
    return True

if __name__ == "__main__":
    print("Selenium功能验证")
    print("=" * 50)
    
    # 验证集成
    integration_result = verify_selenium_integration()
    
    # 验证配置
    config_result = verify_selenium_config()
    
    # 解释优势
    benefits_result = explain_selenium_benefits()
    
    print("\n=== 验证总结 ===")
    if integration_result:
        print("✓ Selenium集成正确")
    if config_result:
        print("✓ Selenium配置完整")
    if benefits_result:
        print("✓ 功能优势已说明")
    
    if integration_result and config_result:
        print("\n🎉 Selenium功能已成功集成！")
        print("\n使用方法:")
        print("python app.py  # 自动使用Selenium")
        print("python test_selenium.py  # 测试Selenium功能")
    else:
        print("\n❌ 部分功能未正确集成")
    
    print("\n验证完成！") 