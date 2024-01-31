set "SCRIPT_DIR=%~dp0"
pip3 install --upgrade pip

pip3 install pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple

rd /s /q "%SCRIPT_DIR%\Bin\Logs"
PyInstaller -y -F -n App --add-data "%SCRIPT_DIR%\Bin;./Bin" %SCRIPT_DIR%\m3u8Downloader.py 

@pause
 