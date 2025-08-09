# 数据库存储功能说明

## 概述

现在程序已升级为使用 SQLite 数据库存储视频数据，不再创建文件夹和下载缩略图/预览视频。所有采集的数据都保存在 `database/pornhub_videos.db` 文件中。

## 功能特点

✅ **SQLite数据库存储** - 结构化存储视频信息  
✅ **无文件下载** - 不下载缩略图和预览视频，只保存URL  
✅ **完整视频信息** - 视频ID、标题、上传者、观看数、时长、M3U8链接等  
✅ **分类支持** - 支持视频分类的多对多关系  
✅ **M3U8链接管理** - 保存所有质量的M3U8链接  
✅ **数据查询工具** - 提供命令行查询和导出功能  

## 数据库结构

### 主要表

1. **videos** - 视频主表
   - `video_id` - 视频ID (viewkey)
   - `title` - 视频标题
   - `original_url` - 原始视频地址
   - `uploader` - 上传者
   - `views` - 观看次数
   - `duration` - 时长
   - `publish_time` - 发布时间
   - `best_m3u8_url` - 最佳质量M3U8链接
   - `thumbnail_url` - 缩略图URL
   - `preview_url` - 预览视频URL
   - `created_at` - 采集时间

2. **categories** - 分类表
   - `name` - 分类名称

3. **video_categories** - 视频分类关联表
   - 多对多关系表

4. **m3u8_urls** - M3U8链接表
   - 存储不同质量的M3U8链接

## 使用方法

### 1. 数据采集

```bash
# 采集第1页的1页数据
python app.py 1 1

# 采集第1-5页
python app.py 1 5

# 采集第10页开始的3页
python app.py 10 3
```

### 2. 数据查询

```bash
# 查看数据库统计信息
python db_viewer.py --stats

# 查看最近采集的20个视频
python db_viewer.py --recent 20

# 搜索视频（按标题或上传者）
python db_viewer.py --search "关键词"

# 查看特定视频详情
python db_viewer.py --detail "视频ID"

# 导出数据到JSON文件
python db_viewer.py --export "videos.json"

# 导出前100条数据
python db_viewer.py --export "videos.json" --limit 100
```

### 3. 数据库位置

数据库文件保存在：
```
database/pornhub_videos.db
```

## 数据查看示例

### 统计信息
```bash
python db_viewer.py --stats
```
输出：
```
============================================================
📊 数据库统计信息
============================================================
总视频数: 44
总分类数: 0
最新采集时间: 2025-08-09 04:28:53

🔥 热门上传者 (前10):
  1. 用户A                          (15 个视频)
  2. 用户B                          (12 个视频)

🏷️  热门分类 (前10):
  1. 分类A              (25 个视频)
  2. 分类B              (18 个视频)
```

### 视频详情
```bash
python db_viewer.py --detail "ph62af9cfcd3b5c"
```
输出：
```
============================================================
📺 视频详细信息
============================================================
标题: 视频标题
视频ID: ph62af9cfcd3b5c
原始链接: https://cn.pornhub.com/view_video.php?viewkey=ph62af9cfcd3b5c
上传者: 上传者名称
观看数: 229K次观看
最佳M3U8: https://example.com/video.m3u8
缩略图URL: https://example.com/thumb.jpg
预览视频URL: https://example.com/preview.webm
采集时间: 2025-08-09 04:28:53

📹 可用M3U8链接 (4个):
  1. https://example.com/1080p.m3u8
  2. https://example.com/720p.m3u8
  3. https://example.com/480p.m3u8
  4. https://example.com/240p.m3u8
```

## 与原版本的区别

| 功能 | 原版本 | 数据库版本 |
|------|--------|------------|
| 数据存储 | 文件夹 + HTML | SQLite数据库 |
| 缩略图 | 下载到本地 | 只保存URL |
| 预览视频 | 下载到本地 | 只保存URL |
| 数据查询 | 浏览文件夹 | 命令行工具 |
| 数据导出 | 无 | JSON导出 |
| 存储空间 | 大量文件 | 单个数据库文件 |
| 查询速度 | 慢 | 快（索引支持） |

## 数据导出格式

导出的JSON文件格式示例：
```json
[
  {
    "id": 1,
    "video_id": "ph62af9cfcd3b5c",
    "title": "视频标题",
    "original_url": "https://cn.pornhub.com/view_video.php?viewkey=ph62af9cfcd3b5c",
    "uploader": "上传者",
    "views": "229K次观看",
    "best_m3u8_url": "https://example.com/video.m3u8",
    "thumbnail_url": "https://example.com/thumb.jpg",
    "preview_url": "https://example.com/preview.webm",
    "created_at": "2025-08-09 04:28:53",
    "categories": ["分类1", "分类2"],
    "m3u8_urls": [
      "https://example.com/1080p.m3u8",
      "https://example.com/720p.m3u8"
    ]
  }
]
```

## 注意事项

1. **数据迁移**: 如果您之前使用文件版本，新的数据库版本不会读取旧的文件数据
2. **存储空间**: 数据库版本大大减少了存储空间需求
3. **查询性能**: 数据库版本提供了更快的查询和统计功能
4. **数据完整性**: 数据库确保了数据的一致性和完整性
5. **备份**: 建议定期备份 `database/pornhub_videos.db` 文件

## 开发者信息

数据库管理模块 (`database_manager.py`) 提供了完整的数据库操作API，可以轻松扩展新功能。 