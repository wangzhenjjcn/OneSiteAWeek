#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地CORS代理服务器
用于解决m3u8播放的跨域问题
"""

from flask import Flask, request, Response
import requests
import urllib.parse

app = Flask(__name__)

@app.route('/proxy/<path:url>')
def proxy(url):
    """代理请求"""
    try:
        # 解码URL
        decoded_url = urllib.parse.unquote(url)
        
        # 设置请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://cn.pornhub.com/',
            'Origin': 'https://cn.pornhub.com'
        }
        
        # 发送请求
        response = requests.get(decoded_url, headers=headers, stream=True, verify=False)
        
        # 设置CORS头
        cors_headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Content-Type': response.headers.get('Content-Type', 'application/octet-stream')
        }
        
        return Response(
            response.iter_content(chunk_size=8192),
            status=response.status_code,
            headers=cors_headers
        )
        
    except Exception as e:
        return f"代理错误: {str(e)}", 500

@app.route('/')
def index():
    """主页"""
    return """
    <h1>本地CORS代理服务器</h1>
    <p>使用方法: http://localhost:5000/proxy/URL</p>
    <p>例如: http://localhost:5000/proxy/https://example.com/video.m3u8</p>
    """

if __name__ == '__main__':
    print("启动CORS代理服务器...")
    print("访问 http://localhost:5000 查看使用说明")
    print("按 Ctrl+C 停止服务器")
    app.run(host='0.0.0.0', port=5000, debug=True) 