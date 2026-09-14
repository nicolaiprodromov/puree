# Created by XWZ
# ~*~ Distributed for free at:
# https://github.com/nicolaiprodromov/puree
"""Unit tests for puree.media.upload - the (buffer, texture) combo probe.

The module is loaded FRESH per test under a synthetic package (so the
once-per-session probe cache starts empty) against fake ``gpu`` modules
emulating real Blender personalities:

- UBYTE-happy builds (most): ``Buffer('UBYTE')`` accepted directly.
- FLOAT-only builds (observed live, 2026-07-20 session): ``GPUTexture``
  raises ``TypeError("Only Buffer of format 'FLOAT' is currently
  supported")`` for UBYTE buffers - frames must convert to normalized
  float32 (numpy) first.
- sRGB-less builds: ``SRGB8_A8`` rejected, ``RGBA8`` accepted.
"""

import importlib.util
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MEDIA_DIR = REPO_ROOT / "puree" / "media"
PKG = "puree_uploadtest"  # synthetic root - the real puree/__init__ imports bpy


class FakeBuffer:
    """gpu.types.Buffer: records format, validates the declared size."""

    def __init__(self, fmt, size, data):
        assert fmt in ("UBYTE", "FLOAT"), fmt
        assert len(data) == size, f"Buffer size mismatch: {len(data)} != {size}"
        self.format = fmt
        self.size = size
        self.data = data


def make_gpu(reject_ubyte=False, reject_srgb=False):
    """Fake gpu module; every GPUTexture attempt is recorded as
    (buffer_format, texture_format, constructed_ok)."""
    attempts = []

    class FakeGPUTexture:
        def __init__(self, size, format="RGBA8", data=None):
            if reject_ubyte and data.format == "UBYTE":
                attempts.append((data.format, format, False))
                raise TypeError("Only Buffer of format 'FLOAT' is currently supported")
            if reject_srgb and format == "SRGB8_A8":
                attempts.append((data.format, format, False))
                raise ValueError("unsupported texture format 'SRGB8_A8'")
            attempts.append((data.format, format, True))
            self.width, self.height = size
            self.format = format
            self.data = data

    gpu = types.ModuleType("gpu")
    gpu.types = types.SimpleNamespace(Buffer=FakeBuffer, GPUTexture=FakeGPUTexture)
    gpu.attempts = attempts
    return gpu


