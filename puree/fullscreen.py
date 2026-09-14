# Created by XWZ
# ◕‿◕ Distributed for free at:
# https://github.com/nicolaiprodromov/puree
"""Fullscreen presentation mode (FULLSCREEN_PLAN, Phase A - engine mode).

Region-only "theater mode": ONE container at a time fills the editor
region Puree draws in. Implemented as a renderer short-circuit (plan
decision 2), NOT a document mutation - the main UI tree, its layout
nodes, flat dicts, blocks and data textures are never touched while the
mode is active, so exit is instant and the main tree stays byte-identical.

On enter (and again on region resize / dirty-sync while active) the
manager builds a PRIVATE pass for the fullscreen subtree:

- layout:   UI.compute_subtree_layout() lays the subtree out as its own
            Taffy root pinned to the region box (same construction path
            as the main document via parser.make_layout_node_builder);
            the temporary node tree is dropped after harvesting boxes.
- flat:     UI._flatten_containers() produces a private flat dict list
            (the node_flat_abs shape) - never written to parser globals.
- blocks:   TextExtractor/ImageExtractor re-run against the private
            layout (crisp text, correctly stretched media boxes).
- gpu:      RenderPipeline.set_fullscreen_pass() packs the private list
            into dedicated fullscreen data textures with the exact
            Phase 5 main/overlay split + flat->LOCAL hover index remap.
- media:    the subtree's Image/media instances are retargeted to the
            private geometry (scroll clips cleared - the private layout
            escapes ancestor clipping by design); their enter-time
            geometry is snapshotted and restored exactly on exit.
- hits:     the Rust HitDetector is hot-loaded with ONLY the private
            subtree rects (the same load_containers hot-sync scrolling
            uses); the full main set is restored on exit. Hit results
            keep applying by container id to the shared main dicts, so
            hover/click/handlers on subtree containers keep working.
- input:    InputRouter treats the whole region as over-UI (the backdrop
            IS drawn there) and ESC is bound through puree.keyboard.
            NOTE: key dispatch runs inside the text-input KeyboardHandler
            modal, so ESC (like the controls SPACE binding) only fires in
            UIs that contain at least one text input - the Phase B controls
            button is the universal exit affordance.
- uploads:  MediaManager gets a visibility filter so non-subtree media
            skip their per-tick frame uploads (their clocks are wall-time
            based and keep running - exiting resumes at the live position,
            browser parity for "other media keep playing").

While active the hidden main tree keeps ticking (transitions, dirty-sync,
media clocks); the render modal calls on_render_tick() AFTER the
dirty-sync/scroll/resize instance updates so the private pass is
re-asserted the same TIMER tick that clobbered it (nothing draws in
between). Known Phase A limitation: transition INTERPOLATION mutates the
main flat dicts, which the private pack does not read per-frame - inside
fullscreen, animated values (e.g. the controls-bar fade) land at their
settle value on the next dirty-sync repack instead of animating.

force_exit() is wired at every teardown/reload site that already calls
MediaManager.shutdown() + unwire_video_controls() (render cancel/stop/
unregister, addon unregister, the reparse operator) - the lifecycle trio
stays together and everything here is idempotent.

The public surface (Phase B) lives on Container and delegates here:
container.request_fullscreen()/exit_fullscreen()/fullscreen call
enter()/exit()/active_id; the controls fullscreen button toggles through
that API and controls seek math reads box_abs(track_id) while active.

Events (Phase B): enter()/exit() fire the container's
on_fullscreen_change handler list as ``fn(container, is_fullscreen)`` -
swap fires False for the old element then True for the new one, ESC and
force_exit fire False. Events fire synchronously on the calling (main)
thread AFTER the mode change is fully committed, so handlers reading
container.fullscreen/active_id see the new state; handler exceptions are
logged and swallowed (the media controller listener contract). Media
containers additionally get the ``media.on("fullscreenchange", fn)``
alias - the container list fires FIRST, then the media event (see
_fire_fullscreen_change). Re-entering the already-active element is a
no-op success and fires nothing (no state change).

Import-safe outside Blender: bpy/gpu and every engine module are only
imported inside methods (the established media/controls convention).
"""

from .log import get_logger

logger = get_logger(__name__)

__all__ = ["FullscreenManager", "fullscreen_manager"]


