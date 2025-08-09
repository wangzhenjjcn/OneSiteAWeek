import requests
import os
import re
import json
import sqlite3
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import random
import threading
from queue import Queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import PROXY_CONFIG, HEADERS, BASE_URL, SCRAPER_CONFIG, OUTPUT_CONFIG, DEBUG, SSL_CONFIG, SELENIUM_CONFIG, DETAIL_PAGE_CONFIG

# Selenium相关导入
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

# 禁用SSL警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 简化类型提示，避免导入问题
try:
    from typing import Dict, List, Optional, Any
except ImportError:
    # 如果typing不可用，定义简单的替代
    Dict = dict
    List = list
    Optional = lambda x: x
    Any = object

class DatabaseManager:
    """视频数据库管理器"""
    
    def __init__(self, db_path=None):
        """初始化数据库管理器
        
        Args:
            db_path: 数据库文件路径，如果为None则使用默认路径
        """
        if db_path is None:
            # 获取当前脚本目录
            script_dir = os.path.dirname(os.path.abspath(__file__))
            database_dir = os.path.join(script_dir, 'database')
            
            # 确保database目录存在
            os.makedirs(database_dir, exist_ok=True)
            
            # 设置数据库文件路径
            self.db_path = os.path.join(database_dir, 'pornhub_videos.db')
        else:
            self.db_path = db_path
            
        self.init_database()
    
    def init_database(self):
        """初始化数据库表结构"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 创建视频表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT UNIQUE NOT NULL,           -- 视频ID (如viewkey)
                    title TEXT NOT NULL,                     -- 视频标题
                    original_url TEXT NOT NULL,              -- 原始视频地址
                    uploader TEXT,                           -- 发布人/上传者
                    views TEXT,                             -- 观看次数
                    duration TEXT,                          -- 时长
                    publish_time TEXT,                      -- 发布时间
                    best_m3u8_url TEXT,                     -- 最佳质量m3u8链接
                    thumbnail_url TEXT,                     -- 缩略图URL
                    preview_url TEXT,                       -- 预览视频URL
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,  -- 采集时间
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP   -- 更新时间
                )
            ''')
            
            # 创建分类表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,              -- 分类名称
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建视频分类关联表（多对多关系）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS video_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id INTEGER NOT NULL,              -- 视频表ID
                    category_id INTEGER NOT NULL,           -- 分类表ID
                    FOREIGN KEY (video_id) REFERENCES videos (id) ON DELETE CASCADE,
                    FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE,
                    UNIQUE(video_id, category_id)
                )
            ''')
            
            # 创建M3U8质量链接表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS m3u8_urls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id INTEGER NOT NULL,              -- 视频表ID
                    quality TEXT NOT NULL,                  -- 质量标识（如1080P, 720P等）
                    url TEXT NOT NULL,                      -- M3U8链接
                    FOREIGN KEY (video_id) REFERENCES videos (id) ON DELETE CASCADE
                )
            ''')
            
            # 创建索引以提高查询性能
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_videos_video_id ON videos(video_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_videos_title ON videos(title)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_videos_uploader ON videos(uploader)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_videos_created_at ON videos(created_at)')
            
            conn.commit()
            print(f"✓ 数据库初始化完成: {self.db_path}")
    
    def insert_video(self, video_data):
        """插入视频数据
        
        Args:
            video_data: 视频数据字典
            
        Returns:
            插入的视频记录ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 准备视频数据
            video_id = video_data.get('viewkey') or video_data.get('video_id', '')
            title = video_data.get('title', '')
            original_url = video_data.get('video_url', '')
            uploader = video_data.get('uploader', '')
            views = video_data.get('views', '')
            duration = video_data.get('duration', '')
            publish_time = video_data.get('publish_time', '')
            best_m3u8_url = video_data.get('best_m3u8_url', '')
            thumbnail_url = video_data.get('thumbnail_url', '')
            preview_url = video_data.get('preview_url', '')
            
            try:
                # 插入或更新视频记录
                cursor.execute('''
                    INSERT OR REPLACE INTO videos 
                    (video_id, title, original_url, uploader, views, duration, 
                     publish_time, best_m3u8_url, thumbnail_url, preview_url, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (video_id, title, original_url, uploader, views, duration,
                      publish_time, best_m3u8_url, thumbnail_url, preview_url))
                
                # 获取插入的视频记录ID
                db_video_id = cursor.lastrowid
                if not db_video_id:
                    # 如果是更新操作，获取现有记录ID
                    cursor.execute('SELECT id FROM videos WHERE video_id = ?', (video_id,))
                    result = cursor.fetchone()
                    db_video_id = result[0] if result else None
                
                if not db_video_id:
                    raise Exception(f"无法获取视频记录ID: {video_id}")
                
                # 处理分类数据
                categories = video_data.get('categories', [])
                if categories:
                    self._insert_video_categories(cursor, db_video_id, categories)
                
                # 处理M3U8链接数据
                m3u8_urls = video_data.get('m3u8_urls', [])
                if m3u8_urls:
                    self._insert_m3u8_urls(cursor, db_video_id, m3u8_urls)
                
                conn.commit()
                print(f"✓ 视频数据已保存到数据库: {title} (ID: {video_id})")
                return db_video_id
                
            except sqlite3.IntegrityError as e:
                print(f"❌ 数据库插入错误: {e}")
                raise
            except Exception as e:
                print(f"❌ 保存视频数据失败: {e}")
                raise
    
    def _insert_video_categories(self, cursor, video_db_id, categories):
        """插入视频分类关联数据"""
        # 先删除现有的分类关联
        cursor.execute('DELETE FROM video_categories WHERE video_id = ?', (video_db_id,))
        
        for category in categories:
            category_name = category.get('name', '').strip()
            if not category_name:
                continue
                
            # 插入分类（如果不存在）
            cursor.execute('INSERT OR IGNORE INTO categories (name) VALUES (?)', (category_name,))
            
            # 获取分类ID
            cursor.execute('SELECT id FROM categories WHERE name = ?', (category_name,))
            category_id = cursor.fetchone()[0]
            
            # 插入视频分类关联
            cursor.execute('''
                INSERT OR IGNORE INTO video_categories (video_id, category_id) 
                VALUES (?, ?)
            ''', (video_db_id, category_id))
    
    def _insert_m3u8_urls(self, cursor, video_db_id, m3u8_urls):
        """插入M3U8链接数据"""
        # 先删除现有的M3U8链接
        cursor.execute('DELETE FROM m3u8_urls WHERE video_id = ?', (video_db_id,))
        
        for url in m3u8_urls:
            if not url or url == 'N/A':
                continue
                
            # 尝试从URL中提取质量信息
            quality = 'Unknown'
            for q in ['1080P', '720P', '480P', '240P', 'HD', 'SD']:
                if q in url:
                    quality = q
                    break
            
            # 插入M3U8链接
            cursor.execute('''
                INSERT INTO m3u8_urls (video_id, quality, url) 
                VALUES (?, ?, ?)
            ''', (video_db_id, quality, url))
    
    def video_exists(self, video_id):
        """检查视频是否已存在于数据库中"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM videos WHERE video_id = ?', (video_id,))
            return cursor.fetchone()[0] > 0
    
    def get_video_by_id(self, video_id):
        """根据视频ID获取视频信息"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM videos WHERE video_id = ?
            ''', (video_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            video_data = dict(row)
            
            # 获取分类信息
            cursor.execute('''
                SELECT c.name FROM categories c
                JOIN video_categories vc ON c.id = vc.category_id
                WHERE vc.video_id = ?
            ''', (video_data['id'],))
            
            categories = [{'name': row[0]} for row in cursor.fetchall()]
            video_data['categories'] = categories
            
            # 获取M3U8链接
            cursor.execute('''
                SELECT quality, url FROM m3u8_urls 
                WHERE video_id = ?
                ORDER BY quality DESC
            ''', (video_data['id'],))
            
            m3u8_urls = [row[1] for row in cursor.fetchall()]
            video_data['m3u8_urls'] = m3u8_urls
            
            return video_data
    
    def search_videos(self, query=None, limit=100, offset=0):
        """搜索视频"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if query:
                cursor.execute('''
                    SELECT * FROM videos 
                    WHERE title LIKE ? OR uploader LIKE ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                ''', (f'%{query}%', f'%{query}%', limit, offset))
            else:
                cursor.execute('''
                    SELECT * FROM videos 
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                ''', (limit, offset))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_statistics(self):
        """获取数据库统计信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 总视频数
            cursor.execute('SELECT COUNT(*) FROM videos')
            total_videos = cursor.fetchone()[0]
            
            # 总分类数
            cursor.execute('SELECT COUNT(*) FROM categories')
            total_categories = cursor.fetchone()[0]
            
            # 最新采集时间
            cursor.execute('SELECT MAX(created_at) FROM videos')
            latest_collection = cursor.fetchone()[0]
            
            # 热门上传者（前10）
            cursor.execute('''
                SELECT uploader, COUNT(*) as video_count 
                FROM videos 
                WHERE uploader != ''
                GROUP BY uploader 
                ORDER BY video_count DESC 
                LIMIT 10
            ''')
            top_uploaders = [{'uploader': row[0], 'count': row[1]} for row in cursor.fetchall()]
            
            # 热门分类（前10）
            cursor.execute('''
                SELECT c.name, COUNT(*) as video_count
                FROM categories c
                JOIN video_categories vc ON c.id = vc.category_id
                GROUP BY c.name
                ORDER BY video_count DESC
                LIMIT 10
            ''')
            top_categories = [{'name': row[0], 'count': row[1]} for row in cursor.fetchall()]
            
            return {
                'total_videos': total_videos,
                'total_categories': total_categories,
                'latest_collection': latest_collection,
                'top_uploaders': top_uploaders,
                'top_categories': top_categories
            }
    
    def export_to_json(self, output_file, limit=None):
        """导出数据到JSON文件"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = 'SELECT * FROM videos ORDER BY created_at DESC'
            if limit:
                query += f' LIMIT {limit}'
            
            cursor.execute(query)
            videos = []
            
            for row in cursor.fetchall():
                video_data = dict(row)
                
                # 获取分类
                cursor.execute('''
                    SELECT c.name FROM categories c
                    JOIN video_categories vc ON c.id = vc.category_id
                    WHERE vc.video_id = ?
                ''', (video_data['id'],))
                
                categories = [row[0] for row in cursor.fetchall()]
                video_data['categories'] = categories
                
                # 获取M3U8链接
                cursor.execute('''
                    SELECT url FROM m3u8_urls 
                    WHERE video_id = ?
                    ORDER BY quality DESC
                ''', (video_data['id'],))
                
                m3u8_urls = [row[0] for row in cursor.fetchall()]
                video_data['m3u8_urls'] = m3u8_urls
                
                videos.append(video_data)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(videos, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"✓ 数据已导出到: {output_file} ({len(videos)} 条记录)")

class PornhubScraper:
    def __init__(self, use_selenium=None):
        self.base_url = BASE_URL
        self.proxies = PROXY_CONFIG
        self.headers = HEADERS
        self.download_queue = Queue()
        self.download_results = {}
        self.download_lock = threading.Lock()
        
        # 初始化数据库管理器
        self.db = DatabaseManager()
        
        # 确定是否使用Selenium
        if use_selenium is None:
            self.use_selenium = SELENIUM_CONFIG.get('use_selenium', True)
        else:
            self.use_selenium = use_selenium
        
        self.driver = None
        self.ad_monitor_thread = None
        self.stop_ad_monitor = False
        
        # 如果使用Selenium，初始化浏览器
        if self.use_selenium:
            self.init_selenium_driver()
            # 启动广告监控线程
            self.start_ad_monitor()
    
    def init_selenium_driver(self):
        """初始化Selenium WebDriver"""
        try:
            print("正在初始化Selenium WebDriver...")
            
            # 检测是否在GitHub Actions环境中
            is_github_actions = self.is_github_actions_environment()
            
            if is_github_actions:
                print("检测到GitHub Actions环境，禁用代理设置")
            
            # Chrome选项配置
            chrome_options = Options()
            
            # 基本设置
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # SSL和跨域优化
            chrome_options.add_argument('--ignore-ssl-errors')
            chrome_options.add_argument('--ignore-certificate-errors')
            chrome_options.add_argument('--ignore-certificate-errors-spki-list')
            chrome_options.add_argument('--ignore-ssl-errors-spki-list')
            chrome_options.add_argument('--allow-running-insecure-content')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--allow-cross-origin-auth-prompt')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            
            # 针对中国大陆网络环境的优化
            chrome_options.add_argument('--disable-images')
            chrome_options.add_argument('--disable-javascript')
            chrome_options.add_argument('--disable-logging')
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            chrome_options.add_argument('--disable-field-trial-config')
            chrome_options.add_argument('--disable-ipc-flooding-protection')
            
            # 中国大陆网络优化
            chrome_options.add_argument('--disable-default-apps')
            chrome_options.add_argument('--disable-sync')
            chrome_options.add_argument('--disable-translate')
            chrome_options.add_argument('--disable-background-networking')
            chrome_options.add_argument('--disable-component-update')
            chrome_options.add_argument('--disable-client-side-phishing-detection')
            chrome_options.add_argument('--disable-hang-monitor')
            chrome_options.add_argument('--disable-prompt-on-repost')
            chrome_options.add_argument('--disable-domain-reliability')
            chrome_options.add_argument('--disable-features=TranslateUI')
            chrome_options.add_argument('--disable-features=BlinkGenPropertyTrees')
            chrome_options.add_argument('--disable-features=AudioServiceOutOfProcess')
            chrome_options.add_argument('--disable-features=NetworkService')
            chrome_options.add_argument('--disable-features=NetworkServiceLogging')
            chrome_options.add_argument('--disable-features=NetworkServiceInProcess')
            chrome_options.add_argument('--disable-features=NetworkServiceSandbox')
            chrome_options.add_argument('--disable-features=NetworkServiceInProcess2')
            chrome_options.add_argument('--disable-features=NetworkServiceInProcess3')
            chrome_options.add_argument('--disable-features=NetworkServiceInProcess4')
            chrome_options.add_argument('--disable-features=NetworkServiceInProcess5')
            chrome_options.add_argument('--disable-features=NetworkServiceInProcess6')
            chrome_options.add_argument('--disable-features=NetworkServiceInProcess7')
            chrome_options.add_argument('--disable-features=NetworkServiceInProcess8')
            chrome_options.add_argument('--disable-features=NetworkServiceInProcess9')
            chrome_options.add_argument('--disable-features=NetworkServiceInProcess10')
            
            # 内存优化
            chrome_options.add_argument('--memory-pressure-off')
            chrome_options.add_argument('--max_old_space_size=4096')
            chrome_options.add_argument('--disable-software-rasterizer')
            
            # 用户代理设置
            chrome_options.add_argument(f'--user-agent={HEADERS["User-Agent"]}')
            
            # 代理设置（仅在非GitHub Actions环境中）
            if not is_github_actions and PROXY_CONFIG.get('http'):
                proxy_url = PROXY_CONFIG['http']
                if proxy_url.startswith('socks5://'):
                    # 对于SOCKS5代理，需要特殊处理
                    chrome_options.add_argument(f'--proxy-server={proxy_url}')
                    print(f"✓ 已配置SOCKS5代理: {proxy_url}")
                else:
                    chrome_options.add_argument(f'--proxy-server={proxy_url}')
                    print(f"✓ 已配置代理: {proxy_url}")
            elif is_github_actions:
                print("⚠️  GitHub Actions环境中跳过代理设置")
            
            # 窗口设置
            window_size = SELENIUM_CONFIG.get('window_size', '1920,1080')
            chrome_options.add_argument(f'--window-size={window_size}')
            
            # 无头模式设置
            if SELENIUM_CONFIG.get('headless', False):
                chrome_options.add_argument('--headless')
            else:
                chrome_options.add_argument('--start-maximized')
            
            # 使用本地ChromeDriver（如果存在）
            try:
                # 首先尝试使用本地ChromeDriver
                import os
                local_chromedriver = os.path.join(os.getcwd(), 'chromedriver.exe')
                if os.path.exists(local_chromedriver):
                    print("✓ 使用本地ChromeDriver")
                    service = Service(local_chromedriver)
                else:
                    # 如果本地没有，则使用系统ChromeDriver
                    print("使用系统ChromeDriver...")
                    service = Service()
            except Exception as e:
                print(f"ChromeDriver初始化失败: {e}")
                print("尝试使用默认ChromeDriver...")
                service = Service()
            
            # 创建WebDriver
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # 设置页面加载超时
            page_load_timeout = SELENIUM_CONFIG.get('page_load_timeout', 10)
            self.driver.set_page_load_timeout(page_load_timeout)
            
            # 设置隐式等待时间
            implicit_wait = SELENIUM_CONFIG.get('implicit_wait', 3)
            self.driver.implicitly_wait(implicit_wait)
            
            # 执行反检测脚本
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print("✓ Selenium WebDriver初始化成功")
            
        except Exception as e:
            print(f"✗ Selenium WebDriver初始化失败: {e}")
            print("将回退到requests模式")
            self.use_selenium = False
            self.driver = None
    
    def is_github_actions_environment(self):
        """检测是否在GitHub Actions环境中"""
        github_actions_indicators = [
            'GITHUB_ACTIONS',  # GitHub Actions环境变量
            'CI',              # 通用CI环境变量
            '/opt/hostedtoolcache',  # GitHub Actions工具缓存路径
            '/home/runner',    # GitHub Actions运行器路径
            '/usr/local/share',  # GitHub Actions共享路径
        ]
        
        # 检查环境变量
        for indicator in github_actions_indicators:
            if os.environ.get(indicator):
                return True
        
        # 检查当前工作目录
        current_dir = os.getcwd()
        for indicator in github_actions_indicators:
            if indicator in current_dir:
                return True
        
        # 检查系统路径
        import platform
        if platform.system() == 'Linux':
            # 在Linux上检查常见路径
            for path in ['/opt/hostedtoolcache', '/home/runner', '/usr/local/share']:
                if os.path.exists(path):
                    return True
        
        return False
    
    def start_ad_monitor(self):
        """启动广告监控线程"""
        if not self.use_selenium or not self.driver:
            return
        
        try:
            self.stop_ad_monitor = False
            self.ad_monitor_thread = threading.Thread(target=self.ad_monitor_worker, daemon=True)
            self.ad_monitor_thread.start()
            if DEBUG['verbose']:
                print("✓ 广告监控线程已启动")
        except Exception as e:
            print(f"启动广告监控线程失败: {e}")
    
    def stop_ad_monitor_thread(self):
        """停止广告监控线程"""
        if self.ad_monitor_thread:
            self.stop_ad_monitor = True
            self.ad_monitor_thread.join(timeout=5)
            if DEBUG['verbose']:
                print("✓ 广告监控线程已停止")
    
    def ad_monitor_worker(self):
        """广告监控工作线程"""
        while not self.stop_ad_monitor:
            try:
                if self.driver:
                    # 检查并关闭广告标签页
                    self.close_ad_tabs()
                
                # 每5秒检查一次
                time.sleep(5)
                
            except Exception as e:
                if DEBUG['verbose']:
                    print(f"广告监控线程出错: {e}")
                time.sleep(5)
    
    def close_driver(self):
        """关闭WebDriver"""
        # 停止广告监控线程
        self.stop_ad_monitor_thread()
        
        if self.driver:
            try:
                self.driver.quit()
                print("✓ WebDriver已关闭")
            except Exception as e:
                print(f"关闭WebDriver时出错: {e}")
            finally:
                self.driver = None
    
    def close_ad_tabs(self):
        """关闭广告标签页"""
        try:
            if not self.driver:
                return
            
            # 获取所有标签页
            all_handles = self.driver.window_handles
            if len(all_handles) <= 1:
                return
            
            # 记录主标签页（第一个标签页）
            main_handle = all_handles[0]
            
            # 检查其他标签页
            for handle in all_handles[1:]:
                try:
                    # 切换到标签页
                    self.driver.switch_to.window(handle)
                    
                    # 获取当前URL
                    current_url = self.driver.current_url
                    
                    # 检查是否为广告页面（非pornhub.com域名）
                    if not self.is_valid_pornhub_url(current_url):
                        if DEBUG['verbose']:
                            print(f"关闭广告标签页: {current_url}")
                        
                        # 关闭标签页
                        self.driver.close()
                        
                        # 切换回主标签页
                        self.driver.switch_to.window(main_handle)
                        
                except Exception as e:
                    if DEBUG['verbose']:
                        print(f"关闭广告标签页时出错: {e}")
                    # 确保切换回主标签页
                    try:
                        self.driver.switch_to.window(main_handle)
                    except:
                        pass
                        
        except Exception as e:
            if DEBUG['verbose']:
                print(f"处理广告标签页时出错: {e}")
    
    def is_valid_pornhub_url(self, url):
        """检查是否为有效的Pornhub URL"""
        try:
            from urllib.parse import urlparse
            
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            # 有效的Pornhub域名
            valid_domains = [
                'pornhub.com',
                'www.pornhub.com',
                'cn.pornhub.com',
                'www.cn.pornhub.com',
                'jp.pornhub.com',
                'www.jp.pornhub.com',
                'phncdn.com',  # Pornhub CDN
                'www.phncdn.com'
            ]
            
            # 检查是否为有效域名
            for valid_domain in valid_domains:
                if domain == valid_domain or domain.endswith('.' + valid_domain):
                    return True
            
            # 检查是否为localhost或127.0.0.1（本地测试）
            if domain in ['localhost', '127.0.0.1']:
                return True
            
            return False
            
        except Exception as e:
            if DEBUG['verbose']:
                print(f"URL验证出错: {e}")
            return False
    
    def handle_age_verification(self):
        """处理年龄验证弹窗 - 强制点击版本"""
        try:
            print("开始处理年龄验证...")
            
            # 无论模态框是否可见，都尝试查找并点击按钮
            button_found = False
            
            # 方法1: 通过XPath查找包含特定文本的按钮
            try:
                # 查找包含完整文本"我年满 18 岁 - 输入"的按钮
                age_button = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '我年满 18 岁 - 输入')]"))
                )
                
                if age_button:
                    print(f"✓ 找到年龄验证按钮: '{age_button.text}'")
                    
                    # 滚动到按钮位置
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", age_button)
                    time.sleep(0.5)
                    
                    # 点击按钮
                    age_button.click()
                    print("✓ 成功点击年龄验证按钮")
                    button_found = True
                    
                    # 等待模态框消失
                    try:
                        WebDriverWait(self.driver, 5).until(
                            EC.invisibility_of_element_located((By.ID, "js-ageDisclaimerModal"))
                        )
                        print("✓ 年龄验证模态框已消失，验证成功")
                        return True
                    except TimeoutException:
                        print("⚠️  点击后模态框未消失，可能验证失败")
                        return False
                    
            except TimeoutException:
                print("通过XPath未找到年龄验证按钮，尝试其他方法...")
                # 如果完整文本匹配失败，尝试部分文本匹配
                try:
                    age_button = WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '我年满 18 岁')]"))
                    )
                    
                    if age_button:
                        print(f"✓ 通过部分文本匹配找到年龄验证按钮: '{age_button.text}'")
                        
                        # 滚动到按钮位置
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", age_button)
                        time.sleep(0.5)
                        
                        # 点击按钮
                        age_button.click()
                        print("✓ 成功点击年龄验证按钮")
                        button_found = True
                        
                        # 等待模态框消失
                        try:
                            WebDriverWait(self.driver, 5).until(
                                EC.invisibility_of_element_located((By.ID, "js-ageDisclaimerModal"))
                            )
                            print("✓ 年龄验证模态框已消失，验证成功")
                            return True
                        except TimeoutException:
                            print("⚠️  点击后模态框未消失，可能验证失败")
                            return False
                except TimeoutException:
                    print("部分文本匹配也失败")
            except Exception as e:
                print(f"XPath方法失败: {e}")
            
            # 方法2: 如果XPath失败，尝试CSS选择器
            if not button_found:
                age_button_selectors = [
                    "button.gtm-event-age-verification.js-closeAgeModal.buttonOver18.orangeButton",
                    "button.gtm-event-age-verification",
                    "button.js-closeAgeModal",
                    "button.buttonOver18",
                    "button.orangeButton",
                    "button[data-event='age_verification']",
                    "button[data-label='over18_enter']",
                    ".orangeButton"
                ]
                
                for selector in age_button_selectors:
                    try:
                        age_button = WebDriverWait(self.driver, 2).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        
                        if age_button:
                            print(f"✓ 通过CSS选择器找到按钮: {selector}")
                            
                            # 滚动到按钮位置
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", age_button)
                            time.sleep(0.5)
                            
                            # 点击按钮
                            age_button.click()
                            print("✓ 成功点击年龄验证按钮")
                            button_found = True
                            
                            # 等待模态框消失
                            try:
                                WebDriverWait(self.driver, 5).until(
                                    EC.invisibility_of_element_located((By.ID, "js-ageDisclaimerModal"))
                                )
                                print("✓ 年龄验证模态框已消失，验证成功")
                                return True
                            except TimeoutException:
                                print("⚠️  点击后模态框未消失，可能验证失败")
                                return False
                            break
                            
                    except TimeoutException:
                        continue
                    except Exception as e:
                        print(f"CSS选择器 {selector} 失败: {e}")
                        continue
            
            # 方法3: 如果CSS选择器失败，尝试JavaScript点击
            if not button_found:
                print("尝试JavaScript方法...")
                js_click_scripts = [
                    "document.querySelector('button.gtm-event-age-verification.js-closeAgeModal.buttonOver18.orangeButton').click();",
                    "document.querySelector('button.gtm-event-age-verification').click();",
                    "document.querySelector('button.js-closeAgeModal').click();",
                    "document.querySelector('button.buttonOver18').click();",
                    "document.querySelector('button.orangeButton').click();",
                    "Array.from(document.querySelectorAll('button')).find(btn => btn.textContent.includes('我年满 18 岁 - 输入')).click();",
                    "Array.from(document.querySelectorAll('button')).find(btn => btn.textContent.includes('我年满 18 岁')).click();",
                    "Array.from(document.querySelectorAll('button')).find(btn => btn.textContent.includes('输入')).click();"
                ]
                
                for script in js_click_scripts:
                    try:
                        self.driver.execute_script(script)
                        print("✓ 通过JavaScript成功点击年龄验证按钮")
                        button_found = True
                        
                        # 等待模态框消失
                        try:
                            WebDriverWait(self.driver, 5).until(
                                EC.invisibility_of_element_located((By.ID, "js-ageDisclaimerModal"))
                            )
                            print("✓ 年龄验证模态框已消失，验证成功")
                            return True
                        except TimeoutException:
                            print("⚠️  点击后模态框未消失，可能验证失败")
                            return False
                        break
                    except Exception as e:
                        print(f"JavaScript脚本失败: {e}")
                        continue
            
            if not button_found:
                print("⚠️  未找到可点击的年龄验证按钮")
                return False
            else:
                print("⚠️  点击了按钮但模态框未消失")
                return False
                
        except Exception as e:
            print(f"处理年龄验证时出错: {e}")
            return False
    

    
    def get_page(self, url):
        """获取页面内容"""
        # 如果使用Selenium且driver可用
        if self.use_selenium and self.driver:
            return self.get_page_selenium(url)
        else:
            return self.get_page_requests(url)
    
    def get_page_selenium(self, url):
        """使用Selenium获取页面内容"""
        max_retries = SCRAPER_CONFIG.get('max_retries', 5)  # 增加重试次数
        
        for attempt in range(max_retries):
            try:
                if DEBUG['verbose']:
                    print(f"Selenium访问: {url} (尝试 {attempt + 1}/{max_retries})")
                
                # 访问页面
                self.driver.get(url)
                
                # 等待页面基本加载
                time.sleep(2)
                
                # 检查页面类型
                page_source = self.driver.page_source
                page_type = self.check_page_type(page_source)
                
                # 根据页面类型进行处理
                if page_type == "region_restricted":
                    print("检测到地区限制页面，尝试绕过...")
                    if self.handle_region_restriction():
                        # 重新获取页面源码
                        page_source = self.driver.page_source
                        page_type = self.check_page_type(page_source)
                    else:
                        print("无法绕过地区限制，尝试使用代理...")
                        # 这里可以添加代理切换逻辑
                        if attempt < max_retries - 1:
                            time.sleep(3)
                        continue
                
                # 处理年龄验证页面
                if page_type == "age_verification":
                    print("检测到年龄验证页面，开始处理...")
                    if not SELENIUM_CONFIG.get('fast_mode', False):
                        age_verification_result = self.handle_age_verification()
                        if age_verification_result:
                            print("✓ 年龄验证成功")
                            # 重新获取页面源码
                            page_source = self.driver.page_source
                            page_type = self.check_page_type(page_source)
                            print(f"验证后页面类型: {page_type}")
                        else:
                            print("⚠️  年龄验证失败")
                
                # 无论页面类型如何，都尝试处理年龄验证（以防模态框不可见但按钮存在）
                if not SELENIUM_CONFIG.get('fast_mode', False):
                    print("尝试处理年龄验证（强制检查）...")
                    age_verification_result = self.handle_age_verification()
                    if age_verification_result:
                        print("✓ 年龄验证成功")
                        # 重新获取页面源码
                        page_source = self.driver.page_source
                        page_type = self.check_page_type(page_source)
                        print(f"验证后页面类型: {page_type}")
                    else:
                        print("⚠️  年龄验证失败或不需要验证")
                
                # 等待页面基本加载完成（减少等待时间）
                explicit_wait = SELENIUM_CONFIG.get('explicit_wait', 8)  # 减少到8秒
                try:
                    WebDriverWait(self.driver, explicit_wait).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                except TimeoutException:
                    # 如果超时，尝试获取当前页面源码
                    if DEBUG['verbose']:
                        print("页面加载超时，尝试获取当前内容...")
                
                # 关闭广告标签页
                self.close_ad_tabs()
                
                # 获取最终页面源码
                page_source = self.driver.page_source
                
                # 检查页面内容是否有效
                if page_source and len(page_source) > 1000:  # 确保页面内容足够
                    if DEBUG['verbose']:
                        print(f"✓ Selenium成功获取页面: {len(page_source)} 字符")
                    return page_source
                else:
                    print(f"页面内容无效或过短: {len(page_source) if page_source else 0} 字符")
                    if attempt < max_retries - 1:
                        time.sleep(3)
                    continue
                
            except TimeoutException as e:
                print(f"Selenium页面加载超时 (尝试 {attempt + 1}/{max_retries}): {e}")
                # 关闭可能的广告标签页
                self.close_ad_tabs()
                if attempt < max_retries - 1:
                    time.sleep(3)
                continue
                
            except WebDriverException as e:
                print(f"Selenium错误 (尝试 {attempt + 1}/{max_retries}): {e}")
                # 关闭可能的广告标签页
                self.close_ad_tabs()
                if attempt < max_retries - 1:
                    time.sleep(5)
                continue
                
            except Exception as e:
                print(f"Selenium获取页面失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                # 关闭可能的广告标签页
                self.close_ad_tabs()
                if attempt < max_retries - 1:
                    time.sleep(2)
                continue
        
        print(f"Selenium所有重试都失败了: {url}")
        return None
    
    def get_page_requests(self, url):
        """使用requests获取页面内容"""
        max_retries = SCRAPER_CONFIG.get('max_retries', 3)
        
        # 检测是否在GitHub Actions环境中
        is_github_actions = self.is_github_actions_environment()
        
        for attempt in range(max_retries):
            try:
                # 完全忽略SSL验证
                kwargs = {
                    'headers': self.headers,
                    'timeout': SCRAPER_CONFIG['timeout'],
                    'verify': False,  # 不验证SSL证书
                    'allow_redirects': True,  # 允许重定向
                }
                
                # 在GitHub Actions环境中不使用代理
                if is_github_actions:
                    if attempt == 0:
                        response = requests.get(url, **kwargs)
                    else:
                        # 重试时也不使用代理
                        response = requests.get(url, **kwargs)
                else:
                    # 尝试不使用代理
                    if attempt == 0:
                        response = requests.get(url, **kwargs)
                    else:
                        # 后续尝试使用代理
                        kwargs['proxies'] = self.proxies
                        response = requests.get(url, **kwargs)
                
                response.raise_for_status()
                return response.text
                
            except requests.exceptions.SSLError as e:
                print(f"SSL错误 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(3)  # SSL错误等待3秒
                continue
                
            except requests.exceptions.ConnectionError as e:
                print(f"连接错误 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)  # 连接错误等待5秒
                continue
                
            except requests.exceptions.Timeout as e:
                print(f"请求超时 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(3)  # 超时等待3秒
                continue
                
            except Exception as e:
                print(f"获取页面失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)  # 其他错误等待2秒
                continue
        
        print(f"所有重试都失败了: {url}")
        return None
    
    def parse_video_list(self, html_content):
        """解析视频列表页面"""
        soup = BeautifulSoup(html_content, 'html.parser')
        video_list = soup.find('ul', {'id': 'videoCategory'})
        
        if not video_list:
            print("未找到视频列表")
            return []
        
        videos = []
        for li in video_list.find_all('li', class_='pcVideoListItem'):
            try:
                # 提取视频信息
                video_data = self.extract_video_info(li)
                if video_data:
                    videos.append(video_data)
            except Exception as e:
                print(f"解析视频信息失败: {e}")
                continue
        
        return videos
    
    def check_is_last_page(self, html_content):
        """检查是否为最后一页"""
        soup = BeautifulSoup(html_content, 'html.parser')
        showing_counter = soup.find('div', class_='showingCounter')
        
        if showing_counter:
            counter_text = showing_counter.get_text(strip=True)
            # 匹配格式：显示1-32个，共有749个
            import re
            pattern = r'显示(\d+)-(\d+)个，共有(\d+)个'
            match = re.search(pattern, counter_text)
            
            if match:
                end_num = int(match.group(2))
                total_num = int(match.group(3))
                return end_num == total_num
        
        return False
    
    def get_total_pages(self, html_content):
        """获取总页数"""
        soup = BeautifulSoup(html_content, 'html.parser')
        showing_counter = soup.find('div', class_='showingCounter')
        
        if showing_counter:
            counter_text = showing_counter.get_text(strip=True)
            import re
            pattern = r'显示(\d+)-(\d+)个，共有(\d+)个'
            match = re.search(pattern, counter_text)
            
            if match:
                start_num = int(match.group(1))
                end_num = int(match.group(2))
                total_num = int(match.group(3))
                
                # 计算总页数
                items_per_page = end_num - start_num + 1
                total_pages = (total_num + items_per_page - 1) // items_per_page
                return total_pages
        
        return None
    
    def extract_video_info(self, li_element):
        """从li元素中提取视频信息"""
        try:
            # 获取视频ID和viewkey
            video_id = li_element.get('data-video-id', '')
            viewkey = li_element.get('data-video-vkey', '')
            
            if not viewkey:
                return None
            
            # 获取视频链接
            link_element = li_element.find('a', class_='linkVideoThumb')
            video_url = urljoin(self.base_url, link_element.get('href', '')) if link_element else ''
            
            # 获取标题
            title_element = li_element.find('a', class_='gtm-event-thumb-click')
            title = title_element.get_text(strip=True) if title_element else ''
            
            # 获取详细信息（发布时间、分类、m3u8地址）
            detailed_info = self.get_video_detailed_info(viewkey)
            
            # 获取缩略图信息
            img_element = li_element.find('img')
            thumbnail_url = ''
            alt_text = ''
            if img_element:
                # 优先使用data-mediumthumb属性
                thumbnail_url = img_element.get('data-mediumthumb', '')
                alt_text = img_element.get('alt', '')
                
                # 如果data-mediumthumb为空，尝试src属性
                if not thumbnail_url:
                    thumbnail_url = img_element.get('src', '')
                
                # 如果还是为空，尝试其他可能的属性
                if not thumbnail_url:
                    thumbnail_url = img_element.get('data-src', '')
                if not thumbnail_url:
                    thumbnail_url = img_element.get('data-original', '')
            
            # 获取预览视频URL - 尝试多个可能的属性
            preview_url = ''
            if img_element:
                # 优先尝试 data-mediabook 属性
                preview_url = img_element.get('data-mediabook', '')
                
                # 如果data-mediabook为空，尝试其他可能的属性
                if not preview_url:
                    preview_url = img_element.get('data-preview', '')
                if not preview_url:
                    preview_url = img_element.get('data-video-preview', '')
                if not preview_url:
                    preview_url = img_element.get('data-video-src', '')
                if not preview_url:
                    # 尝试从其他相关元素获取
                    preview_element = li_element.find('video', {'data-preview': True})
                    if preview_element:
                        preview_url = preview_element.get('src', '')
                
                # 如果还是找不到，尝试从链接元素获取
                if not preview_url:
                    link_element = li_element.find('a', class_='linkVideoThumb')
                    if link_element:
                        preview_url = link_element.get('data-preview', '')
                
                # 清理URL（移除HTML实体编码）
                if preview_url:
                    import html
                    preview_url = html.unescape(preview_url)
            
            # 注意：实际HTML中可能没有预览视频URL，这是正常现象
            # 某些视频可能没有预览视频，或者预览视频需要特殊权限
            
            # 获取时长
            duration_element = li_element.find('var', class_='duration')
            duration = duration_element.get_text(strip=True) if duration_element else ''
            
            # 获取上传者信息
            uploader = ''
            # 尝试从usernameBadgesWrapper中获取
            uploader_element = li_element.find('span', class_='usernameBadgesWrapper')
            if uploader_element:
                # 在usernameBadgesWrapper中查找链接
                uploader_link = uploader_element.find('a')
                if uploader_link:
                    uploader = uploader_link.get_text(strip=True)
            
            # 如果上面的方法失败，尝试其他选择器
            if not uploader:
                uploader_element = li_element.find('a', href=lambda x: x and '/model/' in x)
                if uploader_element:
                    uploader = uploader_element.get_text(strip=True)
            
            if not uploader:
                uploader_element = li_element.find('a', class_='')
                if uploader_element:
                    uploader = uploader_element.get_text(strip=True)
            
            # 如果还是找不到，尝试从title属性获取
            if not uploader:
                uploader_element = li_element.find('a', title=True)
                if uploader_element and uploader_element.get('title'):
                    uploader = uploader_element.get('title')
            
            # 获取观看次数
            views = ''
            views_element = li_element.find('span', class_='views')
            if views_element:
                views = views_element.get_text(strip=True)
            
            # 如果上面的方法失败，尝试其他选择器
            if not views:
                views_element = li_element.find('var')
                if views_element and views_element.parent and 'views' in views_element.parent.get('class', []):
                    views = views_element.get_text(strip=True) + '次观看'
            
            # 调试信息
            if DEBUG['verbose']:
                if preview_url:
                    print(f"✓ 找到预览视频URL: {preview_url[:100]}...")
                else:
                    print(f"✗ 未找到预览视频URL，视频标题: {title[:50]}...")
                    # 输出img元素的所有属性用于调试
                    if img_element:
                        print(f"  img元素属性:")
                        for attr, value in img_element.attrs.items():
                            if 'preview' in attr.lower() or 'video' in attr.lower() or 'media' in attr.lower():
                                print(f"    {attr}: {value[:100]}...")
            
            # 合并详细信息
            result = {
                'video_id': video_id,
                'viewkey': viewkey,
                'video_url': video_url,
                'title': title,
                'thumbnail_url': thumbnail_url,
                'alt_text': alt_text,
                'preview_url': preview_url,
                'duration': duration,
                'uploader': uploader,
                'views': views
            }
            
            # 添加详细信息
            if detailed_info:
                result.update(detailed_info)
            
            return result
        except Exception as e:
            print(f"提取视频信息时出错: {e}")
            return None
    
    def get_video_detailed_info(self, viewkey):
        """获取视频详细信息（发布时间、分类、m3u8地址）"""
        try:
            # 构建视频页面URL
            video_url = f"https://cn.pornhub.com/view_video.php?viewkey={viewkey}"
            
            # 获取视频页面
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    kwargs = {
                        'headers': self.headers,
                        'timeout': 30,
                        'verify': False,
                        'allow_redirects': True,
                    }
                    
                    if attempt == 0:
                        response = requests.get(video_url, **kwargs)
                    else:
                        kwargs['proxies'] = self.proxies
                        response = requests.get(video_url, **kwargs)
                    
                    response.raise_for_status()
                    html_content = response.text
                    break
                    
                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(3)
                    else:
                        print(f"获取视频详细信息失败: {e}")
                        return {
                            'publish_time': '',
                            'categories': [],
                            'm3u8_urls': [],
                            'best_m3u8_url': ''
                        }
            
            # 解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 1. 获取发布时间
            publish_time = ''
            video_info = soup.find('div', class_='videoInfo')
            if video_info:
                publish_time = video_info.get_text(strip=True)
            
            # 2. 获取分类数据
            categories = []
            categories_wrapper = soup.find('div', class_='categoriesWrapper')
            if categories_wrapper:
                category_links = categories_wrapper.find_all('a')
                for link in category_links:
                    category_name = link.get_text(strip=True)
                    category_url = link.get('href', '')
                    if category_name and category_name != '建议:':
                        categories.append({
                            'name': category_name,
                            'url': category_url
                        })
            
            # 3. 获取m3u8地址
            m3u8_urls = []
            scripts = soup.find_all('script')
            
            for script in scripts:
                script_content = script.string
                if script_content:
                    # 查找m3u8相关的URL
                    m3u8_patterns = [
                        r'https?://[^"\']*\.m3u8[^"\']*',
                        r'"videoUrl":"([^"]*\.m3u8[^"]*)"',
                        r"'videoUrl':'([^']*\.m3u8[^']*)'",
                        r'"url":"([^"]*\.m3u8[^"]*)"',
                        r"'url':'([^']*\.m3u8[^']*)'",
                    ]
                    
                    for pattern in m3u8_patterns:
                        matches = re.findall(pattern, script_content, re.IGNORECASE)
                        for match in matches:
                            if isinstance(match, tuple):
                                match = match[0]
                            if match and match not in m3u8_urls:
                                # 清理URL（移除转义字符）
                                clean_url = match.replace('\\/', '/')
                                m3u8_urls.append(clean_url)
            
            # 4. 选择最佳m3u8地址（优先1080P，其次720P）
            best_m3u8_url = ''
            if m3u8_urls:
                # 按优先级排序
                priority_order = ['1080P', '720P', '480P', '240P']
                for priority in priority_order:
                    for url in m3u8_urls:
                        if priority in url:
                            best_m3u8_url = url
                            break
                    if best_m3u8_url:
                        break
                
                # 如果没有找到优先级匹配的，使用第一个
                if not best_m3u8_url and m3u8_urls:
                    best_m3u8_url = m3u8_urls[0]
            
            return {
                'publish_time': publish_time,
                'categories': categories,
                'm3u8_urls': m3u8_urls,
                'best_m3u8_url': best_m3u8_url
            }
            
        except Exception as e:
            print(f"获取视频详细信息时出错: {e}")
            return {
                'publish_time': '',
                'categories': [],
                'm3u8_urls': [],
                'best_m3u8_url': ''
            }
    
    def is_video_completed(self, viewkey):
        """检查视频是否已完成采集"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            folder_path = os.path.join(script_dir, OUTPUT_CONFIG['data_folder'], viewkey)
            log_file = os.path.join(folder_path, 'collection_log.txt')
            
            if not os.path.exists(log_file):
                return False
            
            # 读取日志文件
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否包含成功标记
            return '采集状态: 成功' in content
            
        except Exception as e:
            return False
    
    def create_collection_log(self, video_data, folder_path, success=True, error_msg=''):
        """创建采集日志"""
        try:
            import datetime
            
            log_file = os.path.join(folder_path, 'collection_log.txt')
            
            # 获取当前时间
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 构建日志内容
            log_content = f"""采集日志
================

采集时间: {current_time}
视频ID: {video_data.get('video_id', 'N/A')}
ViewKey: {video_data.get('viewkey', 'N/A')}
视频标题: {video_data.get('title', 'N/A')}
视频链接: {video_data.get('video_url', 'N/A')}

采集信息:
- 缩略图: {'已下载' if video_data.get('thumbnail_url') else '无'}
- 预览视频: {'已下载' if video_data.get('preview_url') else '无'}
- 发布时间: {video_data.get('publish_time', 'N/A')}
- 分类数量: {len(video_data.get('categories', []))}
- m3u8地址: {'已获取' if video_data.get('best_m3u8_url') else '无'}

采集状态: {'成功' if success else '失败'}
"""
            
            if not success and error_msg:
                log_content += f"错误信息: {error_msg}\n"
            
            # 写入日志文件
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(log_content)
            
            return True
            
        except Exception as e:
            print(f"创建采集日志失败: {e}")
            return False
    
    def download_file(self, url, filepath):
        """下载文件"""
        max_retries = SCRAPER_CONFIG.get('max_retries', 3)
        
        # 检测是否在GitHub Actions环境中
        is_github_actions = self.is_github_actions_environment()
        
        for attempt in range(max_retries):
            try:
                # 完全忽略SSL验证
                kwargs = {
                    'headers': self.headers,
                    'timeout': SCRAPER_CONFIG['timeout'],
                    'verify': False,  # 不验证SSL证书
                    'allow_redirects': True,  # 允许重定向
                }
                
                # 在GitHub Actions环境中不使用代理
                if is_github_actions:
                    if attempt == 0:
                        response = requests.get(url, **kwargs)
                    else:
                        # 重试时也不使用代理
                        response = requests.get(url, **kwargs)
                else:
                    # 尝试不使用代理
                    if attempt == 0:
                        response = requests.get(url, **kwargs)
                    else:
                        # 后续尝试使用代理
                        kwargs['proxies'] = self.proxies
                        response = requests.get(url, **kwargs)
                
                response.raise_for_status()
                
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return True
                
            except requests.exceptions.SSLError as e:
                print(f"下载SSL错误 {url} (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(3)  # SSL错误等待3秒
                continue
                
            except requests.exceptions.ConnectionError as e:
                print(f"下载连接错误 {url} (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)  # 连接错误等待5秒
                continue
                
            except requests.exceptions.Timeout as e:
                print(f"下载超时 {url} (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(3)  # 超时等待3秒
                continue
                
            except Exception as e:
                print(f"下载文件失败 {url} (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)  # 其他错误等待2秒
                continue
        
        print(f"下载失败，所有重试都失败了: {url}")
        return False
    
    def download_worker(self, worker_id):
        """下载工作线程"""
        while True:
            try:
                # 从队列获取下载任务
                task = self.download_queue.get(timeout=1)
                if task is None:  # 结束信号
                    break
                
                url, filepath, task_type = task
                
                # 只在显示工作线程信息时输出
                if SCRAPER_CONFIG.get('show_worker_info', False):
                    print(f"线程 {worker_id}: 开始下载 {task_type} - {os.path.basename(filepath)}")
                
                success = self.download_file(url, filepath)
                
                with self.download_lock:
                    self.download_results[filepath] = success
                    if success and SCRAPER_CONFIG.get('show_worker_info', False):
                        print(f"线程 {worker_id}: ✓ {task_type} 下载成功")
                    elif not success:
                        print(f"线程 {worker_id}: ✗ {task_type} 下载失败")
                
                self.download_queue.task_done()
                
            except Exception as e:
                # 只显示真正的错误，忽略空错误和超时
                if str(e) and not any(empty_error in str(e).lower() for empty_error in ['timeout', 'empty', 'none']):
                    print(f"线程 {worker_id} 错误: {e}")
                try:
                    self.download_queue.task_done()
                except ValueError:
                    pass  # 忽略task_done调用过多的错误
    
    def start_download_workers(self):
        """启动下载工作线程"""
        self.download_workers = []
        num_threads = SCRAPER_CONFIG.get('download_threads', 30)
        
        for i in range(num_threads):
            worker = threading.Thread(target=self.download_worker, args=(i+1,))
            worker.daemon = True
            worker.start()
            self.download_workers.append(worker)
        
        # 只在调试模式下显示启动信息
        if DEBUG['verbose']:
            print(f"启动 {num_threads} 个下载线程")
    
    def stop_download_workers(self):
        """停止下载工作线程"""
        # 发送结束信号
        for _ in self.download_workers:
            self.download_queue.put(None)
        
        # 等待所有线程结束
        for worker in self.download_workers:
            worker.join()
        
        # 只在调试模式下显示停止信息
        if DEBUG['verbose']:
            print("所有下载线程已停止")
    
    def add_download_task(self, url, filepath, task_type):
        """添加下载任务到队列"""
        self.download_queue.put((url, filepath, task_type))
    
    def wait_for_downloads(self):
        """等待所有下载完成"""
        self.download_queue.join()
        return self.download_results
    
    def create_html_page(self, video_data, folder_path):
        """创建HTML页面"""
        # 获取m3u8地址列表
        m3u8_urls = video_data.get('m3u8_urls', [])
        best_m3u8_url = video_data.get('best_m3u8_url', '')
        
        # 生成质量链接HTML (用于下载链接区域)
        quality_links_html = ""
        if m3u8_urls:
            quality_links_html = f"""
                <div class="quality-section">
                    <h4>所有可用质量:</h4>
                    <div class="quality-links">
                        {self._generate_quality_links(m3u8_urls)}
                    </div>
                </div>"""
        
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{video_data['title']}</title>

    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .video-container {{
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
        .video-info {{
            display: flex;
            flex-direction: column;
            gap: 20px;
            margin-bottom: 20px;
        }}
        @media (min-width: 768px) {{
            .video-info {{
                display: grid;
                grid-template-columns: 570px 1fr;
                gap: 30px;
                align-items: start;
            }}
        }}
        .thumbnail {{
            text-align: center;
            position: relative;
            width: 570px;
            height: 320px;
            margin: 0 auto;
            overflow: hidden;
            border-radius: 8px;
        }}
        .thumbnail img {{
            width: 570px;
            height: 320px;
            object-fit: cover;
            border-radius: 8px;
            cursor: pointer;
            transition: opacity 0.3s ease;
        }}
        .thumbnail:hover img {{
            opacity: 0;
        }}
        .thumbnail {{
            position: relative;
        }}
        .thumbnail:hover::after {{
            content: "🎬 点击观看视频";
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            pointer-events: none;
            z-index: 10;
        }}
        .info-details {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px 20px;
            align-items: start;
        }}
        @media (max-width: 768px) {{
            .info-details {{
                grid-template-columns: 1fr;
                gap: 10px;
            }}
        }}
        .info-item {{
            display: flex;
            flex-direction: column;
            gap: 5px;
        }}
        .info-label {{
            font-weight: bold;
            color: #666;
            font-size: 14px;
        }}
        .info-value {{
            color: #333;
            word-wrap: break-word;
        }}
        .truncated-link {{
            color: #007bff;
            text-decoration: none;
            display: block;
            max-width: 100%;
            overflow: hidden;
        }}
        .truncated-link:hover {{
            color: #0056b3;
            text-decoration: underline;
        }}
        .link-text {{
            display: block;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 100%;
        }}
        .video-player {{
            margin-top: 20px;
        }}
        .video-player video {{
            width: 100%;
            max-width: 800px;
            height: auto;
            border-radius: 8px;
        }}

        .download-links {{
            margin-top: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        .download-links a {{
            display: inline-block;
            margin: 5px 10px 5px 0;
            padding: 8px 15px;
            background: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            transition: background 0.3s;
        }}
        .download-links a:hover {{
            background: #0056b3;
        }}
        .download-items {{
            margin-bottom: 15px;
            text-align: center;
        }}
        .quality-section {{
            margin-top: 15px;
            padding: 15px;
            background: white;
            border-radius: 8px;
            border: 1px solid #dee2e6;
        }}
        .quality-section h4 {{
            margin-bottom: 10px;
            color: #495057;
            font-size: 14px;
            text-align: center;
        }}
        .quality-links {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            justify-content: center;
        }}
        .quality-link {{
            display: inline-block;
            padding: 6px 12px;
            background: #28a745;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            font-size: 12px;
            transition: background 0.3s;
        }}
        .quality-link:hover {{
            background: #1e7e34;
            color: white;
            text-decoration: none;
        }}
        .hover-video {{
            position: absolute;
            top: 0;
            left: 0;
            width: 570px;
            height: 320px;
            object-fit: cover;
            opacity: 0;
            transition: opacity 0.3s ease;
            border-radius: 8px;
            pointer-events: none;
        }}
        .thumbnail:hover .hover-video {{
            opacity: 1;
        }}
        
        /* M3U8下载区域样式 */
        .m3u8-download-section {{
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            border: 2px solid #e9ecef;
        }}
        .m3u8-download-section h3 {{
            margin-bottom: 20px;
            color: #495057;
            text-align: center;
            font-size: 22px;
        }}
        .download-methods {{
            display: flex;
            flex-direction: column;
            gap: 15px;
        }}
        .method-card {{
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border: 1px solid #dee2e6;
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 15px;
        }}
        .method-card h4 {{
            margin: 0;
            min-width: 150px;
            flex-shrink: 0;
        }}
        .method-card p {{
            margin: 0;
            min-width: 200px;
            flex-shrink: 0;
        }}
        .method-content {{
            flex: 1;
            min-width: 300px;
        }}
        .method-card h4 {{
            color: #28a745;
            font-size: 16px;
        }}
        .method-card p {{
            color: #6c757d;
            font-size: 14px;
        }}
        .download-btn {{
            display: inline-block;
            padding: 10px 16px;
            margin: 5px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            text-decoration: none;
            font-size: 14px;
            transition: background 0.3s;
        }}
        .download-btn:hover {{
            background: #0056b3;
            color: white;
        }}
        .online-tools {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .online-tool {{
            background: #28a745;
            white-space: nowrap;
        }}
        .online-tool:hover {{
            background: #1e7e34;
        }}
        .tool-commands {{
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}
        .command-item {{
            margin-bottom: 0;
        }}
        .command-item label {{
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #495057;
            font-size: 13px;
        }}
        .command-box {{
            display: flex;
            align-items: center;
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 8px;
        }}
        .command-box code {{
            flex: 1;
            background: none;
            border: none;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            word-break: break-all;
            color: #495057;
        }}
        .copy-btn {{
            padding: 4px 8px;
            background: #6c757d;
            color: white;
            border: none;
            border-radius: 3px;
            cursor: pointer;
            font-size: 12px;
            margin-left: 8px;
        }}
        .copy-btn:hover {{
            background: #545b62;
        }}
        .copy-btn.copied {{
            background: #28a745;
        }}
        .tool-links {{
            margin-top: 15px;
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .tool-link {{
            display: inline-block;
            padding: 6px 12px;
            background: #6c757d;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            font-size: 12px;
            transition: background 0.3s;
        }}
        .tool-link:hover {{
            background: #545b62;
            color: white;
            text-decoration: none;
        }}
        .extension-links {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .extension-link {{
            display: inline-block;
            padding: 8px 12px;
            background: #17a2b8;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            font-size: 13px;
            transition: background 0.3s;
        }}
        .extension-link:hover {{
            background: #138496;
            color: white;
            text-decoration: none;
        }}
        .m3u8-info {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            border: 1px solid #dee2e6;
        }}
        .info-row {{
            margin-bottom: 12px;
        }}
        .info-row:last-child {{
            margin-bottom: 0;
        }}
        .info-row label {{
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #495057;
            font-size: 13px;
        }}
        .url-box {{
            display: flex;
            align-items: center;
        }}
        .url-box input {{
            flex: 1;
            padding: 6px 10px;
            border: 1px solid #ced4da;
            border-radius: 4px;
            font-size: 12px;
            background: white;
        }}
        
        /* 响应式设计 */
        @media (max-width: 768px) {{
            .download-methods {{
                grid-template-columns: 1fr;
            }}
            .command-box {{
                flex-direction: column;
                align-items: stretch;
            }}
            .command-box code {{
                margin-bottom: 8px;
            }}
            .copy-btn {{
                margin-left: 0;
            }}
        }}

    </style>
</head>
<body>
    <div class="video-container">
        <h1 class="video-title">{video_data['title']}</h1>
        
        <div class="video-info">
            <div class="thumbnail" onclick="openBestQualityVideo()" style="cursor: pointer;" title="点击观看最佳质量视频">
                <img src="{OUTPUT_CONFIG['thumbnail_filename']}" alt="{video_data['alt_text']}" id="thumbnail" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                <div style="display:none; text-align:center; padding:20px; background:#f8f9fa; border-radius:8px; color:#666;">
                    <p>缩略图文件不存在</p>
                    <p>thumbnail.jpg</p>
                </div>
                <video class="hover-video" id="hoverVideo" muted loop onerror="this.style.display='none';" onclick="openBestQualityVideo()" title="点击观看最佳质量视频">
                    <source src="{OUTPUT_CONFIG['preview_filename']}" type="video/webm">
                </video>
            </div>
            <div class="info-details">
                <div class="info-item">
                    <span class="info-label">视频ID:</span>
                    <span class="info-value">{video_data['video_id']}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">ViewKey:</span>
                    <span class="info-value">{video_data['viewkey']}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">时长:</span>
                    <span class="info-value">{video_data['duration']}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">上传者:</span>
                    <span class="info-value">{video_data['uploader']}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">观看次数:</span>
                    <span class="info-value">{video_data['views']}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">发布时间:</span>
                    <span class="info-value">{video_data.get('publish_time', 'N/A')}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">分类:</span>
                    <span class="info-value">
                        {', '.join([cat['name'] for cat in video_data.get('categories', [])]) if video_data.get('categories') else 'N/A'}
                    </span>
                </div>
                <div class="info-item">
                    <span class="info-label">高清地址:</span>
                    <span class="info-value">
                        <a href="{video_data.get('best_m3u8_url', '')}" target="_blank" class="truncated-link" title="{video_data.get('best_m3u8_url', 'N/A')}">
                            <span class="link-text">{video_data.get('best_m3u8_url', 'N/A')}</span>
                        </a>
                    </span>
                </div>
                <div class="info-item">
                    <span class="info-label">原始链接:</span>
                    <span class="info-value">
                        <a href="{video_data['video_url']}" target="_blank" class="truncated-link" title="{video_data['video_url']}">
                            <span class="link-text">{video_data['video_url']}</span>
                        </a>
                    </span>
                </div>
            </div>
        </div>
        

        
        
        <div class="download-links">
            <h3>下载链接</h3>
            <div class="download-items">
                <a href="{OUTPUT_CONFIG['thumbnail_filename']}" download>下载缩略图</a>
                <a href="{OUTPUT_CONFIG['preview_filename']}" download>下载预览视频</a>
                <a href="{video_data['video_url']}" target="_blank">访问原始页面</a>
            </div>
            {quality_links_html}
        </div>
        
        <!-- 视频下载区域 -->
        <div class="m3u8-download-section">
            <h3>🎬 视频下载</h3>
            <div class="download-methods">
                <div class="method-card">
                    <h4>🌐 在线解析下载</h4>
                    <p>直接在新标签页中打开下载网站</p>
                    <div class="method-content">
                        <div class="online-tools">
                            <button class="download-btn online-tool" onclick="openDownloadSite('https://www.8loader.com/')">
                                8Loader 下载器
                            </button>
                            <button class="download-btn online-tool" onclick="openDownloadSite('https://download4.cc/')">
                                Download4 下载器
                            </button>
                            <button class="download-btn online-tool" onclick="openDownloadSite('https://www.clipconverter.cc/')">
                                ClipConverter
                            </button>
                        </div>
                    </div>
                </div>
                
                <div class="method-card">
                    <h4>🛠️ 工具下载</h4>
                    <p>适合技术用户：使用专业下载工具</p>
                    <div class="method-content">
                        <div class="tool-commands">
                        <div class="command-item">
                            <label>yt-dlp 命令：</label>
                            <div class="command-box">
                                <code id="ytdlp-command">yt-dlp "{video_data.get('best_m3u8_url', '')}"</code>
                                <button class="copy-btn" onclick="copyCommand('ytdlp-command')">复制</button>
                            </div>
                        </div>
                        <div class="command-item">
                            <label>N_m3u8DL-RE 命令：</label>
                            <div class="command-box">
                                <code id="n-m3u8dl-command">N_m3u8DL-RE "{video_data.get('best_m3u8_url', '')}" --save-name "{video_data.get('title', 'video')}"</code>
                                <button class="copy-btn" onclick="copyCommand('n-m3u8dl-command')">复制</button>
                            </div>
                        </div>
                        <div class="command-item">
                            <label>FFmpeg 命令：</label>
                            <div class="command-box">
                                <code id="ffmpeg-command">ffmpeg -i "{video_data.get('best_m3u8_url', '')}" -c copy "{video_data.get('title', 'video')}.mp4"</code>
                                <button class="copy-btn" onclick="copyCommand('ffmpeg-command')">复制</button>
                            </div>
                        </div>
                    </div>
                        <div class="tool-links">
                            <a href="https://github.com/yt-dlp/yt-dlp/releases" target="_blank" class="tool-link">下载 yt-dlp</a>
                            <a href="https://github.com/nilaoda/N_m3u8DL-RE/releases" target="_blank" class="tool-link">下载 N_m3u8DL-RE</a>
                            <a href="https://ffmpeg.org/download.html" target="_blank" class="tool-link">下载 FFmpeg</a>
                        </div>
                    </div>
                </div>
                
                <div class="method-card">
                    <h4>🧩 浏览器扩展</h4>
                    <p>便捷：安装浏览器扩展后直接下载</p>
                    <div class="method-content">
                        <div class="extension-links">
                            <a href="https://chrome.google.com/webstore/detail/video-downloader-plus/hkdmdpdhfaamhgaojpelccmeehpfljgf" target="_blank" class="extension-link">Video Downloader Plus</a>
                            <a href="https://chrome.google.com/webstore/detail/stream-recorder/iogidnfllpdhagebkblkgbfijkbkjdmm" target="_blank" class="extension-link">Stream Recorder</a>
                            <a href="https://chrome.google.com/webstore/detail/hls-downloader/apomkbibleoioihonaagahhkpalkdnhf" target="_blank" class="extension-link">HLS Downloader</a>
                        </div>
                    </div>
                </div>
                
                <div class="method-card">
                    <h4>📋 视频链接信息</h4>
                    <p>复制链接到其他下载工具使用</p>
                    <div class="method-content">
                        <div class="m3u8-info">
                            <div class="info-row">
                                <label>高清质量链接：</label>
                                <div class="url-box">
                                    <input type="text" id="best-m3u8-url" value="{video_data.get('best_m3u8_url', '')}" readonly>
                                    <button class="copy-btn" onclick="copyUrl('best-m3u8-url')">复制</button>
                                </div>
                            </div>
                            <div class="info-row">
                                <label>视频标题：</label>
                                <div class="url-box">
                                    <input type="text" id="video-title" value="{video_data.get('title', '')}" readonly>
                                    <button class="copy-btn" onclick="copyUrl('video-title')">复制</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // 鼠标悬停自动播放功能
        const thumbnail = document.getElementById('thumbnail');
        const hoverVideo = document.getElementById('hoverVideo');
        
        if (thumbnail && hoverVideo) {{
            thumbnail.addEventListener('mouseenter', function() {{
                hoverVideo.play();
            }});
            
            thumbnail.addEventListener('mouseleave', function() {{
                hoverVideo.pause();
                hoverVideo.currentTime = 0;
            }});
        }}
        
        // 打开最佳质量视频
        function openBestQualityVideo() {{
            const bestUrl = '{video_data.get('best_m3u8_url', '')}';
            if (bestUrl && bestUrl !== 'N/A' && bestUrl !== '') {{
                window.open(bestUrl, '_blank');
                console.log('打开最佳质量视频:', bestUrl);
            }} else {{
                alert('暂无可用的高清视频链接');
            }}
        }}
        
        // 添加一些交互提示
        document.addEventListener('DOMContentLoaded', function() {{
            const qualityLinks = document.querySelectorAll('.quality-link');
            
            // 为质量链接添加点击提示
            qualityLinks.forEach(function(link) {{
                link.addEventListener('click', function() {{
                    console.log('打开视频:', this.href);
                }});
            }});
        }});
        
        // 在线下载相关功能
        function openDownloadSite(siteUrl) {{
            const m3u8Url = document.getElementById('best-m3u8-url').value;
            if (m3u8Url && m3u8Url !== 'N/A' && m3u8Url !== '') {{
                // 打开下载网站
                window.open(siteUrl, '_blank');
                
                // 自动复制链接到剪贴板
                copyToClipboard(m3u8Url);
                showNotification('视频链接已复制到剪贴板，请在下载网站中粘贴链接');
            }} else {{
                showNotification('没有找到视频链接', 'error');
            }}
        }}
        
        function copyCommand(elementId) {{
            const element = document.getElementById(elementId);
            const text = element.textContent;
            copyToClipboard(text);
            
            // 更改按钮状态
            const btn = element.nextElementSibling;
            btn.textContent = '已复制';
            btn.classList.add('copied');
            setTimeout(() => {{
                btn.textContent = '复制';
                btn.classList.remove('copied');
            }}, 2000);
        }}
        
        function copyUrl(elementId) {{
            const element = document.getElementById(elementId);
            const text = element.value;
            copyToClipboard(text);
            
            // 更改按钮状态
            const btn = element.nextElementSibling;
            btn.textContent = '已复制';
            btn.classList.add('copied');
            setTimeout(() => {{
                btn.textContent = '复制';
                btn.classList.remove('copied');
            }}, 2000);
        }}
        
        function copyToClipboard(text) {{
            if (navigator.clipboard && navigator.clipboard.writeText) {{
                navigator.clipboard.writeText(text).then(() => {{
                    console.log('复制成功');
                }}).catch(err => {{
                    console.error('复制失败:', err);
                    fallbackCopyTextToClipboard(text);
                }});
            }} else {{
                fallbackCopyTextToClipboard(text);
            }}
        }}
        
        function fallbackCopyTextToClipboard(text) {{
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.top = '0';
            textArea.style.left = '0';
            textArea.style.width = '2em';
            textArea.style.height = '2em';
            textArea.style.padding = '0';
            textArea.style.border = 'none';
            textArea.style.outline = 'none';
            textArea.style.boxShadow = 'none';
            textArea.style.background = 'transparent';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            
            try {{
                document.execCommand('copy');
                console.log('后备复制成功');
            }} catch (err) {{
                console.error('后备复制失败:', err);
            }}
            
            document.body.removeChild(textArea);
        }}
        
        function showNotification(message, type = 'info') {{
            // 创建通知元素
            const notification = document.createElement('div');
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 12px 20px;
                background: ${{type === 'error' ? '#dc3545' : '#28a745'}};
                color: white;
                border-radius: 5px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                z-index: 10000;
                max-width: 300px;
                font-size: 14px;
                opacity: 0;
                transform: translateX(100%);
                transition: all 0.3s ease;
            `;
            notification.textContent = message;
            
            document.body.appendChild(notification);
            
            // 显示动画
            setTimeout(() => {{
                notification.style.opacity = '1';
                notification.style.transform = 'translateX(0)';
            }}, 100);
            
            // 自动隐藏
            setTimeout(() => {{
                notification.style.opacity = '0';
                notification.style.transform = 'translateX(100%)';
                setTimeout(() => {{
                    if (notification.parentNode) {{
                        notification.parentNode.removeChild(notification);
                    }}
                }}, 300);
            }}, 3000);
        }}
    </script>
</body>
</html>
        """
        
        html_filepath = os.path.join(folder_path, OUTPUT_CONFIG['html_filename'])
        with open(html_filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return html_filepath
    
    def _generate_quality_links(self, m3u8_urls):
        """生成质量选择链接HTML"""
        if not m3u8_urls:
            return "<p class='no-link'>暂无其他质量可用</p>"
        
        links_html = ""
        quality_priority = ['1080P', '720P', '480P', '240P', 'HD', 'SD']
        
        for i, url in enumerate(m3u8_urls):
            # 尝试从URL中提取质量信息
            quality_name = f"质量 {i+1}"
            for priority in quality_priority:
                if priority in url:
                    quality_name = priority
                    break
            
            links_html += f'<a href="{url}" target="_blank" class="quality-link">{quality_name}</a>'
        
        return links_html
    
    def process_video(self, video_data):
        """处理单个视频 - 保存到数据库并创建文件"""
        if not video_data or not video_data.get('viewkey'):
            return False
        
        viewkey = video_data['viewkey']
        # 获取app.py所在的目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        folder_path = os.path.join(script_dir, OUTPUT_CONFIG['data_folder'], viewkey)
        
        # 检查是否已存在（优先检查本地文件，只有本地和数据库都存在才跳过）
        if SCRAPER_CONFIG.get('skip_existing', True):
            # 检查本地文件是否存在
            file_exists = self.is_video_completed(viewkey)
            
            if file_exists:
                # 本地文件存在，再检查数据库中是否也存在
                db_exists = self.db.video_exists(viewkey)
                
                if db_exists:
                    # 本地文件和数据库都存在，才跳过
                    if DEBUG['verbose']:
                        print(f"跳过已存在的视频 (本地+数据库): {video_data.get('title', 'N/A')} (ID: {viewkey})")
                    return True
                else:
                    # 本地文件存在但数据库不存在，不跳过，重新处理以补充数据库
                    if DEBUG['verbose']:
                        print(f"本地文件存在但数据库缺失，重新处理: {video_data.get('title', 'N/A')} (ID: {viewkey})")
            # 本地文件不存在，不跳过，继续处理
        
        if DEBUG['verbose']:
            print(f"处理视频: {video_data.get('title', 'N/A')} (ID: {viewkey})")
            print(f"文件夹: {folder_path}")
        
        # 创建文件夹
        os.makedirs(folder_path, exist_ok=True)
        
        try:
            # 1. 保存视频数据到数据库
            db_video_id = self.db.insert_video(video_data)
            
            # 启动下载工作线程（如果还没启动）
            if not hasattr(self, 'download_workers') or not self.download_workers:
                self.start_download_workers()
            
            # 2. 添加下载任务到队列
            download_tasks = []
            if video_data.get('thumbnail_url'):
                thumbnail_path = os.path.join(folder_path, OUTPUT_CONFIG['thumbnail_filename'])
                self.add_download_task(video_data['thumbnail_url'], thumbnail_path, "缩略图")
                download_tasks.append(("缩略图", thumbnail_path))
            
            if video_data.get('preview_url'):
                preview_path = os.path.join(folder_path, OUTPUT_CONFIG['preview_filename'])
                self.add_download_task(video_data['preview_url'], preview_path, "预览视频")
                download_tasks.append(("预览视频", preview_path))
            
            # 3. 创建HTML页面
            html_path = self.create_html_page(video_data, folder_path)
            if DEBUG['verbose']:
                print(f"HTML页面创建成功: {html_path}")
            
            # 4. 创建采集日志
            self.create_collection_log(video_data, folder_path, success=True)
            
            if DEBUG['verbose']:
                print(f"✓ 视频数据已保存到数据库 (DB ID: {db_video_id})")
            
            return True
            
        except Exception as e:
            error_msg = f"处理视频时出错: {e}"
            print(f"❌ {error_msg}")
            self.create_collection_log(video_data, folder_path, success=False, error_msg=error_msg)
            if DEBUG['verbose']:
                import traceback
                traceback.print_exc()
            return False
    
    def update_collection_logs(self, videos, download_results):
        """更新所有视频的采集日志"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
            for video_data in videos:
                if not video_data or not video_data.get('viewkey'):
                    continue
                
                viewkey = video_data['viewkey']
                folder_path = os.path.join(script_dir, OUTPUT_CONFIG['data_folder'], viewkey)
                
                # 检查该视频是否有下载任务
                has_downloads = False
                download_success = True
                
                # 检查缩略图下载
                if video_data.get('thumbnail_url'):
                    thumbnail_path = os.path.join(folder_path, OUTPUT_CONFIG['thumbnail_filename'])
                    if thumbnail_path in download_results:
                        has_downloads = True
                        if not download_results[thumbnail_path]:
                            download_success = False
                
                # 检查预览视频下载
                if video_data.get('preview_url'):
                    preview_path = os.path.join(folder_path, OUTPUT_CONFIG['preview_filename'])
                    if preview_path in download_results:
                        has_downloads = True
                        if not download_results[preview_path]:
                            download_success = False
                
                # 更新日志
                if has_downloads:
                    if download_success:
                        self.create_collection_log(video_data, folder_path, success=True)
                    else:
                        self.create_collection_log(video_data, folder_path, success=False, error_msg="部分文件下载失败")
                else:
                    # 没有下载任务，只创建HTML页面
                    self.create_collection_log(video_data, folder_path, success=True)
                    
        except Exception as e:
            print(f"更新采集日志时出错: {e}")
    
    def scrape_pages(self, start_page=1, end_page=None, auto_detect_last=True):
        """抓取指定页数的视频数据"""
        all_videos = []
        current_page = start_page
        
        # 获取第1页来确定总页数
        if auto_detect_last and end_page is None:
            print("获取第1页信息以确定总页数...")
            first_page_url = f"{self.base_url}?page=1"
            first_page_content = self.get_page(first_page_url)
            
            if first_page_content:
                total_pages = self.get_total_pages(first_page_content)
                if total_pages:
                    end_page = total_pages
                    print(f"检测到总页数: {total_pages}")
                else:
                    print("无法检测总页数，使用默认设置")
                    end_page = SCRAPER_CONFIG.get('end_page', 5)
            else:
                print("第1页获取失败，使用默认设置")
                end_page = SCRAPER_CONFIG.get('end_page', 5)
        
        print(f"开始抓取页面: {start_page} - {end_page}")
        
        while current_page <= end_page:
            if DEBUG['verbose']:
                print(f"\n正在抓取第 {current_page} 页...")
            url = f"{self.base_url}?page={current_page}"
            
            html_content = self.get_page(url)
            if not html_content:
                print(f"第 {current_page} 页获取失败，跳过")
                current_page += 1
                continue
            
            videos = self.parse_video_list(html_content)
            if DEBUG['verbose']:
                print(f"第 {current_page} 页找到 {len(videos)} 个视频")
            all_videos.extend(videos)
            
            # 检查是否为最后一页
            if auto_detect_last and self.check_is_last_page(html_content):
                if DEBUG['verbose']:
                    print(f"检测到第 {current_page} 页为最后一页，停止抓取")
                break
            
            # 添加随机延迟，避免被封
            time.sleep(random.uniform(SCRAPER_CONFIG['delay_min'], SCRAPER_CONFIG['delay_max']))
            current_page += 1
        
        if DEBUG['verbose']:
            print(f"\n总共找到 {len(all_videos)} 个视频")
        return all_videos
    
    def scrape_and_download_pages(self, start_page=1, end_page=None, auto_detect_last=True):
        """边解析边下载页面"""
        all_videos = []
        current_page = start_page
        success_count = 0
        
        # 获取第1页来确定总页数
        if auto_detect_last and end_page is None:
            if DEBUG['verbose']:
                print("获取第1页信息以确定总页数...")
            first_page_url = f"{self.base_url}?page=1"
            first_page_content = self.get_page(first_page_url)
            
            if first_page_content:
                total_pages = self.get_total_pages(first_page_content)
                if total_pages:
                    end_page = total_pages
                    if DEBUG['verbose']:
                        print(f"检测到总页数: {total_pages}")
                else:
                    if DEBUG['verbose']:
                        print("无法检测总页数，使用默认设置")
                    end_page = SCRAPER_CONFIG.get('end_page', 5)
            else:
                if DEBUG['verbose']:
                    print("第1页获取失败，使用默认设置")
                end_page = SCRAPER_CONFIG.get('end_page', 5)
        
        if DEBUG['verbose']:
            print(f"开始抓取页面: {start_page} - {end_page}")
        
        while current_page <= end_page:
            if DEBUG['verbose']:
                print(f"\n正在抓取第 {current_page} 页...")
            url = f"{self.base_url}?page={current_page}"
            
            html_content = self.get_page(url)
            if not html_content:
                print(f"第 {current_page} 页获取失败，跳过")
                current_page += 1
                continue
            
            # 解析当前页面的视频
            videos = self.parse_video_list(html_content)
            if DEBUG['verbose']:
                print(f"第 {current_page} 页找到 {len(videos)} 个视频")
            
            # 立即处理当前页面的视频
            for i, video_data in enumerate(videos, 1):
                if DEBUG['verbose']:
                    print(f"处理第 {current_page} 页第 {i}/{len(videos)} 个视频...")
                if self.process_video(video_data):
                    success_count += 1
                    all_videos.append(video_data)
            
            # 检查是否为最后一页
            if auto_detect_last and self.check_is_last_page(html_content):
                if DEBUG['verbose']:
                    print(f"检测到第 {current_page} 页为最后一页，停止抓取")
                break
            
            # 添加随机延迟，避免被封
            time.sleep(random.uniform(SCRAPER_CONFIG['delay_min'], SCRAPER_CONFIG['delay_max']))
            current_page += 1
        
        if DEBUG['verbose']:
            print(f"\n总共找到 {len(all_videos)} 个视频")
        
        return success_count
    
    def update_collection_logs_from_results(self, download_results):
        """根据下载结果更新采集日志"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
            # 从下载结果中提取视频信息
            processed_videos = []
            for filepath in download_results.keys():
                # 从文件路径提取viewkey
                folder_name = os.path.basename(os.path.dirname(filepath))
                if folder_name and folder_name != 'data':
                    # 这里需要从其他地方获取视频数据，暂时跳过
                    continue
            
            # 由于边解析边下载，日志更新会在process_video中完成
            if DEBUG['verbose']:
                print("采集日志已在处理过程中更新")
                    
        except Exception as e:
            print(f"更新采集日志时出错: {e}")
    
    def run(self, start_page=None, end_page=None, auto_detect_last=None):
        """运行抓取程序"""
        if start_page is None:
            start_page = SCRAPER_CONFIG['start_page']
        if auto_detect_last is None:
            auto_detect_last = SCRAPER_CONFIG.get('auto_detect_last', True)
        
        print("开始抓取Pornhub视频数据...")
        print(f"使用代理: {PROXY_CONFIG['http']}")
        print(f"起始页数: {start_page}")
        if end_page and not auto_detect_last:
            print(f"结束页数: {end_page}")
        else:
            print("结束页数: 自动检测")
        print(f"自动检测最后一页: {'是' if auto_detect_last else '否'}")
        print(f"下载线程数: {SCRAPER_CONFIG.get('download_threads', 10)}")
        
        # 启动下载工作线程
        self.start_download_workers()
        
        # 创建data文件夹（在app.py所在目录）
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_folder = os.path.join(script_dir, OUTPUT_CONFIG['data_folder'])
        os.makedirs(data_folder, exist_ok=True)
        
        if DEBUG['verbose']:
            print(f"数据保存目录: {data_folder}")
        
        try:
            # 启动边解析边下载
            success_count = self.scrape_and_download_pages(start_page, end_page, auto_detect_last)
            
            # 等待所有下载完成
            if DEBUG['verbose']:
                print(f"\n等待所有下载任务完成...")
            download_results = self.wait_for_downloads()
            
            # 统计下载结果
            total_downloads = len(download_results)
            successful_downloads = sum(1 for success in download_results.values() if success)
            if total_downloads > 0:
                print(f"下载完成: {successful_downloads}/{total_downloads} 个文件")
            
            # 更新所有视频的采集日志
            self.update_collection_logs_from_results(download_results)
            
            print(f"\n抓取完成！成功处理 {success_count} 个视频")
            script_dir = os.path.dirname(os.path.abspath(__file__))
            data_folder = os.path.join(script_dir, OUTPUT_CONFIG['data_folder'])
            if DEBUG['verbose']:
                print(f"数据保存在 {data_folder} 文件夹中")
            
        finally:
            # 停止下载工作线程
            self.stop_download_workers()
            
            # 关闭WebDriver
            self.close_driver()

    def check_page_type(self, page_source):
        """检查页面类型"""
        try:
            # 检查是否为地区限制页面
            region_restriction_indicators = [
                "Virginia",
                "elected officials",
                "verify your age",
                "ID card",
                "device-based verification",
                "completely disable access",
                "contact your representatives"
            ]
            
            # 检查是否为年龄验证页面 - 通过检查模态框是否存在来判断
            try:
                # 尝试查找年龄验证模态框
                modal = self.driver.find_element(By.ID, "js-ageDisclaimerModal")
                if modal.is_displayed():
                    print("✓ 检测到年龄验证模态框可见")
                    return "age_verification"
                else:
                    print("✓ 年龄验证模态框存在但不可见，可能已验证")
                    # 如果模态框存在但不可见，说明年龄验证已完成，返回正常内容
                    return "normal_content"
            except:
                # 如果找不到模态框，检查页面源码中的年龄验证指示器
                age_verification_indicators = [
                    "我年满 18 岁",
                    "这是个成人网站",
                    "ageDisclaimer",
                    "modalWrapMTubes",
                    "gtm-event-age-verification"
                ]
                
                for indicator in age_verification_indicators:
                    if indicator in page_source:
                        print(f"✓ 检测到年龄验证页面: {indicator}")
                        return "age_verification"
            
            # 检查是否为正常内容页面
            normal_content_indicators = [
                "videoCategory",
                "pcVideoListItem",
                "Pornhub",
                "视频"
            ]
            
            page_source_lower = page_source.lower()
            
            # 检查地区限制
            for indicator in region_restriction_indicators:
                if indicator.lower() in page_source_lower:
                    print(f"⚠️  检测到地区限制页面: {indicator}")
                    return "region_restricted"
            
            # 检查正常内容
            for indicator in normal_content_indicators:
                if indicator in page_source:
                    print(f"✓ 检测到正常内容页面: {indicator}")
                    return "normal_content"
            
            print("⚠️  未知页面类型")
            return "unknown"
            
        except Exception as e:
            print(f"页面类型检测出错: {e}")
            return "unknown"
    
    def handle_region_restriction(self):
        """处理地区限制"""
        try:
            print("检测到地区限制，尝试绕过...")
            
            # 尝试使用不同的User-Agent
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ]
            
            for i, user_agent in enumerate(user_agents, 1):
                try:
                    print(f"尝试User-Agent {i}: {user_agent[:50]}...")
                    
                    # 更新User-Agent
                    self.driver.execute_script(f"Object.defineProperty(navigator, 'userAgent', {{get: () => '{user_agent}'}})")
                    
                    # 刷新页面
                    self.driver.refresh()
                    time.sleep(3)
                    
                    # 检查页面类型
                    page_source = self.driver.page_source
                    page_type = self.check_page_type(page_source)
                    
                    if page_type == "age_verification":
                        print("✓ 成功绕过地区限制，进入年龄验证页面")
                        return True
                    elif page_type == "normal_content":
                        print("✓ 成功绕过地区限制，直接进入正常页面")
                        return True
                    else:
                        print(f"User-Agent {i} 未能绕过地区限制")
                        
                except Exception as e:
                    print(f"User-Agent {i} 尝试失败: {e}")
                    continue
            
            print("✗ 所有User-Agent都无法绕过地区限制")
            return False
            
        except Exception as e:
            print(f"处理地区限制时出错: {e}")
            return False
    
    def fast_scrape_all_pages(self, start_page=1):
        """快速轮询所有页面直到分页结束"""
        print("开始快速轮询所有页面...")
        
        all_video_urls = []
        current_page = start_page
        max_pages = 100  # 最大页数限制，防止无限循环
        is_first_page = True  # 标记是否为第一个页面
        
        while current_page <= max_pages:
            try:
                print(f"正在快速获取第 {current_page} 页...")
                
                # 构建页面URL
                page_url = f"{self.base_url}?page={current_page}"
                
                # 快速获取页面内容（带超时控制）
                page_source = self.get_page_with_timeout_control(page_url, is_first_page)
                
                if not page_source:
                    print(f"第 {current_page} 页获取失败，跳过此页")
                    current_page += 1
                    continue
                
                # 快速解析视频链接（不获取详细信息）
                video_urls = self.fast_parse_video_urls(page_source)
                
                if not video_urls:
                    print(f"第 {current_page} 页没有找到视频链接，可能已到最后一页")
                    break
                
                print(f"第 {current_page} 页找到 {len(video_urls)} 个视频链接")
                all_video_urls.extend(video_urls)
                
                # 检查是否为最后一页
                if self.check_is_last_page(page_source):
                    print(f"检测到第 {current_page} 页为最后一页")
                    break
                
                current_page += 1
                is_first_page = False  # 第一个页面处理完毕
                
                # 短暂延迟，避免请求过快
                time.sleep(0.5)
                
            except Exception as e:
                print(f"处理第 {current_page} 页时出错: {e}")
                current_page += 1
                continue
        
        print(f"轮询完成，总共找到 {len(all_video_urls)} 个视频链接")
        return all_video_urls
    
    def fast_scrape_limited_pages(self, start_page=1, max_pages=5):
        """快速轮询指定数量的页面"""
        print(f"开始快速轮询 {max_pages} 个页面...")
        
        all_video_urls = []
        is_first_page = True
        
        for page_num in range(start_page, start_page + max_pages):
            try:
                print(f"正在快速获取第 {page_num} 页...")
                
                # 构建页面URL
                page_url = f"{self.base_url}?page={page_num}"
                
                # 快速获取页面内容（带超时控制）
                page_source = self.get_page_with_timeout_control(page_url, is_first_page)
                
                if not page_source:
                    print(f"第 {page_num} 页获取失败，跳过此页")
                    continue
                
                # 快速解析视频链接（不获取详细信息）
                video_urls = self.fast_parse_video_urls(page_source)
                
                if not video_urls:
                    print(f"第 {page_num} 页没有找到视频链接")
                    continue
                
                print(f"第 {page_num} 页找到 {len(video_urls)} 个视频链接")
                all_video_urls.extend(video_urls)
                
                is_first_page = False
                
                # 短暂延迟，避免请求过快
                time.sleep(0.5)
                
            except Exception as e:
                print(f"处理第 {page_num} 页时出错: {e}")
                continue
        
        print(f"限制轮询完成，总共找到 {len(all_video_urls)} 个视频链接")
        return all_video_urls
    
    def get_page_with_timeout_control(self, url, is_first_page=False):
        """带超时控制的分页获取"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                if DEBUG['verbose']:
                    print(f"访问页面: {url} (尝试 {attempt + 1}/{max_retries})")
                
                # 访问页面，最多等待5秒
                self.driver.set_page_load_timeout(5)
                self.driver.get(url)
                
                # 等待页面基本加载
                time.sleep(1)
                
                # 检查页面是否已经打开
                page_source = self.driver.page_source
                if page_source and len(page_source) > 1000:
                    print("✓ 页面已成功打开")
                    
                    # 只有第一个页面需要验证18岁
                    if is_first_page:
                        print("检测到第一个页面，进行年龄验证...")
                        if not SELENIUM_CONFIG.get('fast_mode', False):
                            age_verification_result = self.handle_age_verification()
                            if age_verification_result:
                                print("✓ 年龄验证成功")
                                # 重新获取页面源码
                                page_source = self.driver.page_source
                            else:
                                print("⚠️  年龄验证失败")
                    
                    return page_source
                else:
                    print(f"页面内容无效，长度: {len(page_source) if page_source else 0}")
                    
                    if attempt == 0:
                        # 第一次尝试失败，刷新页面等待10秒
                        print("刷新页面，等待10秒...")
                        self.driver.refresh()
                        time.sleep(10)
                    elif attempt == 1:
                        # 第二次尝试失败，等待15秒
                        print("等待15秒...")
                        time.sleep(15)
                    else:
                        # 第三次尝试失败，放弃此页
                        print("页面加载失败，放弃此页")
                        return None
                    
                    continue
                    
            except TimeoutException as e:
                print(f"页面加载超时 (尝试 {attempt + 1}/{max_retries}): {e}")
                
                if attempt == 0:
                    # 第一次超时，刷新页面等待10秒
                    print("页面超时，刷新页面等待10秒...")
                    try:
                        self.driver.refresh()
                        time.sleep(10)
                    except:
                        pass
                elif attempt == 1:
                    # 第二次超时，等待15秒
                    print("页面超时，等待15秒...")
                    time.sleep(15)
                else:
                    # 第三次超时，放弃此页
                    print("页面多次超时，放弃此页")
                    return None
                continue
                
            except WebDriverException as e:
                print(f"WebDriver错误 (尝试 {attempt + 1}/{max_retries}): {e}")
                
                if attempt == 0:
                    # 第一次错误，刷新页面等待10秒
                    print("WebDriver错误，刷新页面等待10秒...")
                    try:
                        self.driver.refresh()
                        time.sleep(10)
                    except:
                        pass
                elif attempt == 1:
                    # 第二次错误，等待15秒
                    print("WebDriver错误，等待15秒...")
                    time.sleep(15)
                else:
                    # 第三次错误，放弃此页
                    print("WebDriver多次错误，放弃此页")
                    return None
                continue
                
            except Exception as e:
                print(f"获取页面失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                
                if attempt == 0:
                    # 第一次错误，刷新页面等待10秒
                    print("获取页面失败，刷新页面等待10秒...")
                    try:
                        self.driver.refresh()
                        time.sleep(10)
                    except:
                        pass
                elif attempt == 1:
                    # 第二次错误，等待15秒
                    print("获取页面失败，等待15秒...")
                    time.sleep(15)
                else:
                    # 第三次错误，放弃此页
                    print("获取页面多次失败，放弃此页")
                    return None
                continue
        
        print(f"所有重试都失败了: {url}")
        return None
    
    def fast_parse_video_urls(self, html_content):
        """快速解析视频链接（不获取详细信息）"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            video_list = soup.find('ul', {'id': 'videoCategory'})
            
            if not video_list:
                return []
            
            video_urls = []
            for li in video_list.find_all('li', class_='pcVideoListItem'):
                try:
                    # 获取视频链接
                    link_element = li.find('a', class_='linkVideoThumb')
                    if link_element:
                        video_url = urljoin(self.base_url, link_element.get('href', ''))
                        if video_url:
                            video_urls.append(video_url)
                except Exception as e:
                    continue
            
            return video_urls
            
        except Exception as e:
            print(f"快速解析视频链接失败: {e}")
            return []
    
    def analyze_video_urls_parallel(self, video_urls, max_workers=10, use_requests=True):
        """多线程分析视频URL，获取详细页面地址数据"""
        print(f"开始多线程分析 {len(video_urls)} 个视频URL...")
        
        if use_requests:
            # 使用requests方式（推荐）
            return self.analyze_video_urls_with_requests(video_urls, max_workers)
        else:
            # 使用Selenium多标签页方式
            return self.analyze_video_urls_with_selenium_tabs(video_urls, max_workers)
    
    def extract_video_metadata(self, soup, video_url):
        """提取视频元数据（时长、上传者、观看次数、发布时间等）"""
        import re
        
        video_data = {
            'video_id': '',
            'viewkey': '',
            'title': '',
            'video_url': video_url,
            'duration': '',
            'uploader': '',
            'views': '',
            'publish_time': '',
            'categories': [],
            'thumbnail_url': '',
            'preview_url': '',
            'best_m3u8_url': '',
            'm3u8_urls': []
        }
        
        # 从URL提取viewkey
        viewkey_match = re.search(r'viewkey=([^&]+)', video_url)
        if viewkey_match:
            video_data['viewkey'] = viewkey_match.group(1)
            video_data['video_id'] = viewkey_match.group(1)
        
        # 提取标题
        title_element = soup.find('title')
        if title_element:
            video_data['title'] = title_element.get_text(strip=True)
            # 清理标题
            for suffix in [' - Pornhub.com', ' - PornHub', ' | Pornhub']:
                video_data['title'] = video_data['title'].replace(suffix, '')
        
        # 提取时长 - 尝试多种选择器
        duration_element = (soup.find('span', class_='duration') or 
                          soup.find('span', {'class': 'runtime'}) or 
                          soup.find('span', {'data-role': 'duration'}) or
                          soup.find('div', class_='duration'))
        if duration_element:
            video_data['duration'] = duration_element.get_text(strip=True)
        else:
            # 从脚本中提取时长
            duration_match = re.search(r'"duration"[:\s]*"([^"]+)"', str(soup))
            if not duration_match:
                duration_match = re.search(r'"runtime"[:\s]*"([^"]+)"', str(soup))
            if duration_match:
                video_data['duration'] = duration_match.group(1)
        
        # 提取上传者 - 尝试多种选择器
        uploader_element = (soup.find('a', class_='username') or 
                          soup.find('a', class_='usernameLink') or 
                          soup.find('span', class_='username') or
                          soup.find('div', class_='usernameBadgesWrapper') or
                          soup.find('a', {'data-qa': 'user-name'}))
        if uploader_element:
            video_data['uploader'] = uploader_element.get_text(strip=True)
        else:
            # 从脚本中提取上传者
            uploader_match = re.search(r'"uploader"[:\s]*"([^"]+)"', str(soup))
            if not uploader_match:
                uploader_match = re.search(r'"author"[:\s]*"([^"]+)"', str(soup))
            if uploader_match:
                video_data['uploader'] = uploader_match.group(1)
        
        # 提取观看次数 - 尝试多种选择器
        views_element = (soup.find('span', class_='views') or 
                       soup.find('span', class_='count') or
                       soup.find('div', class_='views') or
                       soup.find('span', {'data-qa': 'view-count'}))
        if views_element:
            video_data['views'] = views_element.get_text(strip=True)
        else:
            # 从脚本中提取观看次数
            views_match = re.search(r'"views"[:\s]*"([^"]+)"', str(soup))
            if not views_match:
                views_match = re.search(r'"viewCount"[:\s]*(\d+)', str(soup))
            if views_match:
                video_data['views'] = views_match.group(1)
        
        # 提取发布时间 - 尝试多种选择器
        publish_element = (soup.find('span', class_='publishDate') or 
                         soup.find('time') or
                         soup.find('span', class_='added') or
                         soup.find('div', class_='date'))
        if publish_element:
            video_data['publish_time'] = publish_element.get_text(strip=True)
        else:
            # 从脚本中提取发布时间
            publish_match = re.search(r'"publishDate"[:\s]*"([^"]+)"', str(soup))
            if not publish_match:
                publish_match = re.search(r'"datePublished"[:\s]*"([^"]+)"', str(soup))
            if publish_match:
                video_data['publish_time'] = publish_match.group(1)
        
        return video_data

    def analyze_video_urls_with_requests(self, video_urls, max_workers=10):
        """使用requests多线程分析视频URL"""
        print("使用requests方式分析视频URL...")
        
        # 创建线程池
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_url = {executor.submit(self.analyze_single_video_url_with_requests, url): url for url in video_urls}
            
            # 收集结果
            analyzed_data = []
            completed = 0
            
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    if result:
                        analyzed_data.append(result)
                    completed += 1
                    
                    if completed % 10 == 0:
                        print(f"已分析 {completed}/{len(video_urls)} 个视频URL")
                        
                except Exception as e:
                    print(f"分析视频URL失败 {url}: {e}")
                    completed += 1
        
        print(f"分析完成，成功分析 {len(analyzed_data)} 个视频")
        return analyzed_data
    
    def analyze_single_video_url_with_requests(self, video_url):
        """使用requests分析单个视频URL，同时进行下载"""
        try:
            # 使用requests获取视频页面内容
            page_source = self.get_page_requests(video_url)
            
            if not page_source:
                return None
            
            # 解析视频详细信息
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # 使用改进的提取函数获取基本信息
            video_data = self.extract_video_metadata(soup, video_url)
            
            # 保持原有字段名的兼容性
            video_data['url'] = video_url
            video_data['alt_text'] = ''
            
            # 提取缩略图和预览视频 - 使用改进的方法
            thumbnail_url, preview_url = self.extract_thumbnail_and_preview_urls(soup)
            video_data['thumbnail_url'] = thumbnail_url
            video_data['preview_url'] = preview_url
            
            # 提取分类
            categories = []
            category_elements = soup.find_all('a', class_='category')
            for cat in category_elements:
                categories.append({
                    'name': cat.get_text(strip=True),
                    'url': cat.get('href', '')
                })
            video_data['categories'] = categories
            
            # 提取m3u8地址
            m3u8_urls = []
            scripts = soup.find_all('script')
            for script in scripts:
                script_content = script.string
                if script_content:
                    m3u8_patterns = [
                        r'https?://[^"\']*\.m3u8[^"\']*',
                        r'"videoUrl":"([^"]*\.m3u8[^"]*)"',
                        r"'videoUrl':'([^']*\.m3u8[^']*)'",
                    ]
                    
                    for pattern in m3u8_patterns:
                        matches = re.findall(pattern, script_content, re.IGNORECASE)
                        for match in matches:
                            if isinstance(match, tuple):
                                match = match[0]
                            if match and match not in m3u8_urls:
                                clean_url = match.replace('\\/', '/')
                                m3u8_urls.append(clean_url)
            
            video_data['m3u8_urls'] = m3u8_urls
            
            # 选择最佳m3u8地址
            if m3u8_urls:
                priority_order = ['1080P', '720P', '480P', '240P']
                for priority in priority_order:
                    for url in m3u8_urls:
                        if priority in url:
                            video_data['best_m3u8_url'] = url
                            break
                    if video_data['best_m3u8_url']:
                        break
                
                if not video_data['best_m3u8_url'] and m3u8_urls:
                    video_data['best_m3u8_url'] = m3u8_urls[0]
            
            # 保存到数据库
            if video_data.get('viewkey'):
                self.process_video(video_data)
            
            return video_data
            
        except Exception as e:
            print(f"分析视频URL失败 {video_url}: {e}")
            return None
    
    def download_video_data_immediately(self, video_data):
        """立即下载视频数据（优化版：使用异步下载队列）"""
        try:
            viewkey = video_data.get('viewkey', 'unknown')
            script_dir = os.path.dirname(os.path.abspath(__file__))
            folder_path = os.path.join(script_dir, OUTPUT_CONFIG['data_folder'], viewkey)
            os.makedirs(folder_path, exist_ok=True)
            
            # 检查是否已完成（跳过重复处理）
            if SCRAPER_CONFIG.get('skip_existing', True) and self.is_video_completed(viewkey):
                if DEBUG['verbose']:
                    print(f"跳过已完成的视频: {viewkey}")
                return
            
            # 创建HTML页面
            html_path = self.create_html_page(video_data, folder_path)
            if DEBUG['verbose']:
                print(f"✓ HTML页面创建: {viewkey}")
            
            # 启动下载工作线程（如果还没启动）
            if not hasattr(self, 'download_workers') or not self.download_workers:
                self.start_download_workers()
            
            # 添加下载任务到队列（异步下载）
            if video_data.get('thumbnail_url'):
                thumbnail_path = os.path.join(folder_path, OUTPUT_CONFIG['thumbnail_filename'])
                self.add_download_task(video_data['thumbnail_url'], thumbnail_path, "缩略图")
            
            if video_data.get('preview_url'):
                preview_path = os.path.join(folder_path, OUTPUT_CONFIG['preview_filename'])
                self.add_download_task(video_data['preview_url'], preview_path, "预览视频")
            
            # 创建采集日志
            self.create_collection_log(video_data, folder_path, success=True)
            
        except Exception as e:
            print(f"处理视频数据失败 {video_data.get('viewkey', 'unknown')}: {e}")
            # 创建失败日志
            try:
                self.create_collection_log(video_data, folder_path, success=False, error_msg=str(e))
            except:
                pass
    
    def analyze_single_video_url_with_tab(self, video_url):
        """使用新标签页分析单个视频URL"""
        try:
            # 检查driver是否有效
            if not self.driver:
                print(f"Driver无效，跳过: {video_url}")
                return None
            
            # 检查当前标签页数量
            try:
                handles = self.driver.window_handles
                if len(handles) == 0:
                    print(f"没有可用的标签页，跳过: {video_url}")
                    return None
            except Exception as e:
                print(f"获取标签页句柄失败: {e}")
                return None
            
            # 打开新标签页
            try:
                self.driver.execute_script("window.open('');")
                time.sleep(0.5)  # 等待标签页打开
            except Exception as e:
                print(f"打开新标签页失败: {e}")
                return None
            
            # 切换到新标签页
            try:
                new_handles = self.driver.window_handles
                if len(new_handles) > len(handles):
                    self.driver.switch_to.window(new_handles[-1])
                else:
                    print(f"新标签页打开失败，跳过: {video_url}")
                    return None
            except Exception as e:
                print(f"切换到新标签页失败: {e}")
                return None
            
            # 访问视频页面
            try:
                self.driver.get(video_url)
                time.sleep(2)
            except Exception as e:
                print(f"访问页面失败 {video_url}: {e}")
                # 关闭当前标签页并返回
                try:
                    if len(self.driver.window_handles) > 1:
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])
                except:
                    pass
                return None
            
            # 获取页面源码
            try:
                page_source = self.driver.page_source
                if not page_source or len(page_source) < 1000:
                    print(f"页面内容无效 {video_url}")
                    # 关闭当前标签页并返回
                    try:
                        if len(self.driver.window_handles) > 1:
                            self.driver.close()
                            self.driver.switch_to.window(self.driver.window_handles[0])
                    except:
                        pass
                    return None
            except Exception as e:
                print(f"获取页面源码失败 {video_url}: {e}")
                # 关闭当前标签页并返回
                try:
                    if len(self.driver.window_handles) > 1:
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])
                except:
                    pass
                return None
            
            # 解析视频详细信息
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # 使用改进的提取函数获取基本信息
            video_data = self.extract_video_metadata(soup, video_url)
            
            # 保持原有字段名的兼容性
            video_data['url'] = video_url
            
            # 提取缩略图和预览视频 - 使用改进的方法
            thumbnail_url, preview_url = self.extract_thumbnail_and_preview_urls(soup)
            video_data['thumbnail_url'] = thumbnail_url
            video_data['preview_url'] = preview_url
            
            # 提取分类
            categories = []
            category_elements = soup.find_all('a', class_='category')
            for cat in category_elements:
                categories.append({
                    'name': cat.get_text(strip=True),
                    'url': cat.get('href', '')
                })
            video_data['categories'] = categories
            
            # 提取m3u8地址
            m3u8_urls = []
            scripts = soup.find_all('script')
            for script in scripts:
                script_content = script.string
                if script_content:
                    m3u8_patterns = [
                        r'https?://[^"\']*\.m3u8[^"\']*',
                        r'"videoUrl":"([^"]*\.m3u8[^"]*)"',
                        r"'videoUrl':'([^']*\.m3u8[^']*)'",
                    ]
                    
                    for pattern in m3u8_patterns:
                        matches = re.findall(pattern, script_content, re.IGNORECASE)
                        for match in matches:
                            if isinstance(match, tuple):
                                match = match[0]
                            if match and match not in m3u8_urls:
                                clean_url = match.replace('\\/', '/')
                                m3u8_urls.append(clean_url)
            
            video_data['m3u8_urls'] = m3u8_urls
            
            # 选择最佳m3u8地址
            if m3u8_urls:
                priority_order = ['1080P', '720P', '480P', '240P']
                for priority in priority_order:
                    for url in m3u8_urls:
                        if priority in url:
                            video_data['best_m3u8_url'] = url
                            break
                    if video_data['best_m3u8_url']:
                        break
                
                if not video_data['best_m3u8_url'] and m3u8_urls:
                    video_data['best_m3u8_url'] = m3u8_urls[0]
            
            # 保存到数据库
            if video_data.get('viewkey'):
                self.process_video(video_data)
            
            # 关闭当前标签页（但保留至少一个标签页）
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
            except Exception as e:
                print(f"关闭标签页失败: {e}")
                # 尝试重新初始化driver
                try:
                    if len(self.driver.window_handles) > 0:
                        self.driver.switch_to.window(self.driver.window_handles[0])
                except:
                    pass
            
            return video_data
            
        except Exception as e:
            print(f"分析视频URL失败 {video_url}: {e}")
            # 确保关闭标签页并切换回主标签页（但保留至少一个标签页）
            try:
                if self.driver and len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
            return None
    
    def analyze_video_urls_with_selenium_tabs(self, video_urls, max_workers=5):
        """使用Selenium多标签页方式分析视频URL"""
        print("使用Selenium多标签页方式分析视频URL...")
        
        # 限制线程数，避免打开过多标签页
        max_workers = min(max_workers, 3)  # 进一步减少线程数
        
        # 确保主标签页存在（用于年龄验证）
        try:
            if len(self.driver.window_handles) == 0:
                print("错误：没有可用的标签页")
                return []
            
            # 记录主标签页
            main_handle = self.driver.window_handles[0]
        except Exception as e:
            print(f"检查标签页失败: {e}")
            return []
        
        # 创建线程池
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_url = {executor.submit(self.analyze_single_video_url_with_tab, url): url for url in video_urls}
            
            # 收集结果
            analyzed_data = []
            completed = 0
            failed_count = 0
            
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    if result:
                        analyzed_data.append(result)
                    else:
                        failed_count += 1
                    completed += 1
                    
                    if completed % 10 == 0:
                        print(f"已分析 {completed}/{len(video_urls)} 个视频URL (失败: {failed_count})")
                        
                except Exception as e:
                    print(f"分析视频URL失败 {url}: {e}")
                    failed_count += 1
                    completed += 1
                    
                    # 如果失败率过高，考虑降低线程数
                    if failed_count > completed * 0.5 and completed > 20:
                        print("失败率过高，建议降低线程数或切换到requests方式")
        
        # 确保最终回到主标签页
        try:
            if main_handle in self.driver.window_handles:
                self.driver.switch_to.window(main_handle)
            elif len(self.driver.window_handles) > 0:
                self.driver.switch_to.window(self.driver.window_handles[0])
        except Exception as e:
            print(f"切换回主标签页失败: {e}")
        
        print(f"分析完成，成功分析 {len(analyzed_data)} 个视频，失败 {failed_count} 个")
        
        # 如果失败率过高，自动切换到requests方式
        if failed_count > len(video_urls) * 0.3 and len(analyzed_data) < len(video_urls) * 0.5:
            print("Selenium方式失败率过高，自动切换到requests方式...")
            remaining_urls = [url for url in video_urls if not any(data.get('url') == url for data in analyzed_data)]
            if remaining_urls:
                print(f"使用requests方式处理剩余的 {len(remaining_urls)} 个URL...")
                requests_data = self.analyze_video_urls_with_requests(remaining_urls, max_workers=5)
                analyzed_data.extend(requests_data)
                print(f"requests方式成功分析 {len(requests_data)} 个视频")
        
        return analyzed_data
    
    def download_video_data_parallel(self, analyzed_data, max_workers=20):
        """多线程下载视频数据"""
        print(f"开始多线程下载 {len(analyzed_data)} 个视频数据...")
        
        # 创建下载任务
        download_tasks = []
        for video_data in analyzed_data:
            if video_data.get('thumbnail_url'):
                download_tasks.append(('thumbnail', video_data['thumbnail_url'], video_data))
            if video_data.get('preview_url'):
                download_tasks.append(('preview', video_data['preview_url'], video_data))
        
        # 创建线程池
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有下载任务
            future_to_task = {executor.submit(self.download_single_file, task): task for task in download_tasks}
            
            # 收集结果
            download_results = {}
            completed = 0
            
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    if result:
                        download_results[result['filepath']] = result['success']
                    completed += 1
                    
                    if completed % 10 == 0:
                        print(f"已下载 {completed}/{len(download_tasks)} 个文件")
                        
                except Exception as e:
                    print(f"下载任务失败: {e}")
                    completed += 1
        
        print(f"下载完成，成功下载 {sum(1 for success in download_results.values() if success)}/{len(download_results)} 个文件")
        return download_results
    
    def download_single_file(self, task):
        """下载单个文件"""
        file_type, url, video_data = task
        
        try:
            # 创建文件夹
            viewkey = video_data.get('viewkey', 'unknown')
            script_dir = os.path.dirname(os.path.abspath(__file__))
            folder_path = os.path.join(script_dir, OUTPUT_CONFIG['data_folder'], viewkey)
            os.makedirs(folder_path, exist_ok=True)
            
            # 确定文件名
            if file_type == 'thumbnail':
                filename = OUTPUT_CONFIG['thumbnail_filename']
            elif file_type == 'preview':
                filename = OUTPUT_CONFIG['preview_filename']
            else:
                filename = f"{file_type}.mp4"
            
            filepath = os.path.join(folder_path, filename)
            
            # 下载文件
            success = self.download_file(url, filepath)
            
            # 创建HTML页面
            if success:
                self.create_html_page(video_data, folder_path)
            
            return {
                'filepath': filepath,
                'success': success,
                'url': url,
                'file_type': file_type
            }
            
        except Exception as e:
            print(f"下载文件失败 {url}: {e}")
            return {
                'filepath': '',
                'success': False,
                'url': url,
                'file_type': file_type
            }
    
    def optimized_run(self, start_page=1, use_requests_for_details=True, max_pages=None):
        """优化的运行流程（改进版）"""
        import time
        start_time = time.time()
        
        print("🚀 开始优化采集流程...")
        print(f"📊 配置: 起始页={start_page}, 使用{'requests' if use_requests_for_details else 'Selenium'}模式")
        
        try:
            # 阶段1: 快速轮询所有页面
            print("\n=== 🔍 阶段1: 快速轮询所有页面 ===")
            if max_pages:
                print(f"限制页数: {max_pages}")
                video_urls = self.fast_scrape_limited_pages(start_page, max_pages)
            else:
                video_urls = self.fast_scrape_all_pages(start_page)
            
            if not video_urls:
                print("❌ 未找到任何视频链接")
                return None
            
            print(f"✅ 第一阶段完成，找到 {len(video_urls)} 个视频链接")
            
            # 获取完视频地址列表后关闭Selenium（如果使用requests方式）
            if use_requests_for_details and self.driver:
                print("💾 视频地址列表获取完成，关闭Selenium以释放资源...")
                self.close_driver()
            
            # 阶段2: 多线程分析视频URL（同时进行下载）
            print("\n=== 📥 阶段2: 多线程分析视频URL（同时进行下载） ===")
            max_workers = DETAIL_PAGE_CONFIG.get('max_workers_requests' if use_requests_for_details else 'max_workers_selenium', 5)
            print(f"使用 {max_workers} 个工作线程")
            
            analyzed_data = self.analyze_video_urls_parallel(video_urls, max_workers=max_workers, use_requests=use_requests_for_details)
            
            if not analyzed_data:
                print("❌ 未成功分析任何视频数据")
                return None
            
            # 等待下载完成
            if hasattr(self, 'download_workers') and self.download_workers:
                print("\n⏳ 等待下载队列完成...")
                self.wait_for_downloads()
                self.stop_download_workers()
            
            # 统计结果
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"\n=== 🎉 采集完成 ===")
            print(f"⏱️  总耗时: {duration:.1f} 秒")
            print(f"🔗 总视频链接数: {len(video_urls)}")
            print(f"✅ 成功分析数: {len(analyzed_data)}")
            print(f"📈 成功率: {len(analyzed_data)/len(video_urls)*100:.1f}%")
            print(f"📁 数据已保存到数据库: {self.db.db_path}")
            
            # 显示数据库统计信息
            stats = self.db.get_statistics()
            print(f"📊 数据库统计: 总视频 {stats['total_videos']} 个，分类 {stats['total_categories']} 个")
            
            return {
                'video_urls': video_urls,
                'analyzed_data': analyzed_data,
                'success_count': len(analyzed_data),
                'total_count': len(video_urls),
                'duration': duration,
                'success_rate': len(analyzed_data)/len(video_urls)*100
            }
            
        except KeyboardInterrupt:
            print("\n\n⚠️ 用户中断采集")
            # 清理资源
            if hasattr(self, 'download_workers') and self.download_workers:
                self.stop_download_workers()
            return None
        except Exception as e:
            print(f"\n❌ 采集过程中出现错误: {e}")
            # 清理资源
            if hasattr(self, 'download_workers') and self.download_workers:
                self.stop_download_workers()
            return None

    def extract_thumbnail_and_preview_urls(self, soup):
        """
        改进的缩略图和预览视频URL提取方法
        """
        thumbnail_url = ''
        preview_url = ''
        
        # === 提取缩略图 ===
        # 方法1：查找带有poster属性的video标签
        video_with_poster = soup.find('video', attrs={'poster': True})
        if video_with_poster and video_with_poster.get('poster'):
            poster_url = video_with_poster.get('poster')
            # 过滤掉base64占位符
            if not poster_url.startswith('data:'):
                thumbnail_url = poster_url
                if DEBUG['verbose']:
                    print(f"✓ 找到video poster缩略图: {thumbnail_url}")
        
        # 方法2：查找特定的缩略图img标签
        if not thumbnail_url:
            # 尝试不同的缩略图选择器
            thumb_selectors = [
                'img[data-poster]',
                'img[data-thumb]',
                'img[data-mediumthumb]',
                'img.videoThumb',
                'img[class*="thumb"]',
                'img[src*="thumb"]'
            ]
            
            for selector in thumb_selectors:
                img_elements = soup.select(selector)
                for img in img_elements:
                    # 优先使用data属性
                    url = img.get('data-poster') or img.get('data-thumb') or img.get('data-mediumthumb') or img.get('src')
                    if url and ('thumb' in url.lower() or 'poster' in url.lower()):
                        thumbnail_url = url
                        if DEBUG['verbose']:
                            print(f"✓ 找到img标签缩略图: {thumbnail_url}")
                        break
                if thumbnail_url:
                    break
        
        # 方法3：从整个页面源码中提取缩略图URL
        if not thumbnail_url:
            # 直接在整个页面源码中搜索，不限于JavaScript
            page_content = str(soup)
            
            # 查找常见的缩略图URL模式
            thumb_patterns = [
                r'"image":\s*"([^"]*\.jpg[^"]*)"',
                r'"poster":\s*"([^"]*\.jpg[^"]*)"',
                r'"thumbnail":\s*"([^"]*\.jpg[^"]*)"',
                r'thumbUrl["\']:\s*["\']([^"\']*\.jpg[^"\']*)["\']',
                r'"defaultThumb":\s*"([^"]*\.jpg[^"]*)"',
                r'"thumb":\s*"([^"]*\.jpg[^"]*)"',
                r'"image_url":\s*"([^"]*\.jpg[^"]*)"',
                # 添加更多模式
                r'data-original="([^"]*\.jpg[^"]*)"',
                r'data-src="([^"]*\.jpg[^"]*)"',
                r'data-mediumthumb="([^"]*\.jpg[^"]*)"',
                r'data-thumb="([^"]*\.jpg[^"]*)"',
                # 查找Pornhub特定的缩略图模式
                r'https://[^"\']*phncdn\.com/[^"\']*\.jpg[^"\']*',
                r'https://[^"\']*pornhubpremium\.com/[^"\']*\.jpg[^"\']*',
                # 直接搜索完整的URL
                r'https://ei\.phncdn\.com/videos/[^"\']*\.jpg[^"\']*'
            ]
            
            for pattern in thumb_patterns:
                matches = re.findall(pattern, page_content, re.IGNORECASE)
                for match in matches:
                    clean_url = match.replace('\\/', '/')
                    # 更宽松的验证，不仅限于包含"thumb"的URL
                    if (clean_url and len(clean_url) > 20 and 
                        '.jpg' in clean_url.lower() and 
                        ('phncdn.com' in clean_url or 'pornhub' in clean_url or 'thumb' in clean_url.lower()) and
                        not clean_url.startswith('data:')):  # 排除base64编码的占位符
                        thumbnail_url = clean_url
                        if DEBUG['verbose']:
                            print(f"✓ 从页面找到缩略图: {thumbnail_url}")
                        break
                if thumbnail_url:
                    break
        
        # === 提取预览视频 ===
        # 方法1：查找video标签及其source子标签
        video_elements = soup.find_all('video')
        for video in video_elements:
            # 检查video标签的src属性
            src = video.get('src', '')
            if src and ('.webm' in src.lower() or '.mp4' in src.lower()) and 'preview' in src.lower():
                preview_url = src
                if DEBUG['verbose']:
                    print(f"✓ 找到video标签预览: {preview_url}")
                break
            
            # 检查source子标签
            sources = video.find_all('source')
            for source in sources:
                src = source.get('src', '')
                src_type = source.get('type', '').lower()
                if src and ('webm' in src_type or '.webm' in src.lower() or 'preview' in src.lower()):
                    preview_url = src
                    if DEBUG['verbose']:
                        print(f"✓ 找到source标签预览: {preview_url}")
                    break
            
            if preview_url:
                break
        
        # 方法2：从整个页面源码中提取预览视频URL
        if not preview_url:
            # 直接在整个页面源码中搜索，不限于JavaScript
            page_content = str(soup)
            
            # 查找常见的预览视频URL模式
            video_patterns = [
                r'"preview":\s*"([^"]*\.webm[^"]*)"',
                r'"videoPreview":\s*"([^"]*\.webm[^"]*)"',
                r'"previewUrl":\s*"([^"]*\.webm[^"]*)"',
                r'previewUrl["\']:\s*["\']([^"\']*\.webm[^"\']*)["\']',
                r'"preview":\s*"([^"]*\.mp4[^"]*)"',
                r'"preview_url":\s*"([^"]*\.webm[^"]*)"',
                # 添加更多模式
                r'data-mediabook="([^"]*\.webm[^"]*)"',
                r'data-preview="([^"]*\.webm[^"]*)"',
                r'data-video-preview="([^"]*\.webm[^"]*)"',
                # 查找Pornhub特定的预览视频模式
                r'https://[^"\']*phncdn\.com/[^"\']*\.webm[^"\']*',
                r'https://[^"\']*pornhubpremium\.com/[^"\']*\.webm[^"\']*',
                # 直接搜索完整的预览视频URL
                r'https://ew\.phncdn\.com/[^"\']*\.webm[^"\']*'
            ]
            
            for pattern in video_patterns:
                matches = re.findall(pattern, page_content, re.IGNORECASE)
                for match in matches:
                    clean_url = match.replace('\\/', '/')
                    # 解码HTML实体
                    import html
                    clean_url = html.unescape(clean_url)
                    # 更宽松的验证
                    if (clean_url and len(clean_url) > 20 and 
                        ('.webm' in clean_url.lower() or '.mp4' in clean_url.lower()) and 
                        ('phncdn.com' in clean_url or 'pornhub' in clean_url or 'preview' in clean_url.lower())):
                        preview_url = clean_url
                        if DEBUG['verbose']:
                            print(f"✓ 从页面找到预览视频: {preview_url}")
                        break
                if preview_url:
                    break
        
        return thumbnail_url, preview_url

def show_database_stats():
    """显示数据库统计信息"""
    db = DatabaseManager()
    stats = db.get_statistics()
    
    print("=" * 60)
    print("📊 数据库统计信息")
    print("=" * 60)
    print(f"总视频数: {stats['total_videos']}")
    print(f"总分类数: {stats['total_categories']}")
    print(f"最新采集时间: {stats['latest_collection']}")
    
    if stats['top_uploaders']:
        print(f"\n🔥 热门上传者 (前10):")
        for i, uploader in enumerate(stats['top_uploaders'][:10], 1):
            print(f"  {i:2d}. {uploader['uploader']:<30} ({uploader['count']} 个视频)")
    
    if stats['top_categories']:
        print(f"\n🏷️  热门分类 (前10):")
        for i, category in enumerate(stats['top_categories'][:10], 1):
            print(f"  {i:2d}. {category['name']:<20} ({category['count']} 个视频)")

def search_videos_cli(query, limit=20):
    """搜索视频命令行接口"""
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

def list_recent_videos_cli(limit=20):
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

def export_database_data(output_file, limit=None):
    """导出数据库数据"""
    db = DatabaseManager()
    try:
        db.export_to_json(output_file, limit=limit)
        print(f"✅ 数据导出成功: {output_file}")
    except Exception as e:
        print(f"❌ 导出失败: {e}")

def main():
    """主函数 - 支持命令行参数和数据库查询"""
    import sys
    
    # 检查是否是数据库查询命令
    if len(sys.argv) > 1 and sys.argv[1] in ['--stats', '--search', '--recent', '--export']:
        command = sys.argv[1]
        
        if command == '--stats':
            show_database_stats()
            return
        elif command == '--search':
            if len(sys.argv) < 3:
                print("❌ 请提供搜索关键词：python app.py --search '关键词'")
                return
            query = sys.argv[2]
            limit = int(sys.argv[3]) if len(sys.argv) > 3 else 20
            search_videos_cli(query, limit)
            return
        elif command == '--recent':
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
            list_recent_videos_cli(limit)
            return
        elif command == '--export':
            if len(sys.argv) < 3:
                print("❌ 请提供输出文件名：python app.py --export 'videos.json'")
                return
            output_file = sys.argv[2]
            limit = int(sys.argv[3]) if len(sys.argv) > 3 else None
            export_database_data(output_file, limit)
            return
    
    # 解析命令行参数（采集功能）
    start_page = 1
    max_pages = None
    
    if len(sys.argv) > 1:
        try:
            start_page = int(sys.argv[1])
        except ValueError:
            print("❌ 起始页参数无效，使用默认值 1")
    
    if len(sys.argv) > 2:
        try:
            max_pages = int(sys.argv[2])
            if max_pages <= 0:
                max_pages = None
        except ValueError:
            print("❌ 最大页数参数无效，将采集所有页面")
    
    print("🎯 Pornhub视频采集工具")
    print("=" * 50)
    
    try:
        scraper = PornhubScraper()
        
        # 从配置文件获取使用方式
        use_requests = DETAIL_PAGE_CONFIG.get('use_requests', True)  # 默认使用requests方式（更稳定）
        
        print(f"📊 配置信息:")
        print(f"  - 采集模式: {'requests' if use_requests else 'Selenium多标签页'}")
        print(f"  - 工作线程: {DETAIL_PAGE_CONFIG.get('max_workers_requests' if use_requests else 'max_workers_selenium', 5)}")
        print(f"  - 下载线程: {SCRAPER_CONFIG.get('download_threads', 10)}")
        print(f"  - 起始页面: {start_page}")
        print(f"  - 页数限制: {max_pages or '无限制'}")
        
        # 使用优化的运行流程
        result = scraper.optimized_run(
            start_page=start_page,
            use_requests_for_details=use_requests,
            max_pages=max_pages
        )
        
        if result:
            print("\n🎉 采集成功完成！")
            print(f"📈 详细统计:")
            print(f"  - 成功率: {result.get('success_rate', 0):.1f}%")
            print(f"  - 处理数量: {result.get('success_count', 0)}/{result.get('total_count', 0)}")
            print(f"  - 总耗时: {result.get('duration', 0):.1f} 秒")
        else:
            print("\n❌ 采集失败或被中断")
            
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断程序")
    except Exception as e:
        print(f"\n❌ 程序运行错误: {e}")
        import traceback
        if DEBUG.get('verbose', False):
            traceback.print_exc()

if __name__ == "__main__":
    main()