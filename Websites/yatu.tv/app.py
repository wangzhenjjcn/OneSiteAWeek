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
        
        # 初始化数据库
        self.db = YatuTVDatabase()
        
        # 定义分类页面URL
        self.category_urls = {
            '动漫': 'https://www.yatu.tv/m-dm/',
            '电影': 'https://www.yatu.tv/m-dy/',
            '电视剧': 'https://www.yatu.tv/m-tv/',
            'jc': 'https://www.yatu.tv/m-dm/jc.htm'  # 特殊页面
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
    
    def get_page(self, url):
        """获取页面内容"""
        try:
            response = self.session.get(url, timeout=10)
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
            return response.text
            
        except Exception as e:
            logger.error(f"获取页面失败: {url}, 错误: {e}")
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
                
                # 提取剧集ID
                series_id = href.strip('/').split('/')[-1] if href else ''
                
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
                logger.info(f"抓取到: {title}")
        
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
                    page_url = f"{category_url.rstrip('/')}/{page}.html"
            
            logger.info(f"正在抓取第 {page} 页: {page_url}")
            
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
            
            # 检查是否到达最后一页（页脚翻页变灰）
            if self._is_last_page(soup):
                logger.info(f"到达最后一页，停止抓取")
                break
            
            page += 1
            time.sleep(1)  # 避免请求过快
        
        logger.info(f"{category_name} 分类总共抓取到 {len(all_items)} 个剧集")
        return all_items
    
    def _extract_series_items(self, soup, category_name):
        """从页面中提取剧集信息"""
        items = []
        
        # 查找剧集链接（m开头的数字ID）
        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            
            # 检查是否是剧集详情页链接（m开头的数字ID）
            if re.match(r'/m\d+/', href):
                title = link.get_text(strip=True)
                if not title:
                    continue
                
                # 完整的链接地址
                full_url = urllib.parse.urljoin(self.base_url, href)
                
                # 提取剧集ID
                series_id = href.strip('/').split('/')[-1] if href else ''
                
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
                logger.debug(f"提取到剧集: {title}")
        
        return items
    
    def _is_last_page(self, soup):
        """检查是否是最后一页（页脚翻页变灰）"""
        # 方法1: 查找页脚翻页链接
        pagination = soup.find('div', class_='pagination') or soup.find('div', class_='page')
        if pagination:
            # 查找"下一页"或"下页"链接
            next_links = pagination.find_all('a', text=re.compile(r'下一页|下页|>'))
            for link in next_links:
                # 检查链接是否变灰（disabled状态）
                if 'disabled' in link.get('class', []) or 'gray' in link.get('class', []):
                    return True
                # 检查链接是否不可点击
                if not link.get('href') or link.get('href') == '#':
                    return True
        
        # 方法2: 查找所有分页链接，检查是否有下一页
        all_pagination_links = soup.find_all('a', href=re.compile(r'\d+\.html'))
        if all_pagination_links:
            # 获取当前页面的数字
            current_page_numbers = []
            for link in all_pagination_links:
                href = link.get('href', '')
                page_match = re.search(r'(\d+)\.html', href)
                if page_match:
                    current_page_numbers.append(int(page_match.group(1)))
            
            # 如果当前页面数字是最大的，说明是最后一页
            if current_page_numbers and max(current_page_numbers) == max(current_page_numbers):
                return True
        
        # 方法3: 检查是否有"没有更多内容"的提示
        no_more_texts = soup.find_all(string=re.compile(r'没有更多|已到最后一页|没有数据|暂无数据'))
        if no_more_texts:
            return True
        
        # 方法4: 检查页面内容是否为空（没有找到任何剧集链接）
        series_links = soup.find_all('a', href=re.compile(r'/m\d+/'))
        if not series_links:
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
            
            # 方法2: 查找play数字-数字.html格式的链接（过滤掉newplay.asp）
            play_links = soup.find_all('a', href=re.compile(r'play\d+-\d+\.html'))
            for link in play_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                if href and text:
                    # 过滤掉以newplay.asp开头的链接
                    if href.startswith('/m/newplay.asp') or 'newplay.asp' in href:
                        continue
                    
                    full_url = urllib.parse.urljoin(self.base_url, href)
                    
                    # 检查是否已存在
                    exists = any(s['source_url'] == full_url for s in sources)
                    if not exists:
                        sources.append({
                            'source_id': f"play_{len(sources)}",
                            'source_name': f"播放链接: {text}",
                            'source_url': full_url,
                            'source_type': '站外片源'
                        })
            
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
    
    def crawl_series_detail(self, series_url, series_id, category_type=None):
        """抓取剧集详情页面"""
        logger.info(f"正在抓取剧集详情: {series_url}")
        
        # 检查数据库和data目录的状态
        db_has_series = self.db.is_series_crawled(series_id)
        existing_data = self.check_existing_data(series_id)
        
        # 只有当数据库和data目录都有数据时才跳过
        if db_has_series and existing_data:
            logger.info(f"剧集 {series_id} 在数据库和data目录中都存在，跳过抓取")
        elif db_has_series and not existing_data:
            logger.info(f"剧集 {series_id} 在数据库中存在但data目录中缺失，需要更新data目录")
        elif not db_has_series and existing_data:
            logger.info(f"剧集 {series_id} 在data目录中存在但数据库中缺失，需要更新数据库")
        else:
            logger.info(f"剧集 {series_id} 在数据库和data目录中都不存在，需要完整抓取")
        
        html = self.get_page(series_url)
        if not html:
            return None
        
        # 保存详情页HTML到数据库
        self.db.save_detail_html(series_id, html)
        logger.info(f"已保存详情页HTML到数据库: {series_id}")
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 查找剧集列表并分析剧集数量和线路
        episodes = []
        episode_patterns = []
        
        # 首先查找现有的播放链接以了解剧集结构
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
        
        # 分析剧集规律：play0-1.html, play0-2.html 等
        max_episodes = 0
        available_lines = set()
        
        import re
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
                logger.info(f"正在分析第{episode['episode']}集的站外片源...")
                
                # 获取播放页面的HTML
                play_html = self.get_page(episode['url'])
                if not play_html:
                    episode['note'] = "无法获取播放页面"
                    self.db.save_episode(series_id, episode)
                    continue
                
                # 查找站外片源（id='cs2'）
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
                        play_url = source['source_url']
                        if 'play' in play_url and '.html' in play_url:
                            real_url = self.get_playframe_url(play_url)
                            if real_url:
                                source['real_url'] = real_url
                                episode['playframe_url'] = real_url
                                episode['note'] = f"✓ 解析成功: {source['source_name']}"
                                playframe_found_count += 1
                                logger.info(f"✓ 解析成功: {source['source_name']} -> {real_url}")
                            else:
                                source['real_url'] = None
                                episode['playframe_url'] = play_url
                                episode['note'] = f"❌ 解析失败: {source['source_name']}"
                                logger.info(f"❌ 解析失败: {source['source_name']}")
                        else:
                            # 非play链接，直接保存
                            source['real_url'] = None
                            episode['playframe_url'] = play_url
                            episode['note'] = f"✓ 站外片源: {source['source_name']}"
                            playframe_found_count += 1
                            logger.info(f"✓ 保存片源链接: {source['source_name']} -> {play_url}")
                        
                        # 立即保存片源信息到数据库
                        self.db.save_source(series_id, episode_id, source)
                        
                        # 延时避免请求过快
                        time.sleep(0.5)  # 减少延时
                    
                    if not episode.get('playframe_url'):
                        episode['note'] = f"站外片源 {len(external_sources)} 个，均无法播放"
                else:
                    episode['note'] = "未找到站外片源"
                    logger.debug(f"- 第{episode['episode']}集未找到站外片源")
                
                # 保存集数信息到数据库
                self.db.save_episode(series_id, episode)
                
                # 延时避免请求过快
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"分析第{episode['episode']}集站外片源失败: {e}")
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
        
        # 保存剧集信息到数据库
        self.db.save_series(series_info)
        
        # 保存剧集数据到data目录（生成HTML文件）
        self.save_series_data(series_info)
        
        return series_info
    
    def get_playframe_url(self, play_url):
        """获取playframe iframe的src地址"""
        try:
            logger.debug(f"正在获取playframe地址: {play_url}")
            
            # 从play_url提取详情页URL作为Referer
            detail_url = '/'.join(play_url.split('/')[:-1]) + '/'
            
            # 为播放页面设置特殊的请求头
            headers = {
                'Referer': detail_url,
                'Sec-Fetch-Dest': 'iframe',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
            }
            
            html = self.get_page_with_headers(play_url, headers)
            if not html:
                return None
            
            # 查找playframe iframe的src地址
            iframe_url = self._extract_iframe_src(html)
            if iframe_url:
                logger.info(f"✓ 找到playframe地址: {iframe_url}")
                return iframe_url
            else:
                logger.debug(f"未找到playframe iframe: {play_url}")
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
    


    def get_page_with_headers(self, url, additional_headers=None):
        """使用特定请求头获取页面内容"""
        try:
            headers = self.session.headers.copy()
            if additional_headers:
                headers.update(additional_headers)
            
            response = self.session.get(url, timeout=10, headers=headers)
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
            return response.text
            
        except Exception as e:
            logger.error(f"获取页面失败: {url}, 错误: {e}")
            return None
    

    
    def _extract_iframe_src(self, html):
        """机械地查找iframe的src完整引用或script中的m3u8地址"""
        try:
            from bs4 import BeautifulSoup
            import re
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # 方法1: 查找所有iframe元素
            iframes = soup.find_all('iframe')
            
            for iframe in iframes:
                iframe_src = iframe.get('src', '')
                
                if iframe_src:
                    logger.info(f"✓ 找到iframe src: {iframe_src}")
                    return iframe_src
            
            # 方法2: 查找script标签中的m3u8地址
            scripts = soup.find_all('script')
            for script in scripts:
                script_content = script.string
                if script_content:
                    # 查找url = "m3u8地址"的模式
                    url_match = re.search(r'url\s*=\s*["\']([^"\']*\.m3u8[^"\']*)["\']', script_content)
                    if url_match:
                        m3u8_url = url_match.group(1)
                        # 移除&next参数
                        if '&next=' in m3u8_url:
                            m3u8_url = m3u8_url.split('&next=')[0]
                        logger.info(f"✓ 找到script中的m3u8地址: {m3u8_url}")
                        return m3u8_url
            
            # 如果没有找到任何播放地址，返回None
            logger.debug("未找到任何iframe或m3u8地址")
            return None
            
        except Exception as e:
            logger.error(f"提取播放地址失败: {e}")
            return None
    
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
            
            # 构建play0-集数.html格式的URL
            play_url = f"https://www.yatu.tv/{series_id}/play0-{episode_num}.html"
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
        
        if cover_image:
            html_content += f'''
                    <img src="{cover_image}" alt="{title}" class="cover-image" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex'">
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
    
    def run(self, use_category_pages=True):
        """主运行函数"""
        logger.info("=== 雅图TV抓取工具启动 ===")
        logger.info("目标网站: https://www.yatu.tv")
        logger.info("抓取内容: 动漫、电影、电视剧列表及详情")
        logger.info("数据保存: data/ 目录")
        logger.info("=" * 50)
        
        if use_category_pages:
            # 使用分类页面抓取
            logger.info("使用分类页面抓取模式")
            categories_data = self.crawl_all_categories()
        else:
            # 使用首页抓取（保留原有功能）
            logger.info("使用首页抓取模式")
            categories_data = self.crawl_homepage()
        
        if not categories_data:
            logger.error("抓取失败")
            return
        
        # 2. 生成首页 HTML
        self.generate_index_html(categories_data)
        
        # 3. 抓取所有剧集详情
        logger.info("开始抓取所有剧集详情...")
        
        detail_count = 0
        total_count = sum(len(info['items']) for info in categories_data.values())
        
        for category_name, category_info in categories_data.items():
            logger.info(f"正在抓取 {category_info['name']} 分类，共 {len(category_info['items'])} 部剧集")
            
            for item in category_info['items']:
                detail_count += 1
                series_id = item['series_id']
                
                if not series_id:
                    logger.warning(f"跳过空剧集ID: {item['title']}")
                    continue
                
                # 检查series_id是否包含无效文件名字符
                invalid_chars = ['?', '&', '=', '<', '>', ':', '"', '|', '*']
                if any(char in series_id for char in invalid_chars):
                    logger.warning(f"跳过包含无效字符的剧集ID '{series_id}': {item['title']}")
                    continue
                
                logger.info(f"[{detail_count}/{total_count}] 正在抓取: {item['title']}")
                
                # 抓取详情，传递分类信息
                series_info = self.crawl_series_detail(item['url'], series_id, item['category'])
                if series_info:
                    self.save_series_data(series_info)
                    logger.info(f"✓ 完成: {item['title']} ({len(series_info['episodes'])}集)")
                else:
                    logger.error(f"✗ 失败: {item['title']}")
                
                # 延时，避免请求过快
                time.sleep(1)
        
        logger.info("=== 抓取完成 ===")

if __name__ == "__main__":
    crawler = YatuTVCrawler()
    # 默认使用分类页面抓取，如需使用首页抓取请设置为False
    crawler.run(use_category_pages=True)
