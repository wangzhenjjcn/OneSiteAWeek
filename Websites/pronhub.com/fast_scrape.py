#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速采集脚本
"""

from app import PornhubScraper
from config import DEBUG, SELENIUM_CONFIG, SCRAPER_CONFIG
import time

def fast_scrape():
    """快速采集模式"""
    print("=== 快速采集模式 ===")
    
    try:
        # 创建快速模式的抓取器
        scraper = PornhubScraper(use_selenium=True)
        
        if not scraper.use_selenium or not scraper.driver:
            print("✗ Selenium初始化失败，尝试使用requests模式")
            scraper = PornhubScraper(use_selenium=False)
        
        print("✓ 抓取器初始化成功")
        print(f"  使用Selenium: {scraper.use_selenium}")
        print(f"  快速模式: {SELENIUM_CONFIG.get('fast_mode', True)}")
        print(f"  页面加载超时: {SELENIUM_CONFIG.get('page_load_timeout', 10)} 秒")
        print(f"  显式等待时间: {SELENIUM_CONFIG.get('explicit_wait', 8)} 秒")
        
        # 测试快速访问
        test_url = "https://cn.pornhub.com/language/chinese?page=1"
        print(f"\n测试快速访问: {test_url}")
        
        start_time = time.time()
        html_content = scraper.get_page(test_url)
        end_time = time.time()
        
        if html_content:
            access_time = end_time - start_time
            print(f"✓ 快速访问成功")
            print(f"  页面大小: {len(html_content)} 字符")
            print(f"  访问时间: {access_time:.2f} 秒")
            
            if access_time < 15:
                print("✓ 访问速度良好")
            else:
                print("⚠️  访问速度较慢")
            
            # 解析视频列表
            print("\n解析视频列表...")
            videos = scraper.parse_video_list(html_content)
            print(f"✓ 找到 {len(videos)} 个视频")
            
            if videos:
                print("前3个视频:")
                for i, video in enumerate(videos[:3], 1):
                    print(f"  {i}. {video.get('title', 'N/A')[:50]}...")
            
            return True
        else:
            print("✗ 快速访问失败")
            return False
            
    except Exception as e:
        print(f"✗ 快速采集出错: {e}")
        return False
    finally:
        if 'scraper' in locals():
            scraper.close_driver()

def test_requests_fallback():
    """测试requests回退模式"""
    print("\n=== Requests回退模式测试 ===")
    
    try:
        scraper = PornhubScraper(use_selenium=False)
        
        test_url = "https://cn.pornhub.com/language/chinese?page=1"
        print(f"测试requests访问: {test_url}")
        
        start_time = time.time()
        html_content = scraper.get_page(test_url)
        end_time = time.time()
        
        if html_content:
            access_time = end_time - start_time
            print(f"✓ Requests访问成功")
            print(f"  页面大小: {len(html_content)} 字符")
            print(f"  访问时间: {access_time:.2f} 秒")
            
            # 解析视频列表
            videos = scraper.parse_video_list(html_content)
            print(f"✓ 找到 {len(videos)} 个视频")
            
            return True
        else:
            print("✗ Requests访问失败")
            return False
            
    except Exception as e:
        print(f"✗ Requests回退测试出错: {e}")
        return False

def show_optimization_tips():
    """显示优化建议"""
    print("\n=== 快速采集优化建议 ===")
    
    print("1. 如果Selenium太慢:")
    print("   - 使用requests模式")
    print("   - 启用快速模式")
    print("   - 减少等待时间")
    
    print("\n2. 如果页面加载超时:")
    print("   - 检查网络连接")
    print("   - 尝试使用代理")
    print("   - 增加重试次数")
    
    print("\n3. 如果SSL错误:")
    print("   - 已启用SSL忽略")
    print("   - 检查代理设置")
    print("   - 尝试不同代理")
    
    print("\n4. 性能优化:")
    print("   - 禁用图片加载")
    print("   - 禁用JavaScript")
    print("   - 使用无头模式")
    
    return True

if __name__ == "__main__":
    print("快速采集测试")
    print("=" * 50)
    
    # 测试快速采集
    fast_result = fast_scrape()
    
    # 测试requests回退
    requests_result = test_requests_fallback()
    
    # 显示优化建议
    tips_result = show_optimization_tips()
    
    print("\n=== 测试总结 ===")
    if fast_result:
        print("✓ 快速采集模式正常")
    if requests_result:
        print("✓ Requests回退模式正常")
    if tips_result:
        print("✓ 优化建议完整")
    
    print("\n快速采集测试完成！")
    print("\n如果Selenium太慢，可以:")
    print("1. 修改config.py中的fast_mode为True")
    print("2. 使用requests模式: scraper = PornhubScraper(use_selenium=False)")
    print("3. 减少等待时间设置") 