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
"""Media playback clock - a monotonic-time playback state machine.

Pure Python, no bpy/gpu imports: unit-testable outside Blender.
Mirrors HTMLMediaElement semantics where they make sense for Puree:
``play()`` after ``ended`` restarts from 0, ``seek()`` clamps to the
duration, ``loop`` may be a bool (HTML) or a play count (GIF Netscape
extension, where 0 means loop forever).
"""

import time
from bisect import bisect_right

__all__ = ["MediaClock", "cumulative_delays", "frame_index_at"]


def cumulative_delays(delays_ms):
    """Exclusive-end frame boundaries (ms) from per-frame delays.

    ``[100, 50, 200]`` -> ``[100, 150, 350]``: frame i is displayed for
    ``boundaries[i-1] <= t_ms < boundaries[i]``.
    """
    boundaries = []
    acc = 0
    for d in delays_ms:
        acc += max(0, int(d))
        boundaries.append(acc)
    return boundaries


def frame_index_at(time_ms, boundaries):
    """Frame index for a media time (ms) against cumulative boundaries."""
    if not boundaries:
        return 0
    return min(bisect_right(boundaries, time_ms), len(boundaries) - 1)


class MediaClock:
    """Playback state machine driven by a monotonic clock.

    Parameters
    ----------
    delays_ms:
        Per-frame delays in milliseconds (animated sources). ``duration``
        derives from their sum unless given explicitly.
    duration:
        Media duration in seconds (overrides the delays sum).
    loop:
        ``True`` -> loop forever, ``False`` -> play once, int ``n > 0`` ->
        play n times total, int ``0`` -> loop forever (GIF loop_count
        convention).
    playback_rate:
        Playback speed multiplier (>= 0). Default 1.0.
    time_fn:
        Time source, defaults to ``time.monotonic`` (injectable in tests).

    The clock starts paused at t=0; call ``play()``.
    """

    def __init__(self, delays_ms=None, duration=None, loop=True, playback_rate=1.0, time_fn=None):
        self._boundaries = cumulative_delays(delays_ms or [])
        if duration is None:
            duration = self._boundaries[-1] / 1000.0 if self._boundaries else 0.0
        self._duration = max(0.0, float(duration))
        self.loop = loop
        self._rate = max(0.0, float(playback_rate))
        self._time = time_fn or time.monotonic
        self._accum = 0.0  # unwrapped media-seconds accumulated up to the last state change
        self._started_at = None  # monotonic timestamp while playing, None while paused

    # ── internals ────────────────────────────────────────────────────

    @property
    def _plays_allowed(self):
        """None for infinite looping, else the total play count (>= 1)."""
        if self.loop is True:
            return None
        if self.loop is False:
            return 1
        n = int(self.loop)
        return None if n <= 0 else n

    def _now(self, now):
        return self._time() if now is None else now

    def _elapsed(self, now=None):
        """Unwrapped media-seconds played since the start (never wraps)."""
        if self._started_at is None:
            return self._accum
        return self._accum + max(0.0, self._now(now) - self._started_at) * self._rate

    def _is_ended(self, now=None):
        if self._duration <= 0.0:
            return False
        allowed = self._plays_allowed
        if allowed is None:
            return False
        return self._elapsed(now) >= self._duration * allowed

    def _time_in_media(self, now=None):
        if self._duration <= 0.0:
            return 0.0
        if self._is_ended(now):
            return self._duration
        return self._elapsed(now) % self._duration

    # ── state ────────────────────────────────────────────────────────

    @property
    def duration(self):
        return self._duration

    @property
    def paused(self):
        return self._started_at is None

    @property
    def playing(self):
        return self._started_at is not None

    @property
    def ended(self):
        return self._is_ended()

    @property
    def current_time(self):
        return self._time_in_media()

    @property
    def playback_rate(self):
        return self._rate

    @playback_rate.setter
    def playback_rate(self, rate):
        # Fold elapsed time at the old rate so past playback is preserved.
        now = self._time()
        self._accum = self._elapsed(now)
        if self._started_at is not None:
            self._started_at = now
        self._rate = max(0.0, float(rate))

    # ── controls ─────────────────────────────────────────────────────

    def play(self, now=None):
        now = self._now(now)
        if self._started_at is not None:
            return
        if self._is_ended(now):
            # HTMLMediaElement: play() on an ended element restarts from 0.
            self._accum = 0.0
        self._started_at = now

    def pause(self, now=None):
        if self._started_at is None:
            return
        now = self._now(now)
        self._accum = self._elapsed(now)
        self._started_at = None

    def toggle(self, now=None):
        if self._started_at is None:
            self.play(now)
        else:
            self.pause(now)

    def seek(self, seconds, now=None):
        """Seek within the current loop iteration (seconds clamp to [0, duration])."""
        if self._duration <= 0.0:
            return
        now = self._now(now)
        t = min(max(0.0, float(seconds)), self._duration)
        iteration = int(self._elapsed(now) // self._duration)
        allowed = self._plays_allowed
        if allowed is not None:
            # Seeking after the end lands in the LAST allowed iteration, so
            # ended clears until playback reaches the end again (HTML parity).
            iteration = min(iteration, allowed - 1)
        self._accum = iteration * self._duration + t
        if self._started_at is not None:
            self._started_at = now

    # ── frame resolution ─────────────────────────────────────────────

    @property
    def frame_count(self):
        return len(self._boundaries)

    def frame_index(self, now=None):
        """Current frame index resolved from the cumulative delays."""
        if not self._boundaries:
            return 0
        if self._is_ended(now):
            return len(self._boundaries) - 1
        return frame_index_at(self._time_in_media(now) * 1000.0, self._boundaries)

    def is_active(self, now=None):
        """True while playback can change the visible frame (gates redraws)."""
        return self._started_at is not None and self._duration > 0.0 and not self._is_ended(now)