@pytest.fixture()
def load_upload():
    """Loader: real upload.py, fresh module + fresh probe cache, given gpu."""
    installed = []
    saved_gpu = sys.modules.get("gpu")

    def _load(gpu):
        root = types.ModuleType(PKG)
        root.__path__ = [str(REPO_ROOT / "puree")]
        media = types.ModuleType(f"{PKG}.media")
        media.__path__ = [str(MEDIA_DIR)]
        for name, module in ((PKG, root), (f"{PKG}.media", media), ("gpu", gpu)):
            sys.modules[name] = module
            installed.append(name)
        spec = importlib.util.spec_from_file_location(f"{PKG}.media.upload", MEDIA_DIR / "upload.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"{PKG}.media.upload"] = module
        installed.append(f"{PKG}.media.upload")
        spec.loader.exec_module(module)
        return module

    yield _load
    for name in installed:
        sys.modules.pop(name, None)
    if saved_gpu is not None:
        sys.modules["gpu"] = saved_gpu


def _silence(module, infos=None, warnings=None):
    """Swap the module logger for a recorder (module is throwaway per test)."""
    module.logger = types.SimpleNamespace(
        info=lambda msg, *a, **k: (infos.append(msg) if infos is not None else None),
        warning=lambda msg, *a, **k: (warnings.append(msg) if warnings is not None else None),
        debug=lambda *a, **k: None,
        error=lambda *a, **k: None,
    )


def test_ubyte_happy_build_picks_ubyte_srgb(load_upload):
    gpu = make_gpu()
    upload = load_upload(gpu)
    data = bytes(range(24))  # 2x3 RGBA8
    texture = upload.upload_texture(2, 3, data)
    assert upload.get_upload_combo() == ("UBYTE", "SRGB8_A8")
    assert upload.get_texture_format() == "SRGB8_A8"
    assert (texture.width, texture.height) == (2, 3)
    assert texture.data.format == "UBYTE" and texture.data.data == data  # bytes pass through untouched
    # exactly one 2x2 probe texture + the real upload, zero failed attempts
    assert gpu.attempts == [("UBYTE", "SRGB8_A8", True), ("UBYTE", "SRGB8_A8", True)]


def test_srgb_less_build_falls_back_to_ubyte_rgba8(load_upload):
    gpu = make_gpu(reject_srgb=True)
    upload = load_upload(gpu)
    texture = upload.upload_texture(1, 1, b"\x10\x20\x30\x40")
    assert upload.get_upload_combo() == ("UBYTE", "RGBA8")
    assert upload.get_texture_format() == "RGBA8"
    assert texture.format == "RGBA8" and texture.data.format == "UBYTE"


def test_float_only_build_lands_on_float_srgb(load_upload):
    """The live-Blender personality: UBYTE rejected at the texture -> the
    probe lands on ('FLOAT', 'SRGB8_A8') and frames convert to float32."""
    np = pytest.importorskip("numpy")
    gpu = make_gpu(reject_ubyte=True)
    upload = load_upload(gpu)
    data = bytes([0, 51, 128, 255] * 6)  # 2x3 RGBA8
    texture = upload.upload_texture(2, 3, data)
    assert upload.get_upload_combo() == ("FLOAT", "SRGB8_A8")
    assert upload.get_texture_format() == "SRGB8_A8"
    payload = texture.data.data
    assert texture.data.format == "FLOAT"
    assert payload.dtype == np.float32
    assert len(payload) == 2 * 3 * 4  # w*h*4 floats
    expected = np.frombuffer(data, dtype=np.uint8).astype(np.float32)
    expected /= 255.0
    assert np.array_equal(payload, expected)  # exactly bytes/255 in float32
    assert payload[0] == 0.0 and payload[3] == 1.0  # 0 -> 0.0, 255 -> 1.0


def test_probe_result_is_cached_minimal_constructions(load_upload):
    gpu = make_gpu(reject_ubyte=True)
    upload = load_upload(gpu)
    for _ in range(4):
        upload.upload_texture(1, 1, b"\x00\x00\x00\x00")
    failed = [a for a in gpu.attempts if not a[2]]
    succeeded = [a for a in gpu.attempts if a[2]]
    # both UBYTE combos failed exactly once each - during the single probe
    assert failed == [("UBYTE", "SRGB8_A8", False), ("UBYTE", "RGBA8", False)]
    # 1 probe texture + 4 real uploads = the minimum possible
    assert len(succeeded) == 5
    assert all(a[:2] == ("FLOAT", "SRGB8_A8") for a in succeeded)


def test_chosen_combo_logged_once_at_info(load_upload):
    gpu = make_gpu(reject_ubyte=True)
    upload = load_upload(gpu)
    infos = []
    _silence(upload, infos=infos)
    upload.upload_texture(1, 1, bytes(4))
    upload.upload_texture(1, 1, bytes(4))
    assert len(infos) == 1  # once per session, not per upload
    assert "FLOAT" in infos[0] and "SRGB8_A8" in infos[0]


def test_float_only_without_numpy_warns_once_and_degrades(load_upload, monkeypatch):
    """numpy missing on a FLOAT-only build: one session-wide warning, then
    every upload raises - MediaManager's per-source handling degrades the
    element (documented in the module docstring)."""
    gpu = make_gpu(reject_ubyte=True)
    upload = load_upload(gpu)
    warnings = []
    _silence(upload, warnings=warnings)
    monkeypatch.setitem(sys.modules, "numpy", None)  # import numpy -> ImportError
    for _ in range(2):
        with pytest.raises(RuntimeError, match="no usable GPU texture upload path"):
            upload.upload_texture(1, 1, b"\x00\x00\x00\x00")
    assert len(warnings) == 1
    assert "numpy" in warnings[0]
    assert upload.get_upload_combo() is None  # nothing usable was cached
