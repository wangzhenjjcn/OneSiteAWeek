#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app import YatuTVCrawler
from database_manager import YatuTVDatabase
import time
import logging

# 配置日志
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(script_dir, 'external_crawler.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_external_source_crawler():
    """运行站外片源批量抓取"""
    
    print("=== 雅图TV站外片源数据库爬虫 ===")
    print("专注于抓取站外非本站片源，边采集边保存到数据库")
    print("支持中断续传，跳过已成功的内容")
    print()
    
    # 初始化
    crawler = YatuTVCrawler()
    db = YatuTVDatabase()
    
    # 显示初始数据库状态
    print("📊 当前数据库状态:")
    stats = db.get_series_stats()
    if stats:
        print(f"   剧集数: {stats['series_count']}")
        print(f"   集数: {stats['episodes_count']}")
        print(f"   成功集数: {stats['successful_episodes']}")
        print(f"   片源数: {stats['sources_count']}")
        print(f"   成功片源: {stats['successful_sources']}")
        print(f"   集数成功率: {stats['episode_success_rate']:.1f}%")
        print(f"   片源成功率: {stats['source_success_rate']:.1f}%")
    print()
    
    # 首先抓取首页获取剧集列表
    print("🔍 正在抓取首页获取剧集列表...")
    try:
        categories = crawler.crawl_homepage()
        
        all_series = []
        for category_name, items in categories.items():
            for item in items:
                all_series.append((item['series_id'], item['url'], item.get('category', category_name)))
        
        print(f"✅ 找到 {len(all_series)} 个剧集")
        
        # 过滤掉已在数据库中的剧集（可选）
        new_series = []
        existing_count = 0
        for series_id, url, category in all_series:
            if db.is_series_crawled(series_id):
                existing_count += 1
            else:
                new_series.append((series_id, url, category))
        
        print(f"   其中 {existing_count} 个已在数据库中")
        print(f"   将处理 {len(new_series)} 个新剧集")
        
    except Exception as e:
        logger.error(f"抓取首页失败: {e}")
        print("❌ 抓取首页失败，使用测试剧集")
        # 使用一些测试剧集
        new_series = [
            ("m038214", "https://www.yatu.tv/m038214/", "动漫"),
            ("m038215", "https://www.yatu.tv/m038215/", "动漫"),
            ("m038216", "https://www.yatu.tv/m038216/", "动漫"),
        ]
    
    if not new_series:
        print("🎉 所有剧集都已在数据库中！")
        return
    
    print()
    print(f"🚀 开始批量抓取 {len(new_series)} 个剧集的站外片源...")
    
    success_count = 0
    failed_count = 0
    
    for i, (series_id, series_url, category) in enumerate(new_series, 1):
        print(f"\n📺 [{i}/{len(new_series)}] 处理剧集: {series_id} ({category})")
        
        try:
            # 抓取剧集详情和站外片源
            series_info = crawler.crawl_series_detail(series_url, series_id, category)
            
            if series_info:
                episodes = series_info.get('episodes', [])
                success_episodes = sum(1 for ep in episodes if ep.get('playframe_url'))
                
                print(f"   ✅ 完成: {len(episodes)} 集，成功获取 {success_episodes} 个播放地址")
                success_count += 1
            else:
                print(f"   ❌ 抓取失败")
                failed_count += 1
                
        except Exception as e:
            logger.error(f"处理剧集 {series_id} 失败: {e}")
            print(f"   ❌ 处理出错: {e}")
            failed_count += 1
        
        # 每处理5个剧集显示一次进度
        if i % 5 == 0 or i == len(new_series):
            current_stats = db.get_series_stats()
            if current_stats:
                print(f"\n📊 当前进度:")
                print(f"   已处理: {i}/{len(new_series)} 剧集")
                print(f"   成功: {success_count}, 失败: {failed_count}")
                print(f"   数据库总计: {current_stats['series_count']} 剧集, {current_stats['episodes_count']} 集")
                print(f"   播放地址获取率: {current_stats['episode_success_rate']:.1f}%")
        
        # 延时避免请求过快
        time.sleep(2)
    
    # 最终统计
    print(f"\n🎯 批量抓取完成！")
    print(f"   总处理: {len(new_series)} 剧集")
    print(f"   成功: {success_count} 剧集")
    print(f"   失败: {failed_count} 剧集")
    
    final_stats = db.get_series_stats()
    if final_stats:
        print(f"\n📊 最终数据库统计:")
        print(f"   剧集数: {final_stats['series_count']}")
        print(f"   集数: {final_stats['episodes_count']}")
        print(f"   成功集数: {final_stats['successful_episodes']}")
        print(f"   片源数: {final_stats['sources_count']}")
        print(f"   成功片源: {final_stats['successful_sources']}")
        print(f"   集数成功率: {final_stats['episode_success_rate']:.1f}%")
        print(f"   片源成功率: {final_stats['source_success_rate']:.1f}%")
    
    print(f"\n💾 数据库文件: database/yatu.tv")
    print(f"📄 日志文件: external_crawler.log")

if __name__ == "__main__":
    try:
        run_external_source_crawler()
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断抓取")
        print("💾 已抓取的数据已保存到数据库中")
        print("🔄 下次运行将自动跳过已成功的内容")
    except Exception as e:
        logger.error(f"程序异常: {e}")
        print(f"\n❌ 程序异常: {e}")
        print("�� 已抓取的数据已保存到数据库中") 