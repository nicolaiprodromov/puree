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
            sys.stderr.write(f"[Puree] reload {mod_name}: {e}\n")

from puree import register as xwz_ui_register, unregister as xwz_ui_unregister
from puree import set_addon_root

bl_info = {
    "name"       : "Puree",
    "author"     : "Nicolai Prodromov",
    "version"    : (0, 1, 3),
    "blender"    : (5, 1, 0),
    "location"   : "3D View > Sidebar > Puree",
    "description": "XWZ Puree UI framework",
    "category"   : "3D View"
}

def register():
    # Resolve symlinks so dev-link paths point to the actual source directory
    set_addon_root(os.path.realpath(os.path.dirname(os.path.abspath(__file__))))
    # Register the framework
    xwz_ui_register()
    # Set default properties
    # ui_conf_path is relative to the addon root directory and
    # is required to point puree to the main configuration file of your UI
    wm = bpy.context.window_manager
    wm.xwz_ui_conf_path = "static/index.yaml"
    wm.xwz_debug_panel  = True
    wm.xwz_auto_start   = True

def unregister():
    # Unregister the framework
    xwz_ui_unregister()
    
if __name__ == "__main__":
    register()