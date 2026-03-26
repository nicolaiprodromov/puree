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
import bpy
import os
import sys
import importlib
import logging
import pathlib

# ── Bootstrap logger for early-stage messages ────────────────────────
# During module reload, the puree package is purged from sys.modules.
# We need a bare logger that works regardless of whether puree.log is loaded.
_boot_logger = logging.getLogger("puree.boot")

def _log(msg, level=logging.INFO):
    """Log via the puree logger if available, otherwise use the boot logger."""
    try:
        from puree.log import get_logger
        get_logger("puree.boot").log(level, msg)
    except Exception:
        _boot_logger.log(level, msg)

# Force-reload all puree submodules so Blender picks up code changes
# without needing a full restart. This runs on F3 → "Reload Scripts"
# or when the addon is re-enabled after disable.
_puree_modules = [k for k in sys.modules if k == "puree" or k.startswith("puree.")]
if _puree_modules:
    # Sort so parents reload before children
    for mod_name in sorted(_puree_modules):
        try:
            importlib.reload(sys.modules[mod_name])
        except Exception as e:
            _log(f"reload {mod_name}: {e}", logging.WARNING)

from puree import register as xwz_ui_register, unregister as xwz_ui_unregister
from puree import set_addon_root
from puree.reload_server import ReloadServer, PUREE_RELOAD_PORT

bl_info = {
    "name"       : "Puree",
    "author"     : "Nicolai Prodromov",
    "version"    : (0, 1, 3),
    "blender"    : (5, 1, 0),
    "location"   : "3D View > Sidebar > Puree",
    "description": "XWZ Puree UI framework",
    "category"   : "3D View"
}

# ── Built-in reload server ───────────────────────────────────────────
# A tiny TCP server (127.0.0.1:19746) that `just reload` connects to.
# No manual activation needed — starts automatically with the addon.

_reload_server = None
_RELOAD_SENTINEL = pathlib.Path(__file__).resolve().parent / ".puree_reload"


def _deferred_reload():
    """Timer callback — runs on main Blender thread to perform the reload."""
    _perform_reload()
    return None  # run once


def _perform_reload():
    """Stop server, purge cached modules, re-register the addon."""
    global _reload_server
    addon_module = "bl_ext.user_default.xwz_puree_ui"

    # 0. Stop the reload server so the port is free for the new instance
    if _reload_server:
        _reload_server.stop()
        _reload_server = None

    # 1. Unregister
    mod = sys.modules.get(addon_module)
    if mod and hasattr(mod, 'unregister'):
        try:
            mod.unregister()
        except Exception as e:
            _log(f"unregister warning: {e}", logging.WARNING)

    # 2. Purge all cached puree modules
    purged = 0
    for key in list(sys.modules.keys()):
        if key == "puree" or key.startswith("puree."):
            del sys.modules[key]
            purged += 1
    for key in list(sys.modules.keys()):
        if "xwz_puree_ui" in key:
            del sys.modules[key]
            purged += 1

    # 3. Clear __pycache__ bytecode
    import shutil
    for sp in sys.path:
        puree_dir = pathlib.Path(sp) / "puree"
        if puree_dir.exists():
            for cache in puree_dir.rglob("__pycache__"):
                if cache.is_dir() and not cache.is_symlink():
                    shutil.rmtree(cache, ignore_errors=True)

    # 4. Re-import and register (starts a fresh reload server)
    try:
        mod = importlib.import_module(addon_module)
        mod.register()
        _log(f"addon reloaded ({purged} modules purged)")
    except Exception as e:
        _log(f"reload error: {e}", logging.ERROR)
        import traceback
        traceback.print_exc()


def _check_reload_sentinel():
    """Fallback timer — polls for sentinel file written by `just reload`."""
    try:
        if _RELOAD_SENTINEL.exists():
            _RELOAD_SENTINEL.unlink(missing_ok=True)
            _perform_reload()
    except Exception as e:
        _log(f"reload watcher error: {e}", logging.ERROR)
    return 2.0  # low frequency fallback


def register():
    global _reload_server
    # Resolve symlinks so linked paths point to the actual source directory
    set_addon_root(os.path.realpath(os.path.dirname(os.path.abspath(__file__))))
    # Register the framework
    xwz_ui_register()
    # Set default properties
    wm = bpy.context.window_manager
    wm.xwz_ui_conf_path = "static/index.yaml"
    wm.xwz_debug_panel  = True
    wm.xwz_auto_start   = True

    # Start the built-in reload server
    _reload_server = ReloadServer(
        port=PUREE_RELOAD_PORT,
        reload_fn=_deferred_reload,
    )
    _reload_server.start()

    # Sentinel fallback (covers edge cases where TCP isn't reachable)
    if not bpy.app.timers.is_registered(_check_reload_sentinel):
        bpy.app.timers.register(_check_reload_sentinel, persistent=True)


def unregister():
    global _reload_server
    # Stop the reload server
    if _reload_server:
        _reload_server.stop()
        _reload_server = None

    # Stop sentinel fallback
    if bpy.app.timers.is_registered(_check_reload_sentinel):
        try:
            bpy.app.timers.unregister(_check_reload_sentinel)
        except Exception:
            pass

    # Clean up any stale sentinel
    _RELOAD_SENTINEL.unlink(missing_ok=True)
    # Unregister the framework
    xwz_ui_unregister()
    
if __name__ == "__main__":
    register()