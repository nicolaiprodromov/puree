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
import pathlib
import importlib as _importlib

# ── Force-reload submodules on Blender script reload ─────────────────
# When Blender re-executes the addon root, it reloads this package.
# We must also force-reload all child modules so code changes take effect.
_submodules = [k for k in sys.modules if k.startswith("puree.")]
if _submodules:
    _boot_logger = logging.getLogger("puree.boot")
    for _mod_name in sorted(_submodules):
        try:
            _importlib.reload(sys.modules[_mod_name])
        except Exception as _e:
            _boot_logger.warning("reload %s: %s", _mod_name, _e)

from .log import get_logger, get_log_path, reinitialize as _reinitialize_logging
from .storage import Storage
from .virtual_scroll import VirtualScroll
from .markdown import render_markdown
logger = get_logger(__name__)

__all__ = ['register', 'unregister', 'set_addon_root', 'get_addon_root', 'get_log_path', 'Storage', 'render_markdown', 'VirtualScroll']
__version__ = "0.1.0"
_ADDON_ROOT = None
_ADDON_MODULE_NAME = None
_try_start_retries = 0

# ── Reload server state ─────────────────────────────────────────────
_reload_server = None


def set_addon_root(path):
    global _ADDON_ROOT, _ADDON_MODULE_NAME
    _ADDON_ROOT = os.path.realpath(path)
    # Auto-detect the addon module name from the caller
    import inspect
    frame = inspect.currentframe().f_back
    _ADDON_MODULE_NAME = frame.f_globals.get('__name__')

def get_addon_root():
    global _ADDON_ROOT
    if _ADDON_ROOT is not None:
        return _ADDON_ROOT
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ── Reload machinery ────────────────────────────────────────────────

def _get_sentinel_path():
    return pathlib.Path(get_addon_root()) / ".puree_reload"


def _deferred_reload():
    """Timer callback — runs on main Blender thread to perform the reload."""
    _perform_reload()
    return None  # run once


def _perform_reload():
    """Stop server, purge cached modules, re-register the addon."""
    import importlib
    import shutil

    global _reload_server
    addon_module = _ADDON_MODULE_NAME
    if not addon_module:
        logger.error("Cannot reload: addon module name unknown")
        return

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
            logger.warning("unregister warning: %s", e)

    # 2. Purge all cached puree modules
    purged = 0
    for key in list(sys.modules.keys()):
        if key == "puree" or key.startswith("puree."):
            del sys.modules[key]
            purged += 1
    for key in list(sys.modules.keys()):
        if key == addon_module or key.startswith(addon_module + "."):
            del sys.modules[key]
            purged += 1

    # 3. Clear __pycache__ bytecode
    addon_dir = pathlib.Path(get_addon_root())
    for cache in addon_dir.rglob("__pycache__"):
        if cache.is_dir() and not cache.is_symlink():
            shutil.rmtree(cache, ignore_errors=True)

    # 4. Re-import and register (starts a fresh reload server)
    try:
        mod = importlib.import_module(addon_module)
        mod.register()
        logger.info("addon reloaded (%d modules purged)", purged)
    except Exception as e:
        logger.error("reload error: %s", e, exc_info=True)


def _check_reload_sentinel():
    """Fallback timer — polls for sentinel file written by `just reload`."""
    try:
        sentinel = _get_sentinel_path()
        if sentinel.exists():
            sentinel.unlink(missing_ok=True)
            _perform_reload()
    except Exception as e:
        logger.error("reload watcher error: %s", e)
    return 2.0  # low frequency fallback


def _try_start_ui():
    import bpy
    from .space_config import parse_space_config, validate_current_configuration
    
    wm = bpy.context.window_manager
    conf_path = getattr(wm, "xwz_ui_conf_path", None)
    if not conf_path:
        logger.debug("No xwz_ui_conf_path set — auto-start skipped.")
        return None
    
    global _try_start_retries
    _try_start_retries += 1
    
    if not parse_space_config(conf_path):
        if _try_start_retries < 5:
            logger.warning(f"Failed to parse space configuration for {conf_path} (attempt {_try_start_retries}), retrying...")
        else:
            logger.error(f"Failed to parse space configuration for {conf_path} after {_try_start_retries} attempts. Auto-start disabled.")
            return None  # Stop retrying
        return 0.5
    
    config_status = validate_current_configuration()
    
    if not config_status['space_available']:
        target_space = config_status.get('target_space', 'Unknown')
        logger.info(f"Target space '{target_space}' not available yet, retrying...")
        return 0.5
    
    area = config_status['area']
    region = config_status['region']
    
    if not (area and region):
        logger.info("Found target space but no WINDOW region, retrying...")
        return 0.5
    
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for screen_area in screen.areas:
            if screen_area == area:
                override = {
                    'window': window,
                    'screen': screen,
                    'area': area,
                    'region': region,
                }
                try:
                    with bpy.context.temp_override(**override):
                        bpy.ops.xwz.start_ui()
                    target_space = config_status.get('target_space', 'Unknown')
                    logger.info(f"Puree UI auto-started successfully in {target_space}")
                    return None
                except Exception as e:
                    logger.error(f"Failed to auto-start Puree UI: {e}", exc_info=True)
                    return None
    
    target_space = config_status.get('target_space', 'Unknown')
    logger.info(f"Target space '{target_space}' found but not accessible, retrying...")
    return 0.5

