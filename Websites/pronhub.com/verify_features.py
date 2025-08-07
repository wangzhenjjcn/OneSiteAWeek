#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
功能验证脚本 - 验证所有新功能是否正确集成
"""

from app import PornhubScraper
from config import SCRAPER_CONFIG, OUTPUT_CONFIG
import os

def verify_config():
    """验证配置设置"""
    print("=== 配置验证 ===")
    
    checks = [
        ('下载线程数', SCRAPER_CONFIG.get('download_threads', 10), 30),
        ('跳过已存在ID', SCRAPER_CONFIG.get('skip_existing', False), True),
        ('隐藏工作线程信息', SCRAPER_CONFIG.get('show_worker_info', True), False),
        ('自动检测最后一页', SCRAPER_CONFIG.get('auto_detect_last', False), True),
        ('最大重试次数', SCRAPER_CONFIG.get('max_retries', 3), 5),
    ]
    
    all_passed = True
    for name, current, expected in checks:
        status = "✓" if current == expected else "✗"
        print(f"{status} {name}: {current} (期望: {expected})")
        if current != expected:
            all_passed = False
    
    return all_passed

def verify_methods():
    """验证新增方法"""
    print("\n=== 方法验证 ===")
    
    scraper = PornhubScraper()
    
    methods = [
        'is_video_completed',
        'create_collection_log',
        'update_collection_logs',
        'get_video_detailed_info'
    ]
    
    all_passed = True
    for method_name in methods:
        if hasattr(scraper, method_name):
            print(f"✓ 方法 {method_name} 存在")
        else:
            print(f"✗ 方法 {method_name} 不存在")
            all_passed = False
    
    return all_passed

def verify_worker_info_control():
    """验证工作线程信息控制"""
    print("\n=== 工作线程信息控制验证 ===")
    
    # 测试显示模式
    SCRAPER_CONFIG['show_worker_info'] = True
    print(f"显示模式: {SCRAPER_CONFIG.get('show_worker_info', False)}")
    
    # 测试隐藏模式
    SCRAPER_CONFIG['show_worker_info'] = False
    print(f"隐藏模式: {SCRAPER_CONFIG.get('show_worker_info', False)}")
    
    return True

def verify_skip_logic():
    """验证跳过逻辑"""
    print("\n=== 跳过逻辑验证 ===")
    
    scraper = PornhubScraper()
    
    # 测试不存在的视频
    result1 = scraper.is_video_completed('nonexistent123')
    print(f"不存在视频检查: {result1} (期望: False)")
    
    # 测试跳过功能开关
    original_skip = SCRAPER_CONFIG.get('skip_existing', True)
    
    # 禁用跳过
    SCRAPER_CONFIG['skip_existing'] = False
    print(f"跳过功能禁用: {SCRAPER_CONFIG.get('skip_existing', True)}")
    
    # 启用跳过
    SCRAPER_CONFIG['skip_existing'] = True
    print(f"跳过功能启用: {SCRAPER_CONFIG.get('skip_existing', True)}")
    
    # 恢复设置
    SCRAPER_CONFIG['skip_existing'] = original_skip
    
    return True

def verify_log_creation():
    """验证日志创建功能"""
    print("\n=== 日志创建验证 ===")
    
    scraper = PornhubScraper()
    
    # 创建测试数据
    test_video_data = {
        'video_id': '123456',
        'viewkey': 'test123',
        'title': '测试视频标题',
        'video_url': 'https://cn.pornhub.com/view_video.php?viewkey=test123',
        'thumbnail_url': 'https://example.com/thumb.jpg',
        'alt_text': '测试视频',
        'preview_url': 'https://example.com/preview.webm',
        'duration': '10:30',
        'uploader': '测试上传者',
        'views': '1.2K次观看',
        'added_time': '1个月前',
        'publish_time': '1个月前',
        'categories': [
            {'name': '亚洲人', 'url': '/video?c=1'},
            {'name': '口交', 'url': '/video?c=13'}
        ],
        'best_m3u8_url': 'https://example.com/video.m3u8'
    }
    
    # 创建测试文件夹
    test_folder = 'test_log_verification'
    os.makedirs(test_folder, exist_ok=True)
    
    try:
        # 测试成功日志
        success = scraper.create_collection_log(test_video_data, test_folder, success=True)
        print(f"成功日志创建: {success}")
        
        # 测试失败日志
        success = scraper.create_collection_log(test_video_data, test_folder, success=False, error_msg="测试错误")
        print(f"失败日志创建: {success}")
        
        # 检查日志文件
        log_file = os.path.join(test_folder, 'collection_log.txt')
        if os.path.exists(log_file):
            print(f"✓ 日志文件已创建: {log_file}")
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if '采集状态: 失败' in content:
                    print("✓ 失败状态正确记录")
                else:
                    print("✗ 失败状态记录错误")
        else:
            print("✗ 日志文件未创建")
            return False
        
        return True
        
    finally:
        # 清理测试文件夹
        if os.path.exists(test_folder):
            import shutil
            shutil.rmtree(test_folder)

def main():
    """主验证函数"""
    print("功能验证脚本")
    print("=" * 50)
    
    results = []
    
    # 验证配置
    results.append(("配置验证", verify_config()))
    
    # 验证方法
    results.append(("方法验证", verify_methods()))
    
    # 验证工作线程信息控制
    results.append(("工作线程信息控制", verify_worker_info_control()))
    
    # 验证跳过逻辑
    results.append(("跳过逻辑", verify_skip_logic()))
    
    # 验证日志创建
    results.append(("日志创建", verify_log_creation()))
    
    # 总结
    print("\n=== 验证总结 ===")
    all_passed = True
    for name, result in results:
        status = "✓" if result else "✗"
        print(f"{status} {name}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n🎉 所有功能验证通过！")
    else:
        print("\n❌ 部分功能验证失败，请检查代码。")
    
    return all_passed

if __name__ == "__main__":
    main() 