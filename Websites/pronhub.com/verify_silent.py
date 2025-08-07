#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
静默模式验证脚本
"""

from config import DEBUG, SCRAPER_CONFIG

def verify_silent_config():
    """验证静默模式配置"""
    print("=== 静默模式配置验证 ===")
    
    print(f"DEBUG['verbose']: {DEBUG['verbose']}")
    print(f"SCRAPER_CONFIG['show_worker_info']: {SCRAPER_CONFIG['show_worker_info']}")
    
    if not DEBUG['verbose'] and not SCRAPER_CONFIG['show_worker_info']:
        print("✓ 静默模式已正确配置")
        return True
    else:
        print("✗ 静默模式配置错误")
        return False

if __name__ == "__main__":
    verify_silent_config() 