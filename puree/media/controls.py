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
"""Default video-controls behavior wiring (MEDIA_PLAN section 7.2).

The parser injects the [video_controls] component under every ``video:``
node with ``controls: true`` (parser.UI._inject_video_controls); this
module wires its behavior. ``wire_video_controls(ui)`` runs from
XWZ_OT_ui_parser.execute right after user scripts compile - which covers
BOTH the initial parse and every hot reload (trigger_ui_reload re-runs
the parse operator) - and BEFORE the extractors, so initial icon/label
state lands in the first text/image extraction.

Idempotency / lifecycle: containers (and their click/hover handler
lists) are rebuilt fresh on every parse and need no cleanup, but three
registrations OUTLIVE the container tree - MediaController listeners
(controllers are id-bound and persist in MediaManager), the
mouse_state callback and the SPACE key binding. wire_video_controls()
therefore starts by unwiring the previous run (keyed by root identity),
and the mouse callback additionally carries the stale-root guard from
tests/helloworld/script.py as a belt against reparses that skip wiring.
The video's on_fullscreen_change handler dies with the tree like
click/hover, but release() removes it anyway so a same-tree rewire
(tests, defensive re-runs) never stacks a second icon-flip handler.

Interaction map per video (see video_controls.yaml for the tree):

- play/pause button click  -> media.toggle(); the paired icon wraps flip
  on 'play'/'pause'/'ended' events via the display FLEX/NONE swap
  (collapse.py pattern) plus an opacity guard on the img child.
- mute button click        -> media.muted toggle + icon flip.
- time labels              -> 'timeupdate' (throttled ~250 ms by the
  controller) writes m:ss text; duration label once metadata is known.
- seek                     -> click on the track starts the gesture
  (click fires on PRESS), mouse_state streams moves/release (the
  helloworld draggable-card pattern; InputRouter capture holds the
  gesture), mouse-x maps through parser.node_flat_abs[track] to
  0..1 * duration. Seeks are throttled to <= 10/s while scrubbing; the
  fill width updates locally on every move for responsiveness.
- auto-hide                -> video hover shows the bar, hoverout while
  playing hides it, pause/ended always show it. The fade animates the
  wrapper's opacity through the engine TransitionManager using the
  SCSS-declared transition (snaps when the render pipeline is not
  running). The injected wrapper is passive, so the video container
  keeps its hover state while the cursor is over the bar. Works inside
  fullscreen too: hit results apply by container id, so hover/hoverout
  flow through the swapped fullscreen hit set unchanged.
- fullscreen button        -> container.request_fullscreen()/
  exit_fullscreen() toggle (FULLSCREEN_PLAN Phase B - the generic
  Container API; region "theater mode"). The paired icon wraps flip on
  the video's on_fullscreen_change EVENT, never on the click itself, so
  ESC exits, scripts and hot-reload force-exits flip the icon too.
  While fullscreen, seek geometry reads the PRIVATE layout box from
  fullscreen_manager.box_abs(track_id) instead of parser.node_flat_abs
  (the main-tree box is stale inside the mode) - see _track_box.
- SPACE                    -> container-scoped key binding (the injector
  marks video nodes focusable; clicking the video focuses it). NOTE:
  key dispatch runs inside the text-input KeyboardHandler modal, so
  SPACE only works in UIs that contain at least one text input
  (pre-existing engine constraint).

Events fire on the main thread from MediaManager.tick - no threading
here.
"""

import time

try:
    from ..log import get_logger

    logger = get_logger(__name__)
except Exception:  # pragma: no cover - outside the package/Blender
    import logging

    logger = logging.getLogger(__name__)

from ..keyboard import keys
from . import media_manager

__all__ = ["wire_video_controls", "unwire_video_controls", "format_time"]

SEEK_INTERVAL = 0.1  # seconds between scrub seeks (<= 10/s while dragging)
DEFAULT_FADE = (0.2, "ease", 0.0)  # (duration s, timing, delay) fallback

_wired = []  # live _WiredControls, replaced wholesale on every parse
_current_root = None  # root of the tree the current wiring belongs to


