#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pornhub视频抓取配置文件 - 优化版本
"""

# 代理设置
PROXY_CONFIG = {
    'http': 'socks5://127.0.0.1:12345',
    'https': 'socks5://127.0.0.1:12345'
}

# 请求头设置
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Cache-Control': 'max-age=0'
}

# SSL设置
SSL_CONFIG = {
    'verify': False,
    'allow_redirects': True,
}

# 网站设置
BASE_URL = "https://cn.pornhub.com/language/chinese"

# 核心抓取设置
SCRAPER_CONFIG = {
    'start_page': 1,
    'delay_min': 1.5,      # 减少延迟提高效率
    'delay_max': 3.0,      # 减少延迟提高效率
    'timeout': 30,         # 减少超时时间
    'max_retries': 3,
    'download_threads': 8, # 适中的线程数
    'skip_existing': True,
    'auto_detect_last': True,
}

# 输出设置
OUTPUT_CONFIG = {
    'data_folder': 'data',
    'html_filename': 'index.html',
    'thumbnail_filename': 'thumbnail.jpg',
    'preview_filename': 'preview.webm',
}

# Selenium设置（简化）
SELENIUM_CONFIG = {
    'use_selenium': False,  # 默认使用requests模式
    'headless': True,
    'disable_images': True,
    'window_size': '1920,1080',
    'page_load_timeout': 15,
    'implicit_wait': 3,
    'explicit_wait': 10,
    'enable_ad_monitor': True,
    'ad_monitor_interval': 3,
}

# 详情页面获取设置
DETAIL_PAGE_CONFIG = {
    'use_requests': True,
    'max_workers_requests': 5,
    'max_workers_selenium': 2,
}

# 调试设置
DEBUG = {
    'verbose': False,
    'save_raw_html': False,
    'test_mode': False,
} 