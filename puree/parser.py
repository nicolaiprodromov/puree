import toml
import os
from stretchable import Node
from stretchable.style import PCT, AUTO, PT
from stretchable import Edge
from stretchable.style.props import BoxSizing
from stretchable.style.props import FlexDirection
from stretchable.style.props import AlignItems, JustifyContent
from stretchable.style.props import Display, Position
from stretchable.style.geometry.rect import RectPointsPercent
from stretchable.style.geometry.length import LengthPointsPercent
from tinycss2 import ast
from tinycss2 import parse_stylesheet, parse_declaration_list
from textual.color import Color
import math

from .components.container import Container
from .components.style import Style

node_flat = {}
node_flat_abs = {}

def srgb_to_linear(value):
    """
    Convert sRGB color value (0-1 range) to linear color space.
    This is the standard sRGB to linear conversion formula used by Blender.
    
    Blender's rendering pipeline works in linear color space for physically accurate lighting,
    but UI color pickers and CSS colors are in sRGB space (what humans perceive as uniform).
    
    References:
    - https://en.wikipedia.org/wiki/SRGB#Transformation
    - Blender API: bpy.types.ColorManagedInputColorspaceSettings
    """
    if value <= 0.04045:
        return value / 12.92
    else:
        return math.pow((value + 0.055) / 1.055, 2.4)

def convert_srgb_to_linear_color(r, g, b, a):
    """
    Convert RGBA color from sRGB to linear color space.
    Alpha channel is not converted as it's not affected by gamma.
    """
    return [
        srgb_to_linear(r),
        srgb_to_linear(g),
        srgb_to_linear(b),
        a  # Alpha is linear already
    ]

class CSSParser:
    def __init__(self):
        self.styles = {}
        self.variables = {}
    
    def _extract_variables(self, styles):
        variables = {}
        for selector, declarations in styles.items():
            for prop, value in declarations.items():
                if prop.startswith('--'):
                    variables[prop] = value
        return variables
    
    def _resolve_variables(self, value, variables, visited=None):
        import re
        if visited is None:
            visited = set()
        
        var_pattern = r'var\(([^)]+)\)'
        
        def replace_var(match):
            var_name = match.group(1).strip()
            if var_name in visited:
                return match.group(0)
            if var_name in variables:
                visited.add(var_name)
                resolved_value = variables[var_name]
                result = self._resolve_variables(resolved_value, variables, visited.copy())
                return result
            return match.group(0)
        
        return re.sub(var_pattern, replace_var, value)
    
    def parse(self, css_string):
        self.styles = {}
        rules = parse_stylesheet(css_string)
        
        for rule in rules:
            if hasattr(rule, 'content'):
                selector = ''.join(token.serialize() for token in rule.prelude).strip()
                declarations = {}
                
                content_str = ''.join(token.serialize() for token in rule.content)
                decl_list = parse_declaration_list(content_str)
                
                for decl in decl_list:
                    if isinstance(decl, ast.Declaration):
                        value = ''.join(token.serialize() for token in decl.value).strip()
                        declarations[decl.name] = value
                
                self.styles[selector] = declarations
        
        self.variables = self._extract_variables(self.styles)
        
        for selector, declarations in self.styles.items():
            for prop, value in declarations.items():
                if not prop.startswith('--'):
                    self.styles[selector][prop] = self._resolve_variables(value, self.variables)
        
        return self.styles

class Settings():
    def __init__(self):
        self.scroll_speed = 0

class Styles():
    def __init__(self):
        pass

class Theme():
    def __init__(self):
        self.name        = ""
        self.author      = ""
        self.version     = ""
        self.scripts     = []
        self.style_files = []
        self.palette     = {}
        self.styles      = Styles()
        self.root        = Container()
        
