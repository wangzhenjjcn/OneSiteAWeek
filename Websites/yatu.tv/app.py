#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import os
import json
import time
import urllib.parse
from datetime import datetime
import logging
import chardet
import re
from database_manager import YatuTVDatabase
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import mimetypes
import psutil
import gc

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class YatuTVCrawler:
    def __init__(self):
        self.base_url = "https://www.yatu.tv"
        
        # 确保数据目录保存在yatu.tv目录下
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(script_dir, "data")
        
        # 确保数据目录存在
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        
        # 确保错误页面目录存在
        self.err_dir = os.path.join(script_dir, "err")
        if not os.path.exists(self.err_dir):
            os.makedirs(self.err_dir)
        
        # 初始化数据库
        self.db = YatuTVDatabase()
        
        # 定义分类页面URL
        self.category_urls = {
            '动漫': 'https://www.yatu.tv/m-dm/',
            '电影': 'https://www.yatu.tv/m-dy/',
            '电视剧': 'https://www.yatu.tv/m-tv/',
            'jc': 'https://www.yatu.tv/m-dm/jc.htm'  # 特殊页面
        }
        
        # 统计信息
        self.stats = {
            'skipped_newplay': 0,  # 跳过的newplay.asp链接数量
            'total_series': 0,     # 总剧集数量
            'successful_series': 0, # 成功抓取的剧集数量
            'consecutive_failures': 0,  # 连续失败次数
            'total_failures': 0,   # 总失败次数
            'network_errors': 0,   # 网络错误次数
            'auth_errors': 0,      # 认证错误次数
            'rate_limit_errors': 0, # 频率限制错误次数
            'server_errors': 0,    # 服务器错误次数
        }
        
        # 错误处理配置
        self.error_config = {
            'max_consecutive_failures': 10,  # 最大连续失败次数
            'retry_delay': 30,              # 重试延迟（秒）
            'max_retries': 3,               # 最大重试次数
            'backoff_factor': 2,            # 退避因子
        }
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        })
        
        # 多线程配置
        self.max_series_workers = 10  # 剧集级最大线程数
        self.max_episode_workers = 10  # 集数级最大线程数
        self.thread_lock = threading.Lock()  # 线程锁，用于保护共享资源
        self.progress_lock = threading.Lock()  # 进度锁，用于保护进度输出
        self.episode_thread_pool = None  # 集数级线程池
        self.episode_queue = []  # 集数任务队列
        self.episode_results = {}  # 集数分析结果
        
        # 内存优化配置
        self.memory_limit_mb = 1024  # 内存限制（MB）
        self.batch_size = 5  # 批处理大小
        self.gc_interval = 10  # 垃圾回收间隔（处理的剧集数）
        self.save_interval = 5  # 保存间隔（处理的剧集数）
        self.processed_count = 0  # 已处理剧集计数
    
    def get_page(self, url, series_id=None, episode_id=None, session=None):
        """获取页面内容"""
        try:
            # 使用传入的session或默认session
            current_session = session if session else self.session
            response = current_session.get(url, timeout=10)
            response.raise_for_status()
            
            # 智能编码检测和处理
            content_type = response.headers.get('content-type', '').lower()
            
            # 1. 首先检查HTTP头中的编码声明
            if 'charset=gb2312' in content_type or 'charset=gbk' in content_type:
                response.encoding = 'gb2312'
            elif 'charset=utf-8' in content_type:
                response.encoding = 'utf-8'
            else:
                # 2. 如果HTTP头没有明确编码，使用chardet自动检测
                detected = chardet.detect(response.content)
                detected_encoding = detected.get('encoding', '').lower()
                
                if detected_encoding in ['gb2312', 'gbk', 'gb18030']:
                    response.encoding = 'gb2312'
                elif detected_encoding in ['utf-8', 'utf-8-sig']:
                    response.encoding = 'utf-8'
                elif not response.encoding or response.encoding == 'ISO-8859-1':
                    # 3. 如果仍然检测不到，根据网站特点默认使用GB2312
                    response.encoding = 'gb2312'
            
            logger.debug(f"页面编码: {response.encoding}")
            
            # 检查页面内容是否正常
            html = response.text
            if self._is_error_page(html):
                error_type = self._analyze_error_page(html)
                self._handle_error(error_type, url, series_id=series_id, episode_id=episode_id, html_content=html)
                return None
            
            # 重置连续失败计数
            self.stats['consecutive_failures'] = 0
            return html
            
        except Exception as e:
            error_type = self._analyze_exception(e)
            self._handle_error(error_type, url, str(e), series_id=series_id, episode_id=episode_id, html_content=html if 'html' in locals() else None)
            return None
    
    def crawl_all_categories(self):
        """抓取所有分类页面的内容"""
        logger.info("开始抓取所有分类页面...")
        
        all_categories = {}
        
        for category_name, category_url in self.category_urls.items():
            logger.info(f"正在抓取 {category_name} 分类: {category_url}")
            
            # 抓取分类页面
            category_items = self.crawl_category_pages(category_url, category_name)
            
            all_categories[category_name] = {
                'name': category_name,
                'url': category_url,
                'items': category_items
            }
            
            logger.info(f"{category_name} 分类抓取完成，共 {len(category_items)} 部剧集")
        
        return all_categories
    
    def crawl_homepage(self):
        """抓取首页三个列表的内容（保留原有功能）"""
        logger.info("开始抓取首页内容...")
        
        html = self.get_page(self.base_url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 定义三个分类
        categories = {
            'sin1': {'name': '动漫', 'items': []},
            'sin2': {'name': '电影', 'items': []},
            'sin3': {'name': '电视剧', 'items': []}
        }
        
        for category_id, category_info in categories.items():
            logger.info(f"正在抓取 {category_info['name']} 列表...")
            
            # 查找对应的表格（注意：是直接查找table元素）
            table = soup.find('table', {'class': 'uptab', 'id': category_id})
            if not table:
                logger.warning(f"未找到 {category_id} 表格")
                continue
            
            rows = table.find_all('tr')
            for row in rows:
                # 查找剧集名称和链接
                cname2_td = row.find('td', class_='cname2')
                if not cname2_td:
                    continue
                
                a_tag = cname2_td.find('a')
                if not a_tag:
                    continue
                
                # 获取剧集信息
                title = a_tag.get_text(strip=True)
                href = a_tag.get('href', '')
                
                # 获取更新集数
                span_tag = cname2_td.find('span')
                episode_info = span_tag.get_text(strip=True) if span_tag else ''
                
                # 获取更新日期
                cdate_td = row.find('td', class_='cdate')
                update_date = cdate_td.get_text(strip=True) if cdate_td else ''
                
                # 完整的链接地址
                full_url = urllib.parse.urljoin(self.base_url, href)
                
                # 过滤掉newplay.asp开头的链接
                if full_url.startswith('https://www.yatu.tv/m/newplay.asp'):
                    logger.debug(f"跳过newplay.asp链接: {title}")
                    self.stats['skipped_newplay'] += 1
                    continue
                
                # 验证链接格式：必须是 /m数字id/ 格式的剧集详情页链接
                if not re.match(r'^/m\d+/$', href) and not re.match(r'^\.\./m\d+/$', href):
                    logger.debug(f"跳过不符合格式的剧集链接: {title} -> {href}")
                    self.stats['skipped_newplay'] += 1
                    continue
                
                # 提取剧集ID（从 /m030926/ 中提取 030926）
                series_id = href.strip('/').split('/')[-1] if href else ''
                # 如果series_id以m开头，去掉m前缀
                if series_id.startswith('m'):
                    series_id = series_id[1:]
                
                # 清理series_id，移除URL参数
                if '?' in series_id:
                    series_id = series_id.split('?')[0]
                
                item = {
                    'title': title,
                    'url': full_url,
                    'series_id': series_id,
                    'episode_info': episode_info,
                    'update_date': update_date,
                    'category': category_info['name']
                }
                
                category_info['items'].append(item)
                logger.info(f"抓取到: {title} -> {full_url}")
        
        return categories
    
    def crawl_category_pages(self, category_url, category_name):
        """抓取分类分页列表"""
        logger.info(f"开始抓取 {category_name} 分类分页...")
        
        all_items = []
        page = 1
        
        while True:
            # 构建分页URL
            if page == 1:
                page_url = category_url
            else:
                # 处理特殊页面（如jc.htm）
                if category_url.endswith('.htm'):
                    base_url = category_url.replace('.htm', '')
                    page_url = f"{base_url}/{page}.html"
                else:
                    # 新的分页格式：/m-dm/387.html, /m-dy/852.html, /m-tv/627.html
                    page_url = f"{category_url.rstrip('/')}/{page}.html"
            
            logger.info(f"正在抓取第 {page} 页: {page_url}")
            
            # 设置当前URL用于最后一页检测
            self.current_url = page_url
            
            html = self.get_page(page_url)
            if not html:
                logger.warning(f"无法获取第 {page} 页内容")
                break
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找剧集列表
            items = self._extract_series_items(soup, category_name)
            if not items:
                logger.info(f"第 {page} 页没有找到剧集")
                break
            
            all_items.extend(items)
            logger.info(f"第 {page} 页抓取到 {len(items)} 个剧集")
            if items:
                logger.info(f"第 {page} 页剧集列表:")
                for i, item in enumerate(items[:3]):  # 只显示前3个
                    logger.info(f"  {i+1}. {item['title']} -> {item['url']}")
                if len(items) > 3:
                    logger.info(f"  ... 还有 {len(items)-3} 个剧集")
            
            # 检查是否到达最后一页
            if self._is_last_page(soup):
                logger.info(f"到达最后一页，停止抓取")
                break
            
            page += 1
            time.sleep(1)  # 避免请求过快
        
        logger.info(f"{category_name} 分类总共抓取到 {len(all_items)} 个剧集")
        if all_items:
            logger.info(f"{category_name} 分类剧集详情:")
            for i, item in enumerate(all_items):
                logger.info(f"  {i+1}. {item['title']} -> {item['url']}")
        return all_items
    
    def _extract_series_items(self, soup, category_name):
        """从页面中提取剧集信息"""
        items = []
        
        # 查找剧集链接（m开头的数字ID）
        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            
            # 检查是否是剧集详情页链接（m开头的数字ID）
            # 使用更精确的正则表达式
            if re.match(r'^/m\d+/$', href) or re.match(r'^\.\./m\d+/$', href):
                title = link.get_text(strip=True)
                if not title:
                    continue
                
                # 完整的链接地址
                full_url = urllib.parse.urljoin(self.base_url, href)
                
                # 过滤掉newplay.asp开头的链接
                if full_url.startswith('https://www.yatu.tv/m/newplay.asp'):
                    logger.debug(f"跳过newplay.asp链接: {title}")
                    self.stats['skipped_newplay'] += 1
                    continue
                
                # 验证链接格式：必须是 /m数字id/ 格式的剧集详情页链接
                if not re.match(r'^/m\d+/$', href) and not re.match(r'^\.\./m\d+/$', href):
                    logger.debug(f"跳过不符合格式的剧集链接: {title} -> {href}")
                    self.stats['skipped_newplay'] += 1
                    continue
                
                # 提取剧集ID（从 /m030926/ 中提取 030926）
                series_id = href.strip('/').split('/')[-1] if href else ''
                # 如果series_id以m开头，去掉m前缀
                if series_id.startswith('m'):
                    series_id = series_id[1:]
                
                # 清理series_id，移除URL参数
                if '?' in series_id:
                    series_id = series_id.split('?')[0]
                
                item = {
                    'title': title,
                    'url': full_url,
                    'series_id': series_id,
                    'episode_info': '',
                    'update_date': '',
                    'category': category_name
                }
                
                items.append(item)
                logger.info(f"提取到剧集: {title} -> {full_url}")
        
        return items
    
    def _is_last_page(self, soup):
        """检查是否是最后一页"""
        # 方法1: 检查页面内容是否为空（没有找到任何剧集链接）
        series_links = soup.find_all('a', href=re.compile(r'/m\d+/'))
        if not series_links:
            return True
        
        # 方法2: 根据翻页链接数量判断
        # 查找所有"翻页"链接
        next_page_links = []
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            text = link.get_text(strip=True)
            if '翻页' in text:
                next_page_links.append({
                    'text': text,
                    'href': link.get('href', '')
                })
        
        # 如果只有一个翻页链接，说明是第一页或最后一页
        if len(next_page_links) == 1:
            next_link = next_page_links[0]
            next_href = next_link['href']
            
            # 如果翻页链接指向的是当前页面或首页，说明是最后一页
            if next_href.endswith('/') or next_href == '' or next_href == '#':
                return True
            
            # 检查是否指向较小的页码（说明是最后一页）
            page_match = re.search(r'(\d+)\.html', next_href)
            if page_match:
                next_page_num = int(page_match.group(1))
                # 从当前URL中提取当前页码
                current_page_match = re.search(r'(\d+)\.html', self.current_url)
                if current_page_match:
                    current_page_num = int(current_page_match.group(1))
                    if next_page_num < current_page_num:
                        return True
                else:
                    # 如果当前URL没有页码，说明是第一页
                    return False
        
        # 方法3: 检查是否有"没有更多内容"的提示
        no_more_texts = soup.find_all(string=re.compile(r'没有更多|已到最后一页|没有数据|暂无数据'))
        if no_more_texts:
            return True
        
        # 方法4: 检查页面内容是否明显少于正常页面（可能是最后一页）
        # 正常情况下每页应该有20-40个剧集
        if len(series_links) < 10:
            return True
        
        return False
    
    def find_external_sources(self, html):
        """查找站外片源"""
        try:
            from bs4 import BeautifulSoup
            import re
            
            soup = BeautifulSoup(html, 'html.parser')
            sources = []
            
            # 方法1: 查找包含"非本站片源"文本附近的元素
            non_local_texts = soup.find_all(string=re.compile("非本站片源"))
            for text in non_local_texts:
                parent = text.parent
                # 向上查找包含链接的容器
                container = parent
                for _ in range(3):  # 最多向上查找3层
                    if container.parent:
                        container = container.parent
                        links = container.find_all('a')
                        if links:
                            break
                
                # 从容器中提取链接
                for link in links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    # 过滤掉明显不是播放链接的内容
                    if href and text and not any(skip in text.lower() for skip in ['登录', '建议', '报错', '注册']):
                        # 构建完整URL
                        if href.startswith('/'):
                            full_url = urllib.parse.urljoin(self.base_url, href)
                        else:
                            full_url = href
                        
                        sources.append({
                            'source_id': f"external_{len(sources)}",
                            'source_name': text,
                            'source_url': full_url,
                            'source_type': '站外片源'
                        })
            
            # 方法2: 查找play数字-数字.html格式的链接（只接受正确的格式）
            play_links = soup.find_all('a', href=re.compile(r'play\d+-\d+\.html'))
            for link in play_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                if href and text:
                    # 验证链接格式：必须是正确的播放链接格式
                    if not self._is_valid_play_url(href):
                        logger.debug(f"跳过不符合格式的播放链接: {text} -> {href}")
                        continue
                    
                    # 过滤掉以newplay.asp开头的链接
                    if href.startswith('/m/newplay.asp') or 'newplay.asp' in href:
                        logger.debug(f"跳过newplay.asp播放链接: {text} -> {href}")
                        continue
                    
                    full_url = urllib.parse.urljoin(self.base_url, href)
                    
                    # 额外过滤：确保不是newplay.asp开头的完整URL
                    if full_url.startswith('https://www.yatu.tv/m/newplay.asp'):
                        logger.debug(f"跳过newplay.asp完整URL: {text} -> {full_url}")
                        continue
                    
                    # 检查是否已存在
                    exists = any(s['source_url'] == full_url for s in sources)
                    if not exists:
                        sources.append({
                            'source_id': f"play_{len(sources)}",
                            'source_name': f"播放链接: {text}",
                            'source_url': full_url,
                            'source_type': '站外片源'
                        })
                        logger.info(f"找到正确的播放链接: {text} -> {full_url}")
            
            # 方法3: 查找id包含cs的元素
            cs_elements = soup.find_all(attrs={"id": re.compile(r"cs\d*")})
            for element in cs_elements:
                links = element.find_all('a')
                for link in links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    if href and text and not any(skip in text.lower() for skip in ['登录', '建议', '报错', '注册']):
                        if href.startswith('/'):
                            full_url = urllib.parse.urljoin(self.base_url, href)
                        else:
                            full_url = href
                        
                        # 检查是否已存在
                        exists = any(s['source_url'] == full_url for s in sources)
                        if not exists:
                            sources.append({
                                'source_id': f"cs_{len(sources)}",
                                'source_name': text,
                                'source_url': full_url,
                                'source_type': '站外片源'
                            })
            
            logger.info(f"找到 {len(sources)} 个站外片源")
            return sources
            
        except Exception as e:
            logger.error(f"查找站外片源失败: {e}")
            return []
    
    def crawl_series_detail_with_episode_pool(self, series_url, series_id, category_type=None, session=None):
        """使用集数级线程池抓取剧集详情"""
        logger.info(f"正在抓取剧集详情: {series_url}")
        logger.info(f"剧集ID: {series_id}, 分类: {category_type}")
        
        # 检查数据库和data目录的状态
        db_has_series = self.db.is_series_crawled(series_id)
        existing_data = self.check_existing_data(series_id)
        
        # 确定是否需要抓取和生成data文件
        need_crawl = True
        need_generate_data = True
        
        if db_has_series and existing_data:
            logger.info(f"剧集 {series_id} 在数据库和data目录中都存在，跳过抓取")
            need_crawl = False
            need_generate_data = False
        elif db_has_series and not existing_data:
            logger.info(f"剧集 {series_id} 在数据库中存在但data目录中缺失，需要从数据库生成data文件")
            need_crawl = False
            need_generate_data = True
        elif not db_has_series and existing_data:
            logger.info(f"剧集 {series_id} 在data目录中存在但数据库中缺失，需要更新数据库")
            need_crawl = True
            need_generate_data = False
        else:
            logger.info(f"剧集 {series_id} 在数据库和data目录中都不存在，需要完整抓取")
            need_crawl = True
            need_generate_data = True
        
        # 如果不需要抓取但需要生成data文件，从数据库生成
        if not need_crawl and need_generate_data:
            logger.info(f"从数据库生成剧集 {series_id} 的data文件")
            series_info = self._generate_data_from_database(series_id, category_type)
            if series_info:
                self.save_series_data(series_info)
                return series_info
            else:
                logger.warning(f"无法从数据库生成剧集 {series_id} 的数据，将进行完整抓取")
                need_crawl = True
                need_generate_data = True
        
        # 使用传入的session或默认session
        current_session = session if session else self.session
        html = self.get_page(series_url, series_id=series_id, session=current_session)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 查找剧集列表并分析剧集数量和线路
        episodes = []
        episode_patterns = []
        
        # 首先查找现有的播放链接以了解剧集结构
        # 方法1: 查找特定的播放容器
        span_flv = soup.find('span', id='span_flv')
        if not span_flv:
            js_flv_span = soup.find('span', id='js_flv')
            flv_yp0_span = soup.find('span', id='flv_yp0')
            span_flv = flv_yp0_span if flv_yp0_span else js_flv_span
        
        if span_flv:
            a_tags = span_flv.find_all('a', href=True)
            for a_tag in a_tags:
                episode_text = a_tag.get_text(strip=True)
                episode_url = a_tag.get('href', '')
                
                if episode_text and episode_url and 'play' in episode_url:
                    episode_patterns.append((episode_text, episode_url))
        
        # 方法2: 如果方法1没有找到，使用更全面的查找
        if not episode_patterns:
            logger.info("未在特定容器中找到播放链接，使用全面查找方法")
            
            # 查找所有play数字-数字.html格式的链接
            play_links = soup.find_all('a', href=re.compile(r'play\d+-\d+\.html'))
            for link in play_links:
                episode_text = link.get_text(strip=True)
                episode_url = link.get('href', '')
                
                if episode_text and episode_url:
                    # 验证链接格式
                    if self._is_valid_play_url(episode_url):
                        episode_patterns.append((episode_text, episode_url))
                        logger.debug(f"找到播放链接: {episode_text} -> {episode_url}")
        
        # 方法3: 查找id包含cs的元素中的播放链接
        if not episode_patterns:
            logger.info("未找到标准播放链接，查找cs元素中的链接")
            cs_elements = soup.find_all(attrs={"id": re.compile(r"cs\d*")})
            for element in cs_elements:
                links = element.find_all('a')
                for link in links:
                    episode_text = link.get_text(strip=True)
                    episode_url = link.get('href', '')
                    
                    if episode_text and episode_url and 'play' in episode_url:
                        if self._is_valid_play_url(episode_url):
                            episode_patterns.append((episode_text, episode_url))
                            logger.debug(f"在cs元素中找到播放链接: {episode_text} -> {episode_url}")
        
        if not episode_patterns:
            logger.error("未找到任何播放链接，保存页面用于调试")
            self.save_error_page(html, series_id, "no_play_links")
            return None
        
        logger.info(f"总共找到 {len(episode_patterns)} 个播放链接模式")
        
        # 分析剧集规律
        max_episode = 0
        available_lines = set()
        
        for episode_text, episode_url in episode_patterns:
            # 从URL提取线路和集数: play0-123.html
            play_match = re.search(r'play(\d+)-(\d+)\.html', episode_url)
            if play_match:
                line_id = int(play_match.group(1))
                episode_num = int(play_match.group(2))
                available_lines.add(line_id)
                max_episode = max(max_episode, episode_num)
        
        if max_episode == 0:
            logger.error("无法分析剧集规律")
            return None
        
        logger.info(f"发现剧集规律: 最大集数 {max_episode}, 可用线路 {sorted(available_lines)}")
        
        # 选择最佳线路（通常线路0最稳定）
        best_line = 0 if 0 in available_lines else min(available_lines)
        logger.info(f"生成完整剧集列表: {max_episode} 集，使用线路 {best_line}")
        
        # 生成完整的剧集列表
        for episode_num in range(1, max_episode + 1):
            episode_url = f"play{best_line}-{episode_num}.html"
            episode_text = f"第{episode_num:02d}集"
            
            # 检查是否已存在
            if not self.db.is_episode_crawled(series_id, episode_num):
                episodes.append({
                    'episode': episode_num,
                    'title': episode_text,
                    'url': episode_url,
                    'playframe_url': '',
                    'note': ''
                })
            else:
                logger.info(f"第{episode_num:02d}集在数据库和data中都存在，跳过")
        
        if not episodes:
            logger.warning("所有集数都已存在，无需抓取")
            # 从数据库获取现有数据
            series_info = self._generate_data_from_database(series_id, category_type)
            if series_info:
                return series_info
            else:
                logger.error("无法从数据库获取现有数据")
                return None
        
        logger.info(f"找到 {len(episodes)} 集")
        
        # 使用集数级线程池分析详细页面
        self.analyze_episodes_with_thread_pool(episodes, series_id, current_session)
        
        # 保存详情页HTML到数据库
        self.db.save_detail_html(series_id, html)
        logger.info(f"已保存详情页HTML到数据库: {series_id}")
        
        # 下载并保存封面图片
        cover_url = self.extract_cover_image(soup)
        if cover_url:
            self.download_cover_image(cover_url, series_id, current_session)
        
        # 构建完整的剧集信息
        series_info = {
            'series_id': series_id,
            'title': self.extract_title(soup),
            'url': series_url,
            'description': self.extract_description(soup),
            'category': category_type,
            'year': self.extract_year(soup),
            'country': self.extract_country(soup),
            'language': self.extract_language(soup),
            'director': self.extract_director(soup),
            'actors': self.extract_actors(soup),
            'episodes': episodes,
            'cover_image': cover_url if cover_url else ""
        }
        
        # 保存到数据库
        self.db.save_series(series_info)
        for episode in episodes:
            self.db.save_episode(series_id, episode)
        
        return series_info

    def analyze_episodes_with_thread_pool(self, episodes, series_id, session):
        """使用集数级线程池分析剧集详细页面"""
        logger.info("正在分析视频源信息和尝试获取m3u8地址...")
        
        def analyze_single_episode(episode):
            """分析单个集数的详细页面"""
            episode_num = episode['episode']
            episode_url = episode['url']
            
            # 检查是否已存在
            if self.db.is_episode_crawled(series_id, episode_num):
                logger.info(f"第{episode_num:02d}集在数据库中存在但data中缺失，需要更新")
            else:
                logger.info(f"第{episode_num:02d}集在数据库和data中都不存在，需要抓取")
            
            logger.info(f"正在分析第{episode_num:02d}集的播放地址...")
            
            # 构建完整的播放URL
            play_url = urllib.parse.urljoin(f"https://www.yatu.tv/m{series_id}/", episode_url)
            
            # 获取playframe地址
            real_url = self.get_playframe_url(play_url, series_id=series_id, episode_id=episode_num, session=session)
            if real_url:
                episode['playframe_url'] = real_url
                logger.info(f"✓ 第{episode_num:02d}集解析成功: {real_url}")
                return True
            else:
                logger.warning(f"✗ 第{episode_num:02d}集解析失败")
                return False
        
        # 使用集数级线程池分析所有集数
        futures = []
        for episode in episodes:
            future = self.episode_thread_pool.submit(analyze_single_episode, episode)
            futures.append(future)
        
        # 等待所有集数分析完成
        successful_count = 0
        for future in as_completed(futures):
            try:
                if future.result():
                    successful_count += 1
            except Exception as e:
                logger.error(f"集数分析异常: {str(e)}")
        
        logger.info(f"✓ 成功获取到 {successful_count} 集的播放地址")

    def crawl_series_detail(self, series_url, series_id, category_type=None, session=None):
        """抓取剧集详情页面"""
        logger.info(f"正在抓取剧集详情: {series_url}")
        logger.info(f"剧集ID: {series_id}, 分类: {category_type}")
        
        # 检查数据库和data目录的状态
        db_has_series = self.db.is_series_crawled(series_id)
        existing_data = self.check_existing_data(series_id)
        
        # 确定是否需要抓取和生成data文件
        need_crawl = True
        need_generate_data = True
        
        if db_has_series and existing_data:
            logger.info(f"剧集 {series_id} 在数据库和data目录中都存在，跳过抓取")
            need_crawl = False
            need_generate_data = False
        elif db_has_series and not existing_data:
            logger.info(f"剧集 {series_id} 在数据库中存在但data目录中缺失，需要从数据库生成data文件")
            need_crawl = False
            need_generate_data = True
        elif not db_has_series and existing_data:
            logger.info(f"剧集 {series_id} 在data目录中存在但数据库中缺失，需要更新数据库")
            need_crawl = True
            need_generate_data = False
        else:
            logger.info(f"剧集 {series_id} 在数据库和data目录中都不存在，需要完整抓取")
            need_crawl = True
            need_generate_data = True
        
        # 如果不需要抓取但需要生成data文件，从数据库生成
        if not need_crawl and need_generate_data:
            logger.info(f"从数据库生成剧集 {series_id} 的data文件")
            series_info = self._generate_data_from_database(series_id, category_type)
            if series_info:
                self.save_series_data(series_info)
                return series_info
            else:
                logger.warning(f"无法从数据库生成剧集 {series_id} 的数据，将进行完整抓取")
                need_crawl = True
                need_generate_data = True
        
        # 使用传入的session或默认session
        current_session = session if session else self.session
        html = self.get_page(series_url, series_id=series_id, session=current_session)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 查找剧集列表并分析剧集数量和线路
        episodes = []
        episode_patterns = []
        
        # 首先查找现有的播放链接以了解剧集结构
        # 方法1: 查找特定的播放容器
        span_flv = soup.find('span', id='span_flv')
        if not span_flv:
            js_flv_span = soup.find('span', id='js_flv')
            flv_yp0_span = soup.find('span', id='flv_yp0')
            span_flv = flv_yp0_span if flv_yp0_span else js_flv_span
        
        if span_flv:
            a_tags = span_flv.find_all('a', href=True)
            for a_tag in a_tags:
                episode_text = a_tag.get_text(strip=True)
                episode_url = a_tag.get('href', '')
                
                if episode_text and episode_url and 'play' in episode_url:
                    episode_patterns.append((episode_text, episode_url))
        
        # 方法2: 如果方法1没有找到，使用更全面的查找
        if not episode_patterns:
            logger.info("未在特定容器中找到播放链接，使用全面查找方法")
            
            # 查找所有play数字-数字.html格式的链接
            play_links = soup.find_all('a', href=re.compile(r'play\d+-\d+\.html'))
            for link in play_links:
                episode_text = link.get_text(strip=True)
                episode_url = link.get('href', '')
                
                if episode_text and episode_url:
                    # 验证链接格式
                    if self._is_valid_play_url(episode_url):
                        episode_patterns.append((episode_text, episode_url))
                        logger.debug(f"找到播放链接: {episode_text} -> {episode_url}")
        
        # 方法3: 查找id包含cs的元素中的播放链接
        if not episode_patterns:
            logger.info("未找到标准播放链接，查找cs元素中的链接")
            cs_elements = soup.find_all(attrs={"id": re.compile(r"cs\d*")})
            for element in cs_elements:
                links = element.find_all('a')
                for link in links:
                    episode_text = link.get_text(strip=True)
                    episode_url = link.get('href', '')
                    
                    if episode_text and episode_url and 'play' in episode_url:
                        if self._is_valid_play_url(episode_url):
                            episode_patterns.append((episode_text, episode_url))
                            logger.debug(f"在cs元素中找到播放链接: {episode_text} -> {episode_url}")
        
        logger.info(f"总共找到 {len(episode_patterns)} 个播放链接模式")
        
        # 如果没有找到任何播放链接，保存页面用于调试
        if not episode_patterns:
            logger.error(f"未找到任何播放链接，保存页面用于调试")
            self._save_error_page(
                series_id, 
                None, 
                'no_play_links', 
                series_url, 
                html, 
                f"在剧集详情页中未找到任何播放链接，页面类型: {self._analyze_page_type(series_url, html)}"
            )
            return None
        
        # 分析剧集规律：play0-1.html, play0-2.html 等
        max_episodes = 0
        available_lines = set()
        
        for episode_text, episode_url in episode_patterns:
            # 从URL中提取线路和集数：play0-123.html
            play_match = re.search(r'play(\d+)-(\d+)\.html', episode_url)
            if play_match:
                line_num = int(play_match.group(1))
                episode_num = int(play_match.group(2))
                available_lines.add(line_num)
                max_episodes = max(max_episodes, episode_num)
        
        logger.info(f"发现剧集规律: 最大集数 {max_episodes}, 可用线路 {sorted(available_lines)}")
        
        # 如果没有发现规律，使用原始方法
        if not available_lines or max_episodes == 0:
            logger.warning("未发现剧集规律，使用原始抓取方法")
            for episode_text, episode_url in episode_patterns:
                full_episode_url = urllib.parse.urljoin(self.base_url, episode_url)
                episode = {
                    'episode': episode_text,
                    'url': full_episode_url,
                    'line': 0,
                    'episode_num': len(episodes) + 1
                }
                episodes.append(episode)
        else:
            # 使用发现的规律生成完整的剧集列表
            primary_line = min(available_lines)  # 使用第一个线路作为主线路
            
            for ep_num in range(1, max_episodes + 1):
                # 构建正确的播放URL格式：/m数字id/play片源id-剧集集数.html
                episode_url = f"play{primary_line}-{ep_num}.html"
                full_episode_url = urllib.parse.urljoin(series_url, episode_url)
                
                episode = {
                    'episode': f"{ep_num:02d}",  # 格式化为 01, 02, 03...
                    'url': full_episode_url,
                    'line': primary_line,
                    'episode_num': ep_num
                }
                episodes.append(episode)
            
            logger.info(f"生成完整剧集列表: {len(episodes)} 集，使用线路 {primary_line}")
        
        # 获取剧集标题
        title_element = soup.find('h1') or soup.find('title')
        title = title_element.get_text(strip=True) if title_element else series_id
        
        # 获取封面图片
        cover_image = None
        # 查找可能的封面图片
        img_selectors = [
            'img[src*="jpg"]',
            'img[src*="jpeg"]', 
            'img[src*="png"]',
            'img[src*="webp"]'
        ]
        
        for selector in img_selectors:
            img_elements = soup.select(selector)
            for img in img_elements:
                src = img.get('src', '')
                if src and any(keyword in src.lower() for keyword in ['cover', 'poster', 'thumb', series_id]):
                    cover_image = urllib.parse.urljoin(self.base_url, src)
                    break
            if cover_image:
                break
        
        # 如果没找到特定的封面，使用第一个合适大小的图片
        if not cover_image:
            for selector in img_selectors:
                img_elements = soup.select(selector)
                for img in img_elements:
                    src = img.get('src', '')
                    if src and not any(keyword in src.lower() for keyword in ['icon', 'logo', 'button', 'arrow']):
                        # 检查图片尺寸信息或路径，优选可能是封面的图片
                        width = img.get('width', '')
                        height = img.get('height', '')
                        if width and height:
                            try:
                                w, h = int(width), int(height)
                                if w > 100 and h > 100:  # 足够大的图片
                                    cover_image = urllib.parse.urljoin(self.base_url, src)
                                    break
                            except:
                                pass
                        else:
                            cover_image = urllib.parse.urljoin(self.base_url, src)
                            break
                if cover_image:
                    break
        
        # 获取剧集介绍信息
        description = ""
        # 查找可能包含介绍的元素
        desc_selectors = [
            '.intro',
            '.description', 
            '.summary',
            '.content',
            'meta[name="description"]',
            'p'
        ]
        
        for selector in desc_selectors:
            if selector.startswith('meta'):
                meta_desc = soup.select_one(selector)
                if meta_desc:
                    description = meta_desc.get('content', '').strip()
                    if description:
                        break
            else:
                desc_elements = soup.select(selector)
                for desc in desc_elements:
                    text = desc.get_text(strip=True)
                    if text and len(text) > 50:  # 足够长的描述
                        description = text
                        break
                if description:
                    break
        
        # 获取更多元信息
        meta_info = {}
        
        # 查找年份
        year_patterns = [r'(\d{4})年', r'(\d{4})', r'20\d{2}']
        year_text = html
        for pattern in year_patterns:
            year_match = re.search(pattern, year_text)
            if year_match:
                meta_info['year'] = year_match.group(1)
                break
        
        # 设置正确的分类信息
        if category_type:
            meta_info['categories'] = [category_type]
            
            # 添加其他类型关键词（非主分类）
            other_keywords = ['剧情', '喜剧', '动作', '科幻', '恐怖', '悬疑', '战争', '爱情']
            for keyword in other_keywords:
                if keyword in html:
                    meta_info['categories'].append(keyword)
        else:
            # 如果没有分类信息，使用旧的方法
            category_keywords = ['动漫', '电影', '电视剧', '剧情', '喜剧', '动作', '科幻', '恐怖']
            for keyword in category_keywords:
                if keyword in html:
                    meta_info.setdefault('categories', []).append(keyword)
        
        # 查找导演、演员等信息
        if '导演' in html:
            director_match = re.search(r'导演[：:]\s*([^<>\n]+)', html)
            if director_match:
                meta_info['director'] = director_match.group(1).strip()
        
        if '主演' in html or '演员' in html:
            cast_match = re.search(r'(?:主演|演员)[：:]\s*([^<>\n]+)', html)
            if cast_match:
                meta_info['cast'] = cast_match.group(1).strip()
        
        # 为每集添加视频源信息，并尝试获取m3u8地址（重点关注playframe）
        logger.info("正在分析视频源信息和尝试获取m3u8地址...")
        
        # 为所有集数尝试获取playframe地址
        playframe_found_count = 0
        
        for i, episode in enumerate(episodes):
            # 初始化字段
            episode['video_source'] = "站外片源"
            episode['playframe_url'] = None
            episode['note'] = ""
            episode_id = episode['episode']
            
            # 检查现有数据中是否已有此集的playframe地址
            existing_episode = None
            if existing_data and 'episodes' in existing_data:
                current_episode_num = self._extract_episode_number(episode['episode'])
                
                for existing_ep in existing_data['episodes']:
                    existing_episode_id = existing_ep.get('episode')
                    existing_episode_num = self._extract_episode_number(existing_episode_id)
                    
                    # 比较集数数字部分
                    if existing_episode_num and current_episode_num and existing_episode_num == current_episode_num:
                        existing_episode = existing_ep
                        break
            
            # 检查数据库和现有数据的状态
            db_has_episode = self.db.is_episode_crawled(series_id, episode_id)
            
            # 只有当数据库中有此集且现有数据中也有此集时才跳过
            if db_has_episode and existing_episode:
                episode['note'] = "✓ 数据库和data中都已存在"
                playframe_found_count += 1
                logger.info(f"✓ 第{episode_id}集在数据库和data中都存在，跳过")
                continue
            elif db_has_episode and not existing_episode:
                logger.info(f"第{episode_id}集在数据库中存在但data中缺失，需要更新")
            elif not db_has_episode and existing_episode:
                logger.info(f"第{episode_id}集在data中存在但数据库中缺失，需要更新")
            else:
                logger.info(f"第{episode_id}集在数据库和data中都不存在，需要抓取")
            
            # 如果已有playframe地址，直接复用
            if existing_episode and existing_episode.get('playframe_url'):
                episode['playframe_url'] = existing_episode['playframe_url']
                episode['note'] = "✓ 复用播放地址"
                playframe_found_count += 1
                logger.info(f"✓ 复用第{episode['episode']}集的播放地址")
                
                # 保存到数据库
                self.db.save_episode(series_id, episode)
                continue
            
            # 专注于站外片源分析
            try:
                logger.info(f"正在分析第{episode['episode']}集的播放地址...")
                
                # 获取播放页面的HTML
                play_html = self.get_page(episode['url'], series_id=series_id, episode_id=episode['episode'])
                if not play_html:
                    episode['note'] = "无法获取播放页面"
                    self.db.save_episode(series_id, episode)
                    continue
                
                # 直接从播放页面提取iframe地址
                play_url = episode['url']
                if 'play' in play_url and '.html' in play_url:
                    real_url = self.get_playframe_url(play_url, series_id=series_id, episode_id=episode['episode'], session=current_session)
                    if real_url:
                        episode['playframe_url'] = real_url
                        episode['note'] = f"✓ 解析成功: 直接提取"
                        playframe_found_count += 1
                        logger.info(f"✓ 第{episode['episode']}集解析成功: {real_url}")
                        
                        # 保存片源信息到数据库
                        source_info = {
                            'source_id': 'direct_extract',
                            'source_name': '直接提取',
                            'source_url': play_url,
                            'real_url': real_url,
                            'source_type': '直接提取'
                        }
                        self.db.save_source(series_id, episode_id, source_info)
                    else:
                        episode['note'] = f"❌ 解析失败: 无法提取播放地址"
                        logger.info(f"❌ 第{episode['episode']}集解析失败")
                        
                        # 尝试查找站外片源作为备选方案
                        logger.info(f"尝试查找第{episode['episode']}集的站外片源作为备选...")
                        external_sources = self.find_external_sources(play_html)
                        
                        if external_sources:
                            logger.info(f"第{episode['episode']}集找到 {len(external_sources)} 个站外片源")
                            
                            # 处理每个站外片源
                            for source in external_sources:
                                source_id = source['source_id']
                                
                                # 检查数据库中是否已有此片源
                                db_has_source = self.db.is_source_crawled(series_id, episode_id, source_id)
                                
                                # 如果数据库中已有此片源，跳过
                                if db_has_source:
                                    logger.info(f"片源 {source['source_name']} 已在数据库中，跳过")
                                    continue
                                
                                # 解析play页面的iframe实际地址
                                source_play_url = source['source_url']
                                if 'play' in source_play_url and '.html' in source_play_url:
                                    source_real_url = self.get_playframe_url(source_play_url, series_id=series_id, episode_id=episode['episode'], session=current_session)
                                    if source_real_url:
                                        source['real_url'] = source_real_url
                                        episode['playframe_url'] = source_real_url
                                        episode['note'] = f"✓ 备选解析成功: {source['source_name']}"
                                        playframe_found_count += 1
                                        logger.info(f"✓ 备选解析成功: {source['source_name']} -> {source_real_url}")
                                        break  # 找到一个就停止
                                    else:
                                        source['real_url'] = None
                                        logger.info(f"❌ 备选解析失败: {source['source_name']}")
                                else:
                                    # 非play链接，直接保存
                                    source['real_url'] = None
                                    episode['playframe_url'] = source_play_url
                                    episode['note'] = f"✓ 备选站外片源: {source['source_name']}"
                                    playframe_found_count += 1
                                    logger.info(f"✓ 备选保存片源链接: {source['source_name']} -> {source_play_url}")
                                    break  # 找到一个就停止
                                
                                # 立即保存片源信息到数据库
                                self.db.save_source(series_id, episode_id, source)
                                
                                # 延时避免请求过快
                                time.sleep(0.5)
                            
                            if not episode.get('playframe_url'):
                                episode['note'] = f"站外片源 {len(external_sources)} 个，均无法播放"
                        else:
                            episode['note'] = "未找到站外片源"
                            logger.debug(f"- 第{episode['episode']}集未找到站外片源")
                else:
                    # 非play链接，直接保存
                    episode['playframe_url'] = play_url
                    episode['note'] = f"✓ 非播放链接: 直接保存"
                    playframe_found_count += 1
                    logger.info(f"✓ 非播放链接: {play_url}")
                    
                    # 保存片源信息到数据库
                    source_info = {
                        'source_id': 'non_play_link',
                        'source_name': '非播放链接',
                        'source_url': play_url,
                        'real_url': None,
                        'source_type': '非播放链接'
                    }
                    self.db.save_source(series_id, episode_id, source_info)
                
                # 保存集数信息到数据库
                self.db.save_episode(series_id, episode)
                
                # 延时避免请求过快
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"分析第{episode['episode']}集播放地址失败: {e}")
                episode['note'] = "分析失败"
                self.db.save_episode(series_id, episode)
        
        if playframe_found_count > 0:
            logger.info(f"✓ 成功获取到 {playframe_found_count} 集的播放地址")
        else:
            logger.info("未能获取到播放地址")
        
        logger.info(f"视频源分析完成 - 共{len(episodes)}集，类型：{episodes[0]['video_source'] if episodes else '未知'}")
        
        series_info = {
            'title': title,
            'series_id': series_id,
            'url': series_url,
            'cover_image': cover_image,
            'description': description,
            'meta_info': meta_info,
            'episodes': episodes,
            'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        logger.info(f"找到 {len(episodes)} 集")
        
        # 保存详情页HTML到数据库
        self.db.save_detail_html(series_id, html)
        logger.info(f"已保存详情页HTML到数据库: {series_id}")
        
        # 保存剧集信息到数据库
        self.db.save_series(series_info)
        
        # 保存剧集数据到data目录（生成HTML文件）
        self.save_series_data(series_info)
        
        return series_info
    
    def get_playframe_url(self, play_url, series_id=None, episode_id=None, session=None):
        """获取playframe iframe的src地址"""
        try:
            logger.info(f"正在获取playframe地址: {play_url}")
            
            # 从play_url提取详情页URL作为Referer
            detail_url = '/'.join(play_url.split('/')[:-1]) + '/'
            logger.debug(f"设置Referer: {detail_url}")
            
            # 为播放页面设置特殊的请求头
            headers = {
                'Referer': detail_url,
                'Sec-Fetch-Dest': 'iframe',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
            }
            
            html = self.get_page_with_headers(play_url, headers, series_id=series_id, episode_id=episode_id, session=session)
            if not html:
                logger.error(f"无法获取播放页面HTML: {play_url}")
                return None
            
            logger.debug(f"播放页面HTML长度: {len(html)} 字符")
            
            # 查找playframe iframe的src地址
            iframe_url = self._extract_iframe_src(html)
            if iframe_url:
                logger.info(f"✓ 找到playframe地址: {iframe_url}")
                return iframe_url
            else:
                logger.warning(f"未找到playframe iframe: {play_url}")
                # 输出HTML片段用于调试
                if len(html) > 500:
                    logger.debug(f"HTML片段: {html[:500]}...")
                
                # 尝试从JavaScript中提取
                logger.info("尝试从JavaScript中提取iframe链接...")
                js_iframe_url = self._extract_iframe_from_js(html)
                if js_iframe_url:
                    logger.info(f"✓ 从JavaScript中找到playframe地址: {js_iframe_url}")
                    return js_iframe_url
                
                # 如果还是没找到，输出更多调试信息
                logger.debug(f"页面总长度: {len(html)} 字符")
                if 'iframe' in html.lower():
                    logger.debug("页面包含iframe标签")
                if 'script' in html.lower():
                    logger.debug("页面包含script标签")
                if 'playframe' in html.lower():
                    logger.debug("页面包含playframe相关内容")
                
                return None
            
        except Exception as e:
            logger.error(f"获取playframe地址失败: {play_url}, 错误: {e}")
            return None
    
    def check_existing_data(self, series_id):
        """检查是否已存在剧集数据"""
        try:
            series_dir = os.path.join(self.data_dir, series_id)
            json_file = os.path.join(series_dir, 'info.json')
            
            if os.path.exists(json_file):
                with open(json_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.debug(f"检查已存在数据失败: {e}")
            return None
    
    def _generate_data_from_database(self, series_id, category_type=None):
        """从数据库生成剧集数据"""
        try:
            # 获取剧集基本信息
            series_data = self.db.get_series_by_id(series_id)
            if not series_data:
                logger.error(f"数据库中未找到剧集 {series_id} 的基本信息")
                return None
            
            # 获取剧集的所有集数
            episodes_data = self.db.get_episodes(series_id)
            if not episodes_data:
                logger.error(f"数据库中未找到剧集 {series_id} 的集数信息")
                return None
            
            # 构建剧集信息
            series_info = {
                'series_id': series_id,
                'title': series_data.get('title', ''),
                'url': series_data.get('url', series_data.get('series_url', '')),
                'description': series_data.get('description', ''),
                'category': series_data.get('category', category_type or ''),
                'year': series_data.get('year', series_data.get('release_date', '')),
                'country': series_data.get('country', ''),
                'language': series_data.get('language', ''),
                'director': series_data.get('director', ''),
                'actors': series_data.get('actors', ''),
                'cover_image': '',
                'meta_info': {},
                'episodes': []
            }
            
            # 处理集数信息
            for episode_data in episodes_data:
                episode_id = episode_data.get('episode', episode_data.get('episode_id', ''))
                episode_title = episode_data.get('title', episode_data.get('episode_title', ''))
                episode_url = episode_data.get('url', episode_data.get('source_url', ''))
                playframe_url = episode_data.get('playframe_url', '')
                
                # 获取该集数的所有片源
                sources_data = self.db.get_sources(series_id, episode_id)
                sources = []
                
                for source_data in sources_data:
                    source = {
                        'source_id': source_data.get('source_id', ''),
                        'source_name': source_data.get('source_name', ''),
                        'source_url': source_data.get('source_url', ''),
                        'real_url': source_data.get('real_url', ''),
                        'source_type': source_data.get('source_type', '')
                    }
                    sources.append(source)
                
                episode = {
                    'episode': episode_id,
                    'title': episode_title,
                    'url': episode_url,
                    'playframe_url': playframe_url,
                    'note': '',
                    'sources': sources
                }
                
                series_info['episodes'].append(episode)
            
            logger.info(f"从数据库成功生成剧集 {series_id} 的数据，共 {len(series_info['episodes'])} 集")
            return series_info
            
        except Exception as e:
            logger.error(f"从数据库生成剧集 {series_id} 数据失败: {e}")
            return None
    
    def get_page_with_headers(self, url, additional_headers=None, series_id=None, episode_id=None, session=None):
        """使用特定请求头获取页面内容"""
        try:
            # 使用传入的session或默认session
            current_session = session if session else self.session
            headers = current_session.headers.copy()
            if additional_headers:
                headers.update(additional_headers)
            
            response = current_session.get(url, timeout=10, headers=headers)
            response.raise_for_status()
            
            # 智能编码检测和处理
            content_type = response.headers.get('content-type', '').lower()
            
            if 'charset=gb2312' in content_type or 'charset=gbk' in content_type:
                response.encoding = 'gb2312'
            elif 'charset=utf-8' in content_type:
                response.encoding = 'utf-8'
            else:
                import chardet
                detected = chardet.detect(response.content)
                detected_encoding = detected.get('encoding', '').lower()
                
                if detected_encoding in ['gb2312', 'gbk', 'gb18030']:
                    response.encoding = 'gb2312'
                elif detected_encoding in ['utf-8', 'utf-8-sig']:
                    response.encoding = 'utf-8'
                elif not response.encoding or response.encoding == 'ISO-8859-1':
                    response.encoding = 'gb2312'
            
            logger.debug(f"页面编码: {response.encoding}")
            
            # 检查页面内容是否正常
            html = response.text
            if self._is_error_page(html):
                error_type = self._analyze_error_page(html)
                self._handle_error(error_type, url, series_id=series_id, episode_id=episode_id, html_content=html)
                return None
            
            # 重置连续失败计数
            self.stats['consecutive_failures'] = 0
            return html
            
        except Exception as e:
            error_type = self._analyze_exception(e)
            self._handle_error(error_type, url, str(e), series_id=series_id, episode_id=episode_id, html_content=html if 'html' in locals() else None)
            return None
    
    def _extract_iframe_src(self, html):
        """机械地查找iframe的src完整引用或script中的m3u8地址"""
        try:
            from bs4 import BeautifulSoup
            import re
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # 方法1: 优先查找 id="playframe" 的iframe（这是真正的播放器）
            playframe = soup.find('iframe', {'id': 'playframe'})
            if playframe:
                iframe_src = playframe.get('src', '')
                if iframe_src:
                    logger.info(f"✓ 找到playframe iframe src: {iframe_src}")
                    return iframe_src
            
            # 方法2: 查找name="playframe"的iframe
            playframe_by_name = soup.find('iframe', {'name': 'playframe'})
            if playframe_by_name:
                iframe_src = playframe_by_name.get('src', '')
                if iframe_src:
                    logger.info(f"✓ 找到playframe iframe (by name) src: {iframe_src}")
                    return iframe_src
            
            # 方法3: 查找所有iframe元素
            iframes = soup.find_all('iframe')
            logger.debug(f"找到 {len(iframes)} 个iframe元素")
            
            for i, iframe in enumerate(iframes):
                iframe_src = iframe.get('src', '')
                iframe_id = iframe.get('id', '')
                iframe_name = iframe.get('name', '')
                
                if iframe_src:
                    logger.debug(f"iframe[{i}] - id: {iframe_id}, name: {iframe_name}, src: {iframe_src}")
                    # 如果是第一个有src的iframe，返回它
                    if i == 0:
                        logger.info(f"✓ 返回第一个iframe src: {iframe_src}")
                        return iframe_src
            
            # 方法4: 从JavaScript中提取iframe链接
            iframe_url = self._extract_iframe_from_js(html)
            if iframe_url:
                logger.info(f"✓ 从JavaScript中提取到iframe地址: {iframe_url}")
                return iframe_url
            
            # 方法5: 查找script标签中的m3u8地址
            scripts = soup.find_all('script')
            for script in scripts:
                script_content = script.string
                if script_content:
                    # 查找url = "m3u8地址"的模式
                    url_match = re.search(r'url\s*=\s*["\']([^"\']*\.m3u8[^"\']*)["\']', script_content)
                    if url_match:
                        m3u8_url = url_match.group(1)
                        # 转换为m3u8player.org播放器地址
                        player_url = self._convert_m3u8_to_player_url(m3u8_url)
                        logger.info(f"✓ 找到script中的m3u8地址并转换为播放器: {player_url}")
                        return player_url
            
            # 方法6: 查找script标签中的视频ID并构建播放地址
            video_id = self._extract_video_id_from_script(html)
            if video_id:
                logger.info(f"✓ 找到视频ID: {video_id}")
                # 尝试构建播放地址
                play_url = self._build_play_url_from_video_id(video_id)
                if play_url:
                    logger.info(f"✓ 从视频ID构建播放地址: {play_url}")
                    return play_url
            
            # 如果没有找到任何播放地址，返回None
            logger.debug("未找到任何iframe或m3u8地址")
            return None
            
        except Exception as e:
            logger.error(f"提取播放地址失败: {e}")
            return None
    
    def _extract_video_id_from_script(self, html):
        """从JavaScript中提取视频ID"""
        try:
            import re
            
            # 查找url = "v_xxxxx"的模式（原有格式）
            url_match = re.search(r'url\s*=\s*["\'](v_[a-zA-Z0-9_]+)["\']', html)
            if url_match:
                video_id = url_match.group(1)
                return video_id
            
            # 查找url = "字母+数字"的模式（新格式）
            url_match_new = re.search(r'url\s*=\s*["\']([a-zA-Z][a-zA-Z0-9]{10,})["\']', html)
            if url_match_new:
                video_id = url_match_new.group(1)
                return video_id
            
            # 查找其他可能的视频ID模式（v_格式）
            video_id_match = re.search(r'["\'](v_[a-zA-Z0-9_]+)["\']', html)
            if video_id_match:
                video_id = video_id_match.group(1)
                return video_id
            
            # 查找其他可能的视频ID模式（字母+数字格式）
            video_id_match_new = re.search(r'["\']([a-zA-Z][a-zA-Z0-9]{10,})["\']', html)
            if video_id_match_new:
                video_id = video_id_match_new.group(1)
                return video_id
            
            return None
            
        except Exception as e:
            logger.debug(f"提取视频ID失败: {e}")
            return None
    
    def _build_play_url_from_video_id(self, video_id):
        """从视频ID构建播放地址"""
        try:
            # 判断视频ID格式
            if video_id.startswith('v_'):
                # v_格式：使用原有的模板
                templates = [
                    f"https://v.cdnlz22.com/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2025/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2024/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2023/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2022/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2021/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2020/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2019/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2018/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2017/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2016/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2015/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2014/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2013/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2012/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2011/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2010/{video_id}/index.m3u8",
                ]
            else:
                # 字母+数字格式：使用新的模板
                templates = [
                    f"https://v.cdnlz22.com/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2025/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2024/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2023/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2022/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2021/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2020/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2019/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2018/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2017/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2016/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2015/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2014/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2013/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2012/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2011/{video_id}/index.m3u8",
                    f"https://v.cdnlz22.com/2010/{video_id}/index.m3u8",
                ]
            
            # 获取m3u8地址
            m3u8_url = templates[0]
            
            # 使用m3u8player.org的在线播放器
            player_url = f"https://m3u8player.org/player.html?url={m3u8_url}"
            
            return player_url
            
        except Exception as e:
            logger.debug(f"构建播放地址失败: {e}")
            return None
    
    def _convert_m3u8_to_player_url(self, m3u8_url):
        """将m3u8地址转换为m3u8player.org播放器地址"""
        try:
            if m3u8_url and '.m3u8' in m3u8_url:
                # 移除&next=参数
                if '&next=' in m3u8_url:
                    m3u8_url = m3u8_url.split('&next=')[0]
                
                # 使用m3u8player.org的在线播放器
                player_url = f"https://m3u8player.org/player.html?url={m3u8_url}"
                return player_url
            
            return m3u8_url
            
        except Exception as e:
            logger.debug(f"转换播放器地址失败: {e}")
            return m3u8_url
    
    def _extract_episode_number(self, episode_text):
        """从剧集文本中提取集数数字"""
        try:
            import re
            
            # 尝试提取数字
            number_match = re.search(r'(\d+)', episode_text)
            if number_match:
                return number_match.group(1)
            
            return None
            
        except Exception as e:
            logger.debug(f"提取集数失败: {e}")
            return None
    
    def _infer_episode_play_url(self, series_url, episode_text, series_id):
        """推理剧集播放URL (play0-集数.html格式)"""
        try:
            # 提取集数
            episode_number = self._extract_episode_number(episode_text)
            if not episode_number:
                # 如果没有数字，尝试其他方式
                if episode_text in ['1-LZ', '2-LZ', '3-LZ']:
                    episode_number = episode_text.split('-')[0]
                else:
                    logger.debug(f"无法从'{episode_text}'中提取集数")
                    return None
            
            # 去掉前导0，转换为纯数字
            episode_num = str(int(episode_number))
            
            # 构建正确的播放URL格式：/m数字id/play片源id-剧集集数.html
            play_url = f"https://www.yatu.tv/m{series_id}/play0-{episode_num}.html"
            logger.debug(f"推理播放URL: {play_url}")
            return play_url
            
        except Exception as e:
            logger.error(f"推理播放URL失败: {e}")
            return None
    
    def _extract_m3u8_from_iframe(self, html):
        """从HTML中的iframe提取m3u8地址，专注于playframe"""
        try:
            from bs4 import BeautifulSoup
            from urllib.parse import urlparse, parse_qs, unquote, urljoin
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # 优先查找 id="playframe" 的iframe（这是真正的播放器）
            playframe = soup.find('iframe', {'id': 'playframe'})
            if playframe:
                src = playframe.get('src', '')
                logger.info(f"找到playframe iframe: {src}")
                
                if src and '.m3u8' in src:
                    logger.info(f"playframe中发现m3u8地址: {src}")
                    return self._extract_m3u8_from_url(src)
                elif src:
                    # 获取playframe的内容
                    logger.info("playframe src不直接包含m3u8，获取iframe内容...")
                    return self._fetch_iframe_content(src)
            
            # 如果没有找到playframe，查找其他可能的播放iframe
            potential_play_iframes = soup.find_all('iframe', {'name': 'playframe'})
            if not potential_play_iframes:
                potential_play_iframes = soup.find_all('iframe', attrs={'id': lambda x: x and 'play' in x.lower()})
            
            if potential_play_iframes:
                logger.info(f"找到 {len(potential_play_iframes)} 个可能的播放iframe")
                for iframe in potential_play_iframes:
                    src = iframe.get('src', '')
                    iframe_id = iframe.get('id', '')
                    iframe_name = iframe.get('name', '')
                    
                    logger.debug(f"检查iframe - id: {iframe_id}, name: {iframe_name}")
                    
                    if src and '.m3u8' in src:
                        logger.info(f"在iframe中发现m3u8地址: {src}")
                        return self._extract_m3u8_from_url(src)
                    elif src:
                        m3u8_url = self._fetch_iframe_content(src)
                        if m3u8_url:
                            return m3u8_url
            
            # 最后查找所有iframe作为备选
            all_iframes = soup.find_all('iframe')
            logger.debug(f"总共找到 {len(all_iframes)} 个iframe元素")
            
            for i, iframe in enumerate(all_iframes):
                src = iframe.get('src', '')
                iframe_id = iframe.get('id', '')
                
                # 跳过已经检查过的iframe
                if iframe_id == 'playframe' or iframe.get('name') == 'playframe':
                    continue
                
                if src and '.m3u8' in src:
                    logger.info(f"在backup iframe[{i}] (id:{iframe_id}) 中发现m3u8: {src}")
                    return self._extract_m3u8_from_url(src)
            
            return None
            
        except Exception as e:
            logger.error(f"从iframe提取m3u8失败: {e}")
            return None
    
    def _extract_m3u8_from_url(self, url):
        """从URL中提取m3u8地址"""
        try:
            from urllib.parse import urlparse, parse_qs, unquote
            
            logger.debug(f"解析URL: {url}")
            
            # 解析URL参数
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            
            # 查找包含m3u8的参数
            for param_name, param_values in query_params.items():
                for param_value in param_values:
                    if '.m3u8' in param_value:
                        # URL解码
                        decoded_url = unquote(param_value)
                        logger.info(f"从URL参数 '{param_name}' 提取到m3u8: {decoded_url}")
                        return decoded_url
            
            # 如果参数中没找到，尝试直接从URL路径提取
            if '.m3u8' in parsed_url.path:
                full_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
                if parsed_url.query:
                    full_url += f"?{parsed_url.query}"
                logger.info(f"从URL路径提取到m3u8: {full_url}")
                return full_url
            
            # 使用正则表达式提取
            m3u8_patterns = [
                r'url=([^&]*\.m3u8[^&]*)',
                r'(https://[^&\s]*\.m3u8[^&]*)',
                r'([^&\s]*\.m3u8[^&]*)',
            ]
            
            for pattern in m3u8_patterns:
                matches = re.findall(pattern, url, re.IGNORECASE)
                for match in matches:
                    decoded_url = unquote(match)
                    if decoded_url.endswith('.m3u8'):
                        logger.info(f"通过正则从URL提取到m3u8: {decoded_url}")
                        return decoded_url
            
            return None
            
        except Exception as e:
            logger.error(f"从URL提取m3u8失败: {e}")
            return None
    
    def _fetch_iframe_content(self, iframe_src):
        """获取iframe内容并分析"""
        try:
            from urllib.parse import urljoin, urlparse, parse_qs, unquote
            from bs4 import BeautifulSoup
            
            # 构建完整的iframe URL
            iframe_url = urljoin(self.base_url, iframe_src)
            logger.debug(f"正在获取iframe内容: {iframe_url}")
            
            # 获取iframe内容
            iframe_html = self.get_page(iframe_url)
            if not iframe_html:
                return None
            
            # 检查iframe内容是否包含m3u8
            if '.m3u8' in iframe_html:
                logger.info("iframe内容包含m3u8字符串!")
                
                # 使用正则表达式提取iframe中的m3u8
                patterns = [
                    r'src\s*=\s*["\']([^"\']*\.m3u8[^"\']*)',
                    r'url\s*=\s*["\']([^"\']*\.m3u8[^"\']*)', 
                    r'(https://[^\s"\']*\.m3u8[^\s"\']*)',
                    r'([^\s"\']*\.m3u8[^\s"\']*)',
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, iframe_html, re.IGNORECASE)
                    for match in matches:
                        decoded_url = unquote(match)
                        if decoded_url.endswith('.m3u8'):
                            logger.info(f"从iframe内容中提取到m3u8: {decoded_url}")
                            return decoded_url
            
            # 查找iframe内的嵌套iframe
            iframe_soup = BeautifulSoup(iframe_html, 'html.parser')
            nested_iframes = iframe_soup.find_all('iframe')
            
            if nested_iframes:
                logger.debug(f"iframe内发现 {len(nested_iframes)} 个嵌套iframe")
                for j, nested_iframe in enumerate(nested_iframes):
                    nested_src = nested_iframe.get('src', '')
                    nested_id = nested_iframe.get('id', '')
                    logger.debug(f"嵌套iframe[{j}] - id: {nested_id}, src: {nested_src}")
                    
                    if nested_src and '.m3u8' in nested_src:
                        logger.info(f"嵌套iframe包含m3u8: {nested_src}")
                        
                        # 解析嵌套iframe的URL参数
                        parsed_url = urlparse(nested_src)
                        query_params = parse_qs(parsed_url.query)
                        
                        for param_name, param_values in query_params.items():
                            for param_value in param_values:
                                if '.m3u8' in param_value:
                                    decoded_url = unquote(param_value)
                                    logger.info(f"从嵌套iframe参数 '{param_name}' 提取到m3u8: {decoded_url}")
                                    return decoded_url
                    
                    elif nested_src:
                        # 递归获取嵌套iframe内容（限制递归深度避免无限循环）
                        nested_m3u8 = self._fetch_iframe_content(nested_src)
                        if nested_m3u8:
                            return nested_m3u8
            
            return None
            
        except Exception as e:
            logger.error(f"获取iframe内容失败: {e}")
            return None
    
    def _extract_m3u8_from_regex(self, html, play_url):
        """使用正则表达式从HTML中提取m3u8地址（备用方法）"""
        try:
            # 重点：查找JavaScript中的url变量（这是真正的m3u8地址所在）
            js_url_patterns = [
                r'url\s*=\s*"([^"]*\.m3u8[^"&]*)',  # JavaScript: url ="xxx.m3u8"
                r'url\s*=\s*["\']([^"\']*\.m3u8[^"\'&]*)',  # JavaScript: url = "xxx.m3u8"
            ]
            
            # 先查找JavaScript中的url变量
            for pattern in js_url_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                for match in matches:
                    # 清理URL，移除可能的额外参数
                    clean_url = match.split('&')[0]  # 去掉&next=xxx部分
                    if clean_url.endswith('.m3u8'):
                        logger.info(f"✓ 从JavaScript url变量找到m3u8地址: {clean_url}")
                        return clean_url
            
            # 备用方案：使用其他正则表达式查找m3u8地址
            backup_patterns = [
                r'["\']([^"\']*high25-playback[^"\']*\.m3u8[^"\'&]*)',  # 特定域名模式
                r'(https://[^"\'&\s]*\.m3u8)',  # 查找https开头的m3u8
                r'["\']([^"\']*\.m3u8[^"\'&]*)',  # 通用m3u8模式
            ]
            
            # 先查找包含m3u8的行进行调试
            lines = html.split('\n')
            m3u8_lines = []
            for i, line in enumerate(lines):
                if 'm3u8' in line.lower():
                    m3u8_lines.append((i+1, line.strip()))
            
            if m3u8_lines:
                logger.debug(f"找到{len(m3u8_lines)}行包含m3u8的内容")
                for line_num, line_content in m3u8_lines[:3]:  # 只显示前3行
                    logger.debug(f"  第{line_num}行: {line_content[:100]}")
            
            for pattern in backup_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                for match in matches:
                    # 清理URL，移除可能的额外参数
                    clean_url = match.split('&')[0]  # 去掉&next=xxx部分
                    if clean_url.endswith('.m3u8'):
                        logger.info(f"通过备用正则找到m3u8地址: {clean_url}")
                        return clean_url
            
            return None
            
        except Exception as e:
            logger.error(f"正则表达式提取m3u8失败: {e}")
            return None
    
    def save_series_data(self, series_info):
        """保存剧集数据到文件"""
        series_id = series_info['series_id']
        series_dir = os.path.join(self.data_dir, series_id)
        
        if not os.path.exists(series_dir):
            os.makedirs(series_dir)
        
        # 保存 JSON 数据
        json_file = os.path.join(series_dir, 'info.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(series_info, f, ensure_ascii=False, indent=2)
        
        # 生成剧集的 HTML 页面
        self.generate_series_html(series_info, series_dir)
        
        logger.info(f"剧集数据已保存到: {series_dir}")
    
    def generate_series_html(self, series_info, series_dir):
        """为剧集生成HTML播放页面"""
        series_id = series_info['series_id']
        title = series_info['title']
        cover_image = series_info.get('cover_image', '')
        description = series_info.get('description', '')
        meta_info = series_info.get('meta_info', {})
        episodes = series_info.get('episodes', [])
        
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Microsoft YaHei', 'PingFang SC', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
        }}
        
        .series-info {{
            display: flex;
            gap: 30px;
            align-items: flex-start;
        }}
        
        .cover-container {{
            flex-shrink: 0;
        }}
        
        .cover-image {{
            width: 200px;
            height: 280px;
            object-fit: cover;
            border-radius: 10px;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
            transition: transform 0.3s ease;
        }}
        
        .cover-image:hover {{
            transform: scale(1.05);
        }}
        
        .no-cover {{
            width: 200px;
            height: 280px;
            background: linear-gradient(45deg, #f0f0f0, #e0e0e0);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #999;
            font-size: 14px;
            text-align: center;
            border: 2px dashed #ccc;
        }}
        
        .details {{
            flex: 1;
        }}
        
        .title {{
            font-size: 2.5em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 15px;
            line-height: 1.2;
        }}
        
        .meta-tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 20px;
        }}
        
        .tag {{
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: 500;
        }}
        
        .description {{
            color: #555;
            line-height: 1.6;
            font-size: 1.1em;
            margin-bottom: 20px;
        }}
        
        .stats {{
            display: flex;
            gap: 30px;
        }}
        
        .stat-item {{
            text-align: center;
        }}
        
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
            display: block;
        }}
        
        .stat-label {{
            color: #666;
            font-size: 0.9em;
        }}
        
        .episodes-section {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
        }}
        
        .section-title {{
            font-size: 1.8em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 25px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .section-title::before {{
            content: "🎬";
            font-size: 1.2em;
        }}
        
        .episodes-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 20px;
        }}
        
        .episode-card {{
            background: #fff;
            border-radius: 12px;
            padding: 20px;
            border: 2px solid transparent;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }}
        
        .episode-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            transform: scaleX(0);
            transition: transform 0.3s ease;
        }}
        
        .episode-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
            border-color: #667eea;
        }}
        
        .episode-card:hover::before {{
            transform: scaleX(1);
        }}
        
        .episode-number {{
            font-size: 1.3em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 10px;
        }}
        
        .episode-info {{
            margin-bottom: 15px;
        }}
        
        .video-source {{
            display: inline-block;
            background: #e8f4f8;
            color: #2c3e50;
            padding: 4px 10px;
            border-radius: 15px;
            font-size: 0.85em;
            margin-bottom: 8px;
        }}
        
        .play-buttons {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        
        .play-btn {{
            padding: 10px 15px;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            text-align: center;
            font-weight: 500;
            transition: all 0.3s ease;
            font-size: 0.9em;
        }}
        
        .btn-primary {{
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
        }}
        
        .btn-primary:hover {{
            background: linear-gradient(45deg, #5a6fd8, #6a4190);
            transform: scale(1.05);
        }}
        
        .btn-secondary {{
            background: #f8f9fa;
            color: #6c757d;
            border: 1px solid #dee2e6;
        }}
        
        .btn-secondary:hover {{
            background: #e9ecef;
            color: #495057;
        }}
        
        .playframe-found {{
            border-left: 4px solid #28a745;
        }}
        
        .btn-disabled {{
            background: #f8f9fa;
            color: #6c757d;
            border: 1px solid #dee2e6;
            cursor: not-allowed;
            opacity: 0.6;
        }}
        
        .note {{
            font-size: 0.8em;
            color: #666;
            margin-top: 8px;
            font-style: italic;
        }}
        
        .back-btn {{
            position: fixed;
            top: 20px;
            left: 20px;
            background: rgba(255, 255, 255, 0.9);
            color: #667eea;
            padding: 10px 20px;
            border-radius: 25px;
            text-decoration: none;
            font-weight: 500;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
            border: 2px solid transparent;
        }}
        
        .back-btn:hover {{
            background: #667eea;
            color: white;
            transform: scale(1.05);
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 15px;
            }}
            
            .series-info {{
                flex-direction: column;
                text-align: center;
            }}
            
            .title {{
                font-size: 2em;
            }}
            
            .episodes-grid {{
                grid-template-columns: 1fr;
            }}
            
            .stats {{
                justify-content: center;
            }}
        }}
    </style>
