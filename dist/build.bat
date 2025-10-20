@echo off
setlocal enabledelayedexpansion

set build_dir=%cd%
cd /d "%~dp0\.."
set addon_dir=%cd%

echo working from: %addon_dir%

set "blender_exe="
set "latest_version="

if exist "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" (
    set "blender_exe=C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
    set "latest_version=4.5"
    goto :found_blender
)

if exist "C:\Program Files (x86)\Blender Foundation\Blender 4.5\blender.exe" (
    set "blender_exe=C:\Program Files (x86)\Blender Foundation\Blender 4.5\blender.exe"
    set "latest_version=4.5"
    goto :found_blender
)

if exist "C:\Program Files\Blender Foundation\Blender 4.4\blender.exe" (
    set "blender_exe=C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"
    set "latest_version=4.4"
    goto :found_blender
)

if exist "C:\Program Files (x86)\Blender Foundation\Blender 4.4\blender.exe" (
    set "blender_exe=C:\Program Files (x86)\Blender Foundation\Blender 4.4\blender.exe"
    set "latest_version=4.4"
    goto :found_blender
)

if exist "C:\Program Files\Blender Foundation\Blender 4.3\blender.exe" (
    set "blender_exe=C:\Program Files\Blender Foundation\Blender 4.3\blender.exe"
    set "latest_version=4.3"
    goto :found_blender
)

if exist "C:\Program Files (x86)\Blender Foundation\Blender 4.3\blender.exe" (
    set "blender_exe=C:\Program Files (x86)\Blender Foundation\Blender 4.3\blender.exe"
    set "latest_version=4.3"
    goto :found_blender
)

if exist "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe" (
    set "blender_exe=C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"
    set "latest_version=4.2"
    goto :found_blender
)

if exist "C:\Program Files (x86)\Blender Foundation\Blender 4.2\blender.exe" (
    set "blender_exe=C:\Program Files (x86)\Blender Foundation\Blender 4.2\blender.exe"
    set "latest_version=4.2"
    goto :found_blender
)

if exist "C:\Program Files\Blender Foundation\Blender 4.1\blender.exe" (
    set "blender_exe=C:\Program Files\Blender Foundation\Blender 4.1\blender.exe"
    set "latest_version=4.1"
    goto :found_blender
)

if exist "C:\Program Files (x86)\Blender Foundation\Blender 4.1\blender.exe" (
    set "blender_exe=C:\Program Files (x86)\Blender Foundation\Blender 4.1\blender.exe"
    set "latest_version=4.1"
    goto :found_blender
)


echo ERROR: Blender 4.0+ installation not found!
echo Please ensure Blender 4.0 or newer is installed.
pause
exit /b 1

:found_blender
echo %latest_version% at: %blender_exe%

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