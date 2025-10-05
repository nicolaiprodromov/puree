import bpy
from time import sleep
from . import parser_op
from .scroll_op import scroll_state
from .mouse_op  import mouse_state
from . import text_op
from . import img_op

hit_modal_running = False
_container_data   = []

class XWZ_OT_hit(bpy.types.Operator):
    bl_idname  = "xwz.hit_detect"
    bl_label   = "Detect interactions in UI"
    bl_options = {'REGISTER'}
 
    def invoke(self, context, event):
        global hit_modal_running, _container_data
        hit_modal_running = True
        context.window_manager.modal_handler_add(self)

        _container_data = parser_op._container_json_data

        return {'RUNNING_MODAL'}
    
    def modal(self, context, event):
        global hit_modal_running
        
        if not hit_modal_running:
            return {'FINISHED'}
            
        if not self._is_mouse_in_viewport():
            return {'PASS_THROUGH'}
        
        #self.handle_scroll_event()
        self.handle_hover_event()
        self.handle_click_event()
        self.handle_toggle_event()
        for _container in _container_data:
            _container['_prev_hovered'] = _container['_hovered']
            _container['_prev_clicked'] = _container['_clicked']
            _container['_prev_toggled'] = _container['_toggled']

        scroll_state._prev_scroll_value = scroll_state.scroll_value

        return {'PASS_THROUGH'}
    
    def handle_hover_event(self):
        for _container in _container_data:
            if self.detect_hover(_container):
                _any_child_hovered = False
                for child_ind in _container['children']:
                    _child_ = _container_data[child_ind]
                    if self.detect_hover(_child_):
                        _any_child_hovered = True
                        break
                if not _any_child_hovered:
                    _container['_hovered'] = True
                    if _container['_hovered'] is True and _container['_prev_hovered'] is False:
                        for _hover_handler in _container['hover']:
                            _hover_handler(_container)
                            sleep(0.1)
                        _container['_prev_hovered'] = _container['_hovered']
                else:
                    _container['_hovered']      = False
            else:
                _container['_hovered']      = False
                if _container['_hovered'] is False and _container['_prev_hovered'] is True:
                    for _hover_handler in _container['hoverout']:
                        _hover_handler(_container)
                        sleep(0.1)
                    _container['_prev_hovered'] = _container['_hovered']

    def handle_click_event(self):
        for _container in _container_data:
            if self.detect_hover(_container):
                _any_child_hovered = False
                for child_ind in _container['children']:
                    _child_ = _container_data[child_ind]
                    if self.detect_hover(_child_):
                        _any_child_hovered = True
                        break
                if not _any_child_hovered and mouse_state.is_clicked is True:
                    _container['_clicked'] = True
                    if _container['_clicked'] is True and _container['_prev_clicked'] is False:
                        for _click_handler in _container['click']:
                            _click_handler(_container)
                            sleep(0.1)
                        _container['_prev_clicked'] = _container['_clicked']
                else:
                    _container['_clicked']      = False
                    _container['_prev_clicked'] = False
            else:
                _container['_clicked']      = False
                _container['_prev_clicked'] = False

    def handle_scroll_event(self):
        for _container in _container_data:
            if self.detect_hover(_container):
                _any_child_scrollable = False
                for cc_indy in _container['children']:
                    _child_ = _container_data[cc_indy]

                    if self.detect_hover(_child_):
                        ccbb = []
                        for __child_ind in _child_['children']:
                            _cc_ = _container_data[__child_ind]
                            ccbb.append((_cc_['position'][0], _cc_['position'][1], _cc_['size'][0], _cc_['size'][1]))
                        if len(ccbb) > 0:
                            min_y = min([box[1] for box in ccbb])
                            max_y = max([box[1] + box[3] for box in ccbb])
                            container_height = _child_['size'][1]
                            content_height   = max_y - min_y
                            if content_height > container_height:
                                _any_child_scrollable = True
                        break

                if not _any_child_scrollable:
                    child_bounding_box = []
                    for child_ind in _container['children']:
                        _ccc_ = _container_data[child_ind]
                        child_bounding_box.append((_ccc_['position'][0], _ccc_['position'][1], _ccc_['size'][0], _ccc_['size'][1]))
                    if len(child_bounding_box) > 0:
                        min_y = min([box[1] for box in child_bounding_box])
                        max_y = max([box[1] + box[3] for box in child_bounding_box])
                        container_height = _container['size'][1]
                        content_height   = max_y - min_y
                        if content_height > container_height:
                            if scroll_state.scroll_value != scroll_state._prev_scroll_value:
                                for child_ind in _container['children']:
                                    __child = _container_data[child_ind]

                                    __child['position'][1] -= int(scroll_state.scroll_delta * parser_op.XWZ_UI.settings.scroll_speed)
                                
                        # perform bounding box of children check to prevent overscroll
                        child_bounding_box = []
                        for child_ind in _container['children']:
                            _ccc_ = _container_data[child_ind]
                            child_bounding_box.append((_ccc_['position'][0], _ccc_['position'][1], _ccc_['size'][0], _ccc_['size'][1]))

                        if len(child_bounding_box) > 0:
                            min_y = min([box[1] for box in child_bounding_box])
                            max_y = max([box[1] + box[3] for box in child_bounding_box])
                            container_top = 0
                            container_bottom = _container['size'][1]
                            
                            if min_y > container_top:  # first child scrolled below container top
                                offset = container_top - min_y
                                for child_ind in _container['children']:
                                    _ccb_ = _container_data[child_ind]
                                    _ccb_['position'][1] += offset
                                    
                            if max_y < container_bottom:  # last child scrolled above container bottom
                                offset = container_bottom - max_y
                                for child_ind in _container['children']:
                                    _ccb_ = _container_data[child_ind]
                                    _ccb_['position'][1] += offset
                        else:
                            _container['_scroll_value'] = 0
                    else:
                            _container['_scroll_value'] = 0


                    child_bounding_box = []
                    for child_ind in _container['children']:
                        _ccc_ = _container_data[child_ind]
                        child_bounding_box.append((_ccc_['position'][0], _ccc_['position'][1], _ccc_['size'][0], _ccc_['size'][1]))

                    if len(child_bounding_box) > 0:
                        min_y            = min([box[1] for box in child_bounding_box])
                        max_y            = max([box[1] + box[3] for box in child_bounding_box])
                        container_top    = 0
                        container_bottom = int(_container['size'][1])
                    
                        for cc_indy in _container['children']:

                            _child_ = _container_data[cc_indy]

                            if _child_['img'] != '':

                                for _img_instance in img_op._image_instances:
                                    if _img_instance.container_id == _child_['id']:

                                        rel_y_pos = int(_child_['position'][1] + _container['position'][1])

                                        if _child_['position'][1] < _container['position'][1]:
                                            rel_mask_y = int(rel_y_pos + (container_top - min_y))
                                        else:
                                            rel_mask_y = rel_y_pos

                                        if int(_child_['position'][1] + _child_['size'][1]) > int(_container['position'][1] + _container['size'][1]) + 1:
                                            rel_mask_h = int(_child_['size'][1] + (container_bottom - max_y))
                                        else:
                                            rel_mask_h = int(_child_['size'][1])

                                        bpy.ops.xwz.update_image(
                                            instance_id = _img_instance.id,
                                            y_pos       = rel_y_pos,
                                            mask_y      = rel_mask_y,
                                            mask_height = rel_mask_h
                                        )

                                        break

                            if _child_['text'] != '':

                                for _txt_instance in text_op._text_instances:
                                    if _txt_instance.container_id == _child_['id']:

                                        rel_y_pos = int(_child_['position'][1] + _container['position'][1])

                                        if _child_['position'][1] < _container['position'][1]:
                                            rel_mask_y = int(rel_y_pos + (container_top - min_y))
                                        else:
                                            rel_mask_y = rel_y_pos

                                        if int(_child_['position'][1] + _child_['size'][1]) > int(_container['position'][1] + _container['size'][1]) + 1:
                                            rel_mask_h = int(_child_['size'][1] + (container_bottom - max_y))
                                        else:
                                            rel_mask_h = int(_child_['size'][1])

                                        bpy.ops.xwz.update_text(
                                            instance_id = _txt_instance.id,
                                            y_pos       = rel_y_pos,
                                            mask_y      = rel_mask_y,
                                            mask_height = rel_mask_h
                                        )

                                        break
    
    def handle_toggle_event(self):
        for _container in _container_data:
            if self.detect_hover(_container):
                _any_child_hovered = False
                for child_ind in _container['children']:
                    _child_ = _container_data[child_ind]
                    if self.detect_hover(_child_):
                        _any_child_hovered = True
                        break
                if not _any_child_hovered and mouse_state.is_clicked is True:
                    _container['_toggled'] = True
                    if _container['_toggled'] is True and _container['_prev_toggled'] is False:
                        _container['_toggle_value'] = not _container['_toggle_value']
                        for _toggle_handler in _container['toggle']:
                            _toggle_handler(_container)
                            sleep(0.1)
                        _container['_prev_toggled'] = _container['_toggled']
                else:
                    _container['_toggled']      = False
                    _container['_prev_toggled'] = False
            else:
                _container['_toggled']      = False
                _container['_prev_toggled'] = False

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
        cx = container['position'][0]
        cy = container['position'][1]
        
        parent_index = container.get('parent', -1)
        while parent_index >= 0 and parent_index < len(_container_data):
            parent = _container_data[parent_index]
            cx += parent['position'][0]
            cy += parent['position'][1]
            parent_index = parent.get('parent', -1)
        
        return cx, cy

    def detect_hover(self, container):
        try:
            mouse_x, mouse_y = self._get_mouse_pos()
            return self._is_point_in_container(mouse_x, mouse_y, container)
        except:
            return False

class XWZ_OT_hit_stop(bpy.types.Operator):
    bl_idname  = "xwz.hit_stop"
    bl_label   = "Stop UI hit detection"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        global hit_modal_running
        hit_modal_running = False
        return {'FINISHED'}
    
def register():
    bpy.utils.register_class(XWZ_OT_hit)
    bpy.utils.register_class(XWZ_OT_hit_stop)

def unregister():
    bpy.utils.unregister_class(XWZ_OT_hit)
    bpy.utils.unregister_class(XWZ_OT_hit_stop)

