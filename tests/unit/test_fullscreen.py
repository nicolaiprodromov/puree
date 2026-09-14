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
"""Unit tests for fullscreen presentation mode (FULLSCREEN_PLAN Phase A).

Three layers, no Blender (the established namespace-mount + stub pattern):

- Parser level: the REAL ``puree.parser.UI`` parses a small app (video tile
  with injected [video_controls] inside a scroll area + a generic card) and
  ``compute_subtree_layout`` must produce a region-sized private layout
  without touching the main tree.
- Manager level: the REAL ``puree.fullscreen.FullscreenManager`` against the
  real parse, a real ``RenderPipeline`` (stubbed gpu), fake instances in the
  real img_op/text_op registries, a recording hit detector and the real
  keyboard/input-router/media singletons - enter/exit round trip, swap,
  resize, dirty-sync re-assert, ESC, hit swap payloads, media clock
  continuity, force_exit idempotence.
- Render level: ``draw_texture``/``draw_overlay_texture`` short-circuit to
  backdrop + fullscreen textures while active and are byte-identical to the
  normal passes when inactive.
"""

import sys
import textwrap
import types
from pathlib import Path

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


# ── module-level stubs (same pattern as test_overlay_pass) ───────────


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
        import numpy as np

        self.data = np.asarray(data)


class _StubGPUTexture:
    def __init__(self, size, format="RGBA32F", data=None):
        self.width, self.height = size
        self.format = format
        self.buffer = data


class _RecordingShader:
    """Records bind/uniform calls - stands in for the native container
    shader AND the builtin UNIFORM_COLOR shader."""

    def __init__(self, name="shader"):
        self.name = name
        self.calls = []

    def bind(self):
        self.calls.append(("bind",))

    def uniform_sampler(self, uniform, tex):
        self.calls.append(("sampler", uniform, tex))

    def uniform_float(self, uniform, value):
        self.calls.append(("float", uniform, value))


class _RecordingBatch:
    def __init__(self, shader, kind, payload):
        self.shader = shader
        self.kind = kind
        self.payload = payload
        self.draw_calls = []

    def draw(self, shader):
        self.draw_calls.append(shader)
        _drawn_batches.append(self)


_drawn_batches = []  # every batch.draw() in order
_builtin_shader = _RecordingShader("UNIFORM_COLOR")


def _batch_for_shader(shader, kind, payload, indices=None):
    return _RecordingBatch(shader, kind, payload)


class _GpuState:
    @staticmethod
    def blend_get():
        return "NONE"

    @staticmethod
    def blend_set(_mode):
        return None

    @staticmethod
    def depth_test_get():
        return "NONE"

    @staticmethod
    def depth_test_set(_mode):
        return None

    @staticmethod
    def scissor_test_set(_on):
        return None

    @staticmethod
    def scissor_set(*_a):
        return None


class _GpuMatrix:
    @staticmethod
    def push():
        return None

    @staticmethod
    def pop():
        return None

    @staticmethod
    def load_identity():
        return None


bpy_mod = _module("bpy")
bpy_mod.types = _module(
    "bpy.types",
    Operator=object,
    SpaceView3D=object,
    Panel=object,
    PropertyGroup=object,
    UIList=object,
)
bpy_mod.props = _module(
    "bpy.props",
    StringProperty=_prop,
    IntProperty=_prop,
    FloatProperty=_prop,
    BoolProperty=_prop,
    EnumProperty=_prop,
    CollectionProperty=_prop,
    FloatVectorProperty=_prop,
)
bpy_mod.app = types.SimpleNamespace(
    timers=types.SimpleNamespace(
        register=lambda *a, **k: None,
        unregister=lambda *a, **k: None,
        is_registered=lambda *a, **k: False,
    )
)
bpy_mod.context = types.SimpleNamespace(
    screen=types.SimpleNamespace(areas=[]),
    window_manager=types.SimpleNamespace(),
)

gpu_mod = _module("gpu")
gpu_mod.types = types.SimpleNamespace(Buffer=_StubBuffer, GPUTexture=_StubGPUTexture)
gpu_mod.state = _GpuState
gpu_mod.matrix = _GpuMatrix
gpu_mod.shader = types.SimpleNamespace(from_builtin=lambda name: _builtin_shader)

_module("moderngl")
gpu_extras = _module("gpu_extras")
gpu_extras_batch = _module("gpu_extras.batch", batch_for_shader=_batch_for_shader)
gpu_extras.batch = gpu_extras_batch

_module(
    "blf",
    load=lambda path: 1,
    size=lambda *a: None,
    dimensions=lambda *a: (10.0, 10.0),
    clipping=lambda *a: None,
    enable=lambda *a: None,
    disable=lambda *a: None,
    position=lambda *a: None,
    color=lambda *a: None,
    draw=lambda *a: None,
    CLIPPING=1,
    SHADOW=2,
)
_module(
    "mathutils",
    Matrix=types.SimpleNamespace(
        Diagonal=lambda *a, **k: None,
        Translation=lambda *a, **k: None,
    ),
)

