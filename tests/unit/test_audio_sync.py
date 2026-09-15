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
"""Unit tests for Phase 4 audio + sync - no bpy/Blender needed.

``aud`` only exists inside Blender, so a controllable FakeAud module is
injected via ``sys.modules`` (``puree.media.audio`` imports aud lazily
inside functions). Fake handles mirror the real aud contract used by
AudioTrack: ``position`` auto-advances in real monotonic time while
PLAYING and the handle auto-stops at the sound's natural end
(``keep=False`` behavior); ``stop()`` invalidates; ``pause``/``resume``
keep the handle alive. That lets the audio-master-clock policy (drift
resync, mute/unmute, decision-4 rate suppression, loop wrap, teardown)
run for real without Blender.

VideoSource-level tests decode ``tests/unit/fixtures/tone_video.mp4`` -
a tiny generated container WITH an AAC audio stream (built on first use
by ``_make_fixture.ensure_tone_video``; none of the committed demo mp4s
carry audio). Those tests need PyAV in the dev environment (in-Blender it
ships bundled with Puree) and skip without it; the AudioTrack-level tests
always run.
"""

import sys
import time
import types
from importlib.util import find_spec
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
DEMO_CLIP = ADDON_DIR / "assets" / "demo_clip.mp4"


def _ensure_puree_package():
    pkg = sys.modules.get("puree")
    if pkg is None:
        pkg = types.ModuleType("puree")
        pkg.__path__ = [str(REPO_ROOT / "puree")]
        sys.modules["puree"] = pkg
    return pkg


_ensure_puree_package()

import puree.media.audio as audio_mod  # noqa: E402
import puree.media.decoders.video as video_mod  # noqa: E402
from puree.media.audio import STATUS_PAUSED, STATUS_PLAYING, STATUS_STOPPED, AudioTrack  # noqa: E402
from puree.media.decoders.video import VideoSource  # noqa: E402

HAS_AV = find_spec("av") is not None
requires_av = pytest.mark.skipif(not HAS_AV, reason="PyAV not installed in this dev env (python -m pip install av)")
requires_demo_clip = pytest.mark.skipif(not DEMO_CLIP.exists(), reason="tests/helloworld/assets/demo_clip.mp4 missing")

# ── FakeAud (the sys.modules-injected stand-in for Blender's aud) ────


class FakeAudError(Exception):
    pass


def make_fake_aud(sound_length=3.0):
    """A fake ``aud`` module mirroring the parts AudioTrack relies on."""
    state = types.SimpleNamespace(
        sound_length=sound_length,  # every FakeSound reports this length
        auto_end=True,  # handles stop at the sound's end, like keep=False
        fail_device=False,  # aud.Device() raises
        fail_open=False,  # aud.Sound() raises (unsupported container)
        fail_position=False,  # handle.position get/set raises
        device_count=0,
        lock_count=0,
        unlock_count=0,
        sounds=[],
        handles=[],
    )

    class Sound:
        def __init__(self, path, stream=0):
            if state.fail_open:
                raise FakeAudError(f"unsupported container: {path}")
            self.path = path
            self.length = state.sound_length
            state.sounds.append(self)

    class Handle:
        def __init__(self, sound):
            self.sound = sound
            self._status = STATUS_PLAYING
            self._base = 0.0
            self._anchor = time.monotonic()
            self._volume = 1.0
            self.volume_history = []
            state.handles.append(self)

        def _raw_position(self):
            if self._status == STATUS_PLAYING:
                return self._base + (time.monotonic() - self._anchor)
            return self._base

        def _auto_stop(self):
            if state.auto_end and self._status == STATUS_PLAYING and self._raw_position() >= self.sound.length:
                self._base = self.sound.length
                self._status = STATUS_STOPPED

        @property
        def status(self):
            self._auto_stop()
            return self._status

        @property
        def position(self):
            if state.fail_position:
                raise FakeAudError("position read failed")
            self._auto_stop()
            return self._raw_position()

        @position.setter
        def position(self, value):
            if state.fail_position:
                raise FakeAudError("position write failed")
            self._auto_stop()
            self._base = float(value)
            self._anchor = time.monotonic()

        @property
        def volume(self):
            return self._volume

        @volume.setter
        def volume(self, value):
            self._volume = float(value)
            self.volume_history.append(float(value))

        def pause(self):
            self._auto_stop()
            if self._status != STATUS_PLAYING:
                return False
            self._base = self._raw_position()
            self._status = STATUS_PAUSED
            return True

        def resume(self):
            if self._status != STATUS_PAUSED:
                return False
            self._anchor = time.monotonic()
            self._status = STATUS_PLAYING
            return True

        def stop(self):
            self._base = self._raw_position()
            self._status = STATUS_STOPPED
            return True

    class Device:
        def __init__(self, *args, **kwargs):
            if state.fail_device:
                raise FakeAudError("no audio backend")
            state.device_count += 1

        def play(self, sound, keep=False):
            return Handle(sound)

        def lock(self):
            state.lock_count += 1

        def unlock(self):
            state.unlock_count += 1

        def stopAll(self):
            for handle in list(state.handles):
                handle.stop()

    mod = types.ModuleType("aud")
    mod.Sound = Sound
    mod.Device = Device
    mod.error = FakeAudError
    mod.STATUS_INVALID = 0
    mod.STATUS_PLAYING = STATUS_PLAYING
    mod.STATUS_PAUSED = STATUS_PAUSED
    mod.STATUS_STOPPED = STATUS_STOPPED
    mod._state = state
    return mod


