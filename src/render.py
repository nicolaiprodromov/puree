import bpy
import gpu
import os
import time
import moderngl as mgl
from .components.container import container_default
import numpy as np

from gpu_extras.batch import batch_for_shader
from bpy.types import Operator, Panel

from .scroll_op import scroll_state, XWZ_OT_scroll, XWZ_OT_scroll_launch
from .mouse_op import mouse_state, XWZ_OT_mouse, XWZ_OT_mouse_launch
from .parser_op import XWZ_OT_ui_parser
from . import parser_op

_render_data = None
_modal_timer = None

class RenderPipeline:
    def __init__(self):
        self.mgl_context     = None
        self.compute_shader  = None
        self.mouse_buffer    = None
        self.container_buffer = None
        self.viewport_buffer = None
        self.debug_buffer    = None
        self.output_texture  = None
        self.blender_texture = None
        self.gpu_shader      = None
        self.batch           = None
        self.draw_handler    = None
        self.running         = False
        self.mouse_pos       = [0.5, 0.5]
        self.start_time      = time.time()
        self.texture_size    = (1920, 1080)
        self.click_value     = 0.0
        self.scroll_callback_registered = False
        self.mouse_callback_registered = False
        self.region_size     = (1, 1)
        self.container_data  = []
        self.debug_counter   = 0
        self.frame_times     = []
        self.compute_fps     = 0.0
        self.last_frame_time = time.perf_counter()
        self.dirty_flag_skips = 0
        self.compute_shader_skips = 0  # Track how many frames we skip compute shader
        self.needs_texture_update = True
        self.texture_needs_readback = True  # Flag for draw_texture to know if readback is needed
        self.last_mouse_pos = [0.5, 0.5]
        self.last_click_value = 0.0
        self.last_scroll_value = 0.0
        self.last_container_update = 0
        self.conf_path = 'xwz.ui.toml'
    def _safe_release_moderngl_object(self, obj):
        """Safely release a ModernGL object, checking if it's valid first"""
        if obj and hasattr(obj, 'mglo'):
            try:
                # Check if the object is still valid (not an InvalidObject)
                if type(obj.mglo).__name__ != 'InvalidObject':
                    obj.release()
                return True
            except Exception as e:
                print(f"Warning: Error releasing ModernGL object: {e}")
                return False
        return False
    def load_shader_file(self, filename):
        addon_dir   = os.path.dirname(os.path.dirname(__file__))
        shader_path = os.path.join(addon_dir, "src", "shaders", filename)
        try:
            with open(shader_path, 'r') as f:
                return f.read()
        except Exception as e:
            print(f"Failed to load shader {filename}: {e}")
            return None
    def load_container_data(self):
        try:  
            wm = bpy.context.window_manager
            bpy.ops.xwz.parse_app_ui(conf_path=wm.xwz_ui_conf_path)
            self.container_data = parser_op._container_json_data
            return True
        except Exception as e:
            print(f"Failed to load container data: {e}")
            return False
    def init_moderngl_context(self):
        try:
            self.mgl_context = mgl.get_context()
            # Set gc_mode to 'context_gc' for proper cleanup when using detected contexts
            # This prevents crashes on exit and ensures resources are properly managed
            self.mgl_context.gc_mode = 'context_gc'
            return True
        except Exception as e:
            print(f"Failed to get ModernGL context: {e}")
            return False
    def create_compute_shader(self):
        shader_source = self.load_shader_file("container.glsl")
        if not shader_source:
            return False
        try:
            self.compute_shader = self.mgl_context.compute_shader(shader_source)
            return True
        except Exception as e:
            print(f"Failed to compile compute shader: {e}")
            return False
    def create_buffers_and_textures(self):
        try:
            mouse_data = np.array([0.5, 0.5, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)
            self.mouse_buffer = self.mgl_context.buffer(mouse_data.tobytes())
            
            print(f"Creating buffers for {len(self.container_data)} containers")
            
            container_array = []
            for i, container in enumerate(self.container_data):
                print(f"Container {i}: display={container.get('display')}, pos={container.get('position')}, size={container.get('size')}")
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
                    container.get('box_shadow_color', [0, 0, 0, 0])[2], container.get('box_shadow_color', [0, 0, 0, 0])[3]
                ]
                container_array.extend(container_struct)
            
            container_data_np = np.array(container_array, dtype=np.float32)
            self.container_buffer = self.mgl_context.buffer(container_data_np.tobytes())
            
            viewport_data = np.array([self.region_size[0], self.region_size[1], len(self.container_data)], dtype=np.float32)
            print(f"Viewport data: {viewport_data}")
            self.viewport_buffer = self.mgl_context.buffer(viewport_data.tobytes())
            
            debug_data = np.zeros(32, dtype=np.float32)
            self.debug_buffer = self.mgl_context.buffer(debug_data.tobytes())
            
            # Use viewport size instead of hardcoded texture size
            self.texture_size = self.region_size
            
            self.output_texture = self.mgl_context.texture(
                self.texture_size, 
                4
            )
            self.output_texture.filter = (mgl.NEAREST, mgl.NEAREST)
            return True
        except Exception as e:
            print(f"Failed to create buffers/textures: {e}")
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
        except Exception as e:
            print(f"Failed to create modern Blender GPU shader: {e}")
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
        except Exception as e:
            print(f"Failed to create fullscreen quad: {e}")
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
        
        if self.viewport_buffer:
            viewport_data = np.array([w, h, len(self.container_data)], dtype=np.float32)
            self.viewport_buffer.write(viewport_data.tobytes())
        
        # CRITICAL: Recreate texture if size changed
        if old_region_size != self.region_size and self.output_texture:
            # Clear the Blender texture wrapper first
            if self.blender_texture:
                self.blender_texture = None
            
            if self._safe_release_moderngl_object(self.output_texture):
                self.texture_size = self.region_size
                self.output_texture = self.mgl_context.texture(
                    self.texture_size,
                    4
                )
                self.output_texture.filter = (mgl.NEAREST, mgl.NEAREST)
                # Reset dirty flag system for new texture
                self.needs_texture_update = True
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
    def debug_print_buffer_data(self):
        try:
            if self.mouse_buffer:
                mouse_data = self.mouse_buffer.read()
                mouse_floats = np.frombuffer(mouse_data, dtype=np.float32)
                print(f"Mouse buffer: {mouse_floats}")
            
            if self.viewport_buffer:
                viewport_data = self.viewport_buffer.read()
                viewport_floats = np.frombuffer(viewport_data, dtype=np.float32)
                print(f"Viewport buffer: {viewport_floats}")
            
            if self.container_buffer and len(self.container_data) > 0:
                container_data = self.container_buffer.read()
                container_floats = np.frombuffer(container_data, dtype=np.float32)
                container_size = 53
                first_container = container_floats[:container_size]
                print(f"First container data ({container_size} values): {first_container[:10]}...")
                
        except Exception as e:
            print(f"Error reading buffer data: {e}")
    def read_debug_buffer(self):
        try:
            if self.debug_buffer:
                self.debug_counter += 1
                if self.debug_counter % 120 == 0:
                    debug_data = self.debug_buffer.read()
                    debug_floats = np.frombuffer(debug_data, dtype=np.float32)
                    
                    # Calculate skip percentages
                    texture_skip_pct = (self.dirty_flag_skips / max(1, self.debug_counter)) * 100
                    compute_skip_pct = (self.compute_shader_skips / max(1, self.debug_counter)) * 100
                    
                    print(f"=== PERFORMANCE STATS ===")
                    print(f"Frame FPS: {self.compute_fps:.1f}")
                    print(f"Compute shader skipped: {self.compute_shader_skips}/{self.debug_counter} ({compute_skip_pct:.1f}%)")
                    print(f"Texture readback skipped: {self.dirty_flag_skips}/{self.debug_counter} ({texture_skip_pct:.1f}%)")
                    print(f"========================")
        except Exception as e:
            print(f"Error reading debug buffer: {e}")
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
        
        # Check mouse position changes
        if (abs(self.mouse_pos[0] - self.last_mouse_pos[0]) > 0.001 or 
            abs(self.mouse_pos[1] - self.last_mouse_pos[1]) > 0.001):
            self.last_mouse_pos = self.mouse_pos.copy()
            changed = True
        
        # Check click state changes
        if self.click_value != self.last_click_value:
            self.last_click_value = self.click_value
            changed = True
        
        # Check scroll changes
        current_scroll = float(scroll_state.scroll_value)
        if abs(current_scroll - self.last_scroll_value) > 0.001:
            self.last_scroll_value = current_scroll
            changed = True
        
        # Check if we have a forced update flag
        if self.needs_texture_update:
            self.needs_texture_update = False
            changed = True
        
        if not changed:
            self.dirty_flag_skips += 1
        
        # Store result for draw_texture to use
        self.texture_needs_readback = changed
        
        return changed
    
    def has_texture_changed(self):
        """Check if texture needs readback. Called from draw_texture."""
        # Use the state set by check_if_changed()
        return self.texture_needs_readback
    def run_compute_shader(self):
        if not (self.compute_shader and self.mouse_buffer and self.container_buffer and 
                self.viewport_buffer and self.output_texture):
            return False
            
        try:
            self.mouse_buffer.bind_to_storage_buffer(0)
            self.container_buffer.bind_to_storage_buffer(1)
            self.viewport_buffer.bind_to_storage_buffer(2)
            if self.debug_buffer:
                self.debug_buffer.bind_to_storage_buffer(3)
            self.output_texture.bind_to_image(4, read=False, write=True)
            
            groups_x = (self.texture_size[0] + 15) // 16
            groups_y = (self.texture_size[1] + 15) // 16

            self.compute_shader.run(groups_x, groups_y, 1)

            #self.mgl_context.finish()
            
            self.read_debug_buffer()
            
            return True
        except Exception as e:
            print(f"Error running compute shader: {e}")
            return False
    def initialize(self):
        # Get current viewport size before anything else
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        self.region_size = (region.width, region.height)
                        break
                break
        
        if not self.load_container_data():
            return False
        if not self.init_moderngl_context():
            return False
        if not self.create_compute_shader():
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
        
        # Force first frame update
        self.needs_texture_update = True
        
        print("Initial buffer data:")
        self.debug_print_buffer_data()
        
        # Add drawing callback
        self.add_drawing_callback()
        return True
    def add_drawing_callback(self):
        self.draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_texture, (), 'WINDOW', 'POST_PIXEL'
        )
    def draw_texture(self):
        if not (self.running and self.gpu_shader and self.batch and self.output_texture):
            return
            
        try:
            # PERFORMANCE OPTIMIZATION:
            # Check if texture has actually changed before doing expensive GPU->CPU readback
            if not self.has_texture_changed():
                # Texture hasn't changed, we can skip expensive recreation
                if self.blender_texture:
                    # Just redraw with existing texture - this is VERY cheap
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
            
            # Texture has changed - we need to update it
            # Unfortunately Blender doesn't support direct OpenGL texture sharing,
            # so we do need the GPU->CPU readback, but ONLY when something changed
            texture_data = self.output_texture.read()
            
            # Convert bytes to float array - NO GAMMA CORRECTION
            # The compute shader outputs linear colors, keep them linear
            float_data = np.frombuffer(texture_data, dtype=np.uint8).astype(np.float32) / 255.0
            
            # Create buffer from float data
            buffer = gpu.types.Buffer('FLOAT', len(float_data), float_data)
            
            # Create or recreate Blender texture only when changed
            if self.blender_texture:
                del self.blender_texture
            
            self.blender_texture = gpu.types.GPUTexture(
                self.texture_size,
                format = 'RGBA8',
                data   = buffer
            )
            
            # Set up OpenGL state
            gpu.state.blend_set('ALPHA')
            gpu.state.depth_test_set('NONE')
            
            # Bind shader and set uniforms
            self.gpu_shader.bind()
            self.gpu_shader.uniform_sampler("inputTexture", self.blender_texture)
            self.gpu_shader.uniform_float("opacity", 1.0)
            
            # Draw fullscreen quad with 1:1 mapping
            gpu.matrix.push()
            gpu.matrix.load_identity()
            
            self.batch.draw(self.gpu_shader)
            gpu.matrix.pop()
            
            # Reset OpenGL state
            gpu.state.blend_set('NONE')
            gpu.state.depth_test_set('LESS_EQUAL')
            
        except Exception as e:
            print(f"Error drawing texture: {e}")
    
    def cleanup(self):
        self.running = False
        
        if self.draw_handler:
            bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler, 'WINDOW')
            self.draw_handler = None
        
        if self.blender_texture:
            self.blender_texture = None
        
        # Reset dirty flag system
        self.needs_texture_update = True
        self.last_mouse_pos = [0.5, 0.5]
        self.last_click_value = 0.0
        self.last_scroll_value = 0.0
        
        # Release ModernGL resources in proper order
        # Release resources before calling gc() to ensure clean state
        if self._safe_release_moderngl_object(self.debug_buffer):
            self.debug_buffer = None
        if self._safe_release_moderngl_object(self.mouse_buffer):
            self.mouse_buffer = None
        if self._safe_release_moderngl_object(self.container_buffer):
            self.container_buffer = None
        if self._safe_release_moderngl_object(self.viewport_buffer):
            self.viewport_buffer = None
        if self._safe_release_moderngl_object(self.output_texture):
            self.output_texture = None
        if self._safe_release_moderngl_object(self.compute_shader):
            self.compute_shader = None
        
        # Call Context.gc() to clean up any remaining resources
        # This is crucial when using 'context_gc' mode with detected contexts
        if self.mgl_context:
            try:
                self.mgl_context.gc()
            except AttributeError as e:
                # Handle InvalidObject errors during garbage collection
                if "'InvalidObject' object has no attribute 'release'" in str(e):
                    print("Warning: Some ModernGL objects were already released, skipping gc()")
                else:
                    print(f"Warning: Error during ModernGL garbage collection: {e}")
            except Exception as e:
                print(f"Warning: Unexpected error during ModernGL cleanup: {e}")
            finally:
                # Ensure we clear the context reference regardless of gc() success
                self.mgl_context = None
        
        # Additional safety: force Python garbage collection
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
        """Update entire container buffer with current interaction states"""
        if not self.container_buffer or not hit_container_data:
            return False
        
        try:
            container_array = []
            updates_made = 0
            
            for i, container in enumerate(hit_container_data):
                # Check if state changed for logging
                state_changed = (
                    container.get('_hovered', False) != container.get('_prev_hovered', False) or
                    container.get('_clicked', False) != container.get('_prev_clicked', False)
                )
                
                if state_changed:
                    updates_made += 1
                
                # Use base colors - let shader handle hover/click states
                current_color = container.get('color', [1, 1, 1, 1]).copy()
                current_color_1 = container.get('color_1', [1, 1, 1, 1]).copy()
                
                # Build container struct with current colors
                container_struct = [
                    int(container.get('display', False)),
                    container.get('position', [0, 0])[0], container.get('position', [0, 0])[1],
                    container.get('size', [100, 100])[0], container.get('size', [100, 100])[1],
                    # Use current colors (positions 5-12)
                    current_color[0], current_color[1], current_color[2], current_color[3],
                    current_color_1[0], current_color_1[1], current_color_1[2], current_color_1[3],
                    container.get('color_gradient_rot', 0.0),
                    # Rest of the structure remains the same...
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
                    container.get('box_shadow_color', [0, 0, 0, 0])[2], container.get('box_shadow_color', [0, 0, 0, 0])[3]
                ]
                container_array.extend(container_struct)
            
            # Update entire buffer
            container_data_np = np.array(container_array, dtype=np.float32)
            self.container_buffer.write(container_data_np.tobytes())
            
            # Mark texture as needing update if containers changed
            if updates_made > 0:
                self.needs_texture_update = True
            
            return True
        except Exception as e:
            print(f"Failed to update container buffer (full): {e}")
            import traceback
            traceback.print_exc()
            return False

