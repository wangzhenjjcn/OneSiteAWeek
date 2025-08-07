#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试脚本 - 分析预览视频URL提取
"""

import requests
from bs4 import BeautifulSoup
from config import PROXY_CONFIG, HEADERS, BASE_URL, DEBUG

def analyze_html_structure():
    """分析HTML结构，找到预览视频URL的正确提取方式"""
    print("开始分析HTML结构...")
    
    # 获取页面内容
    url = f"{BASE_URL}/video?page=1"
    headers = HEADERS
    proxies = PROXY_CONFIG
    
    try:
        response = requests.get(url, headers=headers, proxies=proxies, timeout=30)
        response.raise_for_status()
        html_content = response.text
        
        soup = BeautifulSoup(html_content, 'html.parser')
        video_list = soup.find('ul', {'id': 'videoCategory'})
        
        if not video_list:
            print("未找到视频列表")
            return
        
        # 分析前3个视频的HTML结构
        videos_analyzed = 0
        for li in video_list.find_all('li', class_='pcVideoListItem'):
            if videos_analyzed >= 3:
                break
                
            print(f"\n=== 分析第 {videos_analyzed + 1} 个视频 ===")
            
            # 获取视频ID和viewkey
            video_id = li.get('data-video-id', '')
            viewkey = li.get('data-video-vkey', '')
            print(f"视频ID: {video_id}")
            print(f"ViewKey: {viewkey}")
            
            # 查找img元素
            img_element = li.find('img', class_='js-videoThumb')
            if img_element:
                print("找到img元素，分析其属性:")
                for attr, value in img_element.attrs.items():
                    if 'preview' in attr.lower() or 'video' in attr.lower() or 'media' in attr.lower():
                        print(f"  {attr}: {value[:100]}...")
                
                # 特别检查data-mediabook属性
                mediabook = img_element.get('data-mediabook', '')
                if mediabook:
                    print(f"  data-mediabook: {mediabook[:100]}...")
                else:
                    print("  data-mediabook: 未找到")
            
            # 查找所有可能的预览视频元素
            print("\n查找预览视频相关元素:")
            
            # 查找video元素
            video_elements = li.find_all('video')
            for i, video in enumerate(video_elements):
                print(f"  video元素 {i+1}:")
                for attr, value in video.attrs.items():
                    print(f"    {attr}: {value[:100]}...")
            
            # 查找source元素
            source_elements = li.find_all('source')
            for i, source in enumerate(source_elements):
                print(f"  source元素 {i+1}:")
                for attr, value in source.attrs.items():
                    print(f"    {attr}: {value[:100]}...")
            
            # 查找所有包含preview的data属性
            all_elements = li.find_all()
            preview_attrs = []
            for element in all_elements:
                for attr, value in element.attrs.items():
                    if 'preview' in attr.lower() and value:
                        preview_attrs.append((element.name, attr, value))
            
            if preview_attrs:
                print("\n找到包含preview的data属性:")
                for tag_name, attr, value in preview_attrs:
                    print(f"  {tag_name}.{attr}: {value[:100]}...")
            else:
                print("\n未找到包含preview的data属性")
            
            videos_analyzed += 1
        
        print(f"\n分析完成，共分析了 {videos_analyzed} 个视频")
        
    except Exception as e:
        print(f"分析失败: {e}")

def test_preview_extraction():
    """测试预览视频URL提取"""
    print("\n=== 测试预览视频URL提取 ===")
    
    from app import PornhubScraper
    
    scraper = PornhubScraper()
    url = f"{BASE_URL}/video?page=1"
    html_content = scraper.get_page(url)
    
    if html_content:
        videos = scraper.parse_video_list(html_content)
        print(f"找到 {len(videos)} 个视频")
        
        for i, video in enumerate(videos[:3]):
            print(f"\n视频 {i+1}:")
            print(f"  标题: {video['title'][:50]}...")
            print(f"  预览URL: {video['preview_url'][:100] if video['preview_url'] else '未找到'}...")
            print(f"  缩略图URL: {video['thumbnail_url'][:100] if video['thumbnail_url'] else '未找到'}...")

if __name__ == "__main__":
    print("预览视频URL调试工具")
    print("=" * 50)
    
    analyze_html_structure()
    test_preview_extraction()
    
    print("\n调试完成！") 