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
if not exist "commands\sample_commands.json" (
  echo Missing public sample command library.
  exit /b 1
)
if not exist "commands\machine_catalog.json" (
  echo Missing machine catalogue.
  exit /b 1
)
if not exist "commands\public_additions.json" (
  echo Missing extra public commands.
  exit /b 1
)
py -3 icon_themes.py --build-icon "assets\app.ico"
if errorlevel 1 (
  echo Could not generate default app icon.
  pause
  exit /b 1
)
py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name PocketDesk --icon "assets\app.ico" --collect-all tkinterdnd2 --add-data "assets\app.ico;assets" --hidden-import PIL --hidden-import PIL.ImageTk --add-data "commands\sample_commands.json;commands" --add-data "commands\machine_catalog.json;commands" --add-data "commands\public_additions.json;commands" app.pyw
if errorlevel 1 (
  echo Build failed; check the output above.
  pause
  exit /b 1
)
echo.
echo Built: dist\PocketDesk.exe
pause
