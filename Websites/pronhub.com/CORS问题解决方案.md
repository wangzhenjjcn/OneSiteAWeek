# CORS问题解决方案

## 问题描述

在HTML页面中播放m3u8视频时遇到以下错误：
```
Access to XMLHttpRequest at 'https://hv-h.phncdn.com/...' from origin 'null' has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

## 解决方案

### 方案1: 使用本地CORS代理服务器

1. **安装Flask** (如果未安装):
```bash
pip install flask
```

2. **启动代理服务器**:
```bash
python cors_proxy.py
```

3. **访问代理服务器**:
- 打开浏览器访问: http://localhost:5000
- 查看使用说明

4. **使用代理播放视频**:
- 代理服务器会自动为m3u8地址添加CORS头
- HTML页面会自动使用本地代理

### 方案2: 使用浏览器扩展

1. **安装CORS扩展**:
   - Chrome: "CORS Unblock"
   - Firefox: "CORS Everywhere"

2. **启用扩展**:
   - 在浏览器中启用CORS扩展
   - 刷新页面重新加载视频

### 方案3: 使用本地服务器

1. **使用Python启动本地服务器**:
```bash
# 在HTML文件所在目录运行
python -m http.server 8000
```

2. **通过本地服务器访问**:
```
http://localhost:8000/index.html
```

### 方案4: 修改浏览器启动参数

**Chrome浏览器**:
```bash
chrome.exe --disable-web-security --user-data-dir="C:/temp/chrome_dev"
```

**Firefox浏览器**:
1. 在地址栏输入: `about:config`
2. 搜索: `security.fileuri.strict_origin_policy`
3. 设置为: `false`

## 文件缺失问题

### 缩略图文件缺失
- 错误: `thumbnail.jpg:1 Failed to load resource: net::ERR_FILE_NOT_FOUND`
- 解决: HTML页面已添加错误处理，会显示提示信息

### 预览视频文件缺失
- 错误: `preview.webm:1 Failed to load resource: net::ERR_FILE_NOT_FOUND`
- 解决: HTML页面已添加错误处理，会显示提示信息

## 推荐使用方案

### 最佳方案: 本地CORS代理服务器

1. **启动代理服务器**:
```bash
python cors_proxy.py
```

2. **启动本地HTTP服务器**:
```bash
python -m http.server 8000
```

3. **访问页面**:
```
http://localhost:8000/index.html
```

## 故障排除

### 如果代理服务器无法启动
1. 检查端口5000是否被占用
2. 尝试使用其他端口
3. 检查防火墙设置

### 如果视频仍然无法播放
1. 检查网络连接
2. 确认m3u8地址是否有效
3. 尝试使用VPN
4. 检查浏览器控制台错误信息

## 技术说明

### CORS (跨域资源共享)
- 浏览器的安全策略，阻止跨域请求
- 需要服务器设置正确的CORS头
- 本地文件访问时origin为'null'，更容易被阻止

### 解决方案原理
1. **代理服务器**: 在本地添加CORS头
2. **浏览器扩展**: 禁用CORS检查
3. **本地服务器**: 提供正确的origin

## 更新日志

- **v1.1**: 添加CORS代理解决方案
- **v1.2**: 添加文件缺失错误处理
- **v1.3**: 优化错误提示信息 