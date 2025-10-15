import bpy
import os
from .parser    import UI
from .compiler  import Compiler
from .extract_images import ImageExtractor
from .extract_text   import TextExtractor
from .extract_text_input import TextInputExtractor

XWZ_UI                = None
text_blocks           = {}
text_input_blocks     = {}
image_blocks          = {}
image_blocks_relative = {}
_container_json_data  = []

class XWZ_OT_ui_parser(bpy.types.Operator): 
    bl_idname = "xwz.parse_app_ui"
    bl_label  = "Parse App UI"

    conf_path : bpy.props.StringProperty(
        name        = "UI Config File Path",
        description = "Path to the configuration file for the UI layout",
        default     = "//index.toml"
    )

    def print_ui_struct(self):
        def find_children(children):
            for child in children:
                #print all child attributes
                print(f"Container ID:[ {child.id} ]")
                print(' ├────────────────────────────────────────────')
                print(f" ├─ Data               : {child.data}")
                print(f" ├─ Display            : {child.display}")
                print(f" ├─ Image              : {child.img}")
                print(f" ├─ Aspect Ratio       : {child.aspect_ratio}")
                print(f" ├─ Overflow           : {child.overflow}")
                print(f" ├─ Style              : {child.style}")
                print(' ├────────────────────────────────────────────')
                print(f" ├─ Parent ID          : [ {child.parent.id if child.parent else 'None'} ]")
                print(f" ├─ Number of Children : {len(child.children)}")
                if len(child.children) > 0:
                    for cc in child.children:
                        print(f" ├─────── Child ID : [ {cc.id} ]")
                print(' ├────────────────────────────────────────────')
                print(f" ├─  Position           : ({child.x}, {child.y})")
                print(f" ├─  Size               : ({child.width}, {child.height})")
                print(f" ├─  Color              : {child.color}")
                print(f" ├─  Color1             : {child.color_1}")
                print(f" ├─  Color G Rotation   : {child.color_gradient_rot}")
                print(f" ├─  Hover Color        : {child.hover_color}")
                print(f" ├─  Hover Color1       : {child.hover_color_1}")
                print(f" ├─  Hover Color G Rot  : {child.hover_color_gradient_rot}")
                print(f" ├─  Click Color        : {child.click_color}")
                print(f" ├─  Click Color1       : {child.click_color_1}")
                print(f" ├─  Click Color G Rot  : {child.click_color_gradient_rot}")
                print(f" ├─  Border Radius      : {child.border_radius}")
                print(f" ├─  Border Width       : {child.border_width}")
                print(f" ├─  Border Color       : {child.border_color}")
                print(f" ├─  Border Color1      : {child.border_color_1}")
                print(f" ├─  Border Color G Rot : {child.border_color_gradient_rot}")
                print(' ├───────────────────────────────────────────')
                print(f" ├─  Click Events       : {child.click}")
                print(f" ├─  Toggle Events      : {child.toggle}")
                print(f" ├─  Scroll Events      : {child.scroll}")
                print(f" ├─  Hover Events       : {child.hover}")
                print(' ├───────────────────────────────────────────')
                print(f" ├─  Font             : {child.font}")
                print(f" ├─  Text             : {child.text}")
                print(f" ├─  Text Scale       : {child.text_scale}")
                print(f" ├─  Text X           : {child.text_x}")
                print(f" ├─  Text Y           : {child.text_y}")
                print(f" ├─  Text Color       : {child.text_color}")
                print(f" ├─  Text Color1      : {child.text_color_1}")
                print(f" ├─  Text Color G Rot : {child.text_color_gradient_rot}")
                print(' ├───────────────────────────────────────────')
                print(f" ├─  Box Shadow Color   : {child.box_shadow_color}")
                print(f" ├─  Box Shadow Offset  : {child.box_shadow_offset}")
                print(f" ├─  Box Shadow Blur    : {child.box_shadow_blur}")
                print(' └───────────────────────────────────────────')
                find_children(child.children)
        find_children(self.ui.theme.root.children)
    
    def dump_ui_struct(self):
        global _container_json_data
        self.container_json_data = self.ui.abs_json_data
        _container_json_data = self.container_json_data
        return
    
    def execute(self, context):
        # get viewport size
        region_size = (800, 600)
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        region_size = (region.width, region.height)
                        break
                break
        global XWZ_UI, text_blocks, text_input_blocks, image_blocks, image_blocks_relative
        from . import get_addon_root
        addon_dir  = get_addon_root()

        self.ui              = UI(os.path.join(addon_dir, self.conf_path), addon_dir, canvas_size=region_size)
        self.compiler        = Compiler(self.ui)
        self.ui              = self.compiler.compile()
        
        self.image_extractor = ImageExtractor(self.ui, self.ui.abs_json_data)
        self.text_extractor  = TextExtractor(self.ui, self.ui.abs_json_data)
        self.text_input_extractor = TextInputExtractor(self.ui, self.ui.abs_json_data)

        text_blocks           = self.text_extractor.text_blocks
        text_input_blocks     = self.text_input_extractor.text_input_blocks
        image_blocks          = self.image_extractor.image_blocks
        image_blocks_relative = self.image_extractor.image_blocks_relative

        XWZ_UI = self.ui  # Store UI instance globally for layout recomputation
        self.dump_ui_struct()
        return {'FINISHED'}

