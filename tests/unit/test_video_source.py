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
"""Unit tests for puree.media.decoders.video - no bpy/Blender needed.

``puree/`` is mounted as a namespace-style package (bare module object
with ``__path__``; the real ``puree/__init__.py`` imports bpy and never
runs). GPU is stubbed at the shared upload boundary
(``puree.media.upload.upload_texture``, patched at its rebound name in
the video module) so the real tick path runs and every upload lands in a
recorder; poster resolution is stubbed by injecting a fake
``puree.img_op`` module (the real one imports bpy).

The no-av tests always run (they hide ``av`` via ``sys.modules``); the
decode tests skip when PyAV is missing from the dev environment
(``python -m pip install av``). In-Blender, PyAV ships bundled with Puree
(wheels/ + manifest) - the no-av degrade path stays as a safety net.
"""

import importlib.util
import sys
import threading
import time
import types
from pathlib import Path

import pytest

# Fully import numpy on the MAIN thread up front (when installed): video
# decoder threads import it lazily inside flip_rgba, and pytest.approx
# peeks at sys.modules["numpy"] mid-import otherwise - a flaky
# "partially initialized module" AttributeError.
try:
    import numpy  # noqa: F401
except ImportError:  # pragma: no cover - numpy is optional
    pass

REPO_ROOT = Path(__file__).resolve().parents[2]
ADDON_DIR = REPO_ROOT / "tests" / "helloworld"  # the dev addon (assets/, fonts/, wheels/)
CLIP = ADDON_DIR / "assets" / "demo_clip.mp4"


def _ensure_puree_package():
    pkg = sys.modules.get("puree")
    if pkg is None:
        pkg = types.ModuleType("puree")
        pkg.__path__ = [str(REPO_ROOT / "puree")]
        sys.modules["puree"] = pkg
    return pkg


_ensure_puree_package()

import puree.media.decoders.video as video_mod  # noqa: E402
from puree.media.controller import MediaController  # noqa: E402
from puree.media.decoders.video import VideoSource, flip_rgba  # noqa: E402

HAS_AV = importlib.util.find_spec("av") is not None
requires_av = pytest.mark.skipif(not HAS_AV, reason="PyAV not installed in this dev env (python -m pip install av)")
requires_clip = pytest.mark.skipif(not CLIP.exists(), reason="tests/helloworld/assets/demo_clip.mp4 missing")

# ── harness ──────────────────────────────────────────────────────────


class FakeTexture:
    def __init__(self, width, height, data=None):
        self.width = width
        self.height = height
        self.data = data


class UploadRecorder:
    """Stands in for media.upload.upload_texture (the only gpu touchpoint)."""

    def __init__(self):
        self.calls = []  # (width, height, byte_len)

    def __call__(self, width, height, data):
        self.calls.append((width, height, len(data)))
        return FakeTexture(width, height, data)


class FakeInstance:
    def __init__(self, image_name, container_id="vid"):
        self.container_id = container_id
        self.image_name = image_name
        self.texture = None
        self.batch = None
        self.size = [100, 100]

    def _create_batch(self):
        self.batch = "batch"


@pytest.fixture
def uploads(monkeypatch):
    recorder = UploadRecorder()
    # VideoSource binds `from ..upload import upload_texture` at import -
    # patch the name in the video module so its call sites hit the recorder.
    monkeypatch.setattr(video_mod, "upload_texture", recorder)
    return recorder


@pytest.fixture
def sources():
    """Collects sources and guarantees release (thread join) after each test."""
    created = []
    yield created
    for source in created:
        try:
            source.release()
        except Exception:
            pass


def make_source(sources, block=None, name="demo_clip.mp4", container_id="vid"):
    instance = FakeInstance(name, container_id)
    source = VideoSource(container_id, name, str(CLIP), instance, block=block or {})
    sources.append(source)
    return source, instance


def wait_for(predicate, timeout=10.0, interval=0.016):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(interval)
    return None


# ── flip helper (no av needed) ───────────────────────────────────────


def test_flip_rgba_reverses_scanlines():
    # 1x2 RGBA image: row0 = 0..3, row1 = 4..7 -> flipped swaps the rows
    assert flip_rgba(bytes(range(8)), 1, 2) == bytes([4, 5, 6, 7, 0, 1, 2, 3])


def test_flip_rgba_strips_stride_padding():
    # width 1 (row = 4 bytes) but stride 6: two padding bytes per scanline
    data = bytes([0, 1, 2, 3, 90, 91, 4, 5, 6, 7, 92, 93])
    assert flip_rgba(data, 1, 2, stride=6) == bytes([4, 5, 6, 7, 0, 1, 2, 3])


