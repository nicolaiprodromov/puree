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

"""
Centralized input routing for Puree UI.

Decides whether Blender events should be consumed (RUNNING_MODAL) or
passed through (PASS_THROUGH) based on whether the mouse cursor is
currently over any drawn Puree surface.

Design notes for future drag/interaction support:
  - Capture mode: when a mousedown starts on a Puree surface, all
    subsequent events are consumed until mouseup, even if the cursor
    leaves the surface. This prevents Blender from receiving partial
    drag gestures.
  - The module is intentionally stateless regarding *which* container
    is hit — that responsibility stays in hit_op. This module only
    answers: "should Blender see this event?"
"""


class InputRouter:
    """Singleton that tracks whether the cursor is over Puree UI and
    decides event consumption for all modal operators."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_state()
        return cls._instance

    def _init_state(self):
        # True when any non-passive, visible, drawn container is under the cursor
        self.is_over_ui = False

        # Capture mode — when a press starts on UI we hold capture until release
        self._captured = False

    # ------------------------------------------------------------------
    # State updates (called from hit_op after detection)
    # ------------------------------------------------------------------

    @staticmethod
    def has_drawn_pixels(container: dict) -> bool:
        """Return True if a container renders any visible pixels.

        A container that is purely a layout wrapper (transparent bg,
        no border, no shadow) should not block Blender interaction.

        In the flattened container list produced by Rust, style
        properties are stored at the top level of the dict (not nested
        under a 'style' sub-dict — that key holds the style ID string).
        """
        bg = container.get("background_color")
        if bg and len(bg) >= 4 and bg[3] > 0:
            return True

        bg2 = container.get("background_color_2")
        if bg2 and len(bg2) >= 4 and bg2[3] > 0:
            return True

        bw = container.get("border_width", 0)
        if bw > 0:
            bc = container.get("border_color")
            if bc and len(bc) >= 4 and bc[3] > 0:
                return True

        sc = container.get("box_shadow_color")
        if sc and len(sc) >= 4 and sc[3] > 0:
            blur = container.get("box_shadow_blur", 0)
            offset = container.get("box_shadow_offset", [0, 0, 0])
            if blur > 0 or any(abs(v) > 0 for v in offset):
                return True

        return False

    @staticmethod
    def is_over_drawn_surface(container_data: list) -> bool:
        """Return True if any hovered container, or any ancestor of a
        hovered container, has drawn pixels.

        The Rust HitDetector uses hierarchical occlusion: a hovered
        child prevents its parent from being marked hovered.  So a
        transparent scroll-container inside a drawn panel would be the
        only hovered element.  We walk up the parent chain to find
        whether the cursor is visually inside any drawn surface.
        """
        for c in container_data:
            if not c.get("_hovered", False):
                continue
            if c.get("passive", False):
                continue

            # Walk from the hovered container up through ancestors
            current = c
            while current is not None:
                if InputRouter.has_drawn_pixels(current):
                    return True
                parent_idx = current.get("parent", -1)
                if parent_idx < 0 or parent_idx >= len(container_data):
                    break
                current = container_data[parent_idx]

        return False

    def update_hover_state(self, any_hit: bool):
        """Called every frame by hit_op with the result of hit detection.

        Args:
            any_hit: True if any non-passive, displayed, *drawn* container
                     is hovered.
        """
        self.is_over_ui = any_hit

    def notify_press(self):
        """Called when a mouse press occurs while over UI.
        Enters capture mode so events stay consumed until release."""
        if self.is_over_ui:
            self._captured = True

    def notify_release(self):
        """Called on mouse release — exits capture mode."""
        self._captured = False

    # ------------------------------------------------------------------
    # Query (called by each modal operator before returning)
    # ------------------------------------------------------------------

    def should_consume_event(self, event_type: str = "") -> bool:
        """Return True if the event should be consumed (RUNNING_MODAL).

        When captured (mouse-down started on UI) we consume everything
        until release regardless of current hover state.  Otherwise we
        consume only while hovering over drawn UI.

        Args:
            event_type: Blender event type string (e.g. 'LEFTMOUSE',
                        'WHEELUPMOUSE'). Currently unused but available
                        for future per-type overrides.
        """
        if self._captured:
            return True
        return self.is_over_ui

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self):
        """Reset all state — call on UI stop."""
        self._init_state()


input_router = InputRouter()
