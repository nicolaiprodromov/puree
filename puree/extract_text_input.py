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
        if container.data != "" and container.data.startswith("<INPUT>"):
            placeholder = ""
            if "|" in container.data:
                parts = container.data.split("|", 1)
                if len(parts) > 1:
                    placeholder = parts[1].strip()

            # Use content box (inside padding+border) for text input positioning
            content_box = getattr(container, '_content_box_abs', None)
            if content_box and content_box["width"] > 0:
                input_x = content_box["x"]
                input_y = content_box["y"]
                input_w = content_box["width"]
                input_h = content_box["height"]
            else:
                input_x = self.json_data[self.flat_index]["position"][0]
                input_y = self.json_data[self.flat_index]["position"][1]
                input_w = self.json_data[self.flat_index]["size"][0]
                input_h = self.json_data[self.flat_index]["size"][1]

            self.text_input_blocks[container.id] = {
                "container_id": container.id,
                "placeholder": placeholder,
                "font": container.font if container.font != "" else self.ui.theme.default_font,
                "x_pos": int(input_x + container.style.text_x),
                "y_pos": int(input_y + container.style.text_y),
                "font_size": int(container.style.font_size),
                "color": container.style.color,
                "mask_x": int(input_x),
                "mask_y": int(input_y),
                "mask_width": int(input_w),
                "mask_height": int(input_h),
                "align_h": container.style.text_align,
                "align_v": container.style.text_align_v,
            }

        self.flat_index += 1
        for child in container.children:
            self._extract_text_inputs(child)
