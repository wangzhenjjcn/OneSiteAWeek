#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频页面分析脚本 - 分析原始视频页面结构
"""

import requests
import re
import json
import time
from bs4 import BeautifulSoup
from config import PROXY_CONFIG, HEADERS, BASE_URL, SSL_CONFIG

# 禁用SSL警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def analyze_video_page(viewkey):
    """分析视频页面结构"""
    print(f"=== 分析视频页面: {viewkey} ===")
    
    # 构建视频页面URL
    video_url = f"https://cn.pornhub.com/view_video.php?viewkey={viewkey}"
    print(f"视频页面URL: {video_url}")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 获取视频页面
            kwargs = {
                'headers': HEADERS,
                'timeout': 30,
                'verify': False,
                'allow_redirects': True,
            }
            
            # 尝试不使用代理
            if attempt == 0:
                response = requests.get(video_url, **kwargs)
            else:
                # 后续尝试使用代理
                kwargs['proxies'] = PROXY_CONFIG
                response = requests.get(video_url, **kwargs)
            
            response.raise_for_status()
            html_content = response.text
            break
            
        except Exception as e:
            print(f"获取页面失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(3)  # 等待3秒后重试
            else:
                print(f"所有重试都失败了: {video_url}")
                return None
    
    print(f"✓ 页面获取成功，状态码: {response.status_code}")
    print(f"页面长度: {len(html_content)} 字符")
    
    # 保存HTML用于分析
    with open(f'video_page_{viewkey}.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"✓ HTML已保存到 video_page_{viewkey}.html")
    
    # 解析HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 1. 查找videoInfo元素（发布时间）
    video_info = soup.find('div', class_='videoInfo')
    if video_info:
        publish_time = video_info.get_text(strip=True)
        print(f"✓ 找到发布时间: {publish_time}")
    else:
        print("✗ 未找到videoInfo元素")
        publish_time = None
    
    # 2. 查找categoriesWrapper元素（分类数据）
    categories_wrapper = soup.find('div', class_='categoriesWrapper')
    if categories_wrapper:
        categories = []
        category_links = categories_wrapper.find_all('a')
        for link in category_links:
            category_name = link.get_text(strip=True)
            category_url = link.get('href', '')
            categories.append({
                'name': category_name,
                'url': category_url
            })
        print(f"✓ 找到分类数据: {len(categories)} 个分类")
        for cat in categories:
            print(f"  - {cat['name']}: {cat['url']}")
    else:
        print("✗ 未找到categoriesWrapper元素")
        categories = []
    
    # 3. 查找JavaScript中的m3u8地址
    print("\n=== 查找m3u8地址 ===")
    
    # 查找所有script标签
    scripts = soup.find_all('script')
    m3u8_urls = []
    
    for script in scripts:
        script_content = script.string
        if script_content:
            # 查找m3u8相关的URL
            m3u8_patterns = [
                r'https?://[^"\']*\.m3u8[^"\']*',
                r'https?://[^"\']*\.m3u8\?[^"\']*',
                r'"videoUrl":"([^"]*\.m3u8[^"]*)"',
                r"'videoUrl':'([^']*\.m3u8[^']*)'",
                r'"url":"([^"]*\.m3u8[^"]*)"',
                r"'url':'([^']*\.m3u8[^']*)'",
            ]
            
            for pattern in m3u8_patterns:
                matches = re.findall(pattern, script_content, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]  # 如果是分组匹配
                    if match not in m3u8_urls:
                        m3u8_urls.append(match)
                        print(f"✓ 找到m3u8地址: {match}")
    
    # 4. 查找其他可能的视频信息
    print("\n=== 查找其他视频信息 ===")
    
    # 查找video标签
    video_tags = soup.find_all('video')
    for i, video in enumerate(video_tags):
        print(f"视频标签 {i+1}:")
        print(f"  src: {video.get('src', 'N/A')}")
        print(f"  data-src: {video.get('data-src', 'N/A')}")
        print(f"  poster: {video.get('poster', 'N/A')}")
    
    # 查找包含视频信息的div
    video_divs = soup.find_all('div', class_=lambda x: x and 'video' in x.lower())
    for div in video_divs:
        print(f"视频相关div: {div.get('class', [])}")
    
    return {
        'publish_time': publish_time,
        'categories': categories,
        'm3u8_urls': m3u8_urls,
        'html_content': html_content
    }

def test_multiple_videos():
    """测试多个视频页面"""
    print("\n=== 测试多个视频页面 ===")
    
    # 测试用的viewkey列表
    test_viewkeys = [
        '686b24c4659e9',  # 从之前的测试中获取的
        '67a33ee3e909d',  # 另一个测试用的
    ]
    
    for viewkey in test_viewkeys:
        print(f"\n测试视频: {viewkey}")
        result = analyze_video_page(viewkey)
        
        if result:
            print(f"分析结果:")
            print(f"  发布时间: {result['publish_time']}")
            print(f"  分类数量: {len(result['categories'])}")
            print(f"  m3u8地址数量: {len(result['m3u8_urls'])}")
        else:
            print("分析失败")

def find_m3u8_in_html(html_content):
    """在HTML内容中查找m3u8地址"""
    print("\n=== 在HTML中查找m3u8地址 ===")
    
    # 查找所有可能的m3u8模式
    patterns = [
        r'https?://[^"\']*\.m3u8[^"\']*',
        r'"videoUrl":"([^"]*\.m3u8[^"]*)"',
        r"'videoUrl':'([^']*\.m3u8[^']*)'",
        r'"url":"([^"]*\.m3u8[^"]*)"',
        r"'url':'([^']*\.m3u8[^']*)'",
        r'"src":"([^"]*\.m3u8[^"]*)"',
        r"'src':'([^']*\.m3u8[^']*)'",
    ]
    
    found_urls = []
    
    for pattern in patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                match = match[0]
            if match and match not in found_urls:
                found_urls.append(match)
                print(f"✓ 找到m3u8: {match}")
    
    return found_urls

if __name__ == "__main__":
    print("视频页面分析测试")
    print("=" * 50)
    
    # 测试单个视频页面
    test_viewkey = '686b24c4659e9'
    result = analyze_video_page(test_viewkey)
    
    if result:
        print(f"\n=== 分析总结 ===")
        print(f"发布时间: {result['publish_time']}")
        print(f"分类数量: {len(result['categories'])}")
        print(f"m3u8地址数量: {len(result['m3u8_urls'])}")
        
        # 测试多个视频
        test_multiple_videos()
    else:
        print("分析失败")
    
    print("\n分析完成！") 