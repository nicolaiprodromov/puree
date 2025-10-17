"""
Optimized Hit Detection using Native Backend

This module provides high-performance hit detection
using native-compiled backend for significantly improved performance.
"""

import bpy
from . import parser_op
from .scroll_op import scroll_state
from .mouse_op import mouse_state
from .native_bindings import NativeHitDetector, is_native_available

hit_modal_running = False
_container_data = []
_native_detector = None

class XWZ_OT_hit_detect(bpy.types.Operator):
    """Optimized hit detection using native backend"""
    bl_idname = "xwz.hit_detect"
    bl_label = "Detect interactions in UI (Performance-optimized)"
    bl_options = {'REGISTER'}
    
    def invoke(self, context, event):
        global hit_modal_running, _container_data, _native_detector
        
        # Initialize native detector if not already done
        if _native_detector is None:
            _native_detector = NativeHitDetector()
        
        hit_modal_running = True
        context.window_manager.modal_handler_add(self)
        
        _container_data = parser_op._container_json_data
        
        # Load container data into native detector
        if is_native_available() and _container_data:
            _native_detector.load_containers(_container_data)
        
        return {'RUNNING_MODAL'}
    
    def sync_container_data(self):
        """Sync container data from parser_op when layout is recomputed"""
        global _container_data, _native_detector
        if parser_op._container_json_data:
            _container_data = parser_op._container_json_data
            # Reload into native detector
            if is_native_available() and _native_detector:
                _native_detector.load_containers(_container_data)
    
    def modal(self, context, event):
        global hit_modal_running
        
        if not hit_modal_running:
            return {'FINISHED'}
        
        if not self._is_mouse_in_viewport():
            return {'PASS_THROUGH'}
        
        # Get mouse position in screen coordinates
        try:
            mouse_x, mouse_y = self._get_mouse_pos()
        except:
            return {'PASS_THROUGH'}
        
        # Update native detector with current mouse state
        if is_native_available() and _native_detector:
            _native_detector.update_mouse(
                mouse_x,
                mouse_y,
                mouse_state.is_clicked,
                float(scroll_state.scroll_delta)
            )
            
            # Perform hit detection in native backend
            results = _native_detector.detect_hits()
            
            if results is not None:
                # Apply results to container data
                self.apply_hit_results(results)
            else:
                # Fall back to Python implementation
                self.handle_hover_event_python()
                self.handle_click_event_python()
                self.handle_toggle_event_python()
        else:
            # Use Python implementation if native module not available
            self.handle_hover_event_python()
            self.handle_click_event_python()
            self.handle_toggle_event_python()
        
        # Update previous states
        for _container in _container_data:
            _container['_prev_hovered'] = _container['_hovered']
            _container['_prev_clicked'] = _container['_clicked']
            _container['_prev_toggled'] = _container['_toggled']
        
        scroll_state._prev_scroll_value = scroll_state.scroll_value
        
        return {'PASS_THROUGH'}
    
    def apply_hit_results(self, results):
        """Apply Rust hit detection results to Python container data"""
        # Create lookup dict for fast access
        results_by_id = {r['container_id']: r for r in results}
        
        for container in _container_data:
            container_id = container['id']
            
            if container_id in results_by_id:
                result = results_by_id[container_id]
                
                # Update hover state
                container['_hovered'] = result['is_hovered']
                
                # Trigger hover events if state changed
                if result['hover_changed']:
                    if result['is_hovered'] and not container['_prev_hovered']:
                        # Hover enter
                        for hover_handler in container['hover']:
                            hover_handler(container)
                    elif not result['is_hovered'] and container['_prev_hovered']:
                        # Hover exit
                        for hoverout_handler in container['hoverout']:
                            hoverout_handler(container)
                
                # Update click state
                container['_clicked'] = result['is_clicked']
                
                # Trigger click events if state changed
                if result['click_changed'] and result['is_clicked'] and not container['_prev_clicked']:
                    # Handle text input focus/blur
                    from . import text_input_op
                    
                    text_input_clicked = False
                    for input_instance in text_input_op._text_input_instances:
                        if input_instance.container_id == container_id:
                            bpy.ops.xwz.focus_text_input(instance_id=input_instance.id)
                            text_input_clicked = True
                            break
                    
                    if not text_input_clicked:
                        for input_instance in text_input_op._text_input_instances:
                            if input_instance.is_focused:
                                bpy.ops.xwz.blur_text_input(instance_id=input_instance.id)
                    
                    # Trigger click handlers
                    for click_handler in container['click']:
                        click_handler(container)
                    
                    # Handle toggle
                    container['_toggled'] = True
                    if container['_toggled'] and not container['_prev_toggled']:
                        container['_toggle_value'] = not container['_toggle_value']
                        for toggle_handler in container['toggle']:
                            toggle_handler(container)
                else:
                    container['_toggled'] = False
    
    # Python fallback implementations (same as original hit_op.py)
    def handle_hover_event_python(self):
        """Python fallback for hover detection"""
        for _container in _container_data:
            if _container.get('passive', False):
                continue
            if self.detect_hover(_container):
                _any_child_hovered = False
                for child_ind in _container['children']:
                    _child_ = _container_data[child_ind]
                    if _child_.get('passive', False):
                        continue
                    if self.detect_hover(_child_):
                        _any_child_hovered = True
                        break
                if not _any_child_hovered:
                    _container['_hovered'] = True
                    if _container['_hovered'] is True and _container['_prev_hovered'] is False:
                        for _hover_handler in _container['hover']:
                            _hover_handler(_container)
                else:
                    _container['_hovered'] = False
            else:
                _container['_hovered'] = False
                if _container['_hovered'] is False and _container['_prev_hovered'] is True:
                    for _hover_handler in _container['hoverout']:
                        _hover_handler(_container)
    
    def handle_click_event_python(self):
        """Python fallback for click detection"""
        for _container in _container_data:
            if _container.get('passive', False):
                continue
            if self.detect_hover(_container):
                _any_child_hovered = False
                for child_ind in _container['children']:
                    _child_ = _container_data[child_ind]
                    if _child_.get('passive', False):
                        continue
                    if self.detect_hover(_child_):
                        _any_child_hovered = True
                        break
                if not _any_child_hovered and mouse_state.is_clicked is True:
                    _container['_clicked'] = True
                    if _container['_clicked'] is True and _container['_prev_clicked'] is False:
                        from . import text_input_op
                        
                        text_input_clicked = False
                        for input_instance in text_input_op._text_input_instances:
                            if input_instance.container_id == _container['id']:
                                bpy.ops.xwz.focus_text_input(instance_id=input_instance.id)
                                text_input_clicked = True
                                break
                        
                        if not text_input_clicked:
                            for input_instance in text_input_op._text_input_instances:
                                if input_instance.is_focused:
                                    bpy.ops.xwz.blur_text_input(instance_id=input_instance.id)
                        
                        for _click_handler in _container['click']:
                            _click_handler(_container)
                            
                        _container['_prev_clicked'] = _container['_clicked']
                else:
                    _container['_clicked'] = False
                    _container['_prev_clicked'] = False
            else:
                _container['_clicked'] = False
                _container['_prev_clicked'] = False
    
    def handle_toggle_event_python(self):
        """Python fallback for toggle detection"""
        for _container in _container_data:
            if _container.get('passive', False):
                continue
            if self.detect_hover(_container):
                _any_child_hovered = False
                for child_ind in _container['children']:
                    _child_ = _container_data[child_ind]
                    if _child_.get('passive', False):
                        continue
                    if self.detect_hover(_child_):
                        _any_child_hovered = True
                        break
                if not _any_child_hovered and mouse_state.is_clicked is True:
                    _container['_toggled'] = True
                    if _container['_toggled'] is True and _container['_prev_toggled'] is False:
                        _container['_toggle_value'] = not _container['_toggle_value']
                        for _toggle_handler in _container['toggle']:
                            _toggle_handler(_container)
                else:
                    _container['_toggled'] = False
            else:
                _container['_toggled'] = False
    
    def _is_mouse_in_viewport(self):
        try:
            mouse_x, mouse_y = self._get_mouse_pos()
            width, height = self._get_viewport_size()
            return 0 <= mouse_x <= width and 0 <= mouse_y <= height
        except:
            return False
    
    def _get_viewport_size(self):
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        return region.width, region.height
        return 1920, 1080
    
    def _get_mouse_pos(self):
        width, height = self._get_viewport_size()
        ndc_x = mouse_state.mouse_pos[0]
        ndc_y = mouse_state.mouse_pos[1]
        screen_x = (ndc_x + 1.0) * 0.5 * width
        screen_y = (ndc_y + 1.0) * 0.5 * height
        return screen_x, screen_y
    
    def _is_point_in_container(self, x, y, container):
        cx, cy = self._get_absolute_position(container)
        cw, ch = container['size'][0], container['size'][1]
        return cx <= x <= cx + cw and cy <= y <= cy + ch
    
    def _get_absolute_position(self, container):
        return container['position'][0], container['position'][1]
    
    def detect_hover(self, container):
        try:
            mouse_x, mouse_y = self._get_mouse_pos()
            return self._is_point_in_container(mouse_x, mouse_y, container)
        except:
            return False


class XWZ_OT_hit_stop(bpy.types.Operator):
    """Stop hit detection modal operator"""
    bl_idname = "xwz.hit_stop"
    bl_label = "Stop Hit Detection"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        global hit_modal_running
        hit_modal_running = False
        return {'FINISHED'}


def register():
    bpy.utils.register_class(XWZ_OT_hit_detect)
    bpy.utils.register_class(XWZ_OT_hit_stop)


def unregister():
    bpy.utils.unregister_class(XWZ_OT_hit_stop)
    bpy.utils.unregister_class(XWZ_OT_hit_detect)
