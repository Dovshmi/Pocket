@echo off
setlocal
cd /d "%~dp0"
REM Build only from public example_commands.json. Never bundle commands/commands.json.
where py >nul 2>nul
if errorlevel 1 (
  echo Python 3 is required on the BUILD machine only.
  exit /b 1
)
py -3 -m pip install -r requirements-build.txt
if errorlevel 1 exit /b 1
py -3 icon_themes.py --build-icon "assets\app.ico"
if errorlevel 1 exit /b 1
if not exist "commands\example_commands.json" (
  echo Missing safe example commands. Build cancelled.
  exit /b 1
)
REM Separate temporary build outputs; never delete a user's existing portable folder.
py -3 -m PyInstaller --noconfirm --clean --onedir --windowed --name PocketDesk --icon "assets\app.ico" --collect-all tkinterdnd2 --hidden-import PIL --hidden-import PIL.ImageTk --add-data "assets\app.ico;assets" --add-data "commands\example_commands.json;commands" --distpath "build\portable-binaries" --workpath "build\portable-work" --specpath "build\portable-spec" app.pyw
if errorlevel 1 exit /b 1
py -3 package_portable.py
if errorlevel 1 exit /b 1
echo Pocket Portable archive created in dist\
