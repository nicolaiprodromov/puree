# Created by XWZ
# ◕‿◕ Distributed for free at:
# https://github.com/nicolaiprodromov/puree
"""
collapse.py — Container collapse/expand with smooth animation (Feature 7).

Animates container height between the header-only height and the full expanded
height using ``bpy.app.timers``.  Since Puree cannot animate layout properties
via CSS transitions, this module drives height changes internally by setting
``style.height`` and ``style.overflow`` each frame and calling ``mark_dirty()``.
"""
from __future__ import annotations

import time
from typing import Dict, Optional

from .log import get_logger

logger = get_logger(__name__)

_ANIMATION_DURATION = 0.2  # seconds


def _ease_out_quad(t: float) -> float:
    """Quadratic ease-out: fast start, decelerating."""
    return 1.0 - (1.0 - t) ** 2


class _CollapseAnimation:
    """State for a single in-flight collapse/expand animation."""
    __slots__ = ('container', 'start_height', 'target_height',
                 'start_time', 'duration', 'expanding', '_original_overflow',
                 '_original_height')

    def __init__(self, container, start_height: float, target_height: float,
                 expanding: bool, duration: float = _ANIMATION_DURATION):
        self.container = container
        self.start_height = start_height
        self.target_height = target_height
        self.start_time = time.monotonic()
        self.duration = duration
        self.expanding = expanding
        # Preserve the original style values so we can restore them on completion
        self._original_overflow = getattr(container.style, 'overflow', 'VISIBLE') if container.style else 'VISIBLE'
        self._original_height = getattr(container.style, 'height', 0) if container.style else 0


