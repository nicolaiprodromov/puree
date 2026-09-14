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

cargo build --release
if errorlevel 1 (
    echo Build failed!
    exit /b 1
)

@REM One folder per platform (same layout as the release wheel; see native_bindings.py).
set OUT=..\native_binaries\windows-x64
if not exist %OUT% mkdir %OUT%

copy /Y target\release\puree_rust_core.dll %OUT%\puree_rust_core.pyd
if errorlevel 1 (
    echo Failed to copy binary!
    exit /b 1
)

echo Build complete! Binary copied to %OUT%\

endlocal
