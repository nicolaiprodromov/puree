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
class ImageExtractor:
    def __init__(self, ui, json_data):
        self.ui = ui
        self.json_data = json_data
        self.image_blocks = {}
        self.image_blocks_relative = {}
        self.flat_index = 0
        self._extract_images(self.ui.theme.root)

    def _extract_images(self, container):
        if container.img != "":
            # Use content box (inside padding+border) for image positioning
            content_box = getattr(container, '_content_box_abs', None)
            if content_box and content_box["width"] > 0:
                img_x = content_box["x"]
                img_y = content_box["y"]
                img_w = content_box["width"]
                img_h = content_box["height"]
            else:
                img_x = self.json_data[self.flat_index]["position"][0]
                img_y = self.json_data[self.flat_index]["position"][1]
                img_w = self.json_data[self.flat_index]["size"][0]
                img_h = self.json_data[self.flat_index]["size"][1]

            self.image_blocks[container.id] = {
                "container_id": container.id,
                "image_name": container.img,
                "x_pos": int(img_x),
                "y_pos": int(img_y),
                "width": int(img_w),
                "height": int(img_h),
                "mask_x": int(img_x),
                "mask_y": int(img_y),
                "mask_width": int(img_w),
                "mask_height": int(img_h),
                "aspect_ratio": container.style.aspect_ratio,
                "align_h": container.style.img_align_h,
                "align_v": container.style.img_align_v,
                "opacity": container.style.opacity,
            }
        self.flat_index += 1
        for child in container.children:
            self._extract_images(child)
