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
import sys
import os
import re
import json
import subprocess
import time
import shutil
import zipfile
import tarfile
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

logger = logging.getLogger(f"puree.cli.{os.path.splitext(os.path.basename(__file__))[0]}")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    _log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    os.makedirs(_log_dir, exist_ok=True)
    _fh = RotatingFileHandler(os.path.join(_log_dir, "puree.log"), maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
    _fh.setLevel(logging.DEBUG)
    _fh.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)-8s %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(_fh)
    _ch = logging.StreamHandler()
    _ch.setLevel(logging.INFO)
    _ch.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(_ch)

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

def create_release_archives(version):
    logger.info(f"Creating release archives for version {version}...")
    
    addon_name = get_addon_name()
    project_root = Path(__file__).parent.parent
    dist_dir = Path(__file__).parent
    release_dir = dist_dir / 'release'
    
    release_dir.mkdir(exist_ok=True)
    
    release_items = [
        'assets',
        'fonts',
        'static',
        'wheels',
        '__init__.example.py',
        'blender_manifest.example.toml',
        'LICENSE',
        'README.md'
    ]
    
    temp_build_dir = release_dir / 'temp_build'
    if temp_build_dir.exists():
        shutil.rmtree(temp_build_dir)
    temp_build_dir.mkdir(parents=True)
    
    logger.info("Copying release files...")
    for item in release_items:
        source = project_root / item
        dest = temp_build_dir / item
        
        if not source.exists():
            logger.warning(f"{item} not found, skipping...")
            continue
            
        if source.is_dir():
            shutil.copytree(source, dest)
        else:
            shutil.copy2(source, dest)
    
    zip_file = release_dir / f"{addon_name}_{version}.zip"
    tar_file = release_dir / f"{addon_name}_{version}.tar.gz"
    
    logger.info(f"Creating {zip_file.name}...")
    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(temp_build_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(temp_build_dir)
                zf.write(file_path, arcname)
    
    logger.info(f"Creating {tar_file.name}...")
    with tarfile.open(tar_file, 'w:gz') as tf:
        for root, dirs, files in os.walk(temp_build_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(temp_build_dir)
                tf.add(file_path, arcname)
    
    shutil.rmtree(temp_build_dir)
    
    logger.info("Release archives created successfully!")
    return zip_file, tar_file

def create_github_release(version, zip_file, tar_file):
    logger.info(f"Creating GitHub release v{version}...")
    
    tag = f"v{version}"
    release_name = f"Puree UI {version}"
    
    template_path = Path(__file__).parent.parent / 'docs' / '.release_note.md'
    if not template_path.exists():
        raise Exception(f"Release notes template not found at {template_path}")
    
    release_notes_template = template_path.read_text(encoding='utf-8')
    release_notes = release_notes_template.format(
        version=version,
        zip_name=zip_file.name,
        tar_name=tar_file.name,
        previous_version='0.0.0'
    )
    
    notes_file = Path(__file__).parent / 'release_notes.md'
    notes_file.write_text(release_notes, encoding='utf-8')
    
    cmd = [
        'gh', 'release', 'create', tag,
        str(zip_file),
        str(tar_file),
        '--title', release_name,
        '--notes-file', str(notes_file),
        '--repo', 'nicolaiprodromov/puree'
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info("Release created successfully!")
        logger.info(f"URL: https://github.com/nicolaiprodromov/puree/releases/tag/{tag}")
        
    except subprocess.CalledProcessError as e:
        if 'already exists' in e.stderr.lower():
            logger.warning(f"Release {tag} already exists. Updating...")
            
            delete_cmd = ['gh', 'release', 'delete', tag, '--yes', '--repo', 'nicolaiprodromov/puree']
            subprocess.run(delete_cmd, check=False)
            
            subprocess.run(cmd, check=True)
            logger.info("Release updated successfully!")
        else:
            logger.error(f"Error creating release: {e.stderr}")
            sys.exit(1)
    finally:
        if notes_file.exists():
            notes_file.unlink()

def main():
    if len(sys.argv) < 2:
        logger.info("Usage: python release.py <version>")
        sys.exit(1)
    
    version = sys.argv[1]
    
    try:
        result = subprocess.run(['gh', '--version'], capture_output=True)
        if result.returncode != 0:
            logger.error("Error: GitHub CLI (gh) is not installed or not in PATH")
            logger.error("Install it from: https://cli.github.com/")
            sys.exit(1)
    except FileNotFoundError:
        logger.error("Error: GitHub CLI (gh) is not installed or not in PATH")
        logger.error("Install it from: https://cli.github.com/")
        sys.exit(1)
    
    zip_file, tar_file = create_release_archives(version)
    create_github_release(version, zip_file, tar_file)
    
    logger.info("\nRelease process completed successfully!")

if __name__ == "__main__":
    main()
