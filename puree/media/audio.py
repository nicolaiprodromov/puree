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
"""AudioTrack - video audio playback over Blender's built-in ``aud`` module.

``aud`` (audaspace, FFmpeg-backed) ships with Blender and only exists
inside it, so it is imported lazily inside functions - never at module
import time. Outside Blender (headless tests) or when anything aud-side
fails, an AudioTrack degrades to an inert no-op (``available == False``)
with at most ONE logged warning per track: callers (VideoSource's sync
loop) can call every method unconditionally and never crash a tick.

aud facts this module relies on (verified against the Blender Python API
docs, https://docs.blender.org/api/current/aud.html):

- ``aud.Sound(filename)`` loads any FFmpeg-readable file, including
  video containers (the audio stream is what plays). Construction and
  playback raise ``aud.error`` on unsupported/broken containers.
- ``aud.Device()`` opens a NEW OS audio output each call - hence the
  module-level lazy singleton below (one device per Blender session,
  shared by every AudioTrack; never create devices per play).
- ``device.play(sound, keep=False) -> aud.Handle`` starts playback at
  position 0 immediately; with ``keep=False`` the handle auto-stops at
  the sound's natural end (``status`` becomes ``STATUS_STOPPED``).
- ``handle.position`` is the playback position in seconds, float,
  READ/WRITE (writing seeks) - the master-clock sync loop reads it.
- ``handle.volume`` is the per-handle volume (0..1 range used here).
- ``handle.pause()`` / ``handle.resume()`` keep the handle alive;
  ``handle.stop()`` INVALIDATES the handle (docs warning) - after a
  stop, playing again requires a fresh ``device.play()``.
- ``handle.status`` is one of STATUS_INVALID=0 / STATUS_PLAYING=1 /
  STATUS_PAUSED=2 / STATUS_STOPPED=3 (mirrored as module constants so
  status checks never need the aud import).
- ``device.lock()`` / ``device.unlock()`` make play+seek+volume atomic,
  so starting "at position t" never leaks audible samples from 0.
- ``sound.length`` reports the sound duration (float; may require a
  demux probe). Read defensively and used for logging only - playback
  logic keys off handle status/position instead.
"""

try:
    from ..log import get_logger

    logger = get_logger(__name__)
except Exception:  # pragma: no cover - outside the package/Blender
    import logging

    logger = logging.getLogger(__name__)

__all__ = ["AudioTrack"]

# aud.Handle.status values (aud module constants, mirrored so status
# checks work without importing aud - see module docstring).
STATUS_INVALID = 0
STATUS_PLAYING = 1
STATUS_PAUSED = 2
STATUS_STOPPED = 3

# One aud.Device per session, created lazily on first use. aud.Device()
# opens a fresh OS audio output every call - creating one per play/track
# would exhaust backends and glitch audio. The device lives until the
# module is reloaded (addon reinstall); UI stop/hot reload only stop the
# per-track handles, which is all audaspace needs.
_device = None
_device_failed = False  # aud importable but no usable output - warned once


def _shared_device():
    """The session-wide aud.Device, or None (outside Blender / no output)."""
    global _device, _device_failed
    if _device is not None:
        return _device
    if _device_failed:
        return None
    try:
        import aud
    except ImportError:
        _device_failed = True
        # Normal outside Blender (headless tests, CLI) - not a warning.
        logger.debug("aud module unavailable (outside Blender) - video audio disabled")
        return None
    try:
        _device = aud.Device()
    except Exception as e:
        _device_failed = True
        logger.warning(f"audio output unavailable - video audio disabled: {e}")
        return None
    return _device


