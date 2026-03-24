#!/usr/bin/env python3
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
import os
import sys
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


def update_wheels_in_manifest(manifest_path="blender_manifest.toml"):
    """Update the wheels list in blender_manifest.toml."""
    
    # Get list of actual wheel files
    wheels_dir = Path("wheels")
    if not wheels_dir.exists():
        logger.error("Error: wheels/ directory not found")
        sys.exit(1)
    
    wheel_files = sorted([f"./wheels/{f.name}" for f in wheels_dir.glob("*.whl")])
    
    if not wheel_files:
        logger.warning("No .whl files found in wheels/ directory")
        return
    
    logger.info(f"Found {len(wheel_files)} wheel files:")
    for whl in wheel_files:
        logger.info(f"  - {whl}")
    
    # Read the manifest file
    manifest = Path(manifest_path)
    if not manifest.exists():
        logger.error(f"Error: {manifest_path} not found")
        sys.exit(1)
    
    content = manifest.read_text()
    
    # Find the wheels section
    wheels_start = content.find("wheels = [")
    if wheels_start == -1:
        logger.error("Error: 'wheels = [' not found in manifest")
        sys.exit(1)
    
    # Find the end of the wheels array
    bracket_count = 0
    wheels_end = -1
    in_wheels = False
    
    for i in range(wheels_start, len(content)):
        if content[i] == '[':
            bracket_count += 1
            in_wheels = True
        elif content[i] == ']':
            bracket_count -= 1
            if in_wheels and bracket_count == 0:
                wheels_end = i + 1
                break
    
    if wheels_end == -1:
        logger.error("Error: Could not find end of wheels array")
        sys.exit(1)
    
    # Build the new wheels section
    wheels_lines = ["wheels = ["]
    for whl in wheel_files:
        wheels_lines.append(f'  "{whl}",')
    wheels_lines.append("]")
    
    new_wheels_section = "\n".join(wheels_lines)
    
    # Replace the old wheels section with the new one
    new_content = content[:wheels_start] + new_wheels_section + content[wheels_end:]
    
    # Write back to file
    manifest.write_text(new_content)
    
    logger.info(f"\n✓ Updated {manifest_path} with {len(wheel_files)} wheels")


if __name__ == "__main__":
    update_wheels_in_manifest()
