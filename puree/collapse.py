# Created by XWZ
# ◕‿◕ Distributed for free at:
# https://github.com/nicolaiprodromov/puree
"""
collapse.py — Container collapse/expand system (Feature 7).

Provides snap-toggle visibility of child containers. Since Puree's layout
engine cannot animate layout properties via CSS transitions, collapse/expand
is an instant visibility change: all non-first children are hidden (NONE) or
restored (FLEX) on demand.
"""

from __future__ import annotations


class CollapseManager:
    """Singleton that tracks and drives collapse/expand for containers."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def collapse(self, container) -> None:
        """Collapse *container*: hide every child after the first (header)."""
        container.collapsed = True
        for i, child in enumerate(container.children):
            if i > 0:
                child.style.display = "NONE"
                child.mark_dirty()
        container.mark_dirty()

    def expand(self, container) -> None:
        """Expand *container*: make all children visible."""
        container.collapsed = False
        for child in container.children:
            child.style.display = "FLEX"
            child.mark_dirty()
        container.mark_dirty()

    def toggle(self, container) -> None:
        """Toggle collapse state of *container*."""
        if getattr(container, "collapsed", False):
            self.expand(container)
        else:
            self.collapse(container)

    # ------------------------------------------------------------------
    # Initial-state application (called during parse, before layout)
    # ------------------------------------------------------------------

    def apply_initial_state(self, container) -> None:
        """Apply collapsed state from a single parsed container."""
        if getattr(container, "collapsed", False):
            for i, child in enumerate(container.children):
                if i > 0:
                    if hasattr(child, "style") and child.style is not None and hasattr(child.style, "display"):
                        child.style.display = "NONE"

    def apply_initial_states(self, root_container) -> None:
        """Recursively apply initial collapse states declared in YAML.

        Called after *flatten_node_tree()* but before the first render.
        We do NOT call mark_dirty() here — the UI is not fully initialised
        yet so mark_dirty would be a no-op or could raise.
        """

        def walk(c):
            if getattr(c, "collapsed", False):
                for i, child in enumerate(c.children):
                    if i > 0:
                        if hasattr(child, "style") and child.style is not None and hasattr(child.style, "display"):
                            child.style.display = "NONE"
            for child in c.children:
                walk(child)

        walk(root_container)


# Module-level singleton — import this everywhere.
collapse_manager = CollapseManager()
