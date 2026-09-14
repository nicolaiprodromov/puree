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
"""SVG media source - wraps the Rust ``probe_svg``/``rasterize_svg`` core.

SVGs are static: rasterized once at the element's content-box size
(aspect-fit inside it at the intrinsic ratio from ``probe_svg``, so the
raster is pixel-exact for what draw_all_images will display), uploaded
once, then zero per-tick cost - ``is_active()`` is False while settled,
so a page of SVGs never forces a redraw (MEDIA_PLAN section 5.2/10).

The only ongoing work is a lightweight size-watch inside ``tick()``
(two int comparisons): when the content box changes by more than 1 px
(panel resize, layout change) a ~150 ms debounce starts; once the size
holds still the file is re-rasterized at the new size and the texture
swapped, keeping vectors crisp at any panel size.

Rasters are cached per ``(abs path, raster w, raster h)`` keeping the
last 2 sizes per path, so drag-resizing back and forth re-uploads from
cache instead of re-rasterizing. The cache stores CPU bytes only (GPU
textures are per-element) and survives shutdown() like the GIF decode
cache - a UI restart never re-rasterizes at an already-seen size.
"""

import os
from collections import OrderedDict

try:
    from ...log import get_logger

    logger = get_logger(__name__)
except Exception:  # pragma: no cover - outside the package/Blender
    import logging

    logger = logging.getLogger(__name__)

from ..upload import upload_texture

# Content-box changes at or below this many pixels (per axis) never
# trigger a re-raster (plan section 5.2: +-1 px).
RESIZE_TOLERANCE_PX = 1
# The content box must hold still this long before re-rasterizing -
# absorbs per-frame churn during a panel drag-resize.
RESIZE_DEBOUNCE_S = 0.15
# Raster sizes kept per file: the current one + the previous one.
CACHE_SIZES_PER_PATH = 2

# abs path -> (intrinsic_w, intrinsic_h), from probe_svg
_intrinsic_cache = {}
# abs path -> OrderedDict[(w, h) -> bytes], LRU per path (newest last)
_raster_cache = {}


def get_intrinsic_size(path):
    """Intrinsic (width, height) of an SVG, cached per absolute path.

    Comes from the usvg tree (width/height attributes with a viewBox
    fallback) - feeds aspect-fitting before the first rasterization.
    """
    abs_path = os.path.abspath(path)
    size = _intrinsic_cache.get(abs_path)
    if size is None:
        from ... import native_bindings

        size = tuple(native_bindings.probe_svg(abs_path))
        _intrinsic_cache[abs_path] = size
    return size


def get_fonts_dir():
    """The addon's bundled ``fonts/`` dir (or None when absent).

    Handed to the rasterizer so ``<text>`` elements in SVGs resolve the
    same fonts the UI ships, on top of the system fonts the Rust core
    loads once per session.
    """
    try:
        from ... import get_addon_root

        root = get_addon_root()
    except Exception:  # pragma: no cover - outside the addon package
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    fonts = os.path.join(root, "fonts")
    return fonts if os.path.isdir(fonts) else None


def fit_size(intrinsic_w, intrinsic_h, box_w, box_h):
    """Largest integer raster size that fits ``box_w x box_h`` while
    preserving the intrinsic aspect ratio (aspect-FIT). Never below 1x1."""
    if intrinsic_w <= 0 or intrinsic_h <= 0:
        return max(1, int(box_w)), max(1, int(box_h))
    scale = min(box_w / intrinsic_w, box_h / intrinsic_h)
    return max(1, round(intrinsic_w * scale)), max(1, round(intrinsic_h * scale))


def get_raster(path, width, height):
    """Premultiplied bottom-up RGBA8 bytes for ``path`` at ``width x height``,
    cached per (abs path, w, h) with the last CACHE_SIZES_PER_PATH sizes kept."""
    abs_path = os.path.abspath(path)
    per_path = _raster_cache.setdefault(abs_path, OrderedDict())
    key = (int(width), int(height))
    data = per_path.get(key)
    if data is not None:
        per_path.move_to_end(key)
        return data

    from ... import native_bindings

    data = native_bindings.rasterize_svg(abs_path, key[0], key[1], get_fonts_dir())
    per_path[key] = data
    while len(per_path) > CACHE_SIZES_PER_PATH:
        per_path.popitem(last=False)
    logger.debug(f"Rasterized SVG {os.path.basename(abs_path)} at {key[0]}x{key[1]}")
    return data


def clear_cache():
    """Drop cached intrinsic sizes and rasters (full purge)."""
    _intrinsic_cache.clear()
    _raster_cache.clear()


class SvgSource:
    """Per-element rasterization of one SVG file onto one ImageInstance."""

    kind = "svg"

    def __init__(self, container_id, image_name, path, instance):
        self.container_id = container_id
        self.image_name = image_name  # asset key, e.g. "logo.svg" / "icons/play.svg"
        self.path = os.path.abspath(path)
        self.instance = instance
        self.released = False

        self.intrinsic = get_intrinsic_size(self.path)  # may raise - attach() logs and skips
        self._texture = None
        self._rastered_box = None  # content-box size the current texture was rastered for
        self._pending_box = None  # changed size waiting out the debounce
        self._pending_since = 0.0
        self._rasterize(self._box_size())
        self._apply_texture()

    # -- internals ----------------------------------------------------

    def _box_size(self):
        """The element's live content box as ints.

        ``instance.size`` mirrors the extractor's content box exactly
        (extract_images emits width == mask_width, height == mask_height,
        and every update_all/update_size keeps it >= 1), so it doubles as
        the mask size without touching ``instance.mask`` (which may be
        None while a container reports a zero-size box).
        """
        size = self.instance.size
        return (int(size[0]), int(size[1]))

    def _rasterize(self, box):
        """Rasterize aspect-fit into ``box`` and (re)build the texture."""
        w, h = fit_size(self.intrinsic[0], self.intrinsic[1], box[0], box[1])
        self._texture = upload_texture(w, h, get_raster(self.path, w, h))
        self._rastered_box = box

    def _apply_texture(self):
        """Push the current texture onto the instance (and build its batch)."""
        instance = self.instance
        if instance is None:
            return
        instance.texture = self._texture
        if instance.batch is None:
            instance._create_batch()

    # -- MediaSource interface ----------------------------------------

    def tick(self, now):
        """Size-watch + self-heal; True when the visible texture changed."""
        instance = self.instance
        if self.released or instance is None:
            return False
        if instance.image_name != self.image_name:
            # The element was retargeted to another asset (hot reload /
            # script update_image) - this source no longer owns it.
            self.release()
            return False

        changed = False

        # Lightweight size-watch (the whole per-tick cost of a settled
        # SVG, besides the identity self-heal below): re-raster only when
        # the content box moved beyond the tolerance AND held still for
        # the debounce window ("stable"), so drag-resize churn is free.
        box = self._box_size()
        if (
            abs(box[0] - self._rastered_box[0]) <= RESIZE_TOLERANCE_PX
            and abs(box[1] - self._rastered_box[1]) <= RESIZE_TOLERANCE_PX
        ):
            self._pending_box = None  # settled back onto the current raster
        elif box != self._pending_box:
            self._pending_box = box  # (re)start the debounce
            self._pending_since = now
        elif now - self._pending_since >= RESIZE_DEBOUNCE_S:
            self._rasterize(box)
            self._apply_texture()
            self._pending_box = None
            changed = True

        # Self-heal: scroll/dirty-sync/hot-reload paths call
        # instance.update_all(image_name=...), which resets the texture to
        # the ImageManager stub (None for media formats). Identity check is
        # cheap and keeps the rastered SVG visible through those paths.
        if instance.texture is not self._texture:
            self._apply_texture()
            changed = True
        return changed

    def is_active(self, now=None):
        """True only while a resize debounce is pending.

        A settled SVG is static - it must never count as active so
        MediaManager.has_active() stays False and the UI idles at zero
        redraws (the plan's non-negotiable idle rule).
        """
        return not self.released and self.instance is not None and self._pending_box is not None

    def release(self):
        """Detach from the instance and drop per-element GPU refs (idempotent)."""
        self.released = True
        self._pending_box = None
        self._texture = None
        self.instance = None
