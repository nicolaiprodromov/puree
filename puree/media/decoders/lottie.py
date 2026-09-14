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
"""Lottie media source (``lottie: confetti.json``) - rlottie-python render.

``rlottie-python`` (ctypes over Samsung rlottie) SHIPS BUNDLED with Puree
core (MEDIA_PLAN section 12 decision 1, superseded 2026-07-20). It is
still imported lazily inside methods exactly like ``av`` in the video
decoder - a safety net for exotic platforms / broken installs: this
module imports cleanly without it, and a missing package degrades the
element to ``ready_state == 'unsupported'`` (renders nothing - lottie has
no poster) with ONE warning per session.

Extension registration (design)
-------------------------------
This source registers ``.json`` in ``SOURCE_FACTORIES``. ".json" is far
too broad to mean "Lottie" on its own, so :func:`validate_lottie_json`
sniffs the document ON OPEN for the mandatory Bodymovin top-level keys
(``v``, ``fr``, ``w``, ``h``, ``layers`` - per the lottie/Bodymovin
format spec every playable document carries all five). A non-Lottie
``.json`` in ``assets/`` logs one warning (per path, per session) and the
source becomes an inert 'unsupported' stub - never a crash. The sniff
also guards rlottie itself: ``lottie_animation_from_file`` returns a NULL
animation for unparseable input and every subsequent C call on that NULL
would take Blender down, so nothing reaches rlottie without passing
validation, and a NULL animation afterwards is caught and degrades to
``ready_state == 'error'``. ``.lottie`` zip containers are a declared
plan non-goal (v1) and deliberately NOT registered.

rlottie facts (verified against rlottie-python 1.3.8 source + empirically
on the demo asset - the unit suite re-asserts them)
-------------------------------------------------------------------------
- ``LottieAnimation.from_file(path)`` wraps ``lottie_animation_from_file``;
  metadata comes from ``lottie_animation_get_size/_get_totalframe/
  _get_framerate/_get_duration``.
- ``lottie_animation_get_totalframe()`` is INCLUSIVE of the out-point:
  ``op - ip + 1`` (a 90-frame timeline reports 91), while
  ``get_duration() == (op - ip) / fr``. Playback here shows every frame
  for one native frame-time (GIF model), so our duration is
  ``totalframe / fps`` - one frame-time longer than rlottie's number.
- ``lottie_animation_render(frame_num, width=w, height=h) -> bytes`` is a
  CPU raster of exactly ``w*h*4`` bytes in **BGRA byte order,
  PREMULTIPLIED alpha, top-down rows** (the wrapper itself decodes it as
  PIL raw "BGRA"; a 45%-opacity probe renders with every channel <= alpha).
  The pipeline wants premultiplied RGBA with bottom-up rows (the image
  overlay quad samples uv v=0 at its bottom - same convention as the Rust
  GIF/SVG decoders), so :func:`bgra_to_rgba_bottom_up` swizzles R<->B and
  flips the rows; the swizzle preserves premultiplication.
- rlottie keeps the animation's aspect ratio inside the render surface
  (letterboxing a mismatched surface), so frames are rendered at the
  aspect-FIT of the intrinsic size into the element's content box
  (``fit_size``, shared with the SVG source) - surface aspect == intrinsic
  aspect and no letterbox pixels are ever wasted.

Playback & caching (MEDIA_PLAN sections 5.4 / 10)
-------------------------------------------------
The shared :class:`MediaClock` drives playback at the animation's native
fps: the clock is built from error-diffused per-frame delays
(:func:`frame_delays_ms`, boundaries land on ``round(i*1000/fps)`` so no
drift accumulates) and ``clock.frame_index(now)`` resolves the frame -
loop/seek/playback_rate all ride the tested clock machinery. ``autoplay``
and ``loop`` default TRUE (``lottie-player`` parity - the plan's 6.1
example writes ``loop: true`` only for clarity); ``playback_rate`` is
honored; ``muted``/``volume`` are inert stored attributes (no audio).
``controls:`` is a <video> feature and is ignored for lottie elements.

Rendering is on demand, main-thread, per tick (no decoder thread - a
512 px rlottie raster is ~3 ms, within the plan's budget). When the full
animation at the CURRENT raster size fits the 32 MB budget
(``w*h*4*frame_count``), frames are cached progressively as GPUTextures -
each frame is rendered exactly once and the first full loop leaves later
loops swap-only. Over budget, frames render on demand into a small
2-texture reuse ring (an in-flight draw never loses its texture). A
content-box resize re-renders like the SVG source: >1 px drift starts a
~150 ms debounce, and settling drops every cached frame/ring texture and
re-renders the current frame at the new size (budget re-evaluated). The
GPU caches are per element and die with ``release()`` - re-rendering
after a UI restart is cheap, so no CPU frame cache is kept.

All ``gpu`` work goes through ``puree.media.upload.upload_texture`` (the
shared SRGB8_A8/RGBA8 probe); this module imports cleanly outside Blender.
"""

