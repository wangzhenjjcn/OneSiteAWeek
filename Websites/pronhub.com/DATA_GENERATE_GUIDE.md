# 数据重新生成工具使用指南

## 📖 概述

`generate_data.py` 是一个专门用于从数据库重新生成 `data` 目录下采集文件的独立工具。它可以从两种数据源重新构建完整的采集数据：

1. **HTML数据库** (`pornhub.com.html.db`) - 从保存的原始HTML重新解析生成
2. **视频数据库** (`pornhub_videos.db`) - 从结构化的视频数据重新生成

## 🚀 基本使用方法

### 1. 重新生成所有数据（推荐）
```bash
# 从HTML数据库重新生成所有数据（默认）
python generate_data.py

# 明确指定从HTML数据库生成
python generate_data.py --source html
```

### 2. 从视频数据库生成
```bash
# 从结构化视频数据库生成
python generate_data.py --source video
```

### 3. 限制处理数量
```bash
# 只处理最新的10个视频
python generate_data.py --limit 10

# 从视频数据库处理最新20个
python generate_data.py --source video --limit 20
```

### 4. 强制更新已存在的文件
```bash
# 强制重新生成所有文件（覆盖现有）
python generate_data.py --update

# 强制更新前50个视频
python generate_data.py --limit 50 --update
```

### 5. 处理指定视频
```bash
# 只处理指定的视频ID
python generate_data.py --viewkey 65f9642b4a5f8

# 强制重新处理指定视频
python generate_data.py --viewkey 65f9642b4a5f8 --update
```

### 6. 显示详细信息
```bash
# 显示详细的处理过程
python generate_data.py --verbose

# 查看数据库统计信息
python generate_data.py --stats
```

## 🔧 参数详解

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `--source` | 选择 | 数据源：`html`（默认）或 `video` | `--source html` |
| `--limit` | 数字 | 限制处理的视频数量 | `--limit 50` |
| `--update` | 开关 | 强制更新已存在的文件 | `--update` |
| `--viewkey` | 字符串 | 只处理指定的视频ID | `--viewkey abc123` |
| `--verbose` | 开关 | 显示详细处理信息 | `--verbose` |
| `--stats` | 开关 | 显示数据库统计信息 | `--stats` |

## 📊 数据源对比

### HTML数据库源 (推荐)
- **优点**：
  - 数据最完整，包含原始HTML所有信息
  - 可以重新解析获取最新的提取逻辑结果
  - 支持数据修复和补全
- **缺点**：
  - 处理速度相对较慢
  - 需要重新解析HTML

### 视频数据库源
- **优点**：
  - 处理速度快
  - 直接使用结构化数据
- **缺点**：
  - 数据可能不完整（取决于采集时的解析质量）
  - 无法获取HTML中的新信息

## 🎯 使用场景

### 1. 数据恢复
```bash
# data目录丢失，从HTML数据库恢复所有数据
python generate_data.py --source html

# 快速从视频数据库恢复基本文件
python generate_data.py --source video
```

### 2. 增量更新
```bash
# 只更新最新的100个视频文件
python generate_data.py --limit 100

# 强制重新生成最近50个视频
python generate_data.py --limit 50 --update
```

### 3. 单个视频修复
```bash
# 修复特定视频的文件
python generate_data.py --viewkey 65f9642b4a5f8 --update --verbose
```

### 4. 批量测试
```bash
# 测试前10个视频的生成效果
python generate_data.py --limit 10 --verbose
```

## 📂 生成的文件结构

每个视频会在 `data/{viewkey}/` 目录下生成：

```
data/
├── 65f9642b4a5f8/
│   ├── index.html          # 视频展示页面
│   ├── thumbnail.jpg       # 缩略图文件
│   ├── preview.webm        # 预览视频文件
│   └── collection_log.txt  # 采集日志文件
└── ...
```

## ⚡ 性能优化

### 多线程下载
工具会自动启用多线程下载缩略图和预览视频，提高处理效率。

### 智能跳过
- 默认跳过已存在且完整的文件
- 使用 `--update` 强制重新生成

### 内存管理
- 批量处理时自动管理内存使用
- 大量数据时建议分批处理：`--limit 100`

## 🛠️ 故障排除

### 1. 数据库连接错误
```bash
# 检查数据库状态
python generate_data.py --stats
```

### 2. 文件权限问题
确保有 `data` 目录的写入权限

### 3. 网络下载失败
```bash
# 使用详细模式查看错误
python generate_data.py --verbose
```

### 4. 内存不足
```bash
# 减少批处理数量
python generate_data.py --limit 50
```

## 📝 日志和输出

### 处理统计
```
📊 处理统计:
  - 成功处理: 45
  - 处理失败: 2  
  - 跳过: 3
  - 总计: 50
```

### 详细模式输出
使用 `--verbose` 参数可以看到：
- 每个视频的处理状态
- 文件下载进度
- 错误详情和堆栈信息

## 🔄 与app.py的关系

- `generate_data.py` 是独立工具，调用 `app.py` 中的功能
- 不影响正常的采集流程
- 可以与 `app.py --regenerate` 功能互补使用

## 💡 最佳实践

1. **首次使用**：建议先用 `--limit 5 --verbose` 测试
2. **大批量处理**：使用 `--limit` 分批处理避免内存问题
3. **数据恢复**：优先使用 `--source html` 获得最完整数据
4. **快速预览**：使用 `--source video` 快速生成基本文件
5. **问题调试**：始终使用 `--verbose` 参数查看详细信息

---

📞 **需要帮助？** 查看 `README.md` 或使用 `python generate_data.py --help` 