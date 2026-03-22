# Puree CSS Transition Manager
# Interpolates property values over time for smooth transitions.

import time
import math

def _ease(t):
    """CSS 'ease' timing: cubic-bezier(0.25, 0.1, 0.25, 1.0)"""
    return t * t * (3.0 - 2.0 * t)

def _ease_in(t):
    return t * t * t

def _ease_out(t):
    t1 = 1.0 - t
    return 1.0 - t1 * t1 * t1

def _ease_in_out(t):
    if t < 0.5:
        return 4.0 * t * t * t
    t1 = -2.0 * t + 2.0
    return 1.0 - t1 * t1 * t1 / 2.0

TIMING_FUNCTIONS = {
    'ease': _ease,
    'linear': lambda t: t,
    'ease-in': _ease_in,
    'ease-out': _ease_out,
    'ease-in-out': _ease_in_out,
}


def lerp_color(a, b, t):
    """Linearly interpolate between two RGBA color lists."""
    return [a[i] + (b[i] - a[i]) * t for i in range(min(len(a), len(b)))]


def lerp_float(a, b, t):
    return a + (b - a) * t


class ActiveTransition:
    __slots__ = ('start_value', 'end_value', 'start_time', 'duration', 'delay', 'timing_fn')

    def __init__(self, start_value, end_value, duration, delay, timing_fn):
        self.start_value = start_value
        self.end_value = end_value
        self.start_time = time.monotonic()
        self.duration = duration
        self.delay = delay
        self.timing_fn = timing_fn

    def progress(self, now=None):
        """Return interpolation progress [0.0, 1.0]. Returns > 1.0 when done."""
        if now is None:
            now = time.monotonic()
        elapsed = now - self.start_time - self.delay
        if elapsed < 0:
            return 0.0
        if self.duration <= 0:
            return 1.0
        return min(elapsed / self.duration, 1.0)

    def current_value(self, now=None):
        t = self.progress(now)
        t = self.timing_fn(t)
        if isinstance(self.start_value, list):
            return lerp_color(self.start_value, self.end_value, t)
        elif isinstance(self.start_value, (int, float)):
            return lerp_float(float(self.start_value), float(self.end_value), t)
        # Non-interpolable — snap at 50%
        return self.end_value if t >= 0.5 else self.start_value

    def is_done(self, now=None):
        return self.progress(now) >= 1.0


class TransitionManager:
    """Manages CSS transitions for containers."""

    def __init__(self):
        # Key: (container_id, property_name) → ActiveTransition
        self._active = {}

    def start_transition(self, container_id, prop_name, old_value, new_value, duration, delay=0.0, timing='ease'):
        """Start a transition from old_value to new_value."""
        if duration <= 0:
            return
        if old_value == new_value:
            return
        key = (container_id, prop_name)
        timing_fn = TIMING_FUNCTIONS.get(timing, _ease)
        # If already transitioning this property, use current interpolated value as start
        if key in self._active and not self._active[key].is_done():
            old_value = self._active[key].current_value()
        self._active[key] = ActiveTransition(old_value, new_value, duration, delay, timing_fn)

    def get_value(self, container_id, prop_name):
        """Get current interpolated value, or None if no active transition."""
        key = (container_id, prop_name)
        t = self._active.get(key)
        if t is None:
            return None
        if t.is_done():
            del self._active[key]
            return None
        return t.current_value()

    def has_active(self):
        """Return True if any transitions are active."""
        now = time.monotonic()
        # Clean up finished
        done = [k for k, t in self._active.items() if t.is_done(now)]
        for k in done:
            del self._active[k]
        return len(self._active) > 0

    def clear(self):
        self._active.clear()
