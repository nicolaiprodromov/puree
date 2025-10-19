import bpy
from . import parser_op
from .scroll_op import scroll_state
from .mouse_op import mouse_state
from .native_bindings import HitDetector

hit_modal_running = False
_container_data = []
_native_detector = None

class XWZ_OT_hit_detect(bpy.types.Operator):
    bl_idname = "xwz.hit_detect"
    bl_label = "Detect interactions in UI (Performance-optimized)"
    bl_options = {'REGISTER'}
    
    def invoke(self, context, event):
        global hit_modal_running, _container_data, _native_detector
        
        if _native_detector is None:
            _native_detector = HitDetector()
        
        hit_modal_running = True
        context.window_manager.modal_handler_add(self)
        
        _container_data = parser_op._container_json_data
        
        if _container_data:
            _native_detector.load_containers(_container_data)
        
        return {'RUNNING_MODAL'}
    
    def sync_container_data(self):
        global _container_data, _native_detector
        if parser_op._container_json_data:
            _container_data = parser_op._container_json_data
            if _native_detector:
                _native_detector.load_containers(_container_data)
    
    def modal(self, context, event):
        global hit_modal_running
        
        if not hit_modal_running:
            return {'FINISHED'}
        
        if not self._is_mouse_in_viewport():
            return {'PASS_THROUGH'}
        
        try:
            mouse_x, mouse_y = self._get_mouse_pos()
        except:
            return {'PASS_THROUGH'}
        
        if not _native_detector:
            return {'PASS_THROUGH'}
        
        _native_detector.update_mouse(
            mouse_x,
            mouse_y,
            mouse_state.is_clicked,
            float(scroll_state.scroll_delta)
        )
        
        results = _native_detector.detect_hits()
        
        if results is not None:
            self.apply_hit_results(results)
        
        for _container in _container_data:
            _container['_prev_hovered'] = _container['_hovered']
            _container['_prev_clicked'] = _container['_clicked']
            _container['_prev_toggled'] = _container['_toggled']
        
        scroll_state._prev_scroll_value = scroll_state.scroll_value
        
        return {'PASS_THROUGH'}
    
    def apply_hit_results(self, results):
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
class XWZ_OT_hit_stop(bpy.types.Operator):
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
