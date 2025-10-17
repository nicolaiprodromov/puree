"""
Native Core Integration Module

This module provides Python wrappers and utilities for interfacing with
the native-compiled performance-critical components.
"""

import os
import sys
from typing import List, Dict, Any, Optional

# Try to import the native module from native_binaries directory
NATIVE_AVAILABLE = False
puree_native_core = None

try:
    # Get the directory where this file is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    native_binaries_dir = os.path.join(current_dir, 'native_binaries')
    
    # Add native_binaries to Python path temporarily
    if native_binaries_dir not in sys.path:
        sys.path.insert(0, native_binaries_dir)
    
    # Try to import the module
    import puree_rust_core as puree_native_core
    NATIVE_AVAILABLE = True
    
    # Remove from path to keep it clean
    if native_binaries_dir in sys.path:
        sys.path.remove(native_binaries_dir)
        
except ImportError as e:
    NATIVE_AVAILABLE = False
    print("Warning: Native core module not available. Falling back to Python implementation.")
    print("To build the native module, run: cd puree/hit_core && ./build.sh")
    print(f"Debug: Import error was: {e}")

class NativeHitDetector:
    """
    Wrapper for native-compiled hit detection.
    Provides seamless fallback to Python if native module is not available.
    """
    
    def __init__(self):
        self.use_native = NATIVE_AVAILABLE
        self._detector = None
        
        if self.use_native:
            try:
                self._detector = puree_native_core.HitDetector()
            except Exception as e:
                print(f"Failed to initialize native hit detector: {e}")
                self.use_native = False
    
    def load_containers(self, container_list: List[Dict[str, Any]]) -> bool:
        """Load container data into the detector"""
        if not self.use_native or self._detector is None:
            return False
        
        try:
            self._detector.load_containers(container_list)
            return True
        except Exception as e:
            print(f"Error loading containers into native detector: {e}")
            return False
    
    def update_mouse(self, x: float, y: float, clicked: bool, scroll_delta: float = 0.0):
        """Update mouse state"""
        if self.use_native and self._detector is not None:
            try:
                self._detector.update_mouse(x, y, clicked, scroll_delta)
            except Exception as e:
                print(f"Error updating mouse state: {e}")
    
    def detect_hits(self) -> Optional[List[Dict[str, Any]]]:
        """
        Perform hit detection and return results.
        Returns None if native module is not available or an error occurs.
        """
        if not self.use_native or self._detector is None:
            return None
        
        try:
            return self._detector.detect_hits()
        except Exception as e:
            print(f"Error during hit detection: {e}")
            return None
    
    def detect_hover(self, container_index: int) -> bool:
        """Check if specific container is hovered"""
        if not self.use_native or self._detector is None:
            return False
        
        try:
            return self._detector.detect_hover(container_index)
        except Exception as e:
            print(f"Error detecting hover: {e}")
            return False
    
    def any_children_hovered(self, container_index: int) -> bool:
        """Check if any children of container are hovered"""
        if not self.use_native or self._detector is None:
            return False
        
        try:
            return self._detector.any_children_hovered(container_index)
        except Exception as e:
            print(f"Error checking children hover: {e}")
            return False


class NativeContainerProcessor:
    """
    Wrapper for native-compiled container data processing.
    """
    
    def __init__(self):
        self.use_native = NATIVE_AVAILABLE
        self._processor = None
        
        if self.use_native:
            try:
                self._processor = puree_native_core.ContainerProcessor()
            except Exception as e:
                print(f"Failed to initialize native container processor: {e}")
                self.use_native = False
    
    def flatten_tree(self, root: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Flatten container tree"""
        if not self.use_native or self._processor is None:
            return None
        
        try:
            return self._processor.flatten_tree(root)
        except Exception as e:
            print(f"Error flattening tree: {e}")
            return None
    
    def update_positions_bulk(
        self,
        container_indices: List[int],
        x_offsets: List[float],
        y_offsets: List[float]
    ) -> bool:
        """Update multiple container positions at once"""
        if not self.use_native or self._processor is None:
            return False
        
        try:
            self._processor.update_positions_bulk(container_indices, x_offsets, y_offsets)
            return True
        except Exception as e:
            print(f"Error updating positions: {e}")
            return False
    
    def get_containers(self) -> Optional[List[Dict[str, Any]]]:
        """Get all containers"""
        if not self.use_native or self._processor is None:
            return None
        
        try:
            return self._processor.get_containers()
        except Exception as e:
            print(f"Error getting containers: {e}")
            return None
    
    def update_states_bulk(
        self,
        container_ids: List[str],
        hovered: List[bool],
        clicked: List[bool]
    ) -> bool:
        """Update multiple container states at once"""
        if not self.use_native or self._processor is None:
            return False
        
        try:
            self._processor.update_states_bulk(container_ids, hovered, clicked)
            return True
        except Exception as e:
            print(f"Error updating states: {e}")
            return False


def detect_hover_batch(
    containers: List[Dict[str, Any]],
    mouse_x: float,
    mouse_y: float
) -> List[str]:
    """
    Batch hover detection for all containers.
    Returns list of hovered container IDs.
    Falls back to Python if native module not available.
    """
    if NATIVE_AVAILABLE:
        try:
            return puree_native_core.detect_hover_batch(containers, mouse_x, mouse_y)
        except Exception as e:
            print(f"Error in native hover batch: {e}")
    
    # Python fallback
    hovered = []
    for container in containers:
        pos = container['position']
        size = container['size']
        if (mouse_x >= pos[0] and mouse_x <= pos[0] + size[0] and
            mouse_y >= pos[1] and mouse_y <= pos[1] + size[1]):
            hovered.append(container['id'])
    return hovered


def detect_clicks_batch(
    containers: List[Dict[str, Any]],
    mouse_x: float,
    mouse_y: float,
    is_clicked: bool
) -> Dict[str, bool]:
    """
    Batch click detection for all containers.
    Returns dict of {container_id: is_clicked}.
    Falls back to Python if native module not available.
    """
    if NATIVE_AVAILABLE:
        try:
            return puree_native_core.detect_clicks_batch(containers, mouse_x, mouse_y, is_clicked)
        except Exception as e:
            print(f"Error in native click batch: {e}")
    
    # Python fallback
    if not is_clicked:
        return {}
    
    clicked = {}
    for container in containers:
        if container.get('passive', False):
            continue
        pos = container['position']
        size = container['size']
        if (mouse_x >= pos[0] and mouse_x <= pos[0] + size[0] and
            mouse_y >= pos[1] and mouse_y <= pos[1] + size[1]):
            clicked[container['id']] = True
    return clicked


def is_native_available() -> bool:
    """Check if native core module is available"""
    return NATIVE_AVAILABLE


def get_native_info() -> Dict[str, Any]:
    """Get information about native module status"""
    return {
        'available': NATIVE_AVAILABLE,
        'module_path': os.path.dirname(__file__) if NATIVE_AVAILABLE else None,
        'version': getattr(puree_native_core, '__version__', 'unknown') if NATIVE_AVAILABLE else None,
    }
