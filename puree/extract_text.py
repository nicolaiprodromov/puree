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
                'font'                    : container.font if container.font != '' else self.ui.theme.default_font,
                'text_x'                  : int(self.json_data[self.flat_index]['position'][0] + container.style.text_x),
                'text_y'                  : int(self.json_data[self.flat_index]['position'][1] + container.style.text_y),
                'font_size'               : int(container.style.font_size),
                'color'                   : container.style.color,
                'color_2'                 : container.style.color_2,
                'color_gradient_rot'      : container.style.color_gradient_rot,
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
            }
        self.flat_index += 1
        for child in container.children:  
            self._extract_texts(child)
