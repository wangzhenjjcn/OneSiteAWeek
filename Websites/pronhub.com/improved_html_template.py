#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进的HTML模板生成器
解决文件缺失和CORS问题
"""

def create_improved_html(video_data, folder_path):
    """创建改进的HTML页面"""
    
    # 检查文件是否存在
    import os
    thumbnail_exists = os.path.exists(os.path.join(folder_path, 'thumbnail.jpg'))
    preview_exists = os.path.exists(os.path.join(folder_path, 'preview.webm'))
    
    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{video_data['title']}</title>
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
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
        .file-missing {{
            padding: 20px;
            background: #f8f9fa;
            border: 2px dashed #dee2e6;
            border-radius: 8px;
            text-align: center;
            color: #6c757d;
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
        .m3u8-player-section {{
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            border: 2px solid #007bff;
        }}
        .m3u8-player-container {{
            margin-bottom: 15px;
        }}
        .m3u8-controls {{
            display: flex;
            flex-direction: column;
            gap: 15px;
        }}
        .play-btn {{
            padding: 10px 20px;
            background: #28a745;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            transition: background 0.3s;
        }}
        .play-btn:hover {{
            background: #218838;
        }}
        .quality-buttons {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 10px;
        }}
        .quality-btn {{
            padding: 8px 15px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.3s;
        }}
        .quality-btn:hover {{
            background: #0056b3;
        }}
        .status-message {{
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
            font-weight: bold;
            text-align: center;
        }}
        .status-success {{
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }}
        .status-error {{
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }}
        .cors-notice {{
            background: #fff3cd;
            color: #856404;
            border: 1px solid #ffeaa7;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
        }}
    </style>
</head>
<body>
    <div class="video-container">
        <h1 class="video-title">{video_data['title']}</h1>
        
        <div class="video-info">
            <div class="thumbnail">
                {f'<img src="thumbnail.jpg" alt="{video_data["alt_text"]}" id="thumbnail">' if thumbnail_exists else '''
                <div class="file-missing">
                    <h3>📷 缩略图文件缺失</h3>
                    <p>thumbnail.jpg 文件不存在</p>
                    <p>这不会影响视频播放功能</p>
                </div>
                '''}
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
        
        {f'''
        <div class="video-player">
            <h3>预览视频</h3>
            <video controls>
                <source src="preview.webm" type="video/webm">
                您的浏览器不支持视频播放。
            </video>
        </div>
        ''' if preview_exists else '''
        <div class="video-player">
            <h3>预览视频</h3>
            <div class="file-missing">
                <h3>🎬 预览视频文件缺失</h3>
                <p>preview.webm 文件不存在</p>
                <p>这不会影响m3u8视频播放功能</p>
            </div>
        </div>
        '''}
        
        <div class="cors-notice">
            <h3>⚠️ CORS跨域问题解决方案</h3>
            <p>如果m3u8视频无法播放，请尝试以下方法：</p>
            <ol>
                <li><strong>安装CORS扩展</strong>: Chrome安装"CORS Unblock"，Firefox安装"CORS Everywhere"</li>
                <li><strong>使用本地服务器</strong>: 运行 <code>python -m http.server 8000</code> 然后访问 <code>http://localhost:8000</code></li>
                <li><strong>使用代理服务器</strong>: 运行 <code>python cors_proxy.py</code></li>
            </ol>
        </div>
        
        <div class="m3u8-player-section">
            <h3>🎬 M3U8 视频播放器</h3>
            <div class="m3u8-player-container">
                <video id="m3u8Player" controls style="width: 100%; max-width: 800px; height: auto; border-radius: 8px;">
                    您的浏览器不支持HLS视频播放。
                </video>
            </div>
            <div class="m3u8-controls">
                <button onclick="playBestQuality()" class="play-btn">播放最佳质量</button>
                <div class="quality-buttons">
                    {_generate_quality_buttons(video_data.get('m3u8_urls', []))}
                </div>
            </div>
        </div>
    </div>

    <script>
        let hls = null;
        
        function playM3U8(url) {{
            const video = document.getElementById('m3u8Player');
            if (!video) return;
            
            // 检查URL是否有效
            if (!url || url === 'N/A' || url === '') {{
                showStatus('无效的m3u8地址', 'error');
                return;
            }}
            
            showStatus('正在加载视频...', 'success');
            
            if (Hls.isSupported()) {{
                if (hls) {{
                    hls.destroy();
                }}
                hls = new Hls({{
                    xhrSetup: function(xhr, url) {{
                        // 添加必要的请求头
                        xhr.setRequestHeader('Origin', window.location.origin);
                        xhr.setRequestHeader('Referer', 'https://cn.pornhub.com/');
                    }}
                }});
                
                hls.loadSource(url);
                hls.attachMedia(video);
                hls.on(Hls.Events.MANIFEST_PARSED, function() {{
                    video.play();
                    showStatus('视频加载成功！', 'success');
                }});
                hls.on(Hls.Events.ERROR, function(event, data) {{
                    console.error('HLS错误:', data);
                    if (data.type === 'NETWORK_ERROR' && data.details === 'CORS_ERROR') {{
                        showStatus('跨域访问被阻止，请安装CORS扩展或使用代理', 'error');
                    }} else {{
                        showStatus('视频加载失败，请检查网络连接或尝试其他质量', 'error');
                    }}
                }});
            }} else if (video.canPlayType('application/vnd.apple.mpegurl')) {{
                video.src = url;
                video.addEventListener('loadedmetadata', function() {{
                    video.play();
                    showStatus('视频加载成功！', 'success');
                }});
                video.addEventListener('error', function() {{
                    showStatus('视频加载失败，请检查网络连接', 'error');
                }});
            }} else {{
                showStatus('您的浏览器不支持HLS播放，请使用Chrome或Safari', 'error');
            }}
        }}
        
        function playBestQuality() {{
            const bestUrl = '{video_data.get('best_m3u8_url', '')}';
            if (bestUrl && bestUrl !== 'N/A') {{
                playM3U8(bestUrl);
            }} else {{
                showStatus('没有可用的m3u8地址', 'error');
            }}
        }}
        
        function showStatus(message, type) {{
            const existingStatus = document.querySelector('.status-message');
            if (existingStatus) {{
                existingStatus.remove();
            }}
            
            const statusDiv = document.createElement('div');
            statusDiv.className = `status-message status-${{type}}`;
            statusDiv.textContent = message;
            
            const playerContainer = document.querySelector('.m3u8-player-container');
            if (playerContainer) {{
                playerContainer.parentNode.insertBefore(statusDiv, playerContainer);
            }}
            
            setTimeout(() => {{
                if (statusDiv.parentNode) {{
                    statusDiv.remove();
                }}
            }}, 3000);
        }}
        
        // 页面加载时自动播放最佳质量
        window.addEventListener('load', function() {{
            const bestUrl = '{video_data.get('best_m3u8_url', '')}';
            if (bestUrl && bestUrl !== 'N/A') {{
                setTimeout(() => {{
                    playM3U8(bestUrl);
                }}, 1000);
            }}
        }});
    </script>
</body>
</html>
    """
    
    return html_content