def test_flip_rgba_pure_bytes_fallback_matches_numpy(monkeypatch):
    data = bytes(range(48))  # 2x3 RGBA with stride 8 == row size
    with_numpy = flip_rgba(data, 2, 3)
    monkeypatch.setitem(sys.modules, "numpy", None)  # import numpy -> ImportError
    without_numpy = flip_rgba(data, 2, 3)
    assert with_numpy == without_numpy


def test_flip_rgba_validates_buffer():
    with pytest.raises(ValueError):
        flip_rgba(b"\x00" * 7, 1, 2)  # too small
    with pytest.raises(ValueError):
        flip_rgba(b"\x00" * 8, 1, 2, stride=2)  # stride < row


# ── degrade without av (always runs; av is hidden via sys.modules) ───


class RecordingLogger:
    def __init__(self):
        self.warnings = []

    def warning(self, msg, *args, **kwargs):
        self.warnings.append(msg)

    def __getattr__(self, name):  # debug/info/error - swallow
        return lambda *args, **kwargs: None


@pytest.fixture
def no_av(monkeypatch):
    monkeypatch.setitem(sys.modules, "av", None)  # import av -> ImportError
    monkeypatch.setattr(video_mod, "_warned_no_av", False)


@pytest.fixture
def warn_log(monkeypatch):
    recording = RecordingLogger()
    monkeypatch.setattr(video_mod, "logger", recording)
    return recording


@requires_clip
def test_unsupported_without_av_shows_poster_single_warning(no_av, warn_log, uploads, sources, monkeypatch):
    poster_texture = FakeTexture(64, 64)
    fake_img_op = types.ModuleType("puree.img_op")
    fake_img_op.image_manager = types.SimpleNamespace(resolve=lambda name: poster_texture)
    monkeypatch.setitem(sys.modules, "puree.img_op", fake_img_op)

    source, instance = make_source(
        sources, block={"poster": "intro_poster.png", "autoplay": True, "preload": "metadata"}
    )
    assert source.ready_state == "unsupported"
    assert instance.texture is poster_texture  # poster path chosen
    assert instance.batch is not None  # poster is drawable
    assert source.clock.paused  # autoplay refused
    assert source.duration is None
    assert len(warn_log.warnings) == 1
    assert "'av'" in warn_log.warnings[0]
    assert "bundled with Puree" in warn_log.warnings[0]  # points at a broken/unrefreshed install

    # A second video element does NOT warn again (one warning per session)
    make_source(sources, container_id="vid2")
    assert len(warn_log.warnings) == 1


@requires_clip
def test_unsupported_without_av_is_inert(no_av, warn_log, uploads, sources):
    source, instance = make_source(sources, block={"autoplay": True})
    assert source.ready_state == "unsupported"
    assert instance.texture is None  # no poster set -> renders nothing
    source.play()
    source.seek(5.0)
    assert source._thread is None  # no decoder thread ever starts
    assert source.tick(time.monotonic()) is False
    assert source.is_active() is False
    assert uploads.calls == []


@requires_clip
def test_unsupported_autoplay_never_emits_or_activates(no_av, warn_log, uploads, sources):
    """Regression (live-Blender 2026-07-20): an 'unsupported' video with
    autoplay: true must be FULLY inert - paused clock, ZERO controller
    events over many pumped ticks, no has_active() contribution - so the
    controls bar never rewrites labels / marks containers dirty on its
    account (label churn -> dirty-sync -> per-input update-op log spam)."""
    from puree.media import media_manager

    source, instance = make_source(sources, block={"autoplay": True, "loop": True, "muted": True})
    assert source.ready_state == "unsupported"
    assert source.clock.paused and not source.clock.playing  # autoplay refused

    media_manager._sources["vid"] = source
    controller = media_manager.controller_for("vid")
    fired = {event: 0 for event in ("play", "pause", "ended", "timeupdate", "error")}
    for event in fired:
        controller.on(event, lambda m, e=event: fired.__setitem__(e, fired[e] + 1))
    try:
        base = time.monotonic()
        for i in range(20):  # ~6 s of ticks: >20 would-be timeupdate windows
            assert media_manager.tick(base + i * 0.3) is False
        assert fired == dict.fromkeys(fired, 0)  # zero events
        assert media_manager.has_active() is False
        assert source.clock.current_time == 0.0  # clock never advanced
        assert uploads.calls == []
    finally:
        media_manager._sources.pop("vid", None)
        media_manager._controllers.pop("vid", None)


@requires_av
@requires_clip
def test_mid_play_decode_error_freezes_clock_and_stops_emitting(uploads, sources, monkeypatch):
    """A decode error landing MID-PLAY (_set_error runs on the decoder
    thread) must quiesce the source: clock frozen where the error hit, no
    further timeupdate stream, inactive, play() refused."""
    monkeypatch.setattr(video_mod, "_failed_paths", set())  # log-dedupe hygiene
    source, _ = make_source(sources, block={"autoplay": True, "muted": True})
    assert source.clock.playing

    source._set_error("decode exploded (test)")  # exactly what the thread calls
    assert source.ready_state == "error"
    assert source.clock.paused  # frozen right where the error hit
    assert source.is_active() is False
    assert source.tick(time.monotonic()) is False  # inert branch: no work, no emit fuel
    frozen_at = source.clock.current_time
    source.play()  # refused (debug log)
    assert source.clock.paused and source.clock.current_time == frozen_at