# ── harness (mirrors test_video_source) ──────────────────────────────


class FakeTexture:
    def __init__(self, width, height, data=None):
        self.width = width
        self.height = height
        self.data = data


class UploadRecorder:
    def __init__(self):
        self.calls = []

    def __call__(self, width, height, data):
        self.calls.append((width, height, len(data)))
        return FakeTexture(width, height, data)


class FakeInstance:
    def __init__(self, image_name, container_id="vid_audio"):
        self.container_id = container_id
        self.image_name = image_name
        self.texture = None
        self.batch = None
        self.size = [100, 100]

    def _create_batch(self):
        self.batch = "batch"


class RecordingLogger:
    def __init__(self):
        self.infos = []
        self.warnings = []

    def info(self, msg, *args, **kwargs):
        self.infos.append(str(msg))

    def warning(self, msg, *args, **kwargs):
        self.warnings.append(str(msg))

    def __getattr__(self, name):  # debug/error - swallow
        return lambda *args, **kwargs: None


@pytest.fixture
def fake_aud(monkeypatch):
    """Inject FakeAud + reset the shared-device singleton for the test."""
    mod = make_fake_aud()
    monkeypatch.setitem(sys.modules, "aud", mod)
    monkeypatch.setattr(audio_mod, "_device", None)
    monkeypatch.setattr(audio_mod, "_device_failed", False)
    return mod


@pytest.fixture
def no_aud(monkeypatch):
    """Make ``import aud`` fail (headless Blender-less environment)."""
    monkeypatch.setitem(sys.modules, "aud", None)  # import aud -> ImportError
    monkeypatch.setattr(audio_mod, "_device", None)
    monkeypatch.setattr(audio_mod, "_device_failed", False)


@pytest.fixture
def audio_log(monkeypatch):
    recording = RecordingLogger()
    monkeypatch.setattr(audio_mod, "logger", recording)
    return recording


@pytest.fixture
def video_log(monkeypatch):
    recording = RecordingLogger()
    monkeypatch.setattr(video_mod, "logger", recording)
    return recording


@pytest.fixture
def uploads(monkeypatch):
    recorder = UploadRecorder()
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


@pytest.fixture(scope="module")
def tone_clip():
    """The generated A/V fixture (tiny h264 + AAC tone), built on first use."""
    if not HAS_AV:
        pytest.skip("PyAV not installed in this dev env (python -m pip install av)")
    try:
        from _make_fixture import ensure_tone_video

        path = ensure_tone_video()
    except Exception as e:  # pragma: no cover - numpy/encoder missing
        pytest.skip(f"could not generate tone_video.mp4: {e}")
    assert path.stat().st_size < 200 * 1024, "fixture must stay tiny (< 200 KB)"
    return path


