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
try:
    from .log import get_logger

    logger = get_logger(__name__)
except Exception:  # pragma: no cover - outside the package/Blender
    import logging

    logger = logging.getLogger(__name__)


class ImageExtractor:
    # root/content_boxes (both default None = the pre-fullscreen behavior)
    # let the fullscreen private pass (puree.fullscreen) re-extract ONE
    # subtree against its private layout: root scopes the walk, and
    # content_boxes (id -> {x, y, width, height}) overrides the live
    # container._content_box_abs, which always belongs to the MAIN layout.
    def __init__(self, ui, json_data, root=None, content_boxes=None):
        self.ui = ui
        self.json_data = json_data
        self.content_boxes = content_boxes
        self.image_blocks = {}
        self.image_blocks_relative = {}
        self.flat_index = 0
        self._extract_images(root if root is not None else self.ui.theme.root)

    def _resolve_content_box(self, container):
        if self.content_boxes is not None:
            box = self.content_boxes.get(container.id)
            if box is not None:
                return box
        return getattr(container, "_content_box_abs", None)

    def _extract_images(self, container):
        img_value = str(getattr(container, "img", "") or "")
        video_value = str(getattr(container, "video", "") or "")
        lottie_value = str(getattr(container, "lottie", "") or "")
        if img_value and video_value:
            logger.warning(f"Container '{container.id}' sets both img: and video: - img wins, video: ignored")
            video_value = ""
        if lottie_value and (img_value or video_value):
            # Same precedence pattern: img > video > lottie.
            winner = "img" if img_value else "video"
            logger.warning(
                f"Container '{container.id}' sets both {winner}: and lottie: - {winner} wins, lottie: ignored"
            )
            lottie_value = ""

        if img_value != "" or video_value != "" or lottie_value != "":
            # Use content box (inside padding+border) for image positioning
            content_box = self._resolve_content_box(container)
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

            block = {
                "container_id": container.id,
                # video:/lottie: nodes ride the same image_blocks stream -
                # the asset name is the media filename; MediaManager
                # dispatches on its extension.
                "image_name": img_value or video_value or lottie_value,
                # "image" covers every img: format (gif/svg stay
                # extension-dispatched downstream); "video"/"lottie" mark
                # their dedicated attributes.
                "media_kind": "image" if img_value else ("video" if video_value else "lottie"),
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
            if video_value:
                # Playback attributes travel with the block (Container
                # coerced them to clean bool/float types at assignment).
                from .components.container import coerce_bool, coerce_float

                block["poster"] = str(getattr(container, "poster", "") or "")
                block["controls"] = coerce_bool(getattr(container, "controls", False))
                block["autoplay"] = coerce_bool(getattr(container, "autoplay", False))
                block["loop"] = coerce_bool(getattr(container, "loop", False))
                block["muted"] = coerce_bool(getattr(container, "muted", False))
                block["volume"] = coerce_float(getattr(container, "volume", 1.0), 1.0)
                block["playback_rate"] = coerce_float(getattr(container, "playback_rate", 1.0), 1.0)
                block["preload"] = str(getattr(container, "preload", "metadata") or "metadata").strip().lower()
            elif lottie_value:
                from .components.container import coerce_bool, coerce_float

                # Lottie playback attrs (MEDIA_PLAN section 5.4): autoplay
                # and loop default TRUE (lottie-player parity) while the
                # shared Container defaults stay False (HTML <video>
                # parity) - so the per-kind default applies only when the
                # author never assigned the attr (Container.__setattr__
                # records assignments in _authored_media_attrs).
                authored = getattr(container, "_authored_media_attrs", None) or ()
                block["autoplay"] = (
                    coerce_bool(getattr(container, "autoplay", True)) if "autoplay" in authored else True
                )
                block["loop"] = coerce_bool(getattr(container, "loop", True)) if "loop" in authored else True
                block["playback_rate"] = coerce_float(getattr(container, "playback_rate", 1.0), 1.0)
                if coerce_bool(getattr(container, "controls", False)):
                    # controls: is a <video> feature (the Phase 5 bar) -
                    # not supported on lottie elements (plan section 5.4).
                    logger.debug(f"Container '{container.id}': controls: has no effect on lottie: elements - ignored")
            self.image_blocks[container.id] = block
        self.flat_index += 1
        for child in container.children:
            self._extract_images(child)
