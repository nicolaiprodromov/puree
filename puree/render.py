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
import time
from collections import deque

import bpy
import gpu
import moderngl as mgl
import numpy as np

from .components.container import container_default
from .log import get_logger

logger = get_logger(__name__)

from bpy.types import Operator
from gpu_extras.batch import batch_for_shader

from . import parser_op
from .input_router import input_router
from .mouse_op import XWZ_OT_mouse, XWZ_OT_mouse_launch, mouse_state
from .parser_op import XWZ_OT_ui_parser
from .scroll_op import XWZ_OT_scroll, XWZ_OT_scroll_launch, scroll_state

_render_data = None
_modal_timer = None
_hot_reload_enabled = False
_modal_generation = 0

CONTAINER_STRIDE = 68


class RenderPipeline:
    def __init__(self):
        self.mgl_context = None
        self.compute_shader = None
        self.outline_shader = None
        self.mouse_buffer = None
        self.container_buffer = None
        self.viewport_buffer = None
        self.output_texture = None
        self.outline_texture = None
        self.debug_outline_buffer = None
        self.debug_outline_count_buffer = None
        self.draw_handler = None
        self.running = False
        self.debug_outlined_containers = set()
        self.mouse_pos = [0.5, 0.5]
        self.start_time = time.time()
        self.texture_size = (1920, 1080)
        self.click_value = 0.0
        self.scroll_callback_registered = False
        self.mouse_callback_registered = False
        self.region_size = (1, 1)
        self.container_data = []
        self.frame_times = deque(maxlen=60)
        self.compute_fps = 0.0
        self.last_frame_time = time.perf_counter()
        self.needs_texture_update = True
        self.last_mouse_pos = [0.5, 0.5]
        self.last_click_value = 0.0
        self.last_scroll_value = 0.0
        self.click_frames_remaining = 0
        self._prev_container_states = {}
        self._current_hover_index = -1
        self._current_click_index = -1
        self.last_container_update = 0
        self.conf_path = "xwz.ui.toml"
        self.force_initial_draw = True
        self.native_shader = None
        self.native_batch = None
        self.data_texture = None
        self.gradient_texture = None
        self._gradient_row_map = {}
        self.container_count = 0
        self._data_needs_update = True
        self._hot_reload_frame_counter = 0

        from .transition_manager import TransitionManager

        self.transitions = TransitionManager()
        self._hot_reload_check_interval = 30
        self._cached_target_area = None
        self._cached_target_region = None
        self._cached_target_space = None
        self._area_cache_valid = False
        self._scroll_offsets = {}
        self._original_positions = {}
        self._container_id_to_index = {}
        self._content_bounds = {}
        self._scroll_accumulation = []
        self._scroll_pixels_per_tick = 40.0
        self._scroll_changed = False
        self._original_text_positions = {}
        self._original_image_positions = {}
        self._original_text_input_positions = {}
        self._vis_clips = []

    def _safe_release_moderngl_object(self, obj):
        if obj and hasattr(obj, "mglo"):
            try:
                if type(obj.mglo).__name__ != "InvalidObject":
                    obj.release()
                return True
            except Exception:
                logger.debug("Failed to release ModernGL resource", exc_info=True)
                return False
        return False

    def _write_container_buffer(self, data_bytes):
        if not self.container_buffer:
            return
        need = len(data_bytes)
        if need != self.container_buffer.size:
            self._safe_release_moderngl_object(self.container_buffer)
            self.container_buffer = self.mgl_context.buffer(data_bytes)
        else:
            self.container_buffer.write(data_bytes)

    def load_shader_file(self, filename):
        package_dir = os.path.dirname(os.path.abspath(__file__))
        shader_path = os.path.join(package_dir, "shaders", filename)
        try:
            with open(shader_path, "r") as f:
                return f.read()
        except Exception:
            logger.warning("Failed to read shader source", exc_info=True)
            return None

    def load_container_data(self):
        try:
            wm = bpy.context.window_manager
            bpy.ops.xwz.parse_app_ui(conf_path=wm.xwz_ui_conf_path)
            self.container_data = parser_op._container_json_data
            return True
        except Exception:
            logger.error("Failed to load container data", exc_info=True)
            return False

    def init_moderngl_context(self):
        try:
            self.mgl_context = mgl.get_context()
            self.mgl_context.gc_mode = "context_gc"
            return True
        except Exception:
            logger.error("Failed to initialize ModernGL context", exc_info=True)
            return False

    def create_compute_shader(self):
        shader_source = self.load_shader_file("container.glsl")
        if not shader_source:
            return False
        try:
            self.compute_shader = self.mgl_context.compute_shader(shader_source)
            return True
        except Exception:
            logger.error("Failed to create compute shader", exc_info=True)
            return False

    def create_outline_shader(self):
        shader_source = self.load_shader_file("outline.glsl")
        if not shader_source:
            return False
        try:
            self.outline_shader = self.mgl_context.compute_shader(shader_source)
            return True
        except Exception:
            logger.error("Failed to create outline shader", exc_info=True)
            return False

    def create_buffers_and_textures(self):
        try:
            mouse_data = np.array([0.5, 0.5, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)
            self.mouse_buffer = self.mgl_context.buffer(mouse_data.tobytes())

            container_array = []
            for i, container in enumerate(self.container_data):
                container_array.extend(self._build_container_struct(container))

            container_data_np = np.array(container_array, dtype=np.float32)
            self.container_buffer = self.mgl_context.buffer(container_data_np.tobytes())

            viewport_data = np.array(
                [self.region_size[0], self.region_size[1], len(self.container_data), -1.0, -1.0], dtype=np.float32
            )
            self.viewport_buffer = self.mgl_context.buffer(viewport_data.tobytes())

            self.texture_size = self.region_size

            self.output_texture = self.mgl_context.texture(self.texture_size, 4)
            self.output_texture.filter = (mgl.NEAREST, mgl.NEAREST)

            self.outline_texture = self.mgl_context.texture(self.texture_size, 4)
            self.outline_texture.filter = (mgl.NEAREST, mgl.NEAREST)

            self.debug_outline_buffer = self.mgl_context.buffer(reserve=400)

            outline_count = np.array([0], dtype=np.int32)
            self.debug_outline_count_buffer = self.mgl_context.buffer(outline_count.tobytes())

            return True
        except Exception:
            logger.error("Failed to create buffers and textures", exc_info=True)
            return False

    def create_native_shader(self):
        vert_source = self.load_shader_file("container_draw.vert")
        frag_source = self.load_shader_file("container_draw.frag")

        if not (vert_source and frag_source):
            return False

        try:
            shader_info = gpu.types.GPUShaderCreateInfo()

            shader_info.vertex_in(0, "FLOAT", "containerIdx")
            shader_info.vertex_in(1, "VEC2", "quadCorner")

            shader_info.push_constant("FLOAT", "viewportWidth")
            shader_info.push_constant("FLOAT", "viewportHeight")
            shader_info.push_constant("FLOAT", "hoverIndex")
            shader_info.push_constant("FLOAT", "clickIndex")

            shader_info.sampler(0, "FLOAT_2D", "containerData")
            shader_info.sampler(1, "FLOAT_2D", "gradientTex")

            shader_info.push_constant("FLOAT", "gradTexHeight")

            interface = gpu.types.GPUStageInterfaceInfo("container_interface")
            interface.flat("FLOAT", "vContainerIdx")
            interface.smooth("VEC2", "vPixelPos")
            shader_info.vertex_out(interface)

            shader_info.fragment_out(0, "VEC4", "fragColor")

            shader_info.vertex_source(vert_source)
            shader_info.fragment_source(frag_source)

            self.native_shader = gpu.shader.create_from_info(shader_info)
            return True
        except Exception:
            logger.error("Failed to create native shader", exc_info=True)
            return False

    def create_container_batch(self, count):
        if not self.native_shader or count <= 0:
            return False

        try:
            vertices_idx = []
            vertices_corner = []
            indices = []

            for i in range(count):
                base_v = i * 4
                for cx, cy in [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]:
                    vertices_idx.append(float(i))
                    vertices_corner.append((cx, cy))
                indices.extend(
                    [
                        (base_v, base_v + 1, base_v + 2),
                        (base_v, base_v + 2, base_v + 3),
                    ]
                )

            self.native_batch = batch_for_shader(
                self.native_shader,
                "TRIS",
                {"containerIdx": vertices_idx, "quadCorner": vertices_corner},
                indices=indices,
            )
            self.container_count = count
            return True
        except Exception:
            logger.error("Failed to create container batch", exc_info=True)
            return False

    def _pack_container_data_texture(self, containers):
        n = len(containers)
        data = np.zeros(n * 68, dtype=np.float32)

        self._vis_clips = self._precompute_visibility_and_clips(containers)

        for i, container in enumerate(containers):
            struct = self._build_container_struct(container)
            v, cx, cy, cw, ch, acc_opacity = self._vis_clips[i]
            struct[54] = v
            struct[55] = cx
            struct[56] = cy
            struct[57] = cw
            struct[58] = ch
            struct[59] = acc_opacity

            offset = i * 68
            data[offset : offset + 68] = struct

        return data

    def create_data_texture(self, containers):
        n = len(containers)
        if n == 0:
            return False

        try:
            self._build_gradient_texture(containers)

            data = self._pack_container_data_texture(containers)
            tex_width = n * 17

            buf = gpu.types.Buffer("FLOAT", len(data), data)
            self.data_texture = gpu.types.GPUTexture(
                (tex_width, 1),
                format="RGBA32F",
                data=buf,
            )
            self._data_needs_update = False
            return True
        except Exception:
            logger.error("Failed to create data texture", exc_info=True)
            return False

    def update_data_texture(self, containers):
        if self.data_texture:
            try:
                del self.data_texture
            except Exception:
                pass
            self.data_texture = None

        n = len(containers)
        if n != self.container_count:
            self.create_container_batch(n)

        return self.create_data_texture(containers)

    def update_mouse_position(self, mouse_x, mouse_y):
        self.mouse_pos[0] = max(0.0, min(1.0, mouse_x))
        self.mouse_pos[1] = max(0.0, min(1.0, 1.0 - mouse_y))
        self.write_mouse_buffer()

    def update_region_size(self, width, height):
        w = max(1, int(width))
        h = max(1, int(height))
        old_region_size = self.region_size
        self.region_size = (w, h)

        size_changed = old_region_size != self.region_size

        if size_changed:
            from . import hit_op, img_op, text_input_op, text_op

            hit_op._cached_viewport_size = None
            text_op._cached_viewport_height = None
            img_op._cached_viewport_height = None
            text_input_op._cached_viewport_height = None

            updated_container_data = parser_op.recompute_layout((w, h))

            if updated_container_data:
                self.container_data = updated_container_data

                self.update_data_texture(self.container_data)

                if self.container_buffer:
                    container_array = []
                    for i, container in enumerate(self.container_data):
                        container_array.extend(self._build_container_struct(container))
                    container_data_np = np.array(container_array, dtype=np.float32)
                    self._write_container_buffer(container_data_np.tobytes())

        if self.viewport_buffer:
            viewport_data = np.array(
                [w, h, len(self.container_data), float(self._current_hover_index), float(self._current_click_index)],
                dtype=np.float32,
            )
            self.viewport_buffer.write(viewport_data.tobytes())

        if size_changed and self.output_texture:
            if self._safe_release_moderngl_object(self.output_texture):
                self.texture_size = self.region_size
                self.output_texture = self.mgl_context.texture(self.texture_size, 4)
                self.output_texture.filter = (mgl.NEAREST, mgl.NEAREST)

        return size_changed

    def update_click_value(self, value):
        self.click_value = value
        self.write_mouse_buffer()

    def on_scroll(self, delta, absolute_value):
        from . import hit_op

        containers = hit_op._container_data
        if not containers:
            self.write_mouse_buffer()
            return

        hovered_idx = -1
        for i, c in enumerate(containers):
            if c.get("_hovered", False):
                hovered_idx = i

        if hovered_idx < 0:
            hovered_idx = self._current_hover_index

        if hovered_idx >= 0:
            scrollable_idx = self._find_scrollable_ancestor(hovered_idx, containers)
            if scrollable_idx >= 0:
                offset = self._scroll_offsets.get(scrollable_idx, [0.0, 0.0])
                pixel_delta = delta * self._scroll_pixels_per_tick
                offset[1] = offset[1] + pixel_delta

                bounds = self._content_bounds.get(scrollable_idx)
                if bounds:
                    container_size = containers[scrollable_idx].get("size", [0, 0])
                    max_scroll_y = max(0.0, bounds[1] - float(container_size[1]))
                    offset[1] = max(0.0, min(offset[1], max_scroll_y))

                self._scroll_offsets[scrollable_idx] = offset

                if self._apply_scroll_to_containers(containers):
                    from . import parser_op

                    self._apply_scroll_to_text(parser_op.text_blocks)
                    self._apply_scroll_to_images(parser_op.image_blocks)
                    self._apply_scroll_to_text_inputs(parser_op.text_input_blocks)
                    self._scroll_changed = True

        self.write_mouse_buffer()

    def on_mouse_event(self, event_type, data):
        if event_type == "mouse":
            self.mouse_pos[0] = max(0.0, min(1.0, (data[0] + 1.0) / 2.0))
            self.mouse_pos[1] = max(0.0, min(1.0, (data[1] + 1.0) / 2.0))
        elif event_type == "click":
            self.click_value = 1.0 if data else 0.0
        self.write_mouse_buffer()

    def write_mouse_buffer(self):
        if not self.mouse_buffer:
            return
        current_time = time.time() - self.start_time
        scroll_value = float(scroll_state.scroll_value)
        mouse_data = np.array(
            [self.mouse_pos[0], self.mouse_pos[1], current_time, scroll_value, self.click_value, 0.0], dtype=np.float32
        )
        self.mouse_buffer.write(mouse_data.tobytes())

    def update_fps(self):
        current_time = time.perf_counter()
        frame_time = current_time - self.last_frame_time
        self.last_frame_time = current_time

        self.frame_times.append(frame_time)

        if len(self.frame_times) > 0:
            avg_frame_time = sum(self.frame_times) / len(self.frame_times)
            self.compute_fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0.0

    def check_if_changed(self):
        changed = False

        if self.force_initial_draw:
            self.force_initial_draw = False
            changed = True

        if self.needs_texture_update:
            self.needs_texture_update = False
            changed = True

        return changed

    def update_debug_outline_buffers(self):
        if not self.debug_outline_buffer or not self.debug_outline_count_buffer:
            return

        outlined_ids = [int(cid) for cid in self.debug_outlined_containers]

        outline_count = np.array([len(outlined_ids)], dtype=np.int32)
        self.debug_outline_count_buffer.write(outline_count.tobytes())

        if len(outlined_ids) > 0:
            outline_data = np.array(outlined_ids, dtype=np.int32)
            self.debug_outline_buffer.write(outline_data.tobytes())

    def run_compute_shader(self):
        if not (
            self.compute_shader
            and self.mouse_buffer
            and self.container_buffer
            and self.viewport_buffer
            and self.output_texture
        ):
            return False

        try:
            self.mouse_buffer.bind_to_storage_buffer(0)
            self.container_buffer.bind_to_storage_buffer(1)
            self.viewport_buffer.bind_to_storage_buffer(2)
            self.output_texture.bind_to_image(4, read=False, write=True)

            groups_x = (self.texture_size[0] + 15) // 16
            groups_y = (self.texture_size[1] + 15) // 16

            self.compute_shader.run(groups_x, groups_y, 1)

            if self.outline_shader and len(self.debug_outlined_containers) > 0:
                self.update_debug_outline_buffers()

                self.output_texture.bind_to_image(0, read=True, write=False)
                self.outline_texture.bind_to_image(1, read=False, write=True)
                self.container_buffer.bind_to_storage_buffer(2)
                self.viewport_buffer.bind_to_storage_buffer(3)
                self.debug_outline_buffer.bind_to_storage_buffer(4)
                self.debug_outline_count_buffer.bind_to_storage_buffer(5)

                self.outline_shader.run(groups_x, groups_y, 1)

                temp = self.output_texture
                self.output_texture = self.outline_texture
                self.outline_texture = temp

            return True
        except Exception:
            logger.error("Failed to run compute shader", exc_info=True)
            return False

    def initialize(self):
        from .space_config import find_target_area_and_region

        area, region = find_target_area_and_region()
        if area and region:
            self.region_size = (region.width, region.height)
        else:
            logger.warning("Target space not found, using fallback size")
            self.region_size = (800, 600)

        if not self.load_container_data():
            return False

        if not self.init_moderngl_context():
            pass
        if self.mgl_context:
            self.create_compute_shader()
            self.create_outline_shader()
            self.create_buffers_and_textures()

        if not self.create_native_shader():
            return False
        if not self.create_container_batch(len(self.container_data)):
            return False
        if not self.create_data_texture(self.container_data):
            return False

        self._cache_original_positions(self.container_data)
        self._cache_original_text_positions(parser_op.text_blocks)
        if hasattr(parser_op, "image_blocks"):
            self._cache_original_image_positions(parser_op.image_blocks)
        if hasattr(parser_op, "text_input_blocks"):
            self._cache_original_text_input_positions(parser_op.text_input_blocks)

        scroll_state.register_callback(self.on_scroll)
        self.scroll_callback_registered = True

        mouse_state.register_callback(self.on_mouse_event)
        self.mouse_callback_registered = True

        self.running = True
        self.write_mouse_buffer()

        self.needs_texture_update = True

        self.add_drawing_callback()

        return True

    def add_drawing_callback(self):
        from .space_config import get_space_class

        space_class = get_space_class()
        if not space_class:
            logger.warning("No valid space class found, falling back to SpaceView3D")
            space_class = bpy.types.SpaceView3D

        self.draw_handler = space_class.draw_handler_add(self.draw_texture, (), "WINDOW", "POST_PIXEL")

    def _draw_scrollbars(self):
        from . import hit_op

        containers = hit_op._container_data if hit_op._container_data else self.container_data
        if not containers:
            return

        DEFAULT_BAR_W = 6.0
        DEFAULT_THUMB = (1.0, 1.0, 1.0, 0.35)
        DEFAULT_TRACK = (1.0, 1.0, 1.0, 0.08)
        THUMB_MIN_H = 20.0
        MARGIN = 2.0
        n = len(containers)

        vw = float(self.region_size[0])
        vh = float(self.region_size[1])

        scroll_indices = set()
        for i, c in enumerate(containers):
            if c.get("display", False) and c.get("overflow_type", "VISIBLE") in ("SCROLL", "AUTO"):
                scroll_indices.add(i)

        groups = []

        for i in scroll_indices:
            c = containers[i]

            sbw = c.get("scrollbar_width", None)
            if sbw is not None and sbw == 0.0:
                continue
            bar_w = sbw if sbw else DEFAULT_BAR_W

            pos = c.get("position", [0, 0])
            sz = c.get("size", [0, 0])
            cx, cy = float(pos[0]), float(pos[1])
            cw, ch = float(sz[0]), float(sz[1])
            if cw <= 0 or ch <= 0:
                continue

            bw_r = float(c.get("border_width_right", 0.0) or c.get("border_width", 0.0))
            bw_t = float(c.get("border_width_top", 0.0) or c.get("border_width", 0.0))
            bw_b = float(c.get("border_width_bottom", 0.0) or c.get("border_width", 0.0))

            inner_x = cx + cw - bw_r
            inner_y = cy + bw_t
            inner_h = ch - bw_t - bw_b

            if inner_h <= 0:
                continue

            bounds = self._content_bounds.get(i)
            content_h = bounds[1] if bounds else 0.0
            if content_h <= ch:
                continue

            nesting_depth = 0
            pidx = int(c.get("parent", -1))
            for _ in range(20):
                if pidx < 0 or pidx >= n:
                    break
                if pidx in scroll_indices:
                    nesting_depth += 1
                pidx = int(containers[pidx].get("parent", -1))

            track_x = inner_x - MARGIN - bar_w - nesting_depth * (bar_w + MARGIN)

            offset = self._scroll_offsets.get(i, [0.0, 0.0])
            scroll_y = offset[1]

            thumb_ratio = inner_h / content_h
            thumb_h = max(THUMB_MIN_H, inner_h * thumb_ratio)
            scroll_max = content_h - ch
            scroll_pct = scroll_y / scroll_max if scroll_max > 0 else 0.0
            thumb_y = inner_y + scroll_pct * (inner_h - thumb_h)

            raw_thumb = c.get("scrollbar_thumb_color", None)
            raw_track = c.get("scrollbar_track_color", None)
            thumb_col = tuple(raw_thumb) if raw_thumb else DEFAULT_THUMB
            track_col = tuple(raw_track) if raw_track else DEFAULT_TRACK

            rects = []
            rects.append((track_x, inner_y, bar_w, inner_h, track_col))
            rects.append((track_x, thumb_y, bar_w, thumb_h, thumb_col))

            if i < len(self._vis_clips):
                vis, clip_x, clip_y, clip_w, clip_h, _ = self._vis_clips[i]
                if vis == 0.0:
                    continue
                scr_clip_x = int(clip_x)
                scr_clip_y = int(vh - clip_y - clip_h)
                scr_clip_w = int(clip_w)
                scr_clip_h = int(clip_h)
            else:
                scr_clip_x, scr_clip_y = 0, 0
                scr_clip_w, scr_clip_h = int(vw), int(vh)

            groups.append(((scr_clip_x, scr_clip_y, scr_clip_w, scr_clip_h), rects))

        if not groups:
            return

        saved_blend = gpu.state.blend_get()
        saved_depth = gpu.state.depth_test_get()

        shader = gpu.shader.from_builtin("UNIFORM_COLOR")
        shader.bind()
        gpu.state.blend_set("ALPHA")
        gpu.state.depth_test_set("NONE")

        for clip_rect, rects in groups:
            gpu.state.scissor_test_set(True)
            gpu.state.scissor_set(clip_rect[0], clip_rect[1], clip_rect[2], clip_rect[3])

            for rx, ry, rw, rh, col in rects:
                x0 = rx
                y0 = vh - ry - rh
                x1 = rx + rw
                y1 = vh - ry

                verts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
                shader.uniform_float("color", col)
                batch = batch_for_shader(shader, "TRI_FAN", {"pos": verts})
                batch.draw(shader)

        gpu.state.scissor_test_set(False)
        gpu.state.blend_set(saved_blend)
        gpu.state.depth_test_set(saved_depth)

    def _draw_debug_overlay(self):
        if not self.debug_outlined_containers:
            return

        from . import hit_op

        containers = hit_op._container_data if hit_op._container_data else self.container_data
        if not containers:
            return

        selected_id = next(iter(self.debug_outlined_containers))
        try:
            idx = int(selected_id)
        except (ValueError, TypeError):
            return
        if idx < 0 or idx >= len(containers):
            return

        c = containers[idx]
        if not c.get("display", False):
            return

        pos = c.get("position", [0, 0])
        sz = c.get("size", [0, 0])
        cx, cy_css = float(pos[0]), float(pos[1])
        cw, ch = float(sz[0]), float(sz[1])
        if cw <= 0 or ch <= 0:
            return

        vw = float(self.region_size[0])
        vh = float(self.region_size[1])

        sx = cx
        sy = vh - cy_css - ch

        shader = gpu.shader.from_builtin("UNIFORM_COLOR")
        shader.bind()

        saved_blend = gpu.state.blend_get()
        gpu.state.blend_set("ALPHA")

        overlay_color = (0.0, 0.0, 0.0, 0.7)

        try:
            overlay_alpha = bpy.context.window_manager.xwz_debug_passepartout
            overlay_color = (0.0, 0.0, 0.0, overlay_alpha)
        except Exception:
            pass

        try:
            bc = bpy.context.window_manager.xwz_debug_border_color
            border_color = (bc[0], bc[1], bc[2], 1.0)
        except Exception:
            border_color = (0.1, 0.15, 0.4, 1.0)

        if sy > 0:
            verts = [(0, 0), (vw, 0), (vw, sy), (0, sy)]
            shader.uniform_float("color", overlay_color)
            batch_for_shader(shader, "TRI_FAN", {"pos": verts}).draw(shader)

        top_y = sy + ch
        if top_y < vh:
            verts = [(0, top_y), (vw, top_y), (vw, vh), (0, vh)]
            shader.uniform_float("color", overlay_color)
            batch_for_shader(shader, "TRI_FAN", {"pos": verts}).draw(shader)

        if sx > 0:
            verts = [(0, sy), (sx, sy), (sx, top_y), (0, top_y)]
            shader.uniform_float("color", overlay_color)
            batch_for_shader(shader, "TRI_FAN", {"pos": verts}).draw(shader)

        right_x = sx + cw
        if right_x < vw:
            verts = [(right_x, sy), (vw, sy), (vw, top_y), (right_x, top_y)]
            shader.uniform_float("color", overlay_color)
            batch_for_shader(shader, "TRI_FAN", {"pos": verts}).draw(shader)

        border_w = 2.0

        verts = [
            (sx - border_w, sy - border_w),
            (sx + cw + border_w, sy - border_w),
            (sx + cw + border_w, sy),
            (sx - border_w, sy),
        ]
        shader.uniform_float("color", border_color)
        batch_for_shader(shader, "TRI_FAN", {"pos": verts}).draw(shader)

        verts = [
            (sx - border_w, top_y),
            (sx + cw + border_w, top_y),
            (sx + cw + border_w, top_y + border_w),
            (sx - border_w, top_y + border_w),
        ]
        shader.uniform_float("color", border_color)
        batch_for_shader(shader, "TRI_FAN", {"pos": verts}).draw(shader)

        verts = [(sx - border_w, sy), (sx, sy), (sx, top_y), (sx - border_w, top_y)]
        shader.uniform_float("color", border_color)
        batch_for_shader(shader, "TRI_FAN", {"pos": verts}).draw(shader)

        verts = [(sx + cw, sy), (sx + cw + border_w, sy), (sx + cw + border_w, top_y), (sx + cw, top_y)]
        shader.uniform_float("color", border_color)
        batch_for_shader(shader, "TRI_FAN", {"pos": verts}).draw(shader)

        gpu.state.blend_set(saved_blend)

    def draw_texture(self):
        if not (self.running and self.native_shader and self.native_batch and self.data_texture):
            return

        saved_blend = gpu.state.blend_get()
        saved_depth = gpu.state.depth_test_get()

        try:
            gpu.state.blend_set("ALPHA_PREMULT")
            gpu.state.depth_test_set("NONE")

            self.native_shader.bind()
            self.native_shader.uniform_sampler("containerData", self.data_texture)
            if self.gradient_texture:
                self.native_shader.uniform_sampler("gradientTex", self.gradient_texture)
                self.native_shader.uniform_float("gradTexHeight", float(self.gradient_texture.height))
            else:
                if not hasattr(self, "_dummy_grad_tex") or self._dummy_grad_tex is None:
                    dummy = np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float32)
                    dbuf = gpu.types.Buffer("FLOAT", 4, dummy)
                    self._dummy_grad_tex = gpu.types.GPUTexture((1, 1), format="RGBA32F", data=dbuf)
                self.native_shader.uniform_sampler("gradientTex", self._dummy_grad_tex)
                self.native_shader.uniform_float("gradTexHeight", 1.0)
            self.native_shader.uniform_float("viewportWidth", float(self.region_size[0]))
            self.native_shader.uniform_float("viewportHeight", float(self.region_size[1]))
            self.native_shader.uniform_float("hoverIndex", float(self._current_hover_index))
            self.native_shader.uniform_float("clickIndex", float(self._current_click_index))

            gpu.matrix.push()
            gpu.matrix.load_identity()

            self.native_batch.draw(self.native_shader)
            gpu.matrix.pop()
        except Exception:
            logger.error("Error drawing containers", exc_info=True)

        try:
            self._draw_scrollbars()
        except Exception:
            logger.error("Error drawing scrollbars", exc_info=True)

        try:
            self._draw_debug_overlay()
        except Exception:
            logger.error("Error drawing debug overlay", exc_info=True)

        gpu.state.blend_set(saved_blend)
        gpu.state.depth_test_set(saved_depth)

    def cleanup(self):
        self.running = False

        if self.draw_handler:
            from .space_config import get_space_class

            space_class = get_space_class()
            if not space_class:
                space_class = bpy.types.SpaceView3D

            space_class.draw_handler_remove(self.draw_handler, "WINDOW")
            self.draw_handler = None

        self.needs_texture_update = True
        self.last_mouse_pos = [0.5, 0.5]
        self.last_click_value = 0.0
        self.last_scroll_value = 0.0

        if self._safe_release_moderngl_object(self.mouse_buffer):
            self.mouse_buffer = None
        if self._safe_release_moderngl_object(self.container_buffer):
            self.container_buffer = None
        if self._safe_release_moderngl_object(self.viewport_buffer):
            self.viewport_buffer = None
        if self._safe_release_moderngl_object(self.output_texture):
            self.output_texture = None
        if self._safe_release_moderngl_object(self.outline_texture):
            self.outline_texture = None
        if self._safe_release_moderngl_object(self.debug_outline_buffer):
            self.debug_outline_buffer = None
        if self._safe_release_moderngl_object(self.debug_outline_count_buffer):
            self.debug_outline_count_buffer = None
        if self._safe_release_moderngl_object(self.compute_shader):
            self.compute_shader = None
        if self._safe_release_moderngl_object(self.outline_shader):
            self.outline_shader = None

        if self.mgl_context:
            try:
                self.mgl_context.gc()
            except AttributeError as e:
                if "'InvalidObject' object has no attribute 'release'" not in str(e):
                    logger.warning("Unexpected AttributeError during ModernGL context GC", exc_info=True)
            except Exception:
                logger.warning("Exception during ModernGL context GC", exc_info=True)
            finally:
                self.mgl_context = None

        try:
            import gc

            gc.collect()
        except Exception:
            pass

        if self.scroll_callback_registered:
            scroll_state.unregister_callback(self.on_scroll)
            self.scroll_callback_registered = False

        if self.mouse_callback_registered:
            mouse_state.unregister_callback(self.on_mouse_event)
            self.mouse_callback_registered = False

        self._cached_target_area = None
        self._cached_target_region = None
        self._cached_target_space = None
        self._area_cache_valid = False

        if self.data_texture:
            try:
                del self.data_texture
            except Exception:
                logger.debug("Failed to delete data texture", exc_info=True)
            self.data_texture = None
        self.native_shader = None
        self.native_batch = None
        self.container_count = 0

    def _parse_gradient_stops(self, stops_str):
        if not stops_str or not stops_str.strip():
            return None
        parts = stops_str.strip().split()
        if len(parts) < 6:
            return None
        try:
            angle = float(parts[0])
            stops = []
            i = 1
            while i + 4 < len(parts):
                r, g, b, a, pos = (
                    float(parts[i]),
                    float(parts[i + 1]),
                    float(parts[i + 2]),
                    float(parts[i + 3]),
                    float(parts[i + 4]),
                )
                stops.append((r, g, b, a, pos))
                i += 5
            if len(stops) < 2:
                return None
            return (angle, stops)
        except (ValueError, IndexError):
            logger.debug("Failed to parse gradient stops", exc_info=True)
            return None

    def _prerender_gradient_row(self, stops, width=256):
        row = np.zeros(width * 4, dtype=np.float32)
        for x in range(width):
            t = x / max(width - 1, 1)
            for j in range(len(stops) - 1):
                if stops[j + 1][4] >= t or j == len(stops) - 2:
                    span = stops[j + 1][4] - stops[j][4]
                    local_t = (t - stops[j][4]) / max(span, 1e-6) if span > 0 else 0.0
                    local_t = max(0.0, min(1.0, local_t))
                    for c in range(4):
                        row[x * 4 + c] = stops[j][c] + (stops[j + 1][c] - stops[j][c]) * local_t
                    break
        return row

    def _build_gradient_texture(self, containers):
        gradient_defs = {}

        for c in containers:
            for key in ("gradient_stops", "hover_gradient_stops", "click_gradient_stops"):
                stops_str = c.get(key, "")
                if stops_str and stops_str not in gradient_defs:
                    parsed = self._parse_gradient_stops(stops_str)
                    if parsed:
                        gradient_defs[stops_str] = parsed

        if not gradient_defs:
            self._gradient_row_map = {}
            self.gradient_texture = None
            return False

        width = 256
        height = len(gradient_defs)
        data = np.zeros(width * height * 4, dtype=np.float32)

        self._gradient_row_map = {}
        for i, (stops_str, (angle, stops)) in enumerate(gradient_defs.items()):
            row = self._prerender_gradient_row(stops, width)
            data[i * width * 4 : (i + 1) * width * 4] = row
            self._gradient_row_map[stops_str] = float(i)

        try:
            buf = gpu.types.Buffer("FLOAT", len(data), data)
            self.gradient_texture = gpu.types.GPUTexture(
                (width, height),
                format="RGBA32F",
                data=buf,
            )
            return True
        except Exception:
            logger.error("Failed to create gradient texture", exc_info=True)
            self.gradient_texture = None
            return False

    def _build_container_struct(self, container):
        bg_color = container.get("background_color", [1, 1, 1, 1])
        bg_color_2 = container.get("background_color_2", [1, 1, 1, 1])
        hover_bg_color = container.get("hover_background_color", container_default.hover_background_color)
        hover_bg_color_2 = container.get("hover_background_color_2", container_default.hover_background_color_2)
        click_bg_color = container.get("click_background_color", container_default.click_background_color)
        click_bg_color_2 = container.get("click_background_color_2", container_default.click_background_color_2)
        border_color = container.get("border_color", [1, 1, 1, 1])
        border_color_2 = container.get("border_color_2", [0.0, 0.0, 0.0, 0.0])
        position = container.get("position", [0, 0])
        size = container.get("size", [100, 100])
        shadow_offset = container.get("box_shadow_offset", [0, 0, 0])
        shadow_color = container.get("box_shadow_color", [0, 0, 0, 0])

        br = container.get("border_radius", 0.0)

        grad_row_normal = self._gradient_row_map.get(container.get("gradient_stops", ""), -1.0)
        grad_row_hover = self._gradient_row_map.get(container.get("hover_gradient_stops", ""), -1.0)
        grad_row_click = self._gradient_row_map.get(container.get("click_gradient_stops", ""), -1.0)

        bw = container.get("border_width", 0.0)
        bw_top = container.get("border_width_top", 0.0) or bw
        bw_right = container.get("border_width_right", 0.0) or bw
        bw_bottom = container.get("border_width_bottom", 0.0) or bw
        bw_left = container.get("border_width_left", 0.0) or bw

        return [
            int(container.get("display", False)),
            position[0],
            position[1],
            size[0],
            size[1],
            bg_color[0],
            bg_color[1],
            bg_color[2],
            bg_color[3],
            bg_color_2[0],
            bg_color_2[1],
            bg_color_2[2],
            bg_color_2[3],
            container.get("background_gradient_rot", 0.0),
            hover_bg_color[0],
            hover_bg_color[1],
            hover_bg_color[2],
            hover_bg_color[3],
            hover_bg_color_2[0],
            hover_bg_color_2[1],
            hover_bg_color_2[2],
            hover_bg_color_2[3],
            container.get("hover_background_gradient_rot", 0.0),
            click_bg_color[0],
            click_bg_color[1],
            click_bg_color[2],
            click_bg_color[3],
            click_bg_color_2[0],
            click_bg_color_2[1],
            click_bg_color_2[2],
            click_bg_color_2[3],
            container.get("click_background_gradient_rot", 0.0),
            border_color[0],
            border_color[1],
            border_color[2],
            border_color[3],
            border_color_2[0],
            border_color_2[1],
            border_color_2[2],
            border_color_2[3],
            container.get("border_gradient_rot", 0.0),
            container.get("border_radius_tl", br),  # texel 10.y — radius TL
            container.get("border_width", 0.0),
            container.get("border_radius_tr", br),  # texel 10.w — radius TR
            container.get("border_radius_br", br),  # texel 11.x — radius BR
            shadow_offset[0],
            shadow_offset[1],
            shadow_offset[2],
            container.get("box_shadow_blur", 0.0),
            shadow_color[0],
            shadow_color[1],
            shadow_color[2],
            shadow_color[3],
            int(container.get("passive", False)),
            # Precomputed fields (defaults; overwritten by _precompute_visibility_and_clips)
            1.0,  # visible
            0.0,
            0.0,  # clip_x, clip_y
            99999.0,
            99999.0,  # clip_w, clip_h
            1.0,  # accumulated opacity
            # Texel 15: radius_bl + gradient row indices
            container.get("border_radius_bl", br),
            float(grad_row_normal),
            float(grad_row_hover),
            float(grad_row_click),
            # Texel 16: per-side border widths
            float(bw_top),
            float(bw_right),
            float(bw_bottom),
            float(bw_left),
        ]

    def _precompute_visibility_and_clips(self, containers):
        n = len(containers)
        vw = float(self.region_size[0])
        vh = float(self.region_size[1])
        results = []
        # Cache accumulated opacity per index for parent lookups
        acc_opacities = [1.0] * n

        for i in range(n):
            c = containers[i]
            if not c.get("display", False):
                results.append((0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
                continue

            # visibility: hidden keeps layout space but doesn't render
            if c.get("visibility", "") == "HIDDEN":
                results.append((0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
                continue

            visible = 1.0
            clip_x, clip_y = 0.0, 0.0
            clip_r, clip_b = vw, vh

            # Own opacity
            own_opacity = float(c.get("opacity", 1.0))
            parent_idx = int(c.get("parent", -1))
            parent_opacity = acc_opacities[parent_idx] if 0 <= parent_idx < n else 1.0
            acc_opacity = own_opacity * parent_opacity
            acc_opacities[i] = acc_opacity

            idx = i
            for _ in range(20):
                pidx = int(containers[idx].get("parent", -1))
                if pidx < 0 or pidx >= n:
                    break
                parent = containers[pidx]

                if not parent.get("display", False):
                    visible = 0.0
                    break

                if not parent.get("overflow", False):
                    pp = parent.get("position", [0, 0])
                    ps = parent.get("size", [100, 100])
                    px, py = float(pp[0]), float(pp[1])
                    pw, ph = float(ps[0]), float(ps[1])
                    clip_x = max(clip_x, px)
                    clip_y = max(clip_y, py)
                    clip_r = min(clip_r, px + pw)
                    clip_b = min(clip_b, py + ph)

                # Also clip for overflow:scroll/auto (these clip like hidden but allow scrolling)
                parent_overflow_type = parent.get("overflow_type", "VISIBLE")
                if parent_overflow_type in ("SCROLL", "AUTO"):
                    pp = parent.get("position", [0, 0])
                    ps = parent.get("size", [100, 100])
                    px, py = float(pp[0]), float(pp[1])
                    pw, ph = float(ps[0]), float(ps[1])
                    clip_x = max(clip_x, px)
                    clip_y = max(clip_y, py)
                    clip_r = min(clip_r, px + pw)
                    clip_b = min(clip_b, py + ph)

                idx = pidx

            clip_w = max(0.0, clip_r - clip_x)
            clip_h = max(0.0, clip_b - clip_y)
            results.append((visible, clip_x, clip_y, clip_w, clip_h, acc_opacity))

        return results

    def _cache_original_positions(self, containers):
        self._original_positions = {}
        self._container_id_to_index = {}
        for i, c in enumerate(containers):
            pos = c.get("position", [0, 0])
            self._original_positions[i] = [float(pos[0]), float(pos[1])]
            self._container_id_to_index[c.get("id", "")] = i
        self._compute_content_bounds(containers)

    def _cache_original_text_positions(self, text_blocks):
        self._original_text_positions = {}
        for cid, block in text_blocks.items():
            self._original_text_positions[cid] = {
                "text_x": block["text_x"],
                "text_y": block["text_y"],
                "mask_x": block["mask_x"],
                "mask_y": block["mask_y"],
                "mask_w": block["mask_width"],
                "mask_h": block["mask_height"],
            }

    def _cache_original_image_positions(self, image_blocks):
        self._original_image_positions = {}
        for cid, block in image_blocks.items():
            self._original_image_positions[cid] = {
                "x_pos": block["x_pos"],
                "y_pos": block["y_pos"],
                "mask_x": block["mask_x"],
                "mask_y": block["mask_y"],
            }

    def _compute_content_bounds(self, containers):
        self._content_bounds = {}
        n = len(containers)
        for i, c in enumerate(containers):
            overflow_type = c.get("overflow_type", "VISIBLE")
            if overflow_type in ("SCROLL", "AUTO"):
                max_bottom = 0.0
                max_right = 0.0
                container_pos = c.get("position", [0, 0])
                cx, cy = float(container_pos[0]), float(container_pos[1])
                # BFS over all descendants
                stack = list(c.get("children", []))
                while stack:
                    ci = stack.pop()
                    if ci < 0 or ci >= n:
                        continue
                    child = containers[ci]
                    child_pos = child.get("position", [0, 0])
                    child_size = child.get("size", [0, 0])
                    max_right = max(max_right, float(child_pos[0]) + float(child_size[0]) - cx)
                    max_bottom = max(max_bottom, float(child_pos[1]) + float(child_size[1]) - cy)
                    stack.extend(child.get("children", []))
                self._content_bounds[i] = [max_right, max_bottom]

    def _find_scrollable_ancestor(self, idx, containers):
        current = idx
        n = len(containers)
        for _ in range(20):
            if current < 0 or current >= n:
                return -1
            c = containers[current]
            overflow_type = c.get("overflow_type", "VISIBLE")
            if overflow_type in ("SCROLL", "AUTO"):
                return current
            parent = int(c.get("parent", -1))
            if parent < 0:
                return -1
            current = parent
        return -1

    def _compute_scroll_accumulation(self, containers):
        n = len(containers)
        acc = [[0.0, 0.0] for _ in range(n)]
        computed = [False] * n

        def compute_for(idx):
            if idx < 0 or idx >= n or computed[idx]:
                return
            computed[idx] = True
            parent_idx = int(containers[idx].get("parent", -1))
            if 0 <= parent_idx < n:
                if not computed[parent_idx]:
                    compute_for(parent_idx)
                acc[idx][0] = acc[parent_idx][0]
                acc[idx][1] = acc[parent_idx][1]
                if parent_idx in self._scroll_offsets:
                    acc[idx][0] += self._scroll_offsets[parent_idx][0]
                    acc[idx][1] += self._scroll_offsets[parent_idx][1]
            # position:fixed containers are NOT affected by ancestor scroll
            if containers[idx].get("position_type", "RELATIVE") == "FIXED":
                acc[idx] = [0.0, 0.0]

        for i in range(n):
            compute_for(i)

        self._scroll_accumulation = acc
        return acc

    def _apply_scroll_to_containers(self, containers):
        if not self._scroll_offsets or not self._original_positions:
            return False
        acc = self._compute_scroll_accumulation(containers)
        changed = False
        for i, c in enumerate(containers):
            sx, sy = acc[i]
            if sx != 0.0 or sy != 0.0:
                orig = self._original_positions.get(i, [0.0, 0.0])
                c["position"] = [orig[0] - sx, orig[1] - sy]
                changed = True
            elif i in self._original_positions:
                # Restore original position (in case scroll was removed)
                orig = self._original_positions[i]
                pos = c.get("position", [0, 0])
                if float(pos[0]) != orig[0] or float(pos[1]) != orig[1]:
                    c["position"] = [orig[0], orig[1]]
                    changed = True
        return changed

    def _apply_scroll_to_text(self, text_blocks):
        if not self._scroll_offsets or not self._original_text_positions:
            return
        for cid, block in text_blocks.items():
            orig = self._original_text_positions.get(cid)
            if not orig:
                continue
            idx = self._container_id_to_index.get(cid, -1)
            if idx < 0 or idx >= len(self._scroll_accumulation):
                continue
            sx, sy = self._scroll_accumulation[idx]
            block["text_x"] = int(orig["text_x"] - sx)
            block["text_y"] = int(orig["text_y"] - sy)
            block["mask_x"] = int(orig["mask_x"] - sx)
            block["mask_y"] = int(orig["mask_y"] - sy)

    def _apply_scroll_to_images(self, image_blocks):
        if not self._scroll_offsets or not self._original_image_positions:
            return
        for cid, block in image_blocks.items():
            orig = self._original_image_positions.get(cid)
            if not orig:
                continue
            idx = self._container_id_to_index.get(cid, -1)
            if idx < 0 or idx >= len(self._scroll_accumulation):
                continue
            sx, sy = self._scroll_accumulation[idx]
            block["x_pos"] = int(orig["x_pos"] - sx)
            block["y_pos"] = int(orig["y_pos"] - sy)
            # Don't scroll the mask — it will be set from scroll clip in the render loop

    def _cache_original_text_input_positions(self, text_input_blocks):
        self._original_text_input_positions = {}
        for cid, block in text_input_blocks.items():
            self._original_text_input_positions[cid] = {
                "x_pos": block["x_pos"],
                "y_pos": block["y_pos"],
                "mask_x": block["mask_x"],
                "mask_y": block["mask_y"],
            }

    def _apply_scroll_to_text_inputs(self, text_input_blocks):
        if not self._scroll_offsets or not self._original_text_input_positions:
            return
        for cid, block in text_input_blocks.items():
            orig = self._original_text_input_positions.get(cid)
            if not orig:
                continue
            idx = self._container_id_to_index.get(cid, -1)
            if idx < 0 or idx >= len(self._scroll_accumulation):
                continue
            sx, sy = self._scroll_accumulation[idx]
            block["x_pos"] = int(orig["x_pos"] - sx)
            block["y_pos"] = int(orig["y_pos"] - sy)

    def _get_scroll_clip_for_container(self, idx, containers):
        n = len(containers)
        vw = float(self.region_size[0])
        vh = float(self.region_size[1])
        clip_x, clip_y = 0.0, 0.0
        clip_r, clip_b = vw, vh
        has_clip = False

        current = idx
        for _ in range(20):
            pidx = int(containers[current].get("parent", -1))
            if pidx < 0 or pidx >= n:
                break
            parent = containers[pidx]
            ot = parent.get("overflow_type", "VISIBLE")
            if ot in ("SCROLL", "AUTO"):
                pp = parent.get("position", [0, 0])
                ps = parent.get("size", [100, 100])
                px, py = float(pp[0]), float(pp[1])
                pw, ph = float(ps[0]), float(ps[1])
                clip_x = max(clip_x, px)
                clip_y = max(clip_y, py)
                clip_r = min(clip_r, px + pw)
                clip_b = min(clip_b, py + ph)
                has_clip = True
            current = pidx

        if has_clip:
            return (int(clip_x), int(clip_y), int(max(0, clip_r - clip_x)), int(max(0, clip_b - clip_y)))
        return None

    def _apply_initial_scroll_clips(self, containers, text_blocks, image_blocks=None, text_input_blocks=None):
        for cid, block in text_blocks.items():
            idx = self._container_id_to_index.get(cid, -1)
            if idx < 0:
                continue
            clip = self._get_scroll_clip_for_container(idx, containers)
            if clip:
                # Store scroll clip separately — mask stays as container bounds for alignment
                cx, cy, cw, ch = clip
                block["scroll_clip"] = [cx, cy, cw, ch]
        if image_blocks:
            for cid, block in image_blocks.items():
                idx = self._container_id_to_index.get(cid, -1)
                if idx < 0:
                    continue
                clip = self._get_scroll_clip_for_container(idx, containers)
                if clip:
                    cx, cy, cw, ch = clip
                    mx, my = block["mask_x"], block["mask_y"]
                    mw, mh = block["mask_width"], block["mask_height"]
                    ix = max(mx, cx)
                    iy = max(my, cy)
                    ir = min(mx + mw, cx + cw)
                    ib = min(my + mh, cy + ch)
                    block["mask_x"] = ix
                    block["mask_y"] = iy
                    block["mask_width"] = max(0, ir - ix)
                    block["mask_height"] = max(0, ib - iy)
        if text_input_blocks:
            for cid, block in text_input_blocks.items():
                idx = self._container_id_to_index.get(cid, -1)
                if idx < 0:
                    continue
                clip = self._get_scroll_clip_for_container(idx, containers)
                if clip:
                    cx, cy, cw, ch = clip
                    mx, my = block["mask_x"], block["mask_y"]
                    mw, mh = block["mask_width"], block["mask_height"]
                    ix = max(mx, cx)
                    iy = max(my, cy)
                    ir = min(mx + mw, cx + cw)
                    ib = min(my + mh, cy + ch)
                    block["mask_x"] = ix
                    block["mask_y"] = iy
                    block["mask_width"] = max(0, ir - ix)
                    block["mask_height"] = max(0, ib - iy)

    def _detect_state_changes(self, container_data):
        hover_index = -1
        click_index = -1

        for i, c in enumerate(container_data):
            h = c.get("_hovered", False)
            k = c.get("_clicked", False)
            if h and not c.get("passive", False):
                hover_index = i
            if k and not c.get("passive", False):
                click_index = i

        changed = hover_index != self._current_hover_index or click_index != self._current_click_index

        if changed:
            old_hover = self._current_hover_index
            self._current_hover_index = hover_index
            self._current_click_index = click_index

            # Start transitions for containers with transition CSS properties
            self._start_hover_transitions(old_hover, hover_index, container_data)

        # Inspect mode: auto-highlight hovered container
        try:
            if bpy.context.window_manager.xwz_inspect_mode:
                inspect_idx = -1
                for i, c in enumerate(container_data):
                    if c.get("_hovered", False):
                        inspect_idx = i
                if inspect_idx >= 0:
                    new_id = str(inspect_idx)
                    if new_id not in self.debug_outlined_containers:
                        self.debug_outlined_containers.clear()
                        self.debug_outlined_containers.add(new_id)
                        self.needs_texture_update = True
                        changed = True
        except Exception:
            pass

        return changed

    def _start_hover_transitions(self, old_idx, new_idx, containers):
        n = len(containers)

        def _start_props(c, cid, transitions, entering_hover):
            for t in transitions:
                t_prop = t["property"]
                t_dur = t["duration"]
                t_timing = t["timing"]
                t_delay = t["delay"]
                if t_dur <= 0:
                    continue

                # background-color
                hover_bg = c.get("hover_background_color", [0, 0, 0, -1])
                normal_bg = c.get("background_color", [0, 0, 0, 0])
                if hover_bg[3] >= 0 and t_prop in ("all", "background_color", "background-color"):
                    current = self.transitions.get_value(cid, "background_color")
                    if entering_hover:
                        start = current if current else normal_bg
                        self.transitions.start_transition(
                            cid, "background_color", start, hover_bg, t_dur, t_delay, t_timing
                        )
                    else:
                        start = current if current else hover_bg
                        self.transitions.start_transition(
                            cid, "background_color", start, normal_bg, t_dur, t_delay, t_timing
                        )

                # border-color
                hover_bc = c.get("hover_border_color", [0, 0, 0, -1])
                normal_bc = c.get("border_color", [0, 0, 0, 0])
                if hover_bc[3] >= 0 and t_prop in ("all", "border_color", "border-color"):
                    current = self.transitions.get_value(cid, "border_color")
                    if entering_hover:
                        start = current if current else normal_bc
                        self.transitions.start_transition(
                            cid, "border_color", start, hover_bc, t_dur, t_delay, t_timing
                        )
                    else:
                        start = current if current else hover_bc
                        self.transitions.start_transition(
                            cid, "border_color", start, normal_bc, t_dur, t_delay, t_timing
                        )

                # opacity
                hover_op = c.get("hover_opacity", -1.0)
                normal_op = c.get("opacity", 1.0)
                if hover_op >= 0 and t_prop in ("all", "opacity"):
                    current = self.transitions.get_value(cid, "opacity")
                    if entering_hover:
                        start = current if current is not None else normal_op
                        self.transitions.start_transition(cid, "opacity", start, hover_op, t_dur, t_delay, t_timing)
                    else:
                        start = current if current is not None else hover_op
                        self.transitions.start_transition(cid, "opacity", start, normal_op, t_dur, t_delay, t_timing)

        # Container being un-hovered
        if 0 <= old_idx < n:
            c = containers[old_idx]
            cid = c.get("id", "")
            transitions = c.get("_transitions", [])
            if (
                not transitions
                and c.get("_transition_property", "none") != "none"
                and c.get("_transition_duration", 0.0) > 0
            ):
                transitions = [
                    {
                        "property": c.get("_transition_property"),
                        "duration": c.get("_transition_duration", 0.0),
                        "timing": c.get("_transition_timing_function", "ease"),
                        "delay": c.get("_transition_delay", 0.0),
                    }
                ]
            if transitions:
                _start_props(c, cid, transitions, entering_hover=False)

        # Container being hovered
        if 0 <= new_idx < n:
            c = containers[new_idx]
            cid = c.get("id", "")
            transitions = c.get("_transitions", [])
            if (
                not transitions
                and c.get("_transition_property", "none") != "none"
                and c.get("_transition_duration", 0.0) > 0
            ):
                transitions = [
                    {
                        "property": c.get("_transition_property"),
                        "duration": c.get("_transition_duration", 0.0),
                        "timing": c.get("_transition_timing_function", "ease"),
                        "delay": c.get("_transition_delay", 0.0),
                    }
                ]
            if transitions:
                _start_props(c, cid, transitions, entering_hover=True)

    def update_container_buffer_full(self, hit_container_data):
        if not hit_container_data:
            return False

        try:
            # Update native data texture (primary rendering path)
            self.update_data_texture(hit_container_data)

            # Also update compute shader buffer if available (for outline shader)
            if self.container_buffer:
                vis_clips = self._precompute_visibility_and_clips(hit_container_data)

                container_array = []
                for i, container in enumerate(hit_container_data):
                    struct = self._build_container_struct(container)
                    v, cx, cy, cw, ch, acc_opacity = vis_clips[i]
                    struct[54] = v
                    struct[55] = cx
                    struct[56] = cy
                    struct[57] = cw
                    struct[58] = ch
                    struct[59] = acc_opacity
                    container_array.extend(struct)

                container_data_np = np.array(container_array, dtype=np.float32)
                self._write_container_buffer(container_data_np.tobytes())

            if self.viewport_buffer:
                vp_data = np.array(
                    [
                        float(self.region_size[0]),
                        float(self.region_size[1]),
                        float(len(hit_container_data)),
                        float(self._current_hover_index),
                        float(self._current_click_index),
                    ],
                    dtype=np.float32,
                )
                self.viewport_buffer.write(vp_data.tobytes())

            return True
        except Exception:
            logger.error("Failed to write container buffer", exc_info=True)
            return False


class XWZ_OT_start_ui(Operator):
    bl_idname = "xwz.start_ui"
    bl_label = "Start puree"
    bl_description = "Start puree UI"

    def execute(self, context):
        global _render_data, _modal_timer, _modal_generation

        if _render_data and _render_data.running:
            logger.warning("Demo already running")
            return {"CANCELLED"}

        _modal_generation += 1
        self._generation = _modal_generation

        _render_data = RenderPipeline()

        if not _render_data.initialize():
            logger.error("Failed to initialize compute shader demo")
            _render_data = None
            return {"CANCELLED"}

        # Start native-optimized hit detection
        try:
            bpy.ops.xwz.hit_detect("INVOKE_DEFAULT")
        except Exception as e:
            logger.warning(f"Failed to start hit detect modal: {e}")

        try:
            bpy.ops.xwz.scroll_modal_launch("INVOKE_DEFAULT")
        except Exception as e:
            logger.warning(f"Failed to start scroll modal: {e}")

        try:
            bpy.ops.xwz.mouse_modal_launch("INVOKE_DEFAULT")
        except Exception as e:
            logger.warning(f"Failed to start mouse modal: {e}")

        context.window_manager.modal_handler_add(self)
        _modal_timer = context.window_manager.event_timer_add(0.016, window=context.window)

        # Clip text/image/text_input masks to scroll parent bounds before creating instances
        _render_data._apply_initial_scroll_clips(
            _render_data.container_data,
            parser_op.text_blocks,
            parser_op.image_blocks if hasattr(parser_op, "image_blocks") else None,
            parser_op.text_input_blocks if hasattr(parser_op, "text_input_blocks") else None,
        )

        for _container_id in parser_op.image_blocks:
            block = parser_op.image_blocks[_container_id]
            bpy.ops.xwz.draw_image(
                container_id=_container_id,
                image_name=block["image_name"],
                x_pos=block["x_pos"],
                y_pos=block["y_pos"],
                width=block["width"],
                height=block["height"],
                mask_x=block["mask_x"],
                mask_y=block["mask_y"],
                mask_width=block["mask_width"],
                mask_height=block["mask_height"],
                aspect_ratio=block["aspect_ratio"],
                align_h=block.get("align_h", "LEFT").upper(),
                align_v=block.get("align_v", "TOP").upper(),
                opacity=block.get("opacity", 1.0),
            )

        for _container_id in parser_op.text_blocks:
            block = parser_op.text_blocks[_container_id]
            bpy.ops.xwz.draw_text(
                container_id=_container_id,
                text=block["text"],
                font_name=block["font"],
                size=block["font_size"],
                x_pos=block["text_x"],
                y_pos=block["text_y"],
                color=block["color"],
                mask_x=block["mask_x"],
                mask_y=block["mask_y"],
                mask_width=block["mask_width"],
                mask_height=block["mask_height"],
                align_h=block.get("align_h", "LEFT").upper(),
                align_v=block.get("align_v", "CENTER").upper(),
                text_decoration=block.get("text_decoration", "NONE"),
                letter_spacing=block.get("letter_spacing", 0.0),
                line_height=block.get("line_height", 0.0),
                font_weight=block.get("font_weight", "NORMAL"),
                font_style=block.get("font_style", "NORMAL"),
                white_space=block.get("white_space", "NORMAL"),
                text_overflow=block.get("text_overflow", "CLIP"),
                overflow_wrap=block.get("overflow_wrap", "NORMAL"),
                word_break=block.get("word_break", "NORMAL"),
                text_shadow_color=block.get("text_shadow_color", [0, 0, 0, 0]),
                text_shadow_offset_x=block.get("text_shadow_offset_x", 0.0),
                text_shadow_offset_y=block.get("text_shadow_offset_y", 0.0),
                text_shadow_blur=block.get("text_shadow_blur", 0.0),
            )

        # Set scissor clips on text instances for scroll containers
        from . import text_op as text_op_mod

        for text_instance in text_op_mod._text_instances:
            cid = text_instance.container_id
            block = parser_op.text_blocks.get(cid)
            if block and "scroll_clip" in block:
                text_instance.clip = list(block["scroll_clip"])

        for _container_id in parser_op.text_input_blocks:
            block = parser_op.text_input_blocks[_container_id]
            bpy.ops.xwz.create_text_input(
                container_id=_container_id,
                placeholder=block["placeholder"],
                font_name=block["font"],
                size=block["font_size"],
                x_pos=block["x_pos"],
                y_pos=block["y_pos"],
                color=block["color"],
                mask_x=block["mask_x"],
                mask_y=block["mask_y"],
                mask_width=block["mask_width"],
                mask_height=block["mask_height"],
                align_h=block.get("align_h", "LEFT").upper(),
                align_v=block.get("align_v", "TOP").upper(),
            )

        try:
            from . import get_addon_root
            from .hot_reload import get_hot_reload_manager, register_default_callbacks, setup_hot_reload

            addon_dir = get_addon_root()
            wm = context.window_manager

            if setup_hot_reload(addon_dir, wm.xwz_ui_conf_path):
                register_default_callbacks()
                manager = get_hot_reload_manager()
                manager.enable()

                global _hot_reload_enabled
                _hot_reload_enabled = True

                logger.info("UI Started with hot reload enabled")
            else:
                logger.info("UI Started (hot reload unavailable)")
        except Exception as e:
            logger.warning(f"Hot reload initialization failed: {e}")
            logger.info("UI Started (hot reload disabled)")

        # Update debug panel to appear in the correct space
        try:
            from . import panel

            panel.update_panel_space()
        except Exception as e:
            logger.error(f"Failed to update debug panel space: {e}")

        # Force initial redraw to ensure UI appears immediately
        from .space_config import get_target_space

        target_space = get_target_space()
        if target_space:
            for area in context.screen.areas:
                if area.type == target_space:
                    area.tag_redraw()
                    break

        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        global _render_data, _modal_generation

        if not (_render_data and _render_data.running):
            self.cancel(context)
            return {"CANCELLED"}

        # Stale modal from a previous start — exit without cleanup
        if getattr(self, "_generation", 0) != _modal_generation:
            return {"CANCELLED"}

        if event.type == "WINDOW_DEACTIVATE":
            area = context.area
            region = context.region

            if area and region:
                size_changed = _render_data.update_region_size(region.width, region.height)
                if size_changed:
                    from .hit_op import _container_data

                    if _container_data:
                        _render_data.update_container_buffer_full(_container_data)

                    from .space_config import get_target_space

                    target_space = get_target_space()

                    for area in context.screen.areas:
                        if area.type == target_space:
                            area.tag_redraw()

        if event.type == "TIMER":
            # Use cached area/region lookup — avoids per-frame linear scan
            if not _render_data._area_cache_valid:
                from .space_config import find_target_area_and_region

                target_area, target_region = find_target_area_and_region()
                _render_data._cached_target_area = target_area
                _render_data._cached_target_region = target_region
                _render_data._area_cache_valid = True
            else:
                target_area = _render_data._cached_target_area
                target_region = _render_data._cached_target_region

            texture_changed = False
            size_changed = False
            transitions_active = False
            hover_changed = False

            if target_area and target_region:
                # Throttle hot reload checks to every N frames instead of every frame
                global _hot_reload_enabled
                if _hot_reload_enabled:
                    _render_data._hot_reload_frame_counter += 1
                    if _render_data._hot_reload_frame_counter >= _render_data._hot_reload_check_interval:
                        _render_data._hot_reload_frame_counter = 0
                        try:
                            from .hot_reload import get_hot_reload_manager

                            manager = get_hot_reload_manager()
                            manager.check_for_changes()
                        except Exception as e:
                            logger.warning(f"Hot reload error: {e}")

                _render_data.update_fps()

                size_changed = _render_data.update_region_size(target_region.width, target_region.height)
                if size_changed:
                    # Invalidate area cache on resize
                    _render_data._area_cache_valid = False

                # Detect hover/click state changes from hit detection
                from . import hit_op

                hover_changed = False
                if hit_op._container_data:
                    hover_changed = _render_data._detect_state_changes(hit_op._container_data)

                # Tick active transitions — override container colors with interpolated values
                transitions_active = _render_data.transitions.has_active()
                if transitions_active and hit_op._container_data:
                    for i, c in enumerate(hit_op._container_data):
                        cid = c.get("id", "")

                        # background-color transition
                        bg = _render_data.transitions.get_value(cid, "background_color")
                        if bg is not None:
                            save_key = f"_orig_bg_{cid}"
                            if save_key not in _render_data._prev_container_states:
                                _render_data._prev_container_states[save_key] = list(
                                    c.get("background_color", [0, 0, 0, 0])
                                )
                                _render_data._prev_container_states[f"_orig_hover_{cid}"] = list(
                                    c.get("hover_background_color", [0, 0, 0, -1])
                                )
                            c["background_color"] = bg
                            c["hover_background_color"] = [0, 0, 0, -1]

                        # border-color transition
                        bc = _render_data.transitions.get_value(cid, "border_color")
                        if bc is not None:
                            save_key = f"_orig_bc_{cid}"
                            if save_key not in _render_data._prev_container_states:
                                _render_data._prev_container_states[save_key] = list(
                                    c.get("border_color", [0, 0, 0, 0])
                                )
                            c["border_color"] = bc

                        # opacity transition
                        op = _render_data.transitions.get_value(cid, "opacity")
                        if op is not None:
                            save_key = f"_orig_op_{cid}"
                            if save_key not in _render_data._prev_container_states:
                                _render_data._prev_container_states[save_key] = c.get("opacity", 1.0)
                            c["opacity"] = op

                        # Restore properties whose individual transitions are done
                        if bg is None:
                            save_key = f"_orig_bg_{cid}"
                            if save_key in _render_data._prev_container_states:
                                c["background_color"] = _render_data._prev_container_states.pop(save_key)
                                c["hover_background_color"] = _render_data._prev_container_states.pop(
                                    f"_orig_hover_{cid}", [0, 0, 0, -1]
                                )
                        if bc is None:
                            save_key = f"_orig_bc_{cid}"
                            if save_key in _render_data._prev_container_states:
                                c["border_color"] = _render_data._prev_container_states.pop(save_key)
                        if op is None:
                            save_key = f"_orig_op_{cid}"
                            if save_key in _render_data._prev_container_states:
                                c["opacity"] = _render_data._prev_container_states.pop(save_key)

                    texture_changed = True
                elif not transitions_active and _render_data._prev_container_states and hit_op._container_data:
                    # All transitions ended — restore any remaining saved originals
                    for i, c in enumerate(hit_op._container_data):
                        cid = c.get("id", "")
                        for prefix, prop in [("_orig_bg_", "background_color"), ("_orig_bc_", "border_color")]:
                            save_key = f"{prefix}{cid}"
                            if save_key in _render_data._prev_container_states:
                                c[prop] = _render_data._prev_container_states.pop(save_key)
                        hover_key = f"_orig_hover_{cid}"
                        if hover_key in _render_data._prev_container_states:
                            c["hover_background_color"] = _render_data._prev_container_states.pop(hover_key)
                        op_key = f"_orig_op_{cid}"
                        if op_key in _render_data._prev_container_states:
                            c["opacity"] = _render_data._prev_container_states.pop(op_key)
                    _render_data._prev_container_states.clear()
                    texture_changed = True

                texture_changed = texture_changed or _render_data.check_if_changed()

                state_synced = parser_op.sync_dirty_containers()
                if state_synced:
                    from . import hit_op, text_op

                    new_data = parser_op._container_json_data
                    old_data = hit_op._container_data

                    if old_data and len(old_data) == len(new_data):
                        for i in range(len(new_data)):
                            runtime_keys = [
                                "_hovered",
                                "_prev_hovered",
                                "_clicked",
                                "_prev_clicked",
                                "_toggled",
                                "_prev_toggled",
                                "_toggle_value",
                                "_scroll_value",
                            ]
                            for key in runtime_keys:
                                if key in old_data[i]:
                                    new_data[i][key] = old_data[i][key]

                    hit_op._container_data = new_data

                    # Synced data may have new style values — update saved
                    # transition originals so restores don't revert set_property changes
                    if _render_data._prev_container_states or _render_data.transitions.has_active():
                        for c in new_data:
                            cid = c.get("id", "")
                            new_bg = list(c.get("background_color", [0, 0, 0, 0]))
                            new_hover_bg = list(c.get("hover_background_color", [0, 0, 0, -1]))
                            new_bc = list(c.get("border_color", [0, 0, 0, 0]))
                            new_op = c.get("opacity", 1.0)

                            # Update saved originals
                            bg_key = f"_orig_bg_{cid}"
                            if bg_key in _render_data._prev_container_states:
                                _render_data._prev_container_states[bg_key] = new_bg
                            hover_key = f"_orig_hover_{cid}"
                            if hover_key in _render_data._prev_container_states:
                                _render_data._prev_container_states[hover_key] = new_hover_bg
                            bc_key = f"_orig_bc_{cid}"
                            if bc_key in _render_data._prev_container_states:
                                _render_data._prev_container_states[bc_key] = new_bc
                            op_key = f"_orig_op_{cid}"
                            if op_key in _render_data._prev_container_states:
                                _render_data._prev_container_states[op_key] = new_op

                            # Retarget active transitions to use new values
                            bg_t = _render_data.transitions._active.get((cid, "background_color"))
                            if bg_t and not bg_t.is_done():
                                is_hovered = c.get("_hovered", False)
                                bg_t.end_value = new_hover_bg if is_hovered else new_bg
                            bc_t = _render_data.transitions._active.get((cid, "border_color"))
                            if bc_t and not bc_t.is_done():
                                bc_t.end_value = new_bc
                            op_t = _render_data.transitions._active.get((cid, "opacity"))
                            if op_t and not op_t.is_done():
                                op_t.end_value = new_op

                    # Reload hit detector with updated layout positions
                    if hasattr(hit_op, "_native_detector") and hit_op._native_detector:
                        hit_op._native_detector.load_containers(hit_op._container_data)

                    # Cache original positions and text/image positions for scroll
                    _render_data._cache_original_positions(new_data)
                    _render_data._cache_original_text_positions(parser_op.text_blocks)
                    if hasattr(parser_op, "image_blocks"):
                        _render_data._cache_original_image_positions(parser_op.image_blocks)
                    if hasattr(parser_op, "text_input_blocks"):
                        _render_data._cache_original_text_input_positions(parser_op.text_input_blocks)

                    # Clip masks to scroll parent bounds
                    _render_data._apply_initial_scroll_clips(
                        new_data,
                        parser_op.text_blocks,
                        parser_op.image_blocks if hasattr(parser_op, "image_blocks") else None,
                        parser_op.text_input_blocks if hasattr(parser_op, "text_input_blocks") else None,
                    )

                    # Reapply existing scroll offsets to new layout data
                    if _render_data._scroll_offsets:
                        _render_data._apply_scroll_to_containers(new_data)
                        _render_data._apply_scroll_to_text(parser_op.text_blocks)
                        if hasattr(parser_op, "image_blocks"):
                            _render_data._apply_scroll_to_images(parser_op.image_blocks)
                        if hasattr(parser_op, "text_input_blocks"):
                            _render_data._apply_scroll_to_text_inputs(parser_op.text_input_blocks)

                    for text_instance in text_op._text_instances:
                        container_id = text_instance.container_id
                        if container_id in parser_op.text_blocks:
                            block = parser_op.text_blocks[container_id]
                            clip = list(block["scroll_clip"]) if "scroll_clip" in block else None
                            text_instance.update_all(
                                text=block["text"],
                                font_name=block["font"],
                                size=block["font_size"],
                                pos=[block["text_x"], block["text_y"]],
                                color=block["color"],
                                mask=[block["mask_x"], block["mask_y"], block["mask_width"], block["mask_height"]],
                                clip=clip,
                                align_h=block.get("align_h", "LEFT").upper(),
                                align_v=block.get("align_v", "CENTER").upper(),
                                white_space=block.get("white_space", "NORMAL"),
                                text_overflow=block.get("text_overflow", "CLIP"),
                                overflow_wrap=block.get("overflow_wrap", "NORMAL"),
                                word_break=block.get("word_break", "NORMAL"),
                            )

                    from . import text_input_op

                    for input_instance in text_input_op._text_input_instances:
                        container_id = input_instance.container_id
                        if container_id in parser_op.text_input_blocks:
                            block = parser_op.text_input_blocks[container_id]
                            bpy.ops.xwz.update_text_input(
                                instance_id=input_instance.id,
                                placeholder=block["placeholder"],
                                font_name=block["font"],
                                size=block["font_size"],
                                x_pos=block["x_pos"],
                                y_pos=block["y_pos"],
                                color=block["color"],
                                mask_x=block["mask_x"],
                                mask_y=block["mask_y"],
                                mask_width=block["mask_width"],
                                mask_height=block["mask_height"],
                                align_h=block.get("align_h", "LEFT").upper(),
                                align_v=block.get("align_v", "TOP").upper(),
                            )

                    from . import img_op

                    for image_instance in img_op._image_instances:
                        container_id = image_instance.container_id
                        if container_id in parser_op.image_blocks:
                            block = parser_op.image_blocks[container_id]
                            image_instance.update_all(
                                image_name=block["image_name"],
                                pos=[block["x_pos"], block["y_pos"]],
                                size=[block["width"], block["height"]],
                                mask=[block["mask_x"], block["mask_y"], block["mask_width"], block["mask_height"]],
                                aspect_ratio=block["aspect_ratio"],
                                align_h=block.get("align_h", "LEFT").upper(),
                                align_v=block.get("align_v", "TOP").upper(),
                                opacity=block.get("opacity", 1.0),
                            )

                    texture_changed = True

                # Handle scroll-triggered updates
                scroll_changed = _render_data._scroll_changed
                if scroll_changed:
                    _render_data._scroll_changed = False
                    from . import hit_op, text_op

                    if hit_op._container_data:
                        # Update GPU texture with scroll-adjusted positions
                        _render_data.update_data_texture(hit_op._container_data)

                        # Reload hit detector with scroll-adjusted positions
                        if hasattr(hit_op, "_native_detector") and hit_op._native_detector:
                            hit_op._native_detector.load_containers(hit_op._container_data)

                        acc = _render_data._scroll_accumulation

                        # Update text positions — only for containers inside scroll areas
                        for text_instance in text_op._text_instances:
                            container_id = text_instance.container_id
                            if container_id in parser_op.text_blocks:
                                idx = _render_data._container_id_to_index.get(container_id, -1)
                                if idx < 0 or idx >= len(acc):
                                    continue
                                sx, sy = acc[idx]

                                block = parser_op.text_blocks[container_id]
                                scroll_clip = _render_data._get_scroll_clip_for_container(idx, hit_op._container_data)

                                # Skip containers not in a scroll area
                                if not scroll_clip and sx == 0.0 and sy == 0.0:
                                    continue

                                # Compute scrolled mask using container's float original position
                                # (same source as GPU shader) to guarantee perfect pixel sync
                                orig_pos = _render_data._original_positions.get(idx)
                                if orig_pos:
                                    c_size = hit_op._container_data[idx].get("size", [0, 0])
                                    mask_x = orig_pos[0] - sx
                                    mask_y = orig_pos[1] - sy
                                    mask_w = float(c_size[0])
                                    mask_h = float(c_size[1])
                                else:
                                    c = hit_op._container_data[idx]
                                    c_pos = c.get("position", [0, 0])
                                    c_size = c.get("size", [0, 0])
                                    mask_x = float(c_pos[0])
                                    mask_y = float(c_pos[1])
                                    mask_w = float(c_size[0])
                                    mask_h = float(c_size[1])

                                clip = list(scroll_clip) if scroll_clip else None

                                text_instance.update_all(
                                    text=block["text"],
                                    font_name=block["font"],
                                    size=block["font_size"],
                                    pos=[block["text_x"], block["text_y"]],
                                    color=block["color"],
                                    mask=[mask_x, mask_y, mask_w, mask_h],
                                    clip=clip,
                                    align_h=block.get("align_h", "LEFT").upper(),
                                    align_v=block.get("align_v", "CENTER").upper(),
                                    white_space=block.get("white_space", "NORMAL"),
                                    text_overflow=block.get("text_overflow", "CLIP"),
                                    overflow_wrap=block.get("overflow_wrap", "NORMAL"),
                                    word_break=block.get("word_break", "NORMAL"),
                                )

                        # Update image positions — only for containers inside scroll areas
                        from . import img_op

                        for image_instance in img_op._image_instances:
                            container_id = image_instance.container_id
                            if container_id in parser_op.image_blocks:
                                idx = _render_data._container_id_to_index.get(container_id, -1)
                                if idx < 0 or idx >= len(acc):
                                    continue
                                sx, sy = acc[idx]

                                block = parser_op.image_blocks[container_id]
                                scroll_clip = _render_data._get_scroll_clip_for_container(idx, hit_op._container_data)

                                if not scroll_clip and sx == 0.0 and sy == 0.0:
                                    continue

                                mask_x = block["mask_x"]
                                mask_y = block["mask_y"]
                                mask_w = block["mask_width"]
                                mask_h = block["mask_height"]
                                if scroll_clip:
                                    mask_x, mask_y, mask_w, mask_h = scroll_clip

                                image_instance.update_all(
                                    image_name=block["image_name"],
                                    pos=[block["x_pos"], block["y_pos"]],
                                    size=[block["width"], block["height"]],
                                    mask=[mask_x, mask_y, mask_w, mask_h],
                                    aspect_ratio=block["aspect_ratio"],
                                    align_h=block.get("align_h", "LEFT").upper(),
                                    align_v=block.get("align_v", "TOP").upper(),
                                    opacity=block.get("opacity", 1.0),
                                )

                        # Update text input positions — only for containers inside scroll areas
                        from . import text_input_op

                        for input_instance in text_input_op._text_input_instances:
                            container_id = input_instance.container_id
                            if container_id in parser_op.text_input_blocks:
                                idx = _render_data._container_id_to_index.get(container_id, -1)
                                if idx < 0 or idx >= len(acc):
                                    continue
                                sx, sy = acc[idx]

                                block = parser_op.text_input_blocks[container_id]
                                scroll_clip = _render_data._get_scroll_clip_for_container(idx, hit_op._container_data)

                                if not scroll_clip and sx == 0.0 and sy == 0.0:
                                    continue

                                block = parser_op.text_input_blocks[container_id]
                                scroll_clip = _render_data._get_scroll_clip_for_container(idx, hit_op._container_data)

                                mask_x = block["mask_x"]
                                mask_y = block["mask_y"]
                                mask_w = block["mask_width"]
                                mask_h = block["mask_height"]
                                if scroll_clip:
                                    mask_x, mask_y, mask_w, mask_h = scroll_clip

                                bpy.ops.xwz.update_text_input(
                                    instance_id=input_instance.id,
                                    placeholder=block["placeholder"],
                                    font_name=block["font"],
                                    size=block["font_size"],
                                    x_pos=block["x_pos"],
                                    y_pos=block["y_pos"],
                                    color=block["color"],
                                    mask_x=mask_x,
                                    mask_y=mask_y,
                                    mask_width=mask_w,
                                    mask_height=mask_h,
                                    align_h=block.get("align_h", "LEFT").upper(),
                                    align_v=block.get("align_v", "TOP").upper(),
                                )

                    texture_changed = True

                if texture_changed or size_changed:
                    if size_changed:
                        from . import hit_op

                        new_data = parser_op._container_json_data
                        old_data = hit_op._container_data

                        if old_data and len(old_data) == len(new_data):
                            for i in range(len(new_data)):
                                runtime_keys = [
                                    "_hovered",
                                    "_prev_hovered",
                                    "_clicked",
                                    "_prev_clicked",
                                    "_toggled",
                                    "_prev_toggled",
                                    "_toggle_value",
                                    "_scroll_value",
                                ]
                                for key in runtime_keys:
                                    if key in old_data[i]:
                                        new_data[i][key] = old_data[i][key]

                        hit_op._container_data = new_data

                        # Re-cache original positions after resize layout
                        _render_data._cache_original_positions(new_data)
                        _render_data._cache_original_text_positions(parser_op.text_blocks)
                        if hasattr(parser_op, "image_blocks"):
                            _render_data._cache_original_image_positions(parser_op.image_blocks)
                        if hasattr(parser_op, "text_input_blocks"):
                            _render_data._cache_original_text_input_positions(parser_op.text_input_blocks)

                        # Clip masks to scroll parent bounds
                        _render_data._apply_initial_scroll_clips(
                            new_data,
                            parser_op.text_blocks,
                            parser_op.image_blocks if hasattr(parser_op, "image_blocks") else None,
                            parser_op.text_input_blocks if hasattr(parser_op, "text_input_blocks") else None,
                        )

                        # Update text instance clips from scroll_clip data
                        from . import text_op as _text_op_resize

                        for text_instance in _text_op_resize._text_instances:
                            cid = text_instance.container_id
                            block = parser_op.text_blocks.get(cid)
                            if block and "scroll_clip" in block:
                                text_instance.clip = list(block["scroll_clip"])
                            else:
                                text_instance.clip = None

                        # Reapply scroll offsets after resize
                        if _render_data._scroll_offsets:
                            _render_data._apply_scroll_to_containers(new_data)
                            _render_data._apply_scroll_to_text(parser_op.text_blocks)
                            if hasattr(parser_op, "image_blocks"):
                                _render_data._apply_scroll_to_images(parser_op.image_blocks)
                            if hasattr(parser_op, "text_input_blocks"):
                                _render_data._apply_scroll_to_text_inputs(parser_op.text_input_blocks)

                    from .hit_op import _container_data

                    if _container_data:
                        _render_data.update_container_buffer_full(_container_data)

            # Conditional tag_redraw — only redraw when something actually changed
            # hover_changed only needs tag_redraw (push constants update), no data texture rebuild
            needs_redraw = (
                texture_changed
                or size_changed
                or hover_changed
                or transitions_active
                or _render_data.force_initial_draw
            )
            if _render_data.force_initial_draw:
                _render_data.force_initial_draw = False
                needs_redraw = True

            if needs_redraw:
                if not _render_data._cached_target_space:
                    from .space_config import get_target_space

                    _render_data._cached_target_space = get_target_space()

                if _render_data._cached_target_space:
                    for area in context.screen.areas:
                        if area.type == _render_data._cached_target_space:
                            area.tag_redraw()
                            break

        return {"PASS_THROUGH"}

    def cancel(self, context):
        global _render_data, _modal_timer

        if _modal_timer:
            context.window_manager.event_timer_remove(_modal_timer)
            _modal_timer = None

        if _render_data:
            _render_data.cleanup()
            _render_data = None

        bpy.ops.xwz.hit_stop()
        scroll_state.stop_scrolling()
        mouse_state.stop_mouse_tracking()
        input_router.reset()


class XWZ_OT_stop_ui(Operator):
    bl_idname = "xwz.stop_ui"
    bl_label = "Stop puree"
    bl_description = "Stop puree UI"

    def execute(self, context):
        global _render_data, _modal_timer, _hot_reload_enabled

        if _modal_timer:
            context.window_manager.event_timer_remove(_modal_timer)
            _modal_timer = None

        if _render_data:
            _render_data.cleanup()
            _render_data = None

        if _hot_reload_enabled:
            try:
                from .hot_reload import cleanup_hot_reload

                cleanup_hot_reload()
                _hot_reload_enabled = False
            except Exception as e:
                logger.warning(f"Hot reload cleanup error: {e}")

        bpy.ops.xwz.hit_stop()
        scroll_state.stop_scrolling()
        mouse_state.stop_mouse_tracking()
        input_router.reset()

        try:
            bpy.ops.xwz.clear_text()
            bpy.ops.xwz.clear_text_inputs()
            bpy.ops.xwz.clear_images()
        except Exception:
            pass

        from .space_config import get_target_space

        target_space = get_target_space()

        for area in context.screen.areas:
            if area.type == target_space:
                area.tag_redraw()

        logger.info("Compute shader demo stopped")
        return {"FINISHED"}


classes = [
    XWZ_OT_start_ui,
    XWZ_OT_stop_ui,
    XWZ_OT_scroll,
    XWZ_OT_scroll_launch,
    XWZ_OT_mouse,
    XWZ_OT_mouse_launch,
    XWZ_OT_ui_parser,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    global _render_data, _modal_timer

    if _modal_timer:
        try:
            context = bpy.context
            context.window_manager.event_timer_remove(_modal_timer)
        except Exception:
            pass
        _modal_timer = None

    if _render_data:
        _render_data.cleanup()
        _render_data = None

    scroll_state.stop_scrolling()
    mouse_state.stop_mouse_tracking()

    try:
        import gc
        import sys

        gc.collect()

        modules_to_remove = [name for name in sys.modules.keys() if name.startswith("moderngl")]
        for module_name in modules_to_remove:
            if module_name in sys.modules:
                try:
                    del sys.modules[module_name]
                except Exception:
                    pass

        gc.collect()

    except Exception:
        pass

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