def make_source(sources, clip, block=None, name="tone_video.mp4", container_id="vid_audio"):
    instance = FakeInstance(name, container_id)
    source = VideoSource(container_id, name, str(clip), instance, block=block or {})
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


def pump(source, predicate, timeout=10.0):
    """Tick the source (main-thread style) until *predicate* holds."""
    return wait_for(lambda: (source.tick(time.monotonic()) or True) and predicate(), timeout=timeout)


# ── AudioTrack (FakeAud; no av, no clip needed) ──────────────────────


def test_track_inert_without_aud(no_aud, audio_log):
    track = AudioTrack(label="t")
    assert track.open("whatever.mp4") is False
    assert track.available is False
    # every method is a safe no-op in the inert state
    assert track.play(1.0) is False
    track.pause()
    track.resume()
    track.seek(2.0)
    track.stop()
    track.release()
    assert track.position is None
    assert track.playing is False
    assert audio_log.warnings == []  # missing aud is normal outside Blender


def test_track_open_play_position_shared_device(fake_aud, audio_log):
    state = fake_aud._state
    track_a = AudioTrack(label="a")
    track_b = AudioTrack(label="b")
    assert track_a.open("a.mp4") is True and track_a.available
    assert track_b.open("b.mp4") is True
    assert state.device_count == 1  # ONE aud.Device per session, shared
    assert track_a.duration == pytest.approx(3.0)

    assert track_a.play(1.0) is True
    handle = state.handles[-1]
    assert handle.status == STATUS_PLAYING
    assert track_a.playing is True
    assert track_a.position == pytest.approx(1.0, abs=0.2)
    assert state.lock_count == 1 and state.unlock_count == 1  # atomic start
    assert handle.volume == pytest.approx(1.0)
    track_a.release()
    track_b.release()
    assert handle.status == STATUS_STOPPED
    assert audio_log.warnings == []


def test_track_device_failure_warns_once_for_session(fake_aud, audio_log):
    fake_aud._state.fail_device = True
    track_a = AudioTrack(label="a")
    track_b = AudioTrack(label="b")
    assert track_a.open("a.mp4") is False
    assert track_b.open("b.mp4") is False  # second open never re-probes
    assert len(audio_log.warnings) == 1
    assert "audio output unavailable" in audio_log.warnings[0]


def test_track_open_failure_warns_once(fake_aud, audio_log):
    fake_aud._state.fail_open = True
    track = AudioTrack(label="bad.mp4")
    assert track.open("bad.mp4") is False  # aud raises on unsupported containers
    assert track.available is False
    assert track.play(0.0) is False  # inert afterwards
    track.seek(1.0)
    assert len(audio_log.warnings) == 1
    assert "bad.mp4" in audio_log.warnings[0]


def test_track_pause_resume_and_dead_handle_fallback(fake_aud):
    state = fake_aud._state
    track = AudioTrack(label="t")
    track.open("t.mp4")
    track.play(0.5)
    track.pause()
    assert track.paused is True and track.playing is False
    frozen = track.position
    time.sleep(0.03)
    assert track.position == pytest.approx(frozen)  # paused position is frozen
    track.resume()
    assert track.playing is True  # same handle resumed
    assert len(state.handles) == 1

    # dead-handle fallback: the paused handle dies -> resume() replays at
    # the remembered pause position on a fresh handle
    track.pause()
    remembered = track._paused_position
    state.handles[-1].stop()
    track.resume()
    assert track.playing is True
    assert len(state.handles) == 2
    assert track.position == pytest.approx(remembered, abs=0.2)


def test_track_stop_is_idempotent_and_replayable(fake_aud):
    track = AudioTrack(label="t")
    track.open("t.mp4")
    track.play(0.0)
    track.stop()
    track.stop()  # idempotent
    assert track.position is None and track.playing is False
    assert track.available is True  # stop never degrades the track
    assert track.play(0.25) is True  # fresh handle after a stop
    assert track.position == pytest.approx(0.25, abs=0.2)