def format_time(seconds):
    """``m:ss`` (``h:mm:ss`` past an hour); defensive about None/negatives."""
    try:
        total = int(seconds)
    except (TypeError, ValueError):
        return "0:00"
    if total < 0:
        return "0:00"
    minutes, secs = divmod(total, 60)
    if minutes >= 60:
        hours, minutes = divmod(minutes, 60)
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def wire_video_controls(ui):
    """(Re)wire every injected controls bar in *ui*. Safe to run twice."""
    global _current_root

    unwire_video_controls()

    root = ui.theme.root

    videos = []

    def walk(container):
        for child in container.children:
            walk(child)
        if getattr(container, "video", "") and getattr(container, "controls", False):
            videos.append(container)

    walk(root)
    if not videos:
        return 0

    _current_root = root
    for video in videos:
        wrapper = None
        for child in video.children:
            if getattr(child, "id", "") == f"{video.id}_puree_vc":
                wrapper = child
                break
        if wrapper is None:
            logger.debug(f"video '{video.id}' has controls: true but no injected bar - skipping wiring")
            continue
        try:
            _wired.append(_WiredControls(ui, video, wrapper))
        except Exception:
            logger.error(f"Failed to wire video controls for '{video.id}'", exc_info=True)
    return len(_wired)


def unwire_video_controls():
    """Release listener/callback/keybinding registrations of the last run."""
    global _current_root
    for wired in _wired:
        try:
            wired.release()
        except Exception:
            logger.debug("Video controls release failed", exc_info=True)
    _wired.clear()
    _current_root = None


