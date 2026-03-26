@REM Created by XWZ
@REM ◕‿◕ Distributed for free at:
@REM https://github.com/nicolaiprodromov/puree
@REM ╔═════════════════════════════════╗
@REM ║  ██   ██  ██      ██  ████████  ║
@REM ║   ██ ██   ██  ██  ██       ██   ║
@REM ║    ███    ██  ██  ██     ██     ║
@REM ║   ██ ██   ██  ██  ██   ██       ║
@REM ║  ██   ██   ████████   ████████  ║
@REM ╚═════════════════════════════════╝
@echo off
setlocal enabledelayedexpansion

set build_dir=%cd%
cd /d "%~dp0\.."
set addon_dir=%cd%

echo working from: %addon_dir%

where blender >nul 2>nul
if errorlevel 1 (
    echo ERROR: 'blender' not found on PATH!
    echo Please ensure Blender is installed and available in your system PATH.
    exit /b 1
)

set "blender_exe=blender"

for /f "usebackq tokens=1* delims==" %%a in (`findstr /r "^name" blender_manifest.toml`) do (
    set "addon_name=%%b"
    set "addon_name=!addon_name: =!"
    set "addon_name=!addon_name:"=!"
)

for /f "usebackq tokens=1* delims==" %%a in (`findstr /r "^version" blender_manifest.toml`) do (
    set "version=%%b"
    set "version=!version: =!"
    set "version=!version:"=!"
)

set addon_name=%addon_name: =_%

echo building: %addon_name% version %version%

if not exist "%addon_dir%\dist" mkdir "%addon_dir%\dist"

del /q "%addon_dir%\dist\*.zip" 2>nul

set output_file=%addon_dir%\dist\%addon_name%_%version%.zip

"%blender_exe%" --background --command extension build --source-dir "%addon_dir%" --output-filepath "%output_file%"

if exist "%output_file%" (
    echo ---------------------
    echo Build successful!
    echo Output: %output_file%
) else (
    echo ---------------------
    echo Build failed!
    exit /b 1
)

cd /d "%build_dir%"