def _generate_quality_buttons(m3u8_urls):
    """生成质量选择按钮HTML"""
    if not m3u8_urls:
        return ""
    
    buttons_html = ""
    quality_priority = ['1080P', '720P', '480P', '240P', 'HD', 'SD']
    
    for i, url in enumerate(m3u8_urls):
        # 尝试从URL中提取质量信息
        quality_name = f"质量 {i+1}"
        for priority in quality_priority:
            if priority in url:
                quality_name = priority
                break
        
        buttons_html += f'<button onclick="playM3U8(\'{url}\')" class="quality-btn">{quality_name}</button>'
    
    return buttons_html

# 测试函数
if __name__ == "__main__":
    test_data = {
        'title': '测试视频',
        'video_id': 'test123',
        'viewkey': 'test_viewkey',
        'duration': '10:30',
        'uploader': '测试用户',
        'views': '1000',
        'video_url': 'https://example.com',
        'alt_text': '测试视频',
        'publish_time': '2024-01-01',
        'categories': [{'name': '测试分类', 'url': '#'}],
        'm3u8_urls': [
            'https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8',
            'https://bitdash-a.akamaihd.net/content/sintel/hls/playlist.m3u8'
        ],
        'best_m3u8_url': 'https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8'
    }
    
    html_content = create_improved_html(test_data, '.')
    
    with open('improved_test.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("改进的HTML模板已生成: improved_test.html") 