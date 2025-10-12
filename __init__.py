import bpy
from .puree import register as xwz_ui_register, unregister as xwz_ui_unregister

bl_info = {
    "name"       : "Puree",
    "author"     : "Nicolai Prodromov",
    "version"    : (0, 0, 6),
    "blender"    : (4, 2, 0),
    "location"   : "3D View > Sidebar > Puree",
    "description": "XWZ Puree UI framework",
    "category"   : "3D View"
}

def register():
    xwz_ui_register()
    wm = bpy.context.window_manager
    wm.xwz_ui_conf_path = "static/index.toml"
    wm.xwz_debug_panel  = True
    wm.xwz_auto_start   = True

def unregister():
    xwz_ui_unregister()
    
if __name__ == "__main__":
    register()