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
"""Unit tests for puree.media.controller (container.media) - no bpy needed.

``puree/`` is mounted as a namespace-style package: a bare module object
with ``__path__`` set, so submodules load from disk WITHOUT executing the
real ``puree/__init__.py`` (which imports bpy). The media package and
``components.container`` are import-safe that way.

The controller is exercised against a fake source with an injectable
clock (the real MediaClock with a controlled ``time_fn``), pumping events
manually with controlled ``now`` values - exactly what MediaManager.tick
does on the main thread.
"""

import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _ensure_puree_package():
    pkg = sys.modules.get("puree")
    if pkg is None:
        pkg = types.ModuleType("puree")
        pkg.__path__ = [str(REPO_ROOT / "puree")]
        sys.modules["puree"] = pkg
    return pkg


_ensure_puree_package()

from puree.components.container import Container, coerce_bool, coerce_float  # noqa: E402
from puree.media import media_manager  # noqa: E402
from puree.media.clock import MediaClock  # noqa: E402
from puree.media.controller import MEDIA_EVENTS, MediaController  # noqa: E402

# ── harness ──────────────────────────────────────────────────────────


def make_clock(duration=10.0, loop=False, rate=1.0):
    """MediaClock with an injected, controllable time source (starts at 0)."""
    state = {"now": 0.0}
    clock = MediaClock(duration=duration, loop=loop, playback_rate=rate, time_fn=lambda: state["now"])
    return clock, state


class FakeSource:
    """Minimal source: a clock only - exercises every controller fallback
    (the same shape GifSource presents for play/pause/loop/rate/muted)."""

    def __init__(self, clock, ready_state="ready"):
        self.clock = clock
        self.ready_state = ready_state
        self.released = False
        self.instance = object()


class DelegatingSource(FakeSource):
    """Source implementing the full optional surface (VideoSource shape)."""

    def __init__(self, clock, ready_state="ready"):
        super().__init__(clock, ready_state)
        self.calls = []
        self.muted = False
        self.volume = 1.0
        self.seeking = False
        self.duration = None

    def play(self):
        self.calls.append("play")
        self.clock.play()

    def pause(self):
        self.calls.append("pause")
        self.clock.pause()

    def seek(self, seconds):
        self.calls.append(("seek", seconds))
        self.clock.seek(seconds)

    def stop(self):
        self.calls.append("stop")
        self.clock.pause()
        self.clock.seek(0.0)

    def set_muted(self, muted):
        self.calls.append(("set_muted", muted))
        self.muted = bool(muted)

    def set_volume(self, volume):
        self.calls.append(("set_volume", volume))
        self.volume = float(volume)

    def set_playback_rate(self, rate):
        self.calls.append(("set_playback_rate", rate))
        self.clock.playback_rate = rate

    def set_loop(self, loop):
        self.calls.append(("set_loop", loop))
        self.clock.loop = bool(loop)


class FakeManager:
    def __init__(self):
        self.sources = {}

    def get_source(self, container_id):
        return self.sources.get(container_id)


def make_controller(source=None, container_id="vid"):
    manager = FakeManager()
    if source is not None:
        manager.sources[container_id] = source
    return MediaController(container_id, manager), manager


def record_events(controller, *events):
    fired = {event: [] for event in (events or MEDIA_EVENTS)}
    for event in fired:
        controller.on(event, lambda m, e=event: fired[e].append(m.current_time))
    return fired


# ── no source yet (scripts run before MediaManager.attach) ───────────


def test_controls_noop_without_source():
    controller, _ = make_controller(None)
    controller.play()
    controller.pause()
    controller.toggle()
    controller.seek(3.0)
    controller.stop()
    controller.muted = True
    controller.volume = 0.5
    controller.playback_rate = 2.0
    controller.loop = True
    controller._pump(now=0.0)  # nothing to pump - must not raise


def test_properties_default_without_source():
    controller, _ = make_controller(None)
    assert controller.current_time == 0.0
    assert controller.duration is None
    assert controller.paused is True
    assert controller.ended is False
    assert controller.loop is False
    assert controller.muted is False
    assert controller.volume == 1.0
    assert controller.playback_rate == 1.0
    assert controller.ready_state == "none"