class AudioTrack:
    """Playback of one file's audio stream through the shared aud device.

    Designed for VideoSource's sync loop: every method is safe to call in
    any state; any aud exception degrades the track to inert
    (``available == False``) with one logged warning. ``position`` returns
    None whenever there is no live handle (never started, stopped, or the
    stream reached its natural end), which the sync loop reads as "no
    master this tick".
    """

    __slots__ = (
        "label",
        "path",
        "available",
        "duration",
        "_sound",
        "_handle",
        "_volume",
        "_paused_position",
        "_warned",
    )

    def __init__(self, label=""):
        self.label = label or "audio"
        self.path = None
        self.available = False  # True only between a successful open() and release()/failure
        self.duration = None  # sound.length, informational only (see module docstring)
        self._sound = None
        self._handle = None
        self._volume = 1.0
        self._paused_position = None  # remembered by pause() for resume()'s dead-handle fallback
        self._warned = False

    # ── failure handling ─────────────────────────────────────────────

    def _fail(self, action, exc):
        """Degrade to inert with ONE warning per track (never crash a tick)."""
        if not self._warned:
            self._warned = True
            logger.warning(f"audio disabled for '{self.label}' - {action} failed: {exc}")
        self.available = False
        handle, self._handle = self._handle, None
        if handle is not None:
            try:
                handle.stop()
            except Exception:
                pass

    # ── lifecycle ────────────────────────────────────────────────────

    def open(self, path):
        """Probe *path* for playability; True when audio is available.

        Creates the aud.Sound (aud raises here on unsupported containers).
        ``sound.length`` is read defensively - a missing length is not a
        failure, ``play()`` remains the real gate.
        """
        device = _shared_device()
        if device is None:
            return False
        try:
            import aud

            self._sound = aud.Sound(str(path))
        except Exception as e:
            self._fail("open", e)
            return False
        self.path = str(path)
        try:
            self.duration = float(self._sound.length)
        except Exception:
            self.duration = None
        self.available = True
        return True

    def release(self):
        """Stop playback and drop the sound (idempotent, terminal)."""
        self.stop()
        self._sound = None
        self.available = False

    # ── playback ─────────────────────────────────────────────────────

    def play(self, from_seconds=0.0):
        """Start playback at *from_seconds* on a FRESH handle.

        Any existing handle is stopped first (aud handles are invalid
        after stop - see module docstring), then play+seek+volume run
        under ``device.lock()`` so no samples from position 0 are audible.
        Returns True when the handle is live.
        """
        if not self.available or self._sound is None:
            return False
        device = _shared_device()
        if device is None:
            return False
        self.stop()
        handle = None
        try:
            locked = False
            try:
                device.lock()
                locked = True
            except Exception:
                locked = False  # lock is glitch-prevention, not correctness
            try:
                handle = device.play(self._sound)
                position = max(0.0, float(from_seconds))
                if position > 0.0:
                    handle.position = position
                handle.volume = self._volume
            finally:
                if locked:
                    try:
                        device.unlock()
                    except Exception:
                        pass
            self._handle = handle
            self._paused_position = None
            return True
        except Exception as e:
            if handle is not None:
                try:
                    handle.stop()
                except Exception:
                    pass
            self._fail("play", e)
            return False

    def pause(self):
        """Pause the live handle (kept alive - handle.pause(), not stop()),
        remembering its position for resume()'s dead-handle fallback."""
        handle = self._handle
        if handle is None or not self.available:
            return
        try:
            if handle.status == STATUS_PLAYING:
                self._paused_position = float(handle.position)
                handle.pause()
        except Exception as e:
            self._fail("pause", e)

    def resume(self):
        """Resume a paused handle; a dead/stopped handle falls back to a
        fresh play() at the remembered pause position."""
        if not self.available:
            return
        handle = self._handle
        if handle is not None:
            try:
                if handle.status == STATUS_PAUSED and handle.resume():
                    self._paused_position = None
                    return
            except Exception as e:
                self._fail("resume", e)
                return
        if self._paused_position is not None:
            self.play(self._paused_position)

    def stop(self):
        """Stop and drop the handle (idempotent; stopping an already-dead
        handle is not an error and never flips ``available``)."""
        handle, self._handle = self._handle, None
        self._paused_position = None
        if handle is None:
            return
        try:
            handle.stop()
        except Exception:
            pass

    def seek(self, seconds):
        """Reposition the LIVE handle (playing or paused). Without one this
        is a no-op - the owner decides whether to start via play(t)."""
        handle = self._handle
        if handle is None or not self.available:
            return
        try:
            position = max(0.0, float(seconds))
            handle.position = position
            if self._paused_position is not None:
                self._paused_position = position
        except Exception as e:
            self._fail("seek", e)

    # ── state ────────────────────────────────────────────────────────

    def _status(self):
        handle = self._handle
        if handle is None:
            return None
        try:
            return handle.status
        except Exception as e:
            self._fail("status", e)
            return None

    @property
    def playing(self):
        """True while the handle is actively playing. Handles that stopped
        on their own (natural end of the audio stream) are dropped here."""
        status = self._status()
        if status == STATUS_PLAYING:
            return True
        if status in (STATUS_STOPPED, STATUS_INVALID):
            self._handle = None
        return False

    @property
    def paused(self):
        return self._status() == STATUS_PAUSED

    @property
    def position(self):
        """Playback position in seconds (handle.position), or None when no
        live handle exists - the sync loop's "no master this tick" signal."""
        handle = self._handle
        if handle is None or not self.available:
            return None
        try:
            status = handle.status
            if status not in (STATUS_PLAYING, STATUS_PAUSED):
                self._handle = None  # stopped at the stream's natural end
                return None
            return float(handle.position)
        except Exception as e:
            self._fail("position", e)
            return None

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value):
        """Store (clamped 0..1) and push onto the live handle immediately."""
        try:
            v = min(1.0, max(0.0, float(value)))
        except (TypeError, ValueError):
            return
        self._volume = v
        handle = self._handle
        if handle is None or not self.available:
            return
        try:
            handle.volume = v
        except Exception as e:
            self._fail("volume", e)
