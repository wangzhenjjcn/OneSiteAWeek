#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class YatuTVDatabase:
    def __init__(self, db_path=None):
        """初始化数据库连接"""
        if db_path is None:
            # 确保数据库保存在yatu.tv目录下
            script_dir = os.path.dirname(os.path.abspath(__file__))
            self.db_path = os.path.join(script_dir, "database", "yatu.tv")
        else:
            self.db_path = db_path
            
        self.db_dir = os.path.dirname(self.db_path)
        
        # 确保database目录存在
        if not os.path.exists(self.db_dir):
            os.makedirs(self.db_dir)
        
        self.init_database()
    
    def init_database(self):
        """初始化数据库表结构"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建剧集基本信息表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS series (
                series_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                series_url TEXT,
                category TEXT,
                description TEXT,
                director TEXT,
                screenwriter TEXT,
                language TEXT,
                release_date TEXT,
                rating REAL,
                popularity INTEGER,
                line_count INTEGER,
                crawl_time TEXT,
                update_time TEXT,
                detail_html TEXT
            )
            ''')
            
            # 创建剧集集数表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                series_id TEXT,
                episode_id TEXT,
                episode_number INTEGER,
                episode_title TEXT,
                source_type TEXT,
                source_url TEXT,
                playframe_url TEXT,
                crawl_time TEXT,
                FOREIGN KEY (series_id) REFERENCES series (series_id),
                UNIQUE(series_id, episode_id)
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
                crawl_time TEXT,
                FOREIGN KEY (series_id) REFERENCES series (series_id),
                UNIQUE(series_id, episode_id, source_id)
            )
            ''')
            
            conn.commit()
            conn.close()
            logger.info(f"数据库初始化完成: {self.db_path}")
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    def save_series(self, series_info):
        """保存剧集基本信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 提取meta信息
            meta_info = series_info.get('meta_info', {})
            
            cursor.execute('''
            INSERT OR REPLACE INTO series (
                series_id, title, series_url, category, description,
                director, screenwriter, language, release_date, rating,
                popularity, line_count, crawl_time, update_time, detail_html
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                series_info.get('series_id'),
                series_info.get('title'),
                series_info.get('url'),
                ','.join(meta_info.get('categories', [])),
                series_info.get('description'),
                meta_info.get('director'),
                meta_info.get('screenwriter'),
                meta_info.get('language'),
                meta_info.get('year'),
                meta_info.get('rating'),
                meta_info.get('popularity'),
                len(series_info.get('episodes', [])),
                series_info.get('crawl_time'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                series_info.get('detail_html')
            ))
            
            conn.commit()
            conn.close()
            logger.info(f"剧集信息已保存到数据库: {series_info.get('series_id')}")
            
        except Exception as e:
            logger.error(f"保存剧集信息失败: {e}")
            raise
    
    def save_episode(self, series_id, episode_info):
        """保存单集信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT OR REPLACE INTO episodes (
                series_id, episode_id, episode_number, episode_title,
                source_type, source_url, playframe_url, crawl_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                series_id,
                episode_info.get('episode'),
                episode_info.get('episode_num'),
                episode_info.get('episode_title', ''),
                episode_info.get('video_source'),
                episode_info.get('url'),
                episode_info.get('playframe_url'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            conn.commit()
            conn.close()
            logger.debug(f"集数信息已保存: {series_id} - {episode_info.get('episode')}")
            
        except Exception as e:
            logger.error(f"保存集数信息失败: {e}")
            raise
    
    def save_source(self, series_id, episode_id, source_info):
        """保存片源信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT OR REPLACE INTO sources (
                series_id, episode_id, source_id, source_name,
                source_url, real_url, crawl_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                series_id,
                episode_id,
                source_info.get('source_id'),
                source_info.get('source_name'),
                source_info.get('source_url'),
                source_info.get('real_url'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            conn.commit()
            conn.close()
            logger.debug(f"片源信息已保存: {series_id} - {episode_id} - {source_info.get('source_id')}")
            
        except Exception as e:
            logger.error(f"保存片源信息失败: {e}")
            raise
    
    def save_detail_html(self, series_id, html_content):
        """保存详情页HTML到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            UPDATE series SET detail_html = ?, update_time = ? WHERE series_id = ?
            ''', (
                html_content,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                series_id
            ))
            
            conn.commit()
            conn.close()
            logger.debug(f"详情页HTML已保存: {series_id}")
            
        except Exception as e:
            logger.error(f"保存详情页HTML失败: {e}")
            raise
    
    def get_detail_html(self, series_id):
        """获取详情页HTML"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT detail_html FROM series WHERE series_id = ?', (series_id,))
            result = cursor.fetchone()
            
            conn.close()
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"获取详情页HTML失败: {e}")
            return None
    
    def is_series_crawled(self, series_id):
        """检查剧集是否已抓取"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM series WHERE series_id = ?', (series_id,))
            count = cursor.fetchone()[0]
            
            conn.close()
            return count > 0
            
        except Exception as e:
            logger.error(f"检查剧集状态失败: {e}")
            return False
    
    def is_episode_crawled(self, series_id, episode_id):
        """检查集数是否已抓取"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT COUNT(*) FROM episodes 
            WHERE series_id = ? AND episode_id = ?
            ''', (series_id, episode_id))
            count = cursor.fetchone()[0]
            
            conn.close()
            return count > 0
            
        except Exception as e:
            logger.error(f"检查集数状态失败: {e}")
            return False
    
    def is_source_crawled(self, series_id, episode_id, source_id):
        """检查片源是否已抓取"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT COUNT(*) FROM sources 
            WHERE series_id = ? AND episode_id = ? AND source_id = ?
            ''', (series_id, episode_id, source_id))
            count = cursor.fetchone()[0]
            
            conn.close()
            return count > 0
            
        except Exception as e:
            logger.error(f"检查片源状态失败: {e}")
            return False
    
    def get_series_stats(self):
        """获取数据库统计信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 剧集统计
            cursor.execute('SELECT COUNT(*) FROM series')
            series_count = cursor.fetchone()[0]
            
            # 集数统计
            cursor.execute('SELECT COUNT(*) FROM episodes')
            episodes_count = cursor.fetchone()[0]
            
            # 集数统计（所有集数都算成功，因为只保存链接）
            successful_episodes = episodes_count
            
            # 片源统计
            cursor.execute('SELECT COUNT(*) FROM sources')
            sources_count = cursor.fetchone()[0]
            
            # 片源统计（所有片源都算成功，因为只保存链接）
            successful_sources = sources_count
            
            conn.close()
            
            return {
                'series_count': series_count,
                'episodes_count': episodes_count,
                'successful_episodes': successful_episodes,
                'sources_count': sources_count,
                'successful_sources': successful_sources,
                'episode_success_rate': (successful_episodes / episodes_count * 100) if episodes_count > 0 else 0,
                'source_success_rate': (successful_sources / sources_count * 100) if sources_count > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return None 