def test_on_rejects_unknown_event():
    controller, _ = make_controller(None)
    with pytest.raises(ValueError):
        controller.on("loadedmetadata", lambda m: None)


# ── clock-fallback transport (GifSource shape) ───────────────────────


def test_play_pause_toggle_via_clock():
    clock, state = make_clock()
    controller, _ = make_controller(FakeSource(clock))
    assert controller.paused
    controller.play()
    assert not controller.paused and not clock.paused
    state["now"] = 2.0
    assert controller.current_time == pytest.approx(2.0)
    controller.pause()
    assert controller.paused
    controller.toggle()
    assert not controller.paused
    controller.toggle()
    assert controller.paused


def test_seek_and_stop_via_clock():
    clock, state = make_clock()
    controller, _ = make_controller(FakeSource(clock))
    controller.play()
    state["now"] = 4.0
    controller.seek(7.5)
    assert controller.current_time == pytest.approx(7.5)
    controller.stop()
    assert controller.paused
    assert controller.current_time == 0.0


def test_play_after_ended_replays_from_zero():
    clock, state = make_clock(duration=10.0, loop=False)
    controller, _ = make_controller(FakeSource(clock))
    controller.play()
    state["now"] = 11.0
    assert controller.ended
    controller.play()
    assert not controller.ended
    assert controller.current_time == pytest.approx(0.0)


def test_duration_none_until_known():
    clock, _ = make_clock(duration=0.0)
    controller, _ = make_controller(FakeSource(clock))
    assert controller.duration is None
    clock2, _ = make_clock(duration=12.5)
    controller2, _ = make_controller(FakeSource(clock2))
    assert controller2.duration == pytest.approx(12.5)


def test_muted_volume_rate_fallback_store_on_source():
    clock, _ = make_clock()
    source = FakeSource(clock)
    controller, _ = make_controller(source)
    controller.muted = "true"  # scripts may pass anything - bool() coercion
    assert source.muted is True and controller.muted is True
    controller.volume = 0.25
    assert source.volume == pytest.approx(0.25) and controller.volume == pytest.approx(0.25)
    controller.playback_rate = 2.0
    assert clock.playback_rate == pytest.approx(2.0)
    controller.loop = True
    assert clock.loop is True


# ── delegating transport (VideoSource shape) ─────────────────────────


def test_delegates_to_source_methods():
    clock, _ = make_clock()
    source = DelegatingSource(clock)
    controller, _ = make_controller(source)
    controller.play()
    controller.pause()
    controller.seek(3.0)
    controller.stop()
    controller.muted = True
    controller.volume = 0.5
    controller.playback_rate = 1.5
    controller.loop = True
    names = [c if isinstance(c, str) else c[0] for c in source.calls]
    assert names == ["play", "pause", "seek", "stop", "set_muted", "set_volume", "set_playback_rate", "set_loop"]


def test_duration_property_delegates():
    clock, _ = make_clock(duration=99.0)  # clock says 99...
    source = DelegatingSource(clock)
    source.duration = None  # ...but the source's own metadata wins
    controller, _ = make_controller(source)
    assert controller.duration is None
    source.duration = 45.5
    assert controller.duration == pytest.approx(45.5)


def test_ready_state_reflects_source():
    clock, _ = make_clock()
    source = FakeSource(clock, ready_state="metadata")
    controller, _ = make_controller(source)
    assert controller.ready_state == "metadata"
    source.ready_state = "error"
    assert controller.ready_state == "error"


# ── events (pumped from MediaManager.tick on the main thread) ────────


def test_play_pause_events_edge_detected():
    clock, state = make_clock()
    controller, _ = make_controller(FakeSource(clock))
    fired = record_events(controller, "play", "pause")
    controller._pump(now=0.0)
    assert fired["play"] == [] and fired["pause"] == []  # baseline: no edges
    controller.play()
    controller._pump(now=0.01)
    assert len(fired["play"]) == 1
    controller._pump(now=0.02)
    assert len(fired["play"]) == 1  # no refire without an edge
    controller.pause()
    controller._pump(now=0.03)
    assert len(fired["pause"]) == 1


def test_no_spurious_play_when_subscribing_to_playing_source():
    clock, _ = make_clock()
    clock.play()
    controller, _ = make_controller(FakeSource(clock))  # baseline: playing
    fired = record_events(controller, "play")
    controller._pump(now=0.0)
    assert fired["play"] == []


