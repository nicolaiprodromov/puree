import bpy

class MouseState:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.mouse_pos = [0.0, 0.0]
            cls._instance.is_clicked = False
            cls._instance.callbacks = []
            cls._instance.running_operator = None
        return cls._instance
    
    def set_operator(self, operator):
        self.running_operator = operator
    
    def stop_mouse_tracking(self):
        if self.running_operator:
            self.running_operator.should_stop = True
            self.running_operator = None
    
    def update_mouse(self, pos):
        self.mouse_pos[0] = pos[0]
        self.mouse_pos[1] = pos[1]
        for callback in self.callbacks:
            try:
                callback('mouse', pos)
            except:
                pass
    
    def update_click(self, clicked):
        self.is_clicked = clicked
        for callback in self.callbacks:
            try:
                callback('click', clicked)
            except:
                pass
    
    def register_callback(self, callback):
        if callback not in self.callbacks:
            self.callbacks.append(callback)
    
    def unregister_callback(self, callback):
        if callback in self.callbacks:
            self.callbacks.remove(callback)

class XWZ_OT_mouse(bpy.types.Operator):
    bl_idname = "xwz.mouse_modal"
    bl_label = "Mouse Event Template"
    bl_options = {'REGISTER'}
    
    def invoke(self, context, event):
        self.should_stop = False
        mouse_state.set_operator(self)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    
    def modal(self, context, event):
        if self.should_stop:
            mouse_state.set_operator(None)
            return {'CANCELLED'}
        
        if event.type == 'MOUSEMOVE':
            area = context.area
            if area and area.type == 'VIEW_3D':
                region = context.region
                raw_x = event.mouse_region_x / region.width
                raw_y = event.mouse_region_y / region.height
                pos = [raw_x * 2.0 - 1.0, (1.0 - raw_y) * 2.0 - 1.0]
                mouse_state.update_mouse(pos)
        
        elif event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            mouse_state.update_click(True)
        
        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            mouse_state.update_click(False)
        
        if event.type in {'ESC'}:
            return {'CANCELLED'}
        
        return {'PASS_THROUGH'}

class XWZ_OT_mouse_launch(bpy.types.Operator):
    bl_idname = "xwz.mouse_modal_launch"
    bl_label = "Mouse Context Fix"
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
                bpy.ops.xwz.mouse_modal('INVOKE_DEFAULT')
        except Exception as e:
            print(f"Error invoking mouse modal: {e}")
            
        return {'FINISHED'}

mouse_state = MouseState()