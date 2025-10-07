import bpy
from bpy.app.handlers import persistent
from .render  import register as render_register, unregister as render_unregister
from .text_op import register as txt_register, unregister as txt_unregister
from .img_op  import register as img_register, unregister as img_unregister
from .hit_op  import register as hit_register, unregister as hit_unregister
from .panel   import register as panel_register, unregister as panel_unregister

def _try_start_ui():
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                region = None
                for r in area.regions:
                    if r.type == 'WINDOW':
                        region = r
                        break
                
                if not region:
                    print("Found 3D View but no WINDOW region, retrying...")
                    return 0.5
                
                override = {
                    'window': window,
                    'screen': screen,
                    'area': area,
                    'region': region,
                }
                try:
                    with bpy.context.temp_override(**override):
                        bpy.ops.xwz.start_ui()
                    print("Puree UI auto-started successfully")
                    return None
                except Exception as e:
                    print(f"Failed to auto-start Puree UI: {e}")
                    import traceback
                    traceback.print_exc()
                    return None
    print("No 3D View found yet, retrying...")
    return 0.5
@persistent
def auto_start_ui_handler(dummy):
    wm = bpy.context.window_manager
    if wm.get("xwz_auto_start", False):
        if not bpy.app.timers.is_registered(_try_start_ui):
            bpy.app.timers.register(_try_start_ui, first_interval=0.1)

def register():
    bpy.types.WindowManager.xwz_ui_conf_path = bpy.props.StringProperty(
        name        = "XWZ UI Config Path",
        description = "Path to the configuration file for XWZ UI",
        default     = "index.toml"
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
    img_register()
    panel_register()
    hit_register()

    if auto_start_ui_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(auto_start_ui_handler)
    bpy.app.timers.register(_try_start_ui, first_interval=1.0)

def unregister():
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

    hit_unregister()
    panel_unregister()
    img_unregister()
    txt_unregister()
    render_unregister()

if __name__ == "__main__":
    register()