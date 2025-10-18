class ImageExtractor():
    def __init__(self, ui, json_data):
        self.ui                    = ui
        self.json_data             = json_data
        self.image_blocks          = {}
        self.image_blocks_relative = {}
        self.flat_index            = 0
        self._extract_images(self.ui.theme.root)
    def _extract_images(self, container):
        if container.img != '':
            self.image_blocks[container.id] = {
                'container_id': container.id,
                'image_name'  : container.img,
                'x_pos'       : int(self.json_data[self.flat_index]['position'][0]),
                'y_pos'       : int(self.json_data[self.flat_index]['position'][1]),
                'width'       : int(self.json_data[self.flat_index]['size'][0]),
                'height'      : int(self.json_data[self.flat_index]['size'][1]),
                "mask_x"      : int(self.json_data[self.flat_index]['position'][0]),
                "mask_y"      : int(self.json_data[self.flat_index]['position'][1]),
                "mask_width"  : int(self.json_data[self.flat_index]['size'][0]),
                "mask_height" : int(self.json_data[self.flat_index]['size'][1]),
                "aspect_ratio": container.style.aspect_ratio,
                'align_h'     : container.style.img_align_h,
                'align_v'     : container.style.img_align_v,
                'opacity'     : container.style.img_opacity
            }
        self.flat_index += 1
        for child in container.children:
            self._extract_images(child)

