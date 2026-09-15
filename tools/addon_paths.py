"""Where the development addon lives - the ONE place the tools/ scripts learn it from.

The repository root is the framework (`puree/`), the CLI and the Rust core. The Blender
extension that exercises them is a complete, self-contained Puree project under
`tests/` - exactly the shape `puree init` produces: `__init__.py`, `blender_manifest.toml`,
`assets/`, `fonts/`, `wheels/` and the UI files. Several such addons can sit side by side
in `tests/`; the tooling targets one at a time.

Selection order:
  1. PUREE_ADDON_DIR environment variable (absolute, or relative to the repo root)
  2. the default below

The justfile mirrors this with its `addon_dir` variable (`just --set addon_dir tests/other link`);
the Makefile with `ADDON_DIR`; the release workflow with the `ADDON_DIR` env.
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ADDON = "tests/helloworld"

_env = os.environ.get("PUREE_ADDON_DIR")
ADDON_DIR = (PROJECT_ROOT / _env).resolve() if _env else PROJECT_ROOT / DEFAULT_ADDON

MANIFEST = ADDON_DIR / "blender_manifest.toml"
ADDON_INIT = ADDON_DIR / "__init__.py"
WHEELS_DIR = ADDON_DIR / "wheels"


def require_addon() -> Path:
    """Fail loudly with a useful message when the addon dir is not a Puree project."""
    if not MANIFEST.is_file():
        raise SystemExit(
            f"No blender_manifest.toml in {ADDON_DIR} - not a Puree addon folder "
            f"(set PUREE_ADDON_DIR to point at one under tests/)"
        )
    return ADDON_DIR
