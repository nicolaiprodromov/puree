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
from __future__ import annotations
from typing import Optional, List

class Container(): 
    def __init__(self): 
        self.id       : str                       = ""
        self.parent   : Optional[Container]       = []
        self.children : Optional[List[Container]] = []

        self.style : Optional[str] = ""
        self.data  : Optional[str] = ""
        self.img   : Optional[str] = ""
        self.text  : Optional[str] = ""
        self.font  : Optional[str] = ""

        self.layer   : int   = 0
        self.passive : bool  = False

        self.click         : List  = []
        self.toggle        : List  = []
        self.scroll        : List  = []
        self.hover         : List  = []
        self.hoverout      : List  = []
        
        self._toggle_value : bool  = False
        self._toggled      : bool  = False
        self._clicked      : bool  = False
        self._hovered      : bool  = False
        self._prev_toggled : bool  = False
        self._prev_clicked : bool  = False
        self._prev_hovered : bool  = False
        self._scroll_value : float = 0.0
        
        self._dirty        : bool  = False
        self._layout_node  : Optional[object] = None
    
    def __getattr__(self, name):
        if name in ('children', 'style', '__dict__'):
            raise AttributeError(f"'Container' object has no attribute '{name}'")
        
        try:
            children = object.__getattribute__(self, 'children')
            for child in children:
                if child.id == name or child.id.endswith(f"_{name}"):
                    return child
        except AttributeError:
            pass
        
        try:
            style = object.__getattribute__(self, 'style')
            if style and hasattr(style, name):
                return getattr(style, name)
        except AttributeError:
            pass
        
        raise AttributeError(f"'Container' object has no attribute or child named '{name}'")
    
    def __setattr__(self, name, value):
        container_attrs = {
            'id', 'parent', 'children', 'style', 'data', 'img', 'text', 'font',
            'layer', 'passive', 'click', 'toggle', 'scroll', 'hover', 'hoverout',
            '_toggle_value', '_toggled', '_clicked', '_hovered',
            '_prev_toggled', '_prev_clicked', '_prev_hovered', '_scroll_value', '_dirty', '_layout_node'
        }
        
        if name in container_attrs:
            object.__setattr__(self, name, value)
        else:
            try:
                style = object.__getattribute__(self, 'style')
                if style and hasattr(style, name):
                    setattr(style, name, value)
                else:
                    object.__setattr__(self, name, value)
            except AttributeError:
                object.__setattr__(self, name, value)
    
    def mark_dirty(self):
        self._dirty = True
    
    @staticmethod
    def is_layout_property(name):
        layout_properties = {
            'width', 'height', 'display', 'position', 'overflow', 'scrollbar_width',
            'padding', 'padding_top', 'padding_right', 'padding_bottom', 'padding_left',
            'margin', 'margin_top', 'margin_right', 'margin_bottom', 'margin_left',
            'border', 'border_width',
            'align_items', 'justify_items', 'align_self', 'justify_self',
            'align_content', 'justify_content',
            'size', 'min_size', 'max_size', 'aspect_ratio',
            'flex_wrap', 'flex_direction', 'flex_grow', 'flex_shrink', 'flex_basis',
            'grid_auto_flow', 'grid_template_rows', 'grid_template_columns',
            'grid_auto_rows', 'grid_auto_columns', 'grid_row', 'grid_column',
            'gap'
        }
        return name in layout_properties
    
    def set_property(self, name, value):
        if self.is_layout_property(name):
            self.mark_dirty()
            if self._layout_node is not None:
                from stretchable import Style
                from stretchable.style import PCT, PT
                from stretchable.style.geometry.length import LengthPointsPercentAuto
                from stretchable.style.geometry.size import SizePointsPercentAuto
                
                current_style = self._layout_node.style
                new_style_dict = {}
                
                for attr in ['display', 'overflow_x', 'overflow_y', 'position', 'align_items', 
                            'justify_items', 'align_self', 'justify_self', 'align_content', 
                            'justify_content', 'gap', 'padding', 'border', 'margin', 'size',
                            'min_size', 'max_size', 'aspect_ratio', 'flex_wrap', 'flex_direction',
                            'flex_grow', 'flex_shrink', 'flex_basis']:
                    if hasattr(current_style, attr):
                        new_style_dict[attr] = getattr(current_style, attr)
                
                if name == 'width' or name == 'height':
                    value_str = str(value).lower()
                    if 'px' in value_str:
                        length_val = LengthPointsPercentAuto.from_any(int(value_str.replace('px', '')) * PT)
                    elif '%' in value_str:
                        length_val = LengthPointsPercentAuto.from_any(int(value_str.replace('%', '')) * PCT)
                    else:
                        length_val = LengthPointsPercentAuto.from_any(0 * PT)
                    
                    current_size = new_style_dict.get('size')
                    if name == 'width':
                        new_style_dict['size'] = SizePointsPercentAuto(width=length_val, height=current_size.height if current_size else LengthPointsPercentAuto.from_any(0 * PT))
                    else:
                        new_style_dict['size'] = SizePointsPercentAuto(width=current_size.width if current_size else LengthPointsPercentAuto.from_any(0 * PT), height=length_val)
                
                elif name in ['margin_top', 'margin_right', 'margin_bottom', 'margin_left']:
                    from stretchable.style.geometry.rect import RectPointsPercentAuto
                    
                    value_str = str(value).lower()
                    if 'px' in value_str:
                        length_val = LengthPointsPercentAuto.from_any(int(value_str.replace('px', '')) * PT)
                    elif '%' in value_str:
                        length_val = LengthPointsPercentAuto.from_any(int(value_str.replace('%', '')) * PCT)
                    else:
                        length_val = LengthPointsPercentAuto.from_any(0 * PT)
                    
                    current_margin = new_style_dict.get('margin')
                    if current_margin:
                        top = current_margin.top if hasattr(current_margin, 'top') else LengthPointsPercentAuto.from_any(0 * PT)
                        right = current_margin.right if hasattr(current_margin, 'right') else LengthPointsPercentAuto.from_any(0 * PT)
                        bottom = current_margin.bottom if hasattr(current_margin, 'bottom') else LengthPointsPercentAuto.from_any(0 * PT)
                        left = current_margin.left if hasattr(current_margin, 'left') else LengthPointsPercentAuto.from_any(0 * PT)
                    else:
                        top = right = bottom = left = LengthPointsPercentAuto.from_any(0 * PT)
                    
                    if name == 'margin_top':
                        top = length_val
                    elif name == 'margin_right':
                        right = length_val
                    elif name == 'margin_bottom':
                        bottom = length_val
                    elif name == 'margin_left':
                        left = length_val
                    
                    new_style_dict['margin'] = RectPointsPercentAuto(top=top, right=right, bottom=bottom, left=left)
                
                self._layout_node.style = Style(**new_style_dict)
                self._layout_node.mark_dirty()
        
        setattr(self, name, value)
    
    def get_by_id(self, target_id):
        if self.id == target_id or self.id.endswith(f"_{target_id}"):
            return self
        if self.children:
            for child in self.children:
                result = child.get_by_id(target_id)
                if result:
                    return result
        return None