def auto_start_ui_handler(dummy):
    import bpy
    wm = bpy.context.window_manager
    if wm.get("xwz_auto_start", False):
        if not bpy.app.timers.is_registered(_try_start_ui):
            bpy.app.timers.register(_try_start_ui, first_interval=0.1)

def register():
    _reinitialize_logging()  # Always re-init on addon (re)load — clears stale handlers
    import bpy
    from .render  import register as render_register
    from .text_op import register as txt_register
    from .text_input_op import register as txt_input_register
    from .img_op  import register as img_register
    from .panel   import register as panel_register
    from .hit_op import register as hit_register
    
    hit_register()
    
    bpy.types.WindowManager.xwz_ui_conf_path = bpy.props.StringProperty(
        name        = "XWZ UI Config Path",
        description = "Path to the configuration file for XWZ UI",
        default     = ""
    )
    bpy.types.WindowManager.xwz_debug_panel = bpy.props.BoolProperty(
        name        = "XWZ Debug Panel",
        description = "Enable or disable XWZ debug panel",
        default     = False
    )
    bpy.types.WindowManager.xwz_auto_start = bpy.props.BoolProperty(
        name        = "XWZ Auto Start",
        description = "Automatically start XWZ UI on file load",
        default     = False
    )
    
    render_register()
    txt_register()
    txt_input_register()
    img_register()
    panel_register()

    if auto_start_ui_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(auto_start_ui_handler)
    bpy.app.timers.register(_try_start_ui, first_interval=1.0)

    # Start the built-in reload server (enables `just reload` / `puree reload`)
    from .reload_server import ReloadServer, PUREE_RELOAD_PORT
    global _reload_server
    _reload_server = ReloadServer(
        port=PUREE_RELOAD_PORT,
        reload_fn=_deferred_reload,
    )
    _reload_server.start()

    # Sentinel fallback (covers edge cases where TCP isn't reachable)
    if not bpy.app.timers.is_registered(_check_reload_sentinel):
        bpy.app.timers.register(_check_reload_sentinel, persistent=True)

    # Start HTTP callback drain timer
    from .net import register as net_register
    net_register()

def unregister():
    import bpy
    from .render  import unregister as render_unregister
    from .text_op import unregister as txt_unregister
    from .text_input_op import unregister as txt_input_unregister
    from .img_op  import unregister as img_unregister
    from .panel   import unregister as panel_unregister
    from .hit_op import unregister as hit_unregister
    
    hit_unregister()
    
    if auto_start_ui_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(auto_start_ui_handler)
    if bpy.app.timers.is_registered(_try_start_ui):
        bpy.app.timers.unregister(_try_start_ui)

    try:
        from .render import _render_data, _modal_timer
        if _render_data:
            _render_data.cleanup()
        if _modal_timer:
            try:
                context = bpy.context
                context.window_manager.event_timer_remove(_modal_timer)
            except:
                pass
    except Exception as e:
        logger.warning(f"Error during forced cleanup: {e}")
    
    # Stop the reload server
    global _reload_server
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
    _get_sentinel_path().unlink(missing_ok=True)

    # Stop HTTP callback drain timer
    try:
        from .net import unregister as net_unregister
        net_unregister()
    except Exception as e:
        logger.warning(f"Net unregister warning: {e}")

    # Clean up all Puree-managed timers
    try:
        from .timers import _cleanup_all as _cleanup_timers
        _cleanup_timers()
    except Exception as e:
        logger.warning(f"Timer cleanup warning: {e}")

    del bpy.types.WindowManager.xwz_ui_conf_path
    del bpy.types.WindowManager.xwz_debug_panel
    del bpy.types.WindowManager.xwz_auto_start

    panel_unregister()
    img_unregister()
    txt_input_unregister()
    txt_unregister()
    render_unregister()

if __name__ == "__main__":
    register()