def test_track_error_degrades_inert_with_one_warning(fake_aud, audio_log):
    state = fake_aud._state
    track = AudioTrack(label="t")
    track.open("t.mp4")
    track.play(0.0)
    handle = state.handles[-1]
    state.fail_position = True
    assert track.position is None  # aud raised -> degraded, not crashed
    assert track.available is False
    assert handle.status == STATUS_STOPPED  # failed track stops its handle
    assert len(audio_log.warnings) == 1
    # inert from here on - no retries, no more warnings
    assert track.play(1.0) is False
    track.seek(2.0)
    assert len(audio_log.warnings) == 1


def test_track_volume_clamps_and_updates_live_handle(fake_aud):
    state = fake_aud._state
    track = AudioTrack(label="t")
    track.open("t.mp4")
    track.volume = 0.8  # before any handle - stored
    track.play(0.0)
    handle = state.handles[-1]
    assert handle.volume == pytest.approx(0.8)
    track.volume = 0.3  # live handle update
    assert handle.volume == pytest.approx(0.3)
    track.volume = 5.0
    assert track.volume == 1.0 and handle.volume == 1.0  # clamped high
    track.volume = -2.0
    assert track.volume == 0.0  # clamped low
    track.volume = "nonsense"
    assert track.volume == 0.0  # bad input ignored


# ── VideoSource integration (needs av + the generated fixture) ───────


@requires_av
def test_probe_detects_audio_stream(uploads, sources, tone_clip):
    source, _ = make_source(sources, tone_clip)  # preload: metadata
    assert source.has_audio is True
    assert source.duration == pytest.approx(3.0, abs=0.25)


@requires_av
@requires_demo_clip
def test_probe_detects_missing_audio_stream(uploads, sources):
    # The committed demo asset is video-only - the helloworld tile is
    # silent by nature; the audio path is exercised by the tone fixture.
    source, _ = make_source(sources, DEMO_CLIP, name="demo_clip.mp4")
    assert source.has_audio is False


@requires_av
def test_play_starts_audio_at_clock_time(fake_aud, uploads, sources, tone_clip):
    state = fake_aud._state
    source, _ = make_source(sources, tone_clip)
    source.play()
    assert len(state.sounds) == 1 and len(state.handles) == 1
    handle = state.handles[-1]
    assert handle.status == STATUS_PLAYING
    assert handle.position == pytest.approx(source.clock.current_time, abs=0.2)
    assert state.lock_count == state.unlock_count == 1


@requires_av
def test_audio_master_resync_beyond_threshold_only(fake_aud, uploads, sources, tone_clip, monkeypatch):
    state = fake_aud._state
    source, _ = make_source(sources, tone_clip)
    source.play()
    handle = state.handles[-1]

    seeks = []
    original_seek = source.clock.seek
    monkeypatch.setattr(source.clock, "seek", lambda *a, **k: (seeks.append(a), original_seek(*a, **k)))

    # drift within ~80 ms -> the clock is left alone
    handle.position = source.clock.current_time + 0.03
    source.tick(time.monotonic())
    assert seeks == []

    # drift beyond the threshold -> MediaClock resyncs TO the audio position
    handle.position = 1.2
    source.tick(time.monotonic())
    assert len(seeks) == 1
    assert source.clock.current_time == pytest.approx(1.2, abs=0.1)
    # frame selection now follows the corrected clock (same tick ordering)
    assert source.clock.playing


@requires_av
def test_mute_stops_audio_without_time_jump(fake_aud, uploads, sources, tone_clip):
    state = fake_aud._state
    source, _ = make_source(sources, tone_clip)
    source.play()
    handle = state.handles[-1]
    source.tick(time.monotonic())  # audio-master tick

    before = source.clock.current_time
    source.set_muted(True)
    after = source.clock.current_time
    assert handle.status == STATUS_STOPPED  # audio stopped...
    assert after >= before - 1e-6
    assert after - before < 0.1  # ...clock continues from the same time
    assert source.clock.playing

    source.tick(time.monotonic())
    assert len(state.handles) == 1  # muted playback never restarts audio


