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

build_dir=$(pwd)
cd "$(dirname "$0")/.."
addon_dir=$(pwd)

echo "working from: $addon_dir"

blender_exe=$(which blender 2>/dev/null || true)

if [ -z "$blender_exe" ]; then
    echo "ERROR: 'blender' not found on PATH!"
    echo "Please ensure Blender is installed and available in your system PATH."
    exit 1
fi

addon_name=$(grep '^name' blender_manifest.toml | cut -d'=' -f2 | tr -d ' "')
version=$(grep '^version' blender_manifest.toml | cut -d'=' -f2 | tr -d ' "')

addon_name=$(echo "$addon_name" | tr ' ' '_')

echo "building: $addon_name version $version"

mkdir -p "$addon_dir/dist/out"

rm -f "$addon_dir/dist/out"/*.zip

output_file="$addon_dir/dist/out/${addon_name}_${version}.zip"

"$blender_exe" --background --command extension build --source-dir "$addon_dir" --output-filepath "$output_file"

if [ -f "$output_file" ]; then
    echo ---------------------
    echo "Build successful!"
    echo "Output: $output_file"
else
    echo ---------------------
    echo "Build failed!"
    exit 1
fi

cd "$build_dir"