import bpy
import blf
import os

_text_instances = []
_draw_handle = None
_timer_handle = None

def trigger_text_redraw():
    if _text_instances:
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
    return 0.016

class FontManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.fonts = {}
            self.font_ids = {}
            self._load_fonts()
            self._initialized = True
    
    def _load_fonts(self):
        addon_fonts_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts")
        if os.path.exists(addon_fonts_path):
            for font_file in os.listdir(addon_fonts_path):
                if font_file.lower().endswith(('.otf', '.ttf')):
                    font_path = os.path.join(addon_fonts_path, font_file)
                    try:
                        font_id = blf.load(font_path)
                        font_name = os.path.splitext(font_file)[0]
                        self.fonts[font_name] = font_path
                        self.font_ids[font_name] = font_id
                    except Exception as e:
                        print(f"Failed to load font {font_file}: {e}")
    
    def get_font_id(self, font_name):
        return self.font_ids.get(font_name, 0)
    
    def get_available_fonts(self):
        return list(self.fonts.keys())
    
    def unload_fonts(self):
        for font_name, font_path in self.fonts.items():
            try:
                blf.unload(font_path)
            except Exception as e:
                print(f"Failed to unload font {font_name} (path: {font_path}): {e}")
        self.fonts.clear()
        self.font_ids.clear()

font_manager = FontManager()

class TextInstance:
    def __init__(self, container_id, text="Hello", font_name=None, size=20, pos=[50, 50], color=[1,1,1,1], mask=None):
        self.container_id = container_id
        self.id        = len(_text_instances)
        self.text      = text
        self.font_name = font_name
        self.font_id   = font_manager.get_font_id(self.font_name) if self.font_name else 0
        self.size      = size
        self.position  = pos
        self.color     = color
        self.mask      = mask
    def update_text(self, new_text):
        self.text = new_text
        self._trigger_redraw()
    def update_font(self, new_font_name):
        if new_font_name in font_manager.get_available_fonts():
            self.font_name = new_font_name
            self.font_id = font_manager.get_font_id(new_font_name)
            self._trigger_redraw()
    def update_size(self, new_size):
        self.size = max(1, min(200, new_size))
        self._trigger_redraw()
    def update_position(self, new_pos):
        self.position = list(new_pos)
        self._trigger_redraw()
    def update_color(self, new_color):
        self.color = list(new_color)
        self._trigger_redraw()
    def update_mask(self, new_mask):
        self.mask = new_mask
        self._trigger_redraw()
    def update_all(self, text=None, font_name=None, size=None, pos=None, color=None, mask=None):
        if text is not None:
            self.text = text
        if font_name is not None and font_name in font_manager.get_available_fonts():
            self.font_name = font_name
            self.font_id = font_manager.get_font_id(font_name)
        if size is not None:
            self.size = max(1, min(200, size))
        if pos is not None:
            self.position = list(pos)
        if color is not None:
            self.color = list(color)
        if mask is not None:
            self.mask = mask
        self._trigger_redraw()
    def _trigger_redraw(self):
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

def draw_all_text():
    # Get viewport height to flip Y coordinate
    viewport_height = 0
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for region in area.regions:
                if region.type == 'WINDOW':
                    viewport_height = region.height
                    break
            break
    
    for instance in _text_instances:
        if instance.mask and instance.mask[2] > 0 and instance.mask[3] > 0:
            xmin = instance.mask[0]
            ymin = viewport_height - instance.mask[1] - instance.mask[3]
            xmax = instance.mask[0] + instance.mask[2]
            ymax = viewport_height - instance.mask[1]
            blf.clipping(instance.font_id, xmin, ymin, xmax, ymax)
            blf.enable(instance.font_id, blf.CLIPPING)
        
        flipped_y = viewport_height - instance.position[1] - instance.size
        blf.position(instance.font_id, instance.position[0], flipped_y, 0)
        blf.size(instance.font_id, instance.size)
        blf.color(instance.font_id, *instance.color)
        blf.draw(instance.font_id, instance.text)
        
        if instance.mask and instance.mask[2] > 0 and instance.mask[3] > 0:
            blf.disable(instance.font_id, blf.CLIPPING)

