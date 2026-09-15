#!/usr/bin/env python3
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import addon_paths  # sibling tools script

from puree.log import setup_cli_logging

logger = setup_cli_logging(os.path.splitext(os.path.basename(__file__))[0])


def update_wheels_in_manifest(manifest_path=None, wheels_dir=None):
    """Rewrite the manifest's wheels[] from the .whl files sitting next to it.

    Defaults to the development addon (tools/addon_paths.py); both paths can be
    overridden to run against any Puree project.
    """
    manifest_path = Path(manifest_path) if manifest_path else addon_paths.MANIFEST
    wheels_dir = Path(wheels_dir) if wheels_dir else manifest_path.parent / "wheels"
    if not wheels_dir.exists():
        logger.error(f"Error: wheels directory not found: {wheels_dir}")
        sys.exit(1)

    wheel_files = sorted([f"./wheels/{f.name}" for f in wheels_dir.glob("*.whl")])

    if not wheel_files:
        logger.warning("No .whl files found in wheels/ directory")
        return

    logger.info(f"Found {len(wheel_files)} wheel files:")
    for whl in wheel_files:
        logger.info(f"  - {whl}")

    manifest = manifest_path
    if not manifest.exists():
        logger.error(f"Error: {manifest_path} not found")
        sys.exit(1)

    content = manifest.read_text(encoding="utf-8")

    wheels_start = content.find("wheels = [")
    if wheels_start == -1:
        logger.error("Error: 'wheels = [' not found in manifest")
        sys.exit(1)

    bracket_count = 0
    wheels_end = -1
    in_wheels = False

    for i in range(wheels_start, len(content)):
        if content[i] == "[":
            bracket_count += 1
            in_wheels = True
        elif content[i] == "]":
            bracket_count -= 1
            if in_wheels and bracket_count == 0:
                wheels_end = i + 1
                break

    if wheels_end == -1:
        logger.error("Error: Could not find end of wheels array")
        sys.exit(1)

    wheels_lines = ["wheels = ["]
    for whl in wheel_files:
        wheels_lines.append(f'  "{whl}",')
    wheels_lines.append("]")

    new_wheels_section = "\n".join(wheels_lines)

    new_content = content[:wheels_start] + new_wheels_section + content[wheels_end:]

    manifest.write_text(new_content, encoding="utf-8")

    logger.info(f"\n✓ Updated {manifest_path} with {len(wheel_files)} wheels")


if __name__ == "__main__":
    update_wheels_in_manifest()