class XWZ_OT_start_ui(Operator):
    bl_idname      = "xwz.start_ui"
    bl_label       = "Start XWZ UI"
    bl_description = "Start XWZ UI"
    
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
        
        # print("Text blocks:", parser_op.text_blocks)
        # print("Image blocks:", parser_op.image_blocks)

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
                aspect_ratio = True if block['aspect_ratio'] == 'True' else False
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
                mask_height   = block['mask_height']
            )

        self.report({'INFO'}, "UI Started")
        return {'RUNNING_MODAL'}
    
    def modal(self, context, event):
        global _render_data
        
        if not (_render_data and _render_data.running):
            self.cancel(context)
            return {'CANCELLED'}
        
        if event.type == 'TIMER':
            area = context.area
            region = context.region
            
            if area and region:
                # Update FPS counter on every timer tick (not just when compute shader runs)
                _render_data.update_fps()
                
                _render_data.update_region_size(region.width, region.height)

                # PERFORMANCE OPTIMIZATION:
                # Check if anything changed and run compute shader only when needed
                texture_changed = _render_data.check_if_changed()
                if texture_changed:
                    # Only update container buffer when texture is changing
                    # This avoids rebuilding the entire buffer every frame
                    from .hit_op import _container_data
                    if _container_data:
                        _render_data.update_container_buffer_full(_container_data)
                    
                    _render_data.run_compute_shader()
                else:
                    # Count skipped frames for debugging
                    _render_data.compute_shader_skips += 1
                
                # Periodic garbage collection for ModernGL resources (only every 120 frames = ~2 seconds)
                # Running this every frame causes unnecessary overhead
                if _render_data.mgl_context and _render_data.debug_counter % 120 == 0:
                    try:
                        _render_data.mgl_context.gc()
                    except AttributeError as e:
                        # Handle InvalidObject errors during garbage collection
                        if "'InvalidObject' object has no attribute 'release'" in str(e):
                            pass  # Silently ignore - objects already released
                        else:
                            print(f"Warning: Error during ModernGL garbage collection: {e}")
                    except Exception as e:
                        print(f"Warning: Unexpected error during ModernGL cleanup: {e}")
            
            # Always redraw to display the texture (even if unchanged)
            # This is cheap since we're just displaying the existing texture
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
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
    bl_label       = "Stop XWZ UI"
    bl_description = "Stop XWZ UI"
    
    def execute(self, context):
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
        
        try:
            bpy.ops.xwz.clear_text()
            bpy.ops.xwz.clear_images()
        except Exception as e:
            print(f"Warning: Could not clear instances: {e}")

        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
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
    
    # Additional cleanup to ensure ModernGL resources are fully released
    try:
        import gc
        import sys
        
        # Force garbage collection to clean up any remaining ModernGL objects
        gc.collect()
        
        # Try to remove ModernGL from module cache to force complete cleanup
        # This helps ensure the DLL is released
        modules_to_remove = [name for name in sys.modules.keys() if name.startswith('moderngl')]
        for module_name in modules_to_remove:
            if module_name in sys.modules:
                try:
                    del sys.modules[module_name]
                except:
                    pass
        
        # Force another garbage collection after module cleanup
        gc.collect()
        
    except Exception as e:
        print(f"Warning: Error during extended cleanup: {e}")
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)