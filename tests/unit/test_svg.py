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
"""Unit tests for SVG media support - Rust rasterizer + SvgSource.

Rust level: imports the built ``puree_rust_core`` binary directly (abi3,
no Blender needed) and exercises ``probe_svg``/``rasterize_svg`` against
the committed demo asset plus tiny inline SVGs. Skips cleanly when the
binary for this platform has not been built (`just build_core`).

Python level: loads ``puree/media/decoders/svg.py`` (and the shared
``upload.py``) under a synthetic package with a stubbed ``gpu`` module
and a call-counting ``native_bindings`` shim wrapping the real core -
the same headless pattern Phase 1 used - to test aspect-fit seeding,
the debounced size-watch, the (path, w, h) raster cache and the
is_active/tick contract without bpy.
"""

import importlib
import importlib.util
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ADDON_DIR = REPO_ROOT / "tests" / "helloworld"  # the dev addon (assets/, fonts/, wheels/)
_PYD_NAME = "puree_rust_core.pyd" if sys.platform == "win32" else "puree_rust_core.so"


def _native_dir():
    """Same lookup as puree.native_bindings: native_binaries/<platform id>/ first, then the flat legacy folder."""
    import platform

    arch = "arm64" if platform.machine().lower() in ("arm64", "aarch64") else "x64"
    os_name = "windows" if sys.platform.startswith("win") else ("macos" if sys.platform == "darwin" else "linux")
    root = REPO_ROOT / "puree" / "native_binaries"
    for candidate in (root / f"{os_name}-{arch}", root):
        if (candidate / _PYD_NAME).exists():
            return candidate
    return root / f"{os_name}-{arch}"


NATIVE_DIR = _native_dir()
PYD = NATIVE_DIR / _PYD_NAME
MEDIA_DIR = REPO_ROOT / "puree" / "media"

DEMO_SVG = ADDON_DIR / "assets" / "demo_vector.svg"

pytestmark = pytest.mark.skipif(
    not PYD.exists(),
    reason=f"native core not built for this platform ({PYD.name}) - run `just build_core`",
)

# Synthetic package name for the headless module loads (never collides
# with the real, bpy-importing ``puree`` package).
PKG = "puree_svgtest"


@pytest.fixture(scope="module")
def core():
    sys.path.insert(0, str(NATIVE_DIR))
    try:
        return importlib.import_module("puree_rust_core")
    finally:
        sys.path.remove(str(NATIVE_DIR))


# ---------------------------------------------------------------------
# Rust core: probe_svg / rasterize_svg
# ---------------------------------------------------------------------


def _px(data, width, x, y):
    i = (y * width + x) * 4
    return tuple(data[i : i + 4])


def test_probe_demo_asset_viewbox_size(core):
    # demo_vector.svg has no width/height attributes: the intrinsic size
    # must come from its viewBox (0 0 240 180).
    w, h = core.probe_svg(str(DEMO_SVG))
    assert (w, h) == (240.0, 180.0)


def test_probe_missing_file_raises_ioerror(core):
    with pytest.raises(IOError):
        core.probe_svg(str(REPO_ROOT / "does_not_exist.svg"))


def test_rasterize_demo_dimensions_and_premultiplied(core):
    width, height = 240, 180
    data = core.rasterize_svg(str(DEMO_SVG), width, height)
    assert isinstance(data, bytes)
    assert len(data) == width * height * 4
    assert any(data), "raster should not be empty"
    # Premultiplied RGBA: no color channel may exceed its alpha.
    for i in range(0, len(data), 4):
        r, g, b, a = data[i], data[i + 1], data[i + 2], data[i + 3]
        assert r <= a and g <= a and b <= a, f"straight alpha at byte {i}: {(r, g, b, a)}"


def test_rasterize_scales_to_requested_size(core):
    data = core.rasterize_svg(str(DEMO_SVG), 480, 360)
    assert len(data) == 480 * 360 * 4


def test_rasterize_flips_rows_bottom_up(core, tmp_path):
    # Identifiable feature in the image TOP-left corner: after the
    # bottom-up flip (matching decode_gif and the overlay quad UVs where
    # uv v=0 samples the quad bottom) it must land in the LAST buffer
    # rows, with the buffer START (image bottom) fully transparent.
    svg_path = tmp_path / "corner.svg"
    svg_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4">'
        '<rect x="0" y="0" width="2" height="2" fill="#ff0000"/></svg>'
    )
    data = core.rasterize_svg(str(svg_path), 4, 4)
    assert len(data) == 4 * 4 * 4
    assert _px(data, 4, 0, 3) == (255, 0, 0, 255), "image top-left -> last buffer row"
    assert _px(data, 4, 1, 3) == (255, 0, 0, 255)
    assert _px(data, 4, 3, 3) == (0, 0, 0, 0), "top-right stays empty"
    assert _px(data, 4, 0, 0) == (0, 0, 0, 0), "image bottom -> first buffer row, empty"


