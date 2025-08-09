#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库查看器 - 用于查询和导出视频数据
"""

import argparse
import json
from database_manager import DatabaseManager

def show_statistics():
    """显示数据库统计信息"""
    db = DatabaseManager()
    stats = db.get_statistics()
    
    print("=" * 60)
    print("📊 数据库统计信息")
    print("=" * 60)
    print(f"总视频数: {stats['total_videos']}")
    print(f"总分类数: {stats['total_categories']}")
    print(f"最新采集时间: {stats['latest_collection']}")
    
    print(f"\n🔥 热门上传者 (前10):")
    for i, uploader in enumerate(stats['top_uploaders'][:10], 1):
        print(f"  {i:2d}. {uploader['uploader']:<30} ({uploader['count']} 个视频)")
    
    print(f"\n🏷️  热门分类 (前10):")
    for i, category in enumerate(stats['top_categories'][:10], 1):
        print(f"  {i:2d}. {category['name']:<20} ({category['count']} 个视频)")

def search_videos(query, limit=20):
    """搜索视频"""
    db = DatabaseManager()
    videos = db.search_videos(query=query, limit=limit)
    
    print("=" * 60)
    print(f"🔍 搜索结果: '{query}' (前{limit}条)")
    print("=" * 60)
    
    if not videos:
        print("未找到匹配的视频")
        return
    
    for i, video in enumerate(videos, 1):
        print(f"\n{i:2d}. {video['title']}")
        print(f"    ID: {video['video_id']}")
        print(f"    上传者: {video['uploader'] or 'N/A'}")
        print(f"    观看数: {video['views'] or 'N/A'}")
        print(f"    时长: {video['duration'] or 'N/A'}")
        print(f"    采集时间: {video['created_at']}")

def list_recent_videos(limit=20):
    """列出最近采集的视频"""
    db = DatabaseManager()
    videos = db.search_videos(limit=limit)
    
    print("=" * 60)
    print(f"📺 最近采集的视频 (前{limit}条)")
    print("=" * 60)
    
    for i, video in enumerate(videos, 1):
        print(f"\n{i:2d}. {video['title']}")
        print(f"    ID: {video['video_id']}")
        print(f"    上传者: {video['uploader'] or 'N/A'}")
        print(f"    观看数: {video['views'] or 'N/A'}")
        print(f"    采集时间: {video['created_at']}")

def export_data(output_file, limit=None):
    """导出数据到JSON文件"""
    db = DatabaseManager()
    
    try:
        db.export_to_json(output_file, limit=limit)
        print(f"✅ 数据导出成功: {output_file}")
    except Exception as e:
        print(f"❌ 导出失败: {e}")

def show_video_detail(video_id):
    """显示视频详细信息"""
    db = DatabaseManager()
    video = db.get_video_by_id(video_id)
    
    if not video:
        print(f"❌ 未找到视频: {video_id}")
        return
    
    print("=" * 60)
    print("📺 视频详细信息")
    print("=" * 60)
    print(f"标题: {video['title']}")
    print(f"视频ID: {video['video_id']}")
    print(f"原始链接: {video['original_url']}")
    print(f"上传者: {video['uploader'] or 'N/A'}")
    print(f"观看数: {video['views'] or 'N/A'}")
    print(f"时长: {video['duration'] or 'N/A'}")
    print(f"发布时间: {video['publish_time'] or 'N/A'}")
    print(f"最佳M3U8: {video['best_m3u8_url'] or 'N/A'}")
    print(f"缩略图URL: {video['thumbnail_url'] or 'N/A'}")
    print(f"预览视频URL: {video['preview_url'] or 'N/A'}")
    print(f"采集时间: {video['created_at']}")
    print(f"更新时间: {video['updated_at']}")
    
    if video.get('categories'):
        categories = [cat['name'] for cat in video['categories']]
        print(f"分类: {', '.join(categories)}")
    
    if video.get('m3u8_urls'):
        print(f"\n📹 可用M3U8链接 ({len(video['m3u8_urls'])}个):")
        for i, url in enumerate(video['m3u8_urls'], 1):
            print(f"  {i}. {url}")

def main():
    parser = argparse.ArgumentParser(description='Pornhub视频数据库查看器')
    parser.add_argument('--stats', action='store_true', help='显示数据库统计信息')
    parser.add_argument('--search', type=str, help='搜索视频 (关键词)')
    parser.add_argument('--recent', type=int, default=20, help='显示最近采集的视频 (默认20条)')
    parser.add_argument('--detail', type=str, help='显示指定视频的详细信息 (视频ID)')
    parser.add_argument('--export', type=str, help='导出数据到JSON文件')
    parser.add_argument('--limit', type=int, help='限制查询/导出的记录数')
    
    args = parser.parse_args()
    
    if args.stats:
        show_statistics()
    elif args.search:
        search_videos(args.search, limit=args.limit or 20)
    elif args.detail:
        show_video_detail(args.detail)
    elif args.export:
        export_data(args.export, limit=args.limit)
    else:
        # 默认显示最近的视频
        list_recent_videos(limit=args.recent)

if __name__ == '__main__':
    main() 