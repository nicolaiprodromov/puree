import bpy
from bpy.types import Panel, PropertyGroup, UIList
from bpy.props import CollectionProperty, StringProperty, IntProperty, BoolProperty
from . import render

class ContainerItem(PropertyGroup):
    container_id: StringProperty()
    display_name: StringProperty()
    depth       : IntProperty()
    is_visible  : BoolProperty()
    is_outlined : BoolProperty()

class XWZ_UL_container_hierarchy(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            
            tree_prefix = ""
            for i in range(item.depth):
                if i == item.depth - 1:
                    tree_prefix += "├─ "
                else:
                    tree_prefix += "│  "
            
            icon = 'CHECKBOX_HLT' if item.is_outlined else 'CHECKBOX_DEHLT'
            op = row.operator("xwz.toggle_debug_outline", text="", icon=icon, emboss=False)
            op.container_id = item.container_id
            
            display_icon = 'HIDE_OFF' if item.is_visible else 'HIDE_ON'
            row.label(text=f"{tree_prefix}{item.display_name}", icon=display_icon)
            
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            icon = 'CHECKBOX_HLT' if item.is_outlined else 'CHECKBOX_DEHLT'
            layout.label(text="", icon=icon)

def update_container_hierarchy():
    from . import parser_op
    
    wm = bpy.context.window_manager
    wm.xwz_container_hierarchy.clear()
    
    if not parser_op._container_json_data:
        return
    
    containers = parser_op._container_json_data
    
    def build_tree(container_idx, depth=0, parent_id=None):
        if container_idx < 0 or container_idx >= len(containers):
            return
        
        container = containers[container_idx]
        item = wm.xwz_container_hierarchy.add()
        
        item.container_id = str(container_idx)
        
        full_id = container['id']
        
        if parent_id and full_id.startswith(parent_id + '_'):
            item.display_name = full_id[len(parent_id) + 1:]
        else:
            item.display_name = full_id
        
        item.depth = depth
        item.is_visible = container.get('display', True)
        
        is_outlined = False
        if render._render_data:
            is_outlined = item.container_id in render._render_data.debug_outlined_containers
        item.is_outlined = is_outlined
        
        for child_idx in container.get('children', []):
            build_tree(child_idx, depth + 1, full_id)
    
    build_tree(0, 0)

class XWZ_PT_panel(Panel):
    bl_label       = "puree"
    bl_idname      = "XWZ_PT_panel"
    bl_space_type  = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category    = "puree"
    
    @classmethod
    def poll(cls, context):
        return context.window_manager.xwz_debug_panel
    
    def draw(self, context):
        layout = self.layout
        
        if render._render_data and render._render_data.running:
            layout.label(text="Running", icon='PLAY')
            
            box = layout.box()
            col = box.column(align=True)
            col.separator()
            col.label(text=f"Texture: {render._render_data.texture_size[0]}x{render._render_data.texture_size[1]}")
            col.label(text=f"FPS: {render._render_data.compute_fps:.1f}")
            
            layout.separator()
            layout.operator("xwz.stop_ui", icon='PAUSE')
            
            layout.separator()
            layout.label(text="Container Hierarchy:", icon='OUTLINER')
            
            from . import parser_op
            if parser_op._container_json_data:
                update_container_hierarchy()
                
                wm = context.window_manager
                layout.template_list(
                    "XWZ_UL_container_hierarchy",
                    "",
                    wm,
                    "xwz_container_hierarchy",
                    wm,
                    "xwz_container_hierarchy_index",
                    rows=10
                )
            
        else:
            layout.label(text="Paused", icon='PAUSE')
            layout.operator("xwz.start_ui", icon='PLAY')
        
        layout.separator()
        layout.label(text="This is a debug panel.")

class XWZ_OT_toggle_debug_outline(bpy.types.Operator):
    bl_idname = "xwz.toggle_debug_outline"
    bl_label = "Toggle Debug Outline"
    bl_description = "Toggle debug outline for this container"
    
    container_id: bpy.props.StringProperty()
    
    def execute(self, context):
        if render._render_data:
            if self.container_id in render._render_data.debug_outlined_containers:
                render._render_data.debug_outlined_containers.remove(self.container_id)
            else:
                render._render_data.debug_outlined_containers.add(self.container_id)
            
            render._render_data.needs_texture_update = True
        
        return {'FINISHED'}

def register():
    bpy.utils.register_class(ContainerItem)
    bpy.utils.register_class(XWZ_UL_container_hierarchy)
    bpy.utils.register_class(XWZ_PT_panel)
    bpy.utils.register_class(XWZ_OT_toggle_debug_outline)
    
    bpy.types.WindowManager.xwz_container_hierarchy = CollectionProperty(type=ContainerItem)
    bpy.types.WindowManager.xwz_container_hierarchy_index = IntProperty()

def unregister():
    del bpy.types.WindowManager.xwz_container_hierarchy_index
    del bpy.types.WindowManager.xwz_container_hierarchy
    
    bpy.utils.unregister_class(XWZ_OT_toggle_debug_outline)
    bpy.utils.unregister_class(XWZ_PT_panel)
    bpy.utils.unregister_class(XWZ_UL_container_hierarchy)
    bpy.utils.unregister_class(ContainerItem)