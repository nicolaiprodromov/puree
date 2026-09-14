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
"""Unit tests for puree.media.clock - pure Python, no bpy/Blender needed.

The module is loaded directly from its file so the bpy-importing
``puree`` package __init__ never runs.
"""

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CLOCK_PATH = REPO_ROOT / "puree" / "media" / "clock.py"

_spec = importlib.util.spec_from_file_location("puree_media_clock", CLOCK_PATH)
clock = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(clock)

MediaClock = clock.MediaClock
cumulative_delays = clock.cumulative_delays
frame_index_at = clock.frame_index_at


def make_clock(delays_ms=(100, 100, 100), loop=True, rate=1.0, t0=0.0):
    """Clock with an injected, controllable time source starting at t0."""
    state = {"now": t0}
    c = MediaClock(delays_ms=list(delays_ms), loop=loop, playback_rate=rate, time_fn=lambda: state["now"])
    return c, state


def browser_clamped(delay_ms):
    """The delay normalization applied by the Rust decoder (browser rule):
    anything below 20 ms plays as 100 ms."""
    return 100 if delay_ms < 20 else delay_ms


# ── cumulative delays / frame boundaries ─────────────────────────────


def test_cumulative_delays_boundaries():
    assert cumulative_delays([100, 50, 200]) == [100, 150, 350]
    assert cumulative_delays([]) == []
    assert cumulative_delays([0, 10]) == [0, 10]  # zero delays collapse, no negatives


def test_frame_index_at_exclusive_upper_bounds():
    bounds = cumulative_delays([100, 50, 200])
    assert frame_index_at(0, bounds) == 0
    assert frame_index_at(99.9, bounds) == 0
    assert frame_index_at(100, bounds) == 1  # boundary belongs to the next frame
    assert frame_index_at(149.9, bounds) == 1
    assert frame_index_at(150, bounds) == 2
    assert frame_index_at(349.9, bounds) == 2
    assert frame_index_at(10_000, bounds) == 2  # clamps to the last frame


def test_frame_index_with_browser_clamped_delays():
    # Raw GIF delays of 0/10ms play as 100ms in browsers (and in our Rust
    # decoder) - the Python side just consumes the already-clamped values.
    raw = [10, 0, 250]
    clamped = [browser_clamped(d) for d in raw]
    assert clamped == [100, 100, 250]
    bounds = cumulative_delays(clamped)
    assert bounds == [100, 200, 450]
    assert frame_index_at(50, bounds) == 0
    assert frame_index_at(150, bounds) == 1
    assert frame_index_at(449, bounds) == 2


# ── play / pause / toggle ────────────────────────────────────────────


def test_starts_paused_at_zero():
    c, _ = make_clock()
    assert c.paused and not c.playing
    assert c.current_time == 0.0
    assert c.frame_index() == 0
    assert not c.is_active()


def test_play_advances_with_time():
    c, state = make_clock()
    c.play()
    state["now"] = 0.15
    assert c.playing
    assert abs(c.current_time - 0.15) < 1e-9
    assert c.frame_index() == 1
    assert c.is_active()


def test_pause_freezes_time():
    c, state = make_clock()
    c.play()
    state["now"] = 0.12
    c.pause()
    state["now"] = 5.0
    assert c.paused
    assert abs(c.current_time - 0.12) < 1e-9
    assert c.frame_index() == 1
    assert not c.is_active()


def test_toggle_flips_state():
    c, state = make_clock()
    c.toggle()
    assert c.playing
    state["now"] = 0.05
    c.toggle()
    assert c.paused
    assert abs(c.current_time - 0.05) < 1e-9


def test_play_while_playing_is_noop():
    c, state = make_clock()
    c.play()
    state["now"] = 0.1
    c.play()  # must not reset the start timestamp
    state["now"] = 0.2
    assert abs(c.current_time - 0.2) < 1e-9


# ── seek ─────────────────────────────────────────────────────────────


def test_seek_clamps_to_duration():
    c, _ = make_clock(delays_ms=(100, 100, 100), loop=False)  # duration 0.3s
    c.seek(0.25)
    assert abs(c.current_time - 0.25) < 1e-9
    c.seek(99.0)  # clamps to duration -> end of the single allowed play
    assert abs(c.current_time - 0.3) < 1e-9
    assert c.ended
    c.seek(-5.0)
    assert c.current_time == 0.0


