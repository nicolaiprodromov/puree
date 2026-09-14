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
"""Unit tests for the default video controls (MEDIA_PLAN section 7).

- Injection: the REAL ``puree.parser.UI`` (namespace-mounted package,
  stubbed ``bpy``) parses apps with ``video:`` + ``controls: true`` and
  must inject the namespaced [video_controls] subtree as the LAST child,
  overlay-flagged, with the right passive split - including the
  user-component-shadows-default contract.
- Wiring: ``puree.media.controls`` against a fake source (real
  MediaClock with an injected time source) registered in the real
  MediaManager - button toggles, icon display flips, timeupdate labels,
  seek math from the real layout boxes, the drag lifecycle through
  simulated mouse_state callbacks, auto-hide opacity, idempotent
  rewiring and clean unwiring.
- Assets: the component YAML/SCSS compile through the real loaders.
"""

import sys
import textwrap
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
NATIVE_DIR = REPO_ROOT / "puree" / "native_binaries"
PYD = NATIVE_DIR / ("puree_rust_core.pyd" if sys.platform == "win32" else "puree_rust_core.so")

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


bpy_mod = _module("bpy")
bpy_mod.types = _module("bpy.types", Operator=object, SpaceView3D=object)
bpy_mod.props = _module(
    "bpy.props",
    StringProperty=_prop,
    IntProperty=_prop,
    FloatProperty=_prop,
    BoolProperty=_prop,
    EnumProperty=_prop,
)

pkg = sys.modules.get("puree")
if pkg is None:
    pkg = types.ModuleType("puree")
    pkg.__path__ = [str(REPO_ROOT / "puree")]
    sys.modules["puree"] = pkg
if not hasattr(pkg, "get_addon_root"):
    pkg.get_addon_root = lambda: str(REPO_ROOT)

