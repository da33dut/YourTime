@echo off
setlocal

REM ── YourTime – one-click PyInstaller build ─────────────────────────────────
REM Output: dist\YourTime.exe  (standalone, no Python required on target)
REM
REM Requirements:
REM   pip install pyinstaller pystray pillow

set NAME=YourTime
set ENTRY=backend.py
echo [INFO] Stopping running instance...
taskkill /f /im YourTime.exe > nul 2>&1

echo [INFO] Cleaning up...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

set ICON=img\icon.ico

pyinstaller ^
  --onefile ^
  --windowed ^
  --name "%NAME%" ^
  --icon "%ICON%" ^
  --add-data "img;img" ^
  --add-data "definitions.py;." ^
  --add-data "frontend.py;." ^
  "%ENTRY%"

echo.
if exist "dist\%NAME%.exe" (
    echo BUILD OK  --^>  dist\%NAME%.exe
) else (
    echo BUILD FAILED - check output above.
    exit /b 1
)

echo [INFO] Copying img folder next to exe...
if exist img xcopy /e /i /y img dist\img > nul 2>&1

echo.
echo [INFO] Build successful. Output: dist\YourTime.exe
echo [INFO] The dist\img\ folder is required next to the exe.
endlocal
