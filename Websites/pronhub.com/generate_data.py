#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据重新生成工具
从数据库和HTML数据库重新生成data目录下的所有采集文件

使用方法:
    python generate_data.py                    # 重新生成所有数据
    python generate_data.py --limit 10         # 限制处理10个视频
    python generate_data.py --update           # 强制更新已存在的文件
    python generate_data.py --viewkey 123456   # 只处理指定的视频ID
    python generate_data.py --stats            # 显示数据库统计信息
"""

import os
import sys
import argparse
from app import PornhubScraper, DatabaseManager, show_database_stats

def main():
    parser = argparse.ArgumentParser(description='从数据库重新生成data目录下的采集文件')
    
    # 添加命令行参数
    parser.add_argument('--limit', type=int, help='限制处理的视频数量')
    parser.add_argument('--update', action='store_true', help='强制更新已存在的文件')
    parser.add_argument('--viewkey', type=str, help='只处理指定的视频ID')
    parser.add_argument('--stats', action='store_true', help='显示数据库统计信息')
    parser.add_argument('--verbose', action='store_true', help='显示详细信息')
    parser.add_argument('--source', choices=['html', 'video'], default='html', 
                       help='数据源: html=从HTML数据库, video=从视频数据库 (默认: html)')
    
    args = parser.parse_args()
    
    # 显示统计信息
    if args.stats:
        print("📊 数据库统计信息:")
        show_database_stats()
        return
    
    print("🔄 数据重新生成工具")
    print("=" * 50)
    
    # 初始化采集器
    scraper = None
    try:
        scraper = PornhubScraper()
        
        if args.source == 'html':
            # 从HTML数据库重新生成
            print("📂 从HTML数据库重新生成data目录...")
            result = generate_from_html_database(scraper, args)
        else:
            # 从视频数据库重新生成
            print("📂 从视频数据库重新生成data目录...")
            result = generate_from_video_database(scraper, args)
        
        # 显示结果
        print("\n✅ 重新生成完成!")
        print(f"📊 处理统计:")
        print(f"  - 成功处理: {result['success']}")
        print(f"  - 处理失败: {result['failed']}")
        print(f"  - 跳过: {result['skipped']}")
        print(f"  - 总计: {result['total']}")
        
        if result['failed'] > 0:
            print("\n⚠️  存在处理失败的视频，请检查日志信息")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断程序")
    except Exception as e:
        print(f"\n❌ 程序运行错误: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
    finally:
        if scraper:
            scraper.close_driver()

def generate_from_html_database(scraper, args):
    """从HTML数据库重新生成"""
    print(f"📊 配置信息:")
    print(f"  - 数据源: HTML数据库")
    print(f"  - 处理限制: {args.limit or '无限制'}")
    print(f"  - 强制更新: {'是' if args.update else '否'}")
    print(f"  - 指定视频: {args.viewkey or '全部'}")
    print(f"  - 详细输出: {'是' if args.verbose else '否'}")
    
    if args.viewkey:
        # 处理指定视频
        return generate_single_video_from_html(scraper, args.viewkey, args.update, args.verbose)
    else:
        # 批量处理
        return scraper.regenerate_data_from_html_db(
            limit=args.limit, 
            update_existing=args.update
        )

def generate_from_video_database(scraper, args):
    """从视频数据库重新生成"""
    print(f"📊 配置信息:")
    print(f"  - 数据源: 视频数据库")
    print(f"  - 处理限制: {args.limit or '无限制'}")
    print(f"  - 强制更新: {'是' if args.update else '否'}")
    print(f"  - 指定视频: {args.viewkey or '全部'}")
    
    db = DatabaseManager()
    
    # 获取视频列表
    if args.viewkey:
        videos = [db.get_video_by_id(args.viewkey)]
        videos = [v for v in videos if v]  # 过滤None
    else:
        # 获取所有视频
        with db.get_connection() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT v.*, GROUP_CONCAT(c.name) as category_names,
                       GROUP_CONCAT(m.url) as m3u8_urls
                FROM videos v
                LEFT JOIN video_categories vc ON v.id = vc.video_id
                LEFT JOIN categories c ON vc.category_id = c.id
                LEFT JOIN m3u8_urls m ON v.id = m.video_id
                GROUP BY v.id
                ORDER BY v.created_at DESC
            '''
            if args.limit:
                query += f' LIMIT {args.limit}'
            
            cursor.execute(query)
            videos = cursor.fetchall()
    
    if not videos:
        print("❌ 没有找到视频数据")
        return {'success': 0, 'failed': 0, 'skipped': 0, 'total': 0}
    
    print(f"📊 找到 {len(videos)} 个视频")
    
    # 开始下载工作线程
    scraper.start_download_workers()
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    try:
        for i, video in enumerate(videos, 1):
            try:
                if args.verbose:
                    print(f"\n🔄 处理视频 {i}/{len(videos)}: {video.get('title', 'N/A')[:50]}...")
                
                # 转换数据库格式到视频数据格式
                video_data = convert_db_video_to_data(video)
                
                # 检查是否跳过
                if not args.update and scraper.is_video_completed(video_data['viewkey']):
                    if args.verbose:
                        print(f"⏭️  跳过已存在: {video_data['viewkey']}")
                    skipped_count += 1
                    continue
                
                # 重新生成文件
                data_folder = os.path.join('data', video_data['viewkey'])
                os.makedirs(data_folder, exist_ok=True)
                
                # 创建HTML页面
                scraper.create_html_page(video_data, data_folder)
                
                # 添加下载任务（如果有URL）
                if video_data.get('thumbnail_url'):
                    thumbnail_path = os.path.join(data_folder, 'thumbnail.jpg')
                    scraper.add_download_task(video_data['thumbnail_url'], thumbnail_path, 'thumbnail')
                
                if video_data.get('preview_url'):
                    preview_path = os.path.join(data_folder, 'preview.webm')
                    scraper.add_download_task(video_data['preview_url'], preview_path, 'preview')
                
                # 创建采集日志
                scraper.create_collection_log(video_data, data_folder, success=True)
                
                success_count += 1
                
                if args.verbose:
                    print(f"✅ 成功处理: {video_data['viewkey']}")
                
            except Exception as e:
                failed_count += 1
                if args.verbose:
                    print(f"❌ 处理失败: {e}")
                
        # 等待下载完成
        print("\n⏳ 等待文件下载完成...")
        scraper.wait_for_downloads()
        
    finally:
        scraper.stop_download_workers()
    
    return {
        'success': success_count,
        'failed': failed_count, 
        'skipped': skipped_count,
        'total': len(videos)
    }

def generate_single_video_from_html(scraper, viewkey, update_existing, verbose):
    """从HTML数据库处理单个视频"""
    # 构建视频URL
    video_url = f"https://cn.pornhub.com/view_video.php?viewkey={viewkey}"
    
    # 从HTML数据库获取
    html_content = scraper.db.get_html_page(video_url)
    if not html_content:
        print(f"❌ 在HTML数据库中未找到视频: {viewkey}")
        return {'success': 0, 'failed': 1, 'skipped': 0, 'total': 1}
    
    print(f"🔄 处理单个视频: {viewkey}")
    
    try:
        # 使用HTML重新生成逻辑
        from bs4 import BeautifulSoup
        
        # 确保HTML内容是字符串格式
        if isinstance(html_content, (tuple, list)):
            html_content = html_content[0] if html_content else ""
        elif not isinstance(html_content, str):
            html_content = str(html_content)
            
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 提取视频信息
        video_data = scraper.extract_video_metadata(soup, video_url)
        video_data['viewkey'] = viewkey
        video_data['video_id'] = viewkey
        video_data['video_url'] = video_url
        
        # 检查跳过逻辑
        if not update_existing:
            file_exists = scraper.is_video_completed(viewkey)
            db_exists = scraper.db.video_exists(viewkey)
            
            if file_exists and db_exists:
                print(f"⏭️  跳过已存在: {viewkey}")
                return {'success': 0, 'failed': 0, 'skipped': 1, 'total': 1}
        
        # 处理视频
        scraper.process_video(video_data)
        
        print(f"✅ 成功处理: {viewkey}")
        return {'success': 1, 'failed': 0, 'skipped': 0, 'total': 1}
        
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return {'success': 0, 'failed': 1, 'skipped': 0, 'total': 1}

def convert_db_video_to_data(video_row):
    """将数据库记录转换为视频数据格式"""
    # 处理分类
    categories = []
    if hasattr(video_row, 'category_names') and video_row.category_names:
        for cat_name in video_row.category_names.split(','):
            if cat_name.strip():
                categories.append({'name': cat_name.strip()})
    
    # 处理M3U8链接
    m3u8_urls = []
    best_m3u8_url = ''
    if hasattr(video_row, 'm3u8_urls') and video_row.m3u8_urls:
        m3u8_urls = [url.strip() for url in video_row.m3u8_urls.split(',') if url.strip()]
        if m3u8_urls:
            best_m3u8_url = m3u8_urls[0]  # 第一个作为最佳质量
    
    return {
        'viewkey': video_row.video_id,
        'video_id': video_row.video_id,
        'title': video_row.title or 'N/A',
        'video_url': video_row.original_url or f"https://cn.pornhub.com/view_video.php?viewkey={video_row.video_id}",
        'uploader': video_row.uploader or 'N/A',
        'views': video_row.views or 'N/A',
        'duration': video_row.duration or 'N/A',
        'publish_time': video_row.publish_time or 'N/A',
        'alt_text': f"{video_row.title or '视频'} 缩略图",
        'categories': categories,
        'thumbnail_url': video_row.thumbnail_url or '',
        'preview_url': video_row.preview_url or '',
        'best_m3u8_url': best_m3u8_url,
        'm3u8_urls': m3u8_urls
    }

if __name__ == "__main__":
    main() 