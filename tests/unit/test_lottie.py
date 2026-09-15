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
"""Unit tests for Lottie media support - no bpy/Blender needed.

``puree/`` is mounted as a namespace-style package (bare module object
with ``__path__``; the real ``puree/__init__.py`` imports bpy and never
runs). GPU is stubbed at the shared upload boundary
(``puree.media.upload.upload_texture``, patched at its rebound name in
the lottie module) so the real render/tick path runs and every upload
lands in a recorder that keeps the frame bytes for inspection.

The no-rlottie tests always run (they hide ``rlottie_python`` via
``sys.modules``); the render tests skip when rlottie-python is missing
from the dev environment (``python -m pip install rlottie-python``).
In-Blender, rlottie-python ships bundled with Puree (wheels/ + manifest)
- the no-rlottie degrade path stays as a safety net.

Facts these tests pin down (verified against rlottie-python 1.3.8):
``lottie_animation_get_totalframe()`` is inclusive (op - ip + 1, so the
90-frame demo timeline reports 91); ``lottie_animation_render`` emits
premultiplied top-down BGRA (the swizzle/flip tests prove the pipeline
receives premultiplied bottom-up RGBA).
"""

import importlib.util
import json
import sys
import time
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ADDON_DIR = REPO_ROOT / "tests" / "helloworld"  # the dev addon (assets/, fonts/, wheels/)
DEMO = ADDON_DIR / "assets" / "demo_lottie.json"
MEDIA_DIR = REPO_ROOT / "puree" / "media"


def _ensure_puree_package():
    pkg = sys.modules.get("puree")
    if pkg is None:
        pkg = types.ModuleType("puree")
        pkg.__path__ = [str(REPO_ROOT / "puree")]
        sys.modules["puree"] = pkg
    return pkg


_ensure_puree_package()

import puree.media.decoders.lottie as lottie_mod  # noqa: E402
from puree.media.decoders.lottie import (  # noqa: E402
    LottieSource,
    bgra_to_rgba_bottom_up,
    frame_delays_ms,
    validate_lottie_json,
)

HAS_RLOTTIE = importlib.util.find_spec("rlottie_python") is not None
requires_rlottie = pytest.mark.skipif(
    not HAS_RLOTTIE, reason="rlottie-python not installed in this dev env (python -m pip install rlottie-python)"
)
requires_demo = pytest.mark.skipif(not DEMO.exists(), reason="tests/helloworld/assets/demo_lottie.json missing")

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
    def __init__(self, image_name, container_id="lot", box=(220, 220)):
        self.container_id = container_id
        self.image_name = image_name
        self.texture = None
        self.batch = None
        self.size = list(box)

    def _create_batch(self):
        self.batch = "batch"


@pytest.fixture
def uploads(monkeypatch):
    recorder = UploadRecorder()
    # LottieSource binds `from ..upload import upload_texture` at import -
    # patch the name in the lottie module so its call sites hit the recorder.
    monkeypatch.setattr(lottie_mod, "upload_texture", recorder)
    return recorder


@pytest.fixture
def sources():
    """Collects sources and guarantees release after each test."""
    created = []
    yield created
    for source in created:
        try:
            source.release()
        except Exception:
            pass


class RecordingLogger:
    def __init__(self):
        self.warnings = []
        self.errors = []

    def warning(self, msg, *args, **kwargs):
        self.warnings.append(msg)

    def error(self, msg, *args, **kwargs):
        self.errors.append(msg)

    def __getattr__(self, name):  # debug/info - swallow
        return lambda *args, **kwargs: None


@pytest.fixture
def warn_log(monkeypatch):
    recording = RecordingLogger()
    monkeypatch.setattr(lottie_mod, "logger", recording)
    monkeypatch.setattr(lottie_mod, "_warned_paths", set())
    return recording


@pytest.fixture
def no_rlottie(monkeypatch):
    monkeypatch.setitem(sys.modules, "rlottie_python", None)  # import -> ImportError
    monkeypatch.setattr(lottie_mod, "_warned_no_rlottie", False)


def make_source(sources, block=None, name="demo_lottie.json", container_id="lot", box=(220, 220), path=None):
    instance = FakeInstance(name, container_id, box)
    source = LottieSource(container_id, name, str(path or DEMO), instance, block={} if block is None else block)
    sources.append(source)
    return source, instance


