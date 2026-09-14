# Created by XWZ
# ◕‿◕ Distributed for free at:
# https://github.com/nicolaiprodromov/puree
# ╔═════════════════════════════════╗
# ║  ██   ██  ██      ██  ████████  ║
# ║   ██ ██   ██  ██  ██     ██     ║
# ║    ███    ██  ██  ██     ██     ║
# ║   ██ ██   ██  ██  ██   ██       ║
# ║  ██   ██   ████████   ████████  ║
# ╚═════════════════════════════════╝
"""Unit tests for the overlay container pass (MEDIA_PLAN section 4.3).

Two layers, no Blender:

- Parser level: the REAL ``puree.parser.UI`` (namespace-mounted package,
  stubbed ``bpy`` for space_config) parses a tiny YAML app and the flat
  dicts must carry the ``overlay`` flag with subtree propagation.
- Render level: the REAL ``puree.render.RenderPipeline`` with stubbed
  ``gpu``/``moderngl``/``gpu_extras`` packs main/overlay data textures -
  the split must filter without reordering flat indices, keep
  ``_vis_clips`` flat-indexed, remap hover/click to pass-local indices
  and produce zero overlay work for UIs without overlay containers.
"""

import sys
import textwrap
import types
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
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

pytestmark = pytest.mark.skipif(
    not PYD.exists(),
    reason=f"native core not built for this platform ({PYD.name}) - run `just build_core`",
)


# ── module-level stubs (collection-time, before importing puree.render) ──


def _module(name, **attrs):
    mod = sys.modules.get(name)
    if mod is None:
        mod = types.ModuleType(name)
        sys.modules[name] = mod
    for key, value in attrs.items():
        setattr(mod, key, value)
    return mod


def _prop(**_kwargs):
    return None


class _StubBuffer:
    def __init__(self, fmt, size, data):
        assert fmt == "FLOAT"
        self.size = size
        self.data = np.asarray(data)


class _StubGPUTexture:
    def __init__(self, size, format="RGBA32F", data=None):
        self.width, self.height = size
        self.format = format
        self.buffer = data


bpy_mod = _module("bpy")
bpy_types = _module("bpy.types", Operator=object, SpaceView3D=object)
bpy_props = _module(
    "bpy.props",
    StringProperty=_prop,
    IntProperty=_prop,
    FloatProperty=_prop,
    BoolProperty=_prop,
    EnumProperty=_prop,
)
bpy_mod.types = bpy_types
bpy_mod.props = bpy_props

_module("gpu", types=types.SimpleNamespace(Buffer=_StubBuffer, GPUTexture=_StubGPUTexture))
_module("moderngl")
gpu_extras = _module("gpu_extras")
gpu_extras_batch = _module("gpu_extras.batch", batch_for_shader=lambda *a, **k: object())
gpu_extras.batch = gpu_extras_batch

pkg = sys.modules.get("puree")
if pkg is None:
    pkg = types.ModuleType("puree")
    pkg.__path__ = [str(REPO_ROOT / "puree")]
    sys.modules["puree"] = pkg
if not hasattr(pkg, "get_addon_root"):
    pkg.get_addon_root = lambda: str(REPO_ROOT)

from puree.render import RenderPipeline  # noqa: E402

# ── helpers ──────────────────────────────────────────────────────────


def flat(cid, overlay=False, pos=(0.0, 0.0), size=(100.0, 100.0), parent=-1, children=(), display=True):
    """Minimal flat-dict shape - _build_container_struct defaults the rest."""
    return {
        "id": cid,
        "overlay": overlay,
        "position": list(pos),
        "size": list(size),
        "parent": parent,
        "children": list(children),
        "display": display,
    }


def make_pipeline():
    pipeline = RenderPipeline()
    pipeline.region_size = (800, 600)
    return pipeline


def packed_pos(texture, slot):
    """(pos_x, pos_y) of packed slot *slot* from a stubbed texture."""
    data = texture.buffer.data
    return float(data[slot * 68 + 1]), float(data[slot * 68 + 2])


SAMPLE = [
    flat("root", children=[1, 2, 3, 4], pos=(0, 0), size=(800, 600)),
    flat("a", parent=0, pos=(10, 10)),
    flat("bar", parent=0, overlay=True, pos=(20, 500), children=[3]),
    flat("bar_child", parent=2, overlay=True, pos=(25, 505)),
    flat("b", parent=0, pos=(300, 10)),
]


# ── packing split ────────────────────────────────────────────────────


def test_split_indices_preserve_flat_order():
    main, overlay = RenderPipeline._split_overlay_indices(SAMPLE)
    assert main == [0, 1, 4]
    assert overlay == [2, 3]
    # the flat list itself is untouched - only the packing filters
    assert [c["id"] for c in SAMPLE] == ["root", "a", "bar", "bar_child", "b"]


def test_create_data_texture_packs_two_filtered_textures():
    pipeline = make_pipeline()
    assert pipeline.create_data_texture(SAMPLE) is True

    # main texture: 3 containers x 17 texels
    assert pipeline.data_texture.width == 3 * 17
    assert packed_pos(pipeline.data_texture, 0) == (0.0, 0.0)  # root
    assert packed_pos(pipeline.data_texture, 1) == (10.0, 10.0)  # a
    assert packed_pos(pipeline.data_texture, 2) == (300.0, 10.0)  # b

    # overlay texture: 2 containers x 17 texels, flat order preserved
    assert pipeline.overlay_data_texture.width == 2 * 17
    assert packed_pos(pipeline.overlay_data_texture, 0) == (20.0, 500.0)  # bar
    assert packed_pos(pipeline.overlay_data_texture, 1) == (25.0, 505.0)  # bar_child

    # flat -> local maps for the hover/click uniform remap
    assert pipeline._main_index_map == {0: 0, 1: 1, 4: 2}
    assert pipeline._overlay_index_map == {2: 0, 3: 1}

    # _vis_clips stays indexed by FLAT index (scrollbars + both passes)
    assert len(pipeline._vis_clips) == len(SAMPLE)


