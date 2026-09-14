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
"""Shared GPU texture upload for media decoders.

Blender's ``gpu`` module has no ``texture.write()`` - every new frame is a
fresh ``Buffer`` + ``GPUTexture`` pair (MEDIA_PLAN.md section 3). Which
buffer/texture format combination ``GPUTexture`` accepts varies per
Blender build:

- most builds take ``Buffer('UBYTE', ...)`` directly - the cheap path,
  frame bytes pass through untouched;
- some builds reject UBYTE data outright ("GPUTexture.__new__: Only
  Buffer of format 'FLOAT' is currently supported" - observed live) and
  need the frame converted to normalized float32 first (numpy, which
  ships with Blender's Python; without numpy the FLOAT path is unusable -
  a pure-Python per-byte conversion would be fine for icons but
  unacceptable for video-sized frames - so upload raises after ONE
  warning and MediaManager's per-source error handling degrades that
  element);
- ``SRGB8_A8`` (hardware sRGB->linear on sample, matching how
  ``bpy.data.images`` textures behave) is preferred over plain ``RGBA8``.

The working ``(buffer_format, texture_format)`` combo is probed ONCE per
session with a throwaway 2x2 texture, cheapest first:

    ('UBYTE', 'SRGB8_A8') -> ('UBYTE', 'RGBA8')
        -> ('FLOAT', 'SRGB8_A8') -> ('FLOAT', 'RGBA8')

and the winner is logged once at INFO - it matters when debugging
color-space differences between machines. Every decoder (gif, svg,
video, lottie) uploads through here so the choice is made exactly once.

The ``gpu`` import lives inside the functions so this module imports
cleanly outside Blender (headless unit tests stub it per call).
"""

try:
    from ..log import get_logger

    logger = get_logger(__name__)
except Exception:  # pragma: no cover - outside the package/Blender
    import logging

    logger = logging.getLogger(__name__)

__all__ = ["upload_texture", "get_texture_format", "get_upload_combo", "UPLOAD_COMBOS"]

# Probe order: cheapest buffer kind first (UBYTE = zero-conversion bytes),
# sRGB before linear within each kind (color parity with bpy.data.images).
UPLOAD_COMBOS = (
    ("UBYTE", "SRGB8_A8"),
    ("UBYTE", "RGBA8"),
    ("FLOAT", "SRGB8_A8"),
    ("FLOAT", "RGBA8"),
)

# Chosen at the first upload: (buffer_format, texture_format).
_upload_combo = None
_warned_no_numpy = False  # FLOAT path needs numpy - warn once per session


def _float_payload(frame_bytes, count):
    """Premultiplied RGBA8 bytes -> normalized float32 array (numpy).

    One `astype` copy, normalized in place - no other allocations. numpy
    ships with Blender's Python; when it is missing the FLOAT path cannot
    work (pure Python is unacceptable for video-sized frames), so this
    raises after one session-wide warning and the caller's per-source
    error handling (MediaManager.attach/tick) degrades that element.
    """
    global _warned_no_numpy
    try:
        import numpy as np
    except ImportError:
        if not _warned_no_numpy:
            _warned_no_numpy = True
            logger.warning(
                "this Blender build needs FLOAT GPU buffers and numpy is "
                "unavailable - media elements cannot upload frames and will "
                "not render"
            )
        raise
    payload = np.frombuffer(frame_bytes, dtype=np.uint8, count=count).astype(np.float32)
    payload /= 255.0  # in place - astype() above already copied
    return payload


def _make_buffer(gpu, buffer_format, size, frame_bytes):
    """One frame as a gpu.types.Buffer in the requested buffer format."""
    if buffer_format == "UBYTE":
        return gpu.types.Buffer("UBYTE", size, frame_bytes)
    return gpu.types.Buffer("FLOAT", size, _float_payload(frame_bytes, size))


def _probe_combo(gpu):
    """First (buffer_format, texture_format) combo this build accepts.

    Constructs a throwaway 2x2 test texture per candidate; failures are
    logged at DEBUG, the winner once at INFO (SRGB8_A8 samples through the
    hardware sRGB->linear conversion, RGBA8 does not - the combo choice is
    the first thing to check when colors differ between machines).
    """
    test_bytes = bytes(16)  # 2x2 premultiplied RGBA8, fully transparent
    last_error = None
    for buffer_format, texture_format in UPLOAD_COMBOS:
        try:
            buf = _make_buffer(gpu, buffer_format, 16, test_bytes)
            gpu.types.GPUTexture((2, 2), format=texture_format, data=buf)
        except Exception as e:
            last_error = e
            logger.debug(f"media upload combo {buffer_format}/{texture_format} unavailable: {e}")
            continue
        logger.info(f"media upload path: Buffer('{buffer_format}') -> GPUTexture('{texture_format}')")
        return buffer_format, texture_format
    raise RuntimeError(f"no usable GPU texture upload path on this build (last error: {last_error})")


def upload_texture(width, height, frame_bytes):
    """Upload one premultiplied RGBA8 frame (bottom-up rows) as a GPUTexture.

    Main-thread only - Blender's gpu API is not thread-safe.
    """
    global _upload_combo

    import gpu

    if _upload_combo is None:
        _upload_combo = _probe_combo(gpu)
    buffer_format, texture_format = _upload_combo
    buf = _make_buffer(gpu, buffer_format, width * height * 4, frame_bytes)
    return gpu.types.GPUTexture((width, height), format=texture_format, data=buf)


def get_upload_combo():
    """The probed (buffer_format, texture_format) pair (None until the first upload)."""
    return _upload_combo


def get_texture_format():
    """The GPUTexture format in use (None until the first upload)."""
    return _upload_combo[1] if _upload_combo else None
