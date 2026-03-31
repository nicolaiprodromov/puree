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
        self.ui = ui
        self.json_data = json_data
        self.text_blocks = {}
        self.flat_index = 0
        self._extract_texts(self.ui.theme.root)

    def _extract_texts(self, container):
        if container.text != "":
            text = container.text
            transform = getattr(container.style, "text_transform", "NONE")
            if transform == "UPPERCASE":
                text = text.upper()
            elif transform == "LOWERCASE":
                text = text.lower()
            elif transform == "CAPITALIZE":
                text = text.title()

            # Use content box (inside padding+border) for text positioning
            content_box = getattr(container, '_content_box_abs', None)
            if content_box and content_box["width"] > 0:
                text_origin_x = content_box["x"]
                text_origin_y = content_box["y"]
                text_area_w = content_box["width"]
                text_area_h = content_box["height"]
            else:
                text_origin_x = self.json_data[self.flat_index]["position"][0]
                text_origin_y = self.json_data[self.flat_index]["position"][1]
                text_area_w = self.json_data[self.flat_index]["size"][0]
                text_area_h = self.json_data[self.flat_index]["size"][1]

            self.text_blocks[container.id] = {
                "container_id": container.id,
                "text": text,
                "font": container.font if container.font != "" else (self.ui.theme.default_font or "default"),
                "text_x": int(text_origin_x + container.style.text_x),
                "text_y": int(text_origin_y + container.style.text_y),
                "font_size": int(container.style.font_size),
                "color": container.style.color,
                "mask_x": int(text_origin_x),
                "mask_y": int(text_origin_y),
                "mask_width": int(text_area_w),
                "mask_height": int(text_area_h),
                "align_h": container.style.text_align,
                "align_v": container.style.text_align_v,
                "opacity": container.style.opacity,
                "text_decoration": getattr(container.style, "text_decoration", "NONE"),
                "letter_spacing": float(getattr(container.style, "letter_spacing", 0)),
                "line_height": float(getattr(container.style, "line_height", 0)),
                "font_weight": getattr(container.style, "font_weight", "NORMAL"),
                "font_style": getattr(container.style, "font_style", "NORMAL"),
                "white_space": getattr(container.style, "white_space", "NORMAL"),
                "text_overflow": getattr(container.style, "text_overflow", "CLIP"),
                "overflow_wrap": getattr(container.style, "overflow_wrap", "NORMAL"),
                "word_break": getattr(container.style, "word_break", "NORMAL"),
                "text_shadow_color": getattr(container.style, "text_shadow_color", [0, 0, 0, 0]),
                "text_shadow_offset_x": float(getattr(container.style, "text_shadow_offset_x", 0)),
                "text_shadow_offset_y": float(getattr(container.style, "text_shadow_offset_y", 0)),
                "text_shadow_blur": float(getattr(container.style, "text_shadow_blur", 0)),
            }
        self.flat_index += 1
        for child in container.children:
            self._extract_texts(child)