def _write_json(tmp_path, name, payload):
    path = tmp_path / name
    path.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")
    return path


MINIMAL_VALID = {"v": "5.7.4", "fr": 30, "ip": 0, "op": 10, "w": 8, "h": 8, "layers": []}


# ── pure helpers (no rlottie needed) ─────────────────────────────────


def test_module_imports_without_rlottie(monkeypatch):
    # The dependency is lazy (imported inside methods): a fresh load of the
    # real module file with rlottie_python hidden must succeed.
    monkeypatch.setitem(sys.modules, "rlottie_python", None)
    spec = importlib.util.spec_from_file_location(
        "puree.media.decoders._lottie_isolated", MEDIA_DIR / "decoders" / "lottie.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        assert module.LOTTIE_EXTENSIONS == (".json",)
        assert callable(module.LottieSource)
    finally:
        sys.modules.pop(spec.name, None)


def test_bgra_swizzle_and_flip():
    # 1x2 top-down BGRA: row0=(B10,G20,R30,A40), row1=(B50,G60,R70,A80)
    # -> bottom-up RGBA: first out row is the old LAST row, R and B swapped.
    data = bytes([10, 20, 30, 40, 50, 60, 70, 80])
    assert bgra_to_rgba_bottom_up(data, 1, 2) == bytes([70, 60, 50, 80, 30, 20, 10, 40])


def test_bgra_pure_bytes_fallback_matches_numpy(monkeypatch):
    data = bytes(range(2 * 3 * 4))  # 2x3 surface
    with_numpy = bgra_to_rgba_bottom_up(data, 2, 3)
    monkeypatch.setitem(sys.modules, "numpy", None)  # import numpy -> ImportError
    assert bgra_to_rgba_bottom_up(data, 2, 3) == with_numpy


def test_bgra_validates_buffer():
    with pytest.raises(ValueError):
        bgra_to_rgba_bottom_up(b"\x00" * 7, 1, 2)  # too small


def test_frame_delays_error_diffusion():
    # 30 fps: boundaries land on round(i * 1000/30) -> 33/34 ms, zero drift.
    delays = frame_delays_ms(90, 30.0)
    assert len(delays) == 90 and sum(delays) == 3000 and set(delays) == {33, 34}
    assert sum(frame_delays_ms(91, 30.0)) == 3033  # the demo asset's inclusive count
    assert sum(frame_delays_ms(60, 60.0)) == 1000
    assert sum(frame_delays_ms(24, 24.0)) == 1000


def test_validate_accepts_minimal_bodymovin(tmp_path):
    ok, reason = validate_lottie_json(_write_json(tmp_path, "ok.json", MINIMAL_VALID))
    assert ok and reason == ""


def test_validate_rejects_non_lottie_json(tmp_path):
    cases = [
        ({"just": "config"}, "missing key"),  # arbitrary config json
        ([1, 2, 3], "not an object"),  # array root
        ({**MINIMAL_VALID, "layers": "nope"}, "layers"),  # layers not a list
        ({**MINIMAL_VALID, "fr": 0}, "positive"),  # zero framerate
        ({**MINIMAL_VALID, "w": "wide"}, "not numbers"),  # non-numeric size
        ("this is not json {", "not readable"),  # unparseable text
    ]
    for i, (payload, needle) in enumerate(cases):
        ok, reason = validate_lottie_json(_write_json(tmp_path, f"bad{i}.json", payload))
        assert not ok and needle in reason, (payload, reason)
    ok, reason = validate_lottie_json(str(tmp_path / "missing.json"))
    assert not ok and "not readable" in reason


# ── degrade without rlottie (always runs; hidden via sys.modules) ────


@requires_demo
def test_unsupported_without_rlottie_single_warning(no_rlottie, warn_log, uploads, sources):
    source, instance = make_source(sources)
    assert source.ready_state == "unsupported"
    assert instance.texture is None and instance.batch is None  # poster-less: renders nothing
    assert source.clock.paused  # autoplay (default true) refused
    assert source.duration is None
    source.play()
    source.seek(1.0)
    source.stop()
    assert source.tick(time.monotonic()) is False
    assert source.is_active() is False
    assert uploads.calls == []
    assert len(warn_log.warnings) == 1
    assert "rlottie-python" in warn_log.warnings[0]

    # A second lottie element does NOT warn again (one warning per session)
    make_source(sources, container_id="lot2")
    assert len(warn_log.warnings) == 1


@requires_demo
def test_unsupported_autoplay_never_emits_or_activates(no_rlottie, warn_log, uploads, sources):
    """Same inert guarantee as video (live-Blender 2026-07-20 regression):
    lottie autoplay defaults TRUE, but with the wheel missing the source
    must be FULLY inert - paused clock, ZERO controller events over many
    pumped ticks, no has_active() contribution, no uploads."""
    from puree.media import media_manager

    source, _ = make_source(sources)  # autoplay/loop default true
    assert source.ready_state == "unsupported"
    assert source.clock.paused and not source.clock.playing  # autoplay refused

    media_manager._sources["lot"] = source
    controller = media_manager.controller_for("lot")
    fired = {event: 0 for event in ("play", "pause", "ended", "timeupdate", "error")}
    for event in fired:
        controller.on(event, lambda m, e=event: fired.__setitem__(e, fired[e] + 1))
    try:
        for i in range(20):  # ~6 s of ticks: >20 would-be timeupdate windows
            assert media_manager.tick(1000.0 + i * 0.3) is False
        assert fired == dict.fromkeys(fired, 0)  # zero events
        assert media_manager.has_active() is False
        assert source.clock.current_time == 0.0  # clock never advanced
        assert uploads.calls == []
    finally:
        media_manager._sources.pop("lot", None)
        media_manager._controllers.pop("lot", None)


def test_non_lottie_json_inert_single_warning(warn_log, uploads, sources, tmp_path):
    # Any .json matches the registered extension - a non-Bodymovin document
    # must warn once (per path) and become an inert stub. Runs with or
    # without rlottie installed: validation never imports it.
    bad = _write_json(tmp_path, "app_config.json", {"version": 2, "options": {"theme": "dark"}})
    source, instance = make_source(sources, path=bad, name="app_config.json")
    assert source.ready_state == "unsupported"
    assert instance.texture is None
    assert source.duration is None
    assert source.tick(1.0) is False and source.is_active() is False
    assert uploads.calls == []
    assert len(warn_log.warnings) == 1
    assert "Bodymovin" in warn_log.warnings[0] and "app_config.json" in warn_log.warnings[0]

    make_source(sources, path=bad, name="app_config.json", container_id="lot2")
    assert len(warn_log.warnings) == 1  # per-path, per-session


def test_validation_warning_beats_dependency_warning(no_rlottie, warn_log, uploads, sources, tmp_path):
    # Validation runs BEFORE the dependency check: a wrong .json gets the
    # accurate message even when the wheel is missing.
    bad = _write_json(tmp_path, "settings.json", {"a": 1})
    source, _ = make_source(sources, path=bad, name="settings.json")
    assert source.ready_state == "unsupported"
    assert len(warn_log.warnings) == 1
    assert "Bodymovin" in warn_log.warnings[0]
    assert "rlottie-python" not in warn_log.warnings[0]


# ── open / metadata (needs rlottie + the demo asset) ─────────────────


@requires_rlottie
@requires_demo
def test_open_demo_metadata_and_defaults(uploads, sources):
    source, _ = make_source(sources)
    assert source.ready_state == "ready"
    # rlottie's totalframe is INCLUSIVE of the out point (op - ip + 1):
    # the 90-frame timeline reports 91; every frame gets a display slot.
    assert source.frame_count == 91
    assert source.fps == 30.0
    assert source.intrinsic == (240, 240)
    assert source.duration == pytest.approx(91 / 30.0, abs=0.002)
    assert source.clock.duration == pytest.approx(source.duration)
    assert source._static is False
    # lottie-player parity: autoplay + loop default TRUE (plan section 5.4)
    assert source.clock.playing and source.clock.loop is True
    assert source.is_active()


@requires_rlottie
@requires_demo
def test_explicit_autoplay_loop_false_respected(uploads, sources):
    source, _ = make_source(sources, block={"autoplay": False, "loop": False, "playback_rate": 2.0})
    assert source.clock.paused
    assert source.clock.loop is False
    assert source.clock.playback_rate == pytest.approx(2.0)
    assert source.is_active() is False


@requires_rlottie
@requires_demo
def test_attach_seeds_aspect_fit_frame0(uploads, sources):
    # 240x240 intrinsic aspect-fit into a 220x165 box -> 165x165 raster.
    source, instance = make_source(sources, box=(220, 165))
    assert (instance.texture.width, instance.texture.height) == (165, 165)
    assert instance.batch is not None
    assert uploads.calls[0] == (165, 165, 165 * 165 * 4)


@requires_rlottie
@requires_demo
def test_frame_bytes_premultiplied_rgba(uploads, sources):
    source, instance = make_source(sources, box=(240, 240))
    data = instance.texture.data
    assert len(data) == 240 * 240 * 4
    # Premultiplied RGBA: no color channel may exceed its alpha.
    for i in range(0, len(data), 4):
        r, g, b, a = data[i], data[i + 1], data[i + 2], data[i + 3]
        assert max(r, g, b) <= a, f"straight alpha at byte {i}: {(r, g, b, a)}"
    # Channel order: the canvas center is the accent-blue core (#4772b3) -
    # blue must dominate red after the BGRA->RGBA swizzle.
    i = ((120 * 240) + 120) * 4
    r, b, a = data[i], data[i + 2], data[i + 3]
    assert b > r > 0 and a == 255


@requires_rlottie
def test_render_flips_rows_bottom_up(uploads, sources, tmp_path):
    # Identifiable feature at the animation TOP-left: after the bottom-up
    # flip (matching decode_gif/rasterize_svg and the overlay quad UVs) it
    # must land in the LAST buffer rows, with the buffer START transparent.
    probe = {
        "v": "5.7.4",
        "fr": 10,
        "ip": 0,
        "op": 10,
        "w": 8,
        "h": 8,
        "nm": "p",
        "ddd": 0,
        "assets": [],
        "layers": [
            {
                "ddd": 0,
                "ind": 1,
                "ty": 4,
                "nm": "r",
                "sr": 1,
                "ao": 0,
                "ks": {
                    "o": {"a": 0, "k": 100},
                    "r": {"a": 0, "k": 0},
                    "p": {"a": 0, "k": [2, 2, 0]},
                    "a": {"a": 0, "k": [0, 0, 0]},
                    "s": {"a": 0, "k": [100, 100, 100]},
                },
                "shapes": [
                    {
                        "ty": "gr",
                        "it": [
                            {
                                "ty": "rc",
                                "d": 1,
                                "p": {"a": 0, "k": [0, 0]},
                                "s": {"a": 0, "k": [4, 4]},
                                "r": {"a": 0, "k": 0},
                            },
                            {"ty": "fl", "c": {"a": 0, "k": [1, 0, 0, 1]}, "o": {"a": 0, "k": 100}, "r": 1},
                            {
                                "ty": "tr",
                                "p": {"a": 0, "k": [0, 0]},
                                "a": {"a": 0, "k": [0, 0]},
                                "s": {"a": 0, "k": [100, 100]},
                                "r": {"a": 0, "k": 0},
                                "o": {"a": 0, "k": 100},
                            },
                        ],
                    }
                ],
                "ip": 0,
                "op": 10,
                "st": 0,
            }
        ],
    }
    path = _write_json(tmp_path, "corner.json", probe)
    source, instance = make_source(sources, path=path, name="corner.json", box=(8, 8))
    data = instance.texture.data

    def px(x, y):
        i = (y * 8 + x) * 4
        return tuple(data[i : i + 4])

    assert px(1, 6) == (255, 0, 0, 255), "animation top-left -> last buffer rows, red in RGBA order"
    assert px(6, 6) == (0, 0, 0, 0), "animation top-right stays empty"
    assert px(1, 1) == (0, 0, 0, 0), "animation bottom -> first buffer rows, empty"


# ── clock-driven playback (needs rlottie + the demo asset) ───────────


@requires_rlottie
@requires_demo
def test_clock_driven_frame_advance_and_loop_wrap(uploads, sources):
    source, instance = make_source(sources, box=(100, 100), block={"autoplay": False})
    t0 = 1000.0
    source.clock.play(now=t0)
    assert source.tick(t0) is False  # still on the seeded frame 0
    assert source.tick(t0 + 0.5) is True and source._frame_idx == 15  # 0.5 s at 30 fps
    texture_15 = instance.texture
    assert source.tick(t0 + 1.0) is True and source._frame_idx == 30
    # loop (default true) wraps: one full duration later we are back on 15,
    # served from the progressive cache (same texture object, no render).
    renders_before = len(uploads.calls)
    assert source.tick(t0 + source.clock.duration + 0.5) is True
    assert source._frame_idx == 15
    assert instance.texture is texture_15
    assert len(uploads.calls) == renders_before
    assert not source.clock.ended  # looping media never ends


@requires_rlottie
@requires_demo
def test_non_loop_ends_clamped_on_last_frame(uploads, sources):
    source, _ = make_source(sources, box=(50, 50), block={"loop": False, "autoplay": False})
    t0 = 2000.0
    source.clock.play(now=t0)
    duration = source.clock.duration
    assert source.tick(t0 + duration - 0.01) is True  # inside the last frame slot
    assert source._frame_idx == source.frame_count - 1  # rlottie's true final frame
    assert source.tick(t0 + duration + 0.1) is False  # nothing more to show
    assert source.clock.ended
    assert source.is_active(t0 + duration + 0.1) is False  # ended media never redraws


@requires_rlottie
@requires_demo
def test_play_after_ended_replays_from_start(uploads, sources):
    source, _ = make_source(sources, box=(50, 50), block={"loop": False, "autoplay": False})
    t0 = 3000.0
    source.clock.play(now=t0)
    source.tick(t0 + source.clock.duration - 0.01)
    source.tick(t0 + source.clock.duration + 0.1)
    assert source.clock.ended
    source.play()  # HTML parity: replay from 0 (clock.play() alone no-ops here)
    assert not source.clock.ended
    assert source.clock.current_time < 0.1
    assert source._frame_idx == 0 and source.clock.playing


@requires_rlottie
@requires_demo
def test_seek_swaps_frame_while_paused(uploads, sources):
    source, instance = make_source(sources, box=(50, 50), block={"autoplay": False})
    before = instance.texture
    source.seek(1.0)
    assert source._frame_idx == 30  # 1.0 s at 30 fps
    assert instance.texture is not before  # repainted immediately, no tick needed
    assert source.clock.current_time == pytest.approx(1.0, abs=0.001)
    assert source.clock.paused
    source.seek(999.0)  # clamps to duration; an infinite-loop clock wraps to 0
    assert source.clock.current_time == pytest.approx(0.0, abs=0.001)


@requires_rlottie
@requires_demo
def test_playback_rate_scales_frame_advance(uploads, sources):
    source, _ = make_source(sources, box=(50, 50), block={"autoplay": False, "playback_rate": 2.0})
    t0 = 4000.0
    source.clock.play(now=t0)
    source.tick(t0 + 0.5)  # 0.5 s wall clock at 2x -> 1.0 s media time
    assert source._frame_idx == 30


# ── resize re-render (mirrors the SVG size-watch) ────────────────────


@requires_rlottie
@requires_demo
def test_resize_debounces_rerenders_and_drops_caches(uploads, sources):
    source, instance = make_source(sources, box=(100, 100), block={"autoplay": False})
    source.seek(1.0)  # frame 30 rendered + cached alongside frame 0
    assert set(source._frame_cache) == {0, 30}
    instance.size = [200, 200]
    assert source.tick(100.0) is False  # debounce starts, nothing swapped
    assert source.is_active() is True  # pending resize counts as active
    assert source.tick(100.05) is False  # still inside the 150 ms window
    assert source.tick(100.16) is True  # stable -> re-render the current frame
    assert (instance.texture.width, instance.texture.height) == (200, 200)
    assert set(source._frame_cache) == {30}  # old-size textures dropped, current frame re-seeded
    assert source.is_active() is False  # settled (and still paused)


@requires_rlottie
@requires_demo
def test_resize_within_tolerance_never_rerenders(uploads, sources):
    source, instance = make_source(sources, box=(100, 100), block={"autoplay": False})
    renders = len(uploads.calls)
    instance.size = [101, 101]  # within the +-1 px tolerance
    for t in (10.0, 10.2, 11.0):
        assert source.tick(t) is False
    assert len(uploads.calls) == renders
    assert source.is_active() is False


@requires_rlottie
@requires_demo
def test_resize_churn_restarts_debounce(uploads, sources):
    source, instance = make_source(sources, box=(100, 100), block={"autoplay": False})
    instance.size = [300, 300]
    assert source.tick(50.0) is False
    instance.size = [400, 400]  # user still dragging
    assert source.tick(50.1) is False  # restarts the window
    assert source.tick(50.2) is False  # only 0.1 s since the restart
    assert source.tick(50.26) is True
    assert (instance.texture.width, instance.texture.height) == (400, 400)


# ── cache vs on-demand (MEDIA_PLAN section 10 budget) ────────────────


@requires_rlottie
@requires_demo
def test_progressive_cache_under_budget(uploads, sources):
    source, _ = make_source(sources, box=(100, 100), block={"autoplay": False})
    assert source._use_cache is True  # 100*100*4*91 = 3.5 MB <= 32 MB
    renders = len(uploads.calls)
    source.seek(0.5)
    source.seek(1.0)
    source.seek(0.5)  # revisit -> cache hit
    assert len(uploads.calls) - renders == 2  # frames 15 and 30 rendered exactly once
    assert set(source._frame_cache) == {0, 15, 30}
    assert len(source._ring) == 0


@requires_rlottie
@requires_demo
def test_ring_path_over_budget(uploads, sources, monkeypatch):
    monkeypatch.setattr(lottie_mod, "FRAME_CACHE_BUDGET_BYTES", 1)
    source, _ = make_source(sources, box=(64, 64), block={"autoplay": False})
    assert source._use_cache is False
    renders = len(uploads.calls)
    source.seek(0.5)
    source.seek(1.0)
    source.seek(0.5)  # no cache: every swap renders on demand
    assert len(uploads.calls) - renders == 3
    assert len(source._ring) == 2  # small reuse ring: current + previous
    assert source._frame_cache == {}


@requires_rlottie
@requires_demo
def test_budget_boundary_at_current_raster_size(uploads, sources, monkeypatch):
    probe, _ = make_source(sources, box=(100, 100), block={"autoplay": False})
    exact = 100 * 100 * 4 * probe.frame_count
    monkeypatch.setattr(lottie_mod, "FRAME_CACHE_BUDGET_BYTES", exact)
    at_budget, _ = make_source(sources, box=(100, 100), block={"autoplay": False}, container_id="lot2")
    assert at_budget._use_cache is True  # exactly at the budget still caches
    monkeypatch.setattr(lottie_mod, "FRAME_CACHE_BUDGET_BYTES", exact - 1)
    over, _ = make_source(sources, box=(100, 100), block={"autoplay": False}, container_id="lot3")
    assert over._use_cache is False  # one byte over -> ring


@requires_rlottie
@requires_demo
def test_full_loop_renders_each_frame_once(uploads, sources):
    source, _ = make_source(sources, box=(50, 50), block={"autoplay": False})
    t0 = 500.0
    source.clock.play(now=t0)
    duration = source.clock.duration
    # One loop at 20 Hz, sampled MID-frame (0.01 s offset keeps every sample
    # >= 7 ms away from the 33/34 ms frame boundaries, so the float modulo
    # of the second loop resolves the exact same frame indices).
    steps = [t0 + 0.01 + i * 0.05 for i in range(int(duration / 0.05) + 1)]
    for t in steps:
        source.tick(t)
    loop1_renders = len(uploads.calls) - 1  # minus the attach-time frame 0
    assert loop1_renders == len(source._frame_cache) - 1  # every render cached (frame 0 pre-seeded)
    for t in steps:
        source.tick(t + duration)  # second loop: swap-only
    assert len(uploads.calls) - 1 == loop1_renders


# ── lifecycle / teardown ─────────────────────────────────────────────


@requires_rlottie
@requires_demo
def test_self_heal_after_engine_texture_reset(uploads, sources):
    source, instance = make_source(sources, box=(50, 50), block={"autoplay": False})
    texture = instance.texture
    renders = len(uploads.calls)
    # scroll/dirty-sync/hot-reload call update_all(image_name=...) which
    # resets media textures to the ImageManager stub (None).
    instance.texture = None
    assert source.tick(1.0) is True
    assert instance.texture is texture
    assert len(uploads.calls) == renders  # heal is a swap, not a render


@requires_rlottie
@requires_demo
def test_retarget_releases_source(uploads, sources):
    source, instance = make_source(sources, box=(50, 50))
    instance.image_name = "something_else.png"
    assert source.tick(1.0) is False
    assert source.released is True
    assert source._animation is None  # rlottie C handle freed
    assert source.is_active() is False


@requires_rlottie
@requires_demo
def test_release_idempotent_and_frees_handle(uploads, sources):
    source, _ = make_source(sources, box=(50, 50))
    animation = source._animation
    source.release()
    assert source.released and source.instance is None and source._animation is None
    assert animation.animation_p is None  # C handle destroyed at release, not left to the GC
    assert source._frame_cache == {} and len(source._ring) == 0
    source.release()  # idempotent
    assert source.tick(2.0) is False and source.is_active() is False


@requires_rlottie
@requires_demo
def test_manager_shutdown_releases_lottie(uploads):
    from puree.media import media_manager

    instance = FakeInstance("demo_lottie.json", "lot_a", (50, 50))
    source = LottieSource("lot_a", "demo_lottie.json", str(DEMO), instance, block={})
    media_manager._sources["lot_a"] = source
    media_manager.controller_for("lot_a")
    media_manager.shutdown()
    assert source.released and source._animation is None
    assert media_manager._sources == {} and media_manager._controllers == {}


# ── manager attach / reconcile (matches_block hook) ──────────────────


@requires_rlottie
@requires_demo
def test_manager_attach_builds_and_reconciles(uploads, monkeypatch):
    # attach() resolves assets through puree.img_op (bpy) - inject a fake.
    from puree.media import media_manager

    fake_img_op = types.ModuleType("puree.img_op")
    fake_img_op.image_manager = types.SimpleNamespace(images={"demo_lottie.json": str(DEMO)})
    monkeypatch.setitem(sys.modules, "puree.img_op", fake_img_op)

    instance = FakeInstance("demo_lottie.json", "lot_x", (50, 50))
    block = {
        "container_id": "lot_x",
        "image_name": "demo_lottie.json",
        "media_kind": "lottie",
        "autoplay": True,
        "loop": True,
        "playback_rate": 1.0,
    }
    try:
        media_manager.attach({"lot_x": block}, [instance])
        source = media_manager.get_source("lot_x")
        assert isinstance(source, LottieSource)
        assert source.clock.playing  # the factory received the block (autoplay honored)

        media_manager.attach({"lot_x": block}, [instance])  # identical attach keeps the source
        assert media_manager.get_source("lot_x") is source

        changed = dict(block, playback_rate=2.0)  # YAML attr change rebuilds (matches_block)
        media_manager.attach({"lot_x": changed}, [instance])
        rebuilt = media_manager.get_source("lot_x")
        assert rebuilt is not source and source.released
        assert rebuilt.clock.playback_rate == pytest.approx(2.0)
    finally:
        media_manager.shutdown()


@requires_rlottie
@requires_demo
def test_matches_block_detects_playback_attr_changes(uploads, sources):
    source, _ = make_source(sources, block={})
    assert source.matches_block({})
    assert source.matches_block({"autoplay": True, "loop": True, "playback_rate": 1.0})
    assert not source.matches_block({"autoplay": False})
    assert not source.matches_block({"loop": False})
    assert not source.matches_block({"playback_rate": 2.0})


# ── container.media controller (duck-typed, no special-casing) ───────


@requires_rlottie
@requires_demo
def test_controller_binds_without_special_casing(uploads, sources):
    from puree.media import media_manager

    source, _ = make_source(sources, box=(50, 50), block={"autoplay": False}, container_id="cel")
    media_manager._sources["cel"] = source
    try:
        media = media_manager.controller_for("cel")
        assert media.paused is True and media.ended is False
        assert media.duration == pytest.approx(91 / 30.0, abs=0.002)
        assert media.ready_state == "ready"

        events = []
        media.on("play", lambda m: events.append("play"))
        media.on("pause", lambda m: events.append("pause"))
        media.on("seeked", lambda m: events.append("seeked"))

        media.play()
        media._pump()
        assert media.paused is False and events == ["play"]
        media.seek(1.0)
        media._pump()
        assert media.current_time == pytest.approx(1.0, abs=0.05)
        assert "seeked" in events
        media.toggle()
        media._pump()
        assert media.paused is True and events[-1] == "pause"

        # muted/volume are safe no-ops (lottie has no audio); loop and
        # playback_rate ride the shared clock through the fallbacks.
        media.muted = True
        assert source.muted is True
        media.volume = 0.25
        assert source.volume == pytest.approx(0.25)
        media.playback_rate = 2.0
        assert source.clock.playback_rate == pytest.approx(2.0)
        media.loop = False
        assert source.clock.loop is False
    finally:
        media_manager._sources.pop("cel", None)
        media_manager._controllers.pop("cel", None)


# ── engine plumbing: registry, Container, extractor ──────────────────


def test_registry_registers_json_for_lottie():
    from puree.media import MEDIA_EXTENSIONS, is_media_name
    from puree.media.decoders import SOURCE_FACTORIES, get_factory

    assert SOURCE_FACTORIES[".json"] is LottieSource
    assert get_factory(".JSON") is LottieSource
    assert ".json" in MEDIA_EXTENSIONS
    assert is_media_name("confetti.json") and is_media_name("anim/confetti.json")
    assert not is_media_name("confetti.lottie")  # .lottie zip container: plan non-goal (v1)


def test_container_lottie_attribute_and_media_property():
    from puree.components.container import Container
    from puree.media import media_manager

    c = Container()
    c.id = "cel"
    assert c.lottie == ""  # declared attribute (whitelisted, YAML-routable)
    c.lottie = "confetti.json"
    assert c.lottie == "confetti.json"
    try:
        assert c.media is not None  # controller resolves before attach
    finally:
        media_manager._controllers.pop("cel", None)

    plain = Container()
    plain.id = "plain"
    with pytest.raises(AttributeError, match="has no media source"):
        _ = plain.media


def test_container_tracks_authored_media_attrs():
    from puree.components.container import Container

    c = Container()
    assert c._authored_media_attrs == set()  # construction records nothing
    assert c.autoplay is False and c.loop is False  # shared HTML <video> defaults intact
    c.autoplay = False  # an author's explicit False must be distinguishable
    c.volume = 0.5
    assert "autoplay" in c._authored_media_attrs
    assert "volume" in c._authored_media_attrs
    assert "loop" not in c._authored_media_attrs
    c.loop = "true"  # stringified component param -> coerced AND recorded
    assert c.loop is True and "loop" in c._authored_media_attrs


def _node(node_id, **attrs):
    from puree.components.container import Container

    c = Container()
    c.id = node_id
    c.style = types.SimpleNamespace(aspect_ratio=True, img_align_h="CENTER", img_align_v="CENTER", opacity=1.0)
    for key, value in attrs.items():
        setattr(c, key, value)
    c._content_box_abs = {"x": 0, "y": 0, "width": 220, "height": 220}
    return c


def _extract(*nodes):
    import puree.extract_images as extract_images

    root = _node("root")
    root.children = list(nodes)
    for child in nodes:
        child.children = []
    ui = types.SimpleNamespace(theme=types.SimpleNamespace(root=root))
    return extract_images.ImageExtractor(ui, []).image_blocks


def test_extractor_lottie_defaults_true_and_authored_override():
    blocks = _extract(
        _node("plain_lottie", lottie="demo_lottie.json"),
        _node("tuned", lottie="demo_lottie.json", autoplay=False, loop=False, playback_rate=2.0),
    )
    plain = blocks["plain_lottie"]
    assert plain["media_kind"] == "lottie" and plain["image_name"] == "demo_lottie.json"
    assert plain["autoplay"] is True and plain["loop"] is True  # lottie-player defaults
    assert plain["playback_rate"] == 1.0
    assert "controls" not in plain and "muted" not in plain  # video-only keys stay off
    tuned = blocks["tuned"]
    assert tuned["autoplay"] is False and tuned["loop"] is False  # authored False respected
    assert tuned["playback_rate"] == 2.0


def test_extractor_precedence_img_video_lottie(monkeypatch):
    import puree.extract_images as extract_images

    recording = RecordingLogger()
    monkeypatch.setattr(extract_images, "logger", recording)
    blocks = _extract(
        _node("both_img", img="x.png", lottie="a.json"),
        _node("both_video", video="v.mp4", lottie="a.json"),
    )
    assert blocks["both_img"]["media_kind"] == "image"
    assert blocks["both_img"]["image_name"] == "x.png"  # img wins
    assert blocks["both_video"]["media_kind"] == "video"
    assert blocks["both_video"]["image_name"] == "v.mp4"  # video wins
    assert len(recording.warnings) == 2
    assert "img wins" in recording.warnings[0] and "video wins" in recording.warnings[1]


def test_extractor_ignores_controls_on_lottie():
    blocks = _extract(_node("with_controls", lottie="a.json", controls=True))
    block = blocks["with_controls"]
    assert block["media_kind"] == "lottie"
    assert "controls" not in block  # ignored with a debug note - controls is video-only
