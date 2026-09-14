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
"""Built-in defaults shipped with Puree (`puree/components/defaults/`).

Two kinds of files live here:

- ``*.scss`` — default stylesheets (markdown classes, scrollbar variables, …).
  `get_default_scss()` compiles and concatenates all of them; `UI.parse_css()`
  prepends the result to the user's style string so user rules always win via
  cascade order (and ``!default`` variables stay overridable).
- ``*.yaml`` — default component templates. `get_default_component_paths()`
  lists every file whose parsed YAML has a dict root key matching the filename
  (the same contract as user components); `UI.parse_toml()` registers them into
  the component registry AFTER user components so `add_child("[name]")` works
  for defaults while user components of the same name always win.
  Documentation-only files with no real tree (e.g. ``scrollbar.yaml`` — the
  scrollbar is drawn programmatically by render.py) are skipped.
"""

import os

import yaml

from ...log import get_logger

logger = get_logger(__name__)

_DEFAULTS_DIR = os.path.dirname(os.path.abspath(__file__))


def get_default_scss() -> str:
    """Compile and concatenate every default ``*.scss`` file, sorted by filename.

    Meant to be *prepended* to the user's style string — user styles override
    the defaults through normal cascade order. Files that fail to compile are
    skipped with a logged warning so one bad default can't break parsing.
    """
    from ...native_bindings import SCSSCompiler

    scss_compiler = SCSSCompiler()
    compiled_parts = []
    injected = []
    for fname in sorted(os.listdir(_DEFAULTS_DIR)):
        if not fname.endswith(".scss"):
            continue
        fpath = os.path.join(_DEFAULTS_DIR, fname)
        try:
            compiled_parts.append(scss_compiler.compile_file(fpath))
            injected.append(fname)
        except Exception as err:
            logger.warning("Failed to compile %s: %s", fname, err)
    if injected:
        logger.debug("Injected default SCSS files: %s", ", ".join(injected))
    return "\n".join(compiled_parts)


def get_default_component_paths() -> dict[str, str]:
    """Map component name -> yaml path for every real default component template.

    A file qualifies when its parsed YAML is a mapping with a dict root key
    matching the filename (``video_controls.yaml`` must contain a
    ``video_controls:`` mapping). Files that don't qualify — documentation-only
    files like ``scrollbar.yaml``, or files that fail to parse — are skipped
    gracefully.
    """
    paths: dict[str, str] = {}
    for fname in sorted(os.listdir(_DEFAULTS_DIR)):
        if not fname.endswith(".yaml"):
            continue
        name = fname[:-5]  # strip .yaml
        fpath = os.path.join(_DEFAULTS_DIR, fname)
        try:
            with open(fpath, "r") as f:
                data = yaml.safe_load(f)
        except Exception as err:
            logger.warning("Failed to parse default component %s: %s", fname, err)
            continue
        if not isinstance(data, dict) or not isinstance(data.get(name), dict):
            logger.debug("Skipping %s — no '%s' root mapping (documentation-only)", fname, name)
            continue
        paths[name] = fpath
    return paths
