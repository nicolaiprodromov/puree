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

__all__ = ['register', 'unregister', 'set_addon_root', 'get_addon_root']
__version__ = "0.1.0"
_ADDON_ROOT = None

def set_addon_root(path):
    global _ADDON_ROOT
    _ADDON_ROOT = path

def get_addon_root():
    global _ADDON_ROOT
    if _ADDON_ROOT is not None:
        return _ADDON_ROOT
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _try_start_ui():
    import bpy
    from .space_config import parse_space_config, validate_current_configuration
    
    wm = bpy.context.window_manager
    conf_path = wm.get("xwz_ui_conf_path", "index.yaml")
    
    if not parse_space_config(conf_path):
        print("Failed to parse space configuration, retrying...")
        return 0.5
    
    config_status = validate_current_configuration()
    
    if not config_status['space_available']:
        target_space = config_status.get('target_space', 'Unknown')
        print(f"Target space '{target_space}' not available yet, retrying...")
        return 0.5
    
    area = config_status['area']
    region = config_status['region']
    
    if not (area and region):
        print("Found target space but no WINDOW region, retrying...")
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
                    print(f"Puree UI auto-started successfully in {target_space}")
                    return None
                except Exception as e:
                    print(f"Failed to auto-start Puree UI: {e}")
                    import traceback
                    traceback.print_exc()
                    return None
    
    target_space = config_status.get('target_space', 'Unknown')
    print(f"Target space '{target_space}' found but not accessible, retrying...")
    return 0.5

def auto_start_ui_handler(dummy):
    import bpy
    wm = bpy.context.window_manager
    if wm.get("xwz_auto_start", False):
        if not bpy.app.timers.is_registered(_try_start_ui):
            bpy.app.timers.register(_try_start_ui, first_interval=0.1)

def register():
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
        default     = "index.yaml"
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
        print(f"Warning: Error during forced cleanup: {e}")
    
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