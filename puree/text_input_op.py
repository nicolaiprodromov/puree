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
import blf
import time

from .text_op import FontManager, font_manager
from .mouse_op import mouse_state

_text_input_instances = []
_draw_handle = None
_active_input_id = None
_keyboard_handler_running = False
_next_input_id = 0

class TextInputInstance:
    def __init__(self, container_id, placeholder="", font_name=None, size=20, pos=[50, 50], 
                 color=[1,1,1,1], mask=None, align_h='LEFT', align_v='TOP', 
                 cursor_color=[1,1,1,1], selection_color=[0.3,0.5,0.8,0.3]):
        global _next_input_id
        self.container_id = container_id
        self.id = _next_input_id
        _next_input_id += 1
        self.text = ""
        self.placeholder = placeholder
        self.font_name = font_name
        self.font_id = self._get_font_id()
        self.size = size
        self.position = pos
        self.color = color
        self.mask = mask
        self.align_h = align_h
        self.align_v = align_v
        self.cursor_color = cursor_color
        self.selection_color = selection_color
        
        self.cursor_pos = 0
        self.selection_start = None
        self.is_focused = False
        self.cursor_blink_time = 0.0
        self.show_cursor = True
        
        self.scroll_offset_x = 0
        self.scroll_offset_y = 0
        
        self._last_refresh = 0.0
        self._refresh_delay = 0.016
    
    def _get_font_id(self):
        if self.font_name and font_manager:
            try:
                font_id = font_manager.get_font_id(self.font_name)
                if font_id is not None and font_id >= 0:
                    return font_id
            except:
                pass
        return 0
    
    def refresh_font_id(self):
        self.font_id = self._get_font_id()
    
    def get_wrapped_lines(self):
        if not self.mask or self.mask[2] <= 0:
            return [self.text] if self.text else []
        
        container_width = self.mask[2]
        padding_total = 20
        available_width = max(container_width - padding_total, 50)
        
        blf.size(self.font_id, self.size)
        
        lines = []
        current_line = ""
        
        for char in self.text:
            if char == '\n':
                lines.append(current_line)
                current_line = ""
                continue
            
            test_line = current_line + char
            text_width, _ = blf.dimensions(self.font_id, test_line)
            
            if text_width > available_width:
                if current_line:
                    lines.append(current_line)
                    current_line = char
                else:
                    lines.append(char)
                    current_line = ""
            else:
                current_line = test_line
        
        if current_line:
            lines.append(current_line)
        
        return lines if lines else [""]
    
    def get_cursor_position_2d(self):
        lines = self.get_wrapped_lines()
        char_count = 0
        
        for line_idx, line in enumerate(lines):
            line_len = len(line)
            if char_count + line_len >= self.cursor_pos:
                col = self.cursor_pos - char_count
                return line_idx, col
            char_count += line_len
            if line_idx < len(lines) - 1:
                char_count += 1
        
        return len(lines) - 1, len(lines[-1]) if lines else 0
    
    def insert_text(self, text):
        if self.selection_start is not None:
            self.delete_selection()
        
        self.text = self.text[:self.cursor_pos] + text + self.text[self.cursor_pos:]
        self.cursor_pos += len(text)
        self._request_refresh()
    
    def delete_selection(self):
        if self.selection_start is None:
            return
        
        start = min(self.cursor_pos, self.selection_start)
        end = max(self.cursor_pos, self.selection_start)
        self.text = self.text[:start] + self.text[end:]
        self.cursor_pos = start
        self.selection_start = None
        self._request_refresh()
    
    def backspace(self):
        if self.selection_start is not None:
            self.delete_selection()
        elif self.cursor_pos > 0:
            self.text = self.text[:self.cursor_pos-1] + self.text[self.cursor_pos:]
            self.cursor_pos -= 1
            self._request_refresh()
    
    def delete(self):
        if self.selection_start is not None:
            self.delete_selection()
        elif self.cursor_pos < len(self.text):
            self.text = self.text[:self.cursor_pos] + self.text[self.cursor_pos+1:]
            self._request_refresh()
    
    def move_cursor_left(self, shift=False):
        if shift:
            if self.selection_start is None:
                self.selection_start = self.cursor_pos
        else:
            if self.selection_start is not None:
                self.cursor_pos = min(self.cursor_pos, self.selection_start)
                self.selection_start = None
                return
        
        if self.cursor_pos > 0:
            self.cursor_pos -= 1
        
        if not shift:
            self.selection_start = None
    
    def move_cursor_right(self, shift=False):
        if shift:
            if self.selection_start is None:
                self.selection_start = self.cursor_pos
        else:
            if self.selection_start is not None:
                self.cursor_pos = max(self.cursor_pos, self.selection_start)
                self.selection_start = None
                return
        
        if self.cursor_pos < len(self.text):
            self.cursor_pos += 1
        
        if not shift:
            self.selection_start = None
    
    def move_cursor_up(self, shift=False):
        if shift and self.selection_start is None:
            self.selection_start = self.cursor_pos
        
        lines = self.get_wrapped_lines()
        line_idx, col = self.get_cursor_position_2d()
        
        if line_idx > 0:
            prev_line = lines[line_idx - 1]
            new_col = min(col, len(prev_line))
            
            char_count = sum(len(lines[i]) + (1 if i < len(lines) - 1 else 0) for i in range(line_idx - 1))
            self.cursor_pos = char_count + new_col
        
        if not shift:
            self.selection_start = None
    
    def move_cursor_down(self, shift=False):
        if shift and self.selection_start is None:
            self.selection_start = self.cursor_pos
        
        lines = self.get_wrapped_lines()
        line_idx, col = self.get_cursor_position_2d()
        
        if line_idx < len(lines) - 1:
            next_line = lines[line_idx + 1]
            new_col = min(col, len(next_line))
            
            char_count = sum(len(lines[i]) + (1 if i < len(lines) - 1 else 0) for i in range(line_idx + 1))
            self.cursor_pos = char_count + new_col
        
        if not shift:
            self.selection_start = None
    
    def focus(self):
        global _active_input_id
        self.is_focused = True
        _active_input_id = self.id
        self.cursor_blink_time = time.time()
        self.show_cursor = True
    
    def blur(self):
        global _active_input_id
        self.is_focused = False
        if _active_input_id == self.id:
            _active_input_id = None
        self.selection_start = None
    
    def _request_refresh(self):
        self._last_refresh = time.time()
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
    
    def should_refresh(self):
        return time.time() - self._last_refresh < self._refresh_delay

