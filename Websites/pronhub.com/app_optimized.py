#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pornhub视频抓取工具 - 优化重构版本
修复多线程问题，改进资源管理，提高代码质量
"""

import requests
import os
import re
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import random
import threading
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
import logging
from typing import Dict, List, Optional, Tuple, Any
import atexit
import signal
import sys

# 导入配置
from config import (
    PROXY_CONFIG, HEADERS, BASE_URL, SCRAPER_CONFIG, 
    OUTPUT_CONFIG, DEBUG, SSL_CONFIG, SELENIUM_CONFIG, 
    DETAIL_PAGE_CONFIG
)

# Selenium相关导入
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("警告: Selenium不可用，将只使用requests模式")

# 禁用SSL警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 配置日志
logging.basicConfig(
    level=logging.INFO if DEBUG['verbose'] else logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ResourceManager:
    """资源管理器 - 负责统一管理线程池、连接等资源"""
    
    def __init__(self):
        self.thread_pools: List[ThreadPoolExecutor] = []
        self.cleanup_callbacks: List[callable] = []
        self._lock = threading.Lock()
        
        # 注册清理回调
        atexit.register(self.cleanup_all)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"接收到信号 {signum}，开始清理资源...")
        self.cleanup_all()
        sys.exit(0)
    
    def register_thread_pool(self, pool: ThreadPoolExecutor) -> ThreadPoolExecutor:
        """注册线程池以便统一管理"""
        with self._lock:
            self.thread_pools.append(pool)
        return pool
    
    def register_cleanup_callback(self, callback: callable):
        """注册清理回调函数"""
        with self._lock:
            self.cleanup_callbacks.append(callback)
    
    def cleanup_all(self):
        """清理所有资源"""
        with self._lock:
            # 执行清理回调
            for callback in self.cleanup_callbacks:
                try:
                    callback()
                except Exception as e:
                    logger.error(f"清理回调执行失败: {e}")
            
            # 关闭线程池
            for pool in self.thread_pools:
                try:
                    pool.shutdown(wait=False)
                except Exception as e:
                    logger.error(f"线程池关闭失败: {e}")
            
            self.thread_pools.clear()
            self.cleanup_callbacks.clear()


class SafeSession:
    """线程安全的Session管理器"""
    
    def __init__(self, proxies=None, headers=None, timeout=30):
        self._local = threading.local()
        self.proxies = proxies
        self.headers = headers
        self.timeout = timeout
    
    def _get_session(self) -> requests.Session:
        """获取线程本地的Session"""
        if not hasattr(self._local, 'session'):
            session = requests.Session()
            if self.proxies:
                session.proxies.update(self.proxies)
            if self.headers:
                session.headers.update(self.headers)
            session.verify = SSL_CONFIG.get('verify', False)
            self._local.session = session
        return self._local.session
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """线程安全的GET请求"""
        session = self._get_session()
        kwargs.setdefault('timeout', self.timeout)
        return session.get(url, **kwargs)
    
    def close_all(self):
        """关闭所有Session"""
        if hasattr(self._local, 'session'):
            try:
                self._local.session.close()
                delattr(self._local, 'session')
            except Exception as e:
                logger.error(f"关闭Session失败: {e}")


class PornhubScraperOptimized:
    """优化重构后的Pornhub采集器"""
    
    def __init__(self, use_selenium: Optional[bool] = None):
        self.base_url = BASE_URL
        self.resource_manager = ResourceManager()
        
        # 初始化Session管理器
        self.session_manager = SafeSession(
            proxies=PROXY_CONFIG,
            headers=HEADERS,
            timeout=SCRAPER_CONFIG.get('timeout', 60)
        )
        
        # 注册清理回调
        self.resource_manager.register_cleanup_callback(self._cleanup)
        
        # 下载队列和结果
        self.download_queue = Queue()
        self.download_results = {}
        self.download_lock = threading.Lock()
        self.download_workers = []
        
        # Selenium相关
        self.use_selenium = use_selenium if use_selenium is not None else SELENIUM_CONFIG.get('use_selenium', True)
        self.driver = None
        self.ad_monitor_thread = None
        self.stop_ad_monitor = threading.Event()
        
        # 初始化
        if self.use_selenium and SELENIUM_AVAILABLE:
            self._init_selenium_driver()
        elif self.use_selenium and not SELENIUM_AVAILABLE:
            logger.warning("Selenium不可用，切换到requests模式")
            self.use_selenium = False
    
    def _cleanup(self):
        """清理资源"""
        logger.info("开始清理PornhubScraper资源...")
        
        # 停止下载工作线程
        self._stop_download_workers()
        
        # 停止广告监控
        if self.ad_monitor_thread and self.ad_monitor_thread.is_alive():
            self.stop_ad_monitor.set()
            self.ad_monitor_thread.join(timeout=2)
        
        # 关闭Selenium
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
            except Exception as e:
                logger.error(f"关闭Selenium失败: {e}")
        
        # 关闭Session
        self.session_manager.close_all()
        
        logger.info("PornhubScraper资源清理完成")
    
    def _init_selenium_driver(self):
        """初始化Selenium WebDriver"""
        try:
            logger.info("正在初始化Selenium WebDriver...")
            
            # 检测GitHub Actions环境
            is_github_actions = self._is_github_actions_environment()
            
            chrome_options = Options()
            
            # 基础配置
            basic_args = [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-blink-features=AutomationControlled',
                '--ignore-ssl-errors',
                '--ignore-certificate-errors',
                '--ignore-certificate-errors-spki-list',
                '--disable-web-security',
                '--allow-running-insecure-content',
                '--disable-features=VizDisplayCompositor'
            ]
            
            for arg in basic_args:
                chrome_options.add_argument(arg)
            
            # 无头模式
            if SELENIUM_CONFIG.get('headless', True):
                chrome_options.add_argument('--headless')
            
            # 窗口大小
            window_size = SELENIUM_CONFIG.get('window_size', '1920,1080')
            chrome_options.add_argument(f'--window-size={window_size}')
            
            # 性能优化
            if SELENIUM_CONFIG.get('disable_images', True):
                prefs = {"profile.managed_default_content_settings.images": 2}
                chrome_options.add_experimental_option("prefs", prefs)
            
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # 代理设置
            if not is_github_actions and PROXY_CONFIG:
                proxy_url = PROXY_CONFIG.get('http', '')
                if proxy_url:
                    chrome_options.add_argument(f'--proxy-server={proxy_url}')
            
            # 创建服务
            try:
                service = Service(ChromeDriverManager().install())
            except Exception:
                # 回退到系统PATH中的chromedriver
                service = Service()
            
            # 创建驱动
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # 设置超时
            self.driver.set_page_load_timeout(SELENIUM_CONFIG.get('page_load_timeout', 10))
            self.driver.implicitly_wait(SELENIUM_CONFIG.get('implicit_wait', 3))
            
            # 执行脚本隐藏自动化标识
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("Selenium WebDriver初始化成功")
            
            # 启动广告监控
            if SELENIUM_CONFIG.get('enable_ad_monitor', True):
                self._start_ad_monitor()
                
        except Exception as e:
            logger.error(f"Selenium初始化失败: {e}")
            self.use_selenium = False
            self.driver = None
    
    def _is_github_actions_environment(self) -> bool:
        """检测是否在GitHub Actions环境中"""
        github_env_vars = ['GITHUB_ACTIONS', 'GITHUB_WORKSPACE', 'GITHUB_REPOSITORY']
        return any(os.getenv(var) for var in github_env_vars)
    
    def _start_ad_monitor(self):
        """启动广告监控线程"""
        if self.ad_monitor_thread and self.ad_monitor_thread.is_alive():
            return
        
        self.stop_ad_monitor.clear()
        self.ad_monitor_thread = threading.Thread(target=self._ad_monitor_worker, daemon=True)
        self.ad_monitor_thread.start()
        logger.info("广告监控线程已启动")
    
    def _ad_monitor_worker(self):
        """广告监控工作线程"""
        interval = SELENIUM_CONFIG.get('ad_monitor_interval', 5)
        
        while not self.stop_ad_monitor.wait(interval):
            if not self.driver:
                break
            
            try:
                self._close_ad_tabs()
            except Exception as e:
                logger.debug(f"广告监控异常: {e}")
    
    def _close_ad_tabs(self):
        """关闭广告标签页"""
        if not self.driver:
            return
        
        try:
            current_handles = self.driver.window_handles
            if len(current_handles) <= 1:
                return
            
            main_handle = current_handles[0]
            ad_handles = current_handles[1:]
            
            for handle in ad_handles:
                try:
                    self.driver.switch_to.window(handle)
                    self.driver.close()
                except Exception as e:
                    logger.debug(f"关闭广告标签页失败: {e}")
            
            # 切换回主标签页
            self.driver.switch_to.window(main_handle)
            
        except Exception as e:
            logger.debug(f"广告标签页检查失败: {e}")
    
    @contextmanager
    def download_worker_pool(self, num_workers: int = None):
        """下载工作线程池上下文管理器"""
        if num_workers is None:
            num_workers = SCRAPER_CONFIG.get('download_threads', 10)
        
        # 启动工作线程
        self._start_download_workers(num_workers)
        
        try:
            yield self
        finally:
            # 停止工作线程
            self._stop_download_workers()
    
    def _start_download_workers(self, num_workers: int):
        """启动下载工作线程"""
        if self.download_workers:
            return  # 已经启动
        
        for i in range(num_workers):
            worker = threading.Thread(
                target=self._download_worker, 
                args=(i + 1,), 
                daemon=True
            )
            worker.start()
            self.download_workers.append(worker)
        
        logger.info(f"启动 {num_workers} 个下载工作线程")
    
    def _stop_download_workers(self):
        """停止下载工作线程"""
        if not self.download_workers:
            return
        
        # 发送停止信号
        for _ in self.download_workers:
            self.download_queue.put(None)
        
        # 等待线程结束
        for worker in self.download_workers:
            worker.join(timeout=2)
        
        self.download_workers.clear()
        logger.info("下载工作线程已停止")
    
    def _download_worker(self, worker_id: int):
        """下载工作线程"""
        logger.debug(f"下载工作线程 {worker_id} 启动")
        
        while True:
            try:
                task = self.download_queue.get(timeout=1)
                if task is None:  # 停止信号
                    break
                
                url, filepath, task_type = task
                success = self._download_file(url, filepath)
                
                with self.download_lock:
                    self.download_results[filepath] = {
                        'success': success,
                        'type': task_type,
                        'url': url
                    }
                
                self.download_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"下载工作线程 {worker_id} 异常: {e}")
                try:
                    self.download_queue.task_done()
                except ValueError:
                    pass
        
        logger.debug(f"下载工作线程 {worker_id} 结束")
    
    def _download_file(self, url: str, filepath: str) -> bool:
        """下载单个文件"""
        try:
            # 检查文件是否已存在
            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                return True
            
            # 确保目录存在
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # 下载文件
            response = self.session_manager.get(url, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            return True
            
        except Exception as e:
            logger.error(f"下载文件失败 {url}: {e}")
            return False
    
    def add_download_task(self, url: str, filepath: str, task_type: str):
        """添加下载任务"""
        self.download_queue.put((url, filepath, task_type))
    
    def wait_for_downloads(self) -> Dict[str, Any]:
        """等待所有下载完成"""
        self.download_queue.join()
        return self.download_results.copy()
    
    def get_page_requests(self, url: str) -> Optional[str]:
        """使用requests获取页面内容"""
        max_retries = SCRAPER_CONFIG.get('max_retries', 3)
        
        for attempt in range(max_retries):
            try:
                delay = random.uniform(
                    SCRAPER_CONFIG.get('delay_min', 2),
                    SCRAPER_CONFIG.get('delay_max', 5)
                )
                time.sleep(delay)
                
                response = self.session_manager.get(url)
                response.raise_for_status()
                return response.text
                
            except Exception as e:
                logger.warning(f"获取页面失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
        
        return None
    
    def get_page_selenium(self, url: str) -> Optional[str]:
        """使用Selenium获取页面内容"""
        if not self.driver:
            return None
        
        try:
            self.driver.get(url)
            
            # 处理年龄验证
            self._handle_age_verification()
            
            return self.driver.page_source
            
        except TimeoutException:
            logger.warning(f"页面加载超时: {url}")
            try:
                self.driver.refresh()
                time.sleep(5)
                return self.driver.page_source
            except Exception:
                return None
        except Exception as e:
            logger.error(f"Selenium获取页面失败: {e}")
            return None
    
    def _handle_age_verification(self):
        """处理年龄验证"""
        try:
            # 查找年龄验证按钮
            age_button_selectors = [
                "a[href*='age_verified=1']",
                ".age-verification a",
                "#age-verification-btn",
                ".ageVerificationWrapper a"
            ]
            
            for selector in age_button_selectors:
                try:
                    button = WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    self.driver.execute_script("arguments[0].click();", button)
                    logger.info("年龄验证完成")
                    time.sleep(2)
                    return
                except TimeoutException:
                    continue
                    
        except Exception as e:
            logger.debug(f"年龄验证处理: {e}")
    
    def parse_video_list(self, html_content: str) -> List[Dict[str, Any]]:
        """解析视频列表页面"""
        videos = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            video_elements = soup.find_all('li', {'data-entrycode': True})
            
            for li_element in video_elements:
                try:
                    video_info = self._extract_video_info(li_element)
                    if video_info:
                        videos.append(video_info)
                except Exception as e:
                    logger.debug(f"解析视频信息失败: {e}")
            
        except Exception as e:
            logger.error(f"解析视频列表失败: {e}")
        
        return videos
    
    def _extract_video_info(self, li_element) -> Optional[Dict[str, Any]]:
        """从li元素中提取视频信息"""
        try:
            # 获取viewkey
            viewkey = li_element.get('data-entrycode', '').strip()
            if not viewkey:
                return None
            
            # 获取标题链接
            title_link = li_element.find('a', class_='linkVideoThumb')
            if not title_link:
                return None
            
            title = title_link.get('title', '').strip()
            video_url = urljoin(self.base_url, title_link.get('href', ''))
            
            # 获取缩略图
            img_element = li_element.find('img', class_='thumb')
            thumbnail_url = img_element.get('data-src') or img_element.get('src') if img_element else ''
            
            # 获取时长
            duration_element = li_element.find('var', class_='duration')
            duration = duration_element.get_text().strip() if duration_element else ''
            
            # 获取预览视频
            preview_element = li_element.find('video')
            preview_url = preview_element.get('data-src') if preview_element else ''
            
            return {
                'viewkey': viewkey,
                'title': title,
                'url': video_url,
                'thumbnail_url': thumbnail_url,
                'duration': duration,
                'preview_url': preview_url
            }
            
        except Exception as e:
            logger.debug(f"提取视频信息失败: {e}")
            return None
    
    def get_video_detailed_info(self, viewkey: str) -> Optional[Dict[str, Any]]:
        """获取视频详细信息"""
        video_url = f"https://cn.pornhub.com/view_video.php?viewkey={viewkey}"
        
        # 使用requests获取详情页面
        html_content = self.get_page_requests(video_url)
        if not html_content:
            return None
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取基本信息
            title_element = soup.find('h1', class_='title')
            title = title_element.get_text().strip() if title_element else f"Video_{viewkey}"
            
            # 提取m3u8链接
            m3u8_urls = self._extract_m3u8_urls(html_content)
            
            # 其他信息...
            info = {
                'viewkey': viewkey,
                'title': title,
                'url': video_url,
                'm3u8_urls': m3u8_urls,
                # 可以继续添加其他字段
            }
            
            return info
            
        except Exception as e:
            logger.error(f"解析视频详情失败: {e}")
            return None
    
    def _extract_m3u8_urls(self, html_content: str) -> List[str]:
        """提取m3u8链接"""
        m3u8_urls = []
        
        try:
            # 查找JavaScript中的m3u8链接
            m3u8_pattern = r'https?://[^"\'\s]*\.m3u8[^"\'\s]*'
            matches = re.findall(m3u8_pattern, html_content)
            
            for match in matches:
                # 清理URL
                cleaned_url = match.rstrip('",;})')
                if cleaned_url not in m3u8_urls:
                    m3u8_urls.append(cleaned_url)
            
        except Exception as e:
            logger.debug(f"提取m3u8链接失败: {e}")
        
        return m3u8_urls
    
    def create_html_page(self, video_data: Dict[str, Any], folder_path: str) -> str:
        """创建HTML页面"""
        try:
            # 生成HTML内容
            html_content = self._generate_html_content(video_data)
            
            # 保存HTML文件
            html_filename = OUTPUT_CONFIG.get('html_filename', 'index.html')
            html_filepath = os.path.join(folder_path, html_filename)
            
            os.makedirs(folder_path, exist_ok=True)
            
            with open(html_filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            return html_filepath
            
        except Exception as e:
            logger.error(f"创建HTML页面失败: {e}")
            return ""
    
    def _generate_html_content(self, video_data: Dict[str, Any]) -> str:
        """生成HTML内容"""
        title = video_data.get('title', 'Unknown Video')
        viewkey = video_data.get('viewkey', '')
        m3u8_urls = video_data.get('m3u8_urls', [])
        
        # 选择最佳质量的m3u8
        best_m3u8_url = m3u8_urls[0] if m3u8_urls else 'N/A'
        
        # 生成质量链接
        quality_links_html = self._generate_quality_links(m3u8_urls)
        
        html_template = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .video-info {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .video-title {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
            margin-bottom: 15px;
        }}
        .m3u8-links-section {{
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            border: 2px solid #007bff;
        }}
        .best-quality-btn {{
            display: inline-block;
            padding: 15px 30px;
            background: #28a745;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-size: 18px;
            font-weight: bold;
            transition: background 0.3s;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        }}
        .best-quality-btn:hover {{
            background: #218838;
            text-decoration: none;
            color: white;
        }}
        .quality-links {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 15px;
        }}
        .quality-link {{
            display: inline-block;
            padding: 8px 15px;
            background: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-size: 14px;
            transition: background 0.3s;
        }}
        .quality-link:hover {{
            background: #0056b3;
            text-decoration: none;
            color: white;
        }}
        .no-link {{
            text-align: center;
            color: #6c757d;
            font-style: italic;
            padding: 20px;
        }}
    </style>
</head>
<body>
    <div class="video-info">
        <h1 class="video-title">{title}</h1>
        <p><strong>Viewkey:</strong> {viewkey}</p>
        
        <div class="m3u8-links-section">
            <h3>🎬 M3U8 视频链接</h3>
            <div style="text-align: center; margin-bottom: 15px;">
                {f'<a href="{best_m3u8_url}" target="_blank" class="best-quality-btn">🎯 打开最佳质量视频</a>' if best_m3u8_url != 'N/A' else '<p class="no-link">暂无可用的m3u8视频链接</p>'}
            </div>
            <div>
                <h4>所有可用质量:</h4>
                <div class="quality-links">
                    {quality_links_html}
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""
        
        return html_template
    
    def _generate_quality_links(self, m3u8_urls: List[str]) -> str:
        """生成质量链接HTML"""
        if not m3u8_urls:
            return '<p class="no-link">暂无其他质量可用</p>'
        
        quality_priority = ['1080P', '720P', '480P', '240P', 'HD', 'SD']
        links_html = ""
        
        for i, url in enumerate(m3u8_urls):
            # 尝试从URL中提取质量信息
            quality_name = f"质量 {i+1}"
            for priority in quality_priority:
                if priority in url:
                    quality_name = priority
                    break
            
            links_html += f'<a href="{url}" target="_blank" class="quality-link">{quality_name}</a>'
        
        return links_html
    
    def run_optimized(self, start_page: int = 1, max_pages: int = None) -> Dict[str, Any]:
        """优化的运行流程"""
        logger.info("开始优化采集流程...")
        
        try:
            with self.download_worker_pool():
                # 采集页面并处理视频
                results = self._process_pages(start_page, max_pages)
                
                # 等待下载完成
                download_results = self.wait_for_downloads()
                results['download_results'] = download_results
                
                return results
                
        except Exception as e:
            logger.error(f"采集流程失败: {e}")
            return {}
    
    def _process_pages(self, start_page: int, max_pages: int) -> Dict[str, Any]:
        """处理页面采集"""
        videos_processed = 0
        total_pages = 0
        
        page = start_page
        while True:
            if max_pages and page > start_page + max_pages - 1:
                break
            
            logger.info(f"处理第 {page} 页...")
            
            # 获取页面内容
            page_url = f"{self.base_url}?page={page}"
            html_content = self.get_page_requests(page_url) or self.get_page_selenium(page_url)
            
            if not html_content:
                logger.warning(f"第 {page} 页获取失败，跳过")
                page += 1
                continue
            
            # 解析视频列表
            videos = self.parse_video_list(html_content)
            if not videos:
                logger.info(f"第 {page} 页无视频，停止采集")
                break
            
            # 处理视频
            for video in videos:
                self._process_single_video(video)
                videos_processed += 1
            
            total_pages += 1
            page += 1
            
            logger.info(f"第 {page-1} 页处理完成，共 {len(videos)} 个视频")
        
        return {
            'total_pages': total_pages,
            'videos_processed': videos_processed
        }
    
    def _process_single_video(self, video_info: Dict[str, Any]):
        """处理单个视频"""
        viewkey = video_info.get('viewkey')
        if not viewkey:
            return
        
        # 检查是否已存在
        folder_path = os.path.join(OUTPUT_CONFIG.get('data_folder', 'data'), viewkey)
        if SCRAPER_CONFIG.get('skip_existing', True) and os.path.exists(folder_path):
            logger.debug(f"跳过已存在的视频: {viewkey}")
            return
        
        # 获取详细信息
        detailed_info = self.get_video_detailed_info(viewkey)
        if not detailed_info:
            logger.warning(f"获取视频详情失败: {viewkey}")
            return
        
        # 合并信息
        video_data = {**video_info, **detailed_info}
        
        # 创建文件夹
        os.makedirs(folder_path, exist_ok=True)
        
        # 创建HTML页面
        self.create_html_page(video_data, folder_path)
        
        # 添加下载任务
        if video_info.get('thumbnail_url'):
            thumbnail_path = os.path.join(folder_path, OUTPUT_CONFIG.get('thumbnail_filename', 'thumbnail.jpg'))
            self.add_download_task(video_info['thumbnail_url'], thumbnail_path, 'thumbnail')
        
        if video_info.get('preview_url'):
            preview_path = os.path.join(folder_path, OUTPUT_CONFIG.get('preview_filename', 'preview.webm'))
            self.add_download_task(video_info['preview_url'], preview_path, 'preview')


def main():
    """主函数"""
    scraper = PornhubScraperOptimized()
    
    try:
        results = scraper.run_optimized(
            start_page=SCRAPER_CONFIG.get('start_page', 1),
            max_pages=5  # 测试用，限制页数
        )
        
        logger.info("采集完成!")
        logger.info(f"处理页数: {results.get('total_pages', 0)}")
        logger.info(f"处理视频: {results.get('videos_processed', 0)}")
        
    except KeyboardInterrupt:
        logger.info("用户中断采集")
    except Exception as e:
        logger.error(f"采集过程中出现错误: {e}")


if __name__ == "__main__":
    main() 