def test_seek_to_duration_wraps_on_looping_media():
    # On an infinite loop the end IS the start (HTML: currentTime = duration
    # on a looping element wraps) - seeking to the clamp point reads back 0.
    c, _ = make_clock(delays_ms=(100, 100, 100), loop=True)
    c.seek(99.0)
    assert c.current_time == 0.0
    assert not c.ended


def test_seek_while_playing_continues_from_target():
    c, state = make_clock()
    c.play()
    state["now"] = 0.05
    c.seek(0.2)
    state["now"] = 0.10
    assert abs(c.current_time - 0.25) < 1e-9
    assert c.frame_index() == 2


# ── loop semantics ───────────────────────────────────────────────────


def test_infinite_loop_wraps_and_never_ends():
    c, state = make_clock(loop=True)
    c.play()
    state["now"] = 0.31  # past one 0.3s iteration
    assert not c.ended
    assert abs(c.current_time - 0.01) < 1e-9
    assert c.frame_index() == 0
    state["now"] = 100.05
    assert not c.ended
    assert c.is_active()


def test_loop_zero_means_infinite_gif_convention():
    c, state = make_clock(loop=0)
    c.play()
    state["now"] = 3.0
    assert not c.ended


def test_loop_false_plays_once_then_ends():
    c, state = make_clock(loop=False)
    c.play()
    state["now"] = 0.29
    assert not c.ended
    state["now"] = 0.30
    assert c.ended
    assert c.current_time == c.duration
    assert c.frame_index() == 2  # holds the last frame
    assert not c.is_active()


def test_loop_count_plays_n_times():
    c, state = make_clock(loop=2)
    c.play()
    state["now"] = 0.45  # inside the 2nd play
    assert not c.ended
    assert abs(c.current_time - 0.15) < 1e-9
    state["now"] = 0.60  # 2 x 0.3s consumed
    assert c.ended
    assert c.frame_index() == 2


def test_play_after_ended_restarts_from_zero():
    c, state = make_clock(loop=False)
    c.play()
    state["now"] = 0.5
    assert c.ended
    c.pause()
    c.play()
    assert not c.ended
    state["now"] = 0.55
    assert abs(c.current_time - 0.05) < 1e-9


def test_seek_after_ended_clears_ended_until_end_again():
    c, state = make_clock(loop=False)
    c.play()
    state["now"] = 1.0
    assert c.ended
    c.seek(0.1)
    assert not c.ended
    assert abs(c.current_time - 0.1) < 1e-9
    state["now"] = 1.25  # 0.1 + 0.25 > 0.3 (clear of float boundary noise)
    assert c.ended  # reached the end of the last allowed iteration again


# ── playback rate ────────────────────────────────────────────────────


def test_rate_scales_elapsed_time():
    c, state = make_clock(rate=2.0)
    c.play()
    state["now"] = 0.1
    assert abs(c.current_time - 0.2) < 1e-9
    assert c.frame_index() == 2


def test_rate_change_preserves_played_time():
    c, state = make_clock()
    c.play()
    state["now"] = 0.1  # 0.1s at 1x
    c.playback_rate = 3.0
    state["now"] = 0.15  # +0.05s at 3x = +0.15s
    assert abs(c.current_time - 0.25) < 1e-9
    assert c.playback_rate == 3.0


def test_rate_zero_freezes_playback_but_stays_playing():
    c, state = make_clock()
    c.play()
    state["now"] = 0.1
    c.playback_rate = 0.0
    state["now"] = 9.9
    assert abs(c.current_time - 0.1) < 1e-9
    assert c.playing


def test_negative_rate_clamps_to_zero():
    c, _ = make_clock(rate=-2.0)
    assert c.playback_rate == 0.0


# ── degenerate media ─────────────────────────────────────────────────


def test_empty_delays_is_inert():
    c, state = make_clock(delays_ms=())
    assert c.duration == 0.0
    c.play()
    state["now"] = 5.0
    assert c.current_time == 0.0
    assert c.frame_index() == 0
    assert not c.is_active()  # zero-duration media never gates redraws
    c.seek(1.0)  # must not raise


def test_frame_count():
    c, _ = make_clock(delays_ms=(100, 50))
    assert c.frame_count == 2