def draw_all_text_inputs():
    viewport_height = 0
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for region in area.regions:
                if region.type == 'WINDOW':
                    viewport_height = region.height
                    break
            break
    
    current_time = time.time()
    
    for instance in _text_input_instances:
        if instance.is_focused:
            if current_time - instance.cursor_blink_time > 0.5:
                instance.show_cursor = not instance.show_cursor
                instance.cursor_blink_time = current_time
        
        if instance.mask and instance.mask[2] > 0 and instance.mask[3] > 0:
            xmin = instance.mask[0]
            ymin = viewport_height - instance.mask[1] - instance.mask[3]
            xmax = instance.mask[0] + instance.mask[2]
            ymax = viewport_height - instance.mask[1]
            blf.clipping(instance.font_id, xmin, ymin, xmax, ymax)
            blf.enable(instance.font_id, blf.CLIPPING)
        
        blf.size(instance.font_id, instance.size)
        
        lines = instance.get_wrapped_lines()
        line_height = instance.size * 1.2
        
        display_text = instance.text if instance.text else instance.placeholder
        display_color = instance.color if instance.text else [c * 0.5 for c in instance.color]
        
        x_pos = instance.position[0]
        y_pos = instance.position[1]
        
        if instance.mask and instance.mask[2] > 0 and instance.mask[3] > 0:
            container_width = instance.mask[2]
            container_height = instance.mask[3]
            
            if instance.align_h == 'LEFT':
                x_pos = instance.mask[0] + 5
            elif instance.align_h == 'CENTER':
                x_pos = instance.mask[0] + container_width / 2
            elif instance.align_h == 'RIGHT':
                x_pos = instance.mask[0] + container_width - 5
            
            if instance.align_v == 'TOP':
                y_pos = instance.mask[1] + 5
            elif instance.align_v == 'CENTER':
                total_text_height = len(lines) * line_height
                y_pos = instance.mask[1] + (container_height - total_text_height) / 2
            elif instance.align_v == 'BOTTOM':
                total_text_height = len(lines) * line_height
                y_pos = instance.mask[1] + container_height - total_text_height - 5
        
        for line_idx, line in enumerate(lines):
            line_y = y_pos + line_idx * line_height
            text_baseline_offset = (line_height - instance.size) / 2
            flipped_y = viewport_height - line_y - instance.size - text_baseline_offset
            selection_y = viewport_height - line_y - line_height
            
            if instance.selection_start is not None and instance.text:
                start = min(instance.cursor_pos, instance.selection_start)
                end = max(instance.cursor_pos, instance.selection_start)
                
                char_count = sum(len(lines[i]) + (1 if i < len(lines) - 1 else 0) for i in range(line_idx))
                line_start = char_count
                line_end = char_count + len(line)
                
                if start < line_end and end > line_start:
                    sel_start_in_line = max(0, start - line_start)
                    sel_end_in_line = min(len(line), end - line_start)
                    
                    before_sel = line[:sel_start_in_line]
                    selected = line[sel_start_in_line:sel_end_in_line]
                    
                    before_width, _ = blf.dimensions(instance.font_id, before_sel)
                    sel_width, _ = blf.dimensions(instance.font_id, selected)
                    
                    import gpu
                    from gpu_extras.batch import batch_for_shader
                    
                    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
                    
                    sel_x = x_pos + before_width
                    sel_height = line_height
                    
                    vertices = (
                        (sel_x, selection_y),
                        (sel_x + sel_width, selection_y),
                        (sel_x, selection_y + sel_height),
                        (sel_x + sel_width, selection_y + sel_height),
                    )
                    
                    indices = ((0, 1, 2), (1, 2, 3))
                    
                    batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)
                    shader.bind()
                    shader.uniform_float("color", instance.selection_color)
                    batch.draw(shader)
            
            blf.position(instance.font_id, x_pos, flipped_y, 0)
            blf.color(instance.font_id, *display_color)
            blf.draw(instance.font_id, line)
        
        if instance.is_focused and instance.show_cursor:
            line_idx, col = instance.get_cursor_position_2d()
            
            if line_idx < len(lines):
                line = lines[line_idx]
                text_before_cursor = line[:col]
                cursor_x_offset, _ = blf.dimensions(instance.font_id, text_before_cursor)
                
                cursor_x = x_pos + cursor_x_offset
                cursor_y_line = y_pos + line_idx * line_height
                cursor_y_flipped = viewport_height - cursor_y_line - line_height
                
                import gpu
                from gpu_extras.batch import batch_for_shader
                
                shader = gpu.shader.from_builtin('UNIFORM_COLOR')
                
                cursor_height = line_height
                cursor_width = 2
                vertices = (
                    (cursor_x, cursor_y_flipped),
                    (cursor_x + cursor_width, cursor_y_flipped),
                    (cursor_x, cursor_y_flipped + cursor_height),
                    (cursor_x + cursor_width, cursor_y_flipped + cursor_height),
                )
                
                indices = ((0, 1, 2), (1, 2, 3))
                
                batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)
                shader.bind()
                shader.uniform_float("color", instance.cursor_color)
                batch.draw(shader)
        
        if instance.mask and instance.mask[2] > 0 and instance.mask[3] > 0:
            blf.disable(instance.font_id, blf.CLIPPING)

