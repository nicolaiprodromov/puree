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
import math

class ScrollState:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance                    = super().__new__(cls)
            cls._instance.scroll_value       = 0
            cls._instance.scroll_delta       = 0
            cls._instance._prev_scroll_value = 0
            cls._instance.callbacks          = []
            cls._instance.running_operator   = None
        return cls._instance
    
    def set_operator(self, operator):
        self.running_operator = operator
    
    def stop_scrolling(self):
        if self.running_operator: 
            self.running_operator.should_stop = True
            self.running_operator             = None
    
    def update(self, delta, absolute_value):
        self.scroll_delta = delta
        self.scroll_value = absolute_value
        for callback in self.callbacks:
            try:
                callback(delta, absolute_value)
            except:
                pass
    
    def register_callback(self, callback):
        if callback not in self.callbacks:
            self.callbacks.append(callback)
    
    def unregister_callback(self, callback):
        if callback in self.callbacks:
            self.callbacks.remove(callback)

class XWZ_OT_scroll(bpy.types.Operator):
    bl_idname  = "xwz.scroll_modal"
    bl_label   = "Scroll Event Template"
    bl_options = {'REGISTER'}
    def invoke(self, context, event):
        self.mouse_x          = 0
        self.mouse_y          = 0
        self.trackpad_x_accum = 0
        self.trackpad_y_accum = 0
        self.scroll_offset    = 0
        self.scroll_speed     = 10
        self.mouse_x          = event.mouse_region_x
        self.mouse_y          = event.mouse_region_y

        self.should_stop = False
        scroll_state.set_operator(self)
        
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    
    def modal(self, context, event):
        if self.should_stop:
            scroll_state.set_operator(None)
            return {'CANCELLED'}
        
        self.mouse_x = event.mouse_region_x  
        self.mouse_y = event.mouse_region_y
        
        if not self.is_mouse_in_ui_area(context):
            return {'PASS_THROUGH'}
            
        scroll_delta = 0
        
        if event.type == 'WHEELUPMOUSE' and event.value == 'PRESS':
            scroll_delta = -1
            
        elif event.type == 'WHEELDOWNMOUSE' and event.value == 'PRESS':
            scroll_delta = 1
            
        elif event.type == 'TRACKPADPAN':
            self.trackpad_y_accum += event.mouse_y - event.mouse_prev_y
            
            sensitivity = max(1, 100 - self.scroll_speed)  
            if abs(self.trackpad_y_accum) > sensitivity:
                scroll_delta = math.floor(self.trackpad_y_accum / sensitivity)
                self.trackpad_y_accum -= scroll_delta * sensitivity
            
        if event.type == 'ESC':
            scroll_state.set_operator(None)
            return {'CANCELLED'}
            
        if scroll_delta != 0:
            self.scroll_offset += scroll_delta
            scroll_state.update(scroll_delta, self.scroll_offset)
        
        return {'PASS_THROUGH'}
    
    def is_mouse_in_ui_area(self, context):
        width, height = 1920, 1080
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        width = region.width
                        height = region.height
                        break
                break
        in_bounds = (
            0 <= self.mouse_x <= width and 0 <= self.mouse_y <= height
        )
        return in_bounds
    
class XWZ_OT_scroll_launch(bpy.types.Operator):
    bl_idname  = "xwz.scroll_modal_launch"
    bl_label   = "Scroll Context Fix"
    bl_options = {'INTERNAL'}
    def execute(self, context):
        context_dict = {
            "area"          : context.area,
            "region"        : context.region,
            "space_data"    : context.space_data,
            "screen"        : context.screen,
            "scene"         : context.scene,
            "window"        : context.window,
            "window_manager": context.window_manager,
        }
        
        try:
            with context.temp_override(**context_dict):
                bpy.ops.xwz.scroll_modal('INVOKE_DEFAULT')
        except Exception as e:
            print(f"Error invoking scroll modal: {e}")
        return {'FINISHED'}

scroll_state = ScrollState()
