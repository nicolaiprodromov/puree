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
import sys
from typing import Any, Dict, List

try:
    from .log import get_logger

    logger = get_logger(__name__)
except Exception:
    import logging

    logger = logging.getLogger(__name__)

current_dir = os.path.dirname(os.path.abspath(__file__))
native_binaries_dir = os.path.join(current_dir, "native_binaries")

if native_binaries_dir not in sys.path:
    sys.path.insert(0, native_binaries_dir)

try:
    import puree_rust_core
except ImportError as e:
    logger.error(f"Import error: {e}")
    raise RuntimeError("Puree requires the core modules") from e

finally:
    if native_binaries_dir in sys.path:
        sys.path.remove(native_binaries_dir)


class HitDetector:
    def __init__(self):
        self._detector = puree_rust_core.HitDetector()

    def load_containers(self, container_list: List[Dict[str, Any]]) -> bool:
        try:
            self._detector.load_containers(self._clip_to_overflow_ancestors(container_list))
            return True
        except Exception as e:
            logger.error(f"Error loading containers: {e}")
            return False

    @staticmethod
    def _clip_to_overflow_ancestors(containers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Clip each container's hit rect to its overflow-clipping ancestors.

        The renderer clips children of overflow hidden/scroll/auto containers
        (RenderPipeline._precompute_visibility_and_clips), but the native
        detector does plain rect tests. Without this, content scrolled out of
        a scroll container would still be hoverable/clickable where nothing is
        drawn. Original dicts are never mutated — clipped containers are
        shallow-copied with substituted position/size.
        """
        n = len(containers)
        out = []
        for i, c in enumerate(containers):
            pos = c.get("position", [0, 0])
            size = c.get("size", [0, 0])
            ox, oy = float(pos[0]), float(pos[1])
            ow, oh = float(size[0]), float(size[1])
            x0, y0, x1, y1 = ox, oy, ox + ow, oy + oh

            idx = i
            for _ in range(20):
                pidx = int(containers[idx].get("parent", -1))
                if pidx < 0 or pidx >= n:
                    break
                parent = containers[pidx]
                # overflow (bool) is False for overflow:hidden; scroll/auto clip too
                if not parent.get("overflow", True) or parent.get("overflow_type", "VISIBLE") in ("SCROLL", "AUTO"):
                    pp = parent.get("position", [0, 0])
                    ps = parent.get("size", [0, 0])
                    px, py = float(pp[0]), float(pp[1])
                    x0 = max(x0, px)
                    y0 = max(y0, py)
                    x1 = min(x1, px + float(ps[0]))
                    y1 = min(y1, py + float(ps[1]))
                idx = pidx

            w = max(0.0, x1 - x0)
            h = max(0.0, y1 - y0)
            if x0 == ox and y0 == oy and w == ow and h == oh:
                out.append(c)
                continue
            clipped = dict(c)
            if w <= 0.0 or h <= 0.0:
                # Fully scrolled/clipped out — park the rect far off-screen so
                # a degenerate zero-size rect can't match an exact edge point.
                clipped["position"] = [-1.0e6, -1.0e6]
                clipped["size"] = [0.0, 0.0]
            else:
                clipped["position"] = [x0, y0]
                clipped["size"] = [w, h]
            out.append(clipped)
        return out

    def update_mouse(self, x: float, y: float, clicked: bool, scroll_delta: float = 0.0):
        self._detector.update_mouse(x, y, clicked, scroll_delta)

    def detect_hits(self) -> List[Dict[str, Any]]:
        return self._detector.detect_hits()

    def detect_hover(self, container_index: int) -> bool:
        return self._detector.detect_hover(container_index)

    def any_children_hovered(self, container_index: int) -> bool:
        return self._detector.any_children_hovered(container_index)


class CSSParser:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._parser = puree_rust_core.CSSParser()
        return cls._instance

    def parse(self, css_string: str) -> Dict[str, Dict[str, str]]:
        return self._parser.parse(css_string)

    def get_styles(self) -> Dict[str, Dict[str, str]]:
        return self._parser.get_styles()

    def get_variables(self) -> Dict[str, str]:
        return self._parser.get_variables()


class SCSSCompiler:
    _instance = None
    _cache = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._compiler = puree_rust_core.SCSSCompiler()
            cls._instance._cache = {}
        return cls._instance

    def _make_cache_key(
        self, filepath: str, namespace: str, param_overrides: Dict[str, str], component_name: str
    ) -> str:
        params_str = str(sorted(param_overrides.items())) if param_overrides else ""
        return f"{filepath}:{namespace}:{params_str}:{component_name}"

    def compile(
        self,
        scss_content: str,
        namespace: str = None,
        param_overrides: Dict[str, str] = None,
        component_name: str = None,
    ) -> str:
        return self._compiler.compile(scss_content, namespace, param_overrides, component_name)

    def compile_file(
        self, filepath: str, namespace: str = None, param_overrides: Dict[str, str] = None, component_name: str = None
    ) -> str:
        cache_key = self._make_cache_key(filepath, namespace, param_overrides, component_name)

        try:
            file_mtime = os.path.getmtime(filepath)
            if cache_key in self._cache:
                cached_mtime, cached_result = self._cache[cache_key]
                if cached_mtime >= file_mtime:
                    return cached_result
        except OSError:
            pass

        result = self._compiler.compile_file(filepath, namespace, param_overrides, component_name)

        try:
            file_mtime = os.path.getmtime(filepath)
            self._cache[cache_key] = (file_mtime, result)
        except OSError:
            pass

        return result


class ContainerProcessor:
    def __init__(self):
        self._processor = puree_rust_core.ContainerProcessor()

    def flatten_tree(self, root: Dict[str, Any], node_flat_abs: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self._processor.flatten_tree(root, node_flat_abs)

    def update_positions_bulk(
        self, container_indices: List[int], x_offsets: List[float], y_offsets: List[float]
    ) -> bool:
        try:
            self._processor.update_positions_bulk(container_indices, x_offsets, y_offsets)
            return True
        except Exception as e:
            logger.error(f"Error updating positions: {e}")
            return False

    def get_containers(self) -> List[Dict[str, Any]]:
        return self._processor.get_containers()

    def update_states_bulk(self, container_ids: List[str], hovered: List[bool], clicked: List[bool]) -> bool:
        try:
            self._processor.update_states_bulk(container_ids, hovered, clicked)
            return True
        except Exception as e:
            logger.error(f"Error updating states: {e}")
            return False


class ColorProcessor:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._processor = puree_rust_core.ColorProcessor()
        return cls._instance

    def gamma_correct(self, value: float) -> float:
        return puree_rust_core.gamma_correct(value)

    def apply_gamma_correction(self, r: float, g: float, b: float, a: float) -> List[float]:
        return list(puree_rust_core.apply_gamma_correction_py(r, g, b, a))

    def parse_color(self, color_str: str) -> List[float]:
        return list(puree_rust_core.parse_color_py(color_str))

    def interpolate_color(self, color1: List[float], color2: List[float], t: float) -> List[float]:
        return list(puree_rust_core.interpolate_color_py(color1, color2, t))

    def rotate_gradient(
        self,
        color1: List[float],
        color2: List[float],
        rotation_deg: float,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> List[float]:
        return list(puree_rust_core.rotate_gradient_py(color1, color2, rotation_deg, x, y, width, height))

    def process_colors_batch(self, colors: List[tuple]) -> List[List[float]]:
        return [list(c) for c in self._processor.process_colors_batch(colors)]


class PyFileWatcher:
    def __init__(
        self, debounce_ms: int = 300, watch_yaml: bool = True, watch_styles: bool = True, watch_scripts: bool = True
    ):
        self._watcher = puree_rust_core.PyFileWatcher(debounce_ms, watch_yaml, watch_styles, watch_scripts)

    def watch_path(self, path: str) -> bool:
        return self._watcher.watch_path(path)

    def unwatch_path(self, path: str) -> bool:
        return self._watcher.unwatch_path(path)

    def has_changes(self) -> bool:
        return self._watcher.has_changes()

    def get_changes(self) -> List[Dict[str, Any]]:
        return self._watcher.get_changes()

    def clear_changes(self):
        self._watcher.clear_changes()


class ConfigParser:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._parser = puree_rust_core.ConfigParser()
        return cls._instance

    def parse_yaml(self, yaml_content: str):
        return self._parser.parse_yaml(yaml_content)

    def validate_space(self, space_name: str = None):
        return self._parser.validate_space(space_name)

    def get_supported_spaces(self) -> List[str]:
        return self._parser.get_supported_spaces()


class CSSCascade:
    def __init__(self):
        self._cascade = puree_rust_core.CSSCascade()

    def parse_css(self, css_string: str):
        self._cascade.parse_css(css_string)

    def resolve(self, containers: list, state: str = "normal", viewport=None) -> Dict[str, Dict[str, str]]:
        return self._cascade.resolve(containers, state, viewport)
