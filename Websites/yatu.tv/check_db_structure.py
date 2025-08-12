#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os

def check_database_structure():
    """检查数据库表结构"""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database", "yatu.tv")
    
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return
    
    print(f"检查数据库: {db_path}")
    print("=" * 50)
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"数据库中的表: {[table[0] for table in tables]}")
        print()
        
        for table_name in [table[0] for table in tables]:
            print(f"表: {table_name}")
            print("-" * 30)
            
            # 获取表结构
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            for col in columns:
                col_id, col_name, col_type, not_null, default_val, pk = col
                print(f"  {col_name} ({col_type}) {'NOT NULL' if not_null else 'NULL'} {'PRIMARY KEY' if pk else ''}")
            
            # 获取记录数
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            print(f"  记录数: {count}")
            print()

if __name__ == "__main__":
    check_database_structure() 