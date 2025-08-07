#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查实际HTML结构
"""

import requests
from bs4 import BeautifulSoup
from config import PROXY_CONFIG, HEADERS, BASE_URL

def check_real_html():
    """检查实际HTML结构"""
    print("检查实际HTML结构...")
    
    url = f"{BASE_URL}/video?page=1"
    
    try:
        # 使用代理获取页面
        response = requests.get(url, headers=HEADERS, proxies=PROXY_CONFIG, timeout=30, verify=False)
        response.raise_for_status()
        html_content = response.text
        
        print(f"✓ 成功获取页面，长度: {len(html_content)}")
        
        # 保存HTML内容
        with open('real_page.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        print("✓ HTML内容已保存到 real_page.html")
        
        # 解析HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 查找视频列表
        video_list = soup.find('ul', {'id': 'videoCategory'})
        if video_list:
            print("✓ 找到视频列表")
            videos = video_list.find_all('li', class_='pcVideoListItem')
            print(f"找到 {len(videos)} 个视频")
            
            # 分析第一个视频
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
                
                # 查找上传者信息
                print("\n=== 上传者信息 ===")
                uploader_elements = first_video.find_all(['a', 'span'], class_=lambda x: x and ('username' in x.lower() or 'model' in x.lower()))
                for elem in uploader_elements:
                    print(f"  {elem.name}.{elem.get('class', [])}: {elem.get_text(strip=True)}")
                
                # 查找时间信息
                print("\n=== 时间信息 ===")
                added_element = first_video.find('var', class_='added')
                if added_element:
                    print(f"  上传时间: {added_element.get_text(strip=True)}")
                
                # 查找观看次数
                print("\n=== 观看次数 ===")
                views_element = first_video.find('span', class_='views')
                if views_element:
                    print(f"  观看次数: {views_element.get_text(strip=True)}")
                
        else:
            print("✗ 未找到视频列表")
            
    except Exception as e:
        print(f"✗ 获取页面失败: {e}")

if __name__ == "__main__":
    check_real_html() 