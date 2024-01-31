@echo off
set "SCRIPT_DIR=%~dp0"
echo install requirements ...
pip3 install -r %SCRIPT_DIR%\requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
echo install requirements finished!
@pause
 
