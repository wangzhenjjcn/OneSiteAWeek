#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查HTML内容，了解网站结构
"""

import requests
from bs4 import BeautifulSoup
from config import PROXY_CONFIG, HEADERS, BASE_URL

def check_html_structure():
    """检查HTML结构"""
    print("检查HTML结构...")
    
    url = f"{BASE_URL}/video?page=1"
    
    try:
        # 尝试不使用代理
        print("尝试不使用代理...")
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        html_content = response.text
        
        print(f"✓ 不使用代理成功获取页面，长度: {len(html_content)}")
        
    except Exception as e:
        print(f"✗ 不使用代理失败: {e}")
        
        try:
            # 尝试使用代理
            print("尝试使用代理...")
            response = requests.get(url, headers=HEADERS, proxies=PROXY_CONFIG, timeout=30)
            response.raise_for_status()
            html_content = response.text
            
            print(f"✓ 使用代理成功获取页面，长度: {len(html_content)}")
            
        except Exception as e2:
            print(f"✗ 使用代理也失败: {e2}")
            return
    
    # 保存HTML内容到文件
    with open('debug_page.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("✓ HTML内容已保存到 debug_page.html")
    
    # 解析HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 查找视频列表
    video_list = soup.find('ul', {'id': 'videoCategory'})
    if video_list:
        print("✓ 找到视频列表")
        videos = video_list.find_all('li', class_='pcVideoListItem')
        print(f"找到 {len(videos)} 个视频")
        
        # 分析第一个视频的HTML结构
        if videos:
            first_video = videos[0]
            print("\n=== 第一个视频的HTML结构 ===")
            
            # 查找img元素
            img_elements = first_video.find_all('img')
            print(f"找到 {len(img_elements)} 个img元素")
            
            for i, img in enumerate(img_elements):
                print(f"\nimg元素 {i+1}:")
                print(f"  class: {img.get('class', [])}")
                print(f"  src: {img.get('src', '')[:100]}...")
                print(f"  alt: {img.get('alt', '')[:50]}...")
                
                # 检查所有data属性
                data_attrs = {k: v for k, v in img.attrs.items() if k.startswith('data-')}
                if data_attrs:
                    print("  data属性:")
                    for attr, value in data_attrs.items():
                        print(f"    {attr}: {value[:100]}...")
            
            # 查找所有链接
            links = first_video.find_all('a')
            print(f"\n找到 {len(links)} 个链接")
            
            for i, link in enumerate(links):
                print(f"\n链接 {i+1}:")
                print(f"  href: {link.get('href', '')[:100]}...")
                print(f"  class: {link.get('class', [])}")
                
                # 检查所有data属性
                data_attrs = {k: v for k, v in link.attrs.items() if k.startswith('data-')}
                if data_attrs:
                    print("  data属性:")
                    for attr, value in data_attrs.items():
                        print(f"    {attr}: {value[:100]}...")
    else:
        print("✗ 未找到视频列表")
        
        # 查找其他可能的视频容器
        possible_containers = soup.find_all(['ul', 'div'], class_=lambda x: x and ('video' in x.lower() or 'list' in x.lower()))
        print(f"找到 {len(possible_containers)} 个可能的视频容器")
        
        for i, container in enumerate(possible_containers[:3]):
            print(f"\n容器 {i+1}:")
            print(f"  tag: {container.name}")
            print(f"  class: {container.get('class', [])}")
            print(f"  id: {container.get('id', '')}")

if __name__ == "__main__":
    check_html_structure() 