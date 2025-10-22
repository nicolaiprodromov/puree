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
class TextInputExtractor:
    def __init__(self, ui, json_data):
        self.ui = ui
        self.json_data = json_data
        self.text_input_blocks = {}
        self.flat_index = 0
        self._extract_text_inputs(self.ui.theme.root)
    
    def _extract_text_inputs(self, container):
        if container.data != '' and container.data.startswith('<INPUT>'):
            placeholder = ""
            if '|' in container.data:
                parts = container.data.split('|', 1)
                if len(parts) > 1:
                    placeholder = parts[1].strip()
            
            self.text_input_blocks[container.id] = {
                'container_id': container.id,
                'placeholder': placeholder,
                'font': container.font if container.font != '' else self.ui.theme.default_font,
                'x_pos': int(self.json_data[self.flat_index]['position'][0] + container.style.text_x),
                'y_pos': int(self.json_data[self.flat_index]['position'][1] + container.style.text_y),
                'text_scale': int(container.style.text_scale),
                'text_color': container.style.text_color,
                'text_color_1': container.style.text_color_1,
                'text_color_gradient_rot': container.style.text_color_gradient_rot,
                'mask_x': int(self.json_data[self.flat_index]['position'][0]),
                'mask_y': int(self.json_data[self.flat_index]['position'][1]),
                'mask_width': int(self.json_data[self.flat_index]['size'][0]),
                'mask_height': int(self.json_data[self.flat_index]['size'][1]),
                'align_h': container.style.text_align_h,
                'align_v': container.style.text_align_v
            }
        
        self.flat_index += 1
        for child in container.children:
            self._extract_text_inputs(child)
