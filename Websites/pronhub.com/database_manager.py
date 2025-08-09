#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any

class DatabaseManager:
    """视频数据库管理器"""
    
    def __init__(self, db_path: str = None):
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
    
    def insert_video(self, video_data: Dict[str, Any]) -> int:
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
    
    def _insert_video_categories(self, cursor, video_db_id: int, categories: List[Dict]):
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
    
    def _insert_m3u8_urls(self, cursor, video_db_id: int, m3u8_urls: List[str]):
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
    
    def video_exists(self, video_id: str) -> bool:
        """检查视频是否已存在于数据库中"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM videos WHERE video_id = ?', (video_id,))
            return cursor.fetchone()[0] > 0
    
    def get_video_by_id(self, video_id: str) -> Optional[Dict]:
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
    
    def search_videos(self, query: str = None, limit: int = 100, offset: int = 0) -> List[Dict]:
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
    
    def get_statistics(self) -> Dict[str, Any]:
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
    
    def export_to_json(self, output_file: str, limit: int = None):
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
    
    def close(self):
        """关闭数据库连接（当前实现使用with语句自动关闭）"""
        pass

if __name__ == '__main__':
    # 测试数据库管理器
    db = DatabaseManager()
    
    # 获取统计信息
    stats = db.get_statistics()
    print("数据库统计信息:")
    print(f"  总视频数: {stats['total_videos']}")
    print(f"  总分类数: {stats['total_categories']}")
    print(f"  最新采集: {stats['latest_collection']}")
    
    # 显示热门上传者
    if stats['top_uploaders']:
        print("\n热门上传者:")
        for uploader in stats['top_uploaders'][:5]:
            print(f"  {uploader['uploader']}: {uploader['count']} 个视频")
    
    # 显示热门分类
    if stats['top_categories']:
        print("\n热门分类:")
        for category in stats['top_categories'][:5]:
            print(f"  {category['name']}: {category['count']} 个视频") 