def test_ended_event_fires_once():
    clock, state = make_clock(duration=10.0, loop=False)
    controller, _ = make_controller(FakeSource(clock))
    fired = record_events(controller, "ended")
    controller.play()
    controller._pump(now=0.0)
    state["now"] = 5.0
    controller._pump(now=5.0)
    assert fired["ended"] == []
    state["now"] = 10.5
    controller._pump(now=10.5)
    assert len(fired["ended"]) == 1
    assert fired["ended"][0] == pytest.approx(10.0)  # current_time clamps to duration
    controller._pump(now=10.6)
    assert len(fired["ended"]) == 1  # edge, not level


def test_looping_clock_never_ends():
    clock, state = make_clock(duration=10.0, loop=True)
    controller, _ = make_controller(FakeSource(clock))
    fired = record_events(controller, "ended")
    controller.play()
    state["now"] = 25.0
    controller._pump(now=25.0)
    assert fired["ended"] == []
    assert controller.current_time == pytest.approx(5.0)  # wrapped


def test_seeked_fires_after_controller_seek():
    clock, _ = make_clock()
    controller, _ = make_controller(FakeSource(clock))
    fired = record_events(controller, "seeked")
    controller._pump(now=0.0)
    assert fired["seeked"] == []
    controller.seek(4.0)
    controller._pump(now=0.1)
    assert fired["seeked"] == [pytest.approx(4.0)]
    controller._pump(now=0.2)
    assert len(fired["seeked"]) == 1  # consumed


def test_seeked_defers_while_source_reports_seeking():
    clock, _ = make_clock()
    source = DelegatingSource(clock)
    controller, _ = make_controller(source)
    fired = record_events(controller, "seeked")
    source.seeking = True
    controller.seek(4.0)
    controller._pump(now=0.1)
    assert fired["seeked"] == []  # decoder has not landed yet
    source.seeking = False
    controller._pump(now=0.2)
    assert len(fired["seeked"]) == 1


def test_timeupdate_throttled_at_250ms():
    clock, state = make_clock()
    controller, _ = make_controller(FakeSource(clock))
    fired = record_events(controller, "timeupdate")
    controller.play()
    for now in (0.0, 0.1, 0.2):
        state["now"] = now
        controller._pump(now=now)
    assert fired["timeupdate"] == []  # throttle window not reached
    state["now"] = 0.26
    controller._pump(now=0.26)
    assert len(fired["timeupdate"]) == 1
    for now in (0.3, 0.4, 0.5):
        state["now"] = now
        controller._pump(now=now)
    assert len(fired["timeupdate"]) == 1
    state["now"] = 0.52
    controller._pump(now=0.52)
    assert len(fired["timeupdate"]) == 2


def test_timeupdate_silent_while_paused():
    clock, state = make_clock()
    controller, _ = make_controller(FakeSource(clock))
    fired = record_events(controller, "timeupdate")
    for now in (0.5, 1.0, 2.0):
        controller._pump(now=now)
    assert fired["timeupdate"] == []


def test_error_event_on_ready_state_edge():
    clock, _ = make_clock()
    source = FakeSource(clock, ready_state="metadata")
    controller, _ = make_controller(source)
    fired = record_events(controller, "error")
    controller._pump(now=0.0)
    assert fired["error"] == []
    source.ready_state = "error"
    controller._pump(now=0.1)
    assert len(fired["error"]) == 1
    controller._pump(now=0.2)
    assert len(fired["error"]) == 1  # edge, not level


def test_off_unsubscribes_and_listener_errors_are_contained():
    clock, _ = make_clock()
    controller, _ = make_controller(FakeSource(clock))

    def boom(m):
        raise RuntimeError("listener bug")

    seen = []
    controller.on("play", boom)
    fn = controller.on("play", lambda m: seen.append(True))
    assert controller.has_listeners()
    controller.play()
    controller._pump(now=0.0)  # boom must not break the pump
    assert seen == [True]
    controller.off("play", boom)
    controller.off("play", fn)
    controller.off("play", fn)  # double-off is a no-op
    assert not controller.has_listeners()


# ── Container integration (.media property, attribute coercion) ──────


