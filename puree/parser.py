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
import os
import re
import yaml

from stretchable import Node
from stretchable.style import PCT, AUTO, PT
from stretchable import Edge
from stretchable.style.props import BoxSizing
from stretchable.style.props import FlexDirection, FlexWrap
from stretchable.style.props import AlignItems, AlignSelf, AlignContent
from stretchable.style.props import JustifyContent, JustifyItems, JustifySelf
from stretchable.style.props import Display, Position, Overflow
from stretchable.style.props import GridAutoFlow, GridPlacement
from stretchable.style.props import GridTrackSizing, GridTrackSize
from stretchable.style.geometry.rect import RectPointsPercent, RectPointsPercentAuto
from stretchable.style.geometry.length import LengthPointsPercent, LengthPointsPercentAuto
from stretchable.style.geometry.size import SizePointsPercent, SizePointsPercentAuto

from .components.container import Container
from .components.style import Style
from .native_bindings import ContainerProcessor, SCSSCompiler, ColorProcessor, CSSCascade

node_flat = {}
node_flat_abs = {}

color_processor = ColorProcessor()

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
        from .space_config import get_parsed_config
        
        space_config = get_parsed_config()
        if space_config and space_config.theme_data:
            theme_data = space_config.theme_data
            
            self.selected_theme = theme_data.name
            self.default_theme = theme_data.name
            self.theme_index = 0
            
            self.theme.name = theme_data.name
            self.theme.author = theme_data.author
            self.theme.version = theme_data.version
            self.theme.scripts = theme_data.scripts
            self.theme.style_files = theme_data.styles
            self.theme.default_font = theme_data.default_font
            self.theme.components = theme_data.components
            
            data = self.load_conf_file(path)
            ui_data = data.get('app', {})
            theme = ui_data['theme']
            
            selected_theme = None
            for _theme_ in theme:
                if _theme_['name'] == theme_data.name:
                    selected_theme = _theme_
                    break
            
            if selected_theme:
                root = selected_theme['root']
            else:
                root = {}
        else:
            data = self.load_conf_file(path)
            ui_data = data.get('app', {})
            theme = ui_data['theme']

            self.selected_theme = ui_data['selected_theme']
            self.default_theme = ui_data['default_theme']

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
                self.theme_index = 0
                self.default_theme = theme[0]['name']

            root = ui_data['theme'][self.theme_index]['root']

            self.theme.name = theme[self.theme_index]['name']
            self.theme.author = theme[self.theme_index]['author']
            self.theme.version = theme[self.theme_index]['version']
            self.theme.scripts = theme[self.theme_index]['scripts']
            self.theme.style_files = theme[self.theme_index]['styles']
            self.theme.default_font = theme[self.theme_index]['default_font']
            self.theme.components = theme[self.theme_index]['components']

        self._component_css = ""

        def set_container_attr(container, attr_name, attr_value):
            """Set a YAML attribute on a container, handling 'class' specially."""
            if attr_name == 'class':
                if isinstance(attr_value, str):
                    container.classes = attr_value.split()
                elif isinstance(attr_value, list):
                    container.classes = attr_value
            elif hasattr(container, attr_name):
                setattr(container, attr_name.replace('-', '_'), attr_value)

        def load_container(container_data, parent_container):
            for attr_name, attr_value in container_data.items():

                if isinstance(attr_value, dict):
                    has_component_data = 'data' in attr_value and isinstance(attr_value['data'], str) and attr_value['data'].startswith('[') and attr_value['data'].endswith(']')
                    
                    child_container = Container()
                    if parent_container.id == "root":
                        child_container.id = attr_name
                    else:
                        child_container.id = f"{parent_container.id}_{attr_name}"
                    # Always add YAML key as a class so CSS can target it
                    child_container.classes = [attr_name]
                    child_container.parent = parent_container
                    parent_container.children.append(child_container)
                    
                    for child_attr_name, child_attr_value in attr_value.items():
                        if not isinstance(child_attr_value, dict):
                            if child_attr_name == 'data' and has_component_data:
                                continue
                            set_container_attr(child_container, child_attr_name, child_attr_value)
                    
                    if has_component_data:
                        component_ref = attr_value['data']
                        component_dir = os.path.join(base_dir, self.theme.components)
                        component_loaded = False
                        
                        component_params = {}
                        for param_name, param_value in attr_value.items():
                            if not isinstance(param_value, dict) and param_name != 'data':
                                component_params[param_name] = str(param_value)
                        
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
                                            import re as _re
                                            compiled_css = _re.sub(
                                                r'^([a-zA-Z_][\w]*)([\s:{])',
                                                r'.\1\2',
                                                compiled_css,
                                                flags=_re.MULTILINE
                                            )
                                            self._component_css += compiled_css
                                        
                                        def substitute_params(value, params):
                                            if not isinstance(value, str):
                                                return value
                                            
                                            pattern = r'\{\{(\w+)\s*,\s*["\']([^"\']*?)["\']\}\}'
                                            
                                            def replace_param(match):
                                                param_name = match.group(1)
                                                default_value = match.group(2)
                                                return str(params.get(param_name, default_value))
                                            
                                            return re.sub(pattern, replace_param, value)
                                        
                                        def namespace_class(value):
                                            """Remap component class names to namespaced equivalents."""
                                            if value == component_base_name:
                                                return child_container.id
                                            elif value.startswith(component_base_name + '_'):
                                                return value.replace(component_base_name, child_container.id, 1)
                                            return value
                                        
                                        def load_component(comp_data, parent, params):
                                            for attr_name, attr_value in comp_data.items():
                                                if isinstance(attr_value, dict):
                                                    comp_child = Container()
                                                    comp_child.id = f"{parent.id}_{attr_name}"
                                                    comp_child.parent = parent
                                                    parent.children.append(comp_child)
                                                    
                                                    for child_attr_name, child_attr_value in attr_value.items():
                                                        if not isinstance(child_attr_value, dict):
                                                            substituted = substitute_params(child_attr_value, params)
                                                            if child_attr_name == 'class' and isinstance(substituted, str):
                                                                comp_child.classes = [namespace_class(substituted)]
                                                            elif hasattr(comp_child, child_attr_name):
                                                                setattr(comp_child, child_attr_name.replace('-', '_'), substituted)
                                                    
                                                    load_component(attr_value, comp_child, params)
                                                else:
                                                    substituted = substitute_params(attr_value, params)
                                                    if attr_name == 'class' and isinstance(substituted, str):
                                                        parent.classes = [namespace_class(substituted)]
                                                    elif hasattr(parent, attr_name):
                                                        setattr(parent, attr_name.replace('-', '_'), substituted)
                                        
                                        load_component(component_data[component_key], child_container, component_params)
                                        component_loaded = True
                                    break
                            if component_loaded:
                                break
                    else:
                        load_container(attr_value, child_container)

                else:
                    set_container_attr(parent_container, attr_name, attr_value)


        self.theme.root.id = "root"
        load_container(root, self.theme.root)

    def parse_container_props_from_style(self, attr_name, attr_value):
        attr_name = attr_name.replace('-', '_')

        color_props = [
            'background_color', 'background_color_2',
            'hover_background_color', 'hover_background_color_2',
            'click_background_color', 'click_background_color_2',
            'border_color', 'border_color_2',
            'color', 'color_2',
            'box_shadow_color',
            'text_shadow_color'
            ]
        
        float_props = [
            'border_radius', 'border_radius_tl', 'border_radius_tr',
            'border_radius_br', 'border_radius_bl', 'border_width',
            'border_width_top', 'border_width_right',
            'border_width_bottom', 'border_width_left',
            'font_size', 'text_x', 'text_y',
            'box_shadow_blur', 'opacity',
            'text_shadow_offset_x', 'text_shadow_offset_y', 'text_shadow_blur',
            'flex_grow', 'flex_shrink', 'scrollbar_width',
            'line_height', 'letter_spacing'
            ]

        rotation_props = [
            'background_gradient_rot',
            'hover_background_gradient_rot',
            'click_background_gradient_rot',
            'border_gradient_rot',
            'color_gradient_rot'
            ]

        bool_props = [
            'aspect_ratio'
            ]
        
        string_props = [
            'overflow', 'overflow_x', 'overflow_y',
            'display', 'position', 'box_sizing',
            'pointer_events', 'visibility',
            'font_weight', 'font_style',
            'flex_direction', 'flex_wrap',
            'align_items', 'align_self', 'align_content',
            'justify_content', 'justify_items', 'justify_self',
            'text_align', 'text_align_v',
            'text_transform', 'text_decoration', 'text_overflow', 'white_space',
            'img_align_h', 'img_align_v',
            'grid_auto_flow',
            'gradient_stops', 'hover_gradient_stops', 'click_gradient_stops'
            ]
        
        # These CSS dimension properties pass through as raw strings
        # (parsed later in create_node via parse_css_value)
        dimension_props = [
            'width', 'height', 'min_width', 'min_height', 'max_width', 'max_height',
            'top', 'right', 'bottom', 'left',
            'gap', 'row_gap', 'column_gap', 'flex_basis',
            'font_family',
            'grid_template_rows', 'grid_template_columns',
            'grid_auto_rows', 'grid_auto_columns',
            'grid_row', 'grid_column'
            ]

        if attr_name in color_props:
            try:
                attr_value = color_processor.parse_color(attr_value)
            except Exception as e:
                print(f"⚠️  Color parsing failed for '{attr_name}' = '{attr_value}': {e}")
                print(f"   Using default black color")
                attr_value = [0.0, 0.0, 0.0, 1.0]

        elif attr_name in float_props:
            attr_value = float(attr_value.replace('px', '').strip())

        elif attr_name in rotation_props:
            attr_value = float(attr_value.replace('deg', '').strip())

        elif attr_name == 'box_shadow_offset':
            values = attr_value.strip().split()
            if len(values) >= 3:
                x_offset = float(values[0].replace('px', '').strip())
                y_offset = float(values[1].replace('px', '').strip())
                spread = float(values[2].replace('px', '').strip())
                attr_value = [x_offset, y_offset, spread]
            elif len(values) == 2:
                x_offset = float(values[0].replace('px', '').strip())
                y_offset = float(values[1].replace('px', '').strip())
                attr_value = [x_offset, y_offset, 0.0]
            else:
                attr_value = [0.0, 0.0, 0.0]

        elif attr_name in bool_props:
            attr_value = attr_value.strip().lower() in ('true', '1', 'yes')
        
        elif attr_name == 'z_index':
            try:
                attr_value = int(float(attr_value.strip().replace('px', '')))
            except (ValueError, TypeError):
                attr_value = 0

        elif attr_name in string_props:
            attr_value = attr_value.strip().upper().replace('-', '_')

        elif attr_name in dimension_props:
            attr_value = attr_value.strip()

        elif attr_name == 'transition':
            # Shorthand: "background-color 0.3s ease 0s" or "all 0.2s"
            parts = attr_value.strip().split()
            if parts:
                attr_name = 'transition_property'
                attr_value = parts[0].replace('-', '_')
            # Parse duration if present
            if len(parts) > 1:
                # Will be handled separately via multi-set below
                pass
            return self._parse_transition_shorthand(attr_value if isinstance(attr_value, str) else parts[0], parts)

        elif attr_name == 'transition_duration':
            val = attr_value.strip().lower()
            attr_value = float(val.replace('s', '').replace('ms', '')) 
            if 'ms' in val.replace(str(attr_value), ''):
                attr_value /= 1000.0

        elif attr_name == 'transition_delay':
            val = attr_value.strip().lower()
            attr_value = float(val.replace('s', '').replace('ms', ''))
            if 'ms' in val.replace(str(attr_value), ''):
                attr_value /= 1000.0

        elif attr_name == 'transition_timing_function':
            attr_value = attr_value.strip().lower()

        return attr_name, attr_value

    def _parse_transition_shorthand(self, raw_value, parts):
        """Parse transition shorthand and return multiple (name, value) pairs as a list."""
        prop = parts[0].replace('-', '_') if parts else 'all'
        duration = 0.0
        timing = 'ease'
        delay = 0.0
        
        for p in parts[1:]:
            p_lower = p.lower().strip(',')
            if p_lower in ('ease', 'linear', 'ease-in', 'ease-out', 'ease-in-out'):
                timing = p_lower
            elif 's' in p_lower or 'ms' in p_lower:
                val = float(p_lower.replace('ms', '').replace('s', ''))
                if 'ms' in p_lower:
                    val /= 1000.0
                if duration == 0.0:
                    duration = val
                else:
                    delay = val
        
        # Return as the property name, storing all transition info
        # We'll use a special multi-set approach
        return ('transition_property', prop, duration, timing, delay)

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
        
        # Collect component CSS too
        style_str += self._component_css

        # Build container list and run cascade
        cascade = CSSCascade()
        cascade.parse_css(style_str)

        flat_containers = self._build_container_list()
        if not flat_containers:
            return

        # First pass: resolve normal state
        normal_resolved = {}
        viewport = (float(self.canvas_size[0]), float(self.canvas_size[1]))
        try:
            normal_resolved = cascade.resolve(flat_containers, "normal", viewport) or {}
        except Exception as e:
            print(f"⚠️  CSSCascade resolve(normal) failed: {e}")

        for container_id, props in normal_resolved.items():
            container = self._find_container(container_id)
            if container is None:
                continue
            if not isinstance(container.style, Style):
                container.style = Style()
                container.style.id = container_id
            for prop, value in props.items():
                result = self.parse_container_props_from_style(prop, value)
                if isinstance(result, tuple) and len(result) == 5:
                    # Transition shorthand: (property, prop_value, duration, timing, delay)
                    _, t_prop, t_dur, t_timing, t_delay = result
                    container.style.transition_property = t_prop
                    container.style.transition_duration = t_dur
                    container.style.transition_timing_function = t_timing
                    container.style.transition_delay = t_delay
                else:
                    attr_name, attr_value = result
                    setattr(container.style, attr_name, attr_value)

        # Second pass: hover and active — only set properties that DIFFER from normal
        for state, prefix in (("hover", "hover_"), ("active", "click_")):
            try:
                resolved = cascade.resolve(flat_containers, state, viewport) or {}
            except Exception as e:
                print(f"⚠️  CSSCascade resolve({state}) failed: {e}")
                continue

            for container_id, props in resolved.items():
                container = self._find_container(container_id)
                if container is None:
                    continue
                if not isinstance(container.style, Style):
                    container.style = Style()
                    container.style.id = container_id

                normal_props = normal_resolved.get(container_id, {})
                for prop, value in props.items():
                    # Skip if same as normal — don't override the sentinel defaults
                    if normal_props.get(prop) == value:
                        continue
                    result = self.parse_container_props_from_style(prop, value)
                    if isinstance(result, tuple) and len(result) == 5:
                        continue  # transition shorthand already parsed in normal pass
                    attr_name, attr_value = result
                    state_attr = f"{prefix}{attr_name}" if not attr_name.startswith(prefix) else attr_name
                    if hasattr(container.style, state_attr):
                        setattr(container.style, state_attr, attr_value)

        # Ensure every container has a Style object
        def ensure_styles(container):
            if not isinstance(container.style, Style):
                container.style = Style()
                container.style.id = container.id
            for child in container.children:
                ensure_styles(child)
        ensure_styles(self.theme.root)

    def _build_container_list(self):
        """Build flat list of containers with parent indices for CSSCascade."""
        flat = []

        def walk(container, parent_idx):
            idx = len(flat)
            flat.append({
                "id": container.id,
                "classes": list(container.classes) if container.classes else [],
                "parent_idx": parent_idx
            })
            for child in container.children:
                walk(child, idx)

        walk(self.theme.root, -1)
        return flat

    def _find_container(self, container_id):
        """Find a container by ID in the tree."""
        def search(container):
            if container.id == container_id:
                return container
            for child in container.children:
                found = search(child)
                if found:
                    return found
            return None
        return search(self.theme.root)

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
            
            container._layout_node = node
            
            for i, _container in enumerate(container.children):
                get_all_nodes(_container, node[i])

            return
        # Viewport and font-size context for CSS units
        vw_unit = canvas_size[0] / 100.0  # 1vw = 1% of viewport width
        vh_unit = canvas_size[1] / 100.0  # 1vh = 1% of viewport height
        vmin_unit = min(canvas_size[0], canvas_size[1]) / 100.0  # 1vmin = 1% of smaller dimension
        vmax_unit = max(canvas_size[0], canvas_size[1]) / 100.0  # 1vmax = 1% of larger dimension
        root_font_size = 16.0  # default root font-size (rem base)
        if hasattr(self.theme, 'root') and self.theme.root.style:
            root_font_size = float(self.theme.root.style.font_size or 16.0)

        import re
        _calc_re = re.compile(r'calc\((.+)\)')
        _unit_re = re.compile(r'(-?[\d.]+)\s*(px|%|rem|em|vmin|vmax|vw|vh)?')

        def resolve_units(value_str, parent_font_size=16.0):
            """Resolve a CSS value string to pixels. Returns (px_value, is_percent, pct_value)."""
            value_str = value_str.strip().lower()
            # calc() — evaluate simple expressions
            m = _calc_re.match(value_str)
            if m:
                expr = m.group(1)
                # Tokenize and resolve each term
                tokens = re.split(r'(\s*[+\-]\s*)', expr)
                total = 0.0
                op = '+'
                for token in tokens:
                    token = token.strip()
                    if token in ('+', '-'):
                        op = token
                        continue
                    if not token:
                        continue
                    px_val, is_pct, pct_val = resolve_units(token, parent_font_size)
                    val = px_val
                    if op == '-':
                        total -= val
                    else:
                        total += val
                return (total, False, 0.0)
            
            um = _unit_re.match(value_str)
            if um:
                num = float(um.group(1))
                unit = um.group(2) or 'px'
                if unit == 'px':
                    return (num, False, 0.0)
                elif unit == '%':
                    return (0.0, True, num)
                elif unit == 'rem':
                    return (num * root_font_size, False, 0.0)
                elif unit == 'em':
                    return (num * parent_font_size, False, 0.0)
                elif unit == 'vw':
                    return (num * vw_unit, False, 0.0)
                elif unit == 'vh':
                    return (num * vh_unit, False, 0.0)
                elif unit == 'vmin':
                    return (num * vmin_unit, False, 0.0)
                elif unit == 'vmax':
                    return (num * vmax_unit, False, 0.0)
            return (0.0, False, 0.0)

        def parse_css_value(value_str):
            value_str = str(value_str).lower().strip()
            if value_str in ('auto', ''):
                return AUTO
            # Handle calc(), rem, em, vw, vh, vmin, vmax
            if any(u in value_str for u in ('calc(', 'rem', 'em', 'vw', 'vh', 'vmin', 'vmax')):
                px_val, is_pct, pct_val = resolve_units(value_str)
                if is_pct:
                    return LengthPointsPercent.from_any(pct_val * PCT)
                return LengthPointsPercent.from_any(px_val * PT)
            if 'px' in value_str:
                return LengthPointsPercent.from_any(float(value_str.replace('px', '')) * PT)
            if '%' in value_str:
                return LengthPointsPercent.from_any(float(value_str.replace('%', '')) * PCT)
            try:
                num = float(value_str)
                if num == 0:
                    return LengthPointsPercent.from_any(0 * PT)
                return LengthPointsPercent.from_any(num * PT)
            except (ValueError, TypeError):
                return LengthPointsPercent.from_any(0 * PT)

        def parse_css_value_auto(value_str):
            """Like parse_css_value but returns LengthPointsPercentAuto (supports auto)."""
            value_str = str(value_str).lower().strip()
            if value_str in ('auto', ''):
                return LengthPointsPercentAuto.from_any(AUTO)
            if any(u in value_str for u in ('calc(', 'rem', 'em', 'vw', 'vh', 'vmin', 'vmax')):
                px_val, is_pct, pct_val = resolve_units(value_str)
                if is_pct:
                    return LengthPointsPercentAuto.from_any(pct_val * PCT)
                return LengthPointsPercentAuto.from_any(px_val * PT)
            if 'px' in value_str:
                return LengthPointsPercentAuto.from_any(float(value_str.replace('px', '')) * PT)
            if '%' in value_str:
                return LengthPointsPercentAuto.from_any(float(value_str.replace('%', '')) * PCT)
            try:
                num = float(value_str)
                if num == 0:
                    return LengthPointsPercentAuto.from_any(0 * PT)
                return LengthPointsPercentAuto.from_any(num * PT)
            except (ValueError, TypeError):
                return LengthPointsPercentAuto.from_any(0 * PT)
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
            
            bw = getattr(container.style, 'border_width', None)
            if bw is not None:
                if isinstance(bw, (int, float)):
                    val = LengthPointsPercent.from_any(int(bw) * PT)
                    width_top = width_right = width_bottom = width_left = val
                elif isinstance(bw, str):
                    border_width_str = bw.strip().lower()
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
        def parse_align_items(val_str):
            m = {'start': AlignItems.START, 'end': AlignItems.END,
                 'flex_start': AlignItems.FLEX_START, 'flex_end': AlignItems.FLEX_END,
                 'center': AlignItems.CENTER, 'baseline': AlignItems.BASELINE,
                 'stretch': AlignItems.STRETCH}
            return m.get(val_str.lower().replace('-', '_'), None)

        def parse_align_self(val_str):
            m = {'start': AlignSelf.START, 'end': AlignSelf.END,
                 'flex_start': AlignSelf.FLEX_START, 'flex_end': AlignSelf.FLEX_END,
                 'center': AlignSelf.CENTER, 'baseline': AlignSelf.BASELINE,
                 'stretch': AlignSelf.STRETCH, 'auto': None}
            return m.get(val_str.lower().replace('-', '_'), None)

        def parse_align_content(val_str):
            m = {'start': AlignContent.START, 'end': AlignContent.END,
                 'flex_start': AlignContent.FLEX_START, 'flex_end': AlignContent.FLEX_END,
                 'center': AlignContent.CENTER, 'stretch': AlignContent.STRETCH,
                 'space_between': AlignContent.SPACE_BETWEEN,
                 'space_evenly': AlignContent.SPACE_EVENLY,
                 'space_around': AlignContent.SPACE_AROUND}
            return m.get(val_str.lower().replace('-', '_'), None)

        def parse_justify_content(val_str):
            m = {'start': JustifyContent.START, 'end': JustifyContent.END,
                 'flex_start': JustifyContent.FLEX_START, 'flex_end': JustifyContent.FLEX_END,
                 'center': JustifyContent.CENTER, 'stretch': JustifyContent.STRETCH,
                 'space_between': JustifyContent.SPACE_BETWEEN,
                 'space_evenly': JustifyContent.SPACE_EVENLY,
                 'space_around': JustifyContent.SPACE_AROUND}
            return m.get(val_str.lower().replace('-', '_'), None)

        def parse_justify_items(val_str):
            m = {'start': JustifyItems.START, 'end': JustifyItems.END,
                 'flex_start': JustifyItems.FLEX_START, 'flex_end': JustifyItems.FLEX_END,
                 'center': JustifyItems.CENTER, 'baseline': JustifyItems.BASELINE,
                 'stretch': JustifyItems.STRETCH}
            return m.get(val_str.lower().replace('-', '_'), None)

        def parse_justify_self(val_str):
            m = {'start': JustifySelf.START, 'end': JustifySelf.END,
                 'flex_start': JustifySelf.FLEX_START, 'flex_end': JustifySelf.FLEX_END,
                 'center': JustifySelf.CENTER, 'baseline': JustifySelf.BASELINE,
                 'stretch': JustifySelf.STRETCH, 'auto': None}
            return m.get(val_str.lower().replace('-', '_'), None)

        def parse_gap_value(value_str):
            """Parse gap value into SizePointsPercent."""
            value_str = str(value_str).lower().strip()
            if not value_str or value_str == '0' or value_str == '0px':
                return SizePointsPercent.from_any(0 * PT)
            if 'px' in value_str:
                return SizePointsPercent.from_any(float(value_str.replace('px', '')) * PT)
            if '%' in value_str:
                return SizePointsPercent.from_any(float(value_str.replace('%', '')) * PCT)
            try:
                return SizePointsPercent.from_any(float(value_str) * PT)
            except (ValueError, TypeError):
                return SizePointsPercent.from_any(0 * PT)

        def create_node(container, parent_overflow='VISIBLE'):
            if container.style is None:
                default_style = Style()
                setattr(default_style, 'width', "100%")
                setattr(default_style, 'height', "100%")
                container.style = default_style
            
            s = container.style

            # Display
            disp_str = s.display.lower()
            display_val = {'none': Display.NONE, 'flex': Display.FLEX,
                           'grid': Display.GRID, 'block': Display.BLOCK}.get(disp_str, Display.FLEX)

            # Position
            pos_str = s.position.lower()
            position_val = Position.ABSOLUTE if pos_str in ('absolute', 'fixed') else Position.RELATIVE

            # Overflow (support separate overflow-x / overflow-y)
            overflow_map = {'visible': Overflow.VISIBLE, 'hidden': Overflow.HIDDEN,
                           'scroll': Overflow.SCROLL, 'auto': Overflow.SCROLL, 'clip': Overflow.CLIP}
            overflow_x_str = (s.overflow_x if hasattr(s, 'overflow_x') and s.overflow_x else s.overflow).lower()
            overflow_y_str = (s.overflow_y if hasattr(s, 'overflow_y') and s.overflow_y else s.overflow).lower()
            overflow_x_val = overflow_map.get(overflow_x_str, Overflow.VISIBLE)
            overflow_y_val = overflow_map.get(overflow_y_str, Overflow.VISIBLE)

            # Size
            width_pct  = parse_css_value(s.width)
            height_pct = parse_css_value(s.height)

            # Min/max size
            min_w = parse_css_value_auto(s.min_width) if hasattr(s, 'min_width') else LengthPointsPercentAuto.from_any(AUTO)
            min_h = parse_css_value_auto(s.min_height) if hasattr(s, 'min_height') else LengthPointsPercentAuto.from_any(AUTO)
            max_w = parse_css_value_auto(s.max_width) if hasattr(s, 'max_width') else LengthPointsPercentAuto.from_any(AUTO)
            max_h = parse_css_value_auto(s.max_height) if hasattr(s, 'max_height') else LengthPointsPercentAuto.from_any(AUTO)

            # Inset (top, right, bottom, left) for position:absolute
            inset_top = parse_css_value_auto(s.top) if hasattr(s, 'top') else LengthPointsPercentAuto.from_any(AUTO)
            inset_right = parse_css_value_auto(s.right) if hasattr(s, 'right') else LengthPointsPercentAuto.from_any(AUTO)
            inset_bottom = parse_css_value_auto(s.bottom) if hasattr(s, 'bottom') else LengthPointsPercentAuto.from_any(AUTO)
            inset_left = parse_css_value_auto(s.left) if hasattr(s, 'left') else LengthPointsPercentAuto.from_any(AUTO)

            # Spacing
            padding_val = parse_padding_values(container)
            margin_val  = parse_margin_values(container)
            border_val  = parse_border_values(container)

            # Flex direction
            flex_dir_str = s.flex_direction.lower().replace('-', '_')
            flex_direction_map = {'row': FlexDirection.ROW, 'column': FlexDirection.COLUMN,
                                  'row_reverse': FlexDirection.ROW_REVERSE,
                                  'column_reverse': FlexDirection.COLUMN_REVERSE}
            flex_direction_val = flex_direction_map.get(flex_dir_str, FlexDirection.ROW)

            # Flex wrap
            flex_wrap_str = s.flex_wrap.lower().replace('-', '_')
            flex_wrap_map = {'no_wrap': FlexWrap.NO_WRAP, 'nowrap': FlexWrap.NO_WRAP,
                            'wrap': FlexWrap.WRAP, 'wrap_reverse': FlexWrap.WRAP_REVERSE}
            flex_wrap_val = flex_wrap_map.get(flex_wrap_str, FlexWrap.NO_WRAP)

            # Flex item properties
            flex_grow_val = float(s.flex_grow) if s.flex_grow else 0.0
            flex_shrink_val = float(s.flex_shrink) if s.flex_shrink else 1.0
            flex_basis_str = str(s.flex_basis).lower().strip()
            flex_basis_val = parse_css_value_auto(flex_basis_str)

            # CSS parity: children of overflow:scroll/auto containers don't shrink.
            # Browsers treat scroll containers as having unbounded space in the
            # scroll direction, so flex-shrink never triggers. Taffy doesn't do
            # this automatically, so we force flex_shrink=0 for direct children.
            if parent_overflow in ('SCROLL', 'AUTO'):
                flex_shrink_val = 0.0

            # Alignment
            align_items_val     = parse_align_items(s.align_items) if s.align_items else None
            align_self_val      = parse_align_self(s.align_self) if s.align_self else None
            align_content_val   = parse_align_content(s.align_content) if s.align_content else None
            justify_content_val = parse_justify_content(s.justify_content) if s.justify_content else None
            justify_items_val   = parse_justify_items(s.justify_items) if s.justify_items else None
            justify_self_val    = parse_justify_self(s.justify_self) if s.justify_self else None

            # Gap
            gap_val = parse_gap_value(s.gap) if hasattr(s, 'gap') else SizePointsPercent.from_any(0 * PT)
            if hasattr(s, 'row_gap') and s.row_gap:
                row_gap = parse_css_value(s.row_gap)
                col_gap_str = s.column_gap if hasattr(s, 'column_gap') and s.column_gap else s.gap
                col_gap = parse_css_value(col_gap_str)
                gap_val = SizePointsPercent(width=col_gap, height=row_gap)
            elif hasattr(s, 'column_gap') and s.column_gap:
                col_gap = parse_css_value(s.column_gap)
                row_gap_str = s.row_gap if hasattr(s, 'row_gap') and s.row_gap else s.gap
                row_gap = parse_css_value(row_gap_str)
                gap_val = SizePointsPercent(width=col_gap, height=row_gap)

            # Grid properties
            grid_kwargs = {}
            if disp_str == 'grid':
                grid_auto_flow_str = s.grid_auto_flow.lower().replace('-', '_') if hasattr(s, 'grid_auto_flow') and s.grid_auto_flow else 'row'
                grid_auto_flow_map = {'row': GridAutoFlow.ROW, 'column': GridAutoFlow.COLUMN,
                                      'row_dense': GridAutoFlow.ROW_DENSE,
                                      'column_dense': GridAutoFlow.COLUMN_DENSE}
                grid_kwargs['grid_auto_flow'] = grid_auto_flow_map.get(grid_auto_flow_str, GridAutoFlow.ROW)

                if hasattr(s, 'grid_template_rows') and s.grid_template_rows:
                    val = s.grid_template_rows
                    if isinstance(val, str):
                        # Split CSS value "1fr 1fr 1fr" into individual tracks
                        # but preserve "repeat(...)" and "minmax(...)" as single tokens
                        tracks = re.split(r'\s+(?![^(]*\))', val.strip())
                        grid_kwargs['grid_template_rows'] = [t for t in tracks if t]
                    else:
                        grid_kwargs['grid_template_rows'] = val
                if hasattr(s, 'grid_template_columns') and s.grid_template_columns:
                    val = s.grid_template_columns
                    if isinstance(val, str):
                        tracks = re.split(r'\s+(?![^(]*\))', val.strip())
                        grid_kwargs['grid_template_columns'] = [t for t in tracks if t]
                    else:
                        grid_kwargs['grid_template_columns'] = val
                if hasattr(s, 'grid_auto_rows') and s.grid_auto_rows:
                    val = s.grid_auto_rows
                    if isinstance(val, str):
                        tracks = re.split(r'\s+(?![^(]*\))', val.strip())
                        grid_kwargs['grid_auto_rows'] = [t for t in tracks if t]
                    else:
                        grid_kwargs['grid_auto_rows'] = val
                if hasattr(s, 'grid_auto_columns') and s.grid_auto_columns:
                    val = s.grid_auto_columns
                    if isinstance(val, str):
                        tracks = re.split(r'\s+(?![^(]*\))', val.strip())
                        grid_kwargs['grid_auto_columns'] = [t for t in tracks if t]
                    else:
                        grid_kwargs['grid_auto_columns'] = val

            # Grid child placement
            if hasattr(s, 'grid_row') and s.grid_row and s.grid_row != 'AUTO':
                grid_kwargs['grid_row'] = s.grid_row
            if hasattr(s, 'grid_column') and s.grid_column and s.grid_column != 'AUTO':
                grid_kwargs['grid_column'] = s.grid_column

            # Aspect ratio
            aspect_ratio_val = None
            if hasattr(s, 'aspect_ratio') and s.aspect_ratio and s.aspect_ratio is not True:
                try:
                    aspect_ratio_val = float(s.aspect_ratio)
                except (ValueError, TypeError):
                    pass

            # Box sizing
            box_sizing_str = s.box_sizing.lower() if hasattr(s, 'box_sizing') and s.box_sizing else 'border-box'
            box_sizing_val = BoxSizing.CONTENT if box_sizing_str in ('content_box', 'content-box') else BoxSizing.BORDER

            node = Node(
                display         = display_val,
                position        = position_val,
                box_sizing      = box_sizing_val,
                overflow_x      = overflow_x_val,
                overflow_y      = overflow_y_val,
                scrollbar_width = float(s.scrollbar_width) if hasattr(s, 'scrollbar_width') and s.scrollbar_width else 0.0,
                inset           = RectPointsPercentAuto(top=inset_top, right=inset_right, bottom=inset_bottom, left=inset_left),
                flex_direction  = flex_direction_val,
                flex_wrap       = flex_wrap_val,
                flex_grow       = flex_grow_val,
                flex_shrink     = flex_shrink_val,
                flex_basis      = flex_basis_val,
                align_items     = align_items_val,
                align_self      = align_self_val,
                align_content   = align_content_val,
                justify_content = justify_content_val,
                justify_items   = justify_items_val,
                justify_self    = justify_self_val,
                gap             = gap_val,
                key             = container.id,
                size            = (width_pct, height_pct),
                min_size        = SizePointsPercentAuto(width=min_w, height=min_h),
                max_size        = SizePointsPercentAuto(width=max_w, height=max_h),
                aspect_ratio    = aspect_ratio_val,
                padding         = padding_val,
                margin          = margin_val,
                border          = border_val,
                **grid_kwargs,
            )
            
            # Determine this container's overflow for passing to children
            this_overflow = s.overflow.upper() if hasattr(s, 'overflow') and s.overflow else 'VISIBLE'

            for child in container.children:
                child_node = create_node(child, parent_overflow=this_overflow)
                node.add(child_node)

            return node

        self.root_node = create_node(self.theme.root)
        self.root_node.compute_layout(canvas_size)
        self.canvas_size = canvas_size
        get_all_nodes(self.theme.root, self.root_node)

    def recompute_layout(self, canvas_size):
        global node_flat, node_flat_abs
        
        node_flat.clear()
        node_flat_abs.clear()
        
        self.root_node.compute_layout(canvas_size)
        self.canvas_size = canvas_size
        
        def get_all_nodes(container, node):
            border_box     = node.get_box(Edge.BORDER, relative=True)
            border_box_abs = node.get_box(Edge.BORDER, relative=False)
            
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
        container_processor = ContainerProcessor()
        
        container_dict = self._container_to_dict(self.theme.root)
        
        self.json_data = container_processor.flatten_tree(container_dict, node_flat)
        self.abs_json_data = container_processor.flatten_tree(container_dict, node_flat_abs)
        
        # Post-process: add visibility, opacity, z-index, overflow_type from Style (not in Rust struct)
        visibility_map = {}
        opacity_map = {}
        zindex_map = {}
        overflow_type_map = {}
        position_type_map = {}
        transition_map = {}
        def collect_style_props(container):
            if hasattr(container.style, 'visibility'):
                visibility_map[container.id] = container.style.visibility
            opacity_map[container.id] = float(container.style.opacity)
            zindex_map[container.id] = int(container.style.z_index)
            overflow_type_map[container.id] = container.style.overflow
            position_type_map[container.id] = container.style.position
            if hasattr(container.style, 'transition_property') and container.style.transition_duration > 0:
                transition_map[container.id] = {
                    'property': container.style.transition_property,
                    'duration': float(container.style.transition_duration),
                    'timing': container.style.transition_timing_function,
                    'delay': float(container.style.transition_delay),
                }
            for child in container.children:
                collect_style_props(child)
        collect_style_props(self.theme.root)
        
        def inject_and_sort(data_list):
            for c in data_list:
                cid = c.get('id', '')
                c['visibility'] = visibility_map.get(cid, 'VISIBLE')
                c['opacity'] = opacity_map.get(cid, 1.0)
                c['z_index'] = zindex_map.get(cid, 0)
                c['overflow_type'] = overflow_type_map.get(cid, 'VISIBLE')
                c['position_type'] = position_type_map.get(cid, 'RELATIVE')
                t_data = transition_map.get(cid)
                if t_data:
                    c['_transition_property'] = t_data['property']
                    c['_transition_duration'] = t_data['duration']
                    c['_transition_timing_function'] = t_data['timing']
                    c['_transition_delay'] = t_data['delay']
            # Sort by z-index (stable sort preserves tree order within same z)
            # Build old→new index mapping and remap parent refs
            sorted_list = sorted(enumerate(data_list), key=lambda t: t[1].get('z_index', 0))
            old_to_new = {old_idx: new_idx for new_idx, (old_idx, _) in enumerate(sorted_list)}
            result = []
            for _, c in sorted_list:
                old_parent = c.get('parent', -1)
                if old_parent >= 0 and old_parent in old_to_new:
                    c['parent'] = old_to_new[old_parent]
                children = c.get('children', [])
                c['children'] = [old_to_new[ci] for ci in children if ci in old_to_new]
                result.append(c)
            return result

        self.json_data = inject_and_sort(self.json_data)
        self.abs_json_data = inject_and_sort(self.abs_json_data)
    
    def _container_to_dict(self, container):
        def ensure_string(val):
            if isinstance(val, str):
                return val
            elif hasattr(val, 'name'):
                return val.name
            else:
                return str(val)
        
        display_str = ensure_string(container.style.display)
        overflow_str = ensure_string(container.style.overflow)
        
        container_dict = {
            'id': container.id,
            'style': {
                'id': container.style.id if hasattr(container.style, 'id') else '',
                'display': display_str,
                'overflow': overflow_str,
                'background_color': list(container.style.background_color),
                'background_color_2': list(container.style.background_color_2),
                'background_gradient_rot': float(container.style.background_gradient_rot),
                'hover_background_color': list(container.style.hover_background_color),
                'hover_background_color_2': list(container.style.hover_background_color_2),
                'hover_background_gradient_rot': float(container.style.hover_background_gradient_rot),
                'click_background_color': list(container.style.click_background_color),
                'click_background_color_2': list(container.style.click_background_color_2),
                'click_background_gradient_rot': float(container.style.click_background_gradient_rot),
                'border_color': list(container.style.border_color),
                'border_color_2': list(container.style.border_color_2),
                'border_gradient_rot': float(container.style.border_gradient_rot),
                'hover_border_color': list(container.style.hover_border_color),
                'click_border_color': list(container.style.click_border_color),
                'hover_opacity': float(container.style.hover_opacity),
                'click_opacity': float(container.style.click_opacity),
                'hover_color': list(container.style.hover_color),
                'click_color': list(container.style.click_color),
                'border_radius': float(container.style.border_radius),
                'border_radius_tl': float(container.style.border_radius_tl or container.style.border_radius),
                'border_radius_tr': float(container.style.border_radius_tr or container.style.border_radius),
                'border_radius_br': float(container.style.border_radius_br or container.style.border_radius),
                'border_radius_bl': float(container.style.border_radius_bl or container.style.border_radius),
                'border_width': float(container.style.border_width),
                'border_width_top': float(container.style.border_width_top),
                'border_width_right': float(container.style.border_width_right),
                'border_width_bottom': float(container.style.border_width_bottom),
                'border_width_left': float(container.style.border_width_left),
                'gradient_stops': str(container.style.gradient_stops),
                'hover_gradient_stops': str(container.style.hover_gradient_stops),
                'click_gradient_stops': str(container.style.click_gradient_stops),
                'color': list(container.style.color),
                'color_2': list(container.style.color_2),
                'color_gradient_rot': float(container.style.color_gradient_rot),
                'font_size': float(container.style.font_size),
                'text_x': float(container.style.text_x),
                'text_y': float(container.style.text_y),
                'box_shadow_color': list(container.style.box_shadow_color),
                'box_shadow_offset': list(container.style.box_shadow_offset),
                'box_shadow_blur': float(container.style.box_shadow_blur),
                'aspect_ratio': bool(container.style.aspect_ratio),
                'opacity': float(container.style.opacity),
            },
            'data': str(container.data),
            'img': str(container.img),
            'text': str(container.text),
            'font': str(container.style.font_family).strip().strip("'\"") if hasattr(container.style, 'font_family') and container.style.font_family else str(container.font),
            'passive': bool(container.passive) or (hasattr(container.style, 'pointer_events') and container.style.pointer_events == 'NONE'),
            'click': container.click,
            'toggle': container.toggle,
            'scroll': container.scroll,
            '_scroll_value': float(container._scroll_value),
            'hover': container.hover,
            'hoverout': container.hoverout,
            'children': [self._container_to_dict(child) for child in container.children]
        }
        return container_dict
 