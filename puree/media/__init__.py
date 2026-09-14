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
"""Puree media subsystem - animated/vector media on image elements.

MediaManager is the single owner of media playback: it matches media
assets (by file extension of the ``img:`` value) to their ImageInstance,
decodes through per-format sources (Rust core), advances clocks from the
render modal's TIMER tick and swaps ``instance.texture`` per frame.
Rendering itself stays in the existing image overlay pass
(img_op.draw_all_images) - no layout or container work per frame.

Mirrors TransitionManager's contract: ``tick()``/``has_active()`` gate
redraws so an idle (paused/ended/no-media) UI costs zero.

Import-safe outside Blender: bpy/gpu are only touched inside methods.
"""

import inspect
import os
import time

try:
    from ..log import get_logger

    logger = get_logger(__name__)
except Exception:  # pragma: no cover - outside the package/Blender
    import logging

    logger = logging.getLogger(__name__)

from .decoders import MEDIA_EXTENSIONS, get_factory

__all__ = ["MediaManager", "media_manager", "MEDIA_EXTENSIONS", "is_media_name"]


def is_media_name(image_name):
    """True when an ``img:`` value points at a media format (by extension)."""
    if not image_name:
        return False
    return os.path.splitext(str(image_name))[1].lower() in MEDIA_EXTENSIONS