def test_container_media_attribute_defaults():
    c = Container()
    assert c.video == "" and c.poster == ""
    assert c.controls is False and c.autoplay is False and c.loop is False
    assert c.muted is False  # unmuted-by-default: YAML authors opt in explicitly
    assert c.volume == 1.0 and c.playback_rate == 1.0
    assert c.preload == "metadata"


def test_container_media_attribute_coercion():
    c = Container()
    c.autoplay = "true"  # component param substitution stringifies
    c.loop = "True"
    c.muted = 1
    c.controls = "false"
    c.volume = "0.5"
    c.playback_rate = "not-a-number"  # falls back to the attr default
    assert c.autoplay is True and c.loop is True and c.muted is True
    assert c.controls is False
    assert c.volume == pytest.approx(0.5)
    assert c.playback_rate == pytest.approx(1.0)


def test_coerce_helpers():
    assert coerce_bool("yes") is True and coerce_bool("off") is False
    assert coerce_bool("") is False and coerce_bool(None) is False
    assert coerce_bool("garbage", default=True) is True
    assert coerce_float("2.5") == pytest.approx(2.5)
    assert coerce_float(None, 7.0) == pytest.approx(7.0)


def test_container_media_raises_for_non_media_container():
    c = Container()
    c.id = "plain_box"
    with pytest.raises(AttributeError, match="has no media source"):
        _ = c.media


def test_container_media_resolves_controller_through_manager():
    c = Container()
    c.id = "unit_test_video_node"
    c.video = "clip.mp4"
    try:
        controller = c.media
        assert isinstance(controller, MediaController)
        assert controller.container_id == "unit_test_video_node"
        assert c.media is controller  # id-bound: same controller every access
        assert controller.ready_state == "none"  # no source attached yet
    finally:
        media_manager._controllers.pop("unit_test_video_node", None)


def test_container_media_accepts_gif_img():
    c = Container()
    c.id = "unit_test_gif_node"
    c.img = "spin.gif"
    try:
        assert isinstance(c.media, MediaController)
    finally:
        media_manager._controllers.pop("unit_test_gif_node", None)


def test_manager_controller_for_caches_per_id():
    a = media_manager.controller_for("unit_test_cache_a")
    b = media_manager.controller_for("unit_test_cache_a")
    other = media_manager.controller_for("unit_test_cache_b")
    try:
        assert a is b and a is not other
    finally:
        media_manager._controllers.pop("unit_test_cache_a", None)
        media_manager._controllers.pop("unit_test_cache_b", None)


# ── clock-less (static, SVG-like) sources — release-gate regression ──
# A controller obtained PRE-attach (scripts run first) whose container id
# later resolves to a static source used to raise AttributeError('clock')
# from every MediaManager.tick pump (logged error spam at tick rate).


class ClocklessSource:
    """SvgSource shape: a live source with NO ``clock`` attribute (static
    media has no playback surface - the controller contract requires one)."""

    kind = "svg"

    def __init__(self):
        self.released = False
        self.instance = object()
        self.image_name = "logo.svg"
        self.path = "assets/logo.svg"

    def tick(self, now):
        return False

    def is_active(self, now=None):
        return False

    def release(self):
        self.released = True
        self.instance = None


def test_controller_init_raises_actionable_message_for_clockless_source():
    """Binding a controller to a live clock-less source raises the SAME
    actionable message Container.__getattr__ documents for `.media` -
    explicitly, not via an accidental `source.clock` AttributeError."""
    with pytest.raises(AttributeError, match="has no media source"):
        make_controller(ClocklessSource(), container_id="svg_node")


def test_pump_is_safe_when_id_resolves_to_clockless_source():
    """Pre-attach controller + clock-less source appearing underneath: the
    pump must be a silent no-op every tick (belt to attach()'s pruning)."""
    controller, manager = make_controller(None, container_id="svg_node")
    fired = record_events(controller)
    manager.sources["svg_node"] = ClocklessSource()  # "attach" underneath
    for tick in range(5):
        controller._pump(now=float(tick))  # pre-fix: AttributeError('clock')
    assert all(not calls for calls in fired.values())  # nothing edge-detected
    # getattr-backed state stays sane; baselines untouched
    assert controller.ready_state == "ready"  # source present, no explicit state
    assert controller.muted is False and controller.volume == 1.0
    assert controller._was_paused is True and controller._was_ended is False


