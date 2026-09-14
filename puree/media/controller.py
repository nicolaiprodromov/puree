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
"""``container.media`` controller - the public media playback API.

Pythonic names, HTMLMediaElement semantics (MEDIA_PLAN section 6.3).
One controller per media container id, obtained through
``MediaManager.controller_for()`` (which ``Container.media`` wraps). The
controller never holds the source directly - it re-resolves it through
the manager on every access, so it works before ``attach()`` has run
(scripts execute first: control calls no-op with a debug log, property
reads return safe defaults) and survives hot reloads where the source is
rebuilt underneath.

Works for every media kind. Sources only need a ``clock`` (MediaClock);
everything else is optional and duck-typed: ``play/pause/seek/stop``,
``set_muted/set_volume/set_playback_rate/set_loop``, ``ready_state``,
``duration``, ``seeking``. VideoSource implements all of them - its
``set_muted``/``set_volume``/``set_playback_rate`` hooks drive live audio
(aud) on files with an audio stream, with ``playback_rate != 1.0``
force-muting audio (MEDIA_PLAN decision 4, v1). GifSource ships the
minimal set (``seek`` + ``ready_state``) and falls back to its clock for
the rest - ``muted``/``volume`` are stored as plain attributes there and
are inert (GIFs have no audio).

Events - fired on the main thread from ``MediaManager.tick()`` -> ``_pump``:

- ``play`` / ``pause``: edge-detected on ``clock.paused``.
- ``ended``: edge-detected on ``clock.ended`` (loops never end).
- ``seeked``: after a ``seek()`` through THIS controller completes
  (video: once the post-seek frame is displayed). Source-level seeks do
  not fire it - documented gap.
- ``timeupdate``: while playing, throttled to ~250 ms (browser parity).
- ``error``: edge into ``ready_state == 'error'``.
- ``fullscreenchange``: NOT edge-detected here - pushed by
  ``puree.fullscreen`` when this container enters/leaves fullscreen
  (button, ESC, scripts, swaps, force-exits). The container's
  ``on_fullscreen_change`` list fires FIRST, then this media alias; read
  ``container.fullscreen`` (or ``fullscreen_manager.active_id``) for the
  new state.

Listeners receive the controller: ``fn(media)``. A replay via ``play()``
on an already-ended-but-never-paused clock does not re-fire ``play``
(no ``paused`` edge) - documented gap, matches the state machine.
"""

import time

try:
    from ..log import get_logger

    logger = get_logger(__name__)
except Exception:  # pragma: no cover - outside the package/Blender
    import logging

    logger = logging.getLogger(__name__)

__all__ = ["MediaController", "MEDIA_EVENTS", "TIMEUPDATE_INTERVAL"]

MEDIA_EVENTS = ("play", "pause", "ended", "seeked", "timeupdate", "error", "fullscreenchange")
TIMEUPDATE_INTERVAL = 0.25  # seconds - browser-like throttle