def test_no_overlay_ui_produces_no_overlay_work():
    pipeline = make_pipeline()
    containers = [flat("root", children=[1]), flat("child", parent=0)]
    assert pipeline.create_data_texture(containers) is True

    assert pipeline.data_texture.width == 2 * 17
    assert pipeline.overlay_data_texture is None
    assert pipeline.overlay_batch is None
    assert pipeline.overlay_container_count == 0
    # identity map - local == flat, exactly the pre-overlay behavior
    assert pipeline._main_index_map == {0: 0, 1: 1}


def test_pack_without_indices_matches_pre_overlay_behavior():
    pipeline = make_pipeline()
    data = pipeline._pack_container_data_texture(SAMPLE)
    assert len(data) == len(SAMPLE) * 68
    # slot i == flat i when unfiltered
    assert (float(data[2 * 68 + 1]), float(data[2 * 68 + 2])) == (20.0, 500.0)


def test_update_data_texture_rebuilds_and_drops_stale_overlay():
    pipeline = make_pipeline()
    assert pipeline.create_data_texture(SAMPLE) is True
    assert pipeline.overlay_data_texture is not None

    # overlay flags vanish (e.g. controls removed on hot reload)
    plain = [dict(c, overlay=False) for c in SAMPLE]
    assert pipeline.update_data_texture(plain) is True
    assert pipeline.overlay_data_texture is None
    assert pipeline.overlay_container_count == 0
    assert pipeline.data_texture.width == len(SAMPLE) * 17

    # and back again
    assert pipeline.update_data_texture(SAMPLE) is True
    assert pipeline.overlay_data_texture.width == 2 * 17


def test_pass_state_indices_remap():
    pipeline = make_pipeline()
    pipeline.create_data_texture(SAMPLE)

    pipeline._current_hover_index = 4  # flat "b" -> main local 2
    pipeline._current_click_index = 3  # flat "bar_child" -> overlay local 1

    assert pipeline._pass_state_indices(pipeline._main_index_map) == (2.0, -1.0)
    assert pipeline._pass_state_indices(pipeline._overlay_index_map) == (-1.0, 1.0)

    # no packing yet -> identity passthrough (pre-overlay behavior)
    fresh = make_pipeline()
    fresh._current_hover_index = 7
    fresh._current_click_index = -1
    assert fresh._pass_state_indices(fresh._main_index_map) == (7.0, -1.0)


def test_vis_clips_flat_indexing_shared_between_passes():
    pipeline = make_pipeline()
    hidden = [dict(c) for c in SAMPLE]
    hidden[3]["display"] = False  # bar_child hidden
    pipeline.create_data_texture(hidden)
    # overlay slot 1 (= flat 3) must carry the hidden visibility flag
    data = pipeline.overlay_data_texture.buffer.data
    assert float(data[1 * 68 + 54]) == 0.0  # struct[54] = visible
    assert float(data[0 * 68 + 54]) == 1.0


# ── parser level: flatten carries the flag + subtree propagation ────


@pytest.fixture(scope="module")
def parsed_ui(tmp_path_factory):
    addon_dir = tmp_path_factory.mktemp("overlay_app")
    (addon_dir / "style.scss").write_text(
        ".root { width: 100%; height: 100%; }\n.panel { width: 200px; height: 100px; }\n"
    )
    (addon_dir / "index.yaml").write_text(
        textwrap.dedent(
            """
            app:
              selected_theme: t
              default_theme: t
              theme:
                - name: t
                  author: a
                  version: '1'
                  scripts: []
                  styles: [style.scss]
                  components: components/
                  root:
                    class: root
                    plain:
                      class: panel
                      plain_child:
                        class: panel
                    lifted:
                      class: panel
                      overlay: true
                      lifted_child:
                        class: panel
                        lifted_grandchild:
                          class: panel
            """
        )
    )
    saved_root = pkg.get_addon_root
    pkg.get_addon_root = lambda: str(addon_dir)
    try:
        from puree.parser import UI

        yield UI(str(addon_dir / "index.yaml"), str(addon_dir), canvas_size=(800, 600))
    finally:
        pkg.get_addon_root = saved_root


def test_flatten_carries_overlay_flag(parsed_ui):
    by_id = {c["id"]: c for c in parsed_ui.abs_json_data}
    assert by_id["lifted"]["overlay"] is True
    assert by_id["root"]["overlay"] is False
    assert by_id["plain"]["overlay"] is False
    assert by_id["plain_plain_child"]["overlay"] is False


def test_overlay_flag_propagates_to_whole_subtree(parsed_ui):
    by_id = {c["id"]: c for c in parsed_ui.abs_json_data}
    assert by_id["lifted_lifted_child"]["overlay"] is True
    assert by_id["lifted_lifted_child_lifted_grandchild"]["overlay"] is True


def test_container_overlay_attr_coerces_like_yaml_strings():
    from puree.components.container import Container

    c = Container()
    assert c.overlay is False
    c.overlay = "true"  # component params arrive stringified
    assert c.overlay is True
    c.overlay = "0"
    assert c.overlay is False
