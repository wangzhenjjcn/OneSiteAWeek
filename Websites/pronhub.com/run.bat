@echo off
chcp 65001
echo 正在启动Pornhub视频抓取工具...
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python
    pause
    exit /b 1
)

REM 安装依赖
echo 正在安装依赖包...
pip install -r requirements.txt

REM 运行主程序
echo.
echo 开始抓取视频数据...
python app.py

echo.
echo 程序执行完成！
pause 