import json
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

# Aspect-fit shares the SVG source's helper (largest integer size inside
# the content box at the intrinsic ratio, never below 1x1).
from .svg import fit_size

# Extensions this source registers for (decoders/__init__.SOURCE_FACTORIES
# derives its LottieSource entries from it). ".lottie" zip containers are
# a plan non-goal (v1) - see the module docstring.
LOTTIE_EXTENSIONS = (".json",)

# Top-level keys every playable Bodymovin/Lottie document carries
# (validate_lottie_json) - version, framerate, canvas size, layer list.
REQUIRED_LOTTIE_KEYS = ("v", "fr", "w", "h", "layers")

# Frame-cache budget per element at the current raster size: at or under
# it every rendered frame is kept as a GPUTexture (render-once-then-reuse
# per loop); above it frames render on demand into the reuse ring
# (MEDIA_PLAN section 10 - same 32 MB rule as the GIF pre-upload).
FRAME_CACHE_BUDGET_BYTES = 32 * 1024 * 1024
# Textures kept alive on the over-budget path: current + previous, so an
# in-flight draw never loses its texture (GIF ring precedent).
RING_TEXTURES = 2

# Size-watch, mirrored from the SVG source: content-box changes at or
# below the tolerance never re-render; bigger changes must hold still for
# the debounce window first (drag-resize churn is free).
RESIZE_TOLERANCE_PX = 1
RESIZE_DEBOUNCE_S = 0.15

_warned_no_rlottie = False  # one missing-dependency warning per session
_warned_paths = set()  # abs paths that already logged a validation/open error


def _import_rlottie():
    """Lazily import rlottie-python; None (+ one session warning) when absent."""
    global _warned_no_rlottie
    try:
        from rlottie_python import LottieAnimation

        return LottieAnimation
    except ImportError:
        if not _warned_no_rlottie:
            _warned_no_rlottie = True
            logger.warning(
                "rlottie ('rlottie-python') is unavailable - it ships bundled with Puree; "
                "refresh/reinstall the Puree extension in Blender (Preferences > Extensions) "
                "or restart Blender (lottie: elements render nothing until then)"
            )
        return None


def _warn_once(path, message, error=False):
    """Log *message* once per absolute path (never per tick/element)."""
    if path in _warned_paths:
        return
    _warned_paths.add(path)
    (logger.error if error else logger.warning)(message)


def validate_lottie_json(path):
    """Sniff *path* for a Bodymovin/Lottie document; ``(ok, reason)``.

    Cheap and dependency-free (runs before the rlottie import so authors
    learn about a wrong file even without the wheel): the JSON must parse,
    have an object root carrying all REQUIRED_LOTTIE_KEYS, a list
    ``layers`` and positive numeric ``fr``/``w``/``h``. Not a schema
    check - rlottie still owns real parsing (and its NULL-animation
    failure path is handled by the caller).
    """
    try:
        with open(path, "r", encoding="utf-8-sig") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as e:
        return False, f"is not readable JSON ({e})"
    if not isinstance(doc, dict):
        return False, "is not a Lottie/Bodymovin document (root is not an object)"
    missing = [key for key in REQUIRED_LOTTIE_KEYS if key not in doc]
    if missing:
        return False, f"is not a Lottie/Bodymovin document (missing key(s): {', '.join(missing)})"
    if not isinstance(doc.get("layers"), list):
        return False, "is not a Lottie/Bodymovin document ('layers' is not a list)"
    try:
        fr, w, h = (float(doc[key]) for key in ("fr", "w", "h"))
    except (TypeError, ValueError):
        return False, "is not a Lottie/Bodymovin document ('fr'/'w'/'h' are not numbers)"
    if fr <= 0 or w <= 0 or h <= 0:
        return False, "is not a Lottie/Bodymovin document ('fr'/'w'/'h' must be positive)"
    return True, ""


