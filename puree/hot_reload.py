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
import yaml
from typing import Optional, Dict, Any, Callable, List
from pathlib import Path

try:
    import bpy
except ImportError:
    bpy = None

class HotReloadManager:
    def __init__(self):
        self.watcher = None
        self.enabled: bool = False
        self.addon_dir: Optional[Path] = None
        self.config_path: Optional[Path] = None
        self.watched_items: set = set()
        self.reload_callbacks: Dict[str, list] = {
            'yaml': [],
            'style': [],
            'script': [],
            'component': [],
            'asset': []
        }
        
    def initialize(self, addon_dir: str, config_path: str, debounce_ms: int = 300) -> bool:
        try:
            from .native_bindings import PyFileWatcher
            
            self.addon_dir = Path(addon_dir)
            
            if not Path(config_path).is_absolute():
                self.config_path = self.addon_dir / config_path
            else:
                self.config_path = Path(config_path)
            
            self.watcher = PyFileWatcher(
                debounce_ms=debounce_ms,
                watch_yaml=True,
                watch_styles=True,
                watch_scripts=True
            )
            
            print(f"Hot reload initialized (debounce: {debounce_ms}ms)")
            return True
            
        except Exception as e:
            print(f"Failed to initialize hot reload: {e}")
            return False
    
    def setup_watches_from_config(self) -> bool:
        if not self.config_path or not self.config_path.exists():
            print(f"Config file not found: {self.config_path}")
            return False
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not config or 'app' not in config:
                return False
            
            app = config['app']
            selected_theme_name = app.get('selected_theme')
            themes = app.get('theme', [])
            
            selected_theme = None
            for theme in themes:
                if theme.get('name') == selected_theme_name:
                    selected_theme = theme
                    break
            
            if not selected_theme:
                return False
            
            self._clear_watches()
            
            self.watch_file(str(self.config_path))
            
            for script_path in selected_theme.get('scripts', []):
                full_path = self.addon_dir / script_path
                if full_path.exists():
                    self.watch_file(str(full_path))
            
            for style_path in selected_theme.get('styles', []):
                full_path = self.addon_dir / style_path
                if full_path.exists():
                    self.watch_file(str(full_path))
            
            components_path = selected_theme.get('components')
            if components_path:
                full_path = self.addon_dir / components_path
                if full_path.exists() and full_path.is_dir():
                    self.watch_directory(str(full_path))
            
            print(f"Hot reload watching {len(self.watched_items)} items")
            return True
            
        except Exception as e:
            print(f"Failed to setup watches from config: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _clear_watches(self):
        if not self.watcher:
            return
        
        for item in list(self.watched_items):
            try:
                self.watcher.unwatch_path(str(item))
            except:
                pass
        self.watched_items.clear()
    
    def watch_file(self, filepath: str) -> bool:
        file_path = Path(filepath)
        if not file_path.exists():
            return False
        
        parent_dir = file_path.parent
        if self.watch_directory(str(parent_dir)):
            self.watched_items.add(file_path)
            return True
        return False
    
    def watch_directory(self, directory: str) -> bool:
        if not self.watcher:
            return False
        
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                return False
            
            if self.watcher.watch_path(str(dir_path)):
                self.watched_items.add(dir_path)
                return True
            return False
                
        except Exception as e:
            print(f"Error watching directory: {e}")
            return False
    
    def unwatch_directory(self, directory: str) -> bool:
        if not self.watcher:
            return False
        
        try:
            return self.watcher.unwatch_path(str(directory))
        except Exception as e:
            print(f"Error unwatching directory: {e}")
            return False
    
    def register_callback(self, change_type: str, callback: Callable[[Dict[str, Any]], None]):
        if change_type in self.reload_callbacks:
            self.reload_callbacks[change_type].append(callback)
        else:
            print(f"Unknown change type: {change_type}")
    
    def unregister_callback(self, change_type: str, callback: Callable):
        if change_type in self.reload_callbacks:
            try:
                self.reload_callbacks[change_type].remove(callback)
            except ValueError:
                pass
    
    def check_for_changes(self) -> bool:
        if not self.watcher or not self.enabled:
            return False
        
        try:
            if not self.watcher.has_changes():
                return False
            
            changes = self.watcher.get_changes()
            if not changes:
                return False
            
            config_changed = False
            for change in changes:
                change_path = Path(change.get('path', ''))
                
                if change_path == self.config_path:
                    config_changed = True
                
                self._process_change(change)
            
            if config_changed:
                self.setup_watches_from_config()
            
            return True
            
        except Exception as e:
            print(f"Error checking for changes: {e}")
            return False
    
    def _process_change(self, change: Dict[str, Any]):
        change_type_str = change.get('type', '')
        
        callback_key = None
        if 'Yaml' in change_type_str:
            callback_key = 'yaml'
        elif 'Style' in change_type_str:
            callback_key = 'style'
        elif 'Script' in change_type_str:
            callback_key = 'script'
        elif 'Component' in change_type_str:
            callback_key = 'component'
        elif 'Asset' in change_type_str:
            callback_key = 'asset'
        
        if callback_key:
            for callback in self.reload_callbacks.get(callback_key, []):
                try:
                    callback(change)
                except Exception as e:
                    print(f"Callback error: {e}")
    
    def enable(self):
        self.enabled = True
    
    def disable(self):
        self.enabled = False
    
    def cleanup(self):
        self._clear_watches()
        self.watcher = None
        self.reload_callbacks = {k: [] for k in self.reload_callbacks}


_hot_reload_manager: Optional[HotReloadManager] = None


def get_hot_reload_manager() -> HotReloadManager:
    global _hot_reload_manager
    if _hot_reload_manager is None:
        _hot_reload_manager = HotReloadManager()
    return _hot_reload_manager


def setup_hot_reload(addon_dir: str, config_path: str) -> bool:
    manager = get_hot_reload_manager()
    
    if not manager.initialize(addon_dir, config_path):
        return False
    
    if not manager.setup_watches_from_config():
        return False
    
    return True


def trigger_ui_reload():
    try:
        wm = bpy.context.window_manager
        bpy.ops.xwz.parse_app_ui(conf_path=wm.xwz_ui_conf_path)
        
        from . import render
        from . import parser_op
        from . import hit_op
        
        if not (render._render_data and render._render_data.running):
            return False
        
        new_data = parser_op._container_json_data
        old_data = hit_op._container_data
        
        if old_data and len(old_data) == len(new_data):
            for i in range(len(new_data)):
                runtime_keys = ['_hovered', '_prev_hovered', '_clicked', '_prev_clicked', 
                              '_toggled', '_prev_toggled', '_toggle_value', '_scroll_value']
                for key in runtime_keys:
                    if key in old_data[i]:
                        new_data[i][key] = old_data[i][key]
        
        hit_op._container_data = new_data
        
        from . import text_op
        for text_instance in text_op._text_instances:
            container_id = text_instance.container_id
            if container_id in parser_op.text_blocks:
                block = parser_op.text_blocks[container_id]
                text_instance.update_all(
                    text=block['text'],
                    font_name=block['font'],
                    size=block['text_scale'],
                    pos=[block['text_x'], block['text_y']],
                    color=block['text_color'],
                    mask=[block['mask_x'], block['mask_y'], block['mask_width'], block['mask_height']],
                    align_h=block.get('align_h', 'LEFT').upper(),
                    align_v=block.get('align_v', 'CENTER').upper()
                )
        
        from . import text_input_op
        for input_instance in text_input_op._text_input_instances:
            container_id = input_instance.container_id
            if container_id in parser_op.text_input_blocks:
                block = parser_op.text_input_blocks[container_id]
                bpy.ops.xwz.update_text_input(
                    instance_id=input_instance.id,
                    placeholder=block['placeholder'],
                    font_name=block['font'],
                    size=block['text_scale'],
                    x_pos=block['x_pos'],
                    y_pos=block['y_pos'],
                    color=block['text_color'],
                    mask_x=block['mask_x'],
                    mask_y=block['mask_y'],
                    mask_width=block['mask_width'],
                    mask_height=block['mask_height'],
                    align_h=block.get('align_h', 'LEFT').upper(),
                    align_v=block.get('align_v', 'TOP').upper()
                )
        
        from . import img_op
        for image_instance in img_op._image_instances:
            container_id = image_instance.container_id
            if container_id in parser_op.image_blocks:
                block = parser_op.image_blocks[container_id]
                image_instance.update_all(
                    image_name=block['image_name'],
                    pos=[block['x_pos'], block['y_pos']],
                    size=[block['width'], block['height']],
                    mask=[block['mask_x'], block['mask_y'], block['mask_width'], block['mask_height']],
                    aspect_ratio=block['aspect_ratio'],
                    align_h=block.get('align_h', 'LEFT').upper(),
                    align_v=block.get('align_v', 'TOP').upper(),
                    opacity=block.get('opacity', 1.0)
                )
        
        render._render_data.update_container_buffer_full(hit_op._container_data)
        render._render_data.run_compute_shader()
        
        render._render_data.texture_needs_readback = True
        render._render_data.needs_texture_update = True
        render._render_data.force_initial_draw = True
        
        from .space_config import get_target_space
        target_space = get_target_space()
        
        for area in bpy.context.screen.areas:
            if area.type == target_space:
                area.tag_redraw()
        
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == target_space:
                    for region in area.regions:
                        if region.type == 'WINDOW':
                            region.tag_redraw()
        
        return True
        
    except Exception as e:
        print(f"Failed to reload UI: {e}")
        import traceback
        traceback.print_exc()
        return False


def on_yaml_changed(change: Dict[str, Any]):
    trigger_ui_reload()


def on_style_changed(change: Dict[str, Any]):
    trigger_ui_reload()


def on_script_changed(change: Dict[str, Any]):
    trigger_ui_reload()


def on_component_changed(change: Dict[str, Any]):
    trigger_ui_reload()


def on_asset_changed(change: Dict[str, Any]):
    trigger_ui_reload()


def register_default_callbacks():
    manager = get_hot_reload_manager()
    
    manager.register_callback('yaml', on_yaml_changed)
    manager.register_callback('style', on_style_changed)
    manager.register_callback('script', on_script_changed)
    manager.register_callback('component', on_component_changed)
    manager.register_callback('asset', on_asset_changed)


def cleanup_hot_reload():
    global _hot_reload_manager
    if _hot_reload_manager:
        _hot_reload_manager.cleanup()
        _hot_reload_manager = None
