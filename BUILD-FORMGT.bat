@echo off
setlocal
cd /d "%~dp0"
py -3 -m pip install -r requirements-build.txt
if errorlevel 1 exit /b 1
py -3 pocket\icon_themes.py --build-icon "assets\app.ico"
if errorlevel 1 exit /b 1
py -3 -m PyInstaller --noconfirm --clean --onedir --windowed --noupx --name Pocket-FORMGT --icon "assets\app.ico" --collect-all PIL --collect-all tkinterdnd2 --hidden-import PIL._imaging --hidden-import PIL._imagingtk --hidden-import win32com.client --hidden-import win32com.client.dynamic --hidden-import pythoncom --hidden-import pywintypes --hidden-import _ctypes --hidden-import _tkinter --hidden-import unicodedata --add-data "assets\app.ico;assets" --distpath "dist\FORMGT" --workpath "build\formgt-work" app.pyw
if errorlevel 1 exit /b 1
echo Built: dist\FORMGT\Pocket-FORMGT\Pocket-FORMGT.exe
