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
import gpu
import os
import time
import moderngl as mgl
from .components.container import container_default
import numpy as np
import traceback

from gpu_extras.batch import batch_for_shader
from bpy.types import Operator, Panel

from .scroll_op import scroll_state, XWZ_OT_scroll, XWZ_OT_scroll_launch
from .mouse_op import mouse_state, XWZ_OT_mouse, XWZ_OT_mouse_launch
from .parser_op import XWZ_OT_ui_parser
from . import parser_op

_render_data = None
_modal_timer = None
_hot_reload_enabled = False
_debug_outlined_containers = set()

class RenderPipeline:
    def __init__(self):
        self.mgl_context     = None
        self.compute_shader  = None
        self.outline_shader  = None
        self.mouse_buffer    = None
        self.container_buffer = None
        self.viewport_buffer = None
        self.output_texture  = None
        self.outline_texture = None
        self.debug_outline_buffer = None
        self.debug_outline_count_buffer = None
        self.blender_texture = None
        self.gpu_shader      = None
        self.batch           = None
        self.draw_handler    = None
        self.running         = False
        self.debug_outlined_containers = set()
        self.mouse_pos       = [0.5, 0.5]
        self.start_time      = time.time()
        self.texture_size    = (1920, 1080)
        self.click_value     = 0.0
        self.scroll_callback_registered = False
        self.mouse_callback_registered = False
        self.region_size     = (1, 1)
        self.container_data  = []
        self.frame_times     = []
        self.compute_fps     = 0.0
        self.last_frame_time = time.perf_counter()
        self.needs_texture_update = True
        self.texture_needs_readback = True  # Flag for draw_texture to know if readback is needed
        self.last_mouse_pos = [0.5, 0.5]
        self.last_click_value = 0.0
        self.last_scroll_value = 0.0
        self.click_frames_remaining = 0
        self.last_container_update = 0
        self.conf_path = 'xwz.ui.toml'
        self.pbos            = []
        self.pbo_index       = 0
        self.pbo_count       = 3
        self.force_initial_draw = True  # Force first draw regardless of changes
    def _safe_release_moderngl_object(self, obj):
        """Safely release a ModernGL object, checking if it's valid first"""
        if obj and hasattr(obj, 'mglo'):
            try:
                if type(obj.mglo).__name__ != 'InvalidObject':
                    obj.release()
                return True
            except Exception:
                return False
        return False
    def load_shader_file(self, filename):
        package_dir = os.path.dirname(os.path.abspath(__file__))
        shader_path = os.path.join(package_dir, "shaders", filename)
        try:
            with open(shader_path, 'r') as f:
                return f.read()
        except Exception:
            return None
    def load_container_data(self):
        try:  
            wm = bpy.context.window_manager
            bpy.ops.xwz.parse_app_ui(conf_path=wm.xwz_ui_conf_path)
            self.container_data = parser_op._container_json_data
            return True
        except Exception:
            return False
    def init_moderngl_context(self):
        try:
            self.mgl_context = mgl.get_context()
            self.mgl_context.gc_mode = 'context_gc'
            return True
        except Exception:
            return False
    def create_compute_shader(self):
        shader_source = self.load_shader_file("container.glsl")
        if not shader_source:
            return False
        try:
            self.compute_shader = self.mgl_context.compute_shader(shader_source)
            return True
        except Exception:
            return False
    
    def create_outline_shader(self):
        shader_source = self.load_shader_file("outline.glsl")
        if not shader_source:
            return False
        try:
            self.outline_shader = self.mgl_context.compute_shader(shader_source)
            return True
        except Exception:
            return False
    def create_buffers_and_textures(self):
        try:
            mouse_data = np.array([0.5, 0.5, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)
            self.mouse_buffer = self.mgl_context.buffer(mouse_data.tobytes())
            
            container_array = []
            for i, container in enumerate(self.container_data):
                container_struct = [
                    int(container.get('display', False)),
                    container.get('position', [0, 0])[0], container.get('position', [0, 0])[1],
                    container.get('size', [100, 100])[0], container.get('size', [100, 100])[1],
                    container.get('color', [1, 1, 1, 1])[0], container.get('color', [1, 1, 1, 1])[1], 
                    container.get('color', [1, 1, 1, 1])[2], container.get('color', [1, 1, 1, 1])[3],
                    container.get('color_1', [1, 1, 1, 1])[0], container.get('color_1', [1, 1, 1, 1])[1], 
                    container.get('color_1', [1, 1, 1, 1])[2], container.get('color_1', [1, 1, 1, 1])[3],
                    container.get('color_gradient_rot', 0.0),
                    container.get('hover_color', container_default.hover_color)[0], container.get('hover_color', container_default.hover_color)[1], 
                    container.get('hover_color', container_default.hover_color)[2], container.get('hover_color', container_default.hover_color)[3],
                    container.get('hover_color_1', container_default.hover_color_1)[0], container.get('hover_color_1', container_default.hover_color_1)[1], 
                    container.get('hover_color_1', container_default.hover_color_1)[2], container.get('hover_color_1', container_default.hover_color_1)[3],
                    container.get('hover_color_gradient_rot', 0.0),
                    container.get('click_color', container_default.click_color)[0], container.get('click_color', container_default.click_color)[1], 
                    container.get('click_color', container_default.click_color)[2], container.get('click_color', container_default.click_color)[3],
                    container.get('click_color_1', container_default.click_color_1)[0], container.get('click_color_1', container_default.click_color_1)[1], 
                    container.get('click_color_1', container_default.click_color_1)[2], container.get('click_color_1', container_default.click_color_1)[3],
                    container.get('click_color_gradient_rot', 0.0),
                    container.get('border_color', [1, 1, 1, 1])[0], container.get('border_color', [1, 1, 1, 1])[1], 
                    container.get('border_color', [1, 1, 1, 1])[2], container.get('border_color', [1, 1, 1, 1])[3],
                    container.get('border_color_1', [1, 1, 1, 1])[0], container.get('border_color_1', [1, 1, 1, 1])[1], 
                    container.get('border_color_1', [1, 1, 1, 1])[2], container.get('border_color_1', [1, 1, 1, 1])[3],
                    container.get('border_color_gradient_rot', 0.0),
                    container.get('border_radius', 0.0),
                    container.get('border_width', 0.0),
                    container.get('parent', -1),
                    int(container.get('overflow', False)),
                    container.get('box_shadow_offset', [0, 0, 0])[0], container.get('box_shadow_offset', [0, 0, 0])[1], 
                    container.get('box_shadow_offset', [0, 0, 0])[2],
                    container.get('box_shadow_blur', 0.0),
                    container.get('box_shadow_color', [0, 0, 0, 0])[0], container.get('box_shadow_color', [0, 0, 0, 0])[1], 
                    container.get('box_shadow_color', [0, 0, 0, 0])[2], container.get('box_shadow_color', [0, 0, 0, 0])[3],
                    int(container.get('passive', False))
                ]
                container_array.extend(container_struct)
            
            container_data_np = np.array(container_array, dtype=np.float32)
            self.container_buffer = self.mgl_context.buffer(container_data_np.tobytes())
            
            viewport_data = np.array([self.region_size[0], self.region_size[1], len(self.container_data)], dtype=np.float32)
            self.viewport_buffer = self.mgl_context.buffer(viewport_data.tobytes())
            
            self.texture_size = self.region_size
            
            self.output_texture = self.mgl_context.texture(
                self.texture_size, 
                4
            )
            self.output_texture.filter = (mgl.NEAREST, mgl.NEAREST)
            
            pixel_size = self.texture_size[0] * self.texture_size[1] * 4
            self.pbos = []
            for i in range(self.pbo_count):
                pbo = self.mgl_context.buffer(reserve=pixel_size)
                self.pbos.append(pbo)
            
            self.outline_texture = self.mgl_context.texture(
                self.texture_size, 
                4
            )
            self.outline_texture.filter = (mgl.NEAREST, mgl.NEAREST)
            
            outline_ids = np.array([], dtype=np.int32)
            self.debug_outline_buffer = self.mgl_context.buffer(reserve=400)
            
            outline_count = np.array([0], dtype=np.int32)
            self.debug_outline_count_buffer = self.mgl_context.buffer(outline_count.tobytes())
            
            return True
        except Exception:
            return False
    def create_blender_gpu_shader(self):
        vert_source = self.load_shader_file("vertex.glsl")
        frag_source = self.load_shader_file("fragment.glsl")
        
        if not (vert_source and frag_source):
            return False
            
        try:
            shader_info = gpu.types.GPUShaderCreateInfo()
            
            shader_info.vertex_in(0, 'VEC2', 'position')
            shader_info.vertex_in(1, 'VEC2', 'texCoord_0')
            
            interface = gpu.types.GPUStageInterfaceInfo("default_interface")
            interface.smooth('VEC2', 'fragTexCoord')
            shader_info.vertex_out(interface)
            
            shader_info.sampler(0, 'FLOAT_2D', 'inputTexture')
            shader_info.push_constant('FLOAT', 'opacity')
            
            shader_info.fragment_out(0, 'VEC4', 'fragColor')
            
            shader_info.vertex_source(vert_source)
            shader_info.fragment_source(frag_source)
            
            self.gpu_shader = gpu.shader.create_from_info(shader_info)
            return True
        except Exception:
            return False
    def create_fullscreen_quad(self):
        try:
            vertices = [
                (-1, -1),
                ( 1, -1),
                ( 1,  1),
                (-1,  1),
            ]
            
            texcoords = [
                (0, 0),
                (1, 0),
                (1, 1),
                (0, 1),
            ]
            
            indices = [
                (0, 1, 2),
                (0, 2, 3),
            ]
            
            self.batch = batch_for_shader(
                self.gpu_shader, 
                'TRIS',
                {
                    "position": vertices,
                    "texCoord_0": texcoords,
                },
                indices=indices
            )
            return True
        except Exception:
            return False
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
            updated_container_data = parser_op.recompute_layout((w, h))
            
            if updated_container_data:
                self.container_data = updated_container_data
                
                container_array = []
                for i, container in enumerate(self.container_data):
                    container_struct = [
                        int(container.get('display', False)),
                        container.get('position', [0, 0])[0], container.get('position', [0, 0])[1],
                        container.get('size', [100, 100])[0], container.get('size', [100, 100])[1],
                        container.get('color', [1, 1, 1, 1])[0], container.get('color', [1, 1, 1, 1])[1], 
                        container.get('color', [1, 1, 1, 1])[2], container.get('color', [1, 1, 1, 1])[3],
                        container.get('color_1', [1, 1, 1, 1])[0], container.get('color_1', [1, 1, 1, 1])[1], 
                        container.get('color_1', [1, 1, 1, 1])[2], container.get('color_1', [1, 1, 1, 1])[3],
                        container.get('color_gradient_rot', 0.0),
                        container.get('hover_color', container_default.hover_color)[0], container.get('hover_color', container_default.hover_color)[1], 
                        container.get('hover_color', container_default.hover_color)[2], container.get('hover_color', container_default.hover_color)[3],
                        container.get('hover_color_1', container_default.hover_color_1)[0], container.get('hover_color_1', container_default.hover_color_1)[1], 
                        container.get('hover_color_1', container_default.hover_color_1)[2], container.get('hover_color_1', container_default.hover_color_1)[3],
                        container.get('hover_color_gradient_rot', 0.0),
                        container.get('click_color', container_default.click_color)[0], container.get('click_color', container_default.click_color)[1], 
                        container.get('click_color', container_default.click_color)[2], container.get('click_color', container_default.click_color)[3],
                        container.get('click_color_1', container_default.click_color_1)[0], container.get('click_color_1', container_default.click_color_1)[1], 
                        container.get('click_color_1', container_default.click_color_1)[2], container.get('click_color_1', container_default.click_color_1)[3],
                        container.get('click_color_gradient_rot', 0.0),
                        container.get('border_color', [1, 1, 1, 1])[0], container.get('border_color', [1, 1, 1, 1])[1], 
                        container.get('border_color', [1, 1, 1, 1])[2], container.get('border_color', [1, 1, 1, 1])[3],
                        container.get('border_color_1', [1, 1, 1, 1])[0], container.get('border_color_1', [1, 1, 1, 1])[1], 
                        container.get('border_color_1', [1, 1, 1, 1])[2], container.get('border_color_1', [1, 1, 1, 1])[3],
                        container.get('border_color_gradient_rot', 0.0),
                        container.get('border_radius', 0.0),
                        container.get('border_width', 0.0),
                        container.get('parent', -1),
                        int(container.get('overflow', False)),
                        container.get('box_shadow_offset', [0, 0, 0])[0], container.get('box_shadow_offset', [0, 0, 0])[1], 
                        container.get('box_shadow_offset', [0, 0, 0])[2],
                        container.get('box_shadow_blur', 0.0),
                        container.get('box_shadow_color', [0, 0, 0, 0])[0], container.get('box_shadow_color', [0, 0, 0, 0])[1], 
                        container.get('box_shadow_color', [0, 0, 0, 0])[2], container.get('box_shadow_color', [0, 0, 0, 0])[3],
                        int(container.get('passive', False))
                    ]
                    container_array.extend(container_struct)
                
                if self.container_buffer:
                    container_data_np = np.array(container_array, dtype=np.float32)
                    self.container_buffer.write(container_data_np.tobytes())
        
        if self.viewport_buffer:
            viewport_data = np.array([w, h, len(self.container_data)], dtype=np.float32)
            self.viewport_buffer.write(viewport_data.tobytes())
        
        if size_changed and self.output_texture:
            if self.blender_texture:
                self.blender_texture = None
            
            if self._safe_release_moderngl_object(self.output_texture):
                self.texture_size = self.region_size
                self.output_texture = self.mgl_context.texture(
                    self.texture_size,
                    4
                )
                self.output_texture.filter = (mgl.NEAREST, mgl.NEAREST)
                self.needs_texture_update = True
                
                for pbo in self.pbos:
                    self._safe_release_moderngl_object(pbo)
                self.pbos = []
                
                pixel_size = self.texture_size[0] * self.texture_size[1] * 4
                for i in range(self.pbo_count):
                    pbo = self.mgl_context.buffer(reserve=pixel_size)
                    self.pbos.append(pbo)
                self.pbo_index = 0
        
        return size_changed
    def update_click_value(self, value):
        self.click_value = value
        self.write_mouse_buffer()
    def on_scroll(self, delta, absolute_value):
        self.write_mouse_buffer()
    def on_mouse_event(self, event_type, data):
        if event_type == 'mouse':
            self.mouse_pos[0] = max(0.0, min(1.0, (data[0] + 1.0) / 2.0))
            self.mouse_pos[1] = max(0.0, min(1.0, (data[1] + 1.0) / 2.0))
        elif event_type == 'click':
            self.click_value = 1.0 if data else 0.0
        self.write_mouse_buffer()
    def write_mouse_buffer(self):
        if not self.mouse_buffer:
            return
        current_time = time.time() - self.start_time
        scroll_value = float(scroll_state.scroll_value)
        mouse_data = np.array([
            self.mouse_pos[0],
            self.mouse_pos[1],
            current_time,
            scroll_value,
            self.click_value,
            0.0
        ], dtype=np.float32)
        self.mouse_buffer.write(mouse_data.tobytes())
    
    def update_fps(self):
        current_time = time.perf_counter()
        frame_time = current_time - self.last_frame_time
        self.last_frame_time = current_time
        
        self.frame_times.append(frame_time)
        if len(self.frame_times) > 60:
            self.frame_times.pop(0)
        
        if len(self.frame_times) > 0:
            avg_frame_time = sum(self.frame_times) / len(self.frame_times)
            self.compute_fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0.0
    
    def check_if_changed(self):
        """Check if texture needs updating and update state. Called from modal loop."""
        changed = False
        
        # Force initial draw if this is the first check
        if self.force_initial_draw:
            self.force_initial_draw = False
            changed = True
        
        if (abs(self.mouse_pos[0] - self.last_mouse_pos[0]) > 0.001 or 
            abs(self.mouse_pos[1] - self.last_mouse_pos[1]) > 0.001):
            self.last_mouse_pos = self.mouse_pos.copy()
            changed = True
        
        if self.click_value != self.last_click_value:
            self.last_click_value = self.click_value
            self.click_frames_remaining = 3
            changed = True
        
        if self.click_frames_remaining > 0:
            self.click_frames_remaining -= 1
            changed = True
        
        current_scroll = float(scroll_state.scroll_value)
        if abs(current_scroll - self.last_scroll_value) > 0.001:
            self.last_scroll_value = current_scroll
            changed = True
        
        if self.needs_texture_update:
            self.needs_texture_update = False
            changed = True
        
        self.texture_needs_readback = changed
        
        return changed
    
    def has_texture_changed(self):
        return self.texture_needs_readback
    
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
        if not (self.compute_shader and self.mouse_buffer and self.container_buffer and 
                self.viewport_buffer and self.output_texture):
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
            return False
    def initialize(self):
        from .space_config import find_target_area_and_region
        
        area, region = find_target_area_and_region()
        if area and region:
            self.region_size = (region.width, region.height)
        else:
            print("Warning: Target space not found, using fallback size")
            self.region_size = (800, 600)
        
        if not self.load_container_data():
            return False
        if not self.init_moderngl_context():
            return False
        if not self.create_compute_shader():
            return False
        if not self.create_outline_shader():
            return False
        if not self.create_buffers_and_textures():
            return False
        if not self.create_blender_gpu_shader():
            return False
        if not self.create_fullscreen_quad():
            return False

        scroll_state.register_callback(self.on_scroll)
        self.scroll_callback_registered = True
        
        mouse_state.register_callback(self.on_mouse_event)
        self.mouse_callback_registered = True
        
        self.running = True
        self.write_mouse_buffer()
        
        self.needs_texture_update = True
        
        self.add_drawing_callback()
        
        # Force initial render to ensure content appears immediately
        self.run_compute_shader()
        self.texture_needs_readback = True
        
        return True
    def add_drawing_callback(self):
        from .space_config import get_space_class
        
        space_class = get_space_class()
        if not space_class:
            print("Warning: No valid space class found, falling back to SpaceView3D")
            space_class = bpy.types.SpaceView3D
        
        self.draw_handler = space_class.draw_handler_add(
            self.draw_texture, (), 'WINDOW', 'POST_PIXEL'
        )
    def draw_texture(self):
        if not (self.running and self.gpu_shader and self.batch and self.output_texture):
            return
            
        try:
            if not self.has_texture_changed():
                if self.blender_texture:
                    gpu.state.blend_set('ALPHA')
                    gpu.state.depth_test_set('NONE')
                    
                    self.gpu_shader.bind()
                    self.gpu_shader.uniform_sampler("inputTexture", self.blender_texture)
                    self.gpu_shader.uniform_float("opacity", 1.0)
                    
                    gpu.matrix.push()
                    gpu.matrix.load_identity()
                    
                    self.batch.draw(self.gpu_shader)
                    gpu.matrix.pop()
                    
                    gpu.state.blend_set('NONE')
                    gpu.state.depth_test_set('LESS_EQUAL')
                return
            
            if not self.pbos or len(self.pbos) < self.pbo_count:
                return
            
            advanced = False
            try:
                current_pbo = self.pbos[self.pbo_index]
                self.output_texture.read_into(current_pbo)

                read_index = (self.pbo_index + 2) % self.pbo_count
                read_pbo = self.pbos[read_index]

                texture_data = read_pbo.read()

                expected_size = self.texture_size[0] * self.texture_size[1] * 4
                if len(texture_data) != expected_size:
                    if len(texture_data) > expected_size:
                        texture_data = texture_data[:expected_size]
                    else:
                        raise RuntimeError(f"texture_data too small: {len(texture_data)} < {expected_size}")

                texture_array = np.frombuffer(texture_data, dtype=np.uint8)
                texture_float = np.multiply(texture_array, 0.00392156862745098, dtype=np.float32)
                
                buffer = gpu.types.Buffer('FLOAT', len(texture_float), texture_float)

                if self.blender_texture:
                    try:
                        del self.blender_texture
                    except Exception:
                        pass

                self.blender_texture = gpu.types.GPUTexture(
                    self.texture_size,
                    format = 'RGBA8',
                    data   = buffer
                )

                advanced = True
                self.texture_needs_readback = False

                gpu.state.blend_set('ALPHA')
                gpu.state.depth_test_set('NONE')

                self.gpu_shader.bind()
                self.gpu_shader.uniform_sampler("inputTexture", self.blender_texture)
                self.gpu_shader.uniform_float("opacity", 1.0)

                gpu.matrix.push()
                gpu.matrix.load_identity()

                self.batch.draw(self.gpu_shader)
                gpu.matrix.pop()

                gpu.state.blend_set('NONE')
                gpu.state.depth_test_set('LESS_EQUAL')
            except Exception as e:
                traceback.print_exc()
            finally:
                if advanced:
                    self.pbo_index = (self.pbo_index + 1) % self.pbo_count
            
        except Exception:
            pass
    
    def cleanup(self):
        self.running = False
        
        if self.draw_handler:
            from .space_config import get_space_class
            
            space_class = get_space_class()
            if not space_class:
                space_class = bpy.types.SpaceView3D
            
            space_class.draw_handler_remove(self.draw_handler, 'WINDOW')
            self.draw_handler = None
        
        if self.blender_texture:
            self.blender_texture = None
        
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
        
        for pbo in self.pbos:
            self._safe_release_moderngl_object(pbo)
        self.pbos = []
        self.pbo_index = 0
        
        if self.mgl_context:
            try:
                self.mgl_context.gc()
            except AttributeError as e:
                if "'InvalidObject' object has no attribute 'release'" not in str(e):
                    pass
            except Exception:
                pass
            finally:
                self.mgl_context = None
        
        try:
            import gc
            gc.collect()
        except:
            pass
        
        if self.scroll_callback_registered:
            scroll_state.unregister_callback(self.on_scroll)
            self.scroll_callback_registered = False
        
        if self.mouse_callback_registered:
            mouse_state.unregister_callback(self.on_mouse_event)
            self.mouse_callback_registered = False
    def update_container_buffer_full(self, hit_container_data):
        if not self.container_buffer or not hit_container_data:
            return False
        
        try:
            container_array = []
            updates_made = 0
            
            for i, container in enumerate(hit_container_data):
                state_changed = (
                    container.get('_hovered', False) != container.get('_prev_hovered', False) or
                    container.get('_clicked', False) != container.get('_prev_clicked', False)
                )
                
                if state_changed:
                    updates_made += 1
                
                current_color = container.get('color', [1, 1, 1, 1]).copy()
                current_color_1 = container.get('color_1', [1, 1, 1, 1]).copy()
                
                container_struct = [
                    int(container.get('display', False)),
                    container.get('position', [0, 0])[0], container.get('position', [0, 0])[1],
                    container.get('size', [100, 100])[0], container.get('size', [100, 100])[1],
                    current_color[0], current_color[1], current_color[2], current_color[3],
                    current_color_1[0], current_color_1[1], current_color_1[2], current_color_1[3],
                    container.get('color_gradient_rot', 0.0),
                    container.get('hover_color', container_default.hover_color)[0], container.get('hover_color', container_default.hover_color)[1], 
                    container.get('hover_color', container_default.hover_color)[2], container.get('hover_color', container_default.hover_color)[3],
                    container.get('hover_color_1', container_default.hover_color_1)[0], container.get('hover_color_1', container_default.hover_color_1)[1], 
                    container.get('hover_color_1', container_default.hover_color_1)[2], container.get('hover_color_1', container_default.hover_color_1)[3],
                    container.get('hover_color_gradient_rot', 0.0),
                    container.get('click_color', container_default.click_color)[0], container.get('click_color', container_default.click_color)[1], 
                    container.get('click_color', container_default.click_color)[2], container.get('click_color', container_default.click_color)[3],
                    container.get('click_color_1', container_default.click_color_1)[0], container.get('click_color_1', container_default.click_color_1)[1], 
                    container.get('click_color_1', container_default.click_color_1)[2], container.get('click_color_1', container_default.click_color_1)[3],
                    container.get('click_color_gradient_rot', 0.0),
                    container.get('border_color', [1, 1, 1, 1])[0], container.get('border_color', [1, 1, 1, 1])[1], 
                    container.get('border_color', [1, 1, 1, 1])[2], container.get('border_color', [1, 1, 1, 1])[3],
                    container.get('border_color_1', [1, 1, 1, 1])[0], container.get('border_color_1', [1, 1, 1, 1])[1], 
                    container.get('border_color_1', [1, 1, 1, 1])[2], container.get('border_color_1', [1, 1, 1, 1])[3],
                    container.get('border_color_gradient_rot', 0.0),
                    container.get('border_radius', 0.0),
                    container.get('border_width', 0.0),
                    container.get('parent', -1),
                    int(container.get('overflow', False)),
                    container.get('box_shadow_offset', [0, 0, 0])[0], container.get('box_shadow_offset', [0, 0, 0])[1], 
                    container.get('box_shadow_offset', [0, 0, 0])[2],
                    container.get('box_shadow_blur', 0.0),
                    container.get('box_shadow_color', [0, 0, 0, 0])[0], container.get('box_shadow_color', [0, 0, 0, 0])[1], 
                    container.get('box_shadow_color', [0, 0, 0, 0])[2], container.get('box_shadow_color', [0, 0, 0, 0])[3],
                    int(container.get('passive', False))
                ]
                container_array.extend(container_struct)
            
            # Update entire buffer
            container_data_np = np.array(container_array, dtype=np.float32)
            self.container_buffer.write(container_data_np.tobytes())
            
            if updates_made > 0:
                self.needs_texture_update = True
            
            return True
        except Exception:
            return False

class XWZ_OT_start_ui(Operator):
    bl_idname      = "xwz.start_ui"
    bl_label       = "Start puree"
    bl_description = "Start puree UI"
    
    def execute(self, context):
        global _render_data, _modal_timer
        
        if _render_data and _render_data.running:
            self.report({'WARNING'}, "Demo already running")
            return {'CANCELLED'}
        
        _render_data = RenderPipeline()
        
        if not _render_data.initialize():
            self.report({'ERROR'}, "Failed to initialize compute shader demo")
            _render_data = None
            return {'CANCELLED'}

        # Start native-optimized hit detection
        try:
            bpy.ops.xwz.hit_detect('INVOKE_DEFAULT')
        except Exception as e:
            self.report({'WARNING'}, f"Failed to start hit detect modal: {e}")

        try:
            bpy.ops.xwz.scroll_modal_launch('INVOKE_DEFAULT')
        except Exception as e:
            self.report({'WARNING'}, f"Failed to start scroll modal: {e}")
        
        try:
            bpy.ops.xwz.mouse_modal_launch('INVOKE_DEFAULT')
        except Exception as e:
            self.report({'WARNING'}, f"Failed to start mouse modal: {e}")
        
        context.window_manager.modal_handler_add(self)
        _modal_timer = context.window_manager.event_timer_add(0.016, window=context.window)
        
        for _container_id in parser_op.image_blocks:
            block = parser_op.image_blocks[_container_id]
            bpy.ops.xwz.draw_image(
                container_id = _container_id,
                image_name   = block['image_name'],
                x_pos        = block['x_pos'],
                y_pos        = block['y_pos'],
                width        = block['width'],
                height       = block['height'],
                mask_x       = block['mask_x'],
                mask_y       = block['mask_y'],
                mask_width   = block['mask_width'],
                mask_height  = block['mask_height'],
                aspect_ratio = block['aspect_ratio'],
                align_h      = block.get('align_h', 'LEFT').upper(),
                align_v      = block.get('align_v', 'TOP').upper(),
                opacity      = block.get('opacity', 1.0)
            )
        
        for _container_id in parser_op.text_blocks:
            block = parser_op.text_blocks[_container_id]
            bpy.ops.xwz.draw_text(
                container_id = _container_id,
                text          = block['text'],
                font_name     = block['font'],
                size          = block['text_scale'],
                x_pos         = block['text_x'],
                y_pos         = block['text_y'],
                color         = block['text_color'],
                mask_x        = block['mask_x'],
                mask_y        = block['mask_y'],
                mask_width    = block['mask_width'],
                mask_height   = block['mask_height'],
                align_h       = block.get('align_h', 'LEFT').upper(),
                align_v       = block.get('align_v', 'CENTER').upper()
            )
        
        for _container_id in parser_op.text_input_blocks:
            block = parser_op.text_input_blocks[_container_id]
            bpy.ops.xwz.create_text_input(
                container_id = _container_id,
                placeholder  = block['placeholder'],
                font_name    = block['font'],
                size         = block['text_scale'],
                x_pos        = block['x_pos'],
                y_pos        = block['y_pos'],
                color        = block['text_color'],
                mask_x       = block['mask_x'],
                mask_y       = block['mask_y'],
                mask_width   = block['mask_width'],
                mask_height  = block['mask_height'],
                align_h      = block.get('align_h', 'LEFT').upper(),
                align_v      = block.get('align_v', 'TOP').upper()
            )

        try:
            from .hot_reload import setup_hot_reload, register_default_callbacks, get_hot_reload_manager
            from . import get_addon_root
            
            addon_dir = get_addon_root()
            if setup_hot_reload(addon_dir):
                register_default_callbacks()
                manager = get_hot_reload_manager()
                manager.enable()
                
                global _hot_reload_enabled
                _hot_reload_enabled = True
                
                self.report({'INFO'}, "UI Started with hot reload enabled")
            else:
                self.report({'INFO'}, "UI Started (hot reload unavailable)")
        except Exception as e:
            print(f"Hot reload initialization failed: {e}")
            self.report({'INFO'}, "UI Started (hot reload disabled)")
        
        # Update debug panel to appear in the correct space
        try:
            from . import panel
            panel.update_panel_space()
        except Exception as e:
            print(f"Failed to update debug panel space: {e}")
        
        # Force initial redraw to ensure UI appears immediately
        from .space_config import get_target_space
        target_space = get_target_space()
        if target_space:
            for area in context.screen.areas:
                if area.type == target_space:
                    area.tag_redraw()
                    break
        
        return {'RUNNING_MODAL'}
    
    def modal(self, context, event):
        global _render_data
        
        if not (_render_data and _render_data.running):
            self.cancel(context)
            return {'CANCELLED'}
        
        if event.type == 'WINDOW_DEACTIVATE':
            area = context.area
            region = context.region
            
            if area and region:
                size_changed = _render_data.update_region_size(region.width, region.height)
                if size_changed:
                    from .hit_op import _container_data
                    if _container_data:
                        _render_data.update_container_buffer_full(_container_data)
                    
                    _render_data.run_compute_shader()
                    
                    from .space_config import get_target_space
                    target_space = get_target_space()
                    
                    for area in context.screen.areas:
                        if area.type == target_space:
                            area.tag_redraw()
        
        if event.type == 'TIMER':
            from .space_config import find_target_area_and_region
            
            target_area, target_region = find_target_area_and_region()
            
            if target_area and target_region:
                global _hot_reload_enabled
                if _hot_reload_enabled:
                    try:
                        from .hot_reload import get_hot_reload_manager
                        manager = get_hot_reload_manager()
                        manager.check_for_changes()
                    except Exception as e:
                        print(f"Hot reload error: {e}")

                _render_data.update_fps()

                size_changed = _render_data.update_region_size(target_region.width, target_region.height)

                texture_changed = _render_data.check_if_changed()
                
                state_synced = parser_op.sync_dirty_containers()
                if state_synced:
                    from . import hit_op
                    from . import text_op
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
                    
                    texture_changed = True
                
                if texture_changed or size_changed:
                    if size_changed:
                        from . import hit_op
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
                    
                    from .hit_op import _container_data
                    if _container_data:
                        _render_data.update_container_buffer_full(_container_data)
                    
                    _render_data.run_compute_shader()
            
            from .space_config import get_target_space
            target_space = get_target_space()
            
            for area in context.screen.areas:
                if area.type == target_space:
                    area.tag_redraw()

        elif event.type in {'ESC'}:
            self.cancel(context)
            return {'CANCELLED'}
        
        return {'PASS_THROUGH'}
    
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

class XWZ_OT_stop_ui(Operator):
    bl_idname      = "xwz.stop_ui"
    bl_label       = "Stop puree"
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
                print(f"Hot reload cleanup error: {e}")

        bpy.ops.xwz.hit_stop()
        scroll_state.stop_scrolling()
        mouse_state.stop_mouse_tracking()
        
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
            
        self.report({'INFO'}, "Compute shader demo stopped")
        return {'FINISHED'}

classes = [
    XWZ_OT_start_ui,
    XWZ_OT_stop_ui, 
    XWZ_OT_scroll,
    XWZ_OT_scroll_launch,
    XWZ_OT_mouse,
    XWZ_OT_mouse_launch,
    XWZ_OT_ui_parser
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
        except:
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
        
        modules_to_remove = [name for name in sys.modules.keys() if name.startswith('moderngl')]
        for module_name in modules_to_remove:
            if module_name in sys.modules:
                try:
                    del sys.modules[module_name]
                except:
                    pass
        
        gc.collect()
        
    except Exception:
        pass
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)