from puree.media import controls, media_manager  # noqa: E402
from puree.media.clock import MediaClock  # noqa: E402
from puree.media.controls import format_time, unwire_video_controls, wire_video_controls  # noqa: E402

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
            demo_video:
              class: demo_video
              video: demo_clip.mp4
              controls: true
              muted: true
            plain_video:
              class: demo_video
              video: demo_clip.mp4
    """
)

APP_SCSS = ".root { width: 100%; height: 100%; }\n.demo_video { width: 320px; height: 200px; }\n"


def _build_ui(addon_dir):
    from puree.parser import UI

    saved_root = pkg.get_addon_root
    pkg.get_addon_root = lambda: str(addon_dir)
    try:
        return UI(str(Path(addon_dir) / "index.yaml"), str(addon_dir), canvas_size=(800, 600))
    finally:
        pkg.get_addon_root = saved_root


@pytest.fixture()
def app(tmp_path):
    (tmp_path / "index.yaml").write_text(APP_YAML)
    (tmp_path / "style.scss").write_text(APP_SCSS)
    ui = _build_ui(tmp_path)
    yield types.SimpleNamespace(ui=ui, addon_dir=tmp_path)
    unwire_video_controls()
    media_manager._sources.clear()
    media_manager._controllers.clear()


# ── injection ────────────────────────────────────────────────────────


def test_injection_appends_namespaced_subtree_as_last_child(app):
    video = app.ui.get_by_id("demo_video")
    assert [c.id for c in video.children][-1] == "demo_video_puree_vc"

    by_id = {c["id"]: c for c in app.ui.abs_json_data}
    ns = "demo_video_puree_vc"
    for leaf in (
        f"{ns}_vc_play",
        f"{ns}_vc_play_vc_play_ic",
        f"{ns}_vc_play_vc_play_ic_vc_play_img",
        f"{ns}_vc_play_vc_pause_ic",
        f"{ns}_vc_time",
        f"{ns}_vc_track",
        f"{ns}_vc_track_vc_rail",
        f"{ns}_vc_track_vc_rail_vc_fill",
        f"{ns}_vc_track_vc_rail_vc_fill_vc_thumb",
        f"{ns}_vc_duration",
        f"{ns}_vc_mute",
        f"{ns}_vc_mute_vc_sound_ic",
        f"{ns}_vc_mute_vc_mute_ic",
        f"{ns}_vc_fullscreen",
        f"{ns}_vc_fullscreen_vc_fs_ic",
        f"{ns}_vc_fullscreen_vc_fs_ic_vc_fs_img",
        f"{ns}_vc_fullscreen_vc_exit_fs_ic",
        f"{ns}_vc_fullscreen_vc_exit_fs_ic_vc_exit_fs_img",
    ):
        assert leaf in by_id, f"missing injected node {leaf}"

    # icon assets ride the img attribute
    play_img = app.ui.get_by_id(f"{ns}_vc_play_vc_play_ic_vc_play_img")
    assert play_img.img == "media_play.svg"
    fs_img = app.ui.get_by_id(f"{ns}_vc_fullscreen_vc_fs_ic_vc_fs_img")
    assert fs_img.img == "media_fullscreen.svg"
    exit_fs_img = app.ui.get_by_id(f"{ns}_vc_fullscreen_vc_exit_fs_ic_vc_exit_fs_img")
    assert exit_fs_img.img == "media_exit_fullscreen.svg"

    # the fullscreen button sits AFTER the mute button (bar order)
    wrapper = app.ui.get_by_id(ns)
    child_ids = [c.id for c in wrapper.children]
    assert child_ids.index(f"{ns}_vc_fullscreen") == child_ids.index(f"{ns}_vc_mute") + 1


def test_injection_sets_overlay_passive_and_focus_flags(app):
    by_id = {c["id"]: c for c in app.ui.abs_json_data}
    ns = "demo_video_puree_vc"

    assert by_id["demo_video"]["overlay"] is False
    subtree = [c for c in app.ui.abs_json_data if c["id"].startswith(ns)]
    assert len(subtree) == 22  # 17 pre-fullscreen + the 5 vc_fullscreen nodes
    assert all(c["overlay"] for c in subtree)

    # hit split: wrapper/decoration passive, the four controls are targets
    assert by_id[ns]["passive"] is True
    assert by_id[f"{ns}_vc_play"]["passive"] is False
    assert by_id[f"{ns}_vc_track"]["passive"] is False
    assert by_id[f"{ns}_vc_mute"]["passive"] is False
    assert by_id[f"{ns}_vc_fullscreen"]["passive"] is False
    for decorative in (
        f"{ns}_vc_time",
        f"{ns}_vc_duration",
        f"{ns}_vc_track_vc_rail",
        f"{ns}_vc_track_vc_rail_vc_fill",
        f"{ns}_vc_play_vc_play_ic",
        f"{ns}_vc_play_vc_play_ic_vc_play_img",
        f"{ns}_vc_fullscreen_vc_fs_ic",
        f"{ns}_vc_fullscreen_vc_fs_ic_vc_fs_img",
        f"{ns}_vc_fullscreen_vc_exit_fs_ic",
        f"{ns}_vc_fullscreen_vc_exit_fs_ic_vc_exit_fs_img",
    ):
        assert by_id[decorative]["passive"] is True, decorative

    # SPACE scoping needs a focusable video (flat dict feeds hit_op)
    assert by_id["demo_video"]["focusable"] is True

    # labels have initial text so their text instances exist at startup
    assert app.ui.get_by_id(f"{ns}_vc_time").text == "0:00"
    assert app.ui.get_by_id(f"{ns}_vc_duration").text == "0:00"


def test_injection_css_lands_in_first_cascade(app):
    """The per-instance SCSS goes to _component_css - the FIRST parse_css
    cascade must style the bar (absolute bottom anchor + fade transition)."""
    by_id = {c["id"]: c for c in app.ui.abs_json_data}
    bar = by_id["demo_video_puree_vc"]
    assert bar["size"] == [320.0, 32.0]  # full video width x $vc_bar_height
    assert bar["position"][1] == 168.0  # anchored to the video bottom (200-32)
    transitions = bar.get("_transitions") or []
    assert any(t["property"] == "opacity" and t["duration"] > 0 for t in transitions)


def test_no_controls_means_no_injection(app):
    plain = app.ui.get_by_id("plain_video")
    assert plain.children == []
    assert not any("plain_video_puree_vc" in c["id"] for c in app.ui.abs_json_data)


def test_user_component_shadows_default(tmp_path):
    (tmp_path / "index.yaml").write_text(APP_YAML)
    (tmp_path / "style.scss").write_text(APP_SCSS)
    comp_dir = tmp_path / "components"
    comp_dir.mkdir()
    (comp_dir / "video_controls.yaml").write_text(
        "video_controls:\n  class: video_controls\n  custom_bar:\n    class: video_controls_bar\n    passive: true\n"
    )
    ui = _build_ui(tmp_path)
    ns = "demo_video_puree_vc"
    assert ui.get_by_id(f"{ns}_custom_bar") is not None
    assert ui.get_by_id(f"{ns}_vc_play") is None  # default tree NOT used


def test_user_scss_can_hide_fullscreen_button(tmp_path):
    """There is no allow_fullscreen YAML attr (v1 decision, FULLSCREEN_PLAN):
    the button is always injected with controls: true. COMPONENTS.md
    documents hiding it per video from user SCSS via the namespaced class -
    display:none at parse time bakes Display.NONE into the layout node, so
    the button never gets a box (no draw, no hit target, no icons)."""
    (tmp_path / "index.yaml").write_text(APP_YAML)
    (tmp_path / "style.scss").write_text(APP_SCSS + ".demo_video_puree_vc_fullscreen { display: none; }\n")
    ui = _build_ui(tmp_path)

    button = ui.get_by_id("demo_video_puree_vc_vc_fullscreen")
    assert button is not None  # still injected - just permanently hidden
    assert button.style.display == "NONE"

    by_id = {c["id"]: c for c in ui.abs_json_data}
    assert by_id["demo_video_puree_vc_vc_fullscreen"]["size"] == [0.0, 0.0]
    assert by_id["demo_video_puree_vc_vc_fullscreen_vc_fs_ic"]["size"] == [0.0, 0.0]
    # the rest of the bar is unaffected
    assert by_id["demo_video_puree_vc_vc_mute"]["size"] == [22.0, 22.0]

    # wiring still succeeds - the boxless button just never fires
    assert wire_video_controls(ui) == 1
    unwire_video_controls()
    media_manager._sources.clear()
    media_manager._controllers.clear()


# ── wiring (fake source in the real MediaManager) ────────────────────


class FakeSource:
    """Clock-only source (GifSource shape) - the controller falls back to
    the clock for play/pause/seek and stores muted/volume as attributes."""

    def __init__(self, clock, muted=False):
        self.clock = clock
        self.released = False
        self.instance = object()
        self.ready_state = "ready"
        self.muted = muted


@pytest.fixture()
def wired(app):
    state = {"now": 0.0}
    clock = MediaClock(duration=40.0, loop=False, time_fn=lambda: state["now"])
    media_manager._sources.clear()
    media_manager._controllers.clear()
    media_manager._sources["demo_video"] = FakeSource(clock, muted=True)

    assert wire_video_controls(app.ui) == 1
    wired = controls._wired[0]

    from puree.mouse_op import mouse_state

    def mouse_to_track_frac(frac):
        from puree import parser

        box = parser.node_flat_abs[wired.track.id]
        x = box["x"] + box["width"] * frac
        mouse_state.mouse_pos[0] = (x / app.ui.canvas_size[0]) * 2.0 - 1.0

    yield types.SimpleNamespace(
        app=app,
        wired=wired,
        controller=wired.controller,
        clock=clock,
        state=state,
        mouse_state=mouse_state,
        mouse_to_track_frac=mouse_to_track_frac,
    )


def test_wire_initial_state(wired):
    w = wired.wired
    # paused -> play icon visible, pause icon display-swapped away
    assert w.play_ic.style.display == "FLEX"
    assert w.pause_ic.style.display == "NONE"
    assert w.play_img.style.opacity == 1.0
    assert w.pause_img.style.opacity == 0.0
    # muted (from the source) -> mute icon visible
    assert w.mute_ic.style.display == "FLEX"
    assert w.sound_ic.style.display == "NONE"
    # duration was already known -> label formatted once at wire time
    assert w.duration_label.text == "0:40"
    assert w.time_label.text == "0:00"


def test_play_button_toggles_and_icons_flip_on_events(wired):
    w = wired.wired
    w.play_btn.click[0]({})
    assert wired.controller.paused is False
    wired.controller._pump(0.3)  # 'play' event -> icon flip
    assert w.play_ic.style.display == "NONE"
    assert w.pause_ic.style.display == "FLEX"
    assert w.pause_img.style.opacity == 1.0

    w.play_btn.click[0]({})
    assert wired.controller.paused is True
    wired.controller._pump(0.6)  # 'pause' event
    assert w.play_ic.style.display == "FLEX"
    assert w.pause_ic.style.display == "NONE"


def test_mute_button_flips_muted_and_icons(wired):
    w = wired.wired
    assert w._muted() is True
    w.mute_btn.click[0]({})
    assert wired.controller.muted is False
    assert w.sound_ic.style.display == "FLEX"
    assert w.mute_ic.style.display == "NONE"
    w.mute_btn.click[0]({})
    assert wired.controller.muted is True
    assert w.mute_ic.style.display == "FLEX"


def test_timeupdate_updates_labels_and_fill(wired):
    w = wired.wired
    wired.controller.play()
    wired.state["now"] = 30.0
    wired.controller._pump(1.0)  # timeupdate
    assert w.time_label.text == "0:30"
    assert w.duration_label.text == "0:40"
    assert w._last_fill_pct == 75  # 30/40
    assert w.fill.style.width == "75%"


def test_seek_click_maps_track_x_to_duration(wired):
    w = wired.wired
    wired.mouse_to_track_frac(0.25)
    w.track.click[0]({})  # click fires on press -> immediate seek
    assert w._dragging is True
    assert wired.controller.current_time == pytest.approx(10.0, abs=0.2)
    assert w._last_fill_pct == 25


def test_drag_lifecycle_with_throttled_scrub(wired, monkeypatch):
    w = wired.wired
    monkeypatch.setattr(controls, "SEEK_INTERVAL", 999.0)  # deterministic throttle

    wired.mouse_to_track_frac(0.25)
    w.track.click[0]({})  # press seeks immediately (forced)
    assert wired.controller.current_time == pytest.approx(10.0, abs=0.2)

    # move to 50%: fill follows locally, seek is throttled away
    wired.mouse_to_track_frac(0.5)
    wired.mouse_state.update_mouse([wired.mouse_state.mouse_pos[0], 0.0])
    assert w._last_fill_pct == 50
    assert wired.controller.current_time == pytest.approx(10.0, abs=0.2)

    # release: gesture ends with a final, unthrottled seek
    wired.mouse_state.update_click(False)
    assert w._dragging is False
    assert wired.controller.current_time == pytest.approx(20.0, abs=0.2)


def test_drag_ignored_before_metadata(wired):
    w = wired.wired
    # swap in a metadata-less source (controllers re-resolve per access)
    media_manager._sources["demo_video"] = FakeSource(MediaClock(duration=0.0))
    wired.mouse_to_track_frac(0.5)
    w.track.click[0]({})
    assert w._dragging is False


def test_autohide_opacity(wired):
    w = wired.wired
    # playing + pointer leaves the video -> fade out (snap without pipeline)
    wired.controller.play()
    wired.controller._pump(0.3)  # 'play' event (pointer not over the video)
    w._on_video_hoverout({})
    assert w.wrapper.style.opacity == 0.0
    # pointer returns -> visible
    w._on_video_hover({})
    assert w.wrapper.style.opacity == 1.0
    # hoverout while PAUSED keeps the bar visible
    wired.controller.pause()
    wired.controller._pump(0.6)
    w._on_video_hoverout({})
    assert w.wrapper.style.opacity == 1.0
    # the 'pause' EVENT forces the bar back on even after a fade-out
    wired.controller.play()
    wired.controller._pump(0.9)
    w._on_video_hoverout({})
    assert w.wrapper.style.opacity == 0.0
    wired.controller.pause()
    wired.controller._pump(1.2)  # edge-detected pause -> _set_bar_visible(True)
    assert w.wrapper.style.opacity == 1.0


def test_bar_fade_reads_scss_transition(wired):
    duration, timing, delay = wired.wired._fade
    assert duration == pytest.approx(0.16)  # $vc_fade: 160ms
    assert timing == "ease"
    assert delay == 0.0


def test_space_binding_scoped_to_video(wired):
    from puree.keyboard import keys

    scoped = [b for b in keys._bindings if b.key_combo == "SPACE" and b.container_id == "demo_video"]
    assert len(scoped) == 1
    scoped[0].callback()
    assert wired.controller.paused is False  # SPACE toggled play


# ── fullscreen button (FULLSCREEN_PLAN Phase B) ──────────────────────


def test_fullscreen_button_click_delegates_to_container_api(wired, monkeypatch):
    """Click toggles through the PUBLIC Container surface: windowed ->
    request_fullscreen() -> manager.enter(video.id); this-video-active ->
    exit_fullscreen() -> manager.exit(); another element active ->
    exit_fullscreen() refuses by design, so the click swaps via enter()."""
    from puree.fullscreen import fullscreen_manager

    w = wired.wired
    calls = []
    monkeypatch.setattr(fullscreen_manager, "enter", lambda cid: calls.append(("enter", cid)) or True)
    monkeypatch.setattr(fullscreen_manager, "exit", lambda: calls.append(("exit",)) or True)

    w.fs_btn.click[0]({})
    assert calls == [("enter", "demo_video")]

    monkeypatch.setattr(fullscreen_manager, "_active_id", "demo_video")
    assert w.video.fullscreen is True
    w.fs_btn.click[0]({})
    assert calls == [("enter", "demo_video"), ("exit",)]

    monkeypatch.setattr(fullscreen_manager, "_active_id", "some_other_element")
    assert w.video.fullscreen is False
    assert w.video.exit_fullscreen() is False  # only exits when THIS is active
    w.fs_btn.click[0]({})
    assert calls[-1] == ("enter", "demo_video")  # swap request


def test_fullscreen_icons_flip_on_event_not_click(wired, monkeypatch):
    from puree.fullscreen import fullscreen_manager

    w = wired.wired
    # initial: enter glyph visible, exit glyph display-swapped away
    assert w.fs_ic.style.display == "FLEX"
    assert w.exit_fs_ic.style.display == "NONE"
    assert w.fs_img.style.opacity == 1.0
    assert w.exit_fs_img.style.opacity == 0.0

    # the CLICK itself must not flip anything - ESC/script exits never go
    # through the click, so the event is the single source of truth
    monkeypatch.setattr(fullscreen_manager, "enter", lambda cid: True)
    w.fs_btn.click[0]({})
    assert w.fs_ic.style.display == "FLEX"
    assert w.exit_fs_ic.style.display == "NONE"

    # the manager-fired on_fullscreen_change event flips (enter/exit/ESC/
    # force_exit all funnel through _fire_fullscreen_change)
    fullscreen_manager._fire_fullscreen_change(w.video, w.video.id, True)
    assert w.fs_ic.style.display == "NONE"
    assert w.fs_img.style.opacity == 0.0
    assert w.exit_fs_ic.style.display == "FLEX"
    assert w.exit_fs_img.style.opacity == 1.0

    fullscreen_manager._fire_fullscreen_change(w.video, w.video.id, False)
    assert w.fs_ic.style.display == "FLEX"
    assert w.exit_fs_ic.style.display == "NONE"


def test_track_geometry_prefers_fullscreen_box_when_active(wired, monkeypatch):
    """While fullscreen, seek math must read the PRIVATE layout box from
    fullscreen_manager.box_abs(track_id); parser.node_flat_abs (main tree)
    stays the source in normal mode - both for drag-scrub fractions and
    the press (click-jump) seek."""
    from puree import parser
    from puree.fullscreen import fullscreen_manager

    w = wired.wired
    main_box = parser.node_flat_abs[w.track.id]
    x_px = main_box["x"] + main_box["width"] * 0.6
    wired.mouse_state.mouse_pos[0] = (x_px / wired.app.ui.canvas_size[0]) * 2.0 - 1.0

    # normal mode: box_abs is None (inactive) -> node_flat_abs mapping
    assert fullscreen_manager.box_abs(w.track.id) is None
    assert w._track_frac() == pytest.approx(0.6, abs=0.01)

    # fullscreen: box_abs serves the private region-wide box -> new mapping
    fake_box = {"x": x_px - 30.0, "y": 568.0, "width": 300.0, "height": 32.0}
    monkeypatch.setattr(fullscreen_manager, "box_abs", lambda cid: fake_box if cid == w.track.id else None)
    assert w._track_frac() == pytest.approx(0.1, abs=0.01)  # 30 / 300

    # press-seek (click fires on PRESS) reads the same box: 10% of 40s
    w.track.click[0]({})
    assert w._dragging is True
    assert wired.controller.current_time == pytest.approx(4.0, abs=0.05)
    wired.mouse_state.update_click(False)  # release ends the gesture
    assert w._dragging is False

    # box_abs None again (exited / other element active) -> main mapping
    monkeypatch.setattr(fullscreen_manager, "box_abs", lambda cid: None)
    assert w._track_frac() == pytest.approx(0.6, abs=0.01)


def test_rewire_is_idempotent(wired):
    from puree.keyboard import keys

    assert wire_video_controls(wired.app.ui) == 1  # rewire same tree
    controller = controls._wired[0].controller
    assert len(controller._listeners.get("play", [])) == 1
    assert len(controller._listeners.get("timeupdate", [])) == 1
    assert len([b for b in keys._bindings if b.key_combo == "SPACE"]) == 1
    assert len(wired.mouse_state.callbacks) == 1
    # the fullscreen icon-flip handler never stacks (release removes it)
    assert len(controls._wired[0].video.on_fullscreen_change) == 1


def test_unwire_releases_every_registration(wired):
    from puree.keyboard import keys

    controller = wired.controller
    video = wired.wired.video
    unwire_video_controls()
    assert controls._wired == []
    assert not controller._listeners.get("play")
    assert not controller._listeners.get("timeupdate")
    assert not [b for b in keys._bindings if b.key_combo == "SPACE"]
    assert wired.mouse_state.callbacks == []
    assert video.on_fullscreen_change == []  # icon-flip handler cleared
    # Idempotent: the UI stop paths (render cancel / stop_ui / unregister)
    # call unwire right after media_manager.shutdown() - repeat calls on an
    # already-released state must be clean no-ops.
    unwire_video_controls()
    unwire_video_controls()
    assert controls._wired == []
    assert wired.mouse_state.callbacks == []
    assert not controller._listeners.get("play")
    assert not [b for b in keys._bindings if b.key_combo == "SPACE"]
    assert video.on_fullscreen_change == []


def test_stop_path_shutdown_then_unwire_is_clean(wired):
    """Mirrors the engine teardown order added at every UI stop site
    (render cancel / XWZ_OT_stop_ui / render+addon unregister):
    media_manager.shutdown() FIRST (controller registry cleared, sources
    released), THEN unwire - which must still detach the mouse callback,
    the SPACE binding and the listeners held on the controller object."""
    from puree.keyboard import keys

    controller = wired.controller
    media_manager.shutdown()
    assert media_manager._sources == {} and media_manager._controllers == {}

    unwire_video_controls()
    unwire_video_controls()  # idempotent in the real teardown order too
    assert controls._wired == []
    assert wired.mouse_state.callbacks == []
    assert not [b for b in keys._bindings if b.key_combo == "SPACE"]
    assert not controller._listeners.get("play")
    assert not controller._listeners.get("timeupdate")
    assert not controller.has_listeners()


def test_wiring_survives_missing_bar_nodes(app):
    """A degenerate (user-shadowed) template without the known leaves must
    not break wiring - features degrade to no-ops."""
    video = app.ui.get_by_id("demo_video")
    wrapper = video.children[-1]
    wrapper.children = []  # butcher the subtree
    assert wire_video_controls(app.ui) == 1
    w = controls._wired[0]
    assert w.play_btn is None and w.track is None
    w._on_media_timeupdate()  # label/fill guards
    w._apply_play_icons()  # icon guards


# ── time formatting ──────────────────────────────────────────────────


def test_format_time():
    assert format_time(0) == "0:00"
    assert format_time(9.9) == "0:09"
    assert format_time(65) == "1:05"
    assert format_time(600) == "10:00"
    assert format_time(3671) == "1:01:11"
    assert format_time(None) == "0:00"
    assert format_time(-3) == "0:00"


# ── assets: component YAML/SCSS through the real loaders ─────────────


def test_component_yaml_registered_by_defaults_loader():
    from puree.components.defaults import get_default_component_paths

    paths = get_default_component_paths()
    assert "video_controls" in paths
    import yaml

    data = yaml.safe_load(open(paths["video_controls"]))
    assert isinstance(data["video_controls"], dict)  # root key == filename


def test_component_scss_compiles_namespaced():
    import re

    from puree.native_bindings import SCSSCompiler

    scss_path = REPO_ROOT / "puree" / "components" / "defaults" / "video_controls.scss"
    out = SCSSCompiler().compile_file(str(scss_path), "vid_puree_vc", {}, "video_controls")
    out = re.sub(r"^([a-zA-Z_][\w]*)([\s:{])", r".\1\2", out, flags=re.MULTILINE)
    for cls in (
        ".vid_puree_vc {",
        ".vid_puree_vc_play {",
        ".vid_puree_vc_track {",
        ".vid_puree_vc_fill {",
        ".vid_puree_vc_fullscreen {",
        ".vid_puree_vc_fullscreen:hover {",
        ".vid_puree_vc_fs_ic {",
        ".vid_puree_vc_exit_fs_ic {",
    ):
        assert cls in out
    assert "transition: opacity 160ms ease;" in out
    # every SELECTOR must carry its class dot: the namespacer re-dots only
    # the first selector of a comma group, so the component avoids groups
    # (mixins instead) - this guards against reintroducing one.
    for line in out.splitlines():
        if "{" not in line:
            continue
        for selector in line.split("{")[0].split(","):
            selector = selector.strip()
            assert not selector or selector.startswith("."), f"bare selector: {line}"


def test_helloworld_styles_still_compile():
    from puree.native_bindings import SCSSCompiler

    out = SCSSCompiler().compile_file(str(REPO_ROOT / "tests" / "helloworld" / "style.scss"))
    assert ".media_video" in out


def test_helloworld_video_tile_has_controls():
    import yaml

    data = yaml.safe_load(open(REPO_ROOT / "tests" / "helloworld" / "index.yaml", encoding="utf-8"))
    theme = data["app"]["theme"][0]
    video = theme["root"]["page"]["page_body"]["section_media"]["media_video_frame"]["media_video"]
    assert video["controls"] is True
    assert video["video"] == "demo_video.mp4"


def test_helloworld_gif_tile_fullscreen_demo():
    """The gif tile demos the GENERIC fullscreen capability (Phase B):
    caption note + script.py drives the public Container API."""
    import yaml

    data = yaml.safe_load(open(REPO_ROOT / "tests" / "helloworld" / "index.yaml", encoding="utf-8"))
    theme = data["app"]["theme"][0]
    section = theme["root"]["page"]["page_body"]["section_media"]
    caption = section["media_caption"]["text"]
    assert "fullscreen" in caption
    assert "ESC exits" in caption

    script = (REPO_ROOT / "tests" / "helloworld" / "script.py").read_text(encoding="utf-8")
    assert "request_fullscreen()" in script
    assert "exit_fullscreen()" in script
    assert "on_fullscreen_change" in script


def test_icon_assets_exist_and_rasterize():
    sys.path.insert(0, str(NATIVE_DIR))
    try:
        import puree_rust_core as core
    finally:
        sys.path.remove(str(NATIVE_DIR))
    for name in (
        "media_play.svg",
        "media_pause.svg",
        "media_sound.svg",
        "media_mute.svg",
        "media_fullscreen.svg",
        "media_exit_fullscreen.svg",
    ):
        path = REPO_ROOT / "assets" / name
        assert path.exists(), name
        data = core.rasterize_svg(str(path), 16, 16)
        assert len(data) == 16 * 16 * 4
        assert any(data), f"{name} rasterized empty"