class KeyboardHandler(bpy.types.Operator):
    bl_idname = "xwz.text_input_keyboard"
    bl_label  = "Text Input Keyboard Handler"
    
    def invoke(self, context, event):
        global _keyboard_handler_running
        _keyboard_handler_running = True
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    
    def modal(self, context, event):
        global _active_input_id, _text_input_instances, _keyboard_handler_running
        
        if not _text_input_instances:
            _keyboard_handler_running = False
            return {'CANCELLED'}
        
        if _active_input_id is None:
            return {'PASS_THROUGH'}
        
        active_input = None
        for instance in _text_input_instances:
            if instance.id == _active_input_id:
                active_input = instance
                break
        
        if not active_input:
            return {'PASS_THROUGH'}
        
        if event.type in {'LEFTMOUSE', 'RIGHTMOUSE'} and event.value == 'PRESS':
            return {'PASS_THROUGH'}
        
        if event.type == 'ESC' and event.value == 'PRESS':
            active_input.blur()
            return {'RUNNING_MODAL'}
        
        if event.type == 'RET' and event.value == 'PRESS':
            if event.shift:
                active_input.insert_text('\n')
            else:
                active_input.blur()
            return {'RUNNING_MODAL'}
        
        if event.type == 'BACK_SPACE' and event.value == 'PRESS':
            active_input.backspace()
            return {'RUNNING_MODAL'}
        
        if event.type == 'DEL' and event.value == 'PRESS':
            active_input.delete()
            return {'RUNNING_MODAL'}
        
        if event.type == 'LEFT_ARROW' and event.value == 'PRESS':
            active_input.move_cursor_left(event.shift)
            return {'RUNNING_MODAL'}
        
        if event.type == 'RIGHT_ARROW' and event.value == 'PRESS':
            active_input.move_cursor_right(event.shift)
            return {'RUNNING_MODAL'}
        
        if event.type == 'UP_ARROW' and event.value == 'PRESS':
            active_input.move_cursor_up(event.shift)
            return {'RUNNING_MODAL'}
        
        if event.type == 'DOWN_ARROW' and event.value == 'PRESS':
            active_input.move_cursor_down(event.shift)
            return {'RUNNING_MODAL'}
        
        if event.type == 'HOME' and event.value == 'PRESS':
            if event.ctrl:
                active_input.cursor_pos = 0
            else:
                lines = active_input.get_wrapped_lines()
                line_idx, col = active_input.get_cursor_position_2d()
                char_count = sum(len(lines[i]) + (1 if i < len(lines) - 1 else 0) for i in range(line_idx))
                active_input.cursor_pos = char_count
            
            if not event.shift:
                active_input.selection_start = None
            return {'RUNNING_MODAL'}
        
        if event.type == 'END' and event.value == 'PRESS':
            if event.ctrl:
                active_input.cursor_pos = len(active_input.text)
            else:
                lines = active_input.get_wrapped_lines()
                line_idx, col = active_input.get_cursor_position_2d()
                char_count = sum(len(lines[i]) + (1 if i < len(lines) - 1 else 0) for i in range(line_idx))
                active_input.cursor_pos = char_count + len(lines[line_idx])
            
            if not event.shift:
                active_input.selection_start = None
            return {'RUNNING_MODAL'}
        
        if event.type == 'A' and event.value == 'PRESS' and event.ctrl:
            active_input.selection_start = 0
            active_input.cursor_pos = len(active_input.text)
            return {'RUNNING_MODAL'}
        
        if event.type == 'C' and event.value == 'PRESS' and event.ctrl:
            if active_input.selection_start is not None:
                start = min(active_input.cursor_pos, active_input.selection_start)
                end = max(active_input.cursor_pos, active_input.selection_start)
                selected_text = active_input.text[start:end]
                context.window_manager.clipboard = selected_text
            return {'RUNNING_MODAL'}
        
        if event.type == 'X' and event.value == 'PRESS' and event.ctrl:
            if active_input.selection_start is not None:
                start = min(active_input.cursor_pos, active_input.selection_start)
                end = max(active_input.cursor_pos, active_input.selection_start)
                selected_text = active_input.text[start:end]
                context.window_manager.clipboard = selected_text
                active_input.delete_selection()
            return {'RUNNING_MODAL'}
        
        if event.type == 'V' and event.value == 'PRESS' and event.ctrl:
            clipboard_text = context.window_manager.clipboard
            if clipboard_text:
                active_input.insert_text(clipboard_text)
            return {'RUNNING_MODAL'}
        
        if event.value == 'PRESS' and event.ascii:
            if not event.ctrl and not event.alt:
                active_input.insert_text(event.ascii)
                return {'RUNNING_MODAL'}
        
        return {'PASS_THROUGH'}