pkg = sys.modules.get("puree")
if pkg is None:
    pkg = types.ModuleType("puree")
    pkg.__path__ = [str(REPO_ROOT / "puree")]
    sys.modules["puree"] = pkg
if not hasattr(pkg, "get_addon_root"):
    pkg.get_addon_root = lambda: str(REPO_ROOT)

from puree import hit_op, img_op, parser_op, render, text_op  # noqa: E402
from puree.fullscreen import fullscreen_manager  # noqa: E402
from puree.input_router import input_router  # noqa: E402
from puree.keyboard import keys  # noqa: E402
from puree.media import media_manager  # noqa: E402
from puree.media.clock import MediaClock  # noqa: E402
from puree.media.controls import unwire_video_controls  # noqa: E402
from puree.render import RenderPipeline  # noqa: E402

# render.py from-imports batch_for_shader at module level, so whichever test
# module imports puree.render FIRST freezes ITS gpu_extras stub into render's
# namespace (test_overlay_pass's stub returns inert object()s with no .draw
# recording). Pin the recording stub explicitly so the draw-gating assertions
# below hold in ANY collection order - a no-op in the default alphabetical
# order, where this module imports render first anyway.
render.batch_for_shader = _batch_for_shader

# ── app fixture (real parse) ─────────────────────────────────────────

