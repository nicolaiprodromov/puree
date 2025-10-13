import sys
import os
import re
import json
import subprocess
import time
from pathlib import Path

def get_version():
    manifest_path = Path(__file__).parent.parent / 'blender_manifest.toml'
    with open(manifest_path, 'r') as f:
        content = f.read()
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if match:
        return match.group(1)
    raise Exception("Version not found in blender_manifest.toml")

def get_addon_name():
    manifest_path = Path(__file__).parent.parent / 'blender_manifest.toml'
    with open(manifest_path, 'r') as f:
        content = f.read()
    match = re.search(r'^name\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if match:
        return match.group(1).replace(' ', '')
    raise Exception("Name not found in blender_manifest.toml")

def build_addon(version):
    print(f"Building addon version {version}...")
    
    build_script = Path(__file__).parent / 'build.bat'
    result = subprocess.run([str(build_script)], cwd=build_script.parent, shell=True)
    
    if result.returncode != 0:
        print("Build failed!")
        sys.exit(1)
    
    addon_name = get_addon_name()
    zip_file = Path(__file__).parent / f"{addon_name}_{version}.zip"
    
    print(f"Waiting for zip file: {zip_file}")
    max_wait = 30
    wait_time = 0
    while not zip_file.exists() and wait_time < max_wait:
        time.sleep(1)
        wait_time += 1
        if wait_time % 5 == 0:
            print(f"Still waiting... ({wait_time}s)")
    
    if not zip_file.exists():
        print(f"Error: Expected zip file not found after {max_wait}s: {zip_file}")
        sys.exit(1)
    
    print(f"Zip file found, verifying...")
    initial_size = zip_file.stat().st_size
    time.sleep(1)
    final_size = zip_file.stat().st_size
    
    if initial_size != final_size:
        print("File still being written, waiting...")
        time.sleep(2)
    
    print(f"Build successful: {zip_file}")
    return zip_file

def create_github_release(version, zip_file):
    print(f"Creating GitHub release v{version}...")
    
    tag = f"v{version}"
    release_name = f"Puree UI {version}"
    
    release_notes = f"""## Puree UI {version}

### Installation
1. Download `{zip_file.name}`
2. In Blender, go to Edit > Preferences > Get Extensions
3. Click the dropdown menu (⌄) > Install from Disk
4. Select the downloaded zip file

### What's Changed
See commits since last release for details.
"""
    
    notes_file = Path(__file__).parent / 'release_notes.md'
    notes_file.write_text(release_notes, encoding='utf-8')
    
    cmd = [
        'gh', 'release', 'create', tag,
        str(zip_file),
        '--title', release_name,
        '--notes-file', str(notes_file),
        '--repo', 'nicolaiprodromov/puree'
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"Release created successfully!")
        print(f"URL: https://github.com/nicolaiprodromov/puree/releases/tag/{tag}")
        
    except subprocess.CalledProcessError as e:
        if 'already exists' in e.stderr.lower():
            print(f"Release {tag} already exists. Updating...")
            
            delete_cmd = ['gh', 'release', 'delete', tag, '--yes', '--repo', 'nicolaiprodromov/puree']
            subprocess.run(delete_cmd, check=False)
            
            subprocess.run(cmd, check=True)
            print(f"Release updated successfully!")
        else:
            print(f"Error creating release: {e.stderr}")
            sys.exit(1)
    finally:
        if notes_file.exists():
            notes_file.unlink()

def main():
    if len(sys.argv) < 2:
        print("Usage: python release.py <version>")
        sys.exit(1)
    
    version = sys.argv[1]
    
    try:
        result = subprocess.run(['gh', '--version'], capture_output=True)
        if result.returncode != 0:
            print("Error: GitHub CLI (gh) is not installed or not in PATH")
            print("Install it from: https://cli.github.com/")
            sys.exit(1)
    except FileNotFoundError:
        print("Error: GitHub CLI (gh) is not installed or not in PATH")
        print("Install it from: https://cli.github.com/")
        sys.exit(1)
    
    zip_file = build_addon(version)
    create_github_release(version, zip_file)
    
    print("\nRelease process completed successfully!")

if __name__ == "__main__":
    main()