class CreateTextInputOP(bpy.types.Operator):
    bl_idname = "xwz.create_text_input"
    bl_label = "Create Text Input"
    
    container_id   : bpy.props.StringProperty(name="Container ID", default="root")
    placeholder    : bpy.props.StringProperty(name="Placeholder", default="Type here...")
    font_name      : bpy.props.StringProperty(name="Font Name", default="")
    size           : bpy.props.IntProperty(name="Size", default=20, min=1, max=200)
    x_pos          : bpy.props.IntProperty(name="X Position", default=50)
    y_pos          : bpy.props.IntProperty(name="Y Position", default=50)
    color          : bpy.props.FloatVectorProperty(name="Color", subtype='COLOR', size=4, default=(1.0, 1.0, 1.0, 1.0))
    cursor_color   : bpy.props.FloatVectorProperty(name="Cursor Color", subtype='COLOR', size=4, default=(1.0, 1.0, 1.0, 1.0))
    selection_color: bpy.props.FloatVectorProperty(name="Selection Color", subtype='COLOR', size=4, default=(0.3, 0.5, 0.8, 0.3))
    mask_x         : bpy.props.IntProperty(name="Mask X", default=0)
    mask_y         : bpy.props.IntProperty(name="Mask Y", default=0)
    mask_width     : bpy.props.IntProperty(name="Mask Width", default=0)
    mask_height    : bpy.props.IntProperty(name="Mask Height", default=0)
    align_h: bpy.props.EnumProperty(
        name="Horizontal Align",
        items=[('LEFT', 'Left', ''), ('CENTER', 'Center', ''), ('RIGHT', 'Right', '')],
        default='LEFT'
    )
    align_v: bpy.props.EnumProperty(
        name="Vertical Align",
        items=[('TOP', 'Top', ''), ('CENTER', 'Center', ''), ('BOTTOM', 'Bottom', '')],
        default='TOP'
    )
    
    def execute(self, context):
        global _draw_handle, _text_input_instances, _keyboard_handler_running
        
        mask = None
        if self.mask_width > 0 and self.mask_height > 0:
            mask = [self.mask_x, self.mask_y, self.mask_width, self.mask_height]
        
        font_to_use = self.font_name if self.font_name else None
        if font_to_use and font_to_use not in font_manager.get_available_fonts():
            print(f"Warning: Font '{font_to_use}' not found, using default")
            font_to_use = None
        
        new_instance = TextInputInstance(
            container_id=self.container_id,
            placeholder=self.placeholder,
            font_name=font_to_use,
            size=self.size,
            pos=[self.x_pos, self.y_pos],
            color=list(self.color),
            mask=mask,
            align_h=self.align_h,
            align_v=self.align_v,
            cursor_color=list(self.cursor_color),
            selection_color=list(self.selection_color)
        )
        
        new_instance.refresh_font_id()
        
        _text_input_instances.append(new_instance)
        
        if _draw_handle is None:
            _draw_handle = bpy.types.SpaceView3D.draw_handler_add(
                draw_all_text_inputs, (), 'WINDOW', 'POST_PIXEL')
        
        if not _keyboard_handler_running:
            bpy.ops.xwz.text_input_keyboard('INVOKE_DEFAULT')
        
        context.area.tag_redraw()
        self.report({'INFO'}, f"Created text input instance #{new_instance.id}")
        return {'FINISHED'}

