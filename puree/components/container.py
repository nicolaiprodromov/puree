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
import math as _math


def _parse_css_angle(s):
    """Parse a CSS angle string to degrees."""
    s = s.strip().lower()
    if s.endswith('deg'):
        return float(s[:-3])
    if s.endswith('rad'):
        return _math.degrees(float(s[:-3]))
    if s.endswith('turn'):
        return float(s[:-4]) * 360.0
    return {
        'to top': 0.0, 'to right': 90.0, 'to bottom': 180.0, 'to left': 270.0,
        'to top right': 45.0, 'to right top': 45.0,
        'to bottom right': 135.0, 'to right bottom': 135.0,
        'to bottom left': 225.0, 'to left bottom': 225.0,
        'to top left': 315.0, 'to left top': 315.0,
    }.get(s, 180.0)


def _split_css_args(s):
    """Split string by comma, respecting parentheses depth."""
    args, depth, buf = [], 0, []
    for ch in s:
        if ch == '(':
            depth += 1
            buf.append(ch)
        elif ch == ')':
            depth -= 1
            buf.append(ch)
        elif ch == ',' and depth == 0:
            args.append(''.join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if buf:
        args.append(''.join(buf).strip())
    return args


def _apply_linear_gradient(style, value_str):
    """Parse linear-gradient() and set style fields. Returns True on success."""
    value_str = value_str.strip()
    if not (value_str.startswith('linear-gradient(') and value_str.endswith(')')):
        return False
    inner = value_str[16:-1]
    args = _split_css_args(inner)
    if len(args) < 2:
        return False

    # Determine angle
    first = args[0].strip().lower()
    angle = 180.0
    color_start = 0
    if (first.endswith('deg') or first.endswith('rad') or first.endswith('turn')
            or first.startswith('to ')):
        angle = _parse_css_angle(first)
        color_start = 1

    color_args = args[color_start:]
    if len(color_args) < 2:
        return False

    from ..native_bindings import ColorProcessor
    cp = ColorProcessor()

    def parse_stop(stop_str):
        stop_str = stop_str.strip()
        pos = None
        last_paren = stop_str.rfind(')')
        if last_paren >= 0:
            # Color is a CSS function (rgba, hsl, etc.) — everything up to and
            # including ')' is the color; anything after is an optional position.
            color_str = stop_str[:last_paren + 1]
            trailing = stop_str[last_paren + 1:].strip()
            if trailing.endswith('%'):
                try:
                    pos = float(trailing[:-1]) / 100.0
                except ValueError:
                    pass
        else:
            # Simple keyword or hex, optionally followed by "50%" position.
            parts = stop_str.rsplit(None, 1)
            color_str = parts[0].strip()
            if len(parts) == 2:
                p = parts[1].strip()
                if p.endswith('%'):
                    try:
                        pos = float(p[:-1]) / 100.0
                    except ValueError:
                        pass
        try:
            rgba = cp.parse_color(color_str)
        except Exception:
            rgba = [0.0, 0.0, 0.0, 1.0]
        return rgba, pos

    stops = [parse_stop(s) for s in color_args]

    if len(stops) == 2:
        style.background_color = stops[0][0]
        style.background_color_2 = stops[1][0]
        style.background_gradient_rot = angle
        style.gradient_stops = ''
    else:
        # Distribute auto positions
        n = len(stops)
        for i, (rgba, pos) in enumerate(stops):
            if pos is None:
                stops[i] = (rgba, float(i) / max(n - 1, 1))
        parts_str = str(angle)
        for rgba, pos in stops:
            parts_str += ' {} {} {} {} {}'.format(
                rgba[0], rgba[1], rgba[2], rgba[3], pos)
        style.gradient_stops = parts_str
        style.background_color = stops[0][0]
        style.background_color_2 = stops[1][0]
        style.background_gradient_rot = angle
    return True

class Container(): 
    def __init__(self): 
        self.id       : str                       = ""
        self.parent   : Optional[Container]       = []
        self.children : Optional[List[Container]] = []

        self.style   : Optional['Style'] = None
        self.classes : List[str]     = []
        self.data    : Optional[str] = ""
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
        self.on_focus      : List  = []
        self.on_blur       : List  = []
        self.tab_index     : int   = -1
        self.focusable     : bool  = False
        
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
            'on_focus', 'on_blur', 'tab_index', 'focusable',
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

    # -------------------------------------------------------------------------
    # Dynamic container creation / destruction (Feature 2)
    # -------------------------------------------------------------------------

    def add_child(self, template: str, id: str = None, params: dict = None) -> 'Container':
        """Create a new child container from a component template and append it."""
        from ..dynamic import dynamic_manager
        return dynamic_manager.add_child(self, template, child_id=id, params=params)

    def insert_child(self, index: int, template: str, id: str = None, params: dict = None) -> 'Container':
        """Create a new child container from a component template and insert it at *index*."""
        from ..dynamic import dynamic_manager
        return dynamic_manager.insert_child(self, index, template, child_id=id, params=params)

    def remove_child(self, id_or_container) -> bool:
        """Remove a child container by ID string or Container reference."""
        from ..dynamic import dynamic_manager
        return dynamic_manager.remove_child(self, id_or_container)

    def clear_children(self) -> None:
        """Remove all children from this container."""
        from ..dynamic import dynamic_manager
        dynamic_manager.clear_children(self)

    def focus(self) -> None:
        from ..focus import focus_manager
        focus_manager.focus(self.id, self.on_focus, self.on_blur, container_ref=self)

    def blur(self) -> None:
        from ..focus import focus_manager
        focus_manager.blur(self.id)

    @property
    def is_focused(self) -> bool:
        from ..focus import focus_manager
        return focus_manager.is_focused(self.id)

    @property
    def keys(self):
        """Returns a ContainerKeyProxy for scoping keyboard shortcuts to this container."""
        from ..keyboard import ContainerKeyProxy
        return ContainerKeyProxy(self.id)
    
    @staticmethod
    def is_layout_property(name):
        layout_properties = {
            'width', 'height', 'min_width', 'min_height', 'max_width', 'max_height',
            'display', 'position', 'overflow', 'scrollbar_width',
            'top', 'right', 'bottom', 'left',
            'padding', 'padding_top', 'padding_right', 'padding_bottom', 'padding_left',
            'margin', 'margin_top', 'margin_right', 'margin_bottom', 'margin_left',
            'border', 'border_width',
            'align_items', 'justify_items', 'align_self', 'justify_self',
            'align_content', 'justify_content',
            'size', 'min_size', 'max_size', 'aspect_ratio',
            'flex_wrap', 'flex_direction', 'flex_grow', 'flex_shrink', 'flex_basis',
            'gap', 'row_gap', 'column_gap',
            'grid_auto_flow', 'grid_template_rows', 'grid_template_columns',
            'grid_auto_rows', 'grid_auto_columns', 'grid_row', 'grid_column',
        }
        return name in layout_properties
    
    def set_property(self, name, value):
        # Strip -- prefix from custom properties (Puree extensions)
        if name.startswith('--'):
            name = name[2:]
        
        name = name.replace('-', '_')

        if self.is_layout_property(name):
            self.mark_dirty()
            if self._layout_node is not None:
                from stretchable import Style
                from stretchable.style import PCT, PT
                from stretchable.style.geometry.length import LengthPointsPercentAuto
                from stretchable.style.geometry.size import SizePointsPercentAuto
                
                current_style = self._layout_node.style
                new_style_dict = {}
                
                for attr in ['display', 'overflow_x', 'overflow_y', 'position', 'inset',
                            'align_items', 'justify_items', 'align_self', 'justify_self', 
                            'align_content', 'justify_content', 'gap', 'padding', 'border', 
                            'margin', 'size', 'min_size', 'max_size', 'aspect_ratio', 
                            'flex_wrap', 'flex_direction', 'flex_grow', 'flex_shrink', 
                            'flex_basis', 'scrollbar_width',
                            'grid_auto_flow', 'grid_template_rows', 'grid_template_columns',
                            'grid_auto_rows', 'grid_auto_columns', 'grid_row', 'grid_column']:
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
        
        # Style properties go to self.style with type conversion

        # Handle background/background-color with linear-gradient() value
        if name in ('background', 'background_color') and 'linear-gradient' in str(value) and self.style is not None:
            if _apply_linear_gradient(self.style, str(value)):
                self.mark_dirty()
                return

        # Handle background/background-color with a plain solid color
        if name == 'background' and 'linear-gradient' not in str(value) and self.style is not None:
            name = 'background_color'

        color_props = {'background_color', 'background_color_2',
                       'hover_background_color', 'hover_background_color_2',
                       'click_background_color', 'click_background_color_2',
                       'border_color', 'border_color_2',
                       'color', 'box_shadow_color'}
        if name in color_props and isinstance(value, str) and self.style is not None:
            from ..native_bindings import ColorProcessor
            cp = ColorProcessor()
            try:
                parsed = cp.parse_color(value)
                setattr(self.style, name, parsed)
            except Exception:
                setattr(self.style, name, value)
            self.mark_dirty()
            return
        
        if self.style is not None and hasattr(self.style, name):
            setattr(self.style, name, value)
            self.mark_dirty()
        else:
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
        self.on_focus      = []
        self.on_blur       = []
        self.tab_index     = -1
        self.focusable     = False
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

        self.background_color              = [0.0, 0.0, 0.0, 0.0]
        self.background_color_2            = [0.0, 0.0, 0.0, 0.0]
        self.background_gradient_rot       = 0.0
        
        self.hover_background_color              = [0.0, 0.0, 0.0, -1.0]
        self.hover_background_color_2            = [0.0, 0.0, 0.0, 0.0]
        self.hover_background_gradient_rot       = 0.0

        self.click_background_color              = [0.0, 0.0, 0.0, -1.0]
        self.click_background_color_2            = [0.0, 0.0, 0.0, 0.0]
        self.click_background_gradient_rot       = 0.0

        self.toggle_background_color              = [0.0, 0.0, 0.0, -1.0]
        self.toggle_background_color_2            = [0.0, 0.0, 0.0, 0.0]
        self.toggle_background_gradient_rot       = 0.0

        self.border_color              = [0.0, 0.0, 0.0, 0.0]
        self.border_color_2            = [0.0, 0.0, 0.0, 0.0]
        self.border_gradient_rot       = 0.0
        self.border_radius             = 0.0
        self.border_width              = 0.0
        
        self.color                     = [1.0, 1.0, 1.0, 1.0]
        self.font_size                 = 12.0
        self.text_x                    = 0.0
        self.text_y                    = 0.0
        
        self.box_shadow_color  = [0.0, 0.0, 0.0, 0.0]
        self.box_shadow_offset = [0.0, 0.0, 0.0]
        self.box_shadow_blur   = 0.0
        
container_default = ContainerDefault()