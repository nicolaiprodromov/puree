#!/bin/bash

build_dir=$(pwd)
cd "$(dirname "$0")/.."
addon_dir=$(pwd)

echo "Working from: $addon_dir"

echo "Searching for Blender installation..."

blender_exe=""
latest_version=""

if [ -f "/usr/bin/blender" ]; then
    blender_exe="/usr/bin/blender"
    latest_version=$(blender --version 2>/dev/null | head -1 | grep -o '[0-9]\+\.[0-9]\+' | head -1)
elif [ -f "/usr/local/bin/blender" ]; then
    blender_exe="/usr/local/bin/blender"
    latest_version=$(blender --version 2>/dev/null | head -1 | grep -o '[0-9]\+\.[0-9]\+' | head -1)
elif [ -f "/opt/blender/blender" ]; then
    blender_exe="/opt/blender/blender"
    latest_version=$(blender --version 2>/dev/null | head -1 | grep -o '[0-9]\+\.[0-9]\+' | head -1)
elif [ -f "/snap/bin/blender" ]; then
    blender_exe="/snap/bin/blender"
    latest_version=$(blender --version 2>/dev/null | head -1 | grep -o '[0-9]\+\.[0-9]\+' | head -1)
elif command -v blender >/dev/null 2>&1; then
    blender_exe=$(which blender)
    latest_version=$(blender --version 2>/dev/null | head -1 | grep -o '[0-9]\+\.[0-9]\+' | head -1)
fi

if [ -z "$blender_exe" ]; then
    echo "ERROR: Blender 4.0+ installation not found!"
    echo "Please ensure Blender 4.0 or newer is installed."
    exit 1
fi

echo "Found Blender $latest_version at: $blender_exe"

addon_name=$(grep '^name' blender_manifest.toml | cut -d'=' -f2 | tr -d ' "')
version=$(grep '^version' blender_manifest.toml | cut -d'=' -f2 | tr -d ' "')

addon_name=$(echo "$addon_name" | tr ' ' '_')

echo "Building addon: $addon_name version $version"

mkdir -p "$addon_dir/dist"

output_file="$addon_dir/dist/${addon_name}_${version}.zip"

if [ -f "$output_file" ]; then
    rm -f "$output_file"
fi

echo "Building extension using Blender $latest_version..."
"$blender_exe" --background --command extension build --source-dir "$addon_dir" --output-filepath "$output_file"

if [ -f "$output_file" ]; then
    echo
    echo "Build successful!"
    echo "Output: $output_file"
else
    echo
    echo "Build failed!"
    exit 1
fi

cd "$build_dir"

echo