class RemoveTextInputOP(bpy.types.Operator):
    bl_idname = "xwz.remove_text_input"
    bl_label  = "Remove Text Input"
    
    instance_id: bpy.props.IntProperty(name="Instance ID", default=0, min=0)
    
    def execute(self, context):
        global _draw_handle, _text_input_instances, _active_input_id
        
        for i, instance in enumerate(_text_input_instances):
            if instance.id == self.instance_id:
                if _active_input_id == instance.id:
                    _active_input_id = None
                _text_input_instances.pop(i)
                self.report({'INFO'}, f"Removed text input instance #{self.instance_id}")
                break
        else:
            self.report({'ERROR'}, f"Text input instance #{self.instance_id} not found")
            return {'CANCELLED'}
        
        if not _text_input_instances and _draw_handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, 'WINDOW')
            _draw_handle = None
        
        context.area.tag_redraw()
        return {'FINISHED'}

class ClearTextInputsOP(bpy.types.Operator):
    bl_idname = "xwz.clear_text_inputs"
    bl_label = "Clear All Text Inputs"
    
    def execute(self, context):
        global _draw_handle, _text_input_instances, _active_input_id, _keyboard_handler_running, _next_input_id
        
        _text_input_instances.clear()
        _active_input_id = None
        _keyboard_handler_running = False
        _next_input_id = 0
        
        if _draw_handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, 'WINDOW')
            _draw_handle = None
        
        context.area.tag_redraw()
        return {'FINISHED'}

