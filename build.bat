@echo off
REM Run this from the project root (where main.py lives).
REM Requires: pip install pyinstaller pywin32 pypdf pdfplumber pdf2image pytesseract openpyxl

setlocal
set APP_NAME=PDF-Toolkit

echo.
echo === Cleaning previous build ===
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

echo.
echo === Running PyInstaller (onedir, console) ===
python -m PyInstaller --onedir --console --name "%APP_NAME%" ^
  --hidden-import win32print ^
  --hidden-import win32api ^
  --collect-submodules modules ^
  main.py

if not exist "dist\%APP_NAME%" (
    echo Build failed - dist folder not found.
    exit /b 1
)

echo.
echo === Copying bundled vendor tools into dist folder ===
robocopy vendor "dist\%APP_NAME%\vendor" /E
REM robocopy exit codes 0-7 are success; treat 8+ as failure
if %ERRORLEVEL% GEQ 8 (
    echo robocopy reported an error copying vendor tools.
    exit /b 1
)

echo.
echo === Done ===
echo Self-contained app is in: dist\%APP_NAME%\
echo Test it by copying that folder to a machine with none of these tools installed.
endlocal