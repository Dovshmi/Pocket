@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
    echo Install Python 3 from python.org, then run install.bat.
    pause
    exit /b 1
)
py -3 -c "import tkinterdnd2" >nul 2>nul
if errorlevel 1 (
    echo First-run setup: installing native drag-and-drop support...
    py -3 -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Could not install drag-and-drop support. Check internet access, or try install.bat.
        echo You can still run PocketDesk but dragging will not work.
        pause
    )
)
where pyw >nul 2>nul
if not errorlevel 1 (
    start "" pyw -3 "%~dp0app.pyw"
) else (
    start "" py -3 "%~dp0app.pyw"
)
