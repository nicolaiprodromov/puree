#!/bin/bash
# Created by XWZ
# ◕‿◕ Distributed for free at:
# https://github.com/nicolaiprodromov/puree
# ╔═════════════════════════════════╗
# ║  ██   ██  ██      ██  ████████  ║
# ║   ██ ██   ██  ██  ██       ██   ║
# ║    ███    ██  ██  ██     ██     ║
# ║   ██ ██   ██  ██  ██   ██       ║
# ║  ██   ██   ████████   ████████  ║
# ╚═════════════════════════════════╝

set -e

# Build the native library
cargo build --release

# One folder per platform, named like blender_manifest.toml's `platforms`
# (same layout as the release wheel; see native_bindings.py). Linux and macOS
# both produce `puree_rust_core.so`, which is why they cannot share a folder.
case "$(uname -m)" in
    arm64|aarch64) ARCH="arm64" ;;
    *)             ARCH="x64" ;;
esac

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OUT="../native_binaries/linux-$ARCH"
    SRC="target/release/libpuree_rust_core.so"; DST="puree_rust_core.so"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OUT="../native_binaries/macos-$ARCH"
    SRC="target/release/libpuree_rust_core.dylib"; DST="puree_rust_core.so"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    OUT="../native_binaries/windows-$ARCH"
    SRC="target/release/puree_rust_core.dll"; DST="puree_rust_core.pyd"
else
    echo "Unknown OS: $OSTYPE"
    exit 1
fi

mkdir -p "$OUT"
cp "$SRC" "$OUT/$DST"

echo "Build complete! Binary copied to $OUT/"
