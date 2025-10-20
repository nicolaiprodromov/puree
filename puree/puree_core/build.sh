#!/bin/bash
# Build script for native core module

set -e

# Build the native library
cargo build --release

# Create output directory if it doesn't exist
mkdir -p ../native_binaries

# Detect platform and copy the appropriate binary
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    cp target/release/libpuree_rust_core.so ../native_binaries/puree_rust_core.so
elif [[ "$OSTYPE" == "darwin"* ]]; then
    cp target/release/libpuree_rust_core.dylib ../native_binaries/puree_rust_core.so
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    cp target/release/puree_rust_core.dll ../native_binaries/puree_rust_core.pyd
else
    echo "Unknown OS: $OSTYPE"
    exit 1
fi

echo "Build complete! Binary copied to ../native_binaries/"