class MediaManager:
    """Singleton owning every live MediaSource, keyed by container id."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._sources = {}
            cls._instance._controllers = {}
            cls._instance._visibility_filter = None
        return cls._instance

    # ── visibility gating (FULLSCREEN_PLAN Phase A) ──────────────────

    def set_visibility_filter(self, predicate):
        """Install a ``predicate(container_id) -> bool`` consulted per tick;
        sources whose id reads False skip their frame pull/upload for that
        tick (their clocks are wall-time based, so playback position keeps
        advancing - browser parity: hidden media keep playing, silently for
        the GPU). ``None`` (the default) clears the filter = every source
        ticks, the exact pre-fullscreen behavior. Installed/cleared by
        puree.fullscreen on enter/exit and cleared on shutdown()."""
        self._visibility_filter = predicate

    # ── lifecycle ────────────────────────────────────────────────────

    def attach(self, image_blocks, image_instances):
        """Match media blocks to their ImageInstance and (re)build sources.

        Called from render.XWZ_OT_start_ui.execute() right after the image
        instances are created (and from the hot-reload resync). Reconciles:
        sources whose (container, asset, instance) are unchanged keep their
        clock (playback position survives YAML/SCSS hot reloads); everything
        else is released and rebuilt. Decode results are cached per file, so
        rebuilding a source never re-decodes.
        """
        from ..img_op import image_manager

        previous = self._sources
        self._sources = {}

        for instance in image_instances:
            container_id = instance.container_id
            block = image_blocks.get(container_id) if image_blocks else None
            if not block:
                continue
            image_name = str(block.get("image_name", "")).replace("\\", "/")
            factory = get_factory(os.path.splitext(image_name)[1])
            if factory is None:
                continue
            path = image_manager.images.get(image_name)
            if not path:
                # Unknown asset - ImageManager.resolve() already logged the
                # actionable (did-you-mean) error for this name.
                continue

            kept = previous.pop(container_id, None)
            keep = (
                kept is not None
                and not kept.released
                and kept.instance is instance
                and kept.image_name == image_name
                and kept.path == os.path.abspath(path)
            )
            if keep:
                # Sources with playback attributes (video) also compare the
                # block: a YAML change to loop/muted/... rebuilds the source.
                matcher = getattr(kept, "matches_block", None)
                if matcher is not None:
                    try:
                        keep = bool(matcher(block))
                    except Exception:
                        keep = False
            if keep:
                self._sources[container_id] = kept
                continue
            if kept is not None:
                kept.release()

            try:
                self._sources[container_id] = self._build_source(
                    factory, container_id, image_name, path, instance, block
                )
            except Exception:
                logger.error(f"Failed to attach media source for '{image_name}' ({container_id})", exc_info=True)

        # Elements that no longer exist (or lost their media attribute)
        for stale in previous.values():
            try:
                stale.release()
            except Exception:
                logger.debug("Media source release failed", exc_info=True)

        # Drop listener-less controllers whose media disappeared, and EVERY
        # controller whose id resolved to a clock-less source (static media -
        # SVG): those have no playback surface to pump and can only exist
        # when a script touched `.media` before attach() ran (their events
        # can never fire, so listeners don't keep them alive). Script-held
        # controller references keep working either way - they re-resolve
        # their source through the manager on every access.
        def _controller_stale(cid, controller):
            source = self._sources.get(cid)
            if source is None:
                return not controller.has_listeners()
            return getattr(source, "clock", None) is None

        for cid in [cid for cid, c in self._controllers.items() if _controller_stale(cid, c)]:
            self._controllers.pop(cid, None)

        if self._sources:
            logger.info(f"Media attached: {len(self._sources)} source(s)")

    @staticmethod
    def _build_source(factory, container_id, image_name, path, instance, block):
        """Instantiate a source; factories that declare a ``block`` parameter
        (VideoSource - playback attrs ride the image block) receive it, plain
        Phase 1/2-style 4-arg factories are called unchanged."""
        try:
            accepts_block = "block" in inspect.signature(factory).parameters
        except (TypeError, ValueError):  # exotic callables
            accepts_block = False
        if accepts_block:
            return factory(container_id, image_name, path, instance, block=block)
        return factory(container_id, image_name, path, instance)

    def tick(self, now=None):
        """Advance every source; True when any visible texture changed.

        Runs on each render-modal TIMER tick, after the scroll/dirty-sync
        instance updates and before the needs_redraw computation. A UI with
        no media returns immediately; paused/ended sources only pay one
        texture identity check each.
        """
        sources = self._sources
        if not sources:
            return False
        if now is None:
            now = time.monotonic()

        changed = False
        released = None
        visibility_filter = self._visibility_filter
        for container_id, source in sources.items():
            if visibility_filter is not None:
                try:
                    visible = bool(visibility_filter(container_id))
                except Exception:
                    visible = True
                if not visible:
                    # Hidden while fullscreen: skip the frame pull/upload
                    # entirely (the wall-time clock keeps running; the next
                    # visible tick catches up + the texture self-heal runs).
                    continue
            try:
                if source.tick(now):
                    changed = True
            except Exception:
                logger.error(f"Media tick failed for {container_id} - releasing source", exc_info=True)
                try:
                    source.release()
                except Exception:
                    pass
            if source.released:
                if released is None:
                    released = []
                released.append(container_id)
        if released:
            for container_id in released:
                sources.pop(container_id, None)

        # Media events (play/pause/ended/seeked/timeupdate/error) fire here,
        # on the main thread, after the sources advanced.
        if self._controllers:
            for controller in list(self._controllers.values()):
                try:
                    controller._pump(now)
                except Exception:
                    logger.error("Media controller event pump failed", exc_info=True)
        return changed

    def has_active(self, now=None):
        """True while any source is playing (mirrors transitions.has_active)."""
        if not self._sources:
            return False
        return any(source.is_active(now) for source in self._sources.values())

    # ── container.media (MEDIA_PLAN section 6.3) ─────────────────────

    def get_source(self, container_id):
        """The live MediaSource for a container id, or None."""
        return self._sources.get(container_id)

    def controller_for(self, container_id):
        """The MediaController bound to *container_id* (created lazily).

        Controllers are id-bound and resolve their source through the
        manager on every access, so a controller obtained before attach()
        (scripts run first) or across hot reloads stays valid. Like
        puree.timers, ``on()`` listeners persist across YAML/SCSS hot
        reloads while the source survives - long-lived scripts should use
        ``off()`` or the stale-root guard pattern when re-registering.

        Raises AttributeError (the actionable has-no-media-source message)
        when the id resolves to a live but clock-less source - static media
        (SVG) has no playback controller (see MediaController.__init__).
        """
        from .controller import MediaController

        controller = self._controllers.get(container_id)
        if controller is None:
            controller = MediaController(container_id, self)
            self._controllers[container_id] = controller
        return controller

    def shutdown(self):
        """Stop playback and free GPU resources. Idempotent - called from UI
        stop/restart, render unregister and addon unregister; decoded CPU
        frames stay cached so a restart never re-decodes. Source release
        joins every decoder thread (videos), so no threads leak past here."""
        if self._sources:
            for source in self._sources.values():
                try:
                    source.release()
                except Exception:
                    logger.debug("Media source release failed during shutdown", exc_info=True)
            self._sources.clear()
        self._controllers.clear()
        # Belt: fullscreen force_exit clears this on every teardown path,
        # but a fresh session must never start visibility-gated.
        self._visibility_filter = None
        try:
            from .decoders import gif as gif_decoder

            gif_decoder.release_gpu_textures()
        except Exception:
            logger.debug("Media GPU cache release failed during shutdown", exc_info=True)

    def reset(self):
        """Alias of shutdown() - kept for call-site clarity on UI restart."""
        self.shutdown()


media_manager = MediaManager()
