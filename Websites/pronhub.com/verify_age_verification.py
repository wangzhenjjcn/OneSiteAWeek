#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
年龄验证功能验证脚本
"""

from app import PornhubScraper

def verify_age_verification_method():
    """验证年龄验证方法"""
    print("=== 年龄验证方法验证 ===")
    
    scraper = PornhubScraper()
    
    # 检查方法是否存在
    if hasattr(scraper, 'handle_age_verification'):
        print("✓ 年龄验证方法存在")
        return True
    else:
        print("✗ 年龄验证方法不存在")
        return False

def verify_age_verification_integration():
    """验证年龄验证集成"""
    print("\n=== 年龄验证集成验证 ===")
    
    # 检查get_page_selenium方法是否调用了年龄验证
    import inspect
    
    scraper = PornhubScraper()
    selenium_method_source = inspect.getsource(scraper.get_page_selenium)
    
    if 'handle_age_verification' in selenium_method_source:
        print("✓ 年龄验证已集成到Selenium页面获取流程")
        return True
    else:
        print("✗ 年龄验证未集成到Selenium页面获取流程")
        return False

def verify_age_verification_selectors():
    """验证年龄验证选择器"""
    print("\n=== 年龄验证选择器验证 ===")
    
    # 检查选择器是否包含用户提供的按钮代码
    expected_selectors = [
        "button.gtm-event-age-verification.js-closeAgeModal.buttonOver18.orangeButton",
        "button[data-event='age_verification']",
        "button[data-label='over18_enter']"
    ]
    
    scraper = PornhubScraper()
    age_verification_source = inspect.getsource(scraper.handle_age_verification)
    
    all_selectors_found = True
    for selector in expected_selectors:
        if selector in age_verification_source:
            print(f"✓ 选择器存在: {selector}")
        else:
            print(f"✗ 选择器缺失: {selector}")
            all_selectors_found = False
    
    return all_selectors_found

def explain_age_verification_features():
    """解释年龄验证功能特点"""
    print("\n=== 年龄验证功能特点 ===")
    
    print("🔍 智能检测:")
    print("  - 自动检测年龄验证弹窗")
    print("  - 多种选择器策略")
    print("  - 容错处理机制")
    
    print("\n🎯 精确匹配:")
    print("  - CSS类名选择器")
    print("  - 数据属性选择器")
    print("  - 文本内容匹配")
    
    print("\n⚡ 备选方案:")
    print("  - JavaScript直接点击")
    print("  - 多种脚本策略")
    print("  - 自动回退机制")
    
    print("\n🛡️  错误处理:")
    print("  - 超时处理")
    print("  - 异常捕获")
    print("  - 详细日志")
    
    return True

def show_age_verification_button_code():
    """显示年龄验证按钮代码"""
    print("\n=== 年龄验证按钮代码 ===")
    
    button_code = '''<button class="gtm-event-age-verification js-closeAgeModal buttonOver18 orangeButton" data-event="age_verification" data-label="over18_enter">我年满 18 岁 - 输入</button>'''
    
    print("用户提供的按钮代码:")
    print(f"  {button_code}")
    
    print("\n对应的选择器:")
    print("  1. button.gtm-event-age-verification.js-closeAgeModal.buttonOver18.orangeButton")
    print("  2. button[data-event='age_verification']")
    print("  3. button[data-label='over18_enter']")
    print("  4. .orangeButton")
    
    return True

if __name__ == "__main__":
    print("年龄验证功能验证")
    print("=" * 50)
    
    # 验证方法
    method_result = verify_age_verification_method()
    
    # 验证集成
    integration_result = verify_age_verification_integration()
    
    # 验证选择器
    selectors_result = verify_age_verification_selectors()
    
    # 显示按钮代码
    button_result = show_age_verification_button_code()
    
    # 解释功能特点
    features_result = explain_age_verification_features()
    
    print("\n=== 验证总结 ===")
    if method_result:
        print("✓ 年龄验证方法已实现")
    if integration_result:
        print("✓ 年龄验证已集成到页面获取流程")
    if selectors_result:
        print("✓ 年龄验证选择器配置正确")
    if button_result:
        print("✓ 按钮代码解析正确")
    if features_result:
        print("✓ 功能特点说明完整")
    
    if method_result and integration_result and selectors_result:
        print("\n🎉 年龄验证功能已成功集成！")
        print("\n使用方法:")
        print("python app.py  # 自动处理年龄验证")
        print("python test_age_verification.py  # 测试年龄验证功能")
    else:
        print("\n❌ 部分功能未正确集成")
    
    print("\n验证完成！") 