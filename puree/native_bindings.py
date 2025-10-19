import os
import sys
from typing import List, Dict, Any

current_dir = os.path.dirname(os.path.abspath(__file__))
native_binaries_dir = os.path.join(current_dir, 'native_binaries')

if native_binaries_dir not in sys.path:
    sys.path.insert(0, native_binaries_dir)

try:
    import puree_rust_core
except ImportError as e:
    print("=" * 70)
    print("❌ CRITICAL ERROR: Puree Rust Core Missing")
    print(f"Import error: {e}")
    raise RuntimeError("Puree requires the Rust core module") from e

finally:
    if native_binaries_dir in sys.path:
        sys.path.remove(native_binaries_dir)


class HitDetector:
    def __init__(self):
        self._detector = puree_rust_core.HitDetector()
    
    def load_containers(self, container_list: List[Dict[str, Any]]) -> bool:
        try:
            self._detector.load_containers(container_list)
            return True
        except Exception as e:
            print(f"❌ Error loading containers: {e}")
            return False
    
    def update_mouse(self, x: float, y: float, clicked: bool, scroll_delta: float = 0.0):
        self._detector.update_mouse(x, y, clicked, scroll_delta)
    
    def detect_hits(self) -> List[Dict[str, Any]]:
        return self._detector.detect_hits()
    
    def detect_hover(self, container_index: int) -> bool:
        return self._detector.detect_hover(container_index)
    
    def any_children_hovered(self, container_index: int) -> bool:
        return self._detector.any_children_hovered(container_index)
class ContainerProcessor:
    def __init__(self):
        self._processor = puree_rust_core.ContainerProcessor()
    
    def flatten_tree(self, root: Dict[str, Any], node_flat_abs: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self._processor.flatten_tree(root, node_flat_abs)
    
    def update_positions_bulk(
        self,
        container_indices: List[int],
        x_offsets: List[float],
        y_offsets: List[float]
    ) -> bool:
        try:
            self._processor.update_positions_bulk(container_indices, x_offsets, y_offsets)
            return True
        except Exception as e:
            print(f"❌ Error updating positions: {e}")
            return False
    
    def get_containers(self) -> List[Dict[str, Any]]:
        return self._processor.get_containers()
    
    def update_states_bulk(
        self,
        container_ids: List[str],
        hovered: List[bool],
        clicked: List[bool]
    ) -> bool:
        try:
            self._processor.update_states_bulk(container_ids, hovered, clicked)
            return True
        except Exception as e:
            print(f"❌ Error updating states: {e}")
            return False
