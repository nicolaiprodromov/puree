import bpy
from bpy.types import Panel
from . import render

class XWZ_PT_panel(Panel):
    bl_label       = "XWZ UI"
    bl_idname      = "XWZ_PT_panel"
    bl_space_type  = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category    = "XWZ_UI"
    
    def draw(self, context):
        layout = self.layout
        
        if render._render_data and render._render_data.running:
            layout.label(text="Running", icon='PLAY')
            
            box = layout.box()
            col = box.column(align=True)
            col.separator()
            col.label(text=f"Resolution: {render._render_data.texture_size[0]}x{render._render_data.texture_size[1]}")
            col.label(text=f"FPS: {render._render_data.compute_fps:.1f}")
            
            total_frames = max(1, render._render_data.debug_counter)
            compute_skip_pct = (render._render_data.compute_shader_skips / total_frames) * 100
            texture_skip_pct = (render._render_data.dirty_flag_skips / total_frames) * 100
            
            col.separator()
            col.label(text=f"Compute: {100-compute_skip_pct:.0f}% active")
            col.label(text=f"Readback: {100-texture_skip_pct:.0f}% active")
            
            layout.separator()
            layout.operator("xwz.stop_ui", icon='PAUSE')
        else:
            layout.label(text="Paused", icon='PAUSE')
            layout.operator("xwz.start_ui", icon='PLAY')
        
        layout.separator()
        layout.label(text="This is a debug panel.")

def register():
    bpy.utils.register_class(XWZ_PT_panel)

def unregister():
    bpy.utils.unregister_class(XWZ_PT_panel)