class FocusTextInputOP(bpy.types.Operator):
    bl_idname = "xwz.focus_text_input"
    bl_label  = "Focus Text Input"
    
    instance_id: bpy.props.IntProperty(name="Instance ID", default=0, min=0)
    
    def execute(self, context):
        global _text_input_instances
        
        for instance in _text_input_instances:
            if instance.id == self.instance_id:
                for other in _text_input_instances:
                    if other.id != self.instance_id:
                        other.blur()
                
                instance.focus()
                context.area.tag_redraw()
                return {'FINISHED'}
        
        self.report({'ERROR'}, f"Text input instance #{self.instance_id} not found")
        return {'CANCELLED'}

class BlurTextInputOP(bpy.types.Operator):
    bl_idname = "xwz.blur_text_input"
    bl_label  = "Blur Text Input"
    
    instance_id: bpy.props.IntProperty(name="Instance ID", default=0, min=0)
    
    def execute(self, context):
        global _text_input_instances
        
        for instance in _text_input_instances:
            if instance.id == self.instance_id:
                instance.blur()
                context.area.tag_redraw()
                return {'FINISHED'}
        
        self.report({'ERROR'}, f"Text input instance #{self.instance_id} not found")
        return {'CANCELLED'}

class GetTextInputValueOP(bpy.types.Operator):
    bl_idname = "xwz.get_text_input_value"
    bl_label  = "Get Text Input Value"
    
    instance_id: bpy.props.IntProperty(name="Instance ID", default=0, min=0)
    
    def execute(self, context):
        global _text_input_instances
        
        for instance in _text_input_instances:
            if instance.id == self.instance_id:
                print(f"Text input #{self.instance_id} value: {instance.text}")
                return {'FINISHED'}
        
        self.report({'ERROR'}, f"Text input instance #{self.instance_id} not found")
        return {'CANCELLED'}

class SetTextInputValueOP(bpy.types.Operator):
    bl_idname = "xwz.set_text_input_value"
    bl_label  = "Set Text Input Value"
    
    instance_id: bpy.props.IntProperty(name="Instance ID", default=0, min=0)
    text: bpy.props.StringProperty(name="Text", default="")
    
    def execute(self, context):
        global _text_input_instances
        
        for instance in _text_input_instances:
            if instance.id == self.instance_id:
                instance.text = self.text
                instance.cursor_pos = len(self.text)
                instance.selection_start = None
                instance._request_refresh()
                return {'FINISHED'}
        
        self.report({'ERROR'}, f"Text input instance #{self.instance_id} not found")
        return {'CANCELLED'}