def frame_delays_ms(frame_count, fps):
    """Per-frame delays (ms) at the native fps, error-diffused.

    Frame boundaries land on ``round(i * 1000 / fps)`` so the rounding
    error never accumulates: 91 frames at 30 fps yield delays of 33/34 ms
    summing to exactly 3033 ms (``round(frame_count * 1000 / fps)``),
    keeping MediaClock's integer-ms boundaries drift-free at any fps.
    """
    delays = []
    last = 0
    for i in range(1, int(frame_count) + 1):
        boundary = round(i * 1000.0 / fps)
        delays.append(boundary - last)
        last = boundary
    return delays


def bgra_to_rgba_bottom_up(data, width, height):
    """rlottie surface -> pipeline frame: swizzle BGRA->RGBA, flip rows.

    rlottie renders premultiplied BGRA with top-down rows (verified - see
    the module docstring); the image overlay quad wants premultiplied RGBA
    with bottom-up rows. The channel swizzle preserves premultiplication.
    numpy path (ships with Blender's Python): one fancy-indexed copy.
    Pure-bytes fallback: two strided slice assignments + per-row join.
    """
    expected = width * height * 4
    if len(data) < expected:
        raise ValueError(f"frame buffer too small: {len(data)} < {expected}")
    try:
        import numpy as np

        arr = np.frombuffer(data, dtype=np.uint8)[:expected].reshape(height, width, 4)
        return arr[::-1, :, [2, 1, 0, 3]].tobytes()
    except ImportError:
        pass
    swizzled = bytearray(data[:expected])
    swizzled[0::4] = data[2:expected:4]  # R <- B
    swizzled[2::4] = data[0:expected:4]  # B <- R
    row = width * 4
    return b"".join(swizzled[y * row : (y + 1) * row] for y in range(height - 1, -1, -1))


def _block_attrs(block):
    """Normalized playback-attribute snapshot of an image block (reconcile key).

    autoplay and loop default TRUE (lottie-player parity, MEDIA_PLAN
    section 5.4) - extract_images emits explicit values for ``lottie:``
    nodes, while blocks from an ``img: *.json`` element carry no playback
    keys and land on the same defaults (autoplay + loop, GIF-like).
    """
    block = block or {}
    return (
        bool(block.get("autoplay", True)),
        bool(block.get("loop", True)),
        float(block.get("playback_rate", 1.0)),
    )


