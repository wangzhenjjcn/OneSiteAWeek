#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os
from datetime import datetime

class YatuTVDatabase:
    def __init__(self):
        """初始化数据库管理器"""
        # 确保数据库目录存在
        script_dir = os.path.dirname(os.path.abspath(__file__))
        db_dir = os.path.join(script_dir, "database")
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        self.db_path = os.path.join(db_dir, "yatu.tv")
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 创建剧集表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS series (
                    series_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    url TEXT,
                    description TEXT,
                    category TEXT,
                    year TEXT,
                    country TEXT,
                    language TEXT,
                    director TEXT,
                    actors TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建集数表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    series_id TEXT,
                    episode TEXT,
                    title TEXT,
                    url TEXT,
                    playframe_url TEXT,
                    note TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (series_id) REFERENCES series (series_id)
                )
            ''')
            
            # 创建片源表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    series_id TEXT,
                    episode_id TEXT,
                    source_id TEXT,
                    source_name TEXT,
                    source_url TEXT,
                    real_url TEXT,
                    source_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (series_id) REFERENCES series (series_id)
                )
            ''')
            
            # 创建HTML页面表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS html_pages (
                    series_id TEXT,
                    page_type TEXT,
                    html_content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (series_id, page_type)
                )
            ''')
            
            conn.commit()
    
    def save_series(self, series_info):
        """保存剧集信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                # 尝试使用新结构
                cursor.execute('''
                    INSERT OR REPLACE INTO series
                    (series_id, title, url, description, category, year, country, language, director, actors, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    series_info.get('series_id'),
                    series_info.get('title'),
                    series_info.get('url'),
                    series_info.get('description'),
                    series_info.get('category'),
                    series_info.get('year'),
                    series_info.get('country'),
                    series_info.get('language'),
                    series_info.get('director'),
                    series_info.get('actors')
                ))
            except sqlite3.OperationalError:
                # 使用现有结构
                cursor.execute('''
                    INSERT OR REPLACE INTO series
                    (series_id, title, series_url, category, description, director, language, release_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    series_info.get('series_id'),
                    series_info.get('title'),
                    series_info.get('url'), # This maps to series_url in old schema
                    series_info.get('category'),
                    series_info.get('description'),
                    series_info.get('director'),
                    series_info.get('language'),
                    series_info.get('year') # This maps to release_date in old schema
                ))
            conn.commit()
    
    def save_episode(self, series_id, episode_info):
        """保存集数信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                # 尝试使用新结构
                cursor.execute('''
                    INSERT OR REPLACE INTO episodes 
                    (series_id, episode, title, url, playframe_url, note, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    series_id,
                    episode_info.get('episode'),
                    episode_info.get('title'),
                    episode_info.get('url'),
                    episode_info.get('playframe_url'),
                    episode_info.get('note')
                ))
            except sqlite3.OperationalError:
                # 使用现有结构
                cursor.execute('''
                    INSERT OR REPLACE INTO episodes 
                    (series_id, episode_id, episode_title, source_url, playframe_url, crawl_time)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    series_id,
                    episode_info.get('episode'),
                    episode_info.get('title'),
                    episode_info.get('url'),
                    episode_info.get('playframe_url')
                ))
            conn.commit()
    
    def save_source(self, series_id, episode_id, source_info):
        """保存片源信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                # 尝试使用新结构（包含source_type）
                cursor.execute('''
                    INSERT OR REPLACE INTO sources 
                    (series_id, episode_id, source_id, source_name, source_url, real_url, source_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    series_id,
                    episode_id,
                    source_info.get('source_id'),
                    source_info.get('source_name'),
                    source_info.get('source_url'),
                    source_info.get('real_url'),
                    source_info.get('source_type')
                ))
            except sqlite3.OperationalError:
                # 使用现有结构（不包含source_type）
                cursor.execute('''
                    INSERT OR REPLACE INTO sources 
                    (series_id, episode_id, source_id, source_name, source_url, real_url, crawl_time)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    series_id,
                    episode_id,
                    source_info.get('source_id'),
                    source_info.get('source_name'),
                    source_info.get('source_url'),
                    source_info.get('real_url')
                ))
            conn.commit()
    
    def save_detail_html(self, series_id, html_content):
        """保存详情页HTML"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO html_pages 
                (series_id, page_type, html_content)
                VALUES (?, ?, ?)
            ''', (series_id, 'detail', html_content))
            conn.commit()
    
    def is_series_crawled(self, series_id):
        """检查剧集是否已爬取"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM series WHERE series_id = ?', (series_id,))
            return cursor.fetchone()[0] > 0
    
    def is_episode_crawled(self, series_id, episode_id):
        """检查集数是否已爬取"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                # 尝试使用episode列（新结构）
                cursor.execute('SELECT COUNT(*) FROM episodes WHERE series_id = ? AND episode = ?', (series_id, episode_id))
            except sqlite3.OperationalError:
                # 使用episode_id列（现有结构）
                cursor.execute('SELECT COUNT(*) FROM episodes WHERE series_id = ? AND episode_id = ?', (series_id, episode_id))
            return cursor.fetchone()[0] > 0
    
    def is_source_crawled(self, series_id, episode_id, source_id):
        """检查片源是否已爬取"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM sources WHERE series_id = ? AND episode_id = ? AND source_id = ?', 
                         (series_id, episode_id, source_id))
            return cursor.fetchone()[0] > 0
    
    def get_all_series(self):
        """获取所有剧集"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                # 尝试使用created_at列
                cursor.execute('SELECT * FROM series ORDER BY created_at DESC')
            except sqlite3.OperationalError:
                # 如果没有created_at列，使用其他方式排序
                cursor.execute('SELECT * FROM series')
            
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_episodes(self, series_id):
        """获取指定剧集的所有集数"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                # 尝试使用episode列排序（新结构）
                cursor.execute('SELECT * FROM episodes WHERE series_id = ? ORDER BY episode', (series_id,))
            except sqlite3.OperationalError:
                try:
                    # 尝试使用episode_id列排序（现有结构）
                    cursor.execute('SELECT * FROM episodes WHERE series_id = ? ORDER BY episode_id', (series_id,))
                except sqlite3.OperationalError:
                    # 如果都没有，不排序
                    cursor.execute('SELECT * FROM episodes WHERE series_id = ?', (series_id,))
            
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_sources(self, series_id, episode_id):
        """获取指定集数的所有片源"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM sources WHERE series_id = ? AND episode_id = ?', (series_id, episode_id))
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_series_by_id(self, series_id):
        """根据ID获取剧集信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM series WHERE series_id = ?', (series_id,))
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None
    
    def get_statistics(self):
        """获取数据库统计信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 剧集数量
            cursor.execute('SELECT COUNT(*) FROM series')
            series_count = cursor.fetchone()[0]
            
            # 集数数量
            cursor.execute('SELECT COUNT(*) FROM episodes')
            episode_count = cursor.fetchone()[0]
            
            # 片源数量
            cursor.execute('SELECT COUNT(*) FROM sources')
            source_count = cursor.fetchone()[0]
            
            # 有播放地址的集数
            cursor.execute('SELECT COUNT(*) FROM episodes WHERE playframe_url IS NOT NULL AND playframe_url != ""')
            playable_episodes = cursor.fetchone()[0]
            
            return {
                'series_count': series_count,
                'episode_count': episode_count,
                'source_count': source_count,
                'playable_episodes': playable_episodes,
                'generated_time': datetime.now().isoformat()
            } 