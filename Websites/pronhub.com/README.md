# Pornhub视频数据抓取工具

这个Python脚本用于抓取Pornhub网站的视频数据，包括视频信息、缩略图和预览视频。

## 功能特点

- 使用socks5代理进行网络请求
- 抓取视频列表页面的所有视频信息
- 下载视频缩略图和预览视频
- 为每个视频创建独立的HTML页面
- 支持分页抓取

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

1. 确保socks5代理服务器运行在 `127.0.0.1:12345`
2. 运行脚本：

```bash
python app.py
```

## 配置说明

### 代理设置
脚本默认使用socks5代理：`127.0.0.1:12345`

如需修改代理设置，请编辑 `app.py` 文件中的 `proxies` 配置：

```python
self.proxies = {
    'http': 'socks5://127.0.0.1:12345',
    'https': 'socks5://127.0.0.1:12345'
}
```

### 抓取页数
默认抓取第1-5页的数据，可在 `run()` 方法中修改：

```python
scraper.run(start_page=1, end_page=5)
```

## 输出结构

脚本会在 `app.py` 所在目录下创建 `data` 文件夹，每个视频以viewkey为文件夹名：

```
data/
├── 6870540048f36/
│   ├── index.html          # 视频信息页面
│   ├── thumbnail.jpg       # 缩略图
│   └── preview.webm        # 预览视频
├── 6870540048f37/
│   ├── index.html
│   ├── thumbnail.jpg
│   └── preview.webm
└── ...
```

## 抓取的数据字段

- 视频ID (video_id)
- ViewKey (viewkey)
- 视频标题 (title)
- 视频链接 (video_url)
- 缩略图URL (thumbnail_url)
- 缩略图描述 (alt_text)
- 预览视频URL (preview_url)
- 视频时长 (duration)
- 上传者 (uploader)
- 观看次数 (views)
- 上传时间 (added_time)

## 注意事项

1. 请确保遵守网站的使用条款和robots.txt
2. 建议在抓取时添加适当的延迟，避免对服务器造成过大压力
3. 使用代理时请确保代理服务器正常运行
4. 抓取的内容仅供学习和研究使用

## 错误处理

脚本包含完善的错误处理机制：
- 网络请求失败时会重试
- 解析失败时会跳过该视频继续处理
- 下载失败时会记录错误信息

## 日志输出

脚本运行时会输出详细的进度信息：
- 当前抓取的页数
- 每页找到的视频数量
- 下载进度
- 错误信息 