# ── metadata / preload (needs av + the demo clip) ────────────────────


@requires_av
@requires_clip
def test_metadata_probe(uploads, sources):
    source, instance = make_source(sources)  # preload defaults to "metadata"
    assert source.ready_state == "metadata"
    assert source.duration is not None and source.duration > 0
    assert source._width > 0 and source._height > 0
    assert source.has_audio is False  # demo_clip.mp4 is video-only (av-probed)
    assert source.clock.duration == pytest.approx(source.duration)
    assert source._thread is None  # metadata never starts decoding
    assert uploads.calls == []  # ...nor uploads anything
    assert instance.texture is None


@requires_av
@requires_clip
def test_preload_none_does_nothing_until_play(uploads, sources):
    source, instance = make_source(sources, block={"preload": "none"})
    assert source.ready_state == "none"
    assert source.duration is None
    assert source._thread is None and uploads.calls == []
    source.play()  # play probes lazily, then starts decoding
    assert source.ready_state in ("metadata", "ready")
    assert source.duration is not None and source.duration > 0
    assert source._thread is not None and source._thread.is_alive()


@requires_av
@requires_clip
def test_preload_auto_decodes_and_shows_first_frame(uploads, sources):
    source, instance = make_source(sources, block={"preload": "auto"})
    assert source.ready_state == "ready"
    assert instance.texture is not None
    width, height, byte_len = uploads.calls[0]
    assert (width, height) == (source._width, source._height)
    assert byte_len == width * height * 4
    assert source._thread is None  # first frame only - no thread until play


# ── decoder thread (needs av + the demo clip) ────────────────────────


@requires_av
@requires_clip
def test_decode_thread_yields_full_rgba_frames(uploads, sources):
    source, _ = make_source(sources, block={"autoplay": True})
    assert source._thread is not None and source._thread.is_alive()
    assert source._thread.daemon  # never blocks Blender shutdown
    generation, pts, width, height, data = source._queue.get(timeout=10.0)
    assert len(data) == width * height * 4
    assert (width, height) == (source._width, source._height)
    assert pts >= 0.0


@requires_av
@requires_clip
def test_tick_uploads_and_swaps_instance_texture(uploads, sources):
    source, instance = make_source(sources, block={"autoplay": True, "muted": True})
    changed = wait_for(lambda: source.tick(time.monotonic()))
    assert changed, "tick never produced a frame"
    assert instance.texture is not None
    assert instance.texture.width == source._width
    assert source.ready_state == "ready"
    assert uploads.calls[-1][2] == source._width * source._height * 4
    assert source.is_active()


@requires_av
@requires_clip
def test_seek_lands_within_tolerance(uploads, sources):
    target = 20.0
    source, _ = make_source(sources)  # paused - seek must still decode+display
    source.seek(target)
    frame = wait_for(source._pull_frame, timeout=10.0)
    assert frame is not None, "seek produced no frame"
    assert abs(frame[1] - target) <= 0.5
    # the clock jumped immediately, independent of decode latency
    assert source.clock.current_time == pytest.approx(target, abs=0.01)


@requires_av
@requires_clip
def test_seek_drops_stale_generation_frames(uploads, sources):
    source, _ = make_source(sources, block={"autoplay": True})
    wait_for(lambda: not source._queue.empty(), timeout=10.0)
    stale_generation = source._generation
    source.seek(30.0)
    assert source._generation == stale_generation + 1
    frame = wait_for(source._pull_frame, timeout=10.0)
    assert frame is not None
    assert frame[0] == source._generation  # pre-seek frames never surface
    assert abs(frame[1] - 30.0) <= 0.5


@requires_av
@requires_clip
def test_eof_non_loop_ends_and_ended_event_fires(uploads, sources):
    source, _ = make_source(sources, block={"muted": True})
    manager = types.SimpleNamespace(get_source=lambda cid: source if cid == "vid" else None)
    controller = MediaController("vid", manager)
    fired = []
    controller.on("ended", lambda m: fired.append(m.current_time))

    source.play()
    source.seek(source.duration - 0.3)

    def pump():
        source.tick(time.monotonic())
        controller._pump()
        return fired

    assert wait_for(pump, timeout=15.0), "ended never fired"
    assert source.clock.ended
    assert source.clock.current_time == pytest.approx(source.duration, abs=0.01)
    assert fired[0] == pytest.approx(source.duration, abs=0.01)


