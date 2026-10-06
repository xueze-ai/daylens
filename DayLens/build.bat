@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Please run setup-build.ps1 first.
  exit /b 1
)
call .venv\Scripts\activate.bat
set /p VERSION=<version.txt
python -m PyInstaller --noconfirm --clean --onedir --windowed --name DayLens_v%VERSION% --version-file version_info.txt --icon assets\daylens.ico --add-data "assets\logo.png;assets" --add-data "qt.conf;." --hidden-import win32timezone main.py
if errorlevel 1 exit /b %errorlevel%
echo Built: %CD%\dist\DayLens_v%VERSION%\DayLens_v%VERSION%.exe
