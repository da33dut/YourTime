@echo off
setlocal

echo YourTime Builder
echo.

echo [INFO] Installing dependencies...
pip install pystray pillow pyinstaller > nul 2>&1

echo [INFO] Stopping running instance...
taskkill /f /im YourTime.exe > nul 2>&1

echo [INFO] Cleaning up...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

set ICON=img\icon.ico
if exist %ICON% (
    echo [INFO] Icon found.
    set ICONARG=%ICON%
) else (
    echo [WARNING] Icon not found, building without icon.
    set ICONARG=
)

echo [INFO] Building YourTime...
if defined ICONARG (
    pyinstaller --onefile --windowed --icon=%ICONARG% --name=YourTime --add-data "img;img" --add-data "definitions.py;." backend.py
) else (
    pyinstaller --onefile --windowed --name=YourTime --add-data "img;img" --add-data "definitions.py;." backend.py
)

if errorlevel 1 (
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo [INFO] Copying img folder next to exe so the window icon is found at runtime...
if exist img xcopy /e /i /y img dist\img > nul 2>&1

echo.
echo [INFO] Build successful. Output: dist\YourTime.exe
echo [INFO] The dist\img\ folder contains the icon and is required next to the exe.
pause
