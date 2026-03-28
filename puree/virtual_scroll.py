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
from __future__ import annotations

import bisect
from typing import Any, Callable, List, Optional

from .log import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Module-level helper
# ---------------------------------------------------------------------------

def _build_offsets(heights: list) -> list:
    """Build cumulative prefix-sum list from heights.

    Returns a list of length ``len(heights) + 1`` where ``offsets[i]`` is the
    y-coordinate at which item *i* starts and ``offsets[-1]`` is the total
    height of all items.
    """
    offsets: List[float] = []
    total = 0.0
    for h in heights:
        offsets.append(total)
        total += h
    offsets.append(total)
    return offsets


# ---------------------------------------------------------------------------
# VirtualScroll
# ---------------------------------------------------------------------------

class VirtualScroll:
    """Renders only the visible subset of a large list inside a scroll container.

    Usage (in script.py)::

        from puree.virtual_scroll import VirtualScroll

        scroll = app.get_by_id("messages_scroll")
        vs = VirtualScroll(scroll, item_height=60)   # fixed-height
        vs = VirtualScroll(scroll, item_height='auto')  # variable-height

        vs.set_data(messages_list)
        vs.set_renderer(lambda container, item, index: ...)
        vs.update()
    """

    def __init__(
        self,
        container,
        item_height: Any = 60,
        overscan: int = 2,
        item_class: Optional[str] = None,
    ) -> None:
        """
        Parameters
        ----------
        container:
            The scroll ``Container`` whose children this instance manages.
        item_height:
            Fixed item height in pixels (int/float), or ``'auto'`` to measure
            heights dynamically.
        overscan:
            Number of extra items to render above and below the visible area.
        item_class:
            Optional CSS class string applied to every pool slot container.
        """
        self._container = container
        self._item_height: Any = item_height
        self._item_class: Optional[str] = item_class
        self._overscan: int = overscan
        self._default_height: float = float(60 if item_height == 'auto' else item_height)

        self._data: list = []
        self._renderer: Optional[Callable] = None
        self._pool: List[Any] = []
        self._total_height: float = 0.0

        # Variable-height support
        self._heights: List[float] = []
        self._offsets: List[float] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_data(self, data: list) -> None:
        """Assign the data list.  Call ``update()`` afterwards to refresh the view."""
        self._data = data

        if self._item_height != 'auto':
            self._total_height = len(data) * float(self._item_height)
        else:
            self._heights = [self._default_height] * len(data)
            self._offsets = _build_offsets(self._heights)
            self._total_height = self._offsets[-1] if self._offsets else 0.0

        self._ensure_pool()

    def set_renderer(self, fn: Callable) -> None:
        """Set the item renderer.

        The callable must accept ``(container, item, index)`` and populate
        *container* with whatever child nodes represent *item*.
        """
        self._renderer = fn

    def update(self) -> None:
        """Recalculate the visible range and re-bind pool slots to data items."""
        if not self._data or not self._renderer:
            return

        from .dynamic import dynamic_manager
        ui = dynamic_manager._ui
        if ui is None:
            return

        scroll_offset = max(0.0, float(self._container._scroll_value))
        container_h = float(getattr(self._container, 'height', 0) or 0)

        # Grow pool if container has been resized since set_data()
        self._ensure_pool()

        if self._item_height != 'auto':
            item_h = float(self._item_height)
            first = max(0, int(scroll_offset / item_h) - self._overscan)
            visible = int(container_h / max(item_h, 1)) + self._overscan * 2 + 1
            last = min(len(self._data) - 1, first + visible)
        else:
            first, last = self._visible_range_auto(scroll_offset, container_h)

        # Bind visible items to pool slots
        slot_idx = 0
        for item_idx in range(first, last + 1):
            if slot_idx >= len(self._pool):
                break

            slot = self._pool[slot_idx]
            item = self._data[item_idx]

            # Clear previous render
            for child in slot.children:
                child.parent = None
            slot.children.clear()

            # Invoke user renderer (supports both 2-arg and 3-arg signatures)
            try:
                import inspect
                sig = inspect.signature(self._renderer)
                if len(sig.parameters) >= 3:
                    self._renderer(slot, item, item_idx)
                else:
                    self._renderer(slot, item)
            except Exception as exc:
                logger.error(
                    "VirtualScroll renderer error at index %d: %s",
                    item_idx, exc,
                    exc_info=True,
                )

            # Compute y offset for informational / layout use
            if self._item_height != 'auto':
                y_off = item_idx * float(self._item_height) - scroll_offset
            else:
                y_off = (
                    self._offsets[item_idx] - scroll_offset
                    if item_idx < len(self._offsets)
                    else 0.0
                )

            slot._vs_y_offset = y_off
            slot.style.display = 'FLEX'

            # Update measured height for variable-height mode
            self._update_measured_height(item_idx, slot)

            slot_idx += 1

        # Hide unused slots and clear their children
        for i in range(slot_idx, len(self._pool)):
            idle = self._pool[i]
            idle.style.display = 'NONE'
            for child in idle.children:
                child.parent = None
            idle.children.clear()

        # Commit structural changes to the layout engine
        ui._rebuild_after_structural_change()

    # ------------------------------------------------------------------
    # Scroll-callback integration
    # ------------------------------------------------------------------

    def attach_scroll(self) -> None:
        """Register this instance to auto-update whenever the scroll container scrolls."""
        from .scroll_op import scroll_state
        scroll_state.register_callback(self._on_scroll)

    def detach_scroll(self) -> None:
        """Remove the auto-update scroll callback."""
        from .scroll_op import scroll_state
        scroll_state.unregister_callback(self._on_scroll)

    def _on_scroll(self, delta: float, absolute: float) -> None:
        """Scroll-state callback — triggers an ``update()``."""
        self.update()

    # ------------------------------------------------------------------
    # Pool management
    # ------------------------------------------------------------------

    def _ensure_pool(self) -> None:
        """Grow the slot pool to match the current container size + overscan."""
        item_h = (
            self._item_height
            if self._item_height != 'auto'
            else self._default_height
        )
        item_h = float(max(item_h, 1))
        container_h = float(getattr(self._container, 'height', 0) or 0)
        needed = int(container_h / item_h) + self._overscan * 2 + 4
        needed = max(needed, 4)

        if len(self._pool) >= needed:
            return

        for i in range(len(self._pool), needed):
            slot = self._create_slot(i)
            self._pool.append(slot)

        # One bulk rebuild for all new slots
        from .dynamic import dynamic_manager
        ui = dynamic_manager._ui
        if ui is not None:
            ui._rebuild_after_structural_change()

    def _create_slot(self, slot_index: int):
        """Instantiate a bare Container as a pool slot and attach it to the scroll container."""
        from .components.container import Container

        slot = Container()
        slot.id = f"{self._container.id}_vs_{slot_index}"
        slot.parent = self._container

        if self._item_class:
            slot.classes = [self._item_class]

        self._container.children.append(slot)
        return slot

    # ------------------------------------------------------------------
    # Variable-height helpers
    # ------------------------------------------------------------------

    def _visible_range_auto(
        self, scroll_offset: float, container_h: float
    ):
        """Return ``(first, last)`` item indices visible for variable-height mode."""
        if not self._offsets:
            return 0, 0

        first = max(
            0,
            bisect.bisect_right(self._offsets, scroll_offset) - 1 - self._overscan,
        )
        end_offset = scroll_offset + container_h
        last = min(
            len(self._data) - 1,
            bisect.bisect_left(self._offsets, end_offset) + self._overscan,
        )
        return first, last

    def _update_measured_height(self, item_idx: int, slot) -> None:
        """After layout, read the slot's actual height and refresh the offset table.

        Only meaningful in auto-height mode.
        """
        if self._item_height != 'auto':
            return
        if item_idx >= len(self._heights):
            return

        measured = float(getattr(slot, 'height', self._default_height) or self._default_height)
        if measured != self._heights[item_idx]:
            self._heights[item_idx] = measured
            self._offsets = _build_offsets(self._heights)
            self._total_height = self._offsets[-1] if self._offsets else 0.0
