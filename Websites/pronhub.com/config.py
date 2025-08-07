#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pornhub视频抓取配置文件
"""

# 代理设置
PROXY_CONFIG = {
    'http': 'socks5://127.0.0.1:12345',
    'https': 'socks5://127.0.0.1:12345'
}

# 请求头设置
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

# SSL设置 - 完全忽略所有SSL验证
SSL_CONFIG = {
    'verify': False,  # 不验证SSL证书
    'check_hostname': False,  # 不检查主机名
    'allow_redirects': True,  # 允许重定向
}

# 网站设置
BASE_URL = "https://cn.pornhub.com/language/chinese"

# 抓取设置
SCRAPER_CONFIG = {
    'start_page': 1,      # 开始页数
    'end_page': 5,        # 结束页数（当auto_detect_last=True时会被忽略）
    'delay_min': 1,       # 最小延迟秒数
    'delay_max': 3,       # 最大延迟秒数
    'timeout': 30,        # 请求超时时间
    'max_retries': 5,     # 最大重试次数（增加到5次）
    'verify_ssl': False,  # 是否验证SSL证书
    'download_threads': 30,  # 下载线程数（增加到30个）
    'auto_detect_last': True,  # 是否自动检测最后一页
    'skip_existing': True,  # 是否跳过已存在的ID
    'show_worker_info': False,  # 是否显示工作线程信息
}

# 输出设置
OUTPUT_CONFIG = {
    'data_folder': 'data',           # 数据保存文件夹
    'html_filename': 'index.html',   # HTML文件名
    'thumbnail_filename': 'thumbnail.jpg',  # 缩略图文件名
    'preview_filename': 'preview.webm',     # 预览视频文件名
}

# 文件类型映射
FILE_EXTENSIONS = {
    'thumbnail': '.jpg',
    'preview': '.webm',
}

# Selenium设置
SELENIUM_CONFIG = {
    'use_selenium': True,  # 是否使用Selenium
    'headless': False,     # 是否无头模式（不显示浏览器窗口）
    'disable_images': True,  # 是否禁用图片加载
    'disable_javascript': True,  # 是否禁用JavaScript（改为True以提高性能）
    'window_size': '1920,1080',  # 窗口大小
    'page_load_timeout': 15,  # 页面加载超时时间（减少到15秒）
    'implicit_wait': 5,   # 隐式等待时间（减少到5秒）
    'explicit_wait': 5,   # 显式等待时间（减少到5秒）
}

# 调试设置
DEBUG = {
    'verbose': False,     # 详细输出（默认关闭）
    'save_raw_html': False,  # 保存原始HTML
    'test_mode': False,   # 测试模式
} 