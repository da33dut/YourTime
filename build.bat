@echo off
title YourTime Builder

echo.
echo === YourTime Builder ===
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    pause
    exit /b 1
)

pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo INFO: Installing PyInstaller...
    pip install pyinstaller
)

echo INFO: Installing dependencies...
pip install pystray pillow >nul

echo INFO: Stopping running instance...
taskkill /f /im YourTime.exe >nul 2>&1
timeout /t 1 /nobreak >nul

echo INFO: Cleaning up...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist YourTime.spec del /q YourTime.spec
timeout /t 2 /nobreak >nul

set ICON_ARG=
if exist tools\icon.ico (
    set ICON_ARG=--icon=tools\icon.ico
    echo INFO: Icon found.
) else (
    echo WARN: Icon not found, building without icon.
)

echo INFO: Building YourTime...
pyinstaller --onefile --noconsole --noconfirm --name YourTime ^
 %ICON_ARG% ^
 --add-data definitions.py;. ^
 --add-data frontend.py;. ^
 backend.py

if errorlevel 1 (
    echo ERROR: Build failed!
    pause
    exit /b 1
)

if exist config.json copy /y config.json dist\config.json >nul
if exist tools xcopy /e /i /y tools dist\tools >nul

echo INFO: Unblocking EXE...
powershell -Command "Unblock-File 'dist\YourTime.exe'"

echo.
echo === Build successful: dist\YourTime.exe ===
echo.
pause
