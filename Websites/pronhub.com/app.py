import requests
import os
import re
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import random
import threading
from queue import Queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import PROXY_CONFIG, HEADERS, BASE_URL, SCRAPER_CONFIG, OUTPUT_CONFIG, DEBUG, SSL_CONFIG

# 禁用SSL警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class PornhubScraper:
    def __init__(self):
        self.base_url = BASE_URL
        self.proxies = PROXY_CONFIG
        self.headers = HEADERS
        self.download_queue = Queue()
        self.download_results = {}
        self.download_lock = threading.Lock()
        
    def get_page(self, url):
        """获取页面内容"""
        max_retries = SCRAPER_CONFIG.get('max_retries', 3)
        
        for attempt in range(max_retries):
            try:
                # 完全忽略SSL验证
                kwargs = {
                    'headers': self.headers,
                    'timeout': SCRAPER_CONFIG['timeout'],
                    'verify': False,  # 不验证SSL证书
                    'allow_redirects': True,  # 允许重定向
                }
                
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
            
            # 获取上传时间
            added_element = li_element.find('var', class_='added')
            added_time = added_element.get_text(strip=True) if added_element else ''
            
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
                'views': views,
                'added_time': added_time
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
        
        for attempt in range(max_retries):
            try:
                # 完全忽略SSL验证
                kwargs = {
                    'headers': self.headers,
                    'timeout': SCRAPER_CONFIG['timeout'],
                    'verify': False,  # 不验证SSL证书
                    'allow_redirects': True,  # 允许重定向
                }
                
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
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }}
        .thumbnail {{
            text-align: center;
            position: relative;
        }}
        .thumbnail img {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            cursor: pointer;
            transition: transform 0.3s ease;
        }}
        .thumbnail img:hover {{
            transform: scale(1.05);
        }}
        .info-details {{
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}
        .info-item {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .info-label {{
            font-weight: bold;
            color: #666;
            min-width: 100px;
        }}
        .info-value {{
            color: #333;
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
        .hover-video {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            opacity: 0;
            transition: opacity 0.3s ease;
            border-radius: 8px;
            pointer-events: none;
        }}
        .thumbnail:hover .hover-video {{
            opacity: 1;
        }}
    </style>
</head>
<body>
    <div class="video-container">
        <h1 class="video-title">{video_data['title']}</h1>
        
        <div class="video-info">
            <div class="thumbnail">
                <img src="{OUTPUT_CONFIG['thumbnail_filename']}" alt="{video_data['alt_text']}" id="thumbnail">
                <video class="hover-video" id="hoverVideo" muted loop>
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
                    <span class="info-label">上传时间:</span>
                    <span class="info-value">{video_data['added_time']}</span>
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
                    <span class="info-label">最佳m3u8:</span>
                    <span class="info-value">
                        <a href="{video_data.get('best_m3u8_url', '')}" target="_blank" style="word-break: break-all;">
                            {video_data.get('best_m3u8_url', 'N/A')}
                        </a>
                    </span>
                </div>
                <div class="info-item">
                    <span class="info-label">原始链接:</span>
                    <span class="info-value"><a href="{video_data['video_url']}" target="_blank">{video_data['video_url']}</a></span>
                </div>
            </div>
        </div>
        
        <div class="video-player">
            <h3>预览视频</h3>
            <video controls>
                <source src="{OUTPUT_CONFIG['preview_filename']}" type="video/webm">
                您的浏览器不支持视频播放。
            </video>
        </div>
        
        <div class="download-links">
            <h3>下载链接</h3>
            <a href="{OUTPUT_CONFIG['thumbnail_filename']}" download>下载缩略图</a>
            <a href="{OUTPUT_CONFIG['preview_filename']}" download>下载预览视频</a>
            <a href="{video_data['video_url']}" target="_blank">访问原始页面</a>
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
    </script>
</body>
</html>
        """
        
        html_filepath = os.path.join(folder_path, OUTPUT_CONFIG['html_filename'])
        with open(html_filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return html_filepath
    
    def process_video(self, video_data):
        """处理单个视频"""
        if not video_data or not video_data['viewkey']:
            return False
        
        viewkey = video_data['viewkey']
        # 获取app.py所在的目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        folder_path = os.path.join(script_dir, OUTPUT_CONFIG['data_folder'], viewkey)
        
        # 检查是否已存在且采集完成
        if SCRAPER_CONFIG.get('skip_existing', True):
            if self.is_video_completed(viewkey):
                if DEBUG['verbose']:
                    print(f"跳过已完成的视频: {video_data['title']}")
                return True
        
        if DEBUG['verbose']:
            print(f"处理视频: {video_data['title']}")
            print(f"文件夹: {folder_path}")
        
        # 创建文件夹
        os.makedirs(folder_path, exist_ok=True)
        
        try:
            # 添加下载任务到队列
            download_tasks = []
            if video_data['thumbnail_url']:
                thumbnail_path = os.path.join(folder_path, OUTPUT_CONFIG['thumbnail_filename'])
                self.add_download_task(video_data['thumbnail_url'], thumbnail_path, "缩略图")
                download_tasks.append(("缩略图", thumbnail_path))
            
            if video_data['preview_url']:
                preview_path = os.path.join(folder_path, OUTPUT_CONFIG['preview_filename'])
                self.add_download_task(video_data['preview_url'], preview_path, "预览视频")
                download_tasks.append(("预览视频", preview_path))
            
            # 创建HTML页面
            html_path = self.create_html_page(video_data, folder_path)
            if DEBUG['verbose']:
                print(f"HTML页面创建成功: {html_path}")
            
            # 创建采集日志（初始状态）
            self.create_collection_log(video_data, folder_path, success=False, error_msg="处理中...")
            
            # 立即更新日志为成功状态（因为HTML页面已创建）
            self.create_collection_log(video_data, folder_path, success=True)
            
            return True
            
        except Exception as e:
            error_msg = f"处理视频时出错: {e}"
            print(error_msg)
            self.create_collection_log(video_data, folder_path, success=False, error_msg=error_msg)
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

if __name__ == "__main__":
    scraper = PornhubScraper()
    scraper.run()