def test_attach_prunes_clockless_controllers(monkeypatch):
    """Real MediaManager.attach(): a pre-attach controller whose element
    turns out static (SVG) is dropped from the registry - even WITH
    listeners (they can never fire) - and the next `.media`/controller_for
    access raises the documented actionable message."""
    import puree.media as media_pkg

    cid = "unit_test_svg_prune"
    controller = media_manager.controller_for(cid)  # pre-attach: source None
    controller.on("play", lambda m: None)  # listeners must not keep it alive
    assert media_manager._controllers[cid] is controller

    source = ClocklessSource()
    monkeypatch.setattr(media_pkg, "get_factory", lambda ext: (lambda *a, **k: source))
    fake_img_op = types.ModuleType("puree.img_op")
    fake_img_op.image_manager = types.SimpleNamespace(images={"logo.svg": "assets/logo.svg"})
    monkeypatch.setitem(sys.modules, "puree.img_op", fake_img_op)
    instance = types.SimpleNamespace(container_id=cid, image_name="logo.svg", texture=None, batch=None)

    try:
        media_manager.attach({cid: {"image_name": "logo.svg"}}, [instance])
        assert media_manager.get_source(cid) is source  # source attached fine
        assert cid not in media_manager._controllers  # controller pruned
        assert media_manager.tick(0.0) is False  # pump path clean either way
        with pytest.raises(AttributeError, match="has no media source"):
            media_manager.controller_for(cid)  # post-attach: documented raise
    finally:
        media_manager._sources.pop(cid, None)
        media_manager._controllers.pop(cid, None)


# ── MediaManager error resilience (live-Blender 2026-07-20 regression) ─
# When a source factory explodes (e.g. no usable GPU upload path), the
# failure must stay contained to THAT element; mid-life tick failures must
# release the source so it can never stay active or half-alive.


def test_attach_isolates_per_source_failures(monkeypatch):
    """One exploding factory logs + skips that element only: the healthy
    source attaches, the failed one is absent (never half-attached)."""
    import puree.media as media_pkg

    clock, _ = make_clock()
    good = FakeSource(clock)

    def factory(container_id, image_name, path, instance):
        if image_name == "boom.gif":
            raise RuntimeError("no usable GPU texture upload path (test)")
        return good

    monkeypatch.setattr(media_pkg, "get_factory", lambda ext: factory)
    fake_img_op = types.ModuleType("puree.img_op")
    fake_img_op.image_manager = types.SimpleNamespace(images={"ok.gif": "assets/ok.gif", "boom.gif": "assets/boom.gif"})
    monkeypatch.setitem(sys.modules, "puree.img_op", fake_img_op)

    instances = [
        types.SimpleNamespace(container_id="ok_node", image_name="ok.gif", texture=None, batch=None),
        types.SimpleNamespace(container_id="boom_node", image_name="boom.gif", texture=None, batch=None),
    ]
    blocks = {
        "ok_node": {"image_name": "ok.gif"},
        "boom_node": {"image_name": "boom.gif"},
    }
    try:
        media_manager.attach(blocks, instances)  # must not raise
        assert media_manager.get_source("ok_node") is good  # unaffected
        assert media_manager.get_source("boom_node") is None  # skipped entirely
    finally:
        media_manager._sources.pop("ok_node", None)
        media_manager._sources.pop("boom_node", None)


def test_tick_releases_sources_whose_tick_raises():
    """gif/svg-style mid-life failures (upload/raster exploding inside
    tick) ride the manager: the source is released and dropped, so an
    errored element can never keep the UI active or half-alive."""

    class ExplodingSource:
        def __init__(self):
            self.released = False
            self.instance = object()

        def tick(self, now):
            raise RuntimeError("upload exploded (test)")

        def is_active(self, now=None):
            return not self.released

        def release(self):
            self.released = True
            self.instance = None

    source = ExplodingSource()
    media_manager._sources["unit_test_boom_tick"] = source
    try:
        assert media_manager.tick(0.0) is False
        assert source.released is True
        assert "unit_test_boom_tick" not in media_manager._sources
        assert media_manager.has_active() is False
    finally:
        media_manager._sources.pop("unit_test_boom_tick", None)
