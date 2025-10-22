# Example 2 [CORE UI VOL. I]
# Created by XWZ
# ◕‿◕ Distributed for free at:
# https://github.com/nicolaiprodromov/puree/wiki
# ╔═════════════════════════════════╗
# ║  ██   ██  ██      ██  ████████  ║
# ║   ██ ██   ██  ██  ██       ██   ║
# ║    ███    ██  ██  ██     ██     ║
# ║   ██ ██   ██  ██  ██   ██       ║
# ║  ██   ██   ████████   ████████  ║
# ╚═════════════════════════════════╝

import bpy
from puree.utils import osb

def main(self, app):
    context = bpy.context
    
    if "Cube" not in bpy.data.objects:
        return app
    
    cube = bpy.data.objects["Cube"]
    bbox = osb(cube, context)
    
    if bbox:
        vizor = app.get_by_id("vizor")
        
        if vizor:
            vizor.set_property('width', f"{int(bbox['width']) + 40}px")
            vizor.set_property('height', f"{int(bbox['height']) + 40}px")
            vizor.set_property('margin_left', f"{int(bbox['x']) - 20}px")
            vizor.set_property('margin_top', f"{int(bbox['y']) - 20}px")
            vizor.mark_dirty()
    
    return app