class MediaController:
    """HTMLMediaElement-flavored playback controller for one container."""

    def __init__(self, container_id, manager):
        self.container_id = container_id
        self._manager = manager
        self._listeners = {}
        self._seek_pending = False
        self._last_timeupdate = 0.0
        # Baselines from the current source state, so subscribing to an
        # already-playing source never fires a spurious initial event.
        # A LIVE but clock-less source (static media - SVG) has no playback
        # surface: raise the same actionable message Container.__getattr__
        # surfaces for `.media`, instead of an accidental AttributeError
        # from a bare `source.clock` access.
        source = manager.get_source(container_id)
        clock = getattr(source, "clock", None)
        if source is not None and clock is None:
            raise AttributeError(
                f"container '{container_id}' has no media source - set img: (gif) / video: / lottie: in YAML"
            )
        self._was_paused = clock.paused if clock is not None else True
        self._was_ended = clock.ended if clock is not None else False
        self._last_ready_state = getattr(source, "ready_state", "none") if source is not None else "none"

    # ── source resolution ────────────────────────────────────────────

    @property
    def _source(self):
        return self._manager.get_source(self.container_id)

    def _require_source(self, action):
        source = self._source
        if source is None:
            logger.debug(f"media.{action}(): no media source for '{self.container_id}' (before attach, or removed)")
        return source

    # ── controls ─────────────────────────────────────────────────────

    def play(self):
        source = self._require_source("play")
        if source is None:
            return
        if hasattr(source, "play"):
            source.play()
        else:
            clock = source.clock
            if clock.ended:
                clock.seek(0.0)  # replay from the head (HTML parity)
            clock.play()

    def pause(self):
        source = self._require_source("pause")
        if source is None:
            return
        if hasattr(source, "pause"):
            source.pause()
        else:
            source.clock.pause()

    def toggle(self):
        if self.paused:
            self.play()
        else:
            self.pause()

    def seek(self, seconds):
        source = self._require_source("seek")
        if source is None:
            return
        if hasattr(source, "seek"):
            source.seek(seconds)
        else:
            source.clock.seek(seconds)
        self._seek_pending = True

    def stop(self):
        """Pause and rewind to 0 (not an HTML method - Puree convenience)."""
        source = self._require_source("stop")
        if source is None:
            return
        if hasattr(source, "stop"):
            source.stop()
        else:
            source.clock.pause()
            source.clock.seek(0.0)

    # ── state properties ─────────────────────────────────────────────

    @property
    def current_time(self):
        source = self._source
        return source.clock.current_time if source is not None else 0.0

    @property
    def duration(self):
        """Duration in seconds; None until metadata is known."""
        source = self._source
        if source is None:
            return None
        if hasattr(source, "duration"):
            return source.duration
        d = source.clock.duration
        return d if d > 0.0 else None

    @property
    def paused(self):
        source = self._source
        return source.clock.paused if source is not None else True

    @property
    def ended(self):
        source = self._source
        return source.clock.ended if source is not None else False

    @property
    def loop(self):
        """bool for video; GIFs may report their Netscape play count (int)."""
        source = self._source
        return source.clock.loop if source is not None else False

    @loop.setter
    def loop(self, value):
        source = self._require_source("loop")
        if source is None:
            return
        if hasattr(source, "set_loop"):
            source.set_loop(value)
        else:
            source.clock.loop = value

    @property
    def muted(self):
        """Live on sources with audio (video); a plain stored flag elsewhere."""
        source = self._source
        return bool(getattr(source, "muted", False)) if source is not None else False

    @muted.setter
    def muted(self, value):
        source = self._require_source("muted")
        if source is None:
            return
        if hasattr(source, "set_muted"):
            source.set_muted(value)
        else:
            source.muted = bool(value)

    @property
    def volume(self):
        """Live on sources with audio (video, 0..1); stored-only elsewhere."""
        source = self._source
        return float(getattr(source, "volume", 1.0)) if source is not None else 1.0

    @volume.setter
    def volume(self, value):
        source = self._require_source("volume")
        if source is None:
            return
        if hasattr(source, "set_volume"):
            source.set_volume(value)
        else:
            try:
                source.volume = min(1.0, max(0.0, float(value)))
            except (TypeError, ValueError):
                pass

    @property
    def playback_rate(self):
        source = self._source
        return source.clock.playback_rate if source is not None else 1.0

    @playback_rate.setter
    def playback_rate(self, value):
        # On video sources a rate != 1.0 force-mutes audio until the rate
        # returns to 1.0 (MEDIA_PLAN decision 4, v1 limitation).
        source = self._require_source("playback_rate")
        if source is None:
            return
        if hasattr(source, "set_playback_rate"):
            source.set_playback_rate(value)
        else:
            source.clock.playback_rate = value

    @property
    def ready_state(self):
        """'none'|'metadata'|'ready'|'unsupported'|'error'."""
        source = self._source
        if source is None:
            return "none"
        return getattr(source, "ready_state", "ready")

    # ── events ───────────────────────────────────────────────────────

    def on(self, event, fn):
        """Subscribe *fn* to *event*; returns *fn* (handy for off())."""
        if event not in MEDIA_EVENTS:
            raise ValueError(f"unknown media event '{event}' - one of {', '.join(MEDIA_EVENTS)}")
        self._listeners.setdefault(event, []).append(fn)
        return fn

    def off(self, event, fn):
        """Unsubscribe *fn* from *event* (no-op when not subscribed)."""
        listeners = self._listeners.get(event)
        if listeners is not None:
            try:
                listeners.remove(fn)
            except ValueError:
                pass

    def has_listeners(self):
        return any(self._listeners.values())

    def _emit(self, event):
        for fn in list(self._listeners.get(event, ())):
            try:
                fn(self)
            except Exception:
                logger.error(f"media '{event}' listener failed for '{self.container_id}'", exc_info=True)

    def _pump(self, now=None):
        """Edge-detect state and fire events (main thread, MediaManager.tick)."""
        source = self._source
        if source is None:
            return
        clock = getattr(source, "clock", None)
        if clock is None:
            # Clock-less source (static media - SVG): nothing to edge-detect.
            # Only reachable by a controller created PRE-attach whose id later
            # resolved to a static source - attach() prunes those; this guard
            # is the belt to that suspenders (never a per-tick error).
            return
        if now is None:
            now = time.monotonic()
        paused = clock.paused
        ended = clock.ended
        state = getattr(source, "ready_state", "ready")

        if paused != self._was_paused:
            self._was_paused = paused
            self._emit("pause" if paused else "play")
        if ended and not self._was_ended:
            self._emit("ended")
        self._was_ended = ended
        if state == "error" and self._last_ready_state != "error":
            self._emit("error")
        self._last_ready_state = state
        if self._seek_pending and not getattr(source, "seeking", False):
            self._seek_pending = False
            self._emit("seeked")
        if not paused and not ended and (now - self._last_timeupdate) >= TIMEUPDATE_INTERVAL:
            self._last_timeupdate = now
            self._emit("timeupdate")
