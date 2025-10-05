import bpy
from .render  import register as render_register, unregister as render_unregister
from .text_op import register as txt_register, unregister as txt_unregister
from .img_op  import register as img_register, unregister as img_unregister
from .hit_op  import register as hit_register, unregister as hit_unregister
from .panel   import register as panel_register, unregister as panel_unregister

def register():
    bpy.types.WindowManager.xwz_ui_conf_path = bpy.props.StringProperty(
        name        = "XWZ UI Config Path",
        description = "Path to the configuration file for XWZ UI",
        default     = "index.toml"
    )
    bpy.types.WindowManager.xwz_ui_style_path = bpy.props.StringProperty(
        name        = "XWZ UI Style Path",
        description = "Path to the configuration file for XWZ UI styles",
        default     = "style.css"
    )
    
    render_register()
    txt_register()
    img_register()
    panel_register()
    hit_register()

def unregister():
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
    del bpy.types.WindowManager.xwz_ui_style_path

    hit_unregister()
    panel_unregister()
    img_unregister()
    txt_unregister()
    render_unregister()

if __name__ == "__main__":
    register()