class _WiredControls:
    """Behavior for one video node + its injected [video_controls] subtree."""

    def __init__(self, ui, video, wrapper):
        self.ui = ui
        self.video = video
        self.wrapper = wrapper
        self._root = ui.theme.root
        self._dead = False

        # Resolve subtree nodes by unique id suffix - tolerant of a user
        # component shadowing video_controls.yaml with different nesting,
        # as long as it keeps the leaf names; missing nodes degrade to
        # no-ops for their feature.
        nodes = {}

        def collect(container):
            nodes[container.id] = container
            for child in container.children:
                collect(child)

        collect(wrapper)

        def find(suffix):
            for node_id, node in nodes.items():
                if node_id.endswith(suffix):
                    return node
            return None

        self.play_btn = find("_vc_play")
        self.play_ic = find("_vc_play_ic")
        self.play_img = find("_vc_play_img")
        self.pause_ic = find("_vc_pause_ic")
        self.pause_img = find("_vc_pause_img")
        self.time_label = find("_vc_time")
        self.track = find("_vc_track")
        self.fill = find("_vc_fill")
        self.duration_label = find("_vc_duration")
        self.mute_btn = find("_vc_mute")
        self.sound_ic = find("_vc_sound_ic")
        self.sound_img = find("_vc_sound_img")
        self.mute_ic = find("_vc_mute_ic")
        self.mute_img = find("_vc_mute_img")
        self.fs_btn = find("_vc_fullscreen")
        self.fs_ic = find("_vc_fs_ic")
        self.fs_img = find("_vc_fs_img")
        self.exit_fs_ic = find("_vc_exit_fs_ic")
        self.exit_fs_img = find("_vc_exit_fs_img")

        # id-bound controller: valid before MediaManager.attach() runs
        # (control calls no-op, properties read safe defaults) and across
        # hot reloads.
        self.controller = media_manager.controller_for(video.id)

        self._dragging = False
        self._last_seek = 0.0
        self._last_fill_pct = None
        self._bar_opacity = 1.0
        self._duration_known = False
        self._fade = self._read_fade()

        # Container handler lists are fresh per parse - append, no cleanup.
        if self.play_btn is not None:
            self.play_btn.click.append(self._on_play_click)
        if self.mute_btn is not None:
            self.mute_btn.click.append(self._on_mute_click)
        if self.track is not None:
            self.track.click.append(self._on_track_press)
        if self.fs_btn is not None:
            self.fs_btn.click.append(self._on_fullscreen_click)
        video.hover.append(self._on_video_hover)
        video.hoverout.append(self._on_video_hoverout)
        # Icon truth = the fullscreen-change EVENT (fires for the button,
        # ESC, scripts, swaps and force-exits alike) - removed by release()
        # so same-tree rewires never stack handlers.
        video.on_fullscreen_change.append(self._on_fullscreen_change)

        # Long-lived registrations (released by unwire_video_controls):
        self._listeners = []
        for event, fn in (
            ("play", self._on_media_play),
            ("pause", self._on_media_pause),
            ("ended", self._on_media_ended),
            ("timeupdate", self._on_media_timeupdate),
        ):
            self.controller.on(event, fn)
            self._listeners.append((event, fn))

        from ..mouse_op import mouse_state

        self._mouse_state = mouse_state
        mouse_state.register_callback(self._on_mouse)

        self._space_binding = None
        try:
            # Container-scoped: fires only while the (focusable) video node
            # holds focus - clicking anywhere on the video focuses it.
            self._space_binding = keys.bind("SPACE", self._on_space, container_id=video.id)
        except Exception:
            logger.debug("SPACE binding unavailable", exc_info=True)

        # Initial state - wire runs BEFORE the extractors, so this lands in
        # the very first text/image extraction. Pre-attach, paused reads
        # True (autoplay flips the icon via the 'play' event on the first
        # tick after attach) and muted comes from the YAML attribute. The
        # fullscreen icon reads the live container.fullscreen (False on
        # normal parses - the reparse operator force-exits first).
        self._apply_play_icons()
        self._apply_mute_icons()
        self._apply_fullscreen_icons()
        self._sync_labels()

    # ── clicks ───────────────────────────────────────────────────────

    def _on_play_click(self, _container=None):
        self.controller.toggle()
        # icon flip arrives via the 'play'/'pause' events (single source of
        # truth); pre-attach toggles no-op and the icons stay put.

    def _on_mute_click(self, _container=None):
        self.controller.muted = not self._muted()
        self._apply_mute_icons()

    def _on_fullscreen_click(self, _container=None):
        # The generic Container API (FULLSCREEN_PLAN Phase B) - NOT
        # fullscreen_manager.toggle(), so the button demos the public
        # surface. Icons deliberately do NOT flip here: the
        # on_fullscreen_change event is the single source of truth
        # (ESC/scripts exit fullscreen without going through this click).
        if getattr(self.video, "fullscreen", False):
            self.video.exit_fullscreen()
        else:
            self.video.request_fullscreen()

    def _on_space(self):
        self.controller.toggle()

    # ── seek drag (helloworld draggable-card pattern) ────────────────

    def _on_track_press(self, _container=None):
        # click fires on PRESS - the gesture starts here; InputRouter
        # capture keeps Blender from stealing the drag.
        duration = self.controller.duration
        if not duration or duration <= 0:
            return  # metadata not ready, or unsupported/error source
        frac = self._track_frac()
        if frac is None:
            return
        self._dragging = True
        self._apply_scrub(frac, force_seek=True)

    def _on_mouse(self, kind, value):
        if self._dead:
            return
        if _current_root is not None and self._root is not _current_root:
            return  # stale wiring from a previous tree (helloworld guard)
        if not self._dragging:
            return
        if kind == "click" and not value:
            self._dragging = False
            frac = self._track_frac()
            if frac is not None:
                self._apply_scrub(frac, force_seek=True)  # final, unthrottled
            if not self._video_hovered() and not self.controller.paused:
                self._set_bar_visible(False)
        elif kind == "mouse":
            frac = self._track_frac()
            if frac is not None:
                self._apply_scrub(frac)

    def _apply_scrub(self, frac, force_seek=False):
        self._set_fill(frac)  # local feedback on every move
        duration = self.controller.duration
        if not duration or duration <= 0:
            return
        now = time.monotonic()
        if force_seek or (now - self._last_seek) >= SEEK_INTERVAL:
            self._last_seek = now
            self.controller.seek(frac * duration)

    def _mouse_x_px(self):
        width = self.ui.canvas_size[0]
        ndc_x = self._mouse_state.mouse_pos[0]  # NDC: -1..1 left -> right
        return (ndc_x + 1.0) * 0.5 * width

    def _track_frac(self):
        """Mouse x mapped into the track box -> 0..1 (None when unknown).

        The box comes from _track_box (fullscreen-aware). Boxes are
        unscrolled layout space; the engine only wheel-scrolls vertically,
        so the x axis needs no scroll correction (and the fullscreen
        private layout has no scroll offsets at all).
        """
        if self.track is None:
            return None
        box = self._track_box()
        track_w = float(box.get("width", 0.0))
        if track_w <= 0:
            return None
        frac = (self._mouse_x_px() - float(box.get("x", 0.0))) / track_w
        return max(0.0, min(1.0, frac))

    def _track_box(self):
        """Border box of the seek track (node_flat_abs shape).

        While THIS video's subtree is the active fullscreen element, the
        track's on-screen geometry lives in the manager's PRIVATE layout -
        fullscreen_manager.box_abs(track_id) (Phase A handoff: the
        main-tree box is stale inside the mode). box_abs returns None when
        fullscreen is inactive OR the track is outside the active subtree
        (another element fullscreen), so normal-mode behavior is byte-
        identical: parser.node_flat_abs. Every seek gesture (press-jump
        and drag-scrub both go through _track_frac) reads it per event -
        region resizes mid-drag stay correct.
        """
        try:
            from ..fullscreen import fullscreen_manager

            fs_box = fullscreen_manager.box_abs(self.track.id)
            if fs_box is not None:
                return fs_box
        except Exception:
            logger.debug("Fullscreen track box lookup failed", exc_info=True)
        from .. import parser

        return parser.node_flat_abs.get(self.track.id) or {}

    # ── media events (main thread, MediaManager.tick) ────────────────

    def _on_media_play(self, _media=None):
        self._apply_play_icons()
        if not self._video_hovered():
            self._set_bar_visible(False)

    def _on_media_pause(self, _media=None):
        self._apply_play_icons()
        self._set_bar_visible(True)  # always visible when paused

    def _on_media_ended(self, _media=None):
        self._apply_play_icons()
        self._set_bar_visible(True)

    def _on_media_timeupdate(self, _media=None):
        self._sync_labels()
        duration = self.controller.duration
        if duration and duration > 0 and not self._dragging:
            self._set_fill(max(0.0, min(1.0, self.controller.current_time / duration)))

    # ── fullscreen event (fullscreen_manager, main thread) ───────────

    def _on_fullscreen_change(self, _container=None, is_fullscreen=False):
        """on_fullscreen_change handler on the video container - the ONLY
        place the fullscreen icon flips (covers button, ESC, scripts,
        swaps and hot-reload force-exits)."""
        if self._dead:
            return
        self._apply_fullscreen_icons(bool(is_fullscreen))

    # ── auto-hide ────────────────────────────────────────────────────

    def _on_video_hover(self, _container=None):
        self._set_bar_visible(True)

    def _on_video_hoverout(self, _container=None):
        # The wrapper is passive, so the video keeps hover while the cursor
        # is over the bar - this only fires when truly leaving the video.
        if not self.controller.paused and not self.controller.ended and not self._dragging:
            self._set_bar_visible(False)

    def _set_bar_visible(self, visible):
        target = 1.0 if visible else 0.0
        if target == self._bar_opacity:
            return
        start = self._bar_opacity
        self._bar_opacity = target
        # style value = where the fade settles (dirty-sync retargets the
        # live transition and updates the saved restore value to this).
        self.wrapper.set_property("opacity", target)
        try:
            from .. import render

            pipeline = render._render_data
            if pipeline is not None and pipeline.running:
                duration, timing, delay = self._fade
                live = pipeline.transitions.get_value(self.wrapper.id, "opacity")
                pipeline.transitions.start_transition(
                    self.wrapper.id,
                    "opacity",
                    live if live is not None else start,
                    target,
                    duration,
                    delay,
                    timing,
                )
        except Exception:
            # No render pipeline (headless/tests) - the opacity snaps.
            logger.debug("Bar fade fell back to snap", exc_info=True)

    def _read_fade(self):
        """(duration, timing, delay) of the SCSS opacity transition on the bar."""
        try:
            for flat in self.ui.abs_json_data:
                if flat.get("id") == self.wrapper.id:
                    for transition in flat.get("_transitions", []):
                        if transition.get("property") in ("opacity", "all"):
                            return (
                                float(transition.get("duration", DEFAULT_FADE[0])),
                                transition.get("timing", DEFAULT_FADE[1]),
                                float(transition.get("delay", DEFAULT_FADE[2])),
                            )
                    break
        except Exception:
            logger.debug("Failed to read bar fade transition", exc_info=True)
        return DEFAULT_FADE

    def _video_hovered(self):
        """Live hover state of the video container (flat runtime data)."""
        try:
            from .. import hit_op

            for container in hit_op._container_data or []:
                if container.get("id") == self.video.id:
                    return bool(container.get("_hovered", False))
        except Exception:
            pass
        return False

    # ── icons / labels / fill ────────────────────────────────────────

    def _muted(self):
        if media_manager.get_source(self.video.id) is not None:
            return bool(self.controller.muted)
        return bool(getattr(self.video, "muted", False))  # pre-attach: YAML value

    def _apply_play_icons(self):
        paused = self.controller.paused or self.controller.ended
        self._show_icon(self.play_ic, self.play_img, paused)
        self._show_icon(self.pause_ic, self.pause_img, not paused)

    def _apply_mute_icons(self):
        muted = self._muted()
        self._show_icon(self.sound_ic, self.sound_img, not muted)
        self._show_icon(self.mute_ic, self.mute_img, muted)

    def _apply_fullscreen_icons(self, active=None):
        """Same display-swap pattern as play/mute: enter-fullscreen glyph
        while windowed, exit glyph while THIS video is fullscreen. *active*
        defaults to the live container.fullscreen (wire-time state)."""
        if active is None:
            active = bool(getattr(self.video, "fullscreen", False))
        self._show_icon(self.fs_ic, self.fs_img, not active)
        self._show_icon(self.exit_fs_ic, self.exit_fs_img, active)

    @staticmethod
    def _show_icon(wrap, img, visible):
        """Icon state swap - display FLEX/NONE on the stacked wrap (the
        collapse.py pattern; uppercase!) plus opacity 0/1 on the img child:
        display culls the container and zeroes the subtree boxes on the
        next layout sync, while the opacity keeps the image pass clean in
        the frames before that sync (and wherever a zeroed box would
        otherwise leave a stray min-clamped pixel outside scroll clips)."""
        if wrap is not None and wrap.style is not None:
            wrap.style.display = "FLEX" if visible else "NONE"
            wrap.mark_dirty()
        if img is not None and img.style is not None:
            img.style.opacity = 1.0 if visible else 0.0
            img.mark_dirty()

    def _sync_labels(self):
        self._set_label(self.time_label, format_time(self.controller.current_time))
        duration = self.controller.duration
        if duration and duration > 0:
            self._set_label(self.duration_label, format_time(duration))
            self._duration_known = True

    @staticmethod
    def _set_label(label, text):
        if label is None or label.text == text:
            return  # text relayout is not free - only touch real changes
        label.text = text
        label.mark_dirty()

    def _set_fill(self, frac):
        if self.fill is None:
            return
        # Integer percent: set_property parses "N%" with int() (fractional
        # values would raise), and 1% of a track is comfortably sub-scrub
        # resolution anyway.
        pct = int(round(max(0.0, min(1.0, frac)) * 100.0))
        if pct == self._last_fill_pct:
            return
        self._last_fill_pct = pct
        self.fill.set_property("width", f"{pct}%")  # marks dirty itself

    # ── lifecycle ────────────────────────────────────────────────────

    def release(self):
        """Detach everything that outlives the container tree."""
        self._dead = True
        self._dragging = False
        for event, fn in self._listeners:
            try:
                self.controller.off(event, fn)
            except Exception:
                pass
        self._listeners = []
        # Container lists die with the tree, but a same-tree rewire must
        # not stack a second fullscreen icon-flip handler - remove ours.
        try:
            self.video.on_fullscreen_change.remove(self._on_fullscreen_change)
        except (ValueError, AttributeError):
            pass
        try:
            self._mouse_state.unregister_callback(self._on_mouse)
        except Exception:
            pass
        if self._space_binding is not None:
            try:
                keys.unbind(self._space_binding)
            except Exception:
                pass
            self._space_binding = None