class DrawTextOP(bpy.types.Operator):
    bl_idname = "xwz.draw_text"
    bl_label = "Add Text Instance"

    container_id: bpy.props.StringProperty(name="Container ID", default="root")
    text        : bpy.props.StringProperty(name="Text", default="New Text")
    font_name   : bpy.props.EnumProperty(
        name    = "Font",
        items   = lambda self, context: [(name, name, "") for name in font_manager.get_available_fonts()] or [("default", "Default", "")],
        default = 0
    )
    size       : bpy.props.IntProperty(name="Size", default=20, min=1, max=200)
    x_pos      : bpy.props.IntProperty(name="X Position", default=50)
    y_pos      : bpy.props.IntProperty(name="Y Position", default=50)
    color      : bpy.props.FloatVectorProperty(name="Color", subtype='COLOR', size=4, default=(1.0, 1.0, 1.0, 1.0))
    mask_x     : bpy.props.IntProperty(name="Mask X", default=0)
    mask_y     : bpy.props.IntProperty(name="Mask Y", default=0)
    mask_width : bpy.props.IntProperty(name="Mask Width", default=0)
    mask_height: bpy.props.IntProperty(name="Mask Height", default=0)
    
    def execute(self, context):
        global _draw_handle, _text_instances, _timer_handle
        
        mask = None
        if self.mask_width > 0 and self.mask_height > 0:
            mask = [self.mask_x, self.mask_y, self.mask_width, self.mask_height]
        
        new_instance = TextInstance(
            container_id=self.container_id,
            text=self.text,
            font_name=self.font_name,
            size=self.size,
            pos=[self.x_pos, self.y_pos],
            color=list(self.color),
            mask=mask
        )
        _text_instances.append(new_instance)
        
        if _draw_handle is None:
            _draw_handle = bpy.types.SpaceView3D.draw_handler_add(
                draw_all_text, (), 'WINDOW', 'POST_PIXEL')
        
        if _timer_handle is None:
            _timer_handle = bpy.app.timers.register(trigger_text_redraw)
        
        context.area.tag_redraw()
        self.report({'INFO'}, f"Added text instance #{new_instance.id} with font {self.font_name}")
        return {'FINISHED'}

class RemoveTextOP(bpy.types.Operator):
    bl_idname = "xwz.remove_text"
    bl_label = "Remove Text Instance"
    
    instance_id: bpy.props.IntProperty(name="Instance ID", default=0, min=0)
    
    def execute(self, context):
        global _draw_handle, _text_instances
        
        for i, instance in enumerate(_text_instances):
            if instance.id == self.instance_id:
                _text_instances.pop(i)
                self.report({'INFO'}, f"Removed text instance #{self.instance_id}")
                break
        else:
            self.report({'ERROR'}, f"Text instance #{self.instance_id} not found")
            return {'CANCELLED'}
        
        if not _text_instances and _draw_handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, 'WINDOW')
            _draw_handle = None
        
        context.area.tag_redraw()
        return {'FINISHED'}

class ClearTextOP(bpy.types.Operator):
    bl_idname = "xwz.clear_text"
    bl_label = "Clear All Text"
    
    def execute(self, context):
        global _draw_handle, _text_instances, _timer_handle
        
        _text_instances.clear()
        
        if _draw_handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, 'WINDOW')
            _draw_handle = None
        
        if _timer_handle is not None and bpy.app.timers.is_registered(trigger_text_redraw):
            bpy.app.timers.unregister(trigger_text_redraw)
            _timer_handle = None
        
        context.area.tag_redraw()
        return {'FINISHED'}