@requires_av
def test_unmute_mid_play_starts_audio_at_current_time_and_masters(fake_aud, uploads, sources, tone_clip):
    state = fake_aud._state
    source, _ = make_source(sources, tone_clip, block={"muted": True})
    source.play()
    source.seek(1.0)
    assert state.sounds == [] and state.handles == []  # muted -> aud untouched

    source.set_muted(False)
    handle = state.handles[-1]
    assert handle.status == STATUS_PLAYING
    assert handle.position == pytest.approx(source.clock.current_time, abs=0.15)

    # ...and audio is the master clock from here on
    source.tick(time.monotonic())
    handle.position = 2.0
    source.tick(time.monotonic())
    assert source.clock.current_time == pytest.approx(2.0, abs=0.1)


@requires_av
def test_playback_rate_suppresses_audio_and_restores(fake_aud, uploads, sources, tone_clip, video_log):
    state = fake_aud._state
    source, _ = make_source(sources, tone_clip)
    source.play()
    first = state.handles[-1]

    source.set_playback_rate(2.0)  # decision 4: rate != 1.0 forces mute
    assert first.status == STATUS_STOPPED
    suppression_logs = [m for m in video_log.infos if "forces mute" in m]
    assert len(suppression_logs) == 1  # logged once per source
    source.tick(time.monotonic())
    assert len(state.handles) == 1  # stays silent while rate != 1

    source.set_playback_rate(0.5)  # still suppressed - no second log
    assert len([m for m in video_log.infos if "forces mute" in m]) == 1

    source.set_playback_rate(1.0)  # restore -> audio resumes at current time
    second = state.handles[-1]
    assert second is not first and second.status == STATUS_PLAYING
    assert second.position == pytest.approx(source.clock.current_time, abs=0.15)


@requires_av
def test_playback_rate_from_yaml_block_suppresses_audio(fake_aud, uploads, sources, tone_clip, video_log):
    state = fake_aud._state
    source, _ = make_source(sources, tone_clip, block={"playback_rate": 2.0, "autoplay": True})
    assert source.clock.playing
    source.tick(time.monotonic())
    assert state.handles == []  # audio never starts at rate != 1.0
    assert len([m for m in video_log.infos if "forces mute" in m]) == 1


@requires_av
def test_seek_moves_live_audio_handle_and_keeps_master(fake_aud, uploads, sources, tone_clip):
    state = fake_aud._state
    source, _ = make_source(sources, tone_clip)
    source.play()
    handle = state.handles[-1]

    source.seek(1.5)
    assert len(state.handles) == 1  # the LIVE handle seeked - no restart
    assert handle.position == pytest.approx(1.5, abs=0.15)
    assert source.clock.current_time == pytest.approx(1.5, abs=0.1)

    # master role kept after the seek
    source.tick(time.monotonic())
    handle.position = 0.5
    source.tick(time.monotonic())
    assert source.clock.current_time == pytest.approx(0.5, abs=0.1)


@requires_av
def test_pause_parks_audio_play_realigns(fake_aud, uploads, sources, tone_clip):
    state = fake_aud._state
    source, _ = make_source(sources, tone_clip)
    source.play()
    first = state.handles[-1]

    source.pause()
    assert first.status == STATUS_PAUSED  # parked (handle.pause()), not stopped
    frozen = first.position
    time.sleep(0.03)
    assert first.position == pytest.approx(frozen)

    source.play()  # resume: fresh handle aligned to the clock position
    second = state.handles[-1]
    assert second is not first
    assert first.status == STATUS_STOPPED  # old handle replaced
    assert second.status == STATUS_PLAYING
    assert second.position == pytest.approx(source.clock.current_time, abs=0.15)


