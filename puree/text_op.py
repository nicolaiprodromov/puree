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
import blf
import gpu
import os

from .log import get_logger
logger = get_logger(__name__)

_text_instances = []
_draw_handle = None
_text_dims_cache = {}
_cached_viewport_height = None

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
        from . import get_addon_root
        addon_fonts_path = os.path.join(get_addon_root(), "fonts")
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
                        logger.error(f"Failed to load font {font_file}: {e}")
    
    def get_font_id(self, font_name):
        return self.font_ids.get(font_name, 0)
    
    def get_available_fonts(self):
        return list(self.fonts.keys())
    
    def resolve_font_variant(self, base_font_name, weight='NORMAL', style='NORMAL'):
        """Resolve a font variant based on weight and style.
        Returns a font_id for the best matching variant."""
        if not base_font_name or base_font_name == 'default':
            return self.get_font_id(base_font_name)
        
        # Extract family name by stripping known suffixes
        family = base_font_name
        for suffix in ('BoldItalic', 'LightItalic', 'Bold', 'Italic', 'Light', 'Regular'):
            if family.endswith('-' + suffix):
                family = family[:-len(suffix) - 1]
                break
        
        # Map weight
        weight_str = str(weight).upper()
        if weight_str in ('BOLD', '700', '800', '900'):
            weight_suffix = 'Bold'
        elif weight_str in ('LIGHT', '300'):
            weight_suffix = 'Light'
        else:
            weight_suffix = ''
        
        # Map style
        style_suffix = 'Italic' if str(style).upper() == 'ITALIC' else ''
        
        # Build variant name: family-WeightStyle
        if weight_suffix and style_suffix:
            variant = f"{family}-{weight_suffix}{style_suffix}"
        elif weight_suffix:
            variant = f"{family}-{weight_suffix}"
        elif style_suffix:
            variant = f"{family}-{style_suffix}"
        else:
            variant = f"{family}-Regular"
        
        if variant in self.font_ids:
            return self.font_ids[variant]
        
        # Fallback to the base font name as-is
        return self.get_font_id(base_font_name)
    
    def unload_fonts(self):
        for font_name, font_path in self.fonts.items():
            try:
                blf.unload(font_path)
            except Exception as e:
                logger.error(f"Failed to unload font {font_name} (path: {font_path}): {e}")
        self.fonts.clear()
        self.font_ids.clear()
    
    def reload_fonts(self):
        """Reload all fonts - used when addon is re-enabled without Blender restart"""
        self.unload_fonts()
        self._load_fonts()
    
    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance - used during addon unregister"""
        if cls._instance is not None:
            if cls._instance._initialized:
                cls._instance.unload_fonts()
            cls._instance = None

font_manager = FontManager()

class TextInstance:
    def __init__(self, container_id, text="Hello", font_name=None, size=20, pos=[50, 50], color=[1,1,1,1], mask=None, align_h='LEFT', align_v='CENTER',
                 text_decoration='NONE', letter_spacing=0.0, line_height=0.0,
                 font_weight='NORMAL', font_style='NORMAL', white_space='NORMAL', text_overflow='CLIP',
                 text_shadow_color=None, text_shadow_offset_x=0.0, text_shadow_offset_y=0.0, text_shadow_blur=0.0):
        self.container_id = container_id
        self.id        = len(_text_instances)
        self.text      = text
        self.font_name = font_name
        self.font_weight = font_weight
        self.font_style  = font_style
        self.font_id   = font_manager.resolve_font_variant(self.font_name, self.font_weight, self.font_style) if self.font_name else 0
        self.size      = size
        self.position  = pos
        self.color     = color
        self.mask      = mask
        self.clip      = None  # Separate scissor clip rect [x, y, w, h] for scroll clipping
        self.align_h   = align_h
        self.align_v   = align_v
        self.text_decoration = text_decoration
        self.letter_spacing  = letter_spacing
        self.line_height     = line_height
        self.white_space     = white_space
        self.text_overflow   = text_overflow
        self.text_shadow_color  = text_shadow_color if text_shadow_color is not None else [0, 0, 0, 0]
        self.text_shadow_offset = [text_shadow_offset_x, text_shadow_offset_y]
        self.text_shadow_blur   = text_shadow_blur
        self._cached_dims = None
        self._dims_key = None
    
    def _get_dimensions(self):
        """Get text dimensions, using cache when possible."""
        key = (self.text, self.font_id, self.size, self.letter_spacing)
        if self._dims_key == key and self._cached_dims is not None:
            return self._cached_dims
        blf.size(self.font_id, self.size)
        w, h = blf.dimensions(self.font_id, self.text)
        if self.letter_spacing > 0 and len(self.text) > 1:
            w += self.letter_spacing * (len(self.text) - 1)
        self._cached_dims = (w, h)
        self._dims_key = key
        return self._cached_dims
    
    def _invalidate_dims_cache(self):
        self._cached_dims = None
        self._dims_key = None
    def update_text(self, new_text):
        self.text = new_text
        self._invalidate_dims_cache()
        self._trigger_redraw()
    def update_font(self, new_font_name):
        if new_font_name == "default" or new_font_name in font_manager.get_available_fonts():
            self.font_name = new_font_name
            self.font_id = font_manager.get_font_id(new_font_name)
            self._invalidate_dims_cache()
            self._trigger_redraw()
    def update_size(self, new_size):
        self.size = max(1, min(200, new_size))
        self._invalidate_dims_cache()
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
    def update_all(self, text=None, font_name=None, size=None, pos=None, color=None, mask=None, clip=None, align_h=None, align_v=None,
                   text_decoration=None, letter_spacing=None, line_height=None,
                   font_weight=None, font_style=None, white_space=None, text_overflow=None):
        dims_dirty = False
        if text is not None and text != self.text:
            self.text = text
            dims_dirty = True
        if font_name is not None and (font_name == "default" or font_name in font_manager.get_available_fonts()):
            if font_name != self.font_name:
                self.font_name = font_name
                self.font_id = font_manager.resolve_font_variant(font_name, self.font_weight, self.font_style)
                dims_dirty = True
        if font_weight is not None and font_weight != self.font_weight:
            self.font_weight = font_weight
            self.font_id = font_manager.resolve_font_variant(self.font_name, self.font_weight, self.font_style)
            dims_dirty = True
        if font_style is not None and font_style != self.font_style:
            self.font_style = font_style
            self.font_id = font_manager.resolve_font_variant(self.font_name, self.font_weight, self.font_style)
            dims_dirty = True
        if size is not None and size != self.size:
            self.size = max(1, min(200, size))
            dims_dirty = True
        if pos is not None:
            self.position = list(pos)
        if color is not None:
            self.color = list(color)
        if mask is not None:
            self.mask = mask
        if clip is not None:
            self.clip = clip
        if align_h is not None:
            self.align_h = align_h
        if align_v is not None:
            self.align_v = align_v
        if text_decoration is not None:
            self.text_decoration = text_decoration
        if letter_spacing is not None:
            self.letter_spacing = letter_spacing
        if line_height is not None:
            self.line_height = line_height
        if white_space is not None:
            self.white_space = white_space
        if text_overflow is not None:
            self.text_overflow = text_overflow
        if dims_dirty:
            self._invalidate_dims_cache()
        self._trigger_redraw()
    def _trigger_redraw(self):
        from .space_config import get_target_space
        target_space = get_target_space()
        for area in bpy.context.screen.areas:
            if area.type == target_space:
                area.tag_redraw()

_decoration_shader = None
_decoration_batch_cache = {}

def _get_decoration_shader():
    global _decoration_shader
    if _decoration_shader is None:
        _decoration_shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    return _decoration_shader

def _draw_text_decoration(x, y, text_width, text_height, font_size, color, decoration):
    """Draw underline, overline, or line-through decoration lines."""
    shader = _get_decoration_shader()
    thickness = max(1.0, font_size / 14.0)
    lines = []
    
    if 'UNDERLINE' in decoration:
        line_y = y + thickness
        lines.append((x, line_y, x + text_width, line_y))
    if 'OVERLINE' in decoration:
        line_y = y + text_height - thickness
        lines.append((x, line_y, x + text_width, line_y))
    if 'LINE_THROUGH' in decoration or 'LINE-THROUGH' in decoration:
        line_y = y + text_height * 0.45
        lines.append((x, line_y, x + text_width, line_y))
    
    if not lines:
        return
    
    from gpu_extras.batch import batch_for_shader
    vertices = []
    for x1, y1, x2, y2 in lines:
        # Draw as thin quad for consistent thickness
        half = thickness / 2
        vertices.extend([(x1, y1 - half), (x2, y1 - half), (x2, y1 + half),
                         (x1, y1 - half), (x2, y1 + half), (x1, y1 + half)])
    
    batch = batch_for_shader(shader, 'TRIS', {"pos": vertices})
    shader.bind()
    shader.uniform_float("color", color)
    saved_blend = gpu.state.blend_get()
    gpu.state.blend_set('ALPHA')
    batch.draw(shader)
    gpu.state.blend_set(saved_blend)

def draw_all_text():
    global _cached_viewport_height
    
    # Cache viewport height — only scan areas if not cached
    if _cached_viewport_height is None:
        from .space_config import get_target_space
        target_space = get_target_space()
        for area in bpy.context.screen.areas:
            if area.type == target_space:
                for region in area.regions:
                    if region.type == 'WINDOW':
                        _cached_viewport_height = region.height
                        break
                break
    
    viewport_height = _cached_viewport_height or 0
    
    for instance in _text_instances:
        use_scissor = instance.clip is not None and instance.clip[2] > 0 and instance.clip[3] > 0
        
        # GPU scissor for true pixel-level clipping (scroll containers)
        if use_scissor:
            sc_x = int(instance.clip[0])
            sc_y = int(viewport_height - instance.clip[1] - instance.clip[3])
            sc_w = int(instance.clip[2])
            sc_h = int(instance.clip[3])
            gpu.state.scissor_test_set(True)
            gpu.state.scissor_set(sc_x, sc_y, sc_w, sc_h)
        elif instance.mask and instance.mask[2] > 0 and instance.mask[3] > 0:
            # BLF clipping for non-scroll text (alignment-based)
            xmin = instance.mask[0]
            ymin = viewport_height - instance.mask[1] - instance.mask[3]
            xmax = instance.mask[0] + instance.mask[2]
            ymax = viewport_height - instance.mask[1]
            blf.clipping(instance.font_id, xmin, ymin, xmax, ymax)
            blf.enable(instance.font_id, blf.CLIPPING)
        
        blf.size(instance.font_id, instance.size)
        text_width, text_height = instance._get_dimensions()
        
        # Resolve line height multiplier (0 means default 1.2)
        lh_mult = instance.line_height if instance.line_height > 0 else 1.2
        line_step = instance.size * lh_mult
        
        # Split text into lines based on white_space mode
        ws = instance.white_space
        raw_text = instance.text
        if ws == 'PRE' and '\n' in raw_text:
            lines = raw_text.split('\n')
        elif ws == 'NOWRAP' or '\n' not in raw_text:
            lines = [raw_text]
        else:
            # NORMAL: collapse whitespace, single line (wrapping handled below)
            lines = [raw_text]
        
        # Compute total block dimensions for alignment
        if len(lines) > 1:
            line_widths = []
            for ln in lines:
                lw, _ = blf.dimensions(instance.font_id, ln)
                if instance.letter_spacing > 0 and len(ln) > 1:
                    lw += instance.letter_spacing * (len(ln) - 1)
                line_widths.append(lw)
            block_width = max(line_widths) if line_widths else text_width
            block_height = text_height + line_step * (len(lines) - 1)
        else:
            block_width = text_width
            block_height = text_height
            line_widths = [text_width]
        
        x_pos = instance.position[0]
        y_pos = instance.position[1]
        
        # Alignment is always computed relative to MASK (the container's own bounds)
        if instance.mask and instance.mask[2] > 0 and instance.mask[3] > 0:
            container_width = instance.mask[2]
            container_height = instance.mask[3]
            
            if instance.align_h == 'LEFT':
                x_pos = instance.mask[0]
            elif instance.align_h == 'CENTER':
                x_pos = instance.mask[0] + (container_width - block_width) / 2
            elif instance.align_h == 'RIGHT':
                x_pos = instance.mask[0] + container_width - block_width
            
            if instance.align_v == 'TOP':
                y_pos = instance.mask[1]
            elif instance.align_v == 'CENTER':
                y_pos = instance.mask[1] + (container_height - block_height) / 2
            elif instance.align_v == 'BOTTOM':
                y_pos = instance.mask[1] + container_height - block_height
        
        # Text-overflow: ELLIPSIS truncation
        container_w = instance.mask[2] if instance.mask and instance.mask[2] > 0 else 0
        
        blf.color(instance.font_id, *instance.color)
        
        for line_idx, line_text in enumerate(lines):
            cur_lw = line_widths[line_idx] if line_idx < len(line_widths) else 0
            draw_text = line_text
            
            # Apply ellipsis truncation if text overflows container
            if instance.text_overflow == 'ELLIPSIS' and container_w > 0 and cur_lw > container_w:
                ellipsis = '...'
                ew, _ = blf.dimensions(instance.font_id, ellipsis)
                avail = container_w - ew
                truncated = ''
                tw = 0
                for ch in line_text:
                    cw, _ = blf.dimensions(instance.font_id, ch)
                    if instance.letter_spacing > 0 and truncated:
                        cw += instance.letter_spacing
                    if tw + cw > avail:
                        break
                    truncated += ch
                    tw += cw
                draw_text = truncated + ellipsis
                cur_lw = tw + ew
            
            line_y = y_pos + line_step * line_idx
            flipped_y = viewport_height - line_y - text_height
            
            # Per-line horizontal alignment for multi-line text
            lx = x_pos
            if len(lines) > 1 and instance.mask and instance.mask[2] > 0:
                if instance.align_h == 'CENTER':
                    lx = instance.mask[0] + (container_w - cur_lw) / 2
                elif instance.align_h == 'RIGHT':
                    lx = instance.mask[0] + container_w - cur_lw
            
            # Enable BLF text shadow if configured
            has_shadow = (instance.text_shadow_color[3] > 0 and
                          (instance.text_shadow_blur > 0 or
                           instance.text_shadow_offset[0] != 0 or
                           instance.text_shadow_offset[1] != 0))
            if has_shadow:
                level = 0
                if instance.text_shadow_blur > 0:
                    level = 3 if instance.text_shadow_blur < 4 else 5
                blf.shadow(instance.font_id, level, *instance.text_shadow_color)
                blf.shadow_offset(instance.font_id, int(instance.text_shadow_offset[0]), int(-instance.text_shadow_offset[1]))
                blf.enable(instance.font_id, blf.SHADOW)

            # Draw: char-by-char for letter_spacing, fast path otherwise
            if instance.letter_spacing > 0 and len(draw_text) > 1:
                cx = lx
                for ch in draw_text:
                    blf.position(instance.font_id, cx, flipped_y, 0)
                    blf.draw(instance.font_id, ch)
                    cw, _ = blf.dimensions(instance.font_id, ch)
                    cx += cw + instance.letter_spacing
            else:
                blf.position(instance.font_id, lx, flipped_y, 0)
                blf.draw(instance.font_id, draw_text)

            if has_shadow:
                blf.disable(instance.font_id, blf.SHADOW)
            
            # Text decoration per line
            decoration = getattr(instance, 'text_decoration', 'NONE')
            if decoration and decoration != 'NONE' and cur_lw > 0:
                _draw_text_decoration(lx, flipped_y, cur_lw, text_height, instance.size, instance.color, decoration)
        
        if use_scissor:
            gpu.state.scissor_test_set(False)
        elif instance.mask and instance.mask[2] > 0 and instance.mask[3] > 0:
            blf.disable(instance.font_id, blf.CLIPPING)

class DrawTextOP(bpy.types.Operator):
    bl_idname = "xwz.draw_text"
    bl_label  = "Add Text Instance"

    container_id: bpy.props.StringProperty(name="Container ID", default="root")
    text        : bpy.props.StringProperty(name="Text", default="New Text")
    font_name   : bpy.props.EnumProperty(
        name    = "Font",
        items   = lambda self, context: [("default", "Default (Blender)", "")] + [(name, name, "") for name in font_manager.get_available_fonts()],
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
    align_h    : bpy.props.EnumProperty(
        name="Horizontal Align",
        items=[('LEFT', 'Left', ''), ('CENTER', 'Center', ''), ('RIGHT', 'Right', '')],
        default='LEFT'
    )
    align_v    : bpy.props.EnumProperty(
        name="Vertical Align",
        items=[('TOP', 'Top', ''), ('CENTER', 'Center', ''), ('BOTTOM', 'Bottom', '')],
        default='CENTER'
    )
    text_decoration : bpy.props.StringProperty(name="Text Decoration", default="NONE")
    letter_spacing  : bpy.props.FloatProperty(name="Letter Spacing", default=0.0)
    line_height     : bpy.props.FloatProperty(name="Line Height", default=0.0)
    font_weight     : bpy.props.StringProperty(name="Font Weight", default="NORMAL")
    font_style      : bpy.props.StringProperty(name="Font Style", default="NORMAL")
    white_space     : bpy.props.StringProperty(name="White Space", default="NORMAL")
    text_overflow   : bpy.props.StringProperty(name="Text Overflow", default="CLIP")
    text_shadow_color    : bpy.props.FloatVectorProperty(name="Text Shadow Color", subtype='COLOR', size=4, default=(0.0, 0.0, 0.0, 0.0))
    text_shadow_offset_x : bpy.props.FloatProperty(name="Text Shadow Offset X", default=0.0)
    text_shadow_offset_y : bpy.props.FloatProperty(name="Text Shadow Offset Y", default=0.0)
    text_shadow_blur     : bpy.props.FloatProperty(name="Text Shadow Blur", default=0.0)
    
    def execute(self, context):
        global _draw_handle, _text_instances
        
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
            mask=mask,
            align_h=self.align_h,
            align_v=self.align_v,
            text_decoration=self.text_decoration,
            letter_spacing=self.letter_spacing,
            line_height=self.line_height,
            font_weight=self.font_weight,
            font_style=self.font_style,
            white_space=self.white_space,
            text_overflow=self.text_overflow,
            text_shadow_color=list(self.text_shadow_color),
            text_shadow_offset_x=self.text_shadow_offset_x,
            text_shadow_offset_y=self.text_shadow_offset_y,
            text_shadow_blur=self.text_shadow_blur
        )
        _text_instances.append(new_instance)
        
        if _draw_handle is None:
            from .space_config import get_space_class
            space_class = get_space_class() or bpy.types.SpaceView3D
            _draw_handle = space_class.draw_handler_add(
                draw_all_text, (), 'WINDOW', 'POST_PIXEL')
        
        context.area.tag_redraw()
        logger.debug(f"Added text instance #{new_instance.id} with font {self.font_name}")
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
                logger.debug(f"Removed text instance #{self.instance_id}")
                break
        else:
            logger.error(f"Text instance #{self.instance_id} not found")
            self.report({'ERROR'}, f"Text instance #{self.instance_id} not found")
            return {'CANCELLED'}
        
        if not _text_instances and _draw_handle is not None:
            from .space_config import get_space_class
            space_class = get_space_class() or bpy.types.SpaceView3D
            space_class.draw_handler_remove(_draw_handle, 'WINDOW')
            _draw_handle = None
        
        context.area.tag_redraw()
        return {'FINISHED'}

class ClearTextOP(bpy.types.Operator):
    bl_idname = "xwz.clear_text"
    bl_label = "Clear All Text"
    
    def execute(self, context):
        global _draw_handle, _text_instances
        
        _text_instances.clear()
        
        if _draw_handle is not None:
            from .space_config import get_space_class
            space_class = get_space_class() or bpy.types.SpaceView3D
            space_class.draw_handler_remove(_draw_handle, 'WINDOW')
            _draw_handle = None
        
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
              [("default", "Default (Blender)", "")] + 
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
    align_h    : bpy.props.EnumProperty(
        name="Horizontal Align",
        items=[('__NOCHANGE__', 'No Change', ''), ('LEFT', 'Left', ''), ('CENTER', 'Center', ''), ('RIGHT', 'Right', '')],
        default='__NOCHANGE__'
    )
    align_v    : bpy.props.EnumProperty(
        name="Vertical Align",
        items=[('__NOCHANGE__', 'No Change', ''), ('TOP', 'Top', ''), ('CENTER', 'Center', ''), ('BOTTOM', 'Bottom', '')],
        default='__NOCHANGE__'
    )
    
    def execute(self, context):
        for instance in _text_instances:
            if instance.id == self.instance_id:
                kwargs = {}
                
                if self.text:
                    kwargs['text'] = self.text
                
                if self.font_name != "__NOCHANGE__" and (self.font_name == "default" or self.font_name in font_manager.get_available_fonts()):
                    kwargs['font_name'] = self.font_name
                
                if self.size != -1:
                    kwargs['size'] = self.size
                
                if self.x_pos != -999999 or self.y_pos != -999999:
                    new_x = self.x_pos if self.x_pos != -999999 else instance.position[0]
                    new_y = self.y_pos if self.y_pos != -999999 else instance.position[1]
                    kwargs['pos'] = [new_x, new_y]
                
                if any(c != -1 for c in self.color):
                    current_color = instance.color
                    new_color = [
                        self.color[0] if self.color[0] != -1 else current_color[0],
                        self.color[1] if self.color[1] != -1 else current_color[1],
                        self.color[2] if self.color[2] != -1 else current_color[2],
                        self.color[3] if self.color[3] != -1 else current_color[3]
                    ]
                    kwargs['color'] = new_color
                
                if (self.mask_x != -999999 or self.mask_y != -999999 or 
                    self.mask_width != -1 or self.mask_height != -1):
                    current_mask = instance.mask or [0, 0, 0, 0]
                    new_mask = [
                        self.mask_x if self.mask_x != -999999 else current_mask[0],
                        self.mask_y if self.mask_y != -999999 else current_mask[1],
                        self.mask_width if self.mask_width != -1 else current_mask[2],
                        self.mask_height if self.mask_height != -1 else current_mask[3]
                    ]
                    kwargs['mask'] = new_mask if new_mask[2] > 0 and new_mask[3] > 0 else None
                
                if self.align_h != '__NOCHANGE__':
                    kwargs['align_h'] = self.align_h
                
                if self.align_v != '__NOCHANGE__':
                    kwargs['align_v'] = self.align_v
                
                if kwargs:
                    instance.update_all(**kwargs)
                    updated_props = list(kwargs.keys())
                    logger.debug(f"Updated text instance #{self.instance_id}: {', '.join(updated_props)}")
                else:
                    logger.debug(f"No properties specified to update for text instance #{self.instance_id}")
                
                return {'FINISHED'}
        
        logger.error(f"Text instance #{self.instance_id} not found")
        self.report({'ERROR'}, f"Text instance #{self.instance_id} not found")
        return {'CANCELLED'}

def register():
    global font_manager
    
    if font_manager is None:
        font_manager = FontManager()
    elif font_manager._initialized:
        font_manager.reload_fonts()
    
    bpy.utils.register_class(DrawTextOP)
    bpy.utils.register_class(RemoveTextOP)
    bpy.utils.register_class(ClearTextOP)
    bpy.utils.register_class(UpdateTextOP)

def unregister():
    global _draw_handle, _text_instances, font_manager
    
    _text_instances.clear()
    
    if _draw_handle is not None:
        from .space_config import get_space_class
        space_class = get_space_class() or bpy.types.SpaceView3D
        space_class.draw_handler_remove(_draw_handle, 'WINDOW')
        _draw_handle = None
    
    FontManager.reset_instance()
    font_manager = None
    
    bpy.utils.unregister_class(DrawTextOP)
    bpy.utils.unregister_class(RemoveTextOP)
    bpy.utils.unregister_class(ClearTextOP)
    bpy.utils.unregister_class(UpdateTextOP)