class UpdateTextOP(bpy.types.Operator):
    bl_idname = "xwz.update_text"
    bl_label = "Update Text Instance"
    
    instance_id: bpy.props.IntProperty(name="Instance ID", default=0, min=0)
    text       : bpy.props.StringProperty(name="New Text", default="")
    font_name  : bpy.props.EnumProperty(
        name="Font",
        items=lambda self, context: [("__NOCHANGE__", "No Change", "Don't change the font")] + 
              [(name, name, "") for name in font_manager.get_available_fonts()],
        default=0
    )
    size       : bpy.props.IntProperty(name="Size", default=-1, min=-1, max=200)
    x_pos      : bpy.props.IntProperty(name="X Position", default=-999999)
    y_pos      : bpy.props.IntProperty(name="Y Position", default=-999999)
    color      : bpy.props.FloatVectorProperty(name="Color", subtype='COLOR', size=4, default=(-1, -1, -1, -1))
    mask_x     : bpy.props.IntProperty(name="Mask X", default=-999999)
    mask_y     : bpy.props.IntProperty(name="Mask Y", default=-999999)
    mask_width : bpy.props.IntProperty(name="Mask Width", default=-1)
    mask_height: bpy.props.IntProperty(name="Mask Height", default=-1)
    
    def execute(self, context):
        for instance in _text_instances:
            if instance.id == self.instance_id:
                kwargs = {}
                
                # Check text content
                if self.text:  # Empty string means no change
                    kwargs['text'] = self.text
                
                # Check font
                if self.font_name != "__NOCHANGE__" and self.font_name in font_manager.get_available_fonts():
                    kwargs['font_name'] = self.font_name
                
                # Check size
                if self.size != -1:
                    kwargs['size'] = self.size
                
                # Check position
                if self.x_pos != -999999 or self.y_pos != -999999:
                    new_x = self.x_pos if self.x_pos != -999999 else instance.position[0]
                    new_y = self.y_pos if self.y_pos != -999999 else instance.position[1]
                    kwargs['pos'] = [new_x, new_y]
                
                # Check color (if any component is not -1, update the whole color)
                if any(c != -1 for c in self.color):
                    # If some components are -1, keep the current values for those
                    current_color = instance.color
                    new_color = [
                        self.color[0] if self.color[0] != -1 else current_color[0],
                        self.color[1] if self.color[1] != -1 else current_color[1],
                        self.color[2] if self.color[2] != -1 else current_color[2],
                        self.color[3] if self.color[3] != -1 else current_color[3]
                    ]
                    kwargs['color'] = new_color
                
                # Check mask
                if (self.mask_x != -999999 or self.mask_y != -999999 or 
                    self.mask_width != -1 or self.mask_height != -1):
                    current_mask = instance.mask or [0, 0, 0, 0]
                    new_mask = [
                        self.mask_x if self.mask_x != -999999 else current_mask[0],
                        self.mask_y if self.mask_y != -999999 else current_mask[1],
                        self.mask_width if self.mask_width != -1 else current_mask[2],
                        self.mask_height if self.mask_height != -1 else current_mask[3]
                    ]
                    # Set mask to None if width or height is 0 or negative
                    kwargs['mask'] = new_mask if new_mask[2] > 0 and new_mask[3] > 0 else None
                
                if kwargs:  # Only update if something changed
                    instance.update_all(**kwargs)
                    updated_props = list(kwargs.keys())
                    self.report({'INFO'}, f"Updated text instance #{self.instance_id}: {', '.join(updated_props)}")
                else:
                    self.report({'INFO'}, f"No properties specified to update for text instance #{self.instance_id}")
                
                return {'FINISHED'}
        
        self.report({'ERROR'}, f"Text instance #{self.instance_id} not found")
        return {'CANCELLED'}

def register():
    bpy.utils.register_class(DrawTextOP)
    bpy.utils.register_class(RemoveTextOP)
    bpy.utils.register_class(ClearTextOP)
    bpy.utils.register_class(UpdateTextOP)

def unregister():
    global _draw_handle, _timer_handle, _text_instances
    
    # Force clear all text instances
    _text_instances.clear()
    
    if _draw_handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, 'WINDOW')
        _draw_handle = None
    if _timer_handle is not None and bpy.app.timers.is_registered(trigger_text_redraw):
        bpy.app.timers.unregister(trigger_text_redraw)
        _timer_handle = None
    
    font_manager.unload_fonts()
    
    bpy.utils.unregister_class(DrawTextOP)
    bpy.utils.unregister_class(RemoveTextOP)
    bpy.utils.unregister_class(ClearTextOP)
    bpy.utils.unregister_class(UpdateTextOP)