@requires_av
@requires_clip
def test_play_after_ended_replays_from_start(uploads, sources):
    source, _ = make_source(sources)
    source.play()
    source.seek(source.duration - 0.3)
    assert wait_for(lambda: source.clock.ended, timeout=15.0), "never reached EOF"
    source.play()
    assert not source.clock.ended
    assert source.clock.current_time < 1.0
    frame = wait_for(source._pull_frame, timeout=10.0)
    assert frame is not None and frame[1] < 5.0  # decoding from the head again


@requires_av
@requires_clip
def test_loop_wraps_and_keeps_decoding(uploads, sources):
    source, _ = make_source(sources, block={"loop": True, "muted": True})
    source.play()
    source.seek(source.duration - 0.3)
    assert wait_for(lambda: source.clock.current_time < 2.0, timeout=15.0), "clock never wrapped"
    assert not source.clock.ended  # looping media never ends

    def next_iteration_frame():
        frame = source._pull_frame()
        return frame if (frame is not None and frame[1] < 5.0) else None

    frame = wait_for(next_iteration_frame, timeout=10.0)
    assert frame is not None, "no next-iteration frame after the wrap"


# ── lifecycle / teardown (needs av + the demo clip) ──────────────────


@requires_av
@requires_clip
def test_pause_grace_stops_thread_and_play_restarts_it(uploads, sources, monkeypatch):
    monkeypatch.setattr(video_mod, "PAUSE_GRACE_SECONDS", 0.3)  # keep the test fast
    source, _ = make_source(sources, block={"autoplay": True})
    thread = source._thread
    assert thread.is_alive()
    source.pause()
    assert wait_for(lambda: not thread.is_alive(), timeout=5.0), "thread survived the pause grace"
    source.play()
    assert source._thread is not None and source._thread.is_alive()
    assert source._thread is not thread  # a fresh thread, resumed at position


@requires_av
@requires_clip
def test_release_joins_thread(uploads, sources):
    source, instance = make_source(sources, block={"autoplay": True})
    thread = source._thread
    assert thread.is_alive()
    source.release()
    assert not thread.is_alive()  # joined within release()'s timeout
    assert source.released and source.instance is None
    assert source.tick(time.monotonic()) is False


@requires_av
@requires_clip
def test_manager_shutdown_leaves_zero_leaked_threads(uploads):
    from puree.media import media_manager

    before = {t for t in threading.enumerate()}
    instance_a = FakeInstance("demo_clip.mp4", "vid_a")
    instance_b = FakeInstance("demo_clip.mp4", "vid_b")
    source_a = VideoSource("vid_a", "demo_clip.mp4", str(CLIP), instance_a, block={"autoplay": True})
    source_b = VideoSource("vid_b", "demo_clip.mp4", str(CLIP), instance_b, block={"autoplay": True, "loop": True})
    media_manager._sources.update({"vid_a": source_a, "vid_b": source_b})
    media_manager.controller_for("vid_a").on("play", lambda m: None)

    threads = [source_a._thread, source_b._thread]
    assert all(t is not None and t.is_alive() and t.daemon for t in threads)

    media_manager.shutdown()

    for thread in threads:
        assert not thread.is_alive(), "decoder thread leaked past shutdown()"
    assert media_manager._sources == {} and media_manager._controllers == {}
    leaked = [t for t in threading.enumerate() if t not in before and t.name.startswith("puree-video")]
    assert leaked == []
    non_daemon = [
        t for t in threading.enumerate() if t is not threading.main_thread() and not t.daemon and t not in before
    ]
    assert non_daemon == []


# ── attach-reconcile hook ────────────────────────────────────────────


@requires_av
@requires_clip
def test_matches_block_detects_playback_attr_changes(uploads, sources):
    block = {"loop": True, "muted": True, "volume": 0.8}
    source, _ = make_source(sources, block=dict(block))
    assert source.matches_block(dict(block))
    assert source.matches_block({"loop": True, "muted": True, "volume": 0.8, "autoplay": False})
    assert not source.matches_block({"loop": False, "muted": True, "volume": 0.8})
    assert not source.matches_block({})


@requires_av
@requires_clip
def test_playback_attrs_stored_faithfully(uploads, sources):
    source, _ = make_source(
        sources,
        block={"muted": True, "volume": 0.25, "playback_rate": 2.0, "preload": "metadata"},
    )
    assert source.muted is True  # demo_clip has no audio stream - stored only
    assert source.volume == pytest.approx(0.25)
    assert source.clock.playback_rate == pytest.approx(2.0)  # rate feeds the clock
    source.set_playback_rate(0.5)
    assert source.clock.playback_rate == pytest.approx(0.5)
    source.set_volume(2.0)
    assert source.volume == 1.0  # clamped
    source.set_muted(False)
    assert source.muted is False
