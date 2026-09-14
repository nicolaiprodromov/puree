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
"""Unit tests for the Rust ``decode_gif`` core function.

Imports the built ``puree_rust_core`` binary directly (abi3 - importable
by any Python >= 3.11, no Blender needed). Skips cleanly when the binary
for this platform has not been built (`just build_core`).
"""

import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
NATIVE_DIR = REPO_ROOT / "puree" / "native_binaries"
PYD = NATIVE_DIR / ("puree_rust_core.pyd" if sys.platform == "win32" else "puree_rust_core.so")

GIF_MUNKY = REPO_ROOT / "docs" / "images" / "munky.gif"
GIF_ASSET = REPO_ROOT / "assets" / "demo_munky.gif"

pytestmark = pytest.mark.skipif(
    not PYD.exists(),
    reason=f"native core not built for this platform ({PYD.name}) - run `just build_core`",
)


@pytest.fixture(scope="module")
def core():
    sys.path.insert(0, str(NATIVE_DIR))
    try:
        return importlib.import_module("puree_rust_core")
    finally:
        sys.path.remove(str(NATIVE_DIR))


@pytest.fixture(scope="module")
def munky(core):
    return core.decode_gif(str(GIF_MUNKY))


def test_shape_and_frame_sizes(munky):
    width, height, frames, delays_ms, _loop = munky
    assert (width, height) == (320, 240)
    assert len(frames) > 1, "munky.gif is animated"
    # Disposal-method compositing: every frame must be a FULL canvas even
    # though GIF frames are stored as partial patches.
    assert all(len(f) == width * height * 4 for f in frames)
    assert all(isinstance(f, bytes) for f in frames)
    assert len(delays_ms) == len(frames)


def test_delays_populated_and_clamped(munky):
    _w, _h, _frames, delays_ms, _loop = munky
    # Browser rule baked into the decoder: raw delays below 20ms play as
    # 100ms, so nothing below 20 can ever come out (0 falls back to 100).
    assert all(d >= 20 for d in delays_ms)
    assert all(isinstance(d, int) for d in delays_ms)


def test_loop_count_infinite(munky):
    # munky.gif carries a Netscape loop extension with value 0 = forever.
    _w, _h, _frames, _delays, loop = munky
    assert loop == 0


def test_premultiplied_alpha(munky):
    # Premultiplied RGBA: no color channel may exceed its alpha.
    _w, _h, frames, _delays, _loop = munky
    for frame in (frames[0], frames[len(frames) // 2], frames[-1]):
        for i in range(0, len(frame), 4):
            r, g, b, a = frame[i], frame[i + 1], frame[i + 2], frame[i + 3]
            assert r <= a and g <= a and b <= a, f"straight alpha at byte {i}: {(r, g, b, a)}"


def test_frames_differ(munky):
    _w, _h, frames, _delays, _loop = munky
    assert any(frames[0] != f for f in frames[1:]), "animation frames should not all be identical"


@pytest.mark.skipif(not GIF_ASSET.exists(), reason="demo asset missing")
def test_demo_asset_decodes(core):
    width, height, frames, delays_ms, loop = core.decode_gif(str(GIF_ASSET))
    assert width > 0 and height > 0
    assert len(frames) > 1
    assert len(delays_ms) == len(frames)
    # Fits the 32 MB pre-upload budget (keeps the helloworld demo on the
    # all-frames-resident GPU path).
    assert width * height * 4 * len(frames) <= 32 * 1024 * 1024


def test_missing_file_raises_ioerror(core):
    with pytest.raises(IOError):
        core.decode_gif(str(REPO_ROOT / "does_not_exist.gif"))


def test_non_gif_raises_valueerror(core):
    with pytest.raises(ValueError):
        core.decode_gif(str(REPO_ROOT / "assets" / "loggoui2.png"))
