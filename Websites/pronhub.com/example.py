#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pornhub视频抓取器使用示例
"""

from app import PornhubScraper
from config import SCRAPER_CONFIG

def example_basic_usage():
    """基本使用示例"""
    print("=== 基本使用示例 ===")
    
    # 创建抓取器实例
    scraper = PornhubScraper()
    
    # 使用默认配置运行
    scraper.run()

def example_custom_pages():
    """自定义页数示例"""
    print("\n=== 自定义页数示例 ===")
    
    scraper = PornhubScraper()
    
    # 只抓取第1-3页
    scraper.run(start_page=1, end_page=3)

def example_single_page():
    """单页抓取示例"""
    print("\n=== 单页抓取示例 ===")
    
    scraper = PornhubScraper()
    
    # 只抓取第2页
    videos = scraper.scrape_pages(start_page=2, end_page=2)
    print(f"第2页找到 {len(videos)} 个视频")
    
    # 处理前3个视频
    for i, video in enumerate(videos[:3]):
        print(f"处理视频 {i+1}: {video['title'][:50]}...")
        scraper.process_video(video)

def example_test_mode():
    """测试模式示例"""
    print("\n=== 测试模式示例 ===")
    
    scraper = PornhubScraper()
    
    # 测试页面获取
    url = "https://cn.pornhub.com/video?page=1"
    html = scraper.get_page(url)
    
    if html:
        print("✓ 页面获取成功")
        videos = scraper.parse_video_list(html)
        print(f"✓ 解析到 {len(videos)} 个视频")
        
        if videos:
            print(f"第一个视频标题: {videos[0]['title'][:50]}...")
    else:
        print("✗ 页面获取失败")

if __name__ == "__main__":
    print("Pornhub视频抓取器使用示例")
    print("=" * 50)
    
    # 运行各种示例
    example_test_mode()
    example_single_page()
    example_custom_pages()
    example_basic_usage()
    
    print("\n所有示例运行完成！") 