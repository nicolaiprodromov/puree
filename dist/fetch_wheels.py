#!/usr/bin/env python3
"""Make wheels/ complete for EVERY platform in blender_manifest.toml, then rewrite the manifest.

Why this exists: `pip download` only fetches wheels for the machine it runs on, and
dist/update_wheels.py rewrites the manifest's wheels[] from whatever sits in wheels/.
The old `just wheels` (one pip download) therefore deleted every OTHER platform's wheels
from the manifest whenever it ran on a single machine. This script:

  1. reads the pinned dependencies from pyproject.toml [project].dependencies
  2. reads the target platforms from blender_manifest.toml `platforms`
  3. removes wheels of a managed package at a stale version (a pin bump never leaves two versions)
  4. runs one `pip download --no-deps --platform ...` per (package, platform). Per package,
     because pip aborts the whole call when a single package has no wheel for a tag
     (av ships manylinux_2_28, rlottie manylinux_2_17), and we pass every accepted linux tag
  5. rebuilds the puree_ui wheel into wheels/ (dist/build_package.py)
  6. rewrites the manifest (dist/update_wheels.py) - only reached when 1-5 succeeded

Run via `just wheels` on any OS. Options: --python-version, --only PLATFORM, --fetch-only,
--skip-package. The manifest is never rewritten without a puree_ui wheel on disk.
"""

import argparse
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_package  # sibling dist script
import update_wheels  # sibling dist script

from puree.log import setup_cli_logging

logger = setup_cli_logging(Path(__file__).stem)

# Python shipped by the Blender version the manifest targets (blender_version_min).
BLENDER_PYTHON_VERSION = "3.13"

# manifest platform id -> pip --platform tags.
# pip widens macOS tags downward (macosx_14_0 also accepts 13_0 ... 11_0) but does NOT widen
# manylinux tags, so every linux tag we accept is listed explicitly. Wheels only need to match
# ONE of the tags.
PLATFORM_TAGS = {
    "windows-x64": ["win_amd64"],
    "linux-x64": [
        "manylinux_2_28_x86_64",  # av 18 ships only this tag
        "manylinux_2_17_x86_64",
        "manylinux2014_x86_64",
        "manylinux_2_12_x86_64",
        "manylinux2010_x86_64",
        "manylinux_2_5_x86_64",
        "manylinux1_x86_64",
    ],
    "macos-arm64": ["macosx_14_0_arm64"],  # av 18 arm64 needs macOS 14; the rest are 11_0
    "macos-x64": ["macosx_11_0_x86_64"],
}

PIN_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*==\s*([^\s;]+)")


def _normalize(name: str) -> str:
    """PEP 503 name normalization (wheel filenames use '_' where pins use '-')."""
    return re.sub(r"[-_.]+", "-", name).lower()


def read_pins() -> list[tuple[str, str]]:
    with open(PROJECT_ROOT / "pyproject.toml", "rb") as f:
        deps = tomllib.load(f)["project"]["dependencies"]
    pins = []
    for dep in deps:
        m = PIN_RE.match(dep)
        if not m:
            logger.error(f"Unsupported dependency spec {dep!r} - only exact '==' pins can be bundled")
            sys.exit(1)
        pins.append((m.group(1), m.group(2)))
    return pins


def read_platforms() -> list[str]:
    with open(PROJECT_ROOT / "blender_manifest.toml", "rb") as f:
        platforms = tomllib.load(f).get("platforms", [])
    unknown = [p for p in platforms if p not in PLATFORM_TAGS]
    if unknown:
        logger.error(f"Manifest platform(s) {unknown} have no pip tag mapping - add them to PLATFORM_TAGS")
        sys.exit(1)
    if not platforms:
        logger.error("blender_manifest.toml declares no `platforms`")
        sys.exit(1)
    return platforms


def prune_stale(wheels_dir: Path, pins: list[tuple[str, str]]) -> None:
    pinned = {_normalize(name): version for name, version in pins}
    for whl in sorted(wheels_dir.glob("*.whl")):
        parts = whl.name[:-4].split("-")
        if len(parts) < 5:
            logger.warning(f"Skipping unparseable wheel filename: {whl.name}")
            continue
        name, version = _normalize(parts[0]), parts[1]
        if name == "puree-ui":
            continue  # rebuilt by build_package (which removes the old one itself)
        if name not in pinned:
            logger.warning(f"Unmanaged wheel left in place (it WILL be listed in the manifest): {whl.name}")
        elif version != pinned[name]:
            whl.unlink()
            logger.info(f"Removed stale {whl.name} (pin is {pinned[name]})")


def download(pins, platforms, python_version: str, wheels_dir: Path) -> None:
    wheels_dir.mkdir(exist_ok=True)
    for platform in platforms:
        tags = PLATFORM_TAGS[platform]
        for name, version in pins:
            cmd = [
                sys.executable,
                "-m",
                "pip",
                "download",
                "--disable-pip-version-check",
                "--no-deps",
                "--only-binary=:all:",
                "--python-version",
                python_version,
                "--implementation",
                "cp",
                "--dest",
                str(wheels_dir),
                f"{name}=={version}",
            ]
            for tag in tags:
                cmd += ["--platform", tag]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"pip download failed for {name}=={version} on {platform}:")
                for line in (result.stderr or result.stdout).strip().splitlines()[-8:]:
                    logger.error(f"    {line}")
                sys.exit(1)
            saved = [line.split("/")[-1].split("\\")[-1] for line in result.stdout.splitlines() if "Saved " in line]
            status = f"fetched {saved[0]}" if saved else "already present"
            logger.info(f"  {platform:<12} {name}=={version:<10} {status}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--python-version", default=BLENDER_PYTHON_VERSION, help="Blender's Python (default 3.13)")
    parser.add_argument("--only", metavar="PLATFORM", help="fetch a single manifest platform (testing aid)")
    parser.add_argument("--fetch-only", action="store_true", help="download only; leave the manifest untouched")
    parser.add_argument("--skip-package", action="store_true", help="reuse the puree_ui wheel already in wheels/")
    args = parser.parse_args()

    os.chdir(PROJECT_ROOT)
    wheels_dir = PROJECT_ROOT / "wheels"

    pins = read_pins()
    platforms = read_platforms()
    if args.only:
        if args.only not in platforms:
            logger.error(f"--only {args.only!r} is not a manifest platform ({platforms})")
            sys.exit(1)
        platforms = [args.only]

    logger.info(f"Bundling {len(pins)} pinned dependencies for {len(platforms)} platform(s): {', '.join(platforms)}")
    prune_stale(wheels_dir, pins)
    download(pins, platforms, args.python_version, wheels_dir)

    if args.fetch_only:
        logger.info(f"wheels/ now holds {len(list(wheels_dir.glob('*.whl')))} wheels (manifest untouched)")
        return

    if not args.skip_package:
        build_package.main()

    if not list(wheels_dir.glob("puree_ui-*.whl")):
        logger.error("No puree_ui wheel in wheels/ - refusing to rewrite the manifest without it")
        sys.exit(1)

    update_wheels.update_wheels_in_manifest()
    logger.info(f"wheels/ now holds {len(list(wheels_dir.glob('*.whl')))} wheels")


if __name__ == "__main__":
    main()
