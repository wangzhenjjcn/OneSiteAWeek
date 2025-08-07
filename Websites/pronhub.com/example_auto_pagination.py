#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动分页功能示例脚本
"""

from app import PornhubScraper

def example_auto_pagination():
    """示例：自动检测最后一页并抓取所有数据"""
    print("=== 示例1: 自动抓取所有页面 ===")
    
    scraper = PornhubScraper()
    
    # 自动检测最后一页并抓取所有数据
    videos = scraper.scrape_pages(start_page=1, end_page=None, auto_detect_last=True)
    print(f"总共抓取到 {len(videos)} 个视频")
    
    return videos

def example_limited_pages():
    """示例：只抓取前5页"""
    print("\n=== 示例2: 只抓取前5页 ===")
    
    scraper = PornhubScraper()
    
    # 只抓取前5页
    videos = scraper.scrape_pages(start_page=1, end_page=5, auto_detect_last=False)
    print(f"总共抓取到 {len(videos)} 个视频")
    
    return videos

def example_custom_range():
    """示例：抓取指定范围的页面"""
    print("\n=== 示例3: 抓取第3-7页 ===")
    
    scraper = PornhubScraper()
    
    # 抓取第3-7页
    videos = scraper.scrape_pages(start_page=3, end_page=7, auto_detect_last=False)
    print(f"总共抓取到 {len(videos)} 个视频")
    
    return videos

def example_single_page():
    """示例：只抓取第1页"""
    print("\n=== 示例4: 只抓取第1页 ===")
    
    scraper = PornhubScraper()
    
    # 只抓取第1页
    videos = scraper.scrape_pages(start_page=1, end_page=1, auto_detect_last=False)
    print(f"总共抓取到 {len(videos)} 个视频")
    
    return videos

if __name__ == "__main__":
    print("自动分页功能示例")
    print("=" * 50)
    
    # 注意：这些示例只进行抓取，不进行下载和保存
    # 如果要完整运行，请使用 app.py
    
    print("选择示例:")
    print("1. 自动抓取所有页面")
    print("2. 只抓取前5页")
    print("3. 抓取第3-7页")
    print("4. 只抓取第1页")
    
    choice = input("请输入选择 (1-4): ").strip()
    
    if choice == "1":
        example_auto_pagination()
    elif choice == "2":
        example_limited_pages()
    elif choice == "3":
        example_custom_range()
    elif choice == "4":
        example_single_page()
    else:
        print("无效选择，运行默认示例（自动抓取所有页面）")
        example_auto_pagination()
    
    print("\n示例运行完成！")
    print("注意：这些示例只进行抓取，不进行下载和保存。")
    print("要完整运行（包括下载和保存），请使用 python app.py") 