@echo off
setlocal enabledelayedexpansion

echo Building native core module for puree...

cargo build --release
if errorlevel 1 (
    echo Build failed!
    exit /b 1
)

if not exist ..\native_binaries mkdir ..\native_binaries

echo Windows detected
copy /Y target\release\puree_rust_core.dll ..\native_binaries\puree_rust_core.pyd
if errorlevel 1 (
    echo Failed to copy binary!
    exit /b 1
)

echo Build complete! Binary copied to ..\native_binaries\

endlocal
