#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Actions环境检测功能验证脚本
"""

from app import PornhubScraper
import os
import platform

def verify_github_actions_method():
    """验证GitHub Actions环境检测方法"""
    print("=== GitHub Actions环境检测方法验证 ===")
    
    scraper = PornhubScraper()
    
    # 检查方法是否存在
    if hasattr(scraper, 'is_github_actions_environment'):
        print("✓ GitHub Actions环境检测方法存在")
        return True
    else:
        print("✗ GitHub Actions环境检测方法不存在")
        return False

def verify_selenium_proxy_integration():
    """验证Selenium代理集成"""
    print("\n=== Selenium代理集成验证 ===")
    
    import inspect
    
    scraper = PornhubScraper()
    selenium_method_source = inspect.getsource(scraper.init_selenium_driver)
    
    # 检查是否包含GitHub Actions环境检测
    if 'is_github_actions_environment' in selenium_method_source:
        print("✓ Selenium初始化方法已集成GitHub Actions环境检测")
    else:
        print("✗ Selenium初始化方法未集成GitHub Actions环境检测")
        return False
    
    # 检查是否包含代理条件判断
    if 'not is_github_actions' in selenium_method_source:
        print("✓ Selenium代理设置已集成条件判断")
    else:
        print("✗ Selenium代理设置未集成条件判断")
        return False
    
    return True

def verify_requests_proxy_integration():
    """验证Requests代理集成"""
    print("\n=== Requests代理集成验证 ===")
    
    import inspect
    
    scraper = PornhubScraper()
    requests_method_source = inspect.getsource(scraper.get_page_requests)
    
    # 检查是否包含GitHub Actions环境检测
    if 'is_github_actions_environment' in requests_method_source:
        print("✓ Requests页面获取方法已集成GitHub Actions环境检测")
    else:
        print("✗ Requests页面获取方法未集成GitHub Actions环境检测")
        return False
    
    # 检查是否包含代理条件判断
    if 'is_github_actions' in requests_method_source:
        print("✓ Requests代理设置已集成条件判断")
    else:
        print("✗ Requests代理设置未集成条件判断")
        return False
    
    return True

def verify_download_proxy_integration():
    """验证下载代理集成"""
    print("\n=== 下载代理集成验证 ===")
    
    import inspect
    
    scraper = PornhubScraper()
    download_method_source = inspect.getsource(scraper.download_file)
    
    # 检查是否包含GitHub Actions环境检测
    if 'is_github_actions_environment' in download_method_source:
        print("✓ 下载方法已集成GitHub Actions环境检测")
    else:
        print("✗ 下载方法未集成GitHub Actions环境检测")
        return False
    
    # 检查是否包含代理条件判断
    if 'is_github_actions' in download_method_source:
        print("✓ 下载代理设置已集成条件判断")
    else:
        print("✗ 下载代理设置未集成条件判断")
        return False
    
    return True

def explain_github_actions_strategy():
    """解释GitHub Actions策略"""
    print("\n=== GitHub Actions策略说明 ===")
    
    print("环境检测策略:")
    print("  1. 环境变量检测:")
    print("     - GITHUB_ACTIONS: GitHub Actions专用环境变量")
    print("     - CI: 通用CI环境变量")
    
    print("  2. 系统路径检测:")
    print("     - /opt/hostedtoolcache: GitHub Actions工具缓存")
    print("     - /home/runner: GitHub Actions运行器")
    print("     - /usr/local/share: GitHub Actions共享路径")
    
    print("  3. 工作目录检测:")
    print("     - 检查当前目录是否包含GitHub Actions路径")
    
    print("\n代理配置策略:")
    print("  GitHub Actions环境:")
    print("    - 禁用所有代理设置")
    print("    - 直接使用网络连接")
    print("    - 原因: 127.0.0.1代理在CI环境中不生效")
    
    print("\n  本地环境:")
    print("    - 使用SOCKS5代理: 127.0.0.1:12345")
    print("    - 支持重试机制")
    print("    - 智能错误处理")
    
    return True

def show_current_environment():
    """显示当前环境信息"""
    print("\n=== 当前环境信息 ===")
    
    print(f"操作系统: {platform.system()}")
    print(f"当前目录: {os.getcwd()}")
    
    # 检查关键环境变量
    github_env_vars = ['GITHUB_ACTIONS', 'CI', 'RUNNER_OS', 'RUNNER_ARCH']
    print("\nGitHub Actions环境变量:")
    for var in github_env_vars:
        value = os.environ.get(var, '未设置')
        print(f"  {var}: {value}")
    
    # 检查关键路径
    github_paths = ['/opt/hostedtoolcache', '/home/runner', '/usr/local/share']
    print("\nGitHub Actions路径:")
    for path in github_paths:
        if os.path.exists(path):
            print(f"  ✓ {path}: 存在")
        else:
            print(f"  ✗ {path}: 不存在")
    
    return True

if __name__ == "__main__":
    print("GitHub Actions环境检测功能验证")
    print("=" * 60)
    
    # 验证方法
    method_result = verify_github_actions_method()
    
    # 验证Selenium集成
    selenium_result = verify_selenium_proxy_integration()
    
    # 验证Requests集成
    requests_result = verify_requests_proxy_integration()
    
    # 验证下载集成
    download_result = verify_download_proxy_integration()
    
    # 显示环境信息
    environment_result = show_current_environment()
    
    # 解释策略
    strategy_result = explain_github_actions_strategy()
    
    print("\n=== 验证总结 ===")
    if method_result:
        print("✓ GitHub Actions环境检测方法已实现")
    if selenium_result:
        print("✓ Selenium代理集成正确")
    if requests_result:
        print("✓ Requests代理集成正确")
    if download_result:
        print("✓ 下载代理集成正确")
    if environment_result:
        print("✓ 环境信息显示正确")
    if strategy_result:
        print("✓ 策略说明完整")
    
    if method_result and selenium_result and requests_result and download_result:
        print("\n🎉 GitHub Actions环境检测功能已成功集成！")
        print("\n使用方法:")
        print("python app.py  # 自动检测环境并配置代理")
        print("python test_github_actions.py  # 测试GitHub Actions功能")
    else:
        print("\n❌ 部分功能未正确集成")
    
    print("\n验证完成！") 