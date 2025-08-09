#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新生成HTML页面，添加m3u8播放功能
"""

import os
import json
import re
from app import PornhubScraper

def extract_video_data_from_log(log_filepath):
    """从采集日志中提取视频数据"""
    try:
        with open(log_filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取基本信息
        viewkey_match = re.search(r'ViewKey: (.+)', content)
        title_match = re.search(r'视频标题: (.+)', content)
        video_url_match = re.search(r'视频链接: (.+)', content)
        
        if not all([viewkey_match, title_match, video_url_match]):
            return None
        
        viewkey = viewkey_match.group(1).strip()
        title = title_match.group(1).strip()
        video_url = video_url_match.group(1).strip()
        
        # 检查是否有m3u8地址
        has_m3u8 = 'm3u8地址: 已获取' in content
        
        # 构建视频数据
        video_data = {
            'title': title,
            'video_id': '',
            'viewkey': viewkey,
            'duration': 'N/A',
            'uploader': 'N/A',
            'views': 'N/A',
            'video_url': video_url,
            'alt_text': title,
            'publish_time': 'N/A',
            'categories': [],
            'm3u8_urls': [],
            'best_m3u8_url': ''
        }
        
        # 如果有m3u8地址，尝试从其他文件获取
        if has_m3u8:
            # 这里可以添加从其他文件获取m3u8地址的逻辑
            # 暂时使用占位符
            video_data['m3u8_urls'] = ['https://example.com/video.m3u8']
            video_data['best_m3u8_url'] = 'https://example.com/video.m3u8'
        
        return video_data
        
    except Exception as e:
        print(f"解析日志文件失败 {log_filepath}: {e}")
        return None

def regenerate_html_pages():
    """重新生成所有HTML页面"""
    print("=== 重新生成HTML页面，添加M3U8播放功能 ===")
    
    data_dir = 'data'
    if not os.path.exists(data_dir):
        print("数据目录不存在")
        return
    
    # 创建scraper实例
    scraper = PornhubScraper(use_selenium=False)
    
    # 遍历所有采集数据目录
    processed_count = 0
    success_count = 0
    
    for item in os.listdir(data_dir):
        item_path = os.path.join(data_dir, item)
        if os.path.isdir(item_path):
            log_filepath = os.path.join(item_path, 'collection_log.txt')
            
            if os.path.exists(log_filepath):
                processed_count += 1
                print(f"\n处理目录: {item}")
                
                # 从日志中提取视频数据
                video_data = extract_video_data_from_log(log_filepath)
                
                if video_data:
                    try:
                        # 重新生成HTML页面
                        html_filepath = scraper.create_html_page(video_data, item_path)
                        
                        if os.path.exists(html_filepath):
                            print(f"✓ 成功重新生成: {html_filepath}")
                            success_count += 1
                        else:
                            print(f"✗ 生成失败: {html_filepath}")
                    except Exception as e:
                        print(f"✗ 处理失败: {e}")
                else:
                    print(f"✗ 无法提取视频数据")
    
    print(f"\n=== 处理完成 ===")
    print(f"总处理数量: {processed_count}")
    print(f"成功数量: {success_count}")
    print(f"失败数量: {processed_count - success_count}")

if __name__ == "__main__":
    regenerate_html_pages() 