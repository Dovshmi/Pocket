@echo off
setlocal EnableExtensions
cd /d "%~dp0"
REM Build on Windows using Python 3.11 x64. Target computers need no Python.
REM Use ONLY public example commands; never bundle private commands or note data.
where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python 3.11 x64 is required on the BUILD machine.
  exit /b 1
)
python -c "import sys,struct; assert sys.version_info[:2]==(3,11) and struct.calcsize('P')==8, 'Use 64-bit Python 3.11'"
if errorlevel 1 exit /b 1
if not exist "commands\example_commands.json" (
  echo ERROR: Public example commands are missing.
  exit /b 1
)
python -m pip install --disable-pip-version-check -r requirements-build.txt
if errorlevel 1 exit /b 1
python -m pip check
if errorlevel 1 exit /b 1
python pocket\icon_themes.py --build-icon "assets\app.ico"
if errorlevel 1 exit /b 1
REM Onedir avoids unpacking the program and DLLs into TEMP on every start.
REM No UPX; include required Windows native modules and complete Pillow/TkDnD.
python -m PyInstaller --noconfirm --clean --onedir --windowed --noupx --contents-directory _internal --name PocketDesk --icon "assets\app.ico" --collect-all PIL --collect-all tkinterdnd2 --hidden-import PIL._imaging --hidden-import PIL._imagingtk --hidden-import _ctypes --hidden-import _tkinter --hidden-import unicodedata --add-data "assets\app.ico;assets" --add-data "commands\example_commands.json;commands" --distpath "build\portable-binaries" --workpath "build\portable-work" app.pyw
if errorlevel 1 exit /b 1
python package_portable.py
if errorlevel 1 exit /b 1
echo Portable ZIP prepared in dist\
exit /b 0
