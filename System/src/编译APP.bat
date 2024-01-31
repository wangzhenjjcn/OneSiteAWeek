set "SCRIPT_DIR=%~dp0"
pip3 install --upgrade pip
pip3 install  -r requirement.txt
pip3 install  -r requirements.txt
pip3 install pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple
PyInstaller -y -F -w -n YaTuDownLoader --icon=favicon.gif --additional-hooks=extra-hooks --additional-hooks-dir "%SCRIPT_DIR%\BIn" %SCRIPT_DIR%\app.py 
@pause
 