APP_YAML = textwrap.dedent(
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
            page:
              class: page
              tile:
                class: tile
                video: demo_clip.mp4
                controls: true
                muted: true
                tile_label:
                  class: tile_label
                  text: TILE
              spacer:
                class: spacer
            card:
              class: card
              card_label:
                class: card_label
                text: CARD
    """
)

APP_SCSS = (
    ".root { width: 100%; height: 100%; flex-direction: column; }\n"
    ".page { width: 100%; height: 300px; overflow-y: scroll; flex-direction: column; }\n"
    ".tile { width: 320px; height: 200px; }\n"
    ".tile_label { width: 100px; height: 20px; }\n"
    ".spacer { width: 100px; height: 800px; }\n"
    ".card { width: 200px; height: 100px; }\n"
)

REGION = (800, 600)
VC_BAR_H = 32.0  # $vc_bar_height in components/defaults/video_controls.scss


def _build_ui(addon_dir):
    from puree.parser import UI

    saved_root = pkg.get_addon_root
    pkg.get_addon_root = lambda: str(addon_dir)
    try:
        return UI(str(Path(addon_dir) / "index.yaml"), str(addon_dir), canvas_size=REGION)
    finally:
        pkg.get_addon_root = saved_root


class FakeDetector:
    """Records every load_containers payload (as id lists)."""

    def __init__(self):
        self.loads = []

    def load_containers(self, containers):
        self.loads.append([c.get("id", "") for c in containers])
        return True


class FakeImageInstance:
    def __init__(self, container_id, pos, size, mask, clip=None):
        self.container_id = container_id
        self.position = list(pos)
        self.size = list(size)
        self.mask = list(mask) if mask is not None else None
        self.clip = list(clip) if clip is not None else None
        self.texture = object()
        self.batch = object()
        self.update_calls = []

    def update_all(self, **kwargs):
        self.update_calls.append(kwargs)
        if kwargs.get("pos") is not None:
            self.position = list(kwargs["pos"])
        if kwargs.get("size") is not None:
            self.size = list(kwargs["size"])
        if kwargs.get("mask") is not None:
            self.mask = list(kwargs["mask"])
        if kwargs.get("clip") is not None:
            self.clip = list(kwargs["clip"])


class FakeTextInstance:
    def __init__(self, container_id, pos, mask, clip=None):
        self.container_id = container_id
        self.position = list(pos)
        self.mask = list(mask) if mask is not None else None
        self.clip = list(clip) if clip is not None else None
        self.text = ""
        self.update_calls = []

    def update_all(self, **kwargs):
        self.update_calls.append(kwargs)
        if kwargs.get("pos") is not None:
            self.position = list(kwargs["pos"])
        if kwargs.get("mask") is not None:
            self.mask = list(kwargs["mask"])
        if kwargs.get("clip") is not None:
            self.clip = list(kwargs["clip"])
        if kwargs.get("text") is not None:
            self.text = kwargs["text"]


class FakeSource:
    """Clock-backed source (GifSource shape) whose tick() calls are counted."""

    def __init__(self, clock):
        self.clock = clock
        self.released = False
        self.instance = object()
        self.ready_state = "ready"
        self.tick_calls = 0

    def tick(self, _now):
        self.tick_calls += 1
        return False

    def is_active(self, _now=None):
        return not self.clock.paused


@pytest.fixture()
def app(tmp_path):
    """Real parse + live engine registries wired the way render.execute
    leaves them, torn down completely after each test."""
    (tmp_path / "index.yaml").write_text(APP_YAML)
    (tmp_path / "style.scss").write_text(APP_SCSS)
    ui = _build_ui(tmp_path)

    parser_op.XWZ_UI = ui
    hit_op._container_data = ui.abs_json_data
    detector = FakeDetector()
    hit_op._native_detector = detector

    pipeline = RenderPipeline()
    pipeline.region_size = REGION
    pipeline._cache_original_positions(ui.abs_json_data)
    render._render_data = pipeline

    # The video tile instance sits inside the scroll area -> it carries a
    # scroll clip in production; the label is its text counterpart.
    by_id = {c["id"]: c for c in ui.abs_json_data}
    tile = by_id["page_tile"]
    tile_img = FakeImageInstance(
        "page_tile",
        pos=tile["position"],
        size=tile["size"],
        mask=[*tile["position"], *tile["size"]],
        clip=[0, 100, 800, 300],
    )
    label = by_id["page_tile_tile_label"]
    tile_text = FakeTextInstance(
        "page_tile_tile_label",
        pos=label["position"],
        mask=[*label["position"], *label["size"]],
        clip=[0, 100, 800, 300],
    )
    card_label = by_id["card_card_label"]
    card_text = FakeTextInstance(
        "card_card_label",
        pos=card_label["position"],
        mask=[*card_label["position"], *card_label["size"]],
    )
    other_img = FakeImageInstance("card", pos=[10, 400], size=[50, 50], mask=[10, 400, 50, 50])

    img_op._image_instances.extend([tile_img, other_img])
    text_op._text_instances.extend([tile_text, card_text])

    state = {"now": 0.0}
    clock = MediaClock(duration=40.0, loop=False, time_fn=lambda: state["now"])
    media_manager._sources.clear()
    media_manager._controllers.clear()
    media_manager._sources["page_tile"] = FakeSource(clock)

    yield types.SimpleNamespace(
        ui=ui,
        pipeline=pipeline,
        detector=detector,
        tile_img=tile_img,
        tile_text=tile_text,
        card_text=card_text,
        other_img=other_img,
        clock=clock,
        state=state,
    )

    fullscreen_manager.force_exit()
    fullscreen_manager._reset_state()
    unwire_video_controls()  # Phase B tests wire the real controls
    img_op._image_instances.clear()
    text_op._text_instances.clear()
    media_manager._sources.clear()
    media_manager._controllers.clear()
    media_manager.set_visibility_filter(None)
    keys.clear()
    input_router.reset()
    render._render_data = None
    hit_op._native_detector = None
    hit_op._container_data = []
    parser_op.XWZ_UI = None
    _drawn_batches.clear()
    _builtin_shader.calls.clear()


# ── parser level: private subtree layout ─────────────────────────────


def test_compute_subtree_layout_is_region_sized_and_pure(app):
    from puree import parser

    tile = app.ui.get_by_id("page_tile")
    before_boxes = {cid: dict(box) for cid, box in parser.node_flat_abs.items()}
    before_layout_node = tile._layout_node
    before_content_box = dict(tile._content_box_abs)

    boxes, content_boxes = app.ui.compute_subtree_layout(tile, (640, 480))

    # forced root box: exactly the region, at the origin
    assert boxes["page_tile"] == {"x": 0.0, "y": 0.0, "width": 640.0, "height": 480.0}
    assert content_boxes["page_tile"]["width"] == 640.0
    # subtree-only
    assert "card" not in boxes and "root" not in boxes
    assert "page_tile_tile_label" in boxes
    # controls subtree laid out at region width, pinned to the bottom
    bar = boxes["page_tile_puree_vc"]
    assert bar["width"] == 640.0
    assert bar["height"] == VC_BAR_H
    assert bar["y"] == 480.0 - VC_BAR_H

    # the MAIN tree is byte-identical: globals, node identity, content box
    assert tile._layout_node is before_layout_node
    assert dict(tile._content_box_abs) == before_content_box
    assert {cid: dict(box) for cid, box in parser.node_flat_abs.items()} == before_boxes


def test_private_flat_list_carries_controls_and_overlay_split(app):
    assert fullscreen_manager.enter("page_tile") is True
    flat_ids = [c["id"] for c in fullscreen_manager._flat]
    assert "page_tile" in flat_ids
    assert "page_tile_puree_vc" in flat_ids  # controls subtree present
    assert all(cid.startswith("page_tile") for cid in flat_ids)

    overlay_flags = {c["id"]: c["overlay"] for c in fullscreen_manager._flat}
    assert overlay_flags["page_tile"] is False
    assert overlay_flags["page_tile_puree_vc"] is True  # Phase 5 subtree flag

    # both fullscreen textures exist (main split + controls overlay split)
    assert app.pipeline.fs_active is True
    assert app.pipeline.fs_data_texture is not None
    assert app.pipeline.fs_overlay_texture is not None
    n_overlay = sum(1 for c in fullscreen_manager._flat if c["overlay"])
    assert app.pipeline.fs_overlay_texture.width == n_overlay * 17
    assert app.pipeline.fs_data_texture.width == (len(flat_ids) - n_overlay) * 17


def test_private_text_blocks_from_private_layout(app):
    fullscreen_manager.enter("page_tile")
    blocks = fullscreen_manager._text_blocks
    assert "page_tile_tile_label" in blocks
    # controls labels ride along (initial text from the component YAML)
    time_label_id = next((cid for cid in blocks if cid.endswith("_vc_time")), None)
    assert time_label_id is not None
    assert blocks[time_label_id]["text"] == "0:00"
    # geometry comes from the PRIVATE layout, not the main tree
    label_box = fullscreen_manager._boxes["page_tile_tile_label"]
    assert blocks["page_tile_tile_label"]["mask_x"] == int(label_box["x"])
    assert blocks["page_tile_tile_label"]["mask_width"] == int(label_box["width"])


# ── manager level: enter/exit round trip ─────────────────────────────


def test_enter_exit_round_trip_restores_geometry_exactly(app):
    img_before = {
        "position": list(app.tile_img.position),
        "size": list(app.tile_img.size),
        "mask": list(app.tile_img.mask),
        "clip": list(app.tile_img.clip),
    }
    text_before = {
        "position": list(app.tile_text.position),
        "mask": list(app.tile_text.mask),
        "clip": list(app.tile_text.clip),
    }

    assert fullscreen_manager.enter("page_tile") is True
    assert fullscreen_manager.is_active()
    assert fullscreen_manager.active_id == "page_tile"

    # retargeted: region-sized geometry, scroll clip cleared
    assert app.tile_img.size == [REGION[0], REGION[1]]
    assert app.tile_img.position == [0, 0]
    assert app.tile_img.clip is None
    assert app.tile_text.clip is None
    assert app.tile_img.mask == [0, 0, REGION[0], REGION[1]]
    # non-subtree instances untouched
    assert not app.other_img.update_calls
    assert not app.card_text.update_calls

    assert fullscreen_manager.exit() is True
    assert not fullscreen_manager.is_active()
    assert fullscreen_manager.active_id is None

    assert app.tile_img.position == img_before["position"]
    assert app.tile_img.size == img_before["size"]
    assert app.tile_img.mask == img_before["mask"]
    assert app.tile_img.clip == img_before["clip"]
    assert app.tile_text.position == text_before["position"]
    assert app.tile_text.mask == text_before["mask"]
    assert app.tile_text.clip == text_before["clip"]

    # private data dropped, gpu pass cleared
    assert fullscreen_manager._flat == []
    assert fullscreen_manager._subtree_ids == set()
    assert app.pipeline.fs_active is False
    assert app.pipeline.fs_data_texture is None
    assert app.pipeline.fs_overlay_texture is None

    # exit is idempotent / safe when idle
    assert fullscreen_manager.exit() is False


def test_main_tree_layout_untouched_after_round_trip(app):
    from puree import parser

    tile = app.ui.get_by_id("page_tile")
    node_identities = {}

    def walk(container):
        node_identities[container.id] = container._layout_node
        for child in container.children:
            walk(child)

    walk(app.ui.theme.root)
    flat_before = [(c["id"], list(c["position"]), list(c["size"]), c["overlay"]) for c in app.ui.abs_json_data]
    abs_before = {cid: dict(box) for cid, box in parser.node_flat_abs.items()}
    content_before = dict(tile._content_box_abs)

    fullscreen_manager.enter("page_tile")
    fullscreen_manager.refresh()
    fullscreen_manager.exit()

    def check(container):
        assert container._layout_node is node_identities[container.id]
        for child in container.children:
            check(child)

    check(app.ui.theme.root)
    assert {cid: dict(box) for cid, box in parser.node_flat_abs.items()} == abs_before
    assert dict(tile._content_box_abs) == content_before
    assert [(c["id"], list(c["position"]), list(c["size"]), c["overlay"]) for c in app.ui.abs_json_data] == flat_before


def test_scroll_clipped_element_escapes_clipping(app):
    # the tile lives in an overflow-y: scroll page and carries a scroll clip
    assert app.tile_img.clip is not None
    fullscreen_manager.enter("page_tile")
    # private geometry has no scroll offsets and no ancestor clip
    assert app.tile_img.clip is None
    assert fullscreen_manager._boxes["page_tile"]["y"] == 0.0
    # private visibility precompute has no main-tree scroll parents: the
    # packed struct for the fullscreen root is fully visible
    data = app.pipeline.fs_data_texture.buffer.data
    main_ids = [c["id"] for c in fullscreen_manager._flat if not c["overlay"]]
    slot = main_ids.index("page_tile")
    assert float(data[slot * 68 + 54]) == 1.0  # struct[54] = visible


def test_swap_between_two_elements(app):
    assert fullscreen_manager.enter("page_tile") is True
    assert fullscreen_manager.enter("card") is True  # swap = exit-then-enter
    assert fullscreen_manager.active_id == "card"
    assert fullscreen_manager._boxes["card"]["width"] == float(REGION[0])
    # tile geometry was restored by the swap's implicit exit
    assert app.tile_img.clip == [0, 100, 800, 300]
    assert app.tile_img.size != [REGION[0], REGION[1]]
    # re-enter same id is a no-op success
    assert fullscreen_manager.enter("card") is True
    assert fullscreen_manager.active_id == "card"
    fullscreen_manager.exit()


def test_non_media_container_generic_path(app):
    assert fullscreen_manager.enter("card") is True
    assert fullscreen_manager.active_id == "card"
    assert "card_card_label" in fullscreen_manager._subtree_ids
    assert app.pipeline.fs_data_texture is not None
    assert app.pipeline.fs_overlay_texture is None  # no overlay members
    assert fullscreen_manager.exit() is True


def test_resize_recomputes_private_layout(app):
    fullscreen_manager.enter("page_tile")
    first_texture = app.pipeline.fs_data_texture
    assert fullscreen_manager._region == REGION

    app.pipeline.region_size = (1024, 768)
    assert fullscreen_manager.on_render_tick() is True  # region drift detected
    assert fullscreen_manager._region == (1024, 768)
    assert fullscreen_manager._boxes["page_tile"]["width"] == 1024.0
    assert app.tile_img.size == [1024, 768]
    bar = fullscreen_manager._boxes["page_tile_puree_vc"]
    assert bar["width"] == 1024.0 and bar["y"] == 768.0 - VC_BAR_H
    assert app.pipeline.fs_data_texture is not first_texture  # repacked

    # steady state: no work, no redraw request
    assert fullscreen_manager.on_render_tick() is False


def test_dirty_sync_reasserts_private_pass_and_hit_set(app):
    fullscreen_manager.enter("page_tile")
    # simulate the render modal's dirty-sync clobber (MAIN-tree blocks)
    app.tile_img.update_all(pos=[100, 150], size=[320, 200], mask=[100, 150, 320, 200], clip=[0, 100, 800, 300])
    app.detector.loads.append(["MAIN-RELOAD"])

    assert fullscreen_manager.on_render_tick(dirty_synced=True) is True
    assert app.tile_img.position == [0, 0]
    assert app.tile_img.size == [REGION[0], REGION[1]]
    assert app.tile_img.clip is None
    # the hit set was re-asserted with the private subtree AFTER the clobber
    assert app.detector.loads[-1] != ["MAIN-RELOAD"]
    assert all(cid.startswith("page_tile") for cid in app.detector.loads[-1])


def test_hit_set_swap_payloads(app):
    fullscreen_manager.enter("page_tile")
    subtree_load = app.detector.loads[-1]
    assert sorted(subtree_load) == sorted(fullscreen_manager._subtree_ids)
    assert "root" not in subtree_load and "card" not in subtree_load

    fullscreen_manager.exit()
    full_load = app.detector.loads[-1]
    assert set(full_load) == {c["id"] for c in app.ui.abs_json_data}


def test_esc_binding_lifecycle(app):
    assert not keys._bindings
    fullscreen_manager.enter("page_tile")
    escape_bindings = [b for b in keys._bindings if b.key_combo == "ESCAPE"]
    assert len(escape_bindings) == 1

    event = types.SimpleNamespace(value="PRESS", type="ESC", ctrl=False, shift=False, alt=False)
    assert keys.dispatch(event) is True  # ESC consumed -> exit()
    assert not fullscreen_manager.is_active()
    assert not [b for b in keys._bindings if b.key_combo == "ESCAPE"]  # unbound

    # exit unbinds even without ESC
    fullscreen_manager.enter("page_tile")
    fullscreen_manager.exit()
    assert not keys._bindings


def test_input_router_consumes_all_events_while_active(app):
    input_router.update_hover_state(False)
    assert input_router.should_consume_event("LEFTMOUSE") is False

    fullscreen_manager.enter("page_tile")
    assert input_router.is_over_ui is True
    assert input_router.should_consume_event("LEFTMOUSE") is True
    input_router.update_hover_state(False)  # hit detection sees no drawn hit
    assert input_router.is_over_ui is True  # backdrop counts as drawn UI

    fullscreen_manager.exit()
    input_router.update_hover_state(False)
    assert input_router.is_over_ui is False
    assert input_router.should_consume_event("LEFTMOUSE") is False


def test_media_keeps_playing_across_enter_exit(app):
    app.clock.play()
    app.state["now"] = 5.0
    assert app.clock.current_time == pytest.approx(5.0)

    fullscreen_manager.enter("page_tile")
    app.state["now"] = 8.0
    assert app.clock.paused is False
    assert app.clock.current_time == pytest.approx(8.0)  # clock never stopped

    fullscreen_manager.exit()
    app.state["now"] = 9.5
    assert app.clock.current_time == pytest.approx(9.5)
    assert app.clock.paused is False


def test_media_visibility_filter_skips_hidden_sources(app):
    outside = FakeSource(MediaClock(duration=10.0, loop=True, time_fn=lambda: 0.0))
    media_manager._sources["card"] = outside
    inside = media_manager._sources["page_tile"]

    fullscreen_manager.enter("page_tile")
    media_manager.tick(1.0)
    assert inside.tick_calls == 1
    assert outside.tick_calls == 0  # hidden: no frame pull/upload

    fullscreen_manager.exit()
    media_manager.tick(2.0)
    assert inside.tick_calls == 2
    assert outside.tick_calls == 1  # filter cleared


def test_force_exit_idempotent_and_teardown_safe(app):
    fullscreen_manager.force_exit()  # idle no-op
    assert not fullscreen_manager.is_active()

    fullscreen_manager.enter("page_tile")
    fullscreen_manager.force_exit()
    assert not fullscreen_manager.is_active()
    assert not keys._bindings
    assert input_router._fullscreen_capture is False
    assert media_manager._visibility_filter is None
    assert app.pipeline.fs_active is False

    fullscreen_manager.force_exit()  # double call safe
    assert not fullscreen_manager.is_active()


def test_force_exit_wired_at_every_teardown_site():
    """The lifecycle trio stays together: every media_manager.shutdown()
    teardown site (render cancel/stop/unregister, addon unregister) and the
    reparse operator must force-exit fullscreen alongside."""
    render_src = (REPO_ROOT / "puree" / "render.py").read_text(encoding="utf-8")
    init_src = (REPO_ROOT / "puree" / "__init__.py").read_text(encoding="utf-8")
    parser_op_src = (REPO_ROOT / "puree" / "parser_op.py").read_text(encoding="utf-8")

    for src, shutdown_count in ((render_src, 3), (init_src, 1)):
        chunks = src.split("media_manager.shutdown()")
        assert len(chunks) - 1 == shutdown_count
        for chunk in chunks[:-1]:  # text BEFORE each shutdown call
            assert "fullscreen_manager.force_exit()" in chunk[-2500:], (
                "media_manager.shutdown() site without a preceding fullscreen force_exit"
            )
    assert "fullscreen_manager.force_exit()" in parser_op_src
    assert parser_op_src.index("fullscreen_manager.force_exit()") < parser_op_src.index("wire_video_controls")


def test_enter_refused_without_ui_or_region(app):
    parser_op.XWZ_UI = None
    assert fullscreen_manager.enter("page_tile") is False
    parser_op.XWZ_UI = app.ui
    assert fullscreen_manager.enter("nonexistent_container") is False
    render._render_data = None  # no pipeline and no space -> no region
    assert fullscreen_manager.enter("page_tile") is False
    assert not fullscreen_manager.is_active()
    render._render_data = app.pipeline


def test_toggle_semantics(app):
    assert fullscreen_manager.toggle("page_tile") is True
    assert fullscreen_manager.active_id == "page_tile"
    assert fullscreen_manager.toggle("page_tile") is False  # toggled off
    assert not fullscreen_manager.is_active()
    fullscreen_manager.toggle("page_tile")
    assert fullscreen_manager.toggle("card") is True  # toggle other = swap
    assert fullscreen_manager.active_id == "card"


# ── public API level (Phase B): Container surface + events ──────────


def test_container_api_delegates_to_manager(app):
    tile = app.ui.get_by_id("page_tile")
    card = app.ui.get_by_id("card")

    assert tile.fullscreen is False
    assert tile.exit_fullscreen() is False  # idle no-op

    assert tile.request_fullscreen() is True
    assert fullscreen_manager.active_id == "page_tile"
    assert tile.fullscreen is True
    assert card.fullscreen is False

    # exit_fullscreen only exits when THIS container is the active element
    assert card.exit_fullscreen() is False
    assert fullscreen_manager.is_active()
    assert tile.exit_fullscreen() is True
    assert not fullscreen_manager.is_active()
    assert tile.fullscreen is False


def test_on_fullscreen_change_event_sequences(app):
    """Enter/exit/swap/ESC/force_exit sequences: fn(container, bool) fires
    AFTER the mode change commits (handlers read the new state); swap fires
    False for the old element then True for the new one."""
    log = []
    tile = app.ui.get_by_id("page_tile")
    card = app.ui.get_by_id("card")
    tile.on_fullscreen_change.append(lambda c, fs: log.append((c.id, fs, fullscreen_manager.active_id)))
    card.on_fullscreen_change.append(lambda c, fs: log.append((c.id, fs, fullscreen_manager.active_id)))

    tile.request_fullscreen()
    assert log == [("page_tile", True, "page_tile")]

    card.request_fullscreen()  # swap
    assert log[1:] == [("page_tile", False, None), ("card", True, "card")]

    # re-entering the active element is a no-op success - no event
    n = len(log)
    assert card.request_fullscreen() is True
    assert len(log) == n

    # the ESC path (manager binding) fires False like any exit
    event = types.SimpleNamespace(value="PRESS", type="ESC", ctrl=False, shift=False, alt=False)
    assert keys.dispatch(event) is True
    assert log[-1] == ("card", False, None)

    # force_exit (hot reload / reparse / teardown) fires False too
    tile.request_fullscreen()
    fullscreen_manager.force_exit()
    assert log[-2:] == [("page_tile", True, "page_tile"), ("page_tile", False, None)]


def test_fullscreen_change_handler_errors_are_swallowed(app):
    tile = app.ui.get_by_id("page_tile")
    seen = []

    def bad_handler(container, is_fullscreen):
        raise RuntimeError("boom")

    tile.on_fullscreen_change.append(bad_handler)
    tile.on_fullscreen_change.append(lambda c, fs: seen.append(fs))

    assert tile.request_fullscreen() is True  # enter unaffected
    assert seen == [True]
    assert tile.exit_fullscreen() is True
    assert seen == [True, False]


def test_media_fullscreenchange_alias_and_ordering(app):
    """Media containers get 'fullscreenchange' through their EXISTING
    MediaController, fired AFTER the container list; generic containers
    never create a controller entry."""
    order = []
    tile = app.ui.get_by_id("page_tile")
    tile.on_fullscreen_change.append(lambda c, fs: order.append(("container", fs)))

    controller = media_manager.controller_for("page_tile")
    fn = controller.on(
        "fullscreenchange",
        lambda m: order.append(("media", m.container_id == fullscreen_manager.active_id)),
    )

    assert tile.request_fullscreen() is True
    assert order == [("container", True), ("media", True)]  # container FIRST

    order.clear()
    assert tile.exit_fullscreen() is True
    assert order == [("container", False), ("media", False)]

    controller.off("fullscreenchange", fn)

    # generic (non-media) fullscreen adds nothing to the controller registry
    assert "card" not in media_manager._controllers
    card = app.ui.get_by_id("card")
    assert card.request_fullscreen() is True
    assert "card" not in media_manager._controllers
    card.exit_fullscreen()


def test_controls_fullscreen_button_end_to_end(app):
    """The REAL controls wiring against the REAL manager: the button click
    enters via the Container API, icons flip on the EVENT (incl. the ESC
    exit), auto-hide keeps working inside the mode, and seek geometry
    switches to the PRIVATE box_abs box while fullscreen."""
    from puree import parser
    from puree.media import controls
    from puree.media.controls import wire_video_controls
    from puree.mouse_op import mouse_state

    assert wire_video_controls(app.ui) == 1
    w = controls._wired[0]
    try:
        assert w.fs_btn is not None
        assert w.fs_ic.style.display == "FLEX"
        assert w.exit_fs_ic.style.display == "NONE"

        # button -> request_fullscreen() -> manager active; the event flips
        w.fs_btn.click[0]({})
        assert fullscreen_manager.active_id == "page_tile"
        assert w.fs_ic.style.display == "NONE"
        assert w.exit_fs_ic.style.display == "FLEX"

        # drag-seek while fullscreen reads the PRIVATE track box (box_abs)
        track_box = fullscreen_manager.box_abs(w.track.id)
        assert track_box is not None
        assert track_box != parser.node_flat_abs[w.track.id]  # really private
        x_px = track_box["x"] + track_box["width"] * 0.75
        mouse_state.mouse_pos[0] = (x_px / app.ui.canvas_size[0]) * 2.0 - 1.0
        w.track.click[0]({})  # press = click-jump seek through the same box
        assert app.clock.current_time == pytest.approx(0.75 * 40.0, abs=0.2)
        mouse_state.update_click(False)

        # auto-hide keeps working inside fullscreen (hit results apply by id)
        w.controller.play()
        w._on_video_hoverout({})
        assert w.wrapper.style.opacity == 0.0
        w._on_video_hover({})
        assert w.wrapper.style.opacity == 1.0
        w.controller.pause()

        # ESC exits -> the EVENT flips the icon back (no click involved)
        event = types.SimpleNamespace(value="PRESS", type="ESC", ctrl=False, shift=False, alt=False)
        assert keys.dispatch(event) is True
        assert not fullscreen_manager.is_active()
        assert w.fs_ic.style.display == "FLEX"
        assert w.exit_fs_ic.style.display == "NONE"

        # back in normal mode the seek math reads the MAIN box again
        main_box = parser.node_flat_abs[w.track.id]
        x_px = main_box["x"] + main_box["width"] * 0.25
        mouse_state.mouse_pos[0] = (x_px / app.ui.canvas_size[0]) * 2.0 - 1.0
        w.track.click[0]({})
        assert app.clock.current_time == pytest.approx(0.25 * 40.0, abs=0.2)
        mouse_state.update_click(False)

        # unwire clears the fullscreen registrations with everything else
        video = w.video
        unwire_video_controls()
        assert video.on_fullscreen_change == []
    finally:
        unwire_video_controls()


# ── render level: draw short-circuit ─────────────────────────────────


def _prime_pipeline_for_draw(app):
    pipeline = app.pipeline
    pipeline.native_shader = _RecordingShader("container_shader")
    assert pipeline.create_container_batch(len(app.ui.abs_json_data))
    assert pipeline.create_data_texture(app.ui.abs_json_data)
    pipeline.running = True
    return pipeline


def test_is_active_gates_container_pass(app, monkeypatch):
    pipeline = _prime_pipeline_for_draw(app)
    scrollbar_calls = []
    monkeypatch.setattr(pipeline, "_draw_scrollbars", lambda: scrollbar_calls.append(1))
    monkeypatch.setattr(pipeline, "_draw_debug_overlay", lambda: None)

    # inactive: normal pass binds the MAIN texture and draws scrollbars
    _drawn_batches.clear()
    pipeline.draw_texture()
    samplers = [c for c in pipeline.native_shader.calls if c[0] == "sampler" and c[1] == "containerData"]
    assert samplers[-1][2] is pipeline.data_texture
    assert scrollbar_calls == [1]

    fullscreen_manager.enter("page_tile")
    pipeline.native_shader.calls.clear()
    _drawn_batches.clear()
    _builtin_shader.calls.clear()
    scrollbar_calls.clear()

    pipeline.draw_texture()

    # backdrop first: opaque black region quad through UNIFORM_COLOR
    assert ("float", "color", (0.0, 0.0, 0.0, 1.0)) in _builtin_shader.calls
    assert _drawn_batches[0].shader is _builtin_shader
    assert _drawn_batches[0].payload["pos"][2] == (float(REGION[0]), float(REGION[1]))
    # then the fullscreen main split - never the resident main texture
    samplers = [c for c in pipeline.native_shader.calls if c[0] == "sampler" and c[1] == "containerData"]
    assert len(samplers) == 1
    assert samplers[0][2] is pipeline.fs_data_texture
    assert samplers[0][2] is not pipeline.data_texture
    # scrollbars + debug overlay skipped while active
    assert scrollbar_calls == []
    # main textures stayed resident (exit = instant)
    assert pipeline.data_texture is not None

    fullscreen_manager.exit()
    pipeline.native_shader.calls.clear()
    pipeline.draw_texture()
    samplers = [c for c in pipeline.native_shader.calls if c[0] == "sampler" and c[1] == "containerData"]
    assert samplers[-1][2] is pipeline.data_texture
    assert scrollbar_calls == [1]


def test_is_active_gates_overlay_pass(app):
    pipeline = _prime_pipeline_for_draw(app)

    fullscreen_manager.enter("page_tile")
    pipeline.native_shader.calls.clear()
    pipeline.draw_overlay_texture()
    samplers = [c for c in pipeline.native_shader.calls if c[0] == "sampler" and c[1] == "containerData"]
    assert len(samplers) == 1
    assert samplers[0][2] is pipeline.fs_overlay_texture  # controls above media

    # generic card: no overlay members -> overlay handler is a no-op
    fullscreen_manager.enter("card")
    pipeline.native_shader.calls.clear()
    pipeline.draw_overlay_texture()
    assert not pipeline.native_shader.calls

    fullscreen_manager.exit()


def test_hover_index_remap_full_to_local(app):
    fullscreen_manager.enter("page_tile")
    pipeline = app.pipeline

    full_index_by_id = pipeline._container_id_to_index
    main_ids = [c["id"] for c in fullscreen_manager._flat if not c["overlay"]]
    overlay_ids = [c["id"] for c in fullscreen_manager._flat if c["overlay"]]

    # hovering the fullscreen root remaps to its LOCAL main-split slot
    pipeline._current_hover_index = full_index_by_id["page_tile"]
    pipeline._current_click_index = -1
    hover, click = pipeline._pass_state_indices(pipeline._fs_main_index_map)
    assert hover == float(main_ids.index("page_tile"))
    assert click == -1.0
    # ... and to -1 in the overlay split
    hover, _ = pipeline._pass_state_indices(pipeline._fs_overlay_index_map)
    assert hover == -1.0

    # hovering a NON-subtree container highlights nothing in either split
    pipeline._current_hover_index = full_index_by_id["card"]
    assert pipeline._pass_state_indices(pipeline._fs_main_index_map) == (-1.0, -1.0)
    assert pipeline._pass_state_indices(pipeline._fs_overlay_index_map) == (-1.0, -1.0)

    # an overlay-split member (controls bar) lands in the overlay map
    bar_full = full_index_by_id["page_tile_puree_vc"]
    pipeline._current_hover_index = bar_full
    hover, _ = pipeline._pass_state_indices(pipeline._fs_overlay_index_map)
    assert hover == float(overlay_ids.index("page_tile_puree_vc"))

    pipeline._current_hover_index = -1


def test_draw_filters_expose_subtree_membership(app):
    assert fullscreen_manager.visible_instance_ids() is None  # inactive = draw all
    fullscreen_manager.enter("page_tile")
    visible = fullscreen_manager.visible_instance_ids()
    assert visible is not None
    assert "page_tile" in visible
    assert any(cid.endswith("_vc_time") for cid in visible)  # controls included
    assert "card" not in visible and "root" not in visible
    # box_abs serves Phase B (controls seek math) the PRIVATE track box
    assert fullscreen_manager.box_abs("page_tile")["width"] == float(REGION[0])
    assert fullscreen_manager.box_abs("card") is None
    fullscreen_manager.exit()
    assert fullscreen_manager.visible_instance_ids() is None
    assert fullscreen_manager.box_abs("page_tile") is None