def recompute_layout(canvas_size):
    global XWZ_UI, _container_json_data, text_blocks, text_input_blocks, image_blocks, image_blocks_relative
    
    if XWZ_UI is None:
        return None
    
    # Recompute layout with new canvas size
    updated_data = XWZ_UI.recompute_layout(canvas_size)
    
    # Update global container data
    _container_json_data = updated_data
    
    # Update text and image blocks with new layout
    text_extractor = TextExtractor(XWZ_UI, XWZ_UI.abs_json_data)
    text_input_extractor = TextInputExtractor(XWZ_UI, XWZ_UI.abs_json_data)
    image_extractor = ImageExtractor(XWZ_UI, XWZ_UI.abs_json_data)
    
    text_blocks = text_extractor.text_blocks
    text_input_blocks = text_input_extractor.text_input_blocks
    image_blocks = image_extractor.image_blocks
    image_blocks_relative = image_extractor.image_blocks_relative
    
    return _container_json_data

def sync_dirty_containers():
    """
    Sync container state from live Container objects to _container_json_data
    without full layout recomputation. This is called when scripts modify
    container properties (like colors, text, images) via event handlers.
    """
    global XWZ_UI, _container_json_data, text_blocks, text_input_blocks, image_blocks, image_blocks_relative
    
    if XWZ_UI is None or not _container_json_data:
        return False
    
    # Check if any containers are dirty
    has_dirty = check_dirty_containers(XWZ_UI.theme.root)
    if not has_dirty:
        return False
    
    # Sync live Container tree state to flattened json data
    # by reusing the existing abs_json_data structure
    XWZ_UI.abs_json_data = []
    XWZ_UI.flatten_node_tree()
    _container_json_data = XWZ_UI.abs_json_data
    
    # Regenerate text and image blocks to pick up changes
    # This ensures that changes to container.text and container.img
    # are reflected in the rendered output
    text_extractor = TextExtractor(XWZ_UI, XWZ_UI.abs_json_data)
    text_input_extractor = TextInputExtractor(XWZ_UI, XWZ_UI.abs_json_data)
    image_extractor = ImageExtractor(XWZ_UI, XWZ_UI.abs_json_data)
    
    text_blocks = text_extractor.text_blocks
    text_input_blocks = text_input_extractor.text_input_blocks
    image_blocks = image_extractor.image_blocks
    image_blocks_relative = image_extractor.image_blocks_relative
    
    # Clear dirty flags
    clear_dirty_flags(XWZ_UI.theme.root)
    
    return True

def check_dirty_containers(container):
    """Recursively check if any container in tree is marked dirty"""
    if hasattr(container, '_dirty') and container._dirty:
        return True
    for child in container.children:
        if check_dirty_containers(child):
            return True
    return False

def clear_dirty_flags(container):
    """Recursively clear all dirty flags in container tree"""
    if hasattr(container, '_dirty'):
        container._dirty = False
    for child in container.children:
        clear_dirty_flags(child)
    