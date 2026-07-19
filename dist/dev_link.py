#!/usr/bin/env python3
"""
Windows dev-mode helper: link / unlink / install-deps.

Mirrors the bash `link`, `unlink`, and `install-deps` recipes in the
justfile, using NTFS directory junctions (no admin rights needed,
unlike symlinks). Junctions are removed with os.rmdir, which detaches
the link WITHOUT touching the source tree.

Blender 5.x on Windows keeps extension data under:
  %APPDATA%/Blender Foundation/Blender/<ver>/extensions/user_default
  %APPDATA%/Blender Foundation/Blender/<ver>/extensions/.local/lib/python3.13/site-packages

Usage:
  python dist/dev_link.py link
  python dist/dev_link.py unlink
  python dist/dev_link.py install-deps
"""

import argparse
import ctypes
import os
import subprocess
import sys
import zipfile
from pathlib import Path

BLENDER_VERSION = os.environ.get("PUREE_BLENDER_VERSION", "5.1")
PY_TAG = os.environ.get("PUREE_BLENDER_PY", "3.13")
ADDON_ID = "xwz_puree_ui"
DEP_MARKERS = ["moderngl", "glcontext", "stretchable", "yaml", "attrs"]

REPO = Path(__file__).resolve().parent.parent


def _blender_base():
    appdata = os.environ.get("APPDATA")
    if not appdata:
        print("Error: APPDATA is not set — is this really Windows?")
        sys.exit(1)
    return Path(appdata) / "Blender Foundation" / "Blender" / BLENDER_VERSION


def _ext_dir():
    return _blender_base() / "extensions" / "user_default"


def _site_packages():
    # Verified against Blender 5.1 on Windows: it uses the POSIX-style
    # lib/python3.13/site-packages layout, not Lib/site-packages.
    return _blender_base() / "extensions" / ".local" / "lib" / f"python{PY_TAG}" / "site-packages"


def _is_link(path: Path) -> bool:
    """True for symlinks AND junctions (reparse points), even broken ones."""
    FILE_ATTRIBUTE_REPARSE_POINT = 0x0400
    attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
    return attrs != -1 and bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)


def _remove_link(path: Path):
    """Detach a junction/symlink without deleting the target's contents."""
    os.rmdir(path)


def _make_junction(link: Path, target: Path):
    """Create an NTFS junction. Falls back to symlink if junction fails."""
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError as e:
            print(f"Error: could not create junction or symlink at {link}")
            print(f"  mklink: {result.stderr.strip()}")
            print(f"  symlink: {e}")
            sys.exit(1)


def _deps_installed(site: Path) -> bool:
    if not site.is_dir():
        return False
    names = [p.name.lower() for p in site.iterdir()]
    return all(any(marker in n for n in names) for marker in DEP_MARKERS)


def cmd_install_deps():
    site = _site_packages()
    site.mkdir(parents=True, exist_ok=True)
    wheels = sorted((REPO / "wheels").glob("*.whl"))
    if not wheels:
        print("Error: no wheels in wheels/ — run 'just wheels' first.")
        sys.exit(1)
    print(f"Installing wheel dependencies to {site}")
    count = 0
    for whl in wheels:
        if whl.name.startswith("puree_ui-"):
            print(f"  skip {whl.name} (using source junction)")
            continue
        with zipfile.ZipFile(whl, "r") as zf:
            zf.extractall(site)
        count += 1
        print(f"  + {whl.name}")
    print(f"Done - {count} wheels extracted.")


def cmd_link():
    ext_dir = _ext_dir()
    ext_link = ext_dir / ADDON_ID
    site = _site_packages()
    site_puree = site / "puree"

    if not _deps_installed(site):
        print("Wheel dependencies missing from site-packages...")
        cmd_install_deps()

    ext_dir.mkdir(parents=True, exist_ok=True)

    # Extension dir: replace installed copy (or stale link) with junction
    if _is_link(ext_link):
        print("Link already exists, updating...")
        _remove_link(ext_link)
    elif ext_link.is_dir():
        print("Removing installed extension copy...")
        import shutil

        shutil.rmtree(ext_link)
    _make_junction(ext_link, REPO)
    print(f"+ Linked extension: {ext_link} -> {REPO}")

    # Site-packages puree: replace wheel-installed copy with junction
    if _is_link(site_puree):
        _remove_link(site_puree)
    elif site_puree.is_dir():
        print("Removing wheel-installed puree from site-packages...")
        import shutil

        shutil.rmtree(site_puree)
        for dist_info in site.glob("puree_ui-*.dist-info"):
            shutil.rmtree(dist_info)
    _make_junction(site_puree, REPO / "puree")
    print(f"+ Linked package:   {site_puree} -> {REPO / 'puree'}")

    print()
    print("Dev mode active. Use 'just reload' after code changes.")


def cmd_unlink():
    ext_link = _ext_dir() / ADDON_ID
    site_puree = _site_packages() / "puree"
    if _is_link(ext_link):
        _remove_link(ext_link)
        print("+ Removed extension link")
    else:
        print("No extension link found")
    if _is_link(site_puree):
        _remove_link(site_puree)
        print("+ Removed site-packages link")
    else:
        print("No site-packages link found")
    print("Dev mode deactivated.")


def main():
    parser = argparse.ArgumentParser(description="Puree Windows dev-mode linker")
    parser.add_argument("command", choices=["link", "unlink", "install-deps"])
    args = parser.parse_args()
    {"link": cmd_link, "unlink": cmd_unlink, "install-deps": cmd_install_deps}[args.command]()


if __name__ == "__main__":
    main()