</head>
<body>
    <a href="../index.html" class="back-btn">← 返回首页</a>
    
    <div class="container">
        <div class="header">
            <div class="series-info">
                <div class="cover-container">"""
        
        # 检查是否有本地保存的封面图片
        cover_filename = None
        for ext in ['.jpg', '.png', '.gif', '.webp']:
            cover_path = os.path.join(series_dir, f"cover{ext}")
            if os.path.exists(cover_path):
                cover_filename = f"cover{ext}"
                break
        
        if cover_filename:
            html_content += f'''
                    <img src="{cover_filename}" alt="{title}" class="cover-image" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex'">
                    <div class="no-cover" style="display:none">
                        <div>暂无封面<br>📺</div>
                    </div>'''
        else:
            html_content += '''
                    <div class="no-cover">
                        <div>暂无封面<br>📺</div>
                    </div>'''
        
        html_content += f'''
                </div>
                
                <div class="details">
                    <h1 class="title">{title}</h1>
                    
                    <div class="meta-tags">'''
        
        # 添加元信息标签
        if meta_info.get('year'):
            html_content += f'<span class="tag">{meta_info["year"]}</span>'
        
        if meta_info.get('categories'):
            for category in meta_info['categories'][:3]:  # 最多显示3个分类
                html_content += f'<span class="tag">{category}</span>'
        
        if meta_info.get('director'):
            html_content += f'<span class="tag">导演: {meta_info["director"]}</span>'
        
        html_content += f'''
                    </div>
                    
                    <div class="description">
                        {description if description else "暂无剧集介绍"}
                    </div>
                    
                    <div class="stats">
                        <div class="stat-item">
                            <span class="stat-number">{len(episodes)}</span>
                            <span class="stat-label">总集数</span>
                        </div>

                        <div class="stat-item">
                            <span class="stat-number">{series_info.get('crawl_time', '').split(' ')[0]}</span>
                            <span class="stat-label">更新日期</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="episodes-section">
            <h2 class="section-title">剧集列表</h2>
            
            <div class="episodes-grid">'''
        
        # 生成剧集卡片
        for episode in episodes:
            episode_num = episode.get('episode', '未知')
            video_source = episode.get('video_source', '未知')
            playframe_url = episode.get('playframe_url')
            note = episode.get('note', '')
            
            card_class = "episode-card"
            if playframe_url:
                card_class += " playframe-found"
            
            html_content += f'''
                <div class="{card_class}">
                    <div class="episode-number">第 {episode_num} 集</div>
                    
                    <div class="episode-info">
                    </div>
                    
                    <div class="play-buttons">'''
            
            # 只显示playframe播放按钮
            if playframe_url:
                html_content += f'''
                        <a href="{playframe_url}" class="play-btn btn-primary" target="_blank">
                            🎬 播放器页面
                        </a>'''
            else:
                html_content += f'''
                        <div class="play-btn btn-disabled">
                            ❌ 无播放地址
                        </div>'''
            
            html_content += '</div>'
            

            
            html_content += '</div>'
        
        html_content += '''
            </div>
        </div>
    </div>
    
    <script>
        // 点击统计
        document.querySelectorAll('.play-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                console.log('播放:', this.textContent, this.href);
            });
        });
        
        // 图片加载错误处理
        document.querySelectorAll('.cover-image').forEach(img => {
            img.addEventListener('error', function() {
                this.style.display = 'none';
                const noCover = this.nextElementSibling;
                if (noCover && noCover.classList.contains('no-cover')) {
                    noCover.style.display = 'flex';
                }
            });
        });
    </script>
</body>
</html>'''
        
        # 保存HTML文件
        html_file = os.path.join(series_dir, 'index.html')
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"剧集HTML页面已生成: {html_file}")
    
    def generate_index_html(self, categories_data):
        """生成首页 HTML 文件"""
        logger.info("正在生成 index.html...")
        
        html_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>雅图在线 - 抓取数据</title>
    <style>
        body {
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }
        .update-time {
            margin-top: 10px;
            opacity: 0.9;
            font-size: 14px;
        }
        .category {
            margin: 0;
            border-bottom: 1px solid #eee;
        }
        .category:last-child {
            border-bottom: none;
        }
        .category-header {
            background-color: #f8f9fa;
            padding: 20px 30px;
            border-left: 4px solid;
            position: relative;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .category-header:hover {
            background-color: #e9ecef;
        }
        .anime .category-header { border-left-color: #ff6b6b; }
        .movie .category-header { border-left-color: #4ecdc4; }
        .tv .category-header { border-left-color: #45b7d1; }
        
        .category-title {
            font-size: 1.5em;
            font-weight: 600;
            margin: 0;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .item-count {
            background: rgba(0,0,0,0.1);
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: normal;
        }
        .toggle-icon {
            transition: transform 0.3s ease;
        }
        .category.collapsed .toggle-icon {
            transform: rotate(-90deg);
        }
        .items-container {
            padding: 0 30px 30px;
            transition: all 0.3s ease;
        }
        .category.collapsed .items-container {
            display: none;
        }
        .items-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .item {
            background: #fff;
            border: 1px solid #eee;
            border-radius: 8px;
            padding: 20px;
            transition: all 0.3s ease;
            position: relative;
        }
        .item:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            border-color: #ddd;
        }
        .item-title {
            font-size: 1.1em;
            font-weight: 600;
            margin-bottom: 10px;
            color: #2c3e50;
        }
        .item-title a {
            text-decoration: none;
            color: inherit;
        }
        .item-title a:hover {
            color: #3498db;
        }
        .item-info {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #f0f0f0;
        }
        .episode-info {
            background: #e3f2fd;
            color: #1565c0;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.9em;
            font-weight: 500;
        }
        .update-date {
            color: #666;
            font-size: 0.9em;
        }
        .stats {
            display: flex;
            justify-content: space-around;
            padding: 20px;
            background: #f8f9fa;
            margin: 20px 0;
        }
        .stat-item {
            text-align: center;
        }
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #3498db;
        }
        .stat-label {
            color: #666;
            margin-top: 5px;
        }
        @media (max-width: 768px) {
            .items-grid {
                grid-template-columns: 1fr;
            }
            .container {
                margin: 10px;
            }
            .header {
                padding: 20px;
            }
            .header h1 {
                font-size: 2em;
            }
        }
    </style>
    <script>
        function toggleCategory(element) {
            element.classList.toggle('collapsed');
        }
        
        document.addEventListener('DOMContentLoaded', function() {
            // 添加点击事件
            document.querySelectorAll('.category-header').forEach(header => {
                header.addEventListener('click', function() {
                    toggleCategory(this.parentElement);
                });
            });
        });
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎬 雅图在线数据抓取</h1>
            <div class="update-time">更新时间: """ + datetime.now().strftime('%Y年%m月%d日 %H:%M:%S') + """</div>
        </div>
        
        <div class="stats">
"""
        
        # 计算统计数据
        total_anime = len(categories_data.get('sin1', {}).get('items', []))
        total_movie = len(categories_data.get('sin2', {}).get('items', []))
        total_tv = len(categories_data.get('sin3', {}).get('items', []))
        total_all = total_anime + total_movie + total_tv
        
        html_content += f"""
            <div class="stat-item">
                <div class="stat-number">{total_all}</div>
                <div class="stat-label">总计</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{total_anime}</div>
                <div class="stat-label">动漫</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{total_movie}</div>
                <div class="stat-label">电影</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{total_tv}</div>
                <div class="stat-label">电视剧</div>
            </div>
        </div>
"""
        
        # 生成各分类内容
        category_classes = {'sin1': 'anime', 'sin2': 'movie', 'sin3': 'tv'}
        
        for category_id, category_info in categories_data.items():
            class_name = category_classes.get(category_id, '')
            items = category_info.get('items', [])
            
            html_content += f"""
        <div class="category {class_name}">
            <div class="category-header">
                <h2 class="category-title">
                    {category_info['name']}
                    <span class="item-count">{len(items)} 部</span>
                    <span class="toggle-icon">▼</span>
                </h2>
            </div>
            <div class="items-container">
                <div class="items-grid">
"""
            
            for item in items:
                # 构建剧集HTML页面链接
                series_html_url = f"{item['series_id']}/index.html" if item['series_id'] else item['url']
                
                html_content += f"""
                    <div class="item">
                        <div class="item-title">
                            <a href="{series_html_url}" target="_blank">{item['title']}</a>
                        </div>
                        <div class="item-info">
                            <span class="episode-info">{item['episode_info']}</span>
                            <span class="update-date">{item['update_date']}</span>
                        </div>

                    </div>
"""
            
            html_content += """
                </div>
            </div>
        </div>
"""
        
        html_content += """
    </div>
</body>
</html>
"""
        
        # 保存 HTML 文件
        html_file = os.path.join(self.data_dir, 'index.html')
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML 文件已生成: {html_file}")
    
    def run(self, use_category_pages=True, use_multithread_crawl=False, check_missing=True):
        """主运行函数"""
        logger.info("=== 雅图TV抓取工具启动 ===")
        logger.info("目标网站: https://www.yatu.tv")
        logger.info("抓取内容: 动漫、电影、电视剧列表及详情")
        logger.info("数据保存: data/ 目录")
        logger.info("=" * 50)
        
        if use_multithread_crawl:
            # 使用多线程剧集采集模式
            logger.info("使用多线程剧集采集模式")
            self.run_multithread_crawl()
            return
        
        # 第一步：抓取最新内容（首页）
        logger.info("=== 第一步：抓取最新内容 ===")
        logger.info("使用首页抓取模式获取最新剧集")
        homepage_data = self.crawl_homepage()
        
        if not homepage_data:
            logger.error("首页抓取失败")
            return
        
        # 生成首页HTML
        self.generate_index_html(homepage_data)
        
        # 显示首页抓取结果
        logger.info("=== 首页抓取汇总 ===")
        for category_name, category_info in homepage_data.items():
            items = category_info.get('items', [])
            logger.info(f"{category_name}: {len(items)} 部剧集")
            for item in items:
                logger.info(f"  - {item['title']} -> {item['url']}")
        
        # 收集首页剧集
        homepage_series = []
        homepage_urls = set()
        for category_name, category_info in homepage_data.items():
            for item in category_info.get('items', []):
                homepage_series.append({
                    'item': item,
                    'category_name': category_name,
                    'source': 'homepage'
                })
                homepage_urls.add(item['url'])
        
        # 第二步：检查是否有遗漏（如果启用）
        if check_missing and use_category_pages:
            logger.info("=== 第二步：检查遗漏内容 ===")
            logger.info("使用分类页面抓取模式检查是否有遗漏的剧集")
            
            categories_data = self.crawl_all_categories()
            
            if categories_data:
                # 收集分类页面剧集
                category_series = []
                category_urls = set()
                for category_name, category_info in categories_data.items():
                    for item in category_info.get('items', []):
                        category_series.append({
                            'item': item,
                            'category_name': category_name,
                            'source': 'category'
                        })
                        category_urls.add(item['url'])
                
                # 找出遗漏的剧集
                missing_urls = category_urls - homepage_urls
                missing_series = [s for s in category_series if s['item']['url'] in missing_urls]
                
                if missing_series:
                    logger.info(f"发现 {len(missing_series)} 个遗漏的剧集")
                    logger.info("=== 遗漏剧集列表 ===")
                    for series in missing_series:
                        logger.info(f"  - {series['item']['title']} -> {series['item']['url']} ({series['category_name']})")
                    
                    # 将遗漏的剧集添加到总列表中
                    homepage_series.extend(missing_series)
                    logger.info(f"总共需要抓取 {len(homepage_series)} 个剧集（首页 {len(homepage_urls)} + 遗漏 {len(missing_series)}）")
                else:
                    logger.info("没有发现遗漏的剧集，所有剧集都已包含在首页中")
            else:
                logger.warning("分类页面抓取失败，仅使用首页数据")
        else:
            logger.info("跳过遗漏检查，仅使用首页数据")
        
        # 第三步：抓取所有剧集详情
        logger.info("=== 第三步：抓取剧集详情 ===")
        logger.info(f"使用多级线程池模式:")
        logger.info(f"  - 剧集级线程池: {self.max_series_workers} 个线程")
        logger.info(f"  - 集数级线程池: {self.max_episode_workers} 个线程")
        logger.info(f"  - 批处理大小: {self.batch_size} 个剧集")
        logger.info(f"  - 内存限制: {self.memory_limit_mb}MB")
        
        # 统计信息
        total_count = len(homepage_series)
        self.stats['total_series'] = total_count
        
        # 过滤无效剧集
        valid_series = []
        for series_data in homepage_series:
            item = series_data['item']
            series_id = item['series_id']
            
            if not series_id:
                logger.warning(f"跳过空剧集ID: {item['title']}")
                continue
            
            # 检查series_id是否包含无效文件名字符
            invalid_chars = ['?', '&', '=', '<', '>', ':', '"', '|', '*']
            if any(char in series_id for char in invalid_chars):
                logger.warning(f"跳过包含无效字符的剧集ID '{series_id}': {item['title']}")
                continue
            
            valid_series.append(series_data)
        
        # 分批处理剧集，避免内存占用过高
        self.crawl_series_in_batches(valid_series, total_count)
        
        # 输出统计信息
        logger.info("=== 抓取统计 ===")
        logger.info(f"跳过的newplay.asp链接: {self.stats['skipped_newplay']} 个")
        logger.info(f"总剧集数量: {self.stats['total_series']} 个")
        logger.info(f"成功抓取剧集: {self.stats['successful_series']} 个")
        logger.info(f"失败剧集数量: {self.stats['total_series'] - self.stats['successful_series']} 个")
        
        # 错误统计
        if self.stats['total_failures'] > 0:
            logger.info("=== 错误统计 ===")
            logger.info(f"总失败次数: {self.stats['total_failures']}")
            logger.info(f"网络错误: {self.stats['network_errors']}")
            logger.info(f"认证错误: {self.stats['auth_errors']}")
            logger.info(f"频率限制: {self.stats['rate_limit_errors']}")
            logger.info(f"服务器错误: {self.stats['server_errors']}")
            
            # 错误分析建议
            if self.stats['auth_errors'] > 0:
                logger.warning("建议: 检测到认证错误，可能需要登录或处理验证码")
            if self.stats['rate_limit_errors'] > 0:
                logger.warning("建议: 检测到频率限制，建议增加请求间隔时间")
            if self.stats['server_errors'] > 0:
                logger.warning("建议: 检测到服务器错误，服务器可能维护中，建议稍后重试")
            if self.stats['network_errors'] > 0:
                logger.warning("建议: 检测到网络错误，请检查网络连接")
        
        logger.info("=== 抓取完成 ===")

    def crawl_series_in_batches(self, all_series, total_count):
        """分批处理剧集，避免内存占用过高"""
        logger.info(f"开始分批处理 {len(all_series)} 个剧集，每批 {self.batch_size} 个")
        
        batch_data = []  # 当前批次的数据
        completed_count = 0
        failed_count = 0
        
        # 显示初始内存使用情况
        initial_memory = self.get_memory_usage()
        logger.info(f"初始内存使用: {initial_memory:.1f}MB")
        
        for i in range(0, len(all_series), self.batch_size):
            batch = all_series[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (len(all_series) + self.batch_size - 1) // self.batch_size
            
            logger.info(f"=== 处理第 {batch_num}/{total_batches} 批 ({len(batch)} 个剧集) ===")
            
            # 检查内存使用情况
            current_memory = self.get_memory_usage()
            logger.info(f"当前内存使用: {current_memory:.1f}MB")
            
            if self.check_memory_limit():
                logger.warning("内存使用过高，强制清理内存")
                self.clear_memory()
            
            # 处理当前批次
            batch_results = self.process_batch(batch, completed_count, total_count)
            
            # 收集成功的结果
            for result in batch_results:
                if result['success']:
                    batch_data.append(result['data'])
                    completed_count += 1
                else:
                    failed_count += 1
            
            # 定期保存数据
            if len(batch_data) >= self.save_interval:
                self.save_batch_data(batch_data)
                batch_data = []  # 清空批次数据
            
            # 定期垃圾回收
            if self.processed_count % self.gc_interval == 0:
                logger.info("执行定期垃圾回收...")
                self.force_garbage_collection()
            
            # 批次间暂停，避免请求过快
            if batch_num < total_batches:
                logger.info("批次间暂停 2 秒...")
                time.sleep(2)
        
        # 保存剩余的数据
        if batch_data:
            self.save_batch_data(batch_data)
        
        # 最终内存清理
        self.clear_memory()
        
        # 显示最终统计
        final_memory = self.get_memory_usage()
        logger.info(f"=== 分批处理完成 ===")
        logger.info(f"总剧集数: {total_count}")
        logger.info(f"成功处理: {completed_count}")
        logger.info(f"失败数量: {failed_count}")
        logger.info(f"最终内存使用: {final_memory:.1f}MB (初始: {initial_memory:.1f}MB)")
    
    def process_batch(self, batch, completed_count, total_count):
        """处理单个批次的剧集"""
        results = []
        
        # 初始化集数级线程池
        self.episode_thread_pool = ThreadPoolExecutor(max_workers=self.max_episode_workers)
        
        try:
            # 使用线程池处理批次
            with ThreadPoolExecutor(max_workers=self.max_series_workers) as executor:
                # 提交所有任务
                future_to_series = {
                    executor.submit(self.crawl_single_series_optimized, series_data, completed_count + i, total_count): series_data 
                    for i, series_data in enumerate(batch)
                }
                
                # 收集结果
                for future in as_completed(future_to_series):
                    series_data = future_to_series[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        logger.error(f"处理剧集异常: {series_data['item']['title']} - {e}")
                        results.append({
                            'success': False,
                            'data': None,
                            'error': str(e)
                        })
        finally:
            # 清理线程池
            if self.episode_thread_pool:
                self.episode_thread_pool.shutdown(wait=True)
                self.episode_thread_pool = None
        
        return results
    
    def crawl_single_series_optimized(self, series_data, current_count, total_count):
        """优化的单个剧集抓取函数"""
        item = series_data['item']
        category_name = series_data['category_name']
        series_id = item['series_id']
        
        # 为每个线程创建独立的session
        thread_session = requests.Session()
        thread_session.headers.update(self.session.headers)
        
        try:
            logger.info(f"[{current_count}/{total_count}] 正在抓取: {item['title']}")
            logger.info(f"详情页地址: {item['url']}")
            
            # 抓取详情，传递分类信息和session
            series_info = self.crawl_series_detail_with_episode_pool(
                item['url'], series_id, item['category'], thread_session
            )
            
            if series_info:
                logger.info(f"✓ 完成: {item['title']} ({len(series_info['episodes'])}集)")
                self.processed_count += 1
                return {
                    'success': True,
                    'data': series_info,
                    'error': None
                }
            else:
                logger.error(f"✗ 失败: {item['title']}")
                return {
                    'success': False,
                    'data': None,
                    'error': '抓取失败'
                }
                
        except Exception as e:
            logger.error(f"✗ 抓取异常: {item['title']} - {str(e)}")
            return {
                'success': False,
                'data': None,
                'error': str(e)
            }
        finally:
            # 清理session
            thread_session.close()

    def crawl_series_with_threads(self, all_series, total_count):
        """使用多级线程池抓取剧集详情"""
        completed_count = 0
        failed_count = 0
        
        # 初始化集数级线程池
        self.episode_thread_pool = ThreadPoolExecutor(max_workers=self.max_episode_workers)
        
        def crawl_single_series(series_data):
            """单个线程抓取剧集的函数"""
            nonlocal completed_count, failed_count
            
            item = series_data['item']
            category_name = series_data['category_name']
            series_id = item['series_id']
            
            # 为每个线程创建独立的session
            thread_session = requests.Session()
            thread_session.headers.update(self.session.headers)
            
            try:
                with self.progress_lock:
                    completed_count += 1
                    current_count = completed_count
                    logger.info(f"[{current_count}/{total_count}] 正在抓取: {item['title']}")
                    logger.info(f"详情页地址: {item['url']}")
                
                # 抓取详情，传递分类信息和session
                series_info = self.crawl_series_detail_with_episode_pool(
                    item['url'], series_id, item['category'], thread_session
                )
                
                if series_info:
                    # 保存数据（需要线程锁保护）
                    with self.thread_lock:
                        self.save_series_data(series_info)
                        self.stats['successful_series'] += 1
                    
                    with self.progress_lock:
                        logger.info(f"✓ 完成: {item['title']} ({len(series_info['episodes'])}集)")
                    return True
                else:
                    with self.progress_lock:
                        logger.error(f"✗ 失败: {item['title']}")
                    with self.thread_lock:
                        failed_count += 1
                    return False
                    
            except Exception as e:
                with self.progress_lock:
                    logger.error(f"✗ 抓取异常: {item['title']} - {str(e)}")
                with self.thread_lock:
                    failed_count += 1
                return False
        
        # 使用剧集级线程池执行抓取任务
        with ThreadPoolExecutor(max_workers=self.max_series_workers) as executor:
            # 提交所有任务
            future_to_series = {
                executor.submit(crawl_single_series, series_data): series_data 
                for series_data in all_series
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_series):
                series_data = future_to_series[future]
                try:
                    success = future.result()
                    if not success:
                        with self.thread_lock:
                            self.stats['total_failures'] += 1
                except Exception as e:
                    with self.progress_lock:
                        logger.error(f"线程执行异常: {series_data['item']['title']} - {str(e)}")
                    with self.thread_lock:
                        self.stats['total_failures'] += 1
        
        # 关闭集数级线程池
        if self.episode_thread_pool:
            self.episode_thread_pool.shutdown(wait=True)
        
        logger.info(f"多级线程池抓取完成！成功: {self.stats['successful_series']}, 失败: {failed_count}")

    def _extract_iframe_from_js(self, html):
        """从JavaScript中提取iframe链接"""
        try:
            import re
            from urllib.parse import urljoin, unquote
            
            logger.debug("正在从JavaScript中提取iframe链接...")
            
            # 查找所有script标签
            script_patterns = [
                r'<script[^>]*>(.*?)</script>',  # 内联脚本
                r'src\s*=\s*["\']([^"\']*\.js[^"\']*)["\']',  # 外部JS文件
            ]
            
            # 方法1: 查找iframe相关的JavaScript代码
            iframe_js_patterns = [
                # 常见的iframe设置模式
                r'iframe\.src\s*=\s*["\']([^"\']*)["\']',
                r'iframe\.setAttribute\(["\']src["\'],\s*["\']([^"\']*)["\']\)',
                r'playframe\.src\s*=\s*["\']([^"\']*)["\']',
                r'playframe\.setAttribute\(["\']src["\'],\s*["\']([^"\']*)["\']\)',
                r'document\.getElementById\(["\']playframe["\']\)\.src\s*=\s*["\']([^"\']*)["\']',
                r'document\.getElementById\(["\']playframe["\']\)\.setAttribute\(["\']src["\'],\s*["\']([^"\']*)["\']\)',
                
                # 变量赋值模式
                r'var\s+\w+\s*=\s*["\']([^"\']*jx\.xmflv\.cc[^"\']*)["\']',
                r'let\s+\w+\s*=\s*["\']([^"\']*jx\.xmflv\.cc[^"\']*)["\']',
                r'const\s+\w+\s*=\s*["\']([^"\']*jx\.xmflv\.cc[^"\']*)["\']',
                
                # 函数调用模式
                r'loadIframe\(["\']([^"\']*)["\']\)',
                r'loadPlayer\(["\']([^"\']*)["\']\)',
                r'setIframeSrc\(["\']([^"\']*)["\']\)',
                
                # 通用URL模式（包含常见播放器域名）
                r'["\'](https?://[^"\']*(?:jx\.xmflv\.cc|player\.|play\.|iframe\.)[^"\']*)["\']',
                r'["\'](https?://[^"\']*\?url=[^"\']*)["\']',
                
                # 更广泛的URL模式
                r'["\'](https?://[^"\']*\.cc[^"\']*)["\']',
                r'["\'](https?://[^"\']*\.com[^"\']*\?url=[^"\']*)["\']',
                r'["\'](https?://[^"\']*\.net[^"\']*\?url=[^"\']*)["\']',
                
                # 相对路径模式
                r'["\'](/[^"\']*\.php[^"\']*\?url=[^"\']*)["\']',
                r'["\'](/[^"\']*\.asp[^"\']*\?url=[^"\']*)["\']',
            ]
            
            # 搜索所有script标签内容
            scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
            logger.debug(f"找到 {len(scripts)} 个script标签")
            
            for i, script_content in enumerate(scripts):
                logger.debug(f"分析script[{i}]内容，长度: {len(script_content)}")
                
                # 尝试各种模式匹配
                for j, pattern in enumerate(iframe_js_patterns):
                    matches = re.findall(pattern, script_content, re.IGNORECASE)
                    for match in matches:
                        if match and len(match) > 10:  # 确保URL长度合理
                            # URL解码
                            decoded_url = unquote(match)
                            logger.debug(f"从JavaScript中找到URL: {decoded_url}")
                            
                            # 验证是否是有效的播放器URL
                            if self._is_valid_player_url(decoded_url):
                                logger.info(f"✓ 从JavaScript中提取到有效播放器URL: {decoded_url}")
                                return decoded_url
                            else:
                                logger.debug(f"URL验证失败: {decoded_url}")
            
            # 方法2: 查找动态生成的iframe
            dynamic_iframe_patterns = [
                r'document\.write\(["\']<iframe[^>]*src=["\']([^"\']*)["\']',
                r'innerHTML\s*=\s*["\']<iframe[^>]*src=["\']([^"\']*)["\']',
                r'appendChild\(.*iframe.*src=["\']([^"\']*)["\']',
            ]
            
            for pattern in dynamic_iframe_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    if match and len(match) > 10:
                        decoded_url = unquote(match)
                        if self._is_valid_player_url(decoded_url):
                            logger.info(f"✓ 从动态iframe中提取到URL: {decoded_url}")
                            return decoded_url
            
            # 方法3: 查找AJAX请求中的URL
            ajax_patterns = [
                r'url\s*:\s*["\']([^"\']*jx\.xmflv\.cc[^"\']*)["\']',
                r'data\s*:\s*\{[^}]*url\s*:\s*["\']([^"\']*)["\']',
            ]
            
            for pattern in ajax_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                for match in matches:
                    if match and len(match) > 10:
                        decoded_url = unquote(match)
                        if self._is_valid_player_url(decoded_url):
                            logger.info(f"✓ 从AJAX请求中提取到URL: {decoded_url}")
                            return decoded_url
            
            logger.debug("JavaScript中未找到有效的iframe链接")
            return None
            
        except Exception as e:
            logger.error(f"从JavaScript提取iframe链接失败: {e}")
            return None
    
    def _is_error_page(self, html):
        """检查是否是错误页面"""
        if not html:
            return True
        
        # 检查常见的错误页面标识
        error_indicators = [
            '访问被拒绝', 'Access Denied', '403 Forbidden', '404 Not Found',
            '500 Internal Server Error', '502 Bad Gateway', '503 Service Unavailable',
            '访问过于频繁', '请求过于频繁', 'rate limit', 'too many requests',
            '服务器维护', '系统维护', 'maintenance', 'under construction',
            '网络错误', '连接超时', 'timeout', 'connection error'
        ]
        
        html_lower = html.lower()
        
        # 优先检查是否包含剧集链接（这是最重要的判断标准）
        if '/m' in html and ('play' in html or 'span_flv' in html):
            return False
        
        # 智能判断：如果页面包含正常的剧集内容，则认为是正常页面
        normal_content_indicators = [
            'span_flv', 'js_flv', 'flv_yp',  # 播放链接容器
            'play0-', 'play1-', 'play2-',    # 播放链接格式
            '剧集', '集数', '播放',           # 中文内容标识
            'title', '剧情', '简介'           # 页面内容标识
        ]
        
        # 检查是否包含正常内容标识
        normal_content_count = 0
        for indicator in normal_content_indicators:
            if indicator in html_lower:
                normal_content_count += 1
        
        # 如果页面长度足够且包含多个正常内容标识，认为是正常页面
        if len(html) > 1000 and normal_content_count >= 2:
            return False
        
        # 检查是否包含错误关键词（排除JavaScript代码中的正常用法）
        for indicator in error_indicators:
            if indicator.lower() in html_lower:
                # 检查是否是JavaScript代码中的正常用法
                if indicator.lower() == 'timeout':
                    # 检查是否是setTimeout等正常用法
                    if 'settimeout' in html_lower or 'settimeout(' in html_lower:
                        continue  # 跳过正常的setTimeout用法
                return True
        
        # 改进的认证错误检测：检查是否真的需要登录
        auth_error_indicators = [
            '请登录后访问', '请先登录', '登录后才能访问', '需要登录',
            '请验证码', '请输入验证码', '验证码错误',
            '访问受限', '权限不足', '需要权限',
            '尚未登录，无法显示', '请先登录才能'
        ]
        
        # 检查是否包含认证错误关键词
        for indicator in auth_error_indicators:
            if indicator.lower() in html_lower:
                return True
        
        return False
    
    def _analyze_error_page(self, html):
        """分析错误页面类型"""
        html_lower = html.lower()
        
        # 改进的认证错误检测：更精确的认证错误判断
        auth_error_indicators = [
            '请登录后访问', '请先登录', '登录后才能访问', '需要登录',
            '请验证码', '请输入验证码', '验证码错误',
            '访问受限', '权限不足', '需要权限',
            '尚未登录，无法显示', '请先登录才能'
        ]
        
        # 检查是否真的需要登录（而不是页面中只是包含"登录"字样）
        if any(keyword in html_lower for keyword in auth_error_indicators):
            return 'auth_error'
        
        # 频率限制错误
        if any(keyword in html_lower for keyword in ['访问过于频繁', '请求过于频繁', 'rate limit', 'too many requests']):
            return 'rate_limit_error'
        
        # 服务器错误
        if any(keyword in html_lower for keyword in ['500', '502', '503', '服务器维护', '系统维护', 'maintenance']):
            return 'server_error'
        
        # 访问被拒绝
        if any(keyword in html_lower for keyword in ['访问被拒绝', 'access denied', '403', '404']):
            return 'access_denied'
        
        return 'unknown_error'
    
    def _analyze_exception(self, exception):
        """分析异常类型"""
        exception_str = str(exception).lower()
        
        # 网络连接错误
        if any(keyword in exception_str for keyword in ['connection', 'timeout', 'network', 'dns']):
            return 'network_error'
        
        # HTTP状态码错误
        if '403' in exception_str:
            return 'auth_error'
        elif '429' in exception_str:
            return 'rate_limit_error'
        elif '500' in exception_str or '502' in exception_str or '503' in exception_str:
            return 'server_error'
        elif '404' in exception_str:
            return 'not_found'
        
        return 'unknown_error'
    
    def _handle_error(self, error_type, url, error_msg=None, series_id=None, episode_id=None, html_content=None):
        """处理错误"""
        self.stats['consecutive_failures'] += 1
        self.stats['total_failures'] += 1
        
        # 根据错误类型更新统计
        if error_type == 'network_error':
            self.stats['network_errors'] += 1
            logger.warning(f"网络错误: {url}")
        elif error_type == 'auth_error':
            self.stats['auth_errors'] += 1
            logger.error(f"认证错误: {url} - 可能需要登录")
        elif error_type == 'rate_limit_error':
            self.stats['rate_limit_errors'] += 1
            logger.error(f"频率限制: {url} - 请求过于频繁")
        elif error_type == 'server_error':
            self.stats['server_errors'] += 1
            logger.error(f"服务器错误: {url}")
        else:
            logger.error(f"未知错误: {url} - {error_msg}")
        
        # 保存错误页面到err文件夹
        if html_content and series_id:
            self._save_error_page(series_id, episode_id, error_type, url, html_content, error_msg)
        
        # 检查是否需要暂停
        if self.stats['consecutive_failures'] >= self.error_config['max_consecutive_failures']:
            self._handle_consecutive_failures()
    
    def _handle_consecutive_failures(self):
        """处理连续失败"""
        logger.error(f"连续失败 {self.stats['consecutive_failures']} 次，跳过当前剧集")
        
        # 分析失败原因
        if self.stats['auth_errors'] > 0:
            logger.error("检测到认证错误，可能需要登录或验证码")
        if self.stats['rate_limit_errors'] > 0:
            logger.error("检测到频率限制，需要降低请求频率")
        if self.stats['server_errors'] > 0:
            logger.error("检测到服务器错误，服务器可能维护中")
        if self.stats['network_errors'] > 0:
            logger.error("检测到网络错误，请检查网络连接")
        
        # 暂停一段时间
        delay = self.error_config['retry_delay']
        logger.info(f"暂停 {delay} 秒后继续下一个剧集...")
        time.sleep(delay)
        
        # 重置连续失败计数
        self.stats['consecutive_failures'] = 0
    
    def _save_error_page(self, series_id, episode_id, error_type, url, html_content, error_msg=None):
        """保存错误页面到err文件夹"""
        try:
            # 生成时间戳
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 构建文件名
            if episode_id:
                filename = f"{timestamp}_{series_id}_{episode_id}.html"
            else:
                filename = f"{timestamp}_{series_id}.html"
            
            # 构建文件路径
            file_path = os.path.join(self.err_dir, filename)
            
            # 分析页面类型
            page_type = self._analyze_page_type(url, html_content)
            
            # 构建错误信息HTML
            error_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>错误页面 - {series_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .error-info {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .error-type {{ color: #dc3545; font-weight: bold; }}
        .url {{ color: #007bff; word-break: break-all; }}
        .timestamp {{ color: #6c757d; font-size: 0.9em; }}
        .page-type {{ color: #28a745; font-weight: bold; }}
        .debug-info {{ background: #e9ecef; padding: 10px; border-radius: 3px; margin: 10px 0; }}
        .original-content {{ border: 1px solid #ddd; padding: 10px; background: #fff; }}
    </style>
</head>
<body>
    <div class="error-info">
        <h2>错误信息</h2>
        <p><strong>错误类型:</strong> <span class="error-type">{error_type}</span></p>
        <p><strong>剧集ID:</strong> {series_id}</p>
        <p><strong>集数:</strong> {episode_id if episode_id else 'N/A'}</p>
        <p><strong>URL:</strong> <span class="url">{url}</span></p>
        <p><strong>页面类型:</strong> <span class="page-type">{page_type}</span></p>
        <p><strong>时间:</strong> <span class="timestamp">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span></p>
        {f'<p><strong>错误消息:</strong> {error_msg}</p>' if error_msg else ''}
    </div>
    
    <div class="debug-info">
        <h3>调试信息</h3>
        <p><strong>URL分析:</strong></p>
        <ul>
            <li>完整URL: {url}</li>
            <li>URL路径: {url.split('/')[-2] if len(url.split('/')) > 2 else 'N/A'}</li>
            <li>是否包含play: {'是' if '/play' in url else '否'}</li>
            <li>是否包含newplay.asp: {'是' if 'newplay.asp' in url else '否'}</li>
            <li>URL格式验证: {'通过' if self._is_valid_play_url(url) else '失败'}</li>
        </ul>
        <p><strong>页面内容分析:</strong></p>
        <ul>
            <li>页面长度: {len(html_content) if html_content else 0} 字符</li>
            <li>是否包含剧集信息: {'是' if html_content and ('span_flv' in html_content or 'js_flv' in html_content) else '否'}</li>
            <li>是否包含播放器: {'是' if html_content and 'playframe' in html_content else '否'}</li>
            <li>是否包含认证错误: {'是' if html_content and ('登录' in html_content or '认证' in html_content) else '否'}</li>
        </ul>
    </div>
    
    <div class="original-content">
        <h3>原始页面内容:</h3>
        <pre>{html_content}</pre>
    </div>
</body>
</html>"""
            
            # 保存文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(error_html)
            
            logger.info(f"错误页面已保存: {file_path}")
            
        except Exception as e:
            logger.error(f"保存错误页面失败: {e}")
    
    def _analyze_page_type(self, url, html_content):
        """分析页面类型"""
        try:
            # 分析URL
            if '/play' in url:
                return "播放页面"
            elif '/m' in url and not '/play' in url:
                return "剧集详情页"
            elif 'newplay.asp' in url:
                return "newplay.asp页面"
            else:
                return "未知页面类型"
        except:
            return "页面类型分析失败"
    
    def _is_valid_play_url(self, url):
        """验证是否是有效的播放链接格式"""
        try:
            if not url:
                return False
            
            # 检查是否是 /m数字id/play片源id-剧集集数.html 格式
            if re.match(r'^/m\d+/play\d+-\d+\.html$', url):
                return True
            
            # 检查是否是 play数字-数字.html 格式（相对路径）
            if re.match(r'^play\d+-\d+\.html$', url):
                return True
            
            # 检查是否是完整的URL格式
            if url.startswith('https://www.yatu.tv/m') and '/play' in url and '.html' in url:
                # 提取路径部分进行验证
                from urllib.parse import urlparse
                parsed = urlparse(url)
                path = parsed.path
                if re.match(r'^/m\d+/play\d+-\d+\.html$', path):
                    return True
            
            return False
            
        except Exception as e:
            logger.debug(f"播放链接验证失败: {e}")
            return False
    
    def _is_valid_player_url(self, url):
        """验证是否是有效的播放器URL"""
        try:
            if not url or len(url) < 10:
                return False
            
            # 检查是否包含常见的播放器域名
            player_domains = [
                'jx.xmflv.cc',
                'jx.player.com',
                'player.',
                'play.',
                'iframe.',
                'video.',
                'm3u8',
                'mp4',
                'flv'
            ]
            
            url_lower = url.lower()
            for domain in player_domains:
                if domain in url_lower:
                    return True
            
            # 检查是否是HTTP/HTTPS URL
            if url.startswith(('http://', 'https://')):
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"URL验证失败: {e}")
            return False

    def extract_title(self, soup):
        """提取剧集标题"""
        try:
            title_elem = soup.find('h1') or soup.find('title')
            if title_elem:
                return title_elem.get_text(strip=True)
            return ""
        except:
            return ""
    
    def extract_description(self, soup):
        """提取剧集描述"""
        try:
            desc_elem = soup.find('div', class_='des') or soup.find('div', class_='description')
            if desc_elem:
                return desc_elem.get_text(strip=True)
            return ""
        except:
            return ""
    
    def extract_year(self, soup):
        """提取年份"""
        try:
            year_elem = soup.find(text=re.compile(r'\d{4}'))
            if year_elem:
                year_match = re.search(r'\d{4}', year_elem)
                if year_match:
                    return year_match.group()
            return ""
        except:
            return ""
    
    def extract_country(self, soup):
        """提取国家"""
        try:
            country_elem = soup.find(text=re.compile(r'地区|国家'))
            if country_elem:
                return country_elem.get_text(strip=True)
            return ""
        except:
            return ""
    
    def extract_language(self, soup):
        """提取语言"""
        try:
            lang_elem = soup.find(text=re.compile(r'语言'))
            if lang_elem:
                return lang_elem.get_text(strip=True)
            return ""
        except:
            return ""
    
    def extract_director(self, soup):
        """提取导演"""
        try:
            director_elem = soup.find(text=re.compile(r'导演'))
            if director_elem:
                return director_elem.get_text(strip=True)
            return ""
        except:
            return ""
    
    def extract_actors(self, soup):
        """提取演员"""
        try:
            actors_elem = soup.find(text=re.compile(r'主演|演员'))
            if actors_elem:
                return actors_elem.get_text(strip=True)
            return ""
        except:
            return ""
    
    def extract_cover_image(self, soup):
        """提取封面图片URL"""
        try:
            # 方法1: 查找常见的封面图片元素
            cover_selectors = [
                'img[src*="poster"]',
                'img[src*="cover"]',
                'img[src*="thumb"]',
                '.poster img',
                '.cover img',
                '.thumb img',
                '.pic img',
                '.img img',
                'img[class*="poster"]',
                'img[class*="cover"]',
                'img[class*="thumb"]'
            ]
            
            for selector in cover_selectors:
                img_elem = soup.select_one(selector)
                if img_elem and img_elem.get('src'):
                    src = img_elem.get('src')
                    if src.startswith('http'):
                        return src
                    elif src.startswith('//'):
                        return 'https:' + src
                    elif src.startswith('/'):
                        return 'https://www.yatu.tv' + src
            
            # 方法2: 查找所有图片，选择最大的作为封面
            all_images = soup.find_all('img')
            max_size = 0
            best_image = None
            
            for img in all_images:
                src = img.get('src', '')
                if not src or src.startswith('data:'):
                    continue
                
                # 检查图片尺寸
                width = img.get('width', '0')
                height = img.get('height', '0')
                try:
                    w = int(width) if width.isdigit() else 0
                    h = int(height) if height.isdigit() else 0
                    size = w * h
                    if size > max_size and size > 10000:  # 至少100x100像素
                        max_size = size
                        best_image = src
                except:
                    continue
            
            if best_image:
                if best_image.startswith('http'):
                    return best_image
                elif best_image.startswith('//'):
                    return 'https:' + best_image
                elif best_image.startswith('/'):
                    return 'https://www.yatu.tv' + best_image
            
            return ""
        except Exception as e:
            logger.debug(f"提取封面图片失败: {e}")
            return ""
    
    def download_cover_image(self, cover_url, series_id, session):
        """下载并保存封面图片"""
        try:
            # 确保剧集目录存在
            series_dir = os.path.join(self.data_dir, series_id)
            if not os.path.exists(series_dir):
                os.makedirs(series_dir)
            
            # 获取图片内容
            response = session.get(cover_url, timeout=10, stream=True)
            response.raise_for_status()
            
            # 获取文件扩展名
            content_type = response.headers.get('content-type', '')
            if 'image/jpeg' in content_type or 'image/jpg' in content_type:
                ext = '.jpg'
            elif 'image/png' in content_type:
                ext = '.png'
            elif 'image/gif' in content_type:
                ext = '.gif'
            elif 'image/webp' in content_type:
                ext = '.webp'
            else:
                # 从URL推断扩展名
                parsed_url = urllib.parse.urlparse(cover_url)
                path = parsed_url.path.lower()
                if '.jpg' in path or '.jpeg' in path:
                    ext = '.jpg'
                elif '.png' in path:
                    ext = '.png'
                elif '.gif' in path:
                    ext = '.gif'
                elif '.webp' in path:
                    ext = '.webp'
                else:
                    ext = '.jpg'  # 默认使用jpg
            
            # 保存图片文件
            cover_filename = f"cover{ext}"
            cover_path = os.path.join(series_dir, cover_filename)
            
            with open(cover_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"✓ 封面图片已保存: {cover_path}")
            return cover_filename
            
        except Exception as e:
            logger.warning(f"下载封面图片失败: {cover_url} - {e}")
            return None

    def run_multithread_crawl(self):
        """多线程剧集采集模式"""
        logger.info("=== 开始多线程剧集采集 ===")
        start_time = time.time()
        
        # 显示初始内存使用情况
        initial_memory = self.get_memory_usage()
        logger.info(f"初始内存使用: {initial_memory:.1f}MB")
        
        try:
            # 采集所有分类的剧集
            all_series = self.crawl_all_categories_multithread()
            
            if all_series:
                # 保存结果到JSON文件
                output_file = "data/all_categories_series_multithread.json"
                os.makedirs("data", exist_ok=True)
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(all_series, f, ensure_ascii=False, indent=2)
                
                logger.info(f"采集完成，共 {len(all_series)} 个剧集")
                logger.info(f"结果已保存到: {output_file}")
                
                # 显示最终内存使用情况
                final_memory = self.get_memory_usage()
                logger.info(f"最终内存使用: {final_memory:.1f}MB (初始: {initial_memory:.1f}MB)")
                
                # 清理内存
                self.clear_memory()
            else:
                logger.error("采集失败，未获取到任何剧集")
                
        except Exception as e:
            logger.error(f"多线程采集异常: {e}")
        finally:
            # 最终内存清理
            self.clear_memory()
        
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"多线程采集耗时: {duration:.2f} 秒")

    def crawl_page_with_thread(self, page_info):
        """单个页面采集任务"""
        category_name, category_url, page, thread_id = page_info
        
        try:
            # 为每个线程创建独立的爬虫实例
            crawler = YatuTVCrawler()
            
            # 构建分页URL
            if page == 1:
                page_url = category_url
            else:
                page_url = f"{category_url.rstrip('/')}/{page}.html"
            
            logger.info(f"[线程{thread_id}] 正在采集 {category_name} 第 {page} 页: {page_url}")
            
            # 设置当前URL用于最后一页检测
            crawler.current_url = page_url
            
            html = crawler.get_page(page_url)
            if not html:
                logger.warning(f"[线程{thread_id}] 无法获取 {category_name} 第 {page} 页内容")
                return None
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找剧集列表
            items = crawler._extract_series_items(soup, category_name)
            if not items:
                logger.info(f"[线程{thread_id}] {category_name} 第 {page} 页没有找到剧集")
                return {'is_last': True, 'items': [], 'category': category_name, 'page': page}
            
            # 检查是否到达最后一页
            if crawler._is_last_page(soup):
                logger.info(f"[线程{thread_id}] {category_name} 第 {page} 页是最后一页")
                return {'is_last': True, 'items': items, 'category': category_name, 'page': page}
            
            logger.info(f"[线程{thread_id}] {category_name} 第 {page} 页采集到 {len(items)} 个剧集")
            
            return {'is_last': False, 'items': items, 'category': category_name, 'page': page}
            
        except Exception as e:
            logger.error(f"[线程{thread_id}] 采集 {category_name} 第 {page} 页时出错: {e}")
            return None

    def crawl_category_multithread(self, category_name, category_url, max_workers=10, max_pages=1000):
        """使用多线程采集单个分类"""
        logger.info(f"开始多线程采集 {category_name} 分类: {category_url}")
        
        all_series = []
        last_page_found = False
        page = 1
        batch_size = 5  # 每批处理5页
        
        while page <= max_pages and not last_page_found:
            # 创建当前批次的页面列表
            batch_pages = []
            for i in range(batch_size):
                if page + i <= max_pages:
                    batch_pages.append((category_name, category_url, page + i, f"B{page+i}"))
            
            # 使用线程池批量处理
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有批次任务
                future_to_page = {executor.submit(self.crawl_page_with_thread, page_info): page_info for page_info in batch_pages}
                
                # 处理完成的任务
                for future in as_completed(future_to_page):
                    page_info = future_to_page[future]
                    try:
                        result = future.result()
                        
                        if result is None:
                            continue
                        
                        # 处理结果
                        if result['is_last']:
                            last_page_found = True
                            logger.info(f"{category_name} 在第 {result['page']} 页到达最后一页")
                        
                        # 添加剧集到结果
                        if result['items']:
                            all_series.extend(result['items'])
                            
                            # 显示前3个剧集
                            logger.info(f"{category_name} 第 {result['page']} 页剧集列表:")
                            for i, item in enumerate(result['items'][:3]):
                                logger.info(f"  {i+1}. {item['title']} -> {item['url']}")
                            if len(result['items']) > 3:
                                logger.info(f"  ... 还有 {len(result['items'])-3} 个剧集")
                        
                    except Exception as e:
                        logger.error(f"处理页面 {page_info} 时出错: {e}")
            
            # 移动到下一批次
            page += batch_size
            
            # 避免请求过快
            time.sleep(1)
        
        logger.info(f"{category_name} 分类总共采集到 {len(all_series)} 个剧集")
        return all_series

    def crawl_all_categories_multithread(self):
        """使用多线程采集所有分类"""
        # 定义分类页面URL
        categories = {
            '动漫': 'https://www.yatu.tv/m-dm/',
            '电影': 'https://www.yatu.tv/m-dy/',
            '电视剧': 'https://www.yatu.tv/m-tv/'
        }
        
        all_series = []
        
        # 为每个分类使用多线程采集
        for category_name, category_url in categories.items():
            logger.info(f"开始采集 {category_name} 分类: {category_url}")
            
            # 检查内存使用情况
            current_memory = self.get_memory_usage()
            logger.info(f"当前内存使用: {current_memory:.1f}MB")
            
            if self.check_memory_limit():
                logger.warning("内存使用过高，强制清理内存")
                self.clear_memory()
            
            # 采集当前分类
            category_series = self.crawl_category_multithread(category_name, category_url, max_workers=10)
            all_series.extend(category_series)
            
            # 显示分类统计
            logger.info(f"{category_name} 分类剧集详情:")
            for i, item in enumerate(category_series[:5]):  # 只显示前5个
                logger.info(f"  {i+1}. {item['title']} -> {item['url']}")
            if len(category_series) > 5:
                logger.info(f"  ... 还有 {len(category_series)-5} 个剧集")
            
            logger.info("-" * 50)
            
            # 分类间暂停，避免请求过快
            time.sleep(1)
        
        # 去重处理
        unique_series = []
        seen_urls = set()
        
        for series in all_series:
            if series['url'] not in seen_urls:
                unique_series.append(series)
                seen_urls.add(series['url'])
        
        logger.info(f"去重后总共采集到 {len(unique_series)} 个唯一剧集")
        
        # 清理原始数据
        all_series.clear()
        seen_urls.clear()
        
        return unique_series

    def get_memory_usage(self):
        """获取当前内存使用情况"""
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        return memory_info.rss / 1024 / 1024  # 转换为MB
    
    def check_memory_limit(self):
        """检查内存使用是否超过限制"""
        current_memory = self.get_memory_usage()
        if current_memory > self.memory_limit_mb:
            logger.warning(f"内存使用过高: {current_memory:.1f}MB > {self.memory_limit_mb}MB")
            return True
        return False
    
    def force_garbage_collection(self):
        """强制垃圾回收"""
        import gc
        collected = gc.collect()
        logger.debug(f"垃圾回收完成，释放了 {collected} 个对象")
    
    def clear_memory(self):
        """清理内存"""
        # 清理线程池结果缓存
        self.episode_results.clear()
        self.episode_queue.clear()
        
        # 强制垃圾回收
        self.force_garbage_collection()
        
        # 显示内存使用情况
        current_memory = self.get_memory_usage()
        logger.info(f"内存清理完成，当前使用: {current_memory:.1f}MB")
    
    def save_batch_data(self, batch_data):
        """批量保存数据"""
        if not batch_data:
            return
        
        logger.info(f"批量保存 {len(batch_data)} 个剧集数据...")
        
        for series_info in batch_data:
            try:
                self.save_series_data(series_info)
                self.stats['successful_series'] += 1
            except Exception as e:
                logger.error(f"保存剧集数据失败: {series_info.get('title', 'Unknown')} - {e}")
        
        # 清理批量数据
        batch_data.clear()
        
        # 强制垃圾回收
        self.force_garbage_collection()

if __name__ == "__main__":
    import sys
    
    crawler = YatuTVCrawler()
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode == "multithread" or mode == "mt":
            # 多线程剧集采集模式
            print("启动多线程剧集采集模式...")
            crawler.run(use_multithread_crawl=True)
        elif mode == "homepage" or mode == "hp":
            # 仅首页抓取模式
            print("启动仅首页抓取模式...")
            crawler.run(use_category_pages=False, check_missing=False)
        elif mode == "category" or mode == "cat":
            # 仅分类页面抓取模式
            print("启动仅分类页面抓取模式...")
            crawler.run(use_category_pages=True, check_missing=False)
        elif mode == "full" or mode == "complete":
            # 完整抓取模式（默认）：首页+遗漏检查
            print("启动完整抓取模式（首页+遗漏检查）...")
            crawler.run(use_category_pages=True, check_missing=True)
        elif mode == "help" or mode == "h":
            # 显示帮助信息
            print("雅图TV抓取工具使用方法:")
            print("")
            print("  python app.py                    # 默认完整抓取（首页+遗漏检查）")
            print("  python app.py full               # 完整抓取模式（首页+遗漏检查）")
            print("  python app.py complete           # 完整抓取模式（首页+遗漏检查）")
            print("  python app.py multithread        # 多线程剧集采集")
            print("  python app.py mt                 # 多线程剧集采集(简写)")
            print("  python app.py homepage           # 仅首页抓取")
            print("  python app.py hp                 # 仅首页抓取(简写)")
            print("  python app.py category           # 仅分类页面抓取")
            print("  python app.py cat                # 仅分类页面抓取(简写)")
            print("  python app.py help               # 显示此帮助信息")
            print("")
            print("模式说明:")
            print("  - 完整抓取: 先抓取首页最新内容，再检查分类页面是否有遗漏")
            print("  - 多线程采集: 使用10个线程快速采集所有分类的剧集列表")
            print("  - 仅首页抓取: 只抓取首页显示的最新剧集")
            print("  - 仅分类抓取: 只抓取分类页面的剧集，不抓取首页")
        else:
            print("未知模式，使用方法:")
            print("  python app.py help               # 查看详细帮助")
            print("  python app.py                    # 默认完整抓取")
            print("  python app.py multithread        # 多线程剧集采集")
            print("  python app.py full               # 完整抓取模式")
    else:
        # 默认使用完整抓取模式（首页+遗漏检查）
        print("启动默认完整抓取模式（首页+遗漏检查）...")
        crawler.run(use_category_pages=True, check_missing=True)
