# Created by XWZ
# ◕‿◕ Distributed for free at:
# https://github.com/nicolaiprodromov/puree
from __future__ import annotations

from typing import Optional

from .log import get_logger

logger = get_logger(__name__)


class FocusManager:
    def __init__(self):
        self._focused_id: Optional[str] = None
        self._focused_on_blur: Optional[list] = None  # ref to focused container's on_blur list
        self._focused_container_ref = None

    def focus(self, container_id: str, on_focus: list, on_blur: list, container_ref=None) -> None:
        """Focus a container by ID. Blurs the previous one first."""
        if self._focused_id == container_id:
            return
        # Blur previous
        self._blur_internal()
        # Set new focus
        self._focused_id = container_id
        self._focused_on_blur = on_blur
        self._focused_container_ref = container_ref
        # Fire on_focus callbacks
        for cb in list(on_focus):
            try:
                if container_ref is not None:
                    cb(container_ref)
                else:
                    cb(container_id)
            except Exception as e:
                logger.error(f"on_focus callback error: {e}", exc_info=True)

    def blur(self, container_id: str = None) -> None:
        """Blur a specific container (or all if container_id is None)."""
        if container_id is not None and self._focused_id != container_id:
            return
        self._blur_internal()

    def _blur_internal(self):
        if self._focused_id is None:
            return
        old_id = self._focused_id
        on_blur = self._focused_on_blur or []
        container_ref = self._focused_container_ref
        self._focused_id = None
        self._focused_on_blur = None
        self._focused_container_ref = None
        for cb in list(on_blur):
            try:
                if container_ref is not None:
                    cb(container_ref)
                else:
                    cb(old_id)
            except Exception as e:
                logger.error(f"on_blur callback error: {e}", exc_info=True)

    def get_focused_id(self) -> Optional[str]:
        return self._focused_id

    def is_focused(self, container_id: str) -> bool:
        return self._focused_id == container_id

    def tab_next(self) -> None:
        """Tab to next focusable container (sorted by tab_index ascending)."""
        try:
            from . import parser_op

            containers = parser_op._container_json_data
            focusable = sorted(
                [
                    (c["id"], c.get("on_focus", []), c.get("on_blur", []), c.get("tab_index", 0))
                    for c in containers
                    if c.get("focusable", False) and c.get("tab_index", -1) >= 0
                ],
                key=lambda x: x[3],
            )
        except Exception as e:
            logger.error(f"tab_next error: {e}", exc_info=True)
            return
        if not focusable:
            return
        if self._focused_id is None:
            self.focus(focusable[0][0], focusable[0][1], focusable[0][2])
        else:
            ids = [f[0] for f in focusable]
            if self._focused_id in ids:
                idx = (ids.index(self._focused_id) + 1) % len(ids)
            else:
                idx = 0
            self.focus(focusable[idx][0], focusable[idx][1], focusable[idx][2])

    def tab_prev(self) -> None:
        """Shift+Tab to previous focusable container (sorted by tab_index ascending)."""
        try:
            from . import parser_op

            containers = parser_op._container_json_data
            focusable = sorted(
                [
                    (c["id"], c.get("on_focus", []), c.get("on_blur", []), c.get("tab_index", 0))
                    for c in containers
                    if c.get("focusable", False) and c.get("tab_index", -1) >= 0
                ],
                key=lambda x: x[3],
            )
        except Exception as e:
            logger.error(f"tab_prev error: {e}", exc_info=True)
            return
        if not focusable:
            return
        if self._focused_id is None:
            self.focus(focusable[-1][0], focusable[-1][1], focusable[-1][2])
        else:
            ids = [f[0] for f in focusable]
            if self._focused_id in ids:
                idx = (ids.index(self._focused_id) - 1) % len(ids)
            else:
                idx = len(ids) - 1
            self.focus(focusable[idx][0], focusable[idx][1], focusable[idx][2])

    def clear(self) -> None:
        """Clear all focus state (on hot reload)."""
        self._focused_id = None
        self._focused_on_blur = None
        self._focused_container_ref = None


focus_manager = FocusManager()