class ContainerDefault():
    def __init__(self): 
        self.id    = None
        self.style = None

        self.parent   = None
        self.children = []

        self.click         = []
        self.toggle        = []
        self.scroll        = []
        self.hover         = []
        self.hoverout      = []
        self._toggle_value = False
        self._toggled      = False
        self._clicked      = False
        self._hovered      = False
        self._prev_toggled = False
        self._prev_clicked = False
        self._prev_hovered = False
        self._scroll_value = 0.0

        self.display      = True
        self.overflow     = False
        self.data         = ""
        self.img          = ""
        self.aspect_ratio = False
        self.text         = ""
        self.font         = 'default'

        self.layer   = 0
        self.passive = False

        self.x = 0.0
        self.y = 0.0

        self.width  = 100.0
        self.height = 100.0

        self.color              = [0.0, 0.0, 0.0, 1.0]
        self.color_1            = [0.0, 0.0, 0.0, 0.0]
        self.color_gradient_rot = 0.0
        
        self.hover_color              = [0.0, 0.0, 0.0, -1.0]
        self.hover_color_1            = [0.0, 0.0, 0.0, 0.0]
        self.hover_color_gradient_rot = 0.0

        self.click_color              = [0.0, 0.0, 0.0, -1.0]
        self.click_color_1            = [0.0, 0.0, 0.0, 0.0]
        self.click_color_gradient_rot = 0.0

        self.toggle_color              = [0.0, 0.0, 0.0, -1.0]
        self.toggle_color_1            = [0.0, 0.0, 0.0, 0.0]
        self.toggle_color_gradient_rot = 0.0

        self.border_color              = [0.0, 0.0, 0.0, 0.0]
        self.border_color_1            = [0.0, 0.0, 0.0, 0.0]
        self.border_color_gradient_rot = 0.0
        self.border_radius             = 0.0
        self.border_width              = 0.0
        
        self.text_color              = [1.0, 1.0, 1.0, 1.0]
        self.text_color_1            = [0.0, 0.0, 0.0, 0.0]
        self.text_color_gradient_rot = 0.0
        self.text_scale              = 12.0
        self.text_x                  = 0.0
        self.text_y                  = 0.0
        
        self.box_shadow_color  = [0.0, 0.0, 0.0, 0.0]
        self.box_shadow_offset = [0.0, 0.0, 0.0]
        self.box_shadow_blur   = 0.0
        
container_default = ContainerDefault()