class LottieSource:
    """Per-element playback of one Lottie file onto one ImageInstance."""

    kind = "lottie"

    def __init__(self, container_id, image_name, path, instance, block=None):
        self.container_id = container_id
        self.image_name = image_name  # asset key, e.g. "confetti.json"
        self.path = os.path.abspath(path)
        self.instance = instance
        self.released = False

        self._attrs_snapshot = _block_attrs(block)
        (self.autoplay, self._loop, self._rate) = self._attrs_snapshot
        # Lottie has no audio: muted/volume are plain stored attributes so
        # container.media stays a safe no-op surface for them (the
        # controller falls back to attribute assignment when
        # set_muted/set_volume hooks are absent).
        self.muted = False
        self.volume = 1.0

        # none|ready|unsupported|error (no 'metadata' stage - a parsed
        # animation knows everything and renders frames on demand).
        self.ready_state = "none"
        self.fps = 0.0
        self.frame_count = 0
        self.intrinsic = (0, 0)  # animation canvas size (w, h)
        # Placeholder clock so the controller/manager can always read
        # paused/ended/current_time - replaced once metadata is known.
        self.clock = MediaClock(duration=0.0, loop=self._loop, playback_rate=self._rate)

        self._animation = None  # rlottie handle; None while unsupported/error
        self._texture = None
        self._frame_idx = 0
        self._static = True  # single-frame animations never activate
        self._use_cache = False  # budget verdict at the current raster size
        self._frame_cache = {}  # frame index -> GPUTexture (budget path)
        self._ring = deque(maxlen=RING_TEXTURES)  # over-budget reuse ring
        self._raster_size = (1, 1)
        self._rendered_box = (0, 0)  # content box the raster was fit for
        self._pending_box = None  # changed size waiting out the debounce
        self._pending_since = 0.0

        # 1) Validate BEFORE the dependency check: a non-Lottie .json warns
        # accurately even when the wheel is missing, and nothing unparseable
        # ever reaches rlottie (NULL-animation crash guard - docstring).
        ok, reason = validate_lottie_json(self.path)
        if not ok:
            self.ready_state = "unsupported"
            _warn_once(self.path, f"lottie: '{image_name}' {reason} - element renders nothing")
            return

        # 2) Bundled dependency (lazy-import safety net), like av in video.
        LottieAnimation = _import_rlottie()
        if LottieAnimation is None:
            self.ready_state = "unsupported"
            return

        # 3) Parse + probe + seed frame 0 (so get_display_size aspect-fits
        # correctly before the first draw, like every other decoder).
        try:
            self._animation = LottieAnimation.from_file(self.path)
            if not getattr(self._animation, "animation_p", None):
                raise ValueError("rlottie could not parse the animation")
            width, height = self._animation.lottie_animation_get_size()
            frame_count = int(self._animation.lottie_animation_get_totalframe())
            fps = float(self._animation.lottie_animation_get_framerate())
            if width <= 0 or height <= 0 or frame_count < 1 or fps <= 0:
                raise ValueError(f"degenerate animation ({width}x{height}, {frame_count} frames @ {fps} fps)")
            self.intrinsic = (int(width), int(height))
            self.frame_count = frame_count
            self.fps = fps
            self._static = frame_count <= 1
            # Native-fps clock: duration == frame_count / fps (every frame
            # gets a display slot incl. rlottie's inclusive last frame).
            self.clock = MediaClock(
                delays_ms=frame_delays_ms(frame_count, fps), loop=self._loop, playback_rate=self._rate
            )
            self._apply_box(self._box_size())
        except Exception as e:
            self._destroy_animation()
            self.ready_state = "error"
            _warn_once(self.path, f"lottie: failed to open '{image_name}' ({e})", error=True)
            return

        self.ready_state = "ready"
        logger.debug(
            f"Opened lottie {os.path.basename(self.path)}: {self.intrinsic[0]}x{self.intrinsic[1]}, "
            f"{self.frame_count} frames @ {self.fps:g} fps "
            f"({'frame cache' if self._use_cache else 'texture ring'} at {self._raster_size[0]}x{self._raster_size[1]})"
        )

        # lottie-player parity: autoplay defaults true (plan section 5.4).
        if self.autoplay and not self._static:
            self.clock.play()

    # ── attach() reconcile hook ──────────────────────────────────────

    def matches_block(self, block):
        """False when the YAML playback attrs changed (source gets rebuilt)."""
        return self._attrs_snapshot == _block_attrs(block)

    # ── internals ────────────────────────────────────────────────────

    def _box_size(self):
        """The element's live content box as ints (see SvgSource._box_size:
        instance.size mirrors the extractor's content box exactly)."""
        size = self.instance.size
        return (int(size[0]), int(size[1]))

    def _apply_box(self, box):
        """(Re)fit the raster to *box*: drop every cached frame texture,
        re-evaluate the cache budget at the new size and render the
        current frame. Used at attach and after a settled resize."""
        width, height = fit_size(self.intrinsic[0], self.intrinsic[1], box[0], box[1])
        self._raster_size = (width, height)
        self._rendered_box = box
        self._frame_cache.clear()
        self._ring.clear()
        self._use_cache = width * height * 4 * self.frame_count <= FRAME_CACHE_BUDGET_BYTES
        self._texture = self._texture_for(self._frame_idx)
        self._apply_texture()

    def _render(self, frame_idx):
        """CPU raster of one frame at the current size (premul RGBA, bottom-up)."""
        width, height = self._raster_size
        data = self._animation.lottie_animation_render(frame_num=frame_idx, width=width, height=height)
        return bgra_to_rgba_bottom_up(data, width, height)

    def _texture_for(self, frame_idx):
        """Texture for a frame: progressive per-loop cache under the budget
        (render once, reuse every later loop), reuse ring above it."""
        if self._use_cache:
            texture = self._frame_cache.get(frame_idx)
            if texture is None:
                texture = upload_texture(self._raster_size[0], self._raster_size[1], self._render(frame_idx))
                self._frame_cache[frame_idx] = texture
            return texture
        texture = upload_texture(self._raster_size[0], self._raster_size[1], self._render(frame_idx))
        self._ring.append(texture)
        return texture

    def _apply_texture(self):
        """Push the current texture onto the instance (and build its batch)."""
        instance = self.instance
        if instance is None or self._texture is None:
            return
        instance.texture = self._texture
        if instance.batch is None:
            instance._create_batch()

    def _destroy_animation(self):
        """Free the rlottie C handle (idempotent - also runs from __del__
        inside rlottie-python, but hot reload should not wait for the GC)."""
        animation = self._animation
        self._animation = None
        if animation is not None:
            try:
                animation.lottie_animation_destroy()
            except Exception:
                logger.debug("lottie animation destroy failed", exc_info=True)

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
        if self._animation is None:
            return False  # unsupported/error - inert forever, never crashes

        changed = False

        # Size-watch (mirrors SvgSource): re-render only when the content
        # box moved beyond the tolerance AND held still for the debounce.
        # Settling drops the frame caches (old-size textures) and renders
        # the current frame at the new size.
        box = self._box_size()
        if (
            abs(box[0] - self._rendered_box[0]) <= RESIZE_TOLERANCE_PX
            and abs(box[1] - self._rendered_box[1]) <= RESIZE_TOLERANCE_PX
        ):
            self._pending_box = None  # settled back onto the current raster
        elif box != self._pending_box:
            self._pending_box = box  # (re)start the debounce
            self._pending_since = now
        elif now - self._pending_since >= RESIZE_DEBOUNCE_S:
            self._apply_box(box)
            self._pending_box = None
            changed = True

        # Clock-driven frame advance at the native fps (loop/rate/seek all
        # live in MediaClock; frame_index resolves the cumulative delays).
        if not self._static and self.clock.is_active(now):
            frame_idx = self.clock.frame_index(now)
            if frame_idx != self._frame_idx:
                self._frame_idx = frame_idx
                self._texture = self._texture_for(frame_idx)
                changed = True

        # Self-heal: scroll/dirty-sync/hot-reload paths call
        # instance.update_all(image_name=...), which resets the texture to
        # the ImageManager stub (None for media formats). Identity check is
        # cheap and keeps paused lotties visible through those paths.
        if instance.texture is not self._texture:
            self._apply_texture()
            changed = True
        return changed

    def is_active(self, now=None):
        """True while playback (or a pending resize re-render) can change
        the visible frame - gates redraws via MediaManager.has_active()."""
        if self.released or self.instance is None or self._animation is None:
            return False
        if self._pending_box is not None:
            return True
        return not self._static and self.clock.is_active(now)

    def release(self):
        """Detach, free the rlottie handle and drop per-element GPU refs
        (idempotent). Called by MediaManager.shutdown() and attach-reconcile."""
        self.released = True
        try:
            self.clock.pause()
        except Exception:  # pragma: no cover - MediaClock never raises
            pass
        self._destroy_animation()
        self._frame_cache.clear()
        self._ring.clear()
        self._texture = None
        self._pending_box = None
        self.instance = None

    # ── container.media wiring (duck-typed by MediaController) ───────
    # loop/playback_rate ride the clock via the controller fallbacks;
    # muted/volume are the inert attributes above. play/seek/stop get
    # hooks so replay parity and paused repaints work like video/gif.

    @property
    def duration(self):
        """Duration in seconds (frame_count / fps), or None until known."""
        d = self.clock.duration
        return d if d > 0.0 else None

    def play(self):
        """Start/resume; play() after ended replays from 0 (HTML parity -
        MediaClock.play() alone no-ops on a never-paused ended clock)."""
        if self.released or self._animation is None:
            if not self.released:
                # Inert guarantee: an unsupported/errored source never starts
                # its clock (no timeupdate/play events can ever fire).
                logger.debug(f"lottie '{self.image_name}': play() ignored - source is {self.ready_state}")
            return
        if self.clock.ended:
            self.seek(0.0)
        self.clock.play()

    def pause(self):
        self.clock.pause()

    def seek(self, seconds):
        """Seek the clock and swap the visible frame at once (paused too -
        tick only advances frames on an active clock). Mirrors GifSource."""
        self.clock.seek(seconds)
        if self.released or self.instance is None or self._animation is None or self._static:
            return
        frame_idx = self.clock.frame_index()
        if frame_idx != self._frame_idx:
            self._frame_idx = frame_idx
            self._texture = self._texture_for(frame_idx)
            self._apply_texture()

    def stop(self):
        """Pause and rewind to frame 0 (repaints even while paused)."""
        if self.released:
            return
        self.clock.pause()
        self.seek(0.0)
