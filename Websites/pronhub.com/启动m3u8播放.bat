@echo off
chcp 65001
echo ========================================
echo M3U8播放环境启动脚本
echo ========================================
echo.

echo 1. 启动CORS代理服务器...
start "CORS代理服务器" cmd /k "python cors_proxy.py"

echo 2. 等待3秒让代理服务器启动...
timeout /t 3 /nobreak >nul

echo 3. 启动本地HTTP服务器...
start "本地HTTP服务器" cmd /k "python -m http.server 8000"

echo 4. 等待2秒让HTTP服务器启动...
timeout /t 2 /nobreak >nul

echo 5. 打开浏览器访问页面...
start http://localhost:8000

echo.
echo ========================================
echo 环境启动完成！
echo ========================================
echo.
echo 代理服务器: http://localhost:5000
echo HTTP服务器: http://localhost:8000
echo.
echo 如果HTML文件在data目录中，请访问:
echo http://localhost:8000/data/[viewkey]/index.html
echo.
echo 按任意键退出...
pause >nul 