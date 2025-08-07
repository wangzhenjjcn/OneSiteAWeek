#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分页分析脚本 - 分析showingCounter结构
"""

import requests
import re
from bs4 import BeautifulSoup
from config import PROXY_CONFIG, HEADERS, BASE_URL

def analyze_showing_counter():
    """分析showingCounter的结构"""
    print("=== 分析showingCounter结构 ===")
    
    # 测试第1页
    url = f"{BASE_URL}?page=1"
    print(f"测试URL: {url}")
    
    try:
        response = requests.get(url, headers=HEADERS, proxies=PROXY_CONFIG, timeout=30, verify=False)
        response.raise_for_status()
        html_content = response.text
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 查找showingCounter
        showing_counter = soup.find('div', class_='showingCounter')
        if showing_counter:
            counter_text = showing_counter.get_text(strip=True)
            print(f"找到showingCounter: {counter_text}")
            
            # 使用正则表达式提取数字
            # 匹配格式：显示1-32个，共有749个
            pattern = r'显示(\d+)-(\d+)个，共有(\d+)个'
            match = re.search(pattern, counter_text)
            
            if match:
                start_num = int(match.group(1))
                end_num = int(match.group(2))
                total_num = int(match.group(3))
                
                print(f"解析结果:")
                print(f"  当前显示范围: {start_num}-{end_num}")
                print(f"  总数量: {total_num}")
                print(f"  是否为最后一页: {end_num == total_num}")
                
                # 计算总页数
                items_per_page = end_num - start_num + 1
                total_pages = (total_num + items_per_page - 1) // items_per_page
                print(f"  每页项目数: {items_per_page}")
                print(f"  总页数: {total_pages}")
                
                return {
                    'start': start_num,
                    'end': end_num,
                    'total': total_num,
                    'is_last_page': end_num == total_num,
                    'items_per_page': items_per_page,
                    'total_pages': total_pages
                }
            else:
                print("✗ 无法解析showingCounter文本格式")
                return None
        else:
            print("✗ 未找到showingCounter元素")
            return None
            
    except Exception as e:
        print(f"✗ 分析失败: {e}")
        return None

def test_multiple_pages():
    """测试多个页面的showingCounter"""
    print("\n=== 多页面showingCounter测试 ===")
    
    for page in range(1, 6):  # 测试前5页
        url = f"{BASE_URL}?page={page}"
        print(f"\n测试第 {page} 页: {url}")
        
        try:
            response = requests.get(url, headers=HEADERS, proxies=PROXY_CONFIG, timeout=30, verify=False)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            showing_counter = soup.find('div', class_='showingCounter')
            
            if showing_counter:
                counter_text = showing_counter.get_text(strip=True)
                print(f"  showingCounter: {counter_text}")
                
                # 解析数字
                pattern = r'显示(\d+)-(\d+)个，共有(\d+)个'
                match = re.search(pattern, counter_text)
                
                if match:
                    start_num = int(match.group(1))
                    end_num = int(match.group(2))
                    total_num = int(match.group(3))
                    
                    is_last = end_num == total_num
                    print(f"  范围: {start_num}-{end_num}, 总数: {total_num}")
                    print(f"  是否最后一页: {'是' if is_last else '否'}")
                else:
                    print("  ✗ 无法解析格式")
            else:
                print("  ✗ 未找到showingCounter")
                
        except Exception as e:
            print(f"  ✗ 获取失败: {e}")

if __name__ == "__main__":
    print("分页分析测试")
    print("=" * 50)
    
    # 分析showingCounter结构
    result = analyze_showing_counter()
    
    if result:
        print(f"\n✓ 分析成功！")
        print(f"总页数: {result['total_pages']}")
        print(f"每页项目数: {result['items_per_page']}")
        
        # 测试多个页面
        test_multiple_pages()
    else:
        print("\n✗ 分析失败")
    
    print("\n分析完成！") 