@requires_av
def test_loop_wrap_reseeks_audio_with_the_clock(fake_aud, uploads, sources, tone_clip):
    state = fake_aud._state
    source, _ = make_source(sources, tone_clip, block={"loop": True})
    source.play()
    source.seek(source.duration - 0.3)
    first = state.handles[-1]

    # the fake handle auto-stops at the audio stream's natural end; the
    # clock wraps at duration and the next tick restarts audio at ~0
    assert pump(source, lambda: source.clock.current_time < 1.0 and len(state.handles) > 1, timeout=8.0)
    second = state.handles[-1]
    assert second is not first
    assert second.status == STATUS_PLAYING
    assert second.position == pytest.approx(source.clock.current_time, abs=0.2)
    assert not source.clock.ended


@requires_av
def test_ended_non_loop_stops_audio(fake_aud, uploads, sources, tone_clip):
    state = fake_aud._state
    source, _ = make_source(sources, tone_clip)
    source.play()
    source.seek(source.duration - 0.3)
    handle = state.handles[-1]

    assert pump(source, lambda: source.clock.ended, timeout=8.0)
    assert handle.status == STATUS_STOPPED
    assert source._audio is not None and source._audio.position is None
    assert len(state.handles) == 1  # never restarted after the end


@requires_av
def test_manager_shutdown_stops_audio_handles(fake_aud, uploads, tone_clip):
    from puree.media import media_manager

    state = fake_aud._state
    instance = FakeInstance("tone_video.mp4", "vid_shutdown")
    source = VideoSource("vid_shutdown", "tone_video.mp4", str(tone_clip), instance, block={"autoplay": True})
    media_manager._sources["vid_shutdown"] = source
    handle = state.handles[-1]
    assert handle.status == STATUS_PLAYING

    media_manager.shutdown()
    assert handle.status == STATUS_STOPPED  # no orphaned audio
    assert source.released and source._audio is None
    assert media_manager._sources == {}
    assert all(h.status == STATUS_STOPPED for h in state.handles)


@requires_av
@requires_demo_clip
def test_video_without_audio_stream_never_touches_aud(fake_aud, uploads, sources):
    state = fake_aud._state
    source, _ = make_source(sources, DEMO_CLIP, name="demo_clip.mp4", block={"autoplay": True})
    assert source.has_audio is False
    wait_for(lambda: source.tick(time.monotonic()))
    assert state.sounds == [] and state.handles == []
    assert state.device_count == 0  # the shared device is never even created


@requires_av
def test_aud_missing_video_still_plays_on_monotonic_clock(no_aud, uploads, sources, tone_clip, audio_log):
    source, _ = make_source(sources, tone_clip, block={"autoplay": True})
    assert source.has_audio is True
    assert wait_for(lambda: source.tick(time.monotonic())), "tick never produced a frame"
    assert source.clock.playing
    assert source._audio is not None and source._audio.available is False
    assert audio_log.warnings == []  # aud missing is silent (debug only)


@requires_av
def test_aud_error_mid_play_degrades_and_playback_continues(fake_aud, uploads, sources, tone_clip, audio_log):
    state = fake_aud._state
    source, _ = make_source(sources, tone_clip)
    source.play()
    handle = state.handles[-1]
    source.tick(time.monotonic())

    state.fail_position = True  # aud starts raising mid-play
    source.tick(time.monotonic())  # must not crash the tick
    assert source._audio.available is False
    assert handle.status == STATUS_STOPPED
    assert len(audio_log.warnings) == 1

    before = len(audio_log.warnings)
    assert wait_for(lambda: source.tick(time.monotonic())), "video stalled after audio failure"
    assert source.clock.playing  # monotonic clock took over
    assert len(audio_log.warnings) == before  # no warning spam


@requires_av
def test_volume_set_updates_live_handle(fake_aud, uploads, sources, tone_clip):
    state = fake_aud._state
    source, _ = make_source(sources, tone_clip, block={"volume": 0.8})
    source.play()
    handle = state.handles[-1]
    assert handle.volume == pytest.approx(0.8)  # YAML volume applied at start
    source.set_volume(0.3)
    assert handle.volume == pytest.approx(0.3)  # live update
    source.set_volume(7)
    assert handle.volume == 1.0 and source.volume == 1.0  # clamped
