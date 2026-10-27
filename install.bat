@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
    echo Python 3 is required: https://www.python.org/downloads/windows/
    pause
    exit /b 1
)
echo Installing PocketDesk optional drag-and-drop dependency...
py -3 -m pip install -r requirements.txt
if errorlevel 1 (
    echo Installation failed. Make sure you have an internet connection, then retry.
    pause
    exit /b 1
)
echo.
echo Setup complete. Double-click run.bat to launch PocketDesk.
pause