class FullscreenManager:
    """Singleton owning the fullscreen presentation state (one element at a
    time; entering while active swaps via exit-then-enter). Same lifecycle
    discipline as MediaManager: module-level instance, idempotent teardown."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._reset_state()
        return cls._instance

    def _reset_state(self):
        self._active_id = None
        self._container = None
        self._ui = None
        self._region = None  # (w, h) the current private layout was computed for
        self._flat = []  # private flat dict list (subtree, z-sorted)
        self._boxes = {}  # id -> private border box (node_flat_abs shape)
        self._content_boxes = {}  # id -> private content box
        self._text_blocks = {}  # private text blocks (subtree)
        self._image_blocks = {}  # private image blocks (subtree)
        self._subtree_ids = set()
        self._saved_images = []  # [(instance, snapshot), ...] enter-time geometry
        self._saved_texts = []
        self._esc_binding = None

    # -- public state ----------------------------------------------------

    @property
    def active_id(self):
        """Container id of the fullscreen element, or None."""
        return self._active_id

    def is_active(self):
        return self._active_id is not None

    def visible_instance_ids(self):
        """Draw filter for the image/text/text-input passes: the active
        subtree's container ids, or None when inactive (= draw everything).
        The draw loops treat None as the zero-cost pre-fullscreen path."""
        if self._active_id is None:
            return None
        return self._subtree_ids

    def box_abs(self, container_id):
        """The PRIVATE border box of a subtree container while active
        (Phase B: controls seek math must read the fullscreen track box
        from here instead of parser.node_flat_abs). None when inactive or
        outside the subtree."""
        if self._active_id is None:
            return None
        return self._boxes.get(container_id)

    # -- mode switches -----------------------------------------------------

    def enter(self, container_id):
        """Make *container_id* the fullscreen element. Returns True on
        success. Entering while another element is active swaps
        (exit-then-enter; the Phase B events fire per element)."""
        ui = self._resolve_ui()
        if ui is None:
            logger.warning("Fullscreen enter refused: no parsed UI (start the UI first)")
            return False
        container = self._resolve_container(ui, container_id)
        if container is None:
            logger.warning(f"Fullscreen enter refused: container '{container_id}' not found")
            return False

        if self._active_id is not None:
            if container.id == self._active_id:
                return True  # already fullscreen
            self.exit()  # swap semantics: exit-then-enter

        region = self._region_size()
        if region is None:
            logger.warning("Fullscreen enter refused: no region size available")
            return False

        try:
            self._build_private_pass(ui, container, region)
        except Exception:
            logger.error(f"Fullscreen private pass failed for '{container.id}'", exc_info=True)
            self._reset_state()
            return False

        self._active_id = container.id
        self._container = container
        self._ui = ui

        self._snapshot_instances()
        self._apply_private_pass()

        self._bind_esc()
        self._set_input_capture(True)
        self._set_media_filter(True)
        self._request_redraw()
        self._fire_fullscreen_change(container, container.id, True)
        logger.info(f"Fullscreen enter: '{container.id}' at {region[0]}x{region[1]}")
        return True

    def exit(self):
        """Leave fullscreen: drop all private data and restore the saved
        instance geometry, hit set and input state. Returns True when a
        fullscreen element was active. Safe to call when idle; every
        teardown step is individually guarded so one failure cannot leak
        the others."""
        if self._active_id is None:
            return False
        exited_id = self._active_id
        exited_container = self._container  # kept past _reset_state for the event

        self._unbind_esc()
        self._set_input_capture(False)
        self._set_media_filter(False)

        pipeline = self._pipeline()
        if pipeline is not None:
            try:
                pipeline.clear_fullscreen_pass()
            except Exception:
                logger.debug("Fullscreen pass clear failed", exc_info=True)

        self._restore_instances()
        self._restore_hit_containers()

        self._reset_state()
        self._request_redraw()
        # Fired AFTER the state reset so handlers reading container.fullscreen
        # / active_id see the committed (inactive) state. Covers every exit
        # path: exit_fullscreen(), the controls button, ESC, swap (enter()
        # calls exit() first - False for the old element precedes True for
        # the new one) and force_exit (hot reload/reparse/teardown).
        self._fire_fullscreen_change(exited_container, exited_id, False)
        logger.info(f"Fullscreen exit: '{exited_id}'")
        return True

    def toggle(self, container_id):
        """exit() when *container_id* is the active element, enter() it
        otherwise (incl. the swap-from-another-element case). Returns the
        resulting is_active() for the id."""
        if self._active_id is not None:
            ui = self._resolve_ui()
            container = self._resolve_container(ui, container_id) if ui else None
            resolved_id = container.id if container is not None else container_id
            if resolved_id == self._active_id:
                self.exit()
                return False
        return self.enter(container_id)

    def force_exit(self):
        """Teardown/reload reset - never raises, safe when idle. Wired at
        every MediaManager.shutdown() + unwire_video_controls() site
        (render cancel/stop_ui/unregister, addon unregister, reparse)."""
        if self._active_id is None:
            return
        exited_id = self._active_id
        exited_container = self._container
        try:
            self.exit()  # fires on_fullscreen_change(False) itself
        except Exception:
            logger.error("Fullscreen force-exit failed - resetting state", exc_info=True)
            try:
                self._unbind_esc()
            except Exception:
                pass
            try:
                self._set_input_capture(False)
            except Exception:
                pass
            try:
                self._set_media_filter(False)
            except Exception:
                pass
            self._reset_state()
            # exit() raised before it could fire - the False event still
            # belongs to every teardown path (fire helper never raises).
            self._fire_fullscreen_change(exited_container, exited_id, False)

    # -- public events (Phase B) ---------------------------------------------

    @staticmethod
    def _fire_fullscreen_change(container, container_id, is_fullscreen):
        """Fire the fullscreen-change events for one element. Never raises.

        Ordering contract (documented in API.md): the container's
        on_fullscreen_change handler list fires FIRST as
        ``fn(container, is_fullscreen)``, THEN the media alias - media
        containers with an EXISTING MediaController get 'fullscreenchange'
        emitted through it (``fn(media)``; read ``container.fullscreen``
        for the state). Only controllers already in MediaManager's registry
        are notified - a controller is never created here, so generic
        (non-media) fullscreen containers add nothing to the registry.
        Runs synchronously on the calling (main) thread; per-handler
        exceptions are logged and swallowed (MediaController._emit pattern).
        """
        if container is not None:
            for fn in list(getattr(container, "on_fullscreen_change", None) or ()):
                try:
                    fn(container, is_fullscreen)
                except Exception:
                    logger.error(f"on_fullscreen_change handler failed for '{container_id}'", exc_info=True)
        try:
            from .media import media_manager

            controller = media_manager._controllers.get(container_id)
        except Exception:
            controller = None
        if controller is not None:
            try:
                controller._emit("fullscreenchange")
            except Exception:
                logger.error(f"media 'fullscreenchange' emit failed for '{container_id}'", exc_info=True)

    # -- render-modal integration ------------------------------------------

    def on_render_tick(self, dirty_synced=False, size_changed=False):
        """Called from the render modal's TIMER branch AFTER the
        dirty-sync/scroll/resize update loops (they retarget instances and
        the hit detector from MAIN-tree blocks). Recomputes the private
        pass when the region changed or the tree was dirty-synced, and
        re-asserts instance geometry + the hit set. Returns True when work
        was done (folds into needs_redraw). No-op when inactive."""
        if self._active_id is None:
            return False
        region = self._region_size()
        region_changed = region is not None and region != self._region
        if not (dirty_synced or size_changed or region_changed):
            return False
        return self.refresh()

    def refresh(self):
        """Recompute the private layout/blocks/textures at the current
        region size and re-assert instance geometry + the hit set. The
        enter-time snapshots are NOT retaken - exit always restores the
        pre-fullscreen geometry."""
        if self._active_id is None:
            return False
        region = self._region_size() or self._region
        try:
            self._build_private_pass(self._ui, self._container, region)
            self._apply_private_pass()
        except Exception:
            logger.error("Fullscreen refresh failed - force-exiting", exc_info=True)
            self.force_exit()
        return True

    # -- private pass construction ------------------------------------------

    def _build_private_pass(self, ui, container, region):
        """Compute the private subtree layout at *region* and derive the
        flat list + text/image blocks from it. Pure: main-tree layout
        nodes, globals and blocks are untouched."""
        from .extract_images import ImageExtractor
        from .extract_text import TextExtractor

        boxes, content_boxes = ui.compute_subtree_layout(container, region)
        flat = ui._flatten_containers(container, boxes)
        text_blocks = TextExtractor(ui, flat, root=container, content_boxes=content_boxes).text_blocks
        image_blocks = ImageExtractor(ui, flat, root=container, content_boxes=content_boxes).image_blocks

        self._boxes = boxes
        self._content_boxes = content_boxes
        self._flat = flat
        self._text_blocks = text_blocks
        self._image_blocks = image_blocks
        self._subtree_ids = set(boxes.keys())
        self._region = tuple(region)

    def _snapshot_instances(self):
        """Save the subtree instances' MAIN-tree geometry (pos/size/mask/
        clip) so exit restores it exactly. Taken once per enter()."""
        from . import img_op, text_op

        def _copy(value):
            return list(value) if value is not None else None

        self._saved_images = []
        for instance in img_op._image_instances:
            if instance.container_id in self._subtree_ids:
                self._saved_images.append(
                    (
                        instance,
                        {
                            "position": _copy(instance.position),
                            "size": _copy(instance.size),
                            "mask": _copy(instance.mask),
                            "clip": _copy(instance.clip),
                        },
                    )
                )

        self._saved_texts = []
        for instance in text_op._text_instances:
            if instance.container_id in self._subtree_ids:
                self._saved_texts.append(
                    (
                        instance,
                        {
                            "position": _copy(instance.position),
                            "mask": _copy(instance.mask),
                            "clip": _copy(instance.clip),
                        },
                    )
                )

    def _apply_private_pass(self):
        """Push the private pass to the GPU (fullscreen data textures),
        retarget the subtree instances to the private geometry and hot-load
        the hit detector with ONLY the subtree rects."""
        pipeline = self._pipeline()
        if pipeline is not None:
            try:
                pipeline.set_fullscreen_pass(self._flat)
            except Exception:
                logger.error("Fullscreen data texture build failed", exc_info=True)

        from . import img_op, text_op

        for instance in img_op._image_instances:
            block = self._image_blocks.get(instance.container_id)
            if block is None or instance.container_id not in self._subtree_ids:
                continue
            # Private geometry has no scroll offsets - clear the scroll clip
            # (update_all(clip=None) would KEEP it; assign directly, the
            # hot_reload.py convention). image_name is deliberately NOT
            # passed: it would reset media textures to the ImageManager stub
            # for a frame (MediaManager only self-heals on the next tick).
            instance.clip = None
            instance.update_all(
                pos=[block["x_pos"], block["y_pos"]],
                size=[block["width"], block["height"]],
                mask=[block["mask_x"], block["mask_y"], block["mask_width"], block["mask_height"]],
                aspect_ratio=block["aspect_ratio"],
                align_h=block.get("align_h", "LEFT").upper(),
                align_v=block.get("align_v", "TOP").upper(),
                opacity=block.get("opacity", 1.0),
            )

        for instance in text_op._text_instances:
            block = self._text_blocks.get(instance.container_id)
            if block is None or instance.container_id not in self._subtree_ids:
                continue
            instance.clip = None
            instance.update_all(
                text=block["text"],
                font_name=block["font"],
                size=block["font_size"],
                pos=[block["text_x"], block["text_y"]],
                color=block["color"],
                mask=[block["mask_x"], block["mask_y"], block["mask_width"], block["mask_height"]],
                align_h=block.get("align_h", "LEFT").upper(),
                align_v=block.get("align_v", "CENTER").upper(),
                white_space=block.get("white_space", "NORMAL"),
                text_overflow=block.get("text_overflow", "CLIP"),
                overflow_wrap=block.get("overflow_wrap", "NORMAL"),
                word_break=block.get("word_break", "NORMAL"),
            )

        self._load_hit_containers(self._flat)

    def _restore_instances(self):
        """Put the enter-time geometry back on every retargeted instance
        (direct attribute assignment - exact values, no update_all
        clamping/keep-on-None semantics)."""
        try:
            for instance, snap in self._saved_images:
                instance.position = list(snap["position"]) if snap["position"] is not None else None
                instance.size = list(snap["size"]) if snap["size"] is not None else None
                instance.mask = list(snap["mask"]) if snap["mask"] is not None else None
                instance.clip = list(snap["clip"]) if snap["clip"] is not None else None
            for instance, snap in self._saved_texts:
                instance.position = list(snap["position"]) if snap["position"] is not None else None
                instance.mask = list(snap["mask"]) if snap["mask"] is not None else None
                instance.clip = list(snap["clip"]) if snap["clip"] is not None else None
        except Exception:
            logger.error("Fullscreen instance restore failed", exc_info=True)

    # -- engine plumbing -----------------------------------------------------

    @staticmethod
    def _resolve_ui():
        try:
            from . import parser_op

            return parser_op.XWZ_UI
        except Exception:
            logger.debug("Fullscreen: parser_op unavailable", exc_info=True)
            return None

    @staticmethod
    def _resolve_container(ui, container_id):
        """Exact-id walk first (the manager API is id-exact), falling back
        to the suffix-matching Container.get_by_id scripts already use."""
        root = ui.theme.root

        def walk(container):
            if container.id == container_id:
                return container
            for child in container.children:
                found = walk(child)
                if found is not None:
                    return found
            return None

        exact = walk(root)
        if exact is not None:
            return exact
        try:
            return ui.get_by_id(container_id)
        except Exception:
            return None

    @staticmethod
    def _pipeline():
        try:
            from . import render

            return render._render_data
        except Exception:
            return None

    def _region_size(self):
        """Region dims the way render.py gets them: the live pipeline's
        region_size, else a space_config area/region scan."""
        pipeline = self._pipeline()
        if pipeline is not None:
            size = getattr(pipeline, "region_size", None)
            if size and size[0] > 1 and size[1] > 1:
                return (int(size[0]), int(size[1]))
        try:
            from .space_config import find_target_area_and_region

            _area, region = find_target_area_and_region()
            if region is not None:
                return (int(region.width), int(region.height))
        except Exception:
            logger.debug("Fullscreen: region lookup failed", exc_info=True)
        return None

    def _load_hit_containers(self, containers):
        try:
            from . import hit_op

            detector = getattr(hit_op, "_native_detector", None)
            if detector and containers:
                detector.load_containers(containers)
        except Exception:
            logger.debug("Fullscreen hit-set load failed", exc_info=True)

    def _restore_hit_containers(self):
        """Reload the detector with the live full list (hit_op._container_data
        carries the scroll-adjusted positions the main tree is showing)."""
        try:
            from . import hit_op

            detector = getattr(hit_op, "_native_detector", None)
            if detector and hit_op._container_data:
                detector.load_containers(hit_op._container_data)
        except Exception:
            logger.debug("Fullscreen hit-set restore failed", exc_info=True)

    def _bind_esc(self):
        if self._esc_binding is not None:
            return
        try:
            from .keyboard import keys

            self._esc_binding = keys.bind("ESC", self._on_esc)
        except Exception:
            logger.debug("Fullscreen ESC bind failed", exc_info=True)
            self._esc_binding = None

    def _unbind_esc(self):
        if self._esc_binding is None:
            return
        try:
            from .keyboard import keys

            keys.unbind(self._esc_binding)
        except Exception:
            logger.debug("Fullscreen ESC unbind failed", exc_info=True)
        self._esc_binding = None

    def _on_esc(self):
        self.exit()

    def _set_input_capture(self, active):
        try:
            from .input_router import input_router

            input_router.set_fullscreen_capture(active)
        except Exception:
            logger.debug("Fullscreen input capture toggle failed", exc_info=True)

    def _set_media_filter(self, active):
        try:
            from .media import media_manager

            media_manager.set_visibility_filter(self._media_visible if active else None)
        except Exception:
            logger.debug("Fullscreen media filter toggle failed", exc_info=True)

    def _media_visible(self, container_id):
        """MediaManager visibility predicate while active: only subtree
        media upload frames; hidden clocks keep running (wall time)."""
        return container_id in self._subtree_ids

    def _request_redraw(self):
        """Entering/exiting/refreshing must repaint immediately: mirror the
        hot-reload pattern (pipeline flags) + tag the target areas."""
        pipeline = self._pipeline()
        if pipeline is not None:
            try:
                pipeline.needs_texture_update = True
                pipeline.force_initial_draw = True
            except Exception:
                pass
        try:
            import bpy

            from .space_config import get_target_space

            target_space = get_target_space()
            if target_space:
                for area in bpy.context.screen.areas:
                    if area.type == target_space:
                        area.tag_redraw()
        except Exception:
            pass


fullscreen_manager = FullscreenManager()