class UpdateTextInputOP(bpy.types.Operator):
    bl_idname = "xwz.update_text_input"
    bl_label  = "Update Text Input"
    
    instance_id    : bpy.props.IntProperty(name="Instance ID", default=0, min=0)
    placeholder    : bpy.props.StringProperty(name="Placeholder", default="")
    font_name      : bpy.props.StringProperty(name="Font Name", default="")
    size           : bpy.props.IntProperty(name="Size", default=-1, min=-1, max=200)
    x_pos          : bpy.props.IntProperty(name="X Position", default=-999999)
    y_pos          : bpy.props.IntProperty(name="Y Position", default=-999999)
    color          : bpy.props.FloatVectorProperty(name="Color", subtype='COLOR', size=4, default=(-1, -1, -1, -1))
    cursor_color   : bpy.props.FloatVectorProperty(name="Cursor Color", subtype='COLOR', size=4, default=(-1, -1, -1, -1))
    selection_color: bpy.props.FloatVectorProperty(name="Selection Color", subtype='COLOR', size=4, default=(-1, -1, -1, -1))
    mask_x         : bpy.props.IntProperty(name="Mask X", default=-999999)
    mask_y         : bpy.props.IntProperty(name="Mask Y", default=-999999)
    mask_width     : bpy.props.IntProperty(name="Mask Width", default=-1)
    mask_height    : bpy.props.IntProperty(name="Mask Height", default=-1)
    align_h: bpy.props.EnumProperty(
        name="Horizontal Align",
        items=[('__NOCHANGE__', 'No Change', ''), ('LEFT', 'Left', ''), ('CENTER', 'Center', ''), ('RIGHT', 'Right', '')],
        default='__NOCHANGE__'
    )
    align_v: bpy.props.EnumProperty(
        name="Vertical Align",
        items=[('__NOCHANGE__', 'No Change', ''), ('TOP', 'Top', ''), ('CENTER', 'Center', ''), ('BOTTOM', 'Bottom', '')],
        default='__NOCHANGE__'
    )
    
    def execute(self, context):
        for instance in _text_input_instances:
            if instance.id == self.instance_id:
                updated_props = []
                
                if self.placeholder:
                    instance.placeholder = self.placeholder
                    updated_props.append('placeholder')
                
                if self.font_name and self.font_name in font_manager.get_available_fonts():
                    instance.font_name = self.font_name
                    instance.refresh_font_id()
                    updated_props.append('font_name')
                
                if self.size != -1:
                    instance.size = self.size
                    updated_props.append('size')
                
                if self.x_pos != -999999 or self.y_pos != -999999:
                    if self.x_pos != -999999:
                        instance.position[0] = self.x_pos
                    if self.y_pos != -999999:
                        instance.position[1] = self.y_pos
                    updated_props.append('position')
                
                if any(c != -1 for c in self.color):
                    for i in range(4):
                        if self.color[i] != -1:
                            instance.color[i] = self.color[i]
                    updated_props.append('color')
                
                if any(c != -1 for c in self.cursor_color):
                    for i in range(4):
                        if self.cursor_color[i] != -1:
                            instance.cursor_color[i] = self.cursor_color[i]
                    updated_props.append('cursor_color')
                
                if any(c != -1 for c in self.selection_color):
                    for i in range(4):
                        if self.selection_color[i] != -1:
                            instance.selection_color[i] = self.selection_color[i]
                    updated_props.append('selection_color')
                
                if (self.mask_x != -999999 or self.mask_y != -999999 or 
                    self.mask_width != -1 or self.mask_height != -1):
                    current_mask = instance.mask or [0, 0, 0, 0]
                    new_mask = [
                        self.mask_x if self.mask_x != -999999 else current_mask[0],
                        self.mask_y if self.mask_y != -999999 else current_mask[1],
                        self.mask_width if self.mask_width != -1 else current_mask[2],
                        self.mask_height if self.mask_height != -1 else current_mask[3]
                    ]
                    instance.mask = new_mask if new_mask[2] > 0 and new_mask[3] > 0 else None
                    updated_props.append('mask')
                
                if self.align_h != '__NOCHANGE__':
                    instance.align_h = self.align_h
                    updated_props.append('align_h')
                
                if self.align_v != '__NOCHANGE__':
                    instance.align_v = self.align_v
                    updated_props.append('align_v')
                
                if updated_props:
                    instance._request_refresh()
                    self.report({'INFO'}, f"Updated text input #{self.instance_id}: {', '.join(updated_props)}")
                else:
                    self.report({'INFO'}, f"No properties specified to update for text input #{self.instance_id}")
                
                return {'FINISHED'}
        
        self.report({'ERROR'}, f"Text input instance #{self.instance_id} not found")
        return {'CANCELLED'}

def register():
    bpy.utils.register_class(KeyboardHandler)
    bpy.utils.register_class(CreateTextInputOP)
    bpy.utils.register_class(RemoveTextInputOP)
    bpy.utils.register_class(ClearTextInputsOP)
    bpy.utils.register_class(FocusTextInputOP)
    bpy.utils.register_class(BlurTextInputOP)
    bpy.utils.register_class(GetTextInputValueOP)
    bpy.utils.register_class(SetTextInputValueOP)
    bpy.utils.register_class(UpdateTextInputOP)

def unregister():
    global _draw_handle, _text_input_instances, _active_input_id, _keyboard_handler_running, _next_input_id
    
    _text_input_instances.clear()
    _active_input_id = None
    _keyboard_handler_running = False
    _next_input_id = 0
    
    if _draw_handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, 'WINDOW')
        _draw_handle = None
    
    bpy.utils.unregister_class(KeyboardHandler)
    bpy.utils.unregister_class(CreateTextInputOP)
    bpy.utils.unregister_class(RemoveTextInputOP)
    bpy.utils.unregister_class(ClearTextInputsOP)
    bpy.utils.unregister_class(FocusTextInputOP)
    bpy.utils.unregister_class(BlurTextInputOP)
    bpy.utils.unregister_class(GetTextInputValueOP)
    bpy.utils.unregister_class(SetTextInputValueOP)
    bpy.utils.unregister_class(UpdateTextInputOP)
