#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChromeDriver下载脚本
"""

import os
import sys
import requests
import zipfile
import platform
from pathlib import Path

def get_chrome_version():
    """获取Chrome版本"""
    try:
        import subprocess
        
        if platform.system() == "Windows":
            # Windows系统
            cmd = r'reg query "HKEY_CURRENT_USER\Software\Google\Chrome\BLBeacon" /v version'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                version_line = result.stdout.strip().split('\n')[-1]
                version = version_line.split()[-1]
                return version.split('.')[0]  # 只返回主版本号
        else:
            # Linux/macOS系统
            cmd = "google-chrome --version"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.strip().split()[-1]
                return version.split('.')[0]  # 只返回主版本号
                
    except Exception as e:
        print(f"获取Chrome版本失败: {e}")
    
    return None

def download_chromedriver(version=None):
    """下载ChromeDriver"""
    try:
        if not version:
            version = get_chrome_version()
        
        if not version:
            print("无法获取Chrome版本，使用默认版本114")
            version = "114"
        
        print(f"Chrome版本: {version}")
        
        # 确定系统架构
        if platform.system() == "Windows":
            if platform.machine().endswith('64'):
                platform_name = "win64"
            else:
                platform_name = "win32"
        elif platform.system() == "Linux":
            platform_name = "linux64"
        elif platform.system() == "Darwin":
            platform_name = "mac64"
        else:
            print(f"不支持的操作系统: {platform.system()}")
            return False
        
        # 使用国内镜像源（避免谷歌链接）
        mirror_urls = [
            f"https://npm.taobao.org/mirrors/chromedriver/{version}.0.6045.105/chromedriver_{platform_name}.zip",
            f"https://cdn.npmmirror.com/binaries/chromedriver/{version}.0.6045.105/chromedriver_{platform_name}.zip",
            f"https://registry.npmmirror.com/-/binary/chromedriver/{version}.0.6045.105/chromedriver_{platform_name}.zip"
        ]
        
        # 尝试不同的镜像源
        for i, download_url in enumerate(mirror_urls, 1):
            try:
                print(f"尝试镜像源 {i}: {download_url}")
                
                # 下载文件
                print("正在下载ChromeDriver...")
                response = requests.get(download_url, timeout=30, verify=False)
                
                if response.status_code == 200:
                    # 保存文件
                    zip_path = "chromedriver.zip"
                    with open(zip_path, 'wb') as f:
                        f.write(response.content)
                    
                    # 解压文件
                    print("正在解压ChromeDriver...")
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall('.')
                    
                    # 删除zip文件
                    os.remove(zip_path)
                    
                    # 设置执行权限（Linux/macOS）
                    if platform.system() != "Windows":
                        os.chmod("chromedriver", 0o755)
                    
                    print("✓ ChromeDriver下载完成")
                    return True
                else:
                    print(f"镜像源 {i} 下载失败，状态码: {response.status_code}")
                    continue
                    
            except Exception as e:
                print(f"镜像源 {i} 下载出错: {e}")
                continue
        
        print("所有镜像源都下载失败")
        return False
            
    except Exception as e:
        print(f"下载ChromeDriver时出错: {e}")
        return False

def check_chromedriver():
    """检查ChromeDriver是否存在"""
    chromedriver_name = "chromedriver.exe" if platform.system() == "Windows" else "chromedriver"
    chromedriver_path = os.path.join(os.getcwd(), chromedriver_name)
    
    if os.path.exists(chromedriver_path):
        print(f"✓ ChromeDriver已存在: {chromedriver_path}")
        print(f"  文件大小: {os.path.getsize(chromedriver_path)} 字节")
        return True
    else:
        print(f"✗ ChromeDriver不存在: {chromedriver_path}")
        return False

def main():
    """主函数"""
    print("ChromeDriver下载工具")
    print("=" * 50)
    
    # 检查是否已存在
    if check_chromedriver():
        print("\nChromeDriver已存在，无需下载")
        return
    
    # 获取Chrome版本
    version = get_chrome_version()
    if version:
        print(f"检测到Chrome版本: {version}")
    else:
        print("无法检测Chrome版本，将使用默认版本")
        version = None
    
    # 下载ChromeDriver
    if download_chromedriver(version):
        print("\n✓ ChromeDriver下载成功")
        check_chromedriver()
    else:
        print("\n✗ ChromeDriver下载失败")
        print("\n手动下载方法:")
        print("1. 访问: https://chromedriver.chromium.org/")
        print("2. 下载对应版本的ChromeDriver")
        print("3. 解压并放置在项目根目录")

if __name__ == "__main__":
    main() 