import os
import re
import yaml
import math

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

from .components.container import Container
from .components.style import Style
from .scss_compiler import SCSSCompiler

node_flat = {}
node_flat_abs = {}

def gamma_correct(value):
    return math.pow(value, 2.2)

def apply_gamma_correction(r, g, b, a):
    return [
        gamma_correct(r),
        gamma_correct(g),
        gamma_correct(b),
        a 
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
                new_visited = visited.copy()
                new_visited.add(var_name)
                resolved_value = variables[var_name]
                result = self._resolve_variables(resolved_value, variables, new_visited)
                return result
            return match.group(0)
        
        resolved = re.sub(var_pattern, replace_var, value)
        resolved = ' '.join(resolved.split())
        return resolved
    
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
        self.name         = ""
        self.author       = ""
        self.version      = ""
        self.scripts      = []
        self.style_files  = []
        self.default_font = ""
        self.components   = ""
        self.palette      = {}
        self.styles       = Styles()
        self.root         = Container()
        
class UI():
    def __init__(self, path=None, base_dir=None, canvas_size=(800, 600)):
        self.selected_theme = "xwz_default"
        self.settings       = Settings()
        self.theme          = Theme()
        self.json_data      = []
        self.abs_json_data  = []
        self.root_node      = None
        self.canvas_size    = canvas_size

        self.parse_toml(path, base_dir)
        self.parse_css()
        self.create_node_tree(canvas_size)
        self.flatten_node_tree()

    def get_by_id(self, target_id):
        return self.theme.root.get_by_id(target_id)

    def load_conf_file(self, path):
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        return data
    
    def parse_toml(self, path=None, base_dir=None):
        data     = self.load_conf_file(path)
        ui_data  = data.get('app', {})
        theme    = ui_data['theme']

        self.selected_theme        = ui_data['selected_theme']
        self.default_theme         = ui_data['default_theme']

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

        self.theme.name         = theme[self.theme_index]['name']
        self.theme.author       = theme[self.theme_index]['author']
        self.theme.version      = theme[self.theme_index]['version']
        self.theme.scripts      = theme[self.theme_index]['scripts']
        self.theme.style_files  = theme[self.theme_index]['styles']
        self.theme.default_font = theme[self.theme_index]['default_font']
        self.theme.components   = theme[self.theme_index]['components']

        def load_container(container_data, parent_container):
            for attr_name, attr_value in container_data.items():

                if isinstance(attr_value, dict):
                    has_component_data = 'data' in attr_value and isinstance(attr_value['data'], str) and attr_value['data'].startswith('[') and attr_value['data'].endswith(']')
                    
                    child_container = Container()
                    if parent_container.id == "root":
                        child_container.id = attr_name
                    else:
                        child_container.id = f"{parent_container.id}_{attr_name}"
                    child_container.parent = parent_container
                    parent_container.children.append(child_container)
                    
                    for child_attr_name, child_attr_value in attr_value.items():
                        if not isinstance(child_attr_value, dict):
                            if hasattr(child_container, child_attr_name):
                                if not (child_attr_name == 'data' and has_component_data):
                                    setattr(child_container, child_attr_name.replace('-', '_'), child_attr_value)
                    
                    if has_component_data:
                        component_ref = attr_value['data']
                        component_dir = os.path.join(base_dir, self.theme.components)
                        component_loaded = False
                        
                        component_params = {}
                        for param_name, param_value in attr_value.items():
                            if not isinstance(param_value, dict) and param_name != 'data':
                                component_params[param_name] = param_value
                        
                        for root, dirs, files in os.walk(component_dir):
                            for filename in files:
                                if filename.endswith('.yaml') and f'[{filename.replace(".yaml", "")}]' == component_ref:
                                    file_path = os.path.join(root, filename)
                                    component_base_name = filename.replace('.yaml', '')
                                    scss_file_path = os.path.join(root, f"{component_base_name}.scss")
                                    
                                    with open(file_path, 'r') as f:
                                        component_data = yaml.safe_load(f)
                                        component_key = component_ref.replace("[",'').replace("]",'')
                                        
                                        if os.path.exists(scss_file_path):
                                            scss_compiler = SCSSCompiler()
                                            namespace = child_container.id
                                            compiled_css = scss_compiler.compile_file(
                                                scss_file_path,
                                                namespace=namespace,
                                                param_overrides=component_params,
                                                component_name=component_base_name
                                            )
                                            
                                            css_parser = CSSParser()
                                            component_styles = css_parser.parse(compiled_css)
                                            for selector, declarations in component_styles.items():
                                                style_obj = Style()
                                                style_obj.id = selector
                                                for prop, value in declarations.items():
                                                    attr_name_parsed, attr_value_parsed = self.parse_container_props_from_style(prop, value)
                                                    setattr(style_obj, attr_name_parsed, attr_value_parsed)
                                                self.theme.styles.__dict__[selector] = style_obj
                                        
                                        def substitute_params(value, params):
                                            if not isinstance(value, str):
                                                return value
                                            
                                            pattern = r'\{\{(\w+)\s*,\s*["\']([^"\']*?)["\']\}\}'
                                            
                                            def replace_param(match):
                                                param_name = match.group(1)
                                                default_value = match.group(2)
                                                return str(params.get(param_name, default_value))
                                            
                                            return re.sub(pattern, replace_param, value)
                                        
                                        def load_component_with_namespace(comp_data, parent, namespace_prefix, params):
                                            for attr_name, attr_value in comp_data.items():
                                                if isinstance(attr_value, dict):
                                                    namespaced_child = Container()
                                                    namespaced_child.id = f"{parent.id}_{attr_name}"
                                                    namespaced_child.parent = parent
                                                    parent.children.append(namespaced_child)
                                                    
                                                    for child_attr_name, child_attr_value in attr_value.items():
                                                        if not isinstance(child_attr_value, dict):
                                                            if hasattr(namespaced_child, child_attr_name):
                                                                substituted_value = substitute_params(child_attr_value, params)
                                                                if child_attr_name == 'style' and isinstance(substituted_value, str):
                                                                    if substituted_value == component_base_name:
                                                                        substituted_value = child_container.id
                                                                    elif substituted_value.startswith(component_base_name + '_'):
                                                                        substituted_value = substituted_value.replace(component_base_name, child_container.id, 1)
                                                                setattr(namespaced_child, child_attr_name.replace('-', '_'), substituted_value)
                                                    
                                                    load_component_with_namespace(attr_value, namespaced_child, namespaced_child.id, params)
                                                else:
                                                    if hasattr(parent, attr_name):
                                                        substituted_value = substitute_params(attr_value, params)
                                                        if attr_name == 'style' and isinstance(substituted_value, str):
                                                            if substituted_value == component_base_name:
                                                                substituted_value = child_container.id
                                                            elif substituted_value.startswith(component_base_name + '_'):
                                                                substituted_value = substituted_value.replace(component_base_name, child_container.id, 1)
                                                        setattr(parent, attr_name.replace('-', '_'), substituted_value)
                                        
                                        load_component_with_namespace(component_data[component_key], child_container, attr_name, component_params)
                                        component_loaded = True
                                    break
                            if component_loaded:
                                break
                    else:
                        load_container(attr_value, child_container)

                else:
                    if hasattr(parent_container, attr_name):
                        setattr(parent_container, attr_name.replace('-', '_'), attr_value)


        self.theme.root.id = "root"
        load_container(root, self.theme.root)

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

        bool_props = [
            'aspect_ratio'
            ]

        if attr_name in color_props:
            value_color = Color.parse(attr_value)
            srgb_normalized = [value_color.r / 255.0, value_color.g / 255.0, value_color.b / 255.0, value_color.a]
            attr_value = apply_gamma_correction(*srgb_normalized)

        elif attr_name in float_props:
            attr_value = float(attr_value.replace('px', '').strip())

        elif attr_name in rotation_props:
            attr_value = float(attr_value.replace('deg', '').strip())

        elif attr_name == 'box_shadow_offset':
            values = attr_value.strip().split()
            if len(values) == 2:
                x_offset = float(values[0].replace('px', '').strip())
                y_offset = float(values[1].replace('px', '').strip())
                attr_value = [x_offset, y_offset, 0.0]
            else:
                attr_value = [0.0, 0.0, 0.0]

        elif attr_name in bool_props:
            attr_value = attr_value.strip().lower() in ('true', '1', 'yes')

        return attr_name, attr_value

    def parse_css(self):
        from . import get_addon_root
        addon_dir  = get_addon_root()
        style_str = ""
        scss_compiler = SCSSCompiler()
        
        for _style_file in self.theme.style_files:
            file_path = os.path.join(addon_dir, _style_file)
            if _style_file.endswith('.scss'):
                compiled_css = scss_compiler.compile_file(file_path)
                style_str += compiled_css
            elif _style_file.endswith('.css'):
                with open(file_path, 'r') as f:
                    style_str += f.read()
        
        css_string = style_str
        parser = CSSParser()
        styles = parser.parse(css_string)
        for selector, declarations in styles.items():
            style_obj = Style()
            selector_clean = selector.lstrip('.')
            style_obj.id = selector_clean
            for prop, value in declarations.items():
                attr_name, attr_value = self.parse_container_props_from_style(prop, value)
                setattr(style_obj, attr_name, attr_value)
            self.theme.styles.__dict__[selector_clean] = style_obj
        def apply_styles_to_containers(container):
            if hasattr(container, 'style') and container.style:
                style_name = container.style
                if isinstance(style_name, str):
                    if hasattr(self.theme.styles, style_name):
                        original_style = getattr(self.theme.styles, style_name)
                        style_copy = Style()
                        style_copy.id = original_style.id
                        for attr_name in dir(original_style):
                            if not attr_name.startswith('_'):
                                try:
                                    attr_value = getattr(original_style, attr_name)
                                    if not callable(attr_value):
                                        if isinstance(attr_value, list):
                                            setattr(style_copy, attr_name, attr_value.copy())
                                        else:
                                            setattr(style_copy, attr_name, attr_value)
                                except AttributeError:
                                    pass
                        container.style = style_copy
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
                padding_str = container.style.padding.strip().lower()
                if 'calc(' not in padding_str:
                    # Split on whitespace - this handles multiple spaces correctly
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
                margin_str = container.style.margin.strip().lower()
                if 'calc(' not in margin_str:
                    # Split on whitespace - this handles multiple spaces correctly
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
                border_width_str = container.style.border_width.strip().lower()
                if 'calc(' not in border_width_str:
                    # Split on whitespace - this handles multiple spaces correctly
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
                border_str = container.style.border.strip().lower()
                if 'calc(' not in border_str:
                    # Split on whitespace - this handles multiple spaces correctly
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
            if not hasattr(container, 'style') or container.style is None or isinstance(container.style, str):
                default_style = Style()
                setattr(default_style, 'width', "100%")
                setattr(default_style, 'height', "100%")
                container.style = default_style
            
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
        self.canvas_size = canvas_size
        get_all_nodes(self.theme.root, self.root_node)

    def recompute_layout(self, canvas_size):
        """Recompute layout with new canvas size and regenerate flattened data"""
        global node_flat, node_flat_abs
        
        node_flat.clear()
        node_flat_abs.clear()
        
        self.root_node.compute_layout(canvas_size)
        self.canvas_size = canvas_size
        
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
                    "color"                    : list(container.style.color),
                    "color_1"                  : list(container.style.color_1),
                    "color_gradient_rot"       : container.style.color_gradient_rot,
                    "hover_color"              : list(container.style.hover_color),
                    "hover_color_1"            : list(container.style.hover_color_1),
                    "hover_color_gradient_rot" : container.style.hover_color_gradient_rot,
                    "click_color"              : list(container.style.click_color),
                    "click_color_1"            : list(container.style.click_color_1),
                    "click_color_gradient_rot" : container.style.click_color_gradient_rot,
                    "border_color"             : list(container.style.border_color),
                    "border_color_1"           : list(container.style.border_color_1),
                    "border_color_gradient_rot": container.style.border_color_gradient_rot,
                    "border_radius"            : container.style.border_radius,
                    "border_width"             : container.style.border_width,
                    "text_color"               : list(container.style.text_color),
                    "text_color_1"             : list(container.style.text_color_1),
                    "text_color_gradient_rot"  : container.style.text_color_gradient_rot,
                    "text_scale"               : container.style.text_scale,
                    "text_x"                   : container.style.text_x,
                    "text_y"                   : container.style.text_y,
                    "box_shadow_color"         : list(container.style.box_shadow_color),
                    "box_shadow_offset"        : list(container.style.box_shadow_offset),
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
                    "_clicked"                 : False,
                    "_prev_clicked"            : False,
                    "_toggle_value"            : False,
                    "_toggled"                 : False,
                    "_prev_toggled"            : False,
                    "_hovered"                 : False,
                    "_prev_hovered"            : False
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
                    "color"                    : list(container.style.color),
                    "color_1"                  : list(container.style.color_1),
                    "color_gradient_rot"       : container.style.color_gradient_rot,
                    "hover_color"              : list(container.style.hover_color),
                    "hover_color_1"            : list(container.style.hover_color_1),
                    "hover_color_gradient_rot" : container.style.hover_color_gradient_rot,
                    "click_color"              : list(container.style.click_color),
                    "click_color_1"            : list(container.style.click_color_1),
                    "click_color_gradient_rot" : container.style.click_color_gradient_rot,
                    "border_color"             : list(container.style.border_color),
                    "border_color_1"           : list(container.style.border_color_1),
                    "border_color_gradient_rot": container.style.border_color_gradient_rot,
                    "border_radius"            : container.style.border_radius,
                    "border_width"             : container.style.border_width,
                    "text_color"               : list(container.style.text_color),
                    "text_color_1"             : list(container.style.text_color_1),
                    "text_color_gradient_rot"  : container.style.text_color_gradient_rot,
                    "text_scale"               : container.style.text_scale,
                    "text_x"                   : container.style.text_x,
                    "text_y"                   : container.style.text_y,
                    "box_shadow_color"         : list(container.style.box_shadow_color),
                    "box_shadow_offset"        : list(container.style.box_shadow_offset),
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
                    "_clicked"                 : False,
                    "_prev_clicked"            : False,
                    "_toggle_value"            : False,
                    "_toggled"                 : False,
                    "_prev_toggled"            : False,
                    "_hovered"                 : False,
                    "_prev_hovered"            : False
                }
                self.abs_json_data.append(container_data)
            for child in container.children:
                flatten_conts_abs(child)

        flatten_conts_abs(self.theme.root)
 