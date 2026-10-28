@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python 3 is required. Download it from python.org.
  pause
  exit /b 1
)
py -3 -m pip install -r requirements-build.txt
if errorlevel 1 (
  echo Could not install build dependencies. Verify your connection.
  pause
  exit /b 1
)
if not exist "commands\commands.json" (
  echo Missing commands\commands.json. Put your private command file there.
  pause
  exit /b 1
)
py -3 icon_themes.py --build-icon "assets\app.ico"
if errorlevel 1 (
  echo Could not generate default app icon.
  pause
  exit /b 1
)
py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name PocketDesk --icon "assets\app.ico" --collect-all tkinterdnd2 --add-data "assets\app.ico;assets" --hidden-import PIL --hidden-import PIL.ImageTk --add-data "commands\commands.json;commands" app.pyw
if errorlevel 1 (
  echo Build failed; check the output above.
  pause
  exit /b 1
)
echo.
echo Built: dist\PocketDesk.exe
pause