class UI():
    def __init__(self, path=None, canvas_size=(800, 600)):
        self.selected_theme = "xwz_default"
        self.settings       = Settings()
        self.theme          = Theme()
        self.json_data      = []
        self.abs_json_data  = []
        self.root_node      = None  # Expose root node for recomputation
        self.canvas_size    = canvas_size  # Store current canvas size

        self.parse_toml(path)
        self.parse_css()
        self.create_node_tree(canvas_size)
        self.flatten_node_tree()

    def load_conf_file(self, path):
        with open(path, 'r') as f:
            data = toml.load(f)
        return data
    
    def parse_toml(self, path=None):
        data     = self.load_conf_file(path)
        ui_data  = data.get('app', {})
        settings = ui_data['settings']
        theme    = ui_data['theme']

        self.selected_theme        = ui_data['selected_theme']
        self.default_theme         = ui_data['default_theme']
        # self.settings.scroll_speed = settings['scroll_speed']

        self.theme_index = -1
        for _theme_ in theme:
            if _theme_['name'] == self.selected_theme:
                self.theme_index = theme.index(_theme_)
                break
        if self.theme_index == -1:
            for _theme_ in theme:
                if _theme_['name'] == self.default_theme:
                    self.theme_index = theme.index(_theme_)
                    break
        if self.theme_index == -1:
            self.theme_index   = 0
            self.default_theme = theme[0]['name']

        root = ui_data['theme'][self.theme_index]['root']

        self.theme.name        = theme[self.theme_index]['name']
        self.theme.author      = theme[self.theme_index]['author']
        self.theme.version     = theme[self.theme_index]['version']
        self.theme.scripts     = theme[self.theme_index]['scripts']
        self.theme.style_files = theme[self.theme_index]['styles']

        def load_container(container_data, parent_container):
            for attr_name, attr_value in container_data.items():
                if isinstance(attr_value, dict):
                    child_container = Container()
                    child_container.id = attr_name
                    child_container.parent = parent_container
                    parent_container.children.append(child_container)
                    
                    for child_attr_name, child_attr_value in attr_value.items():
                        if not isinstance(child_attr_value, dict):
                            if hasattr(child_container, child_attr_name):
                                setattr(child_container, child_attr_name.replace('-', '_'), child_attr_value)
                    
                    load_container(attr_value, child_container)
                else:
                    if hasattr(parent_container, attr_name):
                        setattr(parent_container, attr_name.replace('-', '_'), attr_value)

        self.theme.root.id = "root"
        load_container(root, self.theme.root)
        #print(self.theme.root.children[0].id)

    def parse_container_props_from_style(self, attr_name, attr_value):
        attr_name = attr_name.replace('-', '_')

        if attr_name.startswith('__'):
                    attr_name = attr_name[1:]

        attr_name = attr_name.replace('background_color', 'color')

        color_props = [
            'color', 'color_1',
            'hover_color', 'hover_color_1',
            'click_color', 'click_color_1',
            'border_color', 'border_color_1',
            'text_color', 'text_color_1',
            'box_shadow_color'
            ]
        
        float_props = [
            'border_radius', 'border_width',
            'text_scale', 'text_x', 'text_y',
            'box_shadow_blur'
            ]

        rotation_props = [
            'color_gradient_rot',
            'hover_color_gradient_rot',
            'click_color_gradient_rot',
            'border_color_gradient_rot',
            'text_color_gradient_rot'
            ]

        if attr_name in color_props:
            value_color = Color.parse(attr_value)
            # Convert from sRGB (0-255) to linear color space (0-1)
            # First normalize to 0-1, then convert to linear space
            srgb_normalized = [value_color.r / 255.0, value_color.g / 255.0, value_color.b / 255.0, value_color.a]
            attr_value = convert_srgb_to_linear_color(*srgb_normalized)

        elif attr_name in float_props:
            attr_value = float(attr_value.replace('px', '').strip())

        elif attr_name in rotation_props:
            attr_value = float(attr_value.replace('deg', '').strip())

        return attr_name, attr_value

    def parse_css(self):

        addon_dir  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        style_str = ""
        for _style_file in self.theme.style_files:
            if _style_file.endswith('.css'):
                with open(os.path.join(addon_dir, _style_file), 'r') as f:
                    style_str += f.read()

        css_string = style_str

        parser = CSSParser()
        styles = parser.parse(css_string)
        
        for selector, declarations in styles.items():
            style_obj = Style()
            style_obj.id = selector
            for prop, value in declarations.items():
                attr_name, attr_value = self.parse_container_props_from_style(prop, value)
                setattr(style_obj, attr_name, attr_value)
            self.theme.styles.__dict__[selector] = style_obj
        def apply_styles_to_containers(container):
            if hasattr(container, 'style') and container.style:
                style_name = container.style
                if isinstance(style_name, str):
                    if hasattr(self.theme.styles, style_name):
                        container.style = getattr(self.theme.styles, style_name)
                    else:
                        print(f"Warning: Style '{style_name}' not found, using default")
                        default_style = Style()
                        setattr(default_style, 'width', "100%")
                        setattr(default_style, 'height', "100%")
                        container.style = default_style
            for child in container.children:
                apply_styles_to_containers(child)
        apply_styles_to_containers(self.theme.root)

    def create_node_tree(self, canvas_size=(800, 600)):
        def get_all_nodes(container, node):
            border_box     = node.get_box(Edge.BORDER, relative=True)
            border_box_abs = node.get_box(Edge.BORDER, relative=False)
            content_box    = node.get_box(Edge.CONTENT, relative=True)
            content_box_abs = node.get_box(Edge.CONTENT, relative=False)
            padding_box    = node.get_box(Edge.PADDING, relative=True)
            margin_box     = node.get_box(Edge.MARGIN, relative=True)
            margin_box_abs = node.get_box(Edge.MARGIN, relative=False)
            
            edge_used, edge_used_abs = border_box, border_box_abs

            node_flat[container.id] = {
                'x'      : edge_used.x,
                'y'      : edge_used.y,
                'width'  : edge_used.width,
                'height' : edge_used.height
            }

            node_flat_abs[container.id] = {
                'x'      : edge_used_abs.x,
                'y'      : edge_used_abs.y,
                'width'  : edge_used_abs.width,
                'height' : edge_used_abs.height
            }
            
            for i, _container in enumerate(container.children):
                get_all_nodes(_container, node[i])

            return
        def parse_css_value(value_str):
            value_str = str(value_str).lower()
            if 'px' in value_str and 'calc(' not in value_str:
                return LengthPointsPercent.from_any(int(value_str.replace('px', '')) * PT)
            if '%' in value_str and 'calc(' not in value_str:
                return LengthPointsPercent.from_any(int(value_str.replace('%', '')) * PCT)
            if 'auto' in value_str and 'calc(' not in value_str:
                return AUTO
            return LengthPointsPercent.from_any(0 * PT)
        def parse_padding_values(container):
            top = right = bottom = left = LengthPointsPercent.from_any(0 * PT)
            if hasattr(container.style, 'padding_top'):
                top = parse_css_value(container.style.padding_top)
            if hasattr(container.style, 'padding_right'):
                right = parse_css_value(container.style.padding_right)
            if hasattr(container.style, 'padding_bottom'):
                bottom = parse_css_value(container.style.padding_bottom)
            if hasattr(container.style, 'padding_left'):
                left = parse_css_value(container.style.padding_left)
            if hasattr(container.style, 'padding') and isinstance(container.style.padding, str):
                padding_str = container.style.padding.lower()
                if 'calc(' not in padding_str:
                    values = padding_str.split()
                    if len(values) == 1:
                        val = parse_css_value(values[0])
                        top = right = bottom = left = val
                    elif len(values) == 2:
                        vertical   = parse_css_value(values[0])
                        horizontal = parse_css_value(values[1])
                        top        = bottom = vertical
                        right      = left   = horizontal
                    elif len(values) == 3:
                        top        = parse_css_value(values[0])
                        horizontal = parse_css_value(values[1])
                        bottom     = parse_css_value(values[2])
                        right      = left = horizontal
                    elif len(values) == 4:
                        top    = parse_css_value(values[0])
                        right  = parse_css_value(values[1])
                        bottom = parse_css_value(values[2])
                        left   = parse_css_value(values[3])
            return RectPointsPercent.from_any([top, right, bottom, left])
        def parse_margin_values(container):
            top = right = bottom = left = LengthPointsPercent.from_any(0 * PT)
            if hasattr(container.style, 'margin_top'):
                top = parse_css_value(container.style.margin_top)
            if hasattr(container.style, 'margin_right'):
                right = parse_css_value(container.style.margin_right)
            if hasattr(container.style, 'margin_bottom'):
                bottom = parse_css_value(container.style.margin_bottom)
            if hasattr(container.style, 'margin_left'):
                left = parse_css_value(container.style.margin_left)
            if hasattr(container.style, 'margin') and isinstance(container.style.margin, str):
                margin_str = container.style.margin.lower()
                if 'calc(' not in margin_str:
                    values = margin_str.split()
                    
                    if len(values) == 1:
                        val = parse_css_value(values[0])
                        top = right = bottom = left = val
                    elif len(values) == 2:
                        vertical = parse_css_value(values[0])
                        horizontal = parse_css_value(values[1])
                        top = bottom = vertical
                        right = left = horizontal
                    elif len(values) == 3:
                        top = parse_css_value(values[0])
                        horizontal = parse_css_value(values[1])
                        bottom = parse_css_value(values[2])
                        right = left = horizontal
                    elif len(values) == 4:
                        top = parse_css_value(values[0])
                        right = parse_css_value(values[1])
                        bottom = parse_css_value(values[2])
                        left = parse_css_value(values[3])
            return RectPointsPercent.from_any([top, right, bottom, left])
        def parse_border_values(container):
            width_top = width_right = width_bottom = width_left = LengthPointsPercent.from_any(0 * PT)
            
            if hasattr(container.style, 'border_width') and isinstance(container.style.border_width, str):
                border_width_str = container.style.border_width.lower()
                if 'calc(' not in border_width_str:
                    values = border_width_str.split()
                    
                    if len(values) == 1:
                        val = parse_css_value(values[0])
                        width_top = width_right = width_bottom = width_left = val
                    elif len(values) == 2:
                        vertical = parse_css_value(values[0])
                        horizontal = parse_css_value(values[1])
                        width_top = width_bottom = vertical
                        width_right = width_left = horizontal
                    elif len(values) == 3:
                        width_top = parse_css_value(values[0])
                        horizontal = parse_css_value(values[1])
                        width_bottom = parse_css_value(values[2])
                        width_right = width_left = horizontal
                    elif len(values) == 4:
                        width_top = parse_css_value(values[0])
                        width_right = parse_css_value(values[1])
                        width_bottom = parse_css_value(values[2])
                        width_left = parse_css_value(values[3])
            
            if hasattr(container.style, 'border') and isinstance(container.style.border, str):
                border_str = container.style.border.lower()
                if 'calc(' not in border_str:
                    parts = border_str.split()
                    for part in parts:
                        if 'px' in part or '%' in part:
                            val = parse_css_value(part)
                            width_top = width_right = width_bottom = width_left = val
                        elif part.startswith('#') or part in ['red', 'blue', 'green', 'black', 'white', 'transparent']:
                            setattr(container.style, 'border_color_css', part)
            
            if hasattr(container.style, 'border_color') and isinstance(container.style.border_color, str):
                setattr(container.style, 'border_color_css', container.style.border_color.lower())
                        
            return RectPointsPercent.from_any([width_top, width_right, width_bottom, width_left])
        def create_node(container):
            disp_str     = container.style.display.lower()
            pos_str      = container.style.position.lower()
            position_val = Position.RELATIVE
            display_val  = Display.FLEX

            width_val    = container.style.width
            height_val   = container.style.height
            width_pct    = 0
            height_pct   = 0
            
            flex_dir_str        = container.style.flex_direction.lower().replace('-', '_')
            align_str           = container.style.align_items.lower().replace('-', '_')
            justify_str         = container.style.justify_content.lower().replace('-', '_')
            flex_direction_val  = FlexDirection.ROW
            align_items_val     = AlignItems.START
            justify_content_val = JustifyContent.START

            width_pct  = parse_css_value(width_val)
            height_pct = parse_css_value(height_val)

            padding_val = parse_padding_values(container)
            margin_val  = parse_margin_values(container)
            border_val  = parse_border_values(container)

            if pos_str in ['absolute', 'fixed']:
                position_val = Position.ABSOLUTE
            elif pos_str in ['relative', 'static']:
                position_val = Position.RELATIVE

            if disp_str == 'none':
                display_val = Display.NONE
            elif disp_str == 'flex':
                display_val = Display.FLEX
            elif disp_str == 'grid':
                display_val = Display.GRID
            elif disp_str == 'block':
                display_val = Display.BLOCK

            if flex_dir_str == 'row':
                flex_direction_val = FlexDirection.ROW
            elif flex_dir_str == 'column':
                flex_direction_val = FlexDirection.COLUMN
            elif flex_dir_str == 'row_reverse':
                flex_direction_val = FlexDirection.ROW_REVERSE
            elif flex_dir_str == 'column_reverse':
                flex_direction_val = FlexDirection.COLUMN_REVERSE

            if align_str == 'start':
                align_items_val = AlignItems.START
            elif align_str == 'end':
                align_items_val = AlignItems.END
            elif align_str == 'flex_start':
                align_items_val = AlignItems.FLEX_START
            elif align_str == 'flex_end':
                align_items_val = AlignItems.FLEX_END
            elif align_str == 'center':
                align_items_val = AlignItems.CENTER
            elif align_str == 'baseline':
                align_items_val = AlignItems.BASELINE
            elif align_str == 'stretch':
                align_items_val = AlignItems.STRETCH

            if justify_str == 'start':
                justify_content_val = JustifyContent.START
            elif justify_str == 'end':
                justify_content_val = JustifyContent.END
            elif justify_str == 'flex_start':
                justify_content_val = JustifyContent.FLEX_START
            elif justify_str == 'flex_end':
                justify_content_val = JustifyContent.FLEX_END
            elif justify_str == 'center':
                justify_content_val = JustifyContent.CENTER
            elif justify_str == 'stretch':
                justify_content_val = JustifyContent.STRETCH
            elif justify_str == 'space_between':
                justify_content_val = JustifyContent.SPACE_BETWEEN
            elif justify_str == 'space_evenly':
                justify_content_val = JustifyContent.SPACE_EVENLY
            elif justify_str == 'space_around':
                justify_content_val = JustifyContent.SPACE_AROUND

            node = Node(
                display         = display_val,
                position        = position_val,
                box_sizing      = BoxSizing.BORDER,
                flex_direction  = flex_direction_val,
                align_items     = align_items_val,
                justify_content = justify_content_val,
                key             = container.id,
                size            = (width_pct, height_pct),
                padding         = padding_val,
                margin          = margin_val,
                border          = border_val,
            )
            
            for child in container.children:
                child_node = create_node(child)
                node.add(child_node)

            return node

        self.root_node = create_node(self.theme.root)
        self.root_node.compute_layout(canvas_size)
        self.canvas_size = canvas_size  # Update stored canvas size
        get_all_nodes(self.theme.root, self.root_node)

    def recompute_layout(self, canvas_size):
        """Recompute layout with new canvas size and regenerate flattened data"""
        global node_flat, node_flat_abs
        
        # Clear previous layout data
        node_flat.clear()
        node_flat_abs.clear()
        
        # Recompute layout with new canvas size
        self.root_node.compute_layout(canvas_size)
        self.canvas_size = canvas_size
        
        # Regenerate flattened node data
        def get_all_nodes(container, node):
            border_box     = node.get_box(Edge.BORDER, relative=True)
            border_box_abs = node.get_box(Edge.BORDER, relative=False)
            content_box    = node.get_box(Edge.CONTENT, relative=True)
            content_box_abs = node.get_box(Edge.CONTENT, relative=False)
            padding_box    = node.get_box(Edge.PADDING, relative=True)
            margin_box     = node.get_box(Edge.MARGIN, relative=True)
            margin_box_abs = node.get_box(Edge.MARGIN, relative=False)
            
            edge_used, edge_used_abs = border_box, border_box_abs

            node_flat[container.id] = {
                'x'      : edge_used.x,
                'y'      : edge_used.y,
                'width'  : edge_used.width,
                'height' : edge_used.height
            }

            node_flat_abs[container.id] = {
                'x'      : edge_used_abs.x,
                'y'      : edge_used_abs.y,
                'width'  : edge_used_abs.width,
                'height' : edge_used_abs.height
            }
            
            for i, _container in enumerate(container.children):
                get_all_nodes(_container, node[i])
        
        get_all_nodes(self.theme.root, self.root_node)
        
        # Regenerate flattened container data
        self.json_data = []
        self.abs_json_data = []
        self.flatten_node_tree()
        
        return self.abs_json_data

    def flatten_node_tree(self):
        container_id_to_index = {}

        container_id_to_index[self.theme.root.id] = 0

        def get_indices(container):
            for container in container.children:
                container_id_to_index[container.id] = len(container_id_to_index)
                get_indices(container)

        get_indices(self.theme.root)

        def flatten_conts(container):
            x = y = width = height = 0
            node         = node_flat.get(container.id)
            parent_index = -1
            if node:
                x, y          = node['x'], node['y']
                width, height = node['width'], node['height']
                container_data = {
                    "id"                       : container.id,
                    "style"                    : container.style.id,
                    "display"                  : True if container.style.display != Display.NONE else False,
                    "overflow"                 : False if container.style.overflow == 'HIDDEN' else True,
                    "data"                     : container.data,
                    "img"                      : container.img,
                    "aspect_ratio"             : container.style.aspect_ratio,
                    "text"                     : container.text,
                    "font"                     : container.font,
                    "position"                 : [x, y],
                    "size"                     : [width, height],
                    "color"                    : container.style.color,
                    "color_1"                  : container.style.color_1,
                    "color_gradient_rot"       : container.style.color_gradient_rot,
                    "hover_color"              : container.style.hover_color,
                    "hover_color_1"            : container.style.hover_color_1,
                    "hover_color_gradient_rot" : container.style.hover_color_gradient_rot,
                    "click_color"              : container.style.click_color,
                    "click_color_1"            : container.style.click_color_1,
                    "click_color_gradient_rot" : container.style.click_color_gradient_rot,
                    "border_color"             : container.style.border_color,
                    "border_color_1"           : container.style.border_color_1,
                    "border_color_gradient_rot": container.style.border_color_gradient_rot,
                    "border_radius"            : container.style.border_radius,
                    "border_width"             : container.style.border_width,
                    "text_color"               : container.style.text_color,
                    "text_color_1"             : container.style.text_color_1,
                    "text_color_gradient_rot"  : container.style.text_color_gradient_rot,
                    "text_scale"               : container.style.text_scale,
                    "text_x"                   : container.style.text_x,
                    "text_y"                   : container.style.text_y,
                    "box_shadow_color"         : container.style.box_shadow_color,
                    "box_shadow_offset"        : container.style.box_shadow_offset,
                    "box_shadow_blur"          : container.style.box_shadow_blur,
                    "parent"                   : parent_index,
                    "passive"                  : container.passive,
                    "children"                 : [container_id_to_index[child.id] for child in container.children] if container.children else [],
                    "click"                    : container.click,
                    "toggle"                   : container.toggle,
                    "scroll"                   : container.scroll,
                    "_scroll_value"            : container._scroll_value,
                    "hover"                    : container.hover,
                    "hoverout"                 : container.hoverout,
                    "_clicked"                 : container._clicked,
                    "_prev_clicked"            : container._prev_clicked,
                    "_toggle_value"            : container._toggle_value,
                    "_toggled"                 : container._toggled,
                    "_prev_toggled"            : container._prev_toggled,
                    "_hovered"                 : container._hovered,
                    "_prev_hovered"            : container._prev_hovered
                }
                self.json_data.append(container_data)
            for child in container.children:
                flatten_conts(child)

        flatten_conts(self.theme.root)

        def flatten_conts_abs(container):
            x = y = width = height = 0
            node         = node_flat_abs.get(container.id)
            parent_index = -1
            if node:
                x, y          = node['x'], node['y']
                width, height = node['width'], node['height']
                container_data = {
                    "id"                       : container.id,
                    "style"                    : container.style.id,
                    "display"                  : True if container.style.display != Display.NONE else False,
                    "overflow"                 : False if container.style.overflow == 'HIDDEN' else True,
                    "data"                     : container.data,
                    "img"                      : container.img,
                    "aspect_ratio"             : container.style.aspect_ratio,
                    "text"                     : container.text,
                    "font"                     : container.font,
                    "position"                 : [x, y],
                    "size"                     : [width, height],
                    "color"                    : container.style.color,
                    "color_1"                  : container.style.color_1,
                    "color_gradient_rot"       : container.style.color_gradient_rot,
                    "hover_color"              : container.style.hover_color,
                    "hover_color_1"            : container.style.hover_color_1,
                    "hover_color_gradient_rot" : container.style.hover_color_gradient_rot,
                    "click_color"              : container.style.click_color,
                    "click_color_1"            : container.style.click_color_1,
                    "click_color_gradient_rot" : container.style.click_color_gradient_rot,
                    "border_color"             : container.style.border_color,
                    "border_color_1"           : container.style.border_color_1,
                    "border_color_gradient_rot": container.style.border_color_gradient_rot,
                    "border_radius"            : container.style.border_radius,
                    "border_width"             : container.style.border_width,
                    "text_color"               : container.style.text_color,
                    "text_color_1"             : container.style.text_color_1,
                    "text_color_gradient_rot"  : container.style.text_color_gradient_rot,
                    "text_scale"               : container.style.text_scale,
                    "text_x"                   : container.style.text_x,
                    "text_y"                   : container.style.text_y,
                    "box_shadow_color"         : container.style.box_shadow_color,
                    "box_shadow_offset"        : container.style.box_shadow_offset,
                    "box_shadow_blur"          : container.style.box_shadow_blur,
                    "parent"                   : parent_index,
                    "passive"                  : container.passive,
                    "children"                 : [container_id_to_index[child.id] for child in container.children] if container.children else [],
                    "click"                    : container.click,
                    "toggle"                   : container.toggle,
                    "scroll"                   : container.scroll,
                    "_scroll_value"            : container._scroll_value,
                    "hover"                    : container.hover,
                    "hoverout"                 : container.hoverout,
                    "_clicked"                 : container._clicked,
                    "_prev_clicked"            : container._prev_clicked,
                    "_toggle_value"            : container._toggle_value,
                    "_toggled"                 : container._toggled,
                    "_prev_toggled"            : container._prev_toggled,
                    "_hovered"                 : container._hovered,
                    "_prev_hovered"            : container._prev_hovered
                }
                self.abs_json_data.append(container_data)
            for child in container.children:
                flatten_conts_abs(child)

        flatten_conts_abs(self.theme.root)
