import bpy
import os
from puree import register as xwz_ui_register, unregister as xwz_ui_unregister
from puree import set_addon_root

bl_info = {
    "name"       : "Puree",
    "author"     : "Nicolai Prodromov",
    "version"    : (0, 1, 0),
    "blender"    : (4, 2, 0),
    "location"   : "3D View > Sidebar > Puree",
    "description": "XWZ Puree UI framework",
    "category"   : "3D View"
}

def register():
    # Set the addon root directory so puree knows where to find resources
    set_addon_root(os.path.dirname(os.path.abspath(__file__)))
    # Register the framework
    xwz_ui_register()
    # Set default properties
    # ui_conf_path is relative to the addon root directory and
    # is required to point puree to the main configuration file of your UI
    wm = bpy.context.window_manager
    wm.xwz_ui_conf_path = "examples/example1/index.yaml"
    wm.xwz_debug_panel  = True
    wm.xwz_auto_start   = True

def unregister():
    # Unregister the framework
    xwz_ui_unregister()
    
if __name__ == "__main__":
    register()