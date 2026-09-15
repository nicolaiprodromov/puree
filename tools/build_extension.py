#!/usr/bin/env python3
"""Build the development addon into an extension zip with the Blender on PATH.

Replaces the bash/PowerShell `build` recipes: one implementation for every OS,
and it builds the addon under tests/ (tools/addon_paths.py) rather than the cwd.
Output: dist/<Name>_<version>.zip  (one multi-platform zip, like before;
pass --split-platforms for one zip per platform, as the release workflow does).
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import addon_paths  # sibling tools script

from puree.log import setup_cli_logging

logger = setup_cli_logging(Path(__file__).stem)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--split-platforms", action="store_true", help="one zip per manifest platform")
    parser.add_argument("--out", default=str(addon_paths.PROJECT_ROOT / "dist"), help="output directory")
    args = parser.parse_args()

    blender = shutil.which("blender")
    if blender is None:
        logger.error("'blender' not found on PATH")
        sys.exit(1)

    addon = addon_paths.require_addon()
    manifest = addon_paths.MANIFEST.read_text(encoding="utf-8")
    name = re.search(r'^name\s*=\s*"([^"]+)"', manifest, re.M).group(1).replace(" ", "_")
    version = re.search(r'^version\s*=\s*"([^"]+)"', manifest, re.M).group(1)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.zip"):
        old.unlink()

    logger.info(f"Building {name} v{version} from {addon.relative_to(addon_paths.PROJECT_ROOT)} ...")
    cmd = [blender, "--background", "--command", "extension", "build", "--source-dir", str(addon)]
    if args.split_platforms:
        cmd += ["--output-dir", str(out_dir), "--split-platforms"]
    else:
        cmd += ["--output-filepath", str(out_dir / f"{name}_{version}.zip")]

    result = subprocess.run(cmd, capture_output=True, text=True)
    zips = sorted(out_dir.glob("*.zip"))
    if result.returncode != 0 or not zips:
        logger.error("Blender could not build the extension:")
        for line in (result.stdout + result.stderr).strip().splitlines()[-15:]:
            logger.error(f"    {line}")
        sys.exit(1)
    for z in zips:
        shown = z.relative_to(addon_paths.PROJECT_ROOT) if z.is_relative_to(addon_paths.PROJECT_ROOT) else z
        logger.info(f"  {shown}  ({z.stat().st_size / 1e6:.1f} MB)")
    logger.info("Build successful")


if __name__ == "__main__":
    main()
