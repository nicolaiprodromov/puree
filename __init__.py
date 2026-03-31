import importlib
import os
import sys

import bpy

if "puree" in sys.modules:
    importlib.reload(sys.modules["puree"])

from puree import register as xwz_ui_register
from puree import set_addon_root
from puree import unregister as xwz_ui_unregister

bl_info = {
    "name": "Puree",
    "author": "Nicolai Prodromov",
    "version": (0, 1, 3),
    "blender": (5, 1, 0),
    "location": "3D View > Sidebar > Puree",
    "description": "XWZ Puree UI framework",
    "category": "3D View",
}


def register():
    set_addon_root(os.path.dirname(os.path.abspath(__file__)))
    xwz_ui_register()
    wm = bpy.context.window_manager
    wm.xwz_ui_conf_path = "tests/example0/index.yaml"
    wm.xwz_debug_panel = True
    wm.xwz_auto_start = True


def unregister():
    xwz_ui_unregister()


if __name__ == "__main__":
    register()
