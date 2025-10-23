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
import yaml
import os
from typing import Optional, Dict, Any, List, Tuple
from .native_bindings import ConfigParser
from . import get_addon_root

_parsed_config = None
_target_space = None
_space_handler_name = None

class SpaceAwareConfig:
    def __init__(self):
        self.config_parser = ConfigParser()
        self.selected_theme = None
        self.target_space = None
        self.space_handler_name = None
        self.theme_data = None
        
    def parse_config(self, conf_path: str) -> bool:
        try:
            addon_dir = get_addon_root()
            full_path = os.path.join(addon_dir, conf_path)
            
            if not os.path.exists(full_path):
                print(f"Config file not found: {full_path}")
                return False
                
            with open(full_path, 'r') as f:
                yaml_content = f.read()
            
            parse_result = self.config_parser.parse_yaml(yaml_content)
            
            selected_theme_name = parse_result.selected_theme
            target_theme = None
            
            for theme in parse_result.themes:
                if theme.name == selected_theme_name:
                    target_theme = theme
                    break
            
            if not target_theme:
                for theme in parse_result.themes:
                    if theme.name == parse_result.default_theme:
                        target_theme = theme
                        break
            
            if not target_theme and parse_result.themes:
                target_theme = parse_result.themes[0]
            
            if not target_theme:
                print("No valid theme found in config")
                return False
            
            self.selected_theme = target_theme.name
            self.theme_data = target_theme
            
            space_validation = self.config_parser.validate_space(target_theme.space)
            
            if not space_validation.is_valid:
                print(f"Invalid space configuration: {space_validation.error_message}")
                print(f"Supported spaces: {', '.join(self.config_parser.get_supported_spaces())}")
                return False
            
            self.target_space = space_validation.area_type
            self.space_handler_name = space_validation.handler_name
            
            print(f"Parsed config for theme '{self.selected_theme}' targeting space '{self.target_space}'")
            return True
            
        except Exception as e:
            print(f"Error parsing config: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_space_info(self) -> Tuple[Optional[str], Optional[str]]:
        return self.target_space, self.space_handler_name
    
    def get_theme_data(self):
        return self.theme_data

def parse_space_config(conf_path: str) -> bool:
    global _parsed_config, _target_space, _space_handler_name
    
    _parsed_config = SpaceAwareConfig()
    success = _parsed_config.parse_config(conf_path)
    
    if success:
        _target_space, _space_handler_name = _parsed_config.get_space_info()
        
        # Update panel space when configuration changes
        try:
            from . import panel
            panel.update_panel_space()
        except Exception as e:
            print(f"Failed to update panel space: {e}")
    else:
        _parsed_config = None
        _target_space = None
        _space_handler_name = None
    
    return success

def get_target_space() -> Optional[str]:
    return _target_space

def get_space_handler_name() -> Optional[str]:
    return _space_handler_name

def get_parsed_config() -> Optional[SpaceAwareConfig]:
    return _parsed_config

def is_target_space_available() -> bool:
    if not _target_space:
        return False
    
    for area in bpy.context.screen.areas:
        if area.type == _target_space:
            return True
    return False

def find_target_area_and_region():
    if not _target_space:
        return None, None
    
    for area in bpy.context.screen.areas:
        if area.type == _target_space:
            for region in area.regions:
                if region.type == 'WINDOW':
                    return area, region
    return None, None

def get_space_class():
    if not _space_handler_name:
        return None
    
    try:
        return getattr(bpy.types, _space_handler_name)
    except AttributeError:
        print(f"Unknown space handler: {_space_handler_name}")
        return None

def validate_current_configuration() -> Dict[str, Any]:
    result = {
        'config_parsed': _parsed_config is not None,
        'target_space': _target_space,
        'handler_name': _space_handler_name,
        'space_available': False,
        'area': None,
        'region': None,
        'space_class': None
    }
    
    if _parsed_config:
        result['space_available'] = is_target_space_available()
        area, region = find_target_area_and_region()
        result['area'] = area
        result['region'] = region
        result['space_class'] = get_space_class()
    
    return result