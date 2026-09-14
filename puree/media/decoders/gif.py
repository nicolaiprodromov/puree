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
"""GIF media source - wraps the Rust ``decode_gif`` core function.

Decode results are cached per absolute path (module-level) and shared
across elements; every element owns its own :class:`MediaClock` so
multiple instances of the same file play independently (browser parity).

GPU strategy (MEDIA_PLAN.md section 10): when the decoded payload
(``w*h*4*frames``) fits the 32 MB per-file budget, all frames are
pre-uploaded as GPUTextures on the first tick and playback just swaps
among them; larger files keep CPU bytes and upload the needed frame
into a small 2-texture ring on demand.

All ``gpu`` imports live inside functions so this module imports cleanly
outside Blender.
"""

import os
from collections import deque

try:
    from ...log import get_logger

    logger = get_logger(__name__)
except Exception:  # pragma: no cover - outside the package/Blender
    import logging

    logger = logging.getLogger(__name__)

from ..clock import MediaClock

# Texture upload (with the SRGB8_A8/RGBA8 probe) is shared by all media
# decoders - see puree.media.upload (get_texture_format lives there too).
from ..upload import upload_texture

# Per-file GPU budget: pre-upload every frame when the full decoded
# animation fits, else fall back to the upload-on-demand texture ring.
PREUPLOAD_BUDGET_BYTES = 32 * 1024 * 1024

# abs path -> GifData, shared across all elements using the same file
_decode_cache = {}
# abs paths that already logged a decode failure (warn once, never per tick)
_failed_paths = set()


class GifData:
    """Shared, decoded GIF payload for one file (one entry per abs path)."""

    __slots__ = (
        "path",
        "width",
        "height",
        "frames",
        "delays_ms",
        "loop_count",
        "total_bytes",
        "preupload",
        "textures",
        "_first_texture",
    )

    def __init__(self, path, width, height, frames, delays_ms, loop_count):
        self.path = path
        self.width = width
        self.height = height
        self.frames = frames  # list[bytes], premultiplied RGBA8, w*h*4 each
        self.delays_ms = delays_ms
        self.loop_count = loop_count  # 0 = loop forever
        self.total_bytes = width * height * 4 * len(frames)
        self.preupload = self.total_bytes <= PREUPLOAD_BUDGET_BYTES
        self.textures = None  # full frame->GPUTexture list once pre-uploaded
        self._first_texture = None  # frame 0 only (seeded at attach time)

    def first_texture(self):
        """Frame 0 texture - uploaded eagerly at attach so aspect-ratio
        fitting (ImageInstance.get_display_size) is correct immediately."""
        if self.textures:
            return self.textures[0]
        if self._first_texture is None:
            self._first_texture = upload_texture(self.width, self.height, self.frames[0])
        return self._first_texture

    def ensure_all_textures(self):
        """Pre-upload every frame (budget path). Runs once, on the first tick."""
        if self.textures is None:
            textures = []
            for i, frame in enumerate(self.frames):
                if i == 0 and self._first_texture is not None:
                    textures.append(self._first_texture)
                    continue
                textures.append(upload_texture(self.width, self.height, frame))
            self.textures = textures
            self._first_texture = None
        return self.textures

    def release_gpu(self):
        """Drop GPU textures (CPU frames stay cached for fast restarts)."""
        self.textures = None
        self._first_texture = None


def get_gif_data(path):
    """Decode ``path`` via the Rust core, cached per absolute path."""
    abs_path = os.path.abspath(path)
    data = _decode_cache.get(abs_path)
    if data is not None:
        return data

    from ... import native_bindings

    width, height, frames, delays_ms, loop_count = native_bindings.decode_gif(abs_path)
    data = GifData(abs_path, width, height, list(frames), list(delays_ms), loop_count)
    _decode_cache[abs_path] = data
    logger.debug(
        f"Decoded GIF {os.path.basename(abs_path)}: {width}x{height}, "
        f"{len(frames)} frames, {data.total_bytes / (1024 * 1024):.1f} MB "
        f"({'pre-upload' if data.preupload else 'texture ring'}), loop={loop_count or 'infinite'}"
    )
    return data


def release_gpu_textures():
    """Release every cached file's GPU textures (idempotent)."""
    for data in _decode_cache.values():
        data.release_gpu()


def clear_cache():
    """Drop decoded CPU frames too (full purge)."""
    release_gpu_textures()
    _decode_cache.clear()
    _failed_paths.clear()


class GifSource:
    """Per-element playback of one GIF file onto one ImageInstance."""

    kind = "gif"

    def __init__(self, container_id, image_name, path, instance):
        self.container_id = container_id
        self.image_name = image_name  # asset key, e.g. "demo.gif" / "icons/spin.gif"
        self.path = os.path.abspath(path)
        self.instance = instance
        self.released = False

        self.data = get_gif_data(self.path)  # may raise - caller logs and skips
        # 0 = infinite (GIF Netscape convention) -> MediaClock loop=True
        loops = self.data.loop_count
        self.clock = MediaClock(delays_ms=self.data.delays_ms, loop=True if loops == 0 else loops)
        self._static = len(self.data.frames) <= 1
        self._frame_idx = 0
        # Ring only used above the pre-upload budget: hold the current and
        # previous textures so an in-flight draw never loses its texture.
        self._ring = deque(maxlen=2)
        self._texture = self.data.first_texture()
        self._apply_texture()

        # GIFs autoplay on attach, like <img src="*.gif"> in a browser.
        if not self._static:
            self.clock.play()

    # ── internals ────────────────────────────────────────────────────

    def _apply_texture(self):
        """Push the current texture onto the instance (and build its batch)."""
        instance = self.instance
        if instance is None:
            return
        instance.texture = self._texture
        if instance.batch is None:
            instance._create_batch()

    def _texture_for(self, frame_idx):
        if self.data.preupload:
            return self.data.ensure_all_textures()[frame_idx]
        texture = upload_texture(self.data.width, self.data.height, self.data.frames[frame_idx])
        self._ring.append(texture)
        return texture

    # ── MediaSource interface ────────────────────────────────────────

    def tick(self, now):
        """Advance playback; True when the visible texture changed."""
        instance = self.instance
        if self.released or instance is None:
            return False
        if instance.image_name != self.image_name:
            # The element was retargeted to another asset (hot reload /
            # script update_image) - this source no longer owns it.
            self.release()
            return False

        changed = False
        if not self._static and self.clock.is_active(now):
            frame_idx = self.clock.frame_index(now)
            if frame_idx != self._frame_idx:
                self._frame_idx = frame_idx
                self._texture = self._texture_for(frame_idx)
                changed = True

        # Self-heal: scroll/dirty-sync/hot-reload paths call
        # instance.update_all(image_name=...), which resets the texture to
        # the ImageManager stub (None for media formats). Identity check is
        # cheap and keeps paused GIFs visible through those paths.
        if instance.texture is not self._texture:
            self._apply_texture()
            changed = True
        return changed

    def is_active(self, now=None):
        return not self.released and self.instance is not None and not self._static and self.clock.is_active(now)

    def release(self):
        """Detach from the instance and drop per-element GPU refs (idempotent)."""
        self.released = True
        self.clock.pause()
        self._ring.clear()
        self.instance = None

    # ── container.media wiring (Phase 3, minimal) ────────────────────
    # play/pause/loop/playback_rate ride the clock via MediaController's
    # fallbacks; muted/volume are plain stored attributes there (GIFs have
    # no audio - inert by definition). Only seek needs a hook so the frame
    # updates immediately even while paused (tick only advances frames on
    # an active clock).

    ready_state = "ready"  # decoded eagerly at construction

    def seek(self, seconds):
        """Seek the clock and swap the visible frame at once (paused too)."""
        self.clock.seek(seconds)
        if self._static or self.released or self.instance is None:
            return
        frame_idx = self.clock.frame_index()
        if frame_idx != self._frame_idx:
            self._frame_idx = frame_idx
            self._texture = self._texture_for(frame_idx)
            self._apply_texture()
