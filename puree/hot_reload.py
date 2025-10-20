"""
Hot Reload System for Puree UI
Watches for file changes and intelligently reloads the UI
"""
import os
from typing import Optional, Set, Dict, Any, Callable, List
from pathlib import Path

try:
    import bpy
except ImportError:
    bpy = None

class HotReloadManager:
    """
    Manages hot reload functionality for Puree UI system.
    Uses Rust-based file watcher for performance and integrates with the render pipeline.
    """
    
    def __init__(self):
        self.watcher: Optional[PyFileWatcher] = None
        self.enabled: bool = False
        self.addon_dir: Optional[Path] = None
        self.watched_paths: Set[Path] = set()
        self.reload_callbacks: Dict[str, list] = {
            'yaml': [],
            'style': [],
            'script': [],
            'component': [],
            'asset': []
        }
        self.last_reload_time = 0.0
        self.reload_cooldown = 0.5  # Minimum seconds between reloads
        
    def initialize(self, addon_dir: str, debounce_ms: int = 300) -> bool:
        """
        Initialize the hot reload system.
        
        Args:
            addon_dir: Root directory of the addon
            debounce_ms: Milliseconds to wait before processing file changes
            
        Returns:
            True if initialization succeeded
        """
        try:
            from .native_bindings import PyFileWatcher
            
            self.addon_dir = Path(addon_dir)
            self.watcher = PyFileWatcher(
                debounce_ms=debounce_ms,
                watch_yaml=True,
                watch_styles=True,
                watch_scripts=True
            )
            
            print(f"✓ Hot reload system initialized (debounce: {debounce_ms}ms)")
            return True
            
        except Exception as e:
            print(f"✗ Failed to initialize hot reload: {e}")
            return False
    
    def watch_directory(self, directory: str) -> bool:
        """
        Add a directory to the watch list.
        
        Args:
            directory: Path to directory to watch
            
        Returns:
            True if watching started successfully
        """
        if not self.watcher:
            print("✗ Hot reload not initialized")
            return False
        
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                print(f"✗ Directory does not exist: {directory}")
                return False
            
            print(f"📂 Attempting to watch: {dir_path}")
            result = self.watcher.watch_path(str(dir_path))
            print(f"📂 Watch result: {result}")
            
            if result:
                self.watched_paths.add(dir_path)
                print(f"👁  Watching: {dir_path}")
                return True
            else:
                print(f"✗ Failed to watch: {directory}")
                return False
                
        except Exception as e:
            print(f"✗ Error watching directory {directory}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def unwatch_directory(self, directory: str) -> bool:
        """Stop watching a directory."""
        if not self.watcher:
            return False
        
        try:
            dir_path = Path(directory)
            if self.watcher.unwatch_path(str(dir_path)):
                self.watched_paths.discard(dir_path)
                print(f"🚫 Stopped watching: {dir_path}")
                return True
            return False
        except Exception as e:
            print(f"✗ Error unwatching directory {directory}: {e}")
            return False
    
    def register_callback(self, change_type: str, callback: Callable[[Dict[str, Any]], None]):
        """
        Register a callback for specific change types.
        
        Args:
            change_type: One of 'yaml', 'style', 'script', 'component', 'asset'
            callback: Function to call when change is detected
        """
        if change_type in self.reload_callbacks:
            self.reload_callbacks[change_type].append(callback)
        else:
            print(f"✗ Unknown change type: {change_type}")
    
    def unregister_callback(self, change_type: str, callback: Callable):
        """Unregister a specific callback."""
        if change_type in self.reload_callbacks:
            try:
                self.reload_callbacks[change_type].remove(callback)
            except ValueError:
                pass
    
    def check_for_changes(self) -> bool:
        """
        Check for file changes and process them.
        
        Returns:
            True if changes were detected and processed
        """
        if not self.watcher:
            print("⚠️  Hot reload: No watcher initialized")
            return False
            
        if not self.enabled:
            print("⚠️  Hot reload: Not enabled")
            return False
        
        try:
            has_changes = self.watcher.has_changes()
            if not has_changes:
                return False
            
            print("🔍 Hot reload: Changes detected!")
            
            # Check cooldown
            import time
            current_time = time.time()
            if current_time - self.last_reload_time < self.reload_cooldown:
                print(f"⏳ Hot reload: In cooldown ({self.reload_cooldown}s)")
                return False
            
            changes = self.watcher.get_changes()
            print(f"📦 Hot reload: Got {len(changes)} changes")
            
            if not changes:
                return False
            
            # Process changes
            processed_any = False
            for change in changes:
                if self._process_change(change):
                    processed_any = True
            
            if processed_any:
                self.last_reload_time = current_time
                print("✅ Hot reload: Changes processed successfully")
            
            return processed_any
            
        except Exception as e:
            print(f"✗ Error checking for changes: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _process_change(self, change: Dict[str, Any]) -> bool:
        """
        Process a single file change event.
        
        Args:
            change: Dictionary with 'path', 'type', and 'timestamp'
            
        Returns:
            True if change was processed
        """
        change_type_str = change.get('type', '')
        path = change.get('path', '')
        
        print(f"🔄 Detected change: {change_type_str} - {path}")
        
        # Map change types to callback categories
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
            # Execute callbacks for this change type
            callbacks = self.reload_callbacks.get(callback_key, [])
            for callback in callbacks:
                try:
                    callback(change)
                except Exception as e:
                    print(f"✗ Callback error: {e}")
            
            return len(callbacks) > 0
        
        return False
    
    def enable(self):
        """Enable hot reload (start processing changes)."""
        self.enabled = True
        print("🔥 Hot reload enabled")
    
    def disable(self):
        """Disable hot reload (stop processing changes)."""
        self.enabled = False
        print("❄️  Hot reload disabled")
    
    def cleanup(self):
        """Clean up resources."""
        if self.watcher:
            for path in list(self.watched_paths):
                self.unwatch_directory(str(path))
        
        self.watcher = None
        self.watched_paths.clear()
        self.reload_callbacks = {k: [] for k in self.reload_callbacks}
        print("🧹 Hot reload cleaned up")


# Global instance
_hot_reload_manager: Optional[HotReloadManager] = None


def get_hot_reload_manager() -> HotReloadManager:
    """Get or create the global hot reload manager instance."""
    global _hot_reload_manager
    if _hot_reload_manager is None:
        _hot_reload_manager = HotReloadManager()
    return _hot_reload_manager


def setup_hot_reload(addon_dir: str, watch_dirs: Optional[List[str]] = None) -> bool:
    """
    Setup hot reload for the UI system.
    
    Args:
        addon_dir: Root addon directory
        watch_dirs: List of directories to watch (relative to addon_dir)
        
    Returns:
        True if setup succeeded
    """
    manager = get_hot_reload_manager()
    
    if not manager.initialize(addon_dir):
        return False
    
    # Default watch directories
    if watch_dirs is None:
        watch_dirs = ['examples', 'static', 'fonts']
    
    # Watch specified directories
    for watch_dir in watch_dirs:
        full_path = os.path.join(addon_dir, watch_dir)
        if os.path.exists(full_path):
            manager.watch_directory(full_path)
    
    return True


def trigger_ui_reload():
    """
    Trigger a full UI reload by re-parsing and re-rendering.
    """
    try:
        # Re-parse the UI
        wm = bpy.context.window_manager
        bpy.ops.xwz.parse_app_ui(conf_path=wm.xwz_ui_conf_path)
        
        # Update render pipeline
        from . import render
        if render._render_data and render._render_data.running:
            # Reload container data
            render._render_data.load_container_data()
            render._render_data.create_buffers_and_textures()
            
            # Update text blocks
            from . import parser_op
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
            
            # Update image blocks
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
            
            # Mark for re-render
            render._render_data.needs_texture_update = True
            render._render_data.run_compute_shader()
            
            # Redraw viewport
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
            
            print("✓ UI reloaded successfully")
            return True
            
    except Exception as e:
        print(f"✗ Failed to reload UI: {e}")
        import traceback
        traceback.print_exc()
        return False


def on_yaml_changed(change: Dict[str, Any]):
    """Callback for YAML file changes."""
    print(f"📄 YAML changed: {change['path']}")
    trigger_ui_reload()


def on_style_changed(change: Dict[str, Any]):
    """Callback for style file changes."""
    print(f"🎨 Style changed: {change['path']}")
    trigger_ui_reload()


def on_script_changed(change: Dict[str, Any]):
    """Callback for script file changes."""
    print(f"🐍 Script changed: {change['path']}")
    # Scripts require full reload including module reimport
    trigger_ui_reload()


def on_component_changed(change: Dict[str, Any]):
    """Callback for component file changes."""
    print(f"🧩 Component changed: {change['path']}")
    trigger_ui_reload()


def on_asset_changed(change: Dict[str, Any]):
    """Callback for asset file changes."""
    print(f"🖼️  Asset changed: {change['path']}")
    # Assets might just need texture reload
    trigger_ui_reload()


def register_default_callbacks():
    """Register default callbacks for hot reload."""
    manager = get_hot_reload_manager()
    
    manager.register_callback('yaml', on_yaml_changed)
    manager.register_callback('style', on_style_changed)
    manager.register_callback('script', on_script_changed)
    manager.register_callback('component', on_component_changed)
    manager.register_callback('asset', on_asset_changed)


def cleanup_hot_reload():
    """Clean up hot reload system."""
    global _hot_reload_manager
    if _hot_reload_manager:
        _hot_reload_manager.cleanup()
        _hot_reload_manager = None