class CollapseManager:
    """Singleton that tracks and drives collapse/expand animations."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            inst = super().__new__(cls)
            inst._animations: Dict[str, _CollapseAnimation] = {}
            inst._timer_registered = False
            cls._instance = inst
        return cls._instance

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def collapse(self, container) -> None:
        """Collapse *container* with a smooth height animation."""
        if container.id in self._animations:
            # Cancel any running animation on this container
            del self._animations[container.id]

        container.collapsed = True

        # Measure current rendered height from layout data
        current_h = self._get_rendered_height(container)
        if current_h is None or current_h <= 0:
            # Fallback: snap immediately if we can't measure
            self._snap_collapse(container)
            return

        # Target height = first child (header) height
        header_h = self._get_header_height(container)
        if header_h is None:
            header_h = 0.0

        # Lock overflow so content doesn't bleed during animation
        if container.style:
            container.style.overflow = 'HIDDEN'

        anim = _CollapseAnimation(container, current_h, header_h, expanding=False)
        self._animations[container.id] = anim
        self._ensure_timer()

    def expand(self, container) -> None:
        """Expand *container* with a smooth height animation."""
        if container.id in self._animations:
            del self._animations[container.id]

        container.collapsed = False

        # First, make all children visible so we can measure full height
        for child in container.children:
            child.style.display = 'FLEX'
            child.mark_dirty()

        # Current height is the header-only height
        current_h = self._get_rendered_height(container)
        if current_h is None or current_h <= 0:
            self._snap_expand(container)
            return

        # Estimate the full expanded height: sum of all children heights + gaps
        full_h = self._estimate_expanded_height(container)
        if full_h <= current_h:
            # Already at or past full size — just snap
            self._snap_expand(container)
            return

        if container.style:
            container.style.overflow = 'HIDDEN'
            container.style.height = current_h

        anim = _CollapseAnimation(container, current_h, full_h, expanding=True)
        self._animations[container.id] = anim
        self._ensure_timer()

    def toggle(self, container) -> None:
        """Toggle collapse state of *container*."""
        if getattr(container, 'collapsed', False):
            self.expand(container)
        else:
            self.collapse(container)

    # ------------------------------------------------------------------
    # Animation tick (called from bpy.app.timers)
    # ------------------------------------------------------------------

    def _tick(self) -> Optional[float]:
        """Advance all active animations.  Returns timer reschedule interval."""
        if not self._animations:
            self._timer_registered = False
            return None  # stop timer

        now = time.monotonic()
        finished = []

        for cid, anim in list(self._animations.items()):
            elapsed = now - anim.start_time
            t = min(1.0, elapsed / anim.duration) if anim.duration > 0 else 1.0
            eased = _ease_out_quad(t)

            current_h = anim.start_height + (anim.target_height - anim.start_height) * eased

            c = anim.container
            if c.style:
                c.style.height = current_h
            c.mark_dirty()

            if t >= 1.0:
                finished.append(cid)

        for cid in finished:
            anim = self._animations.pop(cid, None)
            if anim is None:
                continue
            c = anim.container
            if anim.expanding:
                # Restore natural sizing — clear explicit height
                if c.style:
                    c.style.height = anim._original_height
                    c.style.overflow = anim._original_overflow
                c.mark_dirty()
            else:
                # Collapsing finished — hide non-header children
                for i, child in enumerate(c.children):
                    if i > 0:
                        child.style.display = 'NONE'
                        child.mark_dirty()
                if c.style:
                    c.style.height = anim._original_height
                    c.style.overflow = anim._original_overflow
                c.mark_dirty()

        if not self._animations:
            self._timer_registered = False
            return None

        return 0.016  # ~60 fps

    def _ensure_timer(self) -> None:
        """Register the animation tick timer if not already running."""
        if self._timer_registered:
            return
        try:
            import bpy
            bpy.app.timers.register(self._tick, first_interval=0.016)
            self._timer_registered = True
        except Exception as e:
            logger.warning("CollapseManager: could not register animation timer: %s", e)
            # Fall back to snap
            for anim in list(self._animations.values()):
                if anim.expanding:
                    self._snap_expand(anim.container)
                else:
                    self._snap_collapse(anim.container)
            self._animations.clear()

    # ------------------------------------------------------------------
    # Snap fallbacks (no animation)
    # ------------------------------------------------------------------

    def _snap_collapse(self, container) -> None:
        """Instantly collapse without animation."""
        container.collapsed = True
        for i, child in enumerate(container.children):
            if i > 0:
                child.style.display = 'NONE'
                child.mark_dirty()
        container.mark_dirty()

    def _snap_expand(self, container) -> None:
        """Instantly expand without animation."""
        container.collapsed = False
        for child in container.children:
            child.style.display = 'FLEX'
            child.mark_dirty()
        container.mark_dirty()

    # ------------------------------------------------------------------
    # Height measurement helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_rendered_height(container) -> Optional[float]:
        """Read the last computed height from the layout data."""
        try:
            from .parser import node_flat_abs
            layout = node_flat_abs.get(container.id)
            if layout:
                return float(layout.get('height', 0))
        except Exception:
            pass
        return None

    @staticmethod
    def _get_header_height(container) -> Optional[float]:
        """Return the rendered height of the first child (header)."""
        if not container.children:
            return 0.0
        try:
            from .parser import node_flat_abs
            header = container.children[0]
            layout = node_flat_abs.get(header.id)
            if layout:
                return float(layout.get('height', 0))
        except Exception:
            pass
        return None

    @staticmethod
    def _estimate_expanded_height(container) -> float:
        """Estimate expanded height by summing children's rendered heights."""
        try:
            from .parser import node_flat_abs
            total = 0.0
            for child in container.children:
                layout = node_flat_abs.get(child.id)
                if layout:
                    total += float(layout.get('height', 0))
            # Add gap if the container uses gap
            if container.style and hasattr(container.style, 'gap') and container.style.gap:
                try:
                    gap_str = str(container.style.gap).replace('px', '').strip()
                    gap_val = float(gap_str) if gap_str else 0.0
                    total += gap_val * max(0, len(container.children) - 1)
                except (ValueError, TypeError):
                    pass
            return total
        except Exception:
            return 0.0

    # ------------------------------------------------------------------
    # Initial-state application (called during parse, before layout)
    # ------------------------------------------------------------------

    def apply_initial_state(self, container) -> None:
        """Apply collapsed state from a single parsed container."""
        if getattr(container, 'collapsed', False):
            for i, child in enumerate(container.children):
                if i > 0:
                    if (hasattr(child, 'style') and child.style is not None
                            and hasattr(child.style, 'display')):
                        child.style.display = 'NONE'

    def apply_initial_states(self, root_container) -> None:
        """Recursively apply initial collapse states declared in YAML.

        Called after *flatten_node_tree()* but before the first render.
        We do NOT call mark_dirty() here — the UI is not fully initialised
        yet so mark_dirty would be a no-op or could raise.
        """
        def walk(c):
            if getattr(c, 'collapsed', False):
                for i, child in enumerate(c.children):
                    if i > 0:
                        if (hasattr(child, 'style') and child.style is not None
                                and hasattr(child.style, 'display')):
                            child.style.display = 'NONE'
            for child in c.children:
                walk(child)

        walk(root_container)


# Module-level singleton — import this everywhere.
collapse_manager = CollapseManager()
