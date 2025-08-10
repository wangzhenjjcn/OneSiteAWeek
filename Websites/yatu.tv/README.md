# 雅图TV抓取工具

## 功能特性

### 🎯 主要功能
- **分类页面抓取**：支持抓取 `/m-dm/`、`/m-dy/`、`/m-tv/` 等分类页面
- **分页自动处理**：自动检测最后一页（页脚翻页变灰时停止）
- **详情页HTML保存**：将详情页完整HTML代码保存到数据库
- **剧集信息提取**：提取剧集标题、封面、描述、集数等信息
- **播放地址解析**：解析站外片源和播放地址
- **数据持久化**：支持SQLite数据库和本地文件双重保存

### 📁 数据存储
- **数据库**：`database/yatu.tv` (SQLite)
- **本地文件**：`data/` 目录下的HTML和JSON文件
- **详情页HTML**：保存在数据库的 `detail_html` 字段中

## 使用方法

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 运行抓取
```bash
# 使用分类页面抓取（推荐）
python app.py

# 或者修改代码中的参数
crawler.run(use_category_pages=True)  # 分类页面抓取
crawler.run(use_category_pages=False) # 首页抓取
```

### 3. 查询数据库
```bash
python query_database.py
```

## 网站结构分析

### 分类页面
- 动漫：`https://www.yatu.tv/m-dm/`
- 电影：`https://www.yatu.tv/m-dy/`
- 电视剧：`https://www.yatu.tv/m-tv/`
- 特殊页面：`https://www.yatu.tv/m-dm/jc.htm`

### 分页规则
- 第1页：`/m-dm/`
- 第2页：`/m-dm/2.html`
- 第3页：`/m-dm/3.html`
- 最后一页检测：页脚翻页按钮变灰

### 详情页格式
- 格式：`https://www.yatu.tv/m0371/` (m开头+数字ID)
- HTML保存：完整保存到数据库

## 代码优化

### 主要改进
1. **支持分类页面抓取**：添加了 `crawl_all_categories()` 方法
2. **详情页HTML保存**：添加了 `save_detail_html()` 方法
3. **优化分页检测**：改进了 `_is_last_page()` 方法
4. **数据库查询工具**：创建了 `query_database.py` 工具

### 新增方法
- `crawl_all_categories()`: 抓取所有分类页面
- `save_detail_html()`: 保存详情页HTML到数据库
- `get_detail_html()`: 获取详情页HTML
- `_is_last_page()`: 优化分页检测逻辑

## 数据库结构

### series表
```sql
CREATE TABLE series (
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
    detail_html TEXT  -- 新增：详情页HTML
)
```

### episodes表
```sql
CREATE TABLE episodes (
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
```

### sources表
```sql
CREATE TABLE sources (
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
```

## 注意事项

1. **请求频率**：代码中已添加延时，避免请求过快
2. **编码处理**：自动检测和处理GB2312/UTF-8编码
3. **错误处理**：完善的异常处理和日志记录
4. **数据完整性**：支持断点续传和数据恢复

## 文件结构

```
yatu.tv/
├── app.py                 # 主抓取程序
├── database_manager.py    # 数据库管理
├── query_database.py      # 数据库查询工具
├── requirements.txt       # 依赖包
├── README.md             # 说明文档
├── database/             # 数据库目录
│   └── yatu.tv          # SQLite数据库文件
└── data/                # 本地数据目录
    ├── index.html       # 首页
    └── m0371/           # 剧集目录
        ├── index.html   # 剧集页面
        └── info.json    # 剧集信息
``` 