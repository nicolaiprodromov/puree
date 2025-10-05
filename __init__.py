import bpy
from .src import register as xwz_ui_register, unregister as xwz_ui_unregister

bl_info = {
    "name"       : "XWZ Shader UI",
    "author"     : "Nicolai Prodromov",
    "version"    : (1, 0, 0),
    "blender"    : (4, 2, 0),
    "location"   : "3D View > Sidebar > XWZ UI",
    "description": "XWZ Shader UI",
    "category"   : "3D View",
}

def register():
    xwz_ui_register()
    wm = bpy.context.window_manager
    wm.xwz_ui_conf_path  = "index.toml"

def unregister():
    xwz_ui_unregister()

if __name__ == "__main__":
    register()