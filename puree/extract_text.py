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
class TextExtractor:
    def __init__(self, ui, json_data):
        self.ui                 = ui
        self.json_data          = json_data
        self.text_blocks        = {}
        self.flat_index         = 0
        self._extract_texts(self.ui.theme.root)
    def _extract_texts(self, container):
        if container.text != '':
            text = container.text
            transform = getattr(container.style, 'text_transform', 'NONE')
            if transform == 'UPPERCASE':
                text = text.upper()
            elif transform == 'LOWERCASE':
                text = text.lower()
            elif transform == 'CAPITALIZE':
                text = text.title()
            self.text_blocks[container.id] = {
                'container_id'            : container.id,
                'text'                    : text,
                'font'                    : container.font if container.font != '' else (self.ui.theme.default_font or 'default'),
                'text_x'                  : int(self.json_data[self.flat_index]['position'][0] + container.style.text_x),
                'text_y'                  : int(self.json_data[self.flat_index]['position'][1] + container.style.text_y),
                'font_size'               : int(container.style.font_size),
                'color'                   : container.style.color,
                'mask_x'                  : int(self.json_data[self.flat_index]['position'][0]),
                'mask_y'                  : int(self.json_data[self.flat_index]['position'][1]),
                'mask_width'              : int(self.json_data[self.flat_index]['size'][0]),
                'mask_height'             : int(self.json_data[self.flat_index]['size'][1]),
                'align_h'                 : container.style.text_align,
                'align_v'                 : container.style.text_align_v,
                'opacity'                 : container.style.opacity,
                'text_decoration'         : getattr(container.style, 'text_decoration', 'NONE'),
                'letter_spacing'          : float(getattr(container.style, 'letter_spacing', 0)),
                'line_height'             : float(getattr(container.style, 'line_height', 0)),
                'font_weight'             : getattr(container.style, 'font_weight', 'NORMAL'),
                'font_style'              : getattr(container.style, 'font_style', 'NORMAL'),
                'white_space'             : getattr(container.style, 'white_space', 'NORMAL'),
                'text_overflow'           : getattr(container.style, 'text_overflow', 'CLIP'),
                'text_shadow_color'       : getattr(container.style, 'text_shadow_color', [0, 0, 0, 0]),
                'text_shadow_offset_x'    : float(getattr(container.style, 'text_shadow_offset_x', 0)),
                'text_shadow_offset_y'    : float(getattr(container.style, 'text_shadow_offset_y', 0)),
                'text_shadow_blur'        : float(getattr(container.style, 'text_shadow_blur', 0)),
            }
        self.flat_index += 1
        for child in container.children:  
            self._extract_texts(child)
