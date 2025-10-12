import bpy
import os
from puree import register as xwz_ui_register, unregister as xwz_ui_unregister
from puree import set_addon_root

bl_info = {
    "name"       : "Puree",
    "author"     : "Nicolai Prodromov",
    "version"    : (0, 0, 7),
    "blender"    : (4, 2, 0),
    "location"   : "3D View > Sidebar > Puree",
    "description": "XWZ Puree UI framework",
    "category"   : "3D View"
}

def register():
    # Set the addon root directory so puree package knows where to find resources
    addon_root = os.path.dirname(os.path.abspath(__file__))
    set_addon_root(addon_root)
    
    xwz_ui_register()
    wm = bpy.context.window_manager
    wm.xwz_ui_conf_path = "static/index.toml"
    wm.xwz_debug_panel  = True
    wm.xwz_auto_start   = True

def unregister():
    xwz_ui_unregister()
    
if __name__ == "__main__":
    register()