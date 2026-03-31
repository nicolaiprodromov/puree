"""
puree.timers — Built-in timer/interval API with auto-cleanup.

Usage:
    from puree.timers import set_interval, set_timeout, clear

    poll_handle    = set_interval(check_server_health, 5000)   # every 5 s
    timeout_handle = set_timeout(hide_notification, 3000)      # after 3 s
    clear(poll_handle)                                          # cancel early

All timers are auto-cancelled on addon unregister / hot reload via
_cleanup_all(), which is called from puree.__init__.unregister().
"""

import uuid
from typing import Callable, Dict, Optional

from .log import get_logger

logger = get_logger(__name__)

_registry: Dict[str, "TimerHandle"] = {}


class TimerHandle:
    """Opaque handle returned by set_interval / set_timeout."""

    def __init__(self, handle_id: str) -> None:
        self.id: str = handle_id
        self.cancelled: bool = False

    def cancel(self) -> None:
        """Cancel this timer.  Safe to call multiple times."""
        if not self.cancelled:
            self.cancelled = True
            _registry.pop(self.id, None)
            logger.debug("TimerHandle %s cancelled", self.id)

    def __repr__(self) -> str:
        return f"<TimerHandle id={self.id} cancelled={self.cancelled}>"


def _generate_handle_id() -> str:
    return str(uuid.uuid4())[:8]


def _register_handle(handle: TimerHandle) -> None:
    _registry[handle.id] = handle


def set_interval(fn: Callable, interval_ms: float) -> TimerHandle:
    """
    Call *fn* repeatedly every *interval_ms* milliseconds.

    Returns a :class:`TimerHandle` that can be passed to :func:`clear` to
    stop the timer before the next scheduled invocation.
    """
    import bpy

    interval_s = interval_ms / 1000.0
    handle = TimerHandle(_generate_handle_id())
    _register_handle(handle)

    def _wrapper() -> Optional[float]:
        if handle.cancelled:
            return None
        try:
            fn()
        except Exception as exc:
            logger.error(
                "set_interval callback %r raised an exception: %s",
                fn,
                exc,
                exc_info=True,
            )
        if handle.cancelled:
            return None
        return interval_s

    try:
        bpy.app.timers.register(
            _wrapper,
            first_interval=interval_s,
            persistent=True,
        )
        logger.debug(
            "set_interval registered handle=%s fn=%r interval=%.3fs",
            handle.id,
            fn,
            interval_s,
        )
    except Exception as exc:
        logger.error("set_interval failed to register timer: %s", exc)
        handle.cancelled = True
        _registry.pop(handle.id, None)

    return handle


def set_timeout(fn: Callable, delay_ms: float) -> TimerHandle:
    """
    Call *fn* once after *delay_ms* milliseconds.

    Returns a :class:`TimerHandle` that can be passed to :func:`clear` to
    prevent *fn* from being invoked if the timer hasn't fired yet.
    """
    import bpy

    delay_s = delay_ms / 1000.0
    handle = TimerHandle(_generate_handle_id())
    _register_handle(handle)

    def _wrapper() -> None:
        _registry.pop(handle.id, None)
        if handle.cancelled:
            return None
        try:
            fn()
        except Exception as exc:
            logger.error(
                "set_timeout callback %r raised an exception: %s",
                fn,
                exc,
                exc_info=True,
            )
        return None

    try:
        bpy.app.timers.register(
            _wrapper,
            first_interval=delay_s,
            persistent=True,
        )
        logger.debug(
            "set_timeout registered handle=%s fn=%r delay=%.3fs",
            handle.id,
            fn,
            delay_s,
        )
    except Exception as exc:
        logger.error("set_timeout failed to register timer: %s", exc)
        handle.cancelled = True
        _registry.pop(handle.id, None)

    return handle


def clear(handle: TimerHandle) -> None:
    """
    Cancel a timer returned by :func:`set_interval` or :func:`set_timeout`.

    Cancellation is signalled via ``handle.cancelled``; the bpy wrapper
    checks this flag on its next invocation and returns ``None`` to
    unschedule itself.  It is safe to call ``clear`` after the timer has
    already fired or been cancelled.
    """
    if not isinstance(handle, TimerHandle):
        logger.warning("clear() received a non-TimerHandle argument: %r", handle)
        return
    handle.cancel()


def _cleanup_all() -> None:
    """
    Cancel every active timer managed by this module.

    Called automatically from ``puree.unregister()`` so that no Puree-owned
    timers outlive the addon lifecycle.
    """
    active = list(_registry.values())
    if not active:
        return
    logger.debug("_cleanup_all: cancelling %d timer(s)", len(active))
    for handle in active:
        try:
            handle.cancel()
        except Exception as exc:
            logger.warning("_cleanup_all: error cancelling handle %s: %s", handle.id, exc)
    _registry.clear()
    logger.info("Timer cleanup complete — %d timer(s) cancelled", len(active))
