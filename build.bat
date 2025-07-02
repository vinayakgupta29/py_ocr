@echo off
rem =========================================================
rem  Portable build script for “MyApp”  (CMD / .bat version)
rem ---------------------------------------------------------
rem  Usage:   build        – normal build
rem           build clean  – wipe \build first
rem ---------------------------------------------------------
rem  Requires: Python 3.x on PATH
rem            requirements.txt with “pyinstaller”
rem =========================================================

setlocal EnableDelayedExpansion

rem --------- project-wide paths ----------------------------
set "PROJ=%~dp0"
if "%PROJ:~-1%"=="\" set "PROJ=%PROJ:~0,-1%"   
rem drop trailing backslash
set "POPPLER_SRC=%PROJ%\lib\poppler"
set "TESSERACT_SRC=%PROJ%\lib\tesseract"
set "MAINPY=%PROJ%\main.py"

set "OUT_BIN=%PROJ%\build\release\app\bin"
set "OUT_LIB=%PROJ%\build\release\app\lib"
set "WORK=%PROJ%\build\obj"
set "SPEC=%PROJ%\build"
set "APPNAME=SarasOCR"
set "DIST=%PROJ%\build\release\myapp\bin"

echo "%POPPLER_SRC% %TESS_SRC%"
echo "%PROJ% %CD%"
:: ─── 2. sanity-check resource folders ────────────────────────
if not exist "%POPPLER_SRC%" (
    echo ERROR: Poppler folder not found at "%POPPLER_SRC%"
    pause
    exit /b 1
)
if not exist "%TESSERACT_SRC%" (
    echo ERROR: Tesseract folder not found at "%TESS_SRC%"
    pause
    exit /b 1
)

rem --------- optional clean -------------------------------
echo Cleaning existing build ...
rmdir /S /Q "%PROJ%\build" 2>nul


rem --------- make sure build deps exist -------------------
echo.
echo Installing/confirming build requirements ...
python -m pip install --quiet --requirement "%PROJ%\requirements.txt"
if errorlevel 1 (
    echo [ERROR] pip failed -- is Python on PATH?  Aborting...
    exit /b 1
)

rem --------- run PyInstaller (ONEDIR, easier to unpack) ---

echo === Running PyInstaller ===
pyinstaller ^
  --noconfirm ^
  --onedir ^
  --name "%APPNAME%" ^
  --distpath "%DIST%" ^
  --contents-directory "lib"^
  --workpath "%PROJ%\build\obj" ^
  --specpath "%PROJ%\build" ^
  --add-data "%POPPLER_SRC%;lib\poppler" ^
  --add-data "%TESSERACT_SRC%;lib\tesseract" ^
    --collect-binaries cv2^
    "%MAINPY%"
if errorlevel 1 (
    echo [ERROR] PyInstaller failed – see log above.
    exit /b 1
)

rem --------- verify output folder -------------------------
if not exist "%OUT_BIN%\myapp\myapp.exe" (
    echo [ERROR] Expected "%OUT_BIN%\myapp\myapp.exe" not found – build incomplete.
    exit /b 1
)

rem --------- arrange final layout -------------------------
echo.
echo Copying runtime files ...
rmdir /S /Q "%OUT_LIB%" 2>nul
mkdir "%OUT_LIB%" 2>nul

rem 1.  move DLLs/.pyd/.pyz etc. into lib
robocopy "%OUT_BIN%\myapp" "%OUT_LIB%" /E >nul
if errorlevel 8 (
    echo [ERROR] robocopy failed copying libs. Aborting.
    exit /b 1
)

rem 2.  move the exe up one level (bin already = OUT_BIN)
move /Y "%OUT_BIN%\myapp\myapp.exe" "%OUT_BIN%\myapp.exe" >nul

rem 3.  delete the now-empty subfolder
rmdir /S /Q "%OUT_BIN%\myapp" 2>nul

echo.
echo ========================================================
echo  ✔ Build finished successfully!
echo    Portable app is in  ^<build\release\app^>
echo    Zip that folder and share it.
echo ========================================================
endlocal
