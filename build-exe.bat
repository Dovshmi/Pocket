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
set "COMMAND_FILE=commands\sample_commands.json"
if exist "commands\commands.json" set "COMMAND_FILE=commands\commands.json"
if not exist "%COMMAND_FILE%" (
  echo No command library found. Verify commands\sample_commands.json is present.
  pause
  exit /b 1
)
py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name PocketDesk --icon "assets\app.ico" --collect-all tkinterdnd2 --add-data "assets\app.ico;assets" --add-data "%COMMAND_FILE%;commands" app.pyw
if errorlevel 1 (
  echo Build failed; check the output above.
  pause
  exit /b 1
)
echo.
echo Built: dist\PocketDesk.exe
pause