def test_rasterize_invalid_svg_raises_valueerror(core, tmp_path):
    bad = tmp_path / "bad.svg"
    bad.write_text("this is not an svg document")
    with pytest.raises(ValueError):
        core.rasterize_svg(str(bad), 8, 8)


def test_rasterize_zero_dimension_raises_valueerror(core):
    with pytest.raises(ValueError):
        core.rasterize_svg(str(DEMO_SVG), 0, 8)
    with pytest.raises(ValueError):
        core.rasterize_svg(str(DEMO_SVG), 8, 0)


# ---------------------------------------------------------------------
# SvgSource (headless: stubbed gpu, call-counting native shim)
# ---------------------------------------------------------------------


class FakeInstance:
    """Just enough of img_op.ImageInstance for SvgSource."""

    def __init__(self, container_id, image_name, size):
        self.container_id = container_id
        self.image_name = image_name
        self.size = list(size)
        self.texture = None
        self.batch = None

    def _create_batch(self):
        self.batch = object()


def _load_module(qualname, path):
    spec = importlib.util.spec_from_file_location(qualname, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[qualname] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def svg_env(core):
    """puree.media.decoders.svg loaded fresh (clean caches per test)."""
    saved_gpu = sys.modules.get("gpu")
    installed = []

    calls = {"probe": 0, "rasterize": 0}

    shim = types.ModuleType(f"{PKG}.native_bindings")

    def probe_svg(path):
        calls["probe"] += 1
        return core.probe_svg(path)

    def rasterize_svg(path, width, height, fonts_dir=None):
        calls["rasterize"] += 1
        return core.rasterize_svg(path, width, height, fonts_dir)

    shim.probe_svg = probe_svg
    shim.rasterize_svg = rasterize_svg

    root = types.ModuleType(PKG)
    root.__path__ = [str(REPO_ROOT / "puree")]
    root.native_bindings = shim
    root.get_addon_root = lambda: str(REPO_ROOT)

    media = types.ModuleType(f"{PKG}.media")
    media.__path__ = [str(MEDIA_DIR)]
    decoders = types.ModuleType(f"{PKG}.media.decoders")
    decoders.__path__ = [str(MEDIA_DIR / "decoders")]

    class Buffer:
        def __init__(self, fmt, size, data):
            assert fmt == "UBYTE"
            self.size = size
            self.data = data

    class GPUTexture:
        def __init__(self, size, format="RGBA8", data=None):
            self.width, self.height = size
            self.format = format
            self.data = data

    gpu = types.ModuleType("gpu")
    gpu.types = types.SimpleNamespace(Buffer=Buffer, GPUTexture=GPUTexture)

    for name, module in [
        (PKG, root),
        (f"{PKG}.media", media),
        (f"{PKG}.media.decoders", decoders),
        (f"{PKG}.native_bindings", shim),
        ("gpu", gpu),
    ]:
        sys.modules[name] = module
        installed.append(name)

    upload = _load_module(f"{PKG}.media.upload", MEDIA_DIR / "upload.py")
    installed.append(f"{PKG}.media.upload")
    svg = _load_module(f"{PKG}.media.decoders.svg", MEDIA_DIR / "decoders" / "svg.py")
    installed.append(f"{PKG}.media.decoders.svg")

    yield types.SimpleNamespace(svg=svg, upload=upload, calls=calls)

    for name in installed:
        sys.modules.pop(name, None)
    if saved_gpu is not None:
        sys.modules["gpu"] = saved_gpu


def make_source(env, box=(220, 220), name="demo_vector.svg"):
    instance = FakeInstance("card", name, box)
    source = env.svg.SvgSource("card", name, str(DEMO_SVG), instance)
    return source, instance


def test_fit_size_aspect_fit_and_min_clamp(svg_env):
    fit = svg_env.svg.fit_size
    assert fit(240, 180, 220, 220) == (220, 165)  # width-bound
    assert fit(240, 180, 480, 180) == (240, 180)  # height-bound
    assert fit(240, 180, 0, 0) == (1, 1)  # never below 1x1
    assert fit(240, 180, 1, 1) == (1, 1)


def test_attach_seeds_aspect_fit_texture(svg_env):
    source, instance = make_source(svg_env, box=(220, 220))
    # 240x180 intrinsic aspect-fit into a 220x220 box -> 220x165 raster.
    assert (instance.texture.width, instance.texture.height) == (220, 165)
    assert instance.batch is not None
    assert svg_env.calls == {"probe": 1, "rasterize": 1}
    # Shared upload probe picked the sRGB format on the stub.
    assert svg_env.upload.get_texture_format() == "SRGB8_A8"
    # Static content: settled SVG is never active and never asks to redraw.
    assert source.is_active() is False
    assert source.tick(100.0) is False
    assert source.is_active() is False


def test_resize_debounces_then_rerasters(svg_env):
    source, instance = make_source(svg_env, box=(220, 220))
    instance.size = [400, 300]
    assert source.tick(100.0) is False  # debounce starts, nothing swapped
    assert source.is_active() is True  # pending resize counts as active
    assert source.tick(100.05) is False  # still inside the 150 ms window
    assert svg_env.calls["rasterize"] == 1
    assert source.tick(100.16) is True  # stable -> re-raster + swap
    assert (instance.texture.width, instance.texture.height) == (400, 300)
    assert source.is_active() is False  # settled again
    assert source.tick(100.2) is False
    assert svg_env.calls["rasterize"] == 2


def test_resize_churn_restarts_debounce(svg_env):
    source, instance = make_source(svg_env, box=(220, 220))
    instance.size = [400, 300]
    assert source.tick(100.0) is False
    instance.size = [500, 400]  # user still dragging
    assert source.tick(100.1) is False  # restarts the window
    assert source.tick(100.2) is False  # only 0.1 s since the restart
    assert source.tick(100.26) is True
    # 240x180 into 500x400 -> 500x375 (width-bound).
    assert (instance.texture.width, instance.texture.height) == (500, 375)
    assert svg_env.calls["rasterize"] == 2


def test_resize_within_tolerance_never_rerasters(svg_env):
    source, instance = make_source(svg_env, box=(220, 220))
    instance.size = [221, 221]  # within the +-1 px tolerance
    for t in (100.0, 100.2, 101.0):
        assert source.tick(t) is False
    assert source.is_active() is False
    assert svg_env.calls["rasterize"] == 1


def test_raster_cache_shares_and_keeps_last_two_sizes(svg_env):
    source_a, instance_a = make_source(svg_env, box=(220, 220))
    source_b, _instance_b = make_source(svg_env, box=(220, 220))
    # Same file, same raster size -> second source hits the cache.
    assert svg_env.calls["rasterize"] == 1
    assert svg_env.calls["probe"] == 1  # intrinsic size cached per path too

    def resize(source, instance, box, t):
        instance.size = list(box)
        assert source.tick(t) is False
        assert source.tick(t + 0.2) is True

    resize(source_a, instance_a, (400, 300), 100.0)  # raster #2: 400x300
    assert svg_env.calls["rasterize"] == 2
    # Back to the original size: still cached (cap keeps the last 2 sizes).
    resize(source_a, instance_a, (220, 220), 101.0)
    assert svg_env.calls["rasterize"] == 2
    # A third size evicts 400x300 (oldest of the two)...
    resize(source_a, instance_a, (100, 100), 102.0)
    assert svg_env.calls["rasterize"] == 3
    # ...so returning to it re-rasterizes.
    resize(source_a, instance_a, (400, 300), 103.0)
    assert svg_env.calls["rasterize"] == 4


def test_self_heals_after_engine_texture_reset(svg_env):
    source, instance = make_source(svg_env)
    texture = instance.texture
    # scroll/dirty-sync/hot-reload call update_all(image_name=...) which
    # resets media textures to the ImageManager stub (None).
    instance.texture = None
    assert source.tick(100.0) is True
    assert instance.texture is texture
    assert svg_env.calls["rasterize"] == 1  # heal is a swap, not a re-raster


def test_retarget_releases_source(svg_env):
    source, instance = make_source(svg_env)
    instance.image_name = "something_else.png"
    assert source.tick(100.0) is False
    assert source.released is True
    assert source.is_active() is False
    source.release()  # idempotent
    assert source.tick(101.0) is False
