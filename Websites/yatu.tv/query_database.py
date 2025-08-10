#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from database_manager import YatuTVDatabase

def main():
    """查询数据库工具"""
    db = YatuTVDatabase()
    
    print("=== 雅图TV数据库查询工具 ===")
    print("1. 查看数据库统计信息")
    print("2. 查看指定剧集的详情页HTML")
    print("3. 查看所有剧集列表")
    print("4. 退出")
    
    while True:
        choice = input("\n请选择功能 (1-4): ").strip()
        
        if choice == '1':
            show_stats(db)
        elif choice == '2':
            show_series_html(db)
        elif choice == '3':
            show_all_series(db)
        elif choice == '4':
            print("退出程序")
            break
        else:
            print("无效选择，请重新输入")

def show_stats(db):
    """显示数据库统计信息"""
    try:
        stats = db.get_series_stats()
        print(f"\n数据库统计信息:")
        print(f"剧集总数: {stats['series_count']}")
        print(f"集数总数: {stats['episodes_count']}")
        print(f"成功抓取的集数: {stats['successful_episodes']}")
        print(f"成功率: {stats['success_rate']:.2f}%")
    except Exception as e:
        print(f"获取统计信息失败: {e}")

def show_series_html(db):
    """查看指定剧集的详情页HTML"""
    series_id = input("请输入剧集ID (如: m0371): ").strip()
    if not series_id:
        print("剧集ID不能为空")
        return
    
    html_content = db.get_detail_html(series_id)
    if html_content:
        print(f"\n剧集 {series_id} 的详情页HTML:")
        print("=" * 50)
        print(html_content[:1000] + "..." if len(html_content) > 1000 else html_content)
        print("=" * 50)
        
        # 保存到文件
        save_choice = input("是否保存到文件? (y/n): ").strip().lower()
        if save_choice == 'y':
            filename = f"{series_id}_detail.html"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"已保存到文件: {filename}")
    else:
        print(f"未找到剧集 {series_id} 的详情页HTML")

def show_all_series(db):
    """查看所有剧集列表"""
    try:
        import sqlite3
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT series_id, title, category, crawl_time 
        FROM series 
        ORDER BY crawl_time DESC 
        LIMIT 20
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        if results:
            print(f"\n最近抓取的20个剧集:")
            print("-" * 80)
            print(f"{'剧集ID':<15} {'标题':<30} {'分类':<10} {'抓取时间':<20}")
            print("-" * 80)
            
            for row in results:
                series_id, title, category, crawl_time = row
                title = title[:28] + ".." if len(title) > 30 else title
                print(f"{series_id:<15} {title:<30} {category:<10} {crawl_time:<20}")
        else:
            print("数据库中没有剧集数据")
            
    except Exception as e:
        print(f"查询失败: {e}")

if __name__ == "__main__":
    main() 