@echo off
chcp 65001 >nul
echo 🔄 数据重新生成工具 - 快速启动
echo =================================
echo.
echo 请选择操作：
echo 1. 查看数据库统计信息
echo 2. 重新生成最新10个视频文件
echo 3. 重新生成最新50个视频文件  
echo 4. 重新生成所有数据（从HTML数据库）
echo 5. 强制更新最新20个视频
echo 6. 自定义参数运行
echo 0. 退出
echo.
set /p choice="请输入选择 (0-6): "

if "%choice%"=="0" goto :end
if "%choice%"=="1" goto :stats
if "%choice%"=="2" goto :gen10
if "%choice%"=="3" goto :gen50
if "%choice%"=="4" goto :genall
if "%choice%"=="5" goto :update20
if "%choice%"=="6" goto :custom
goto :invalid

:stats
echo 📊 显示数据库统计信息...
python generate_data.py --stats
pause
goto :end

:gen10
echo 🔄 重新生成最新10个视频文件...
python generate_data.py --limit 10 --verbose
pause
goto :end

:gen50
echo 🔄 重新生成最新50个视频文件...
python generate_data.py --limit 50
pause
goto :end

:genall
echo 🔄 从HTML数据库重新生成所有数据...
echo 警告：这可能需要很长时间！
set /p confirm="确认继续？(y/N): "
if /i not "%confirm%"=="y" goto :end
python generate_data.py --source html
pause
goto :end

:update20
echo 🔄 强制更新最新20个视频...
python generate_data.py --limit 20 --update --verbose
pause
goto :end

:custom
echo.
echo 自定义参数示例：
echo   --limit 数量          限制处理的视频数量
echo   --update             强制更新已存在文件
echo   --viewkey ID         只处理指定视频ID
echo   --source html/video  选择数据源
echo   --verbose            显示详细信息
echo.
set /p params="请输入参数: "
python generate_data.py %params%
pause
goto :end

:invalid
echo ❌ 无效选择，请重试
pause
goto :end

:end
echo 👋 再见！ 