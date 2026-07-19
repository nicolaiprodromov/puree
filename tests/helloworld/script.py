# ─────────────────────────────────────────────────────────────────────
#  Puree · hello world — script.py
#  The behavior layer. Structure lives in index.yaml, looks in
#  style.scss. Everything here is plain Python running inside Blender:
#  event handlers, timers, persistent storage and markdown rendering.
# ─────────────────────────────────────────────────────────────────────

import time

from puree.keyboard import keys
from puree.mouse_op import mouse_state
from puree.parser import node_flat_abs
from puree.storage import Storage
from puree.timers import clear, set_interval, set_timeout

# ── Palette (mirrors style.scss tokens — Blender dark theme) ─────────
ACCENT = "#4772b3"  # Blender selection blue
ACCENT_HI = "#5b8bd4"
ACCENT_INK = "#ffffff"
ORANGE = "#e87d0d"  # Blender active-object orange
SKY = "#6aa5dc"
GREY = "#9d9d9d"
TXT_DIM = "#a5a5a5"
TXT_MUTE = "#6f6f6f"
SURFACE = "#2d2d2d"
SURFACE_2 = "#3a3a3a"
LINE = "rgba(255, 255, 255, 0.08)"
LINE_STRONG = "rgba(255, 255, 255, 0.16)"

# ── Content ──────────────────────────────────────────────────────────
# The five pipeline stages, straight from the README's "How it works".
PIPELINE = [
    ("chip_parse", "Parse", "Rust-native parsers turn this YAML and SCSS into a styled container tree.", ACCENT),
    ("chip_layout", "Layout", "The Stretchable flexbox engine computes a responsive layout for every container.", SKY),
    ("chip_flatten", "Flatten", "Rust flattens the hierarchy into GPU-ready buffers — 17 texels per container.", GREY),
    ("chip_render", "Render", "ModernGL shaders draw the whole page as signed distance fields, in one pass.", ORANGE),
    (
        "chip_interact",
        "Interact",
        "Rust hit detection routes mouse, scroll and keyboard events back in real time.",
        ACCENT,
    ),
]

MARKDOWN_DEMO = "\n".join(
    [
        "## Quick start",
        "Plain markdown, rendered as containers.",
        "- pip install puree-ui",
        "- puree init && puree build",
        "```",
        "app:",
        "  theme:",
        "    - name: hello",
        "```",
        "> Save any file — hot reload repaints.",
        "---",
        "Built by set_markdown() in script.py.",
    ]
)

# Persistent state — survives Blender restarts (puree.storage).
_store = Storage("puree_helloworld")
_store.auto_save = True

STEP_MIN, STEP_MAX, STEP_DEFAULT = 0, 64, 8


def _read_input_text(container_id):
    """Read the current value of a <INPUT> field by container id.

    There is no public getter for input values yet, so this reaches into
    the engine's text-input registry — guarded, since it is private API.
    """
    try:
        from puree import text_input_op

        for inst in text_input_op._text_input_instances:
            if inst.container_id == container_id and inst.text:
                return inst.text.strip()
    except Exception:
        pass
    return ""


def _is_stale(root_ref):
    """True once hot reload has replaced *root_ref* with a fresh tree.

    Hot reload re-runs main() on every save, so long-lived callbacks
    (timers, key bindings) from the previous run use this to cancel
    themselves instead of piling up.
    """
    try:
        from puree import parser_op

        return parser_op.XWZ_UI is not None and parser_op.XWZ_UI.theme.root is not root_ref
    except Exception:
        return False


def main(self, app):
    root = app.theme.root

    # ── 07 · Markdown — rendered from this script ─────────────────────
    # Done first: set_markdown() rebuilds the container tree and re-runs
    # the style cascade, which would reset any set_property() styling
    # applied before it.
    root.md_body.set_markdown(
        MARKDOWN_DEMO,
        fonts={"regular": "NeueMontreal-Regular", "bold": "NeueMontreal-Bold", "mono": "NeueMontreal-Regular"},
    )

    # ── Draggable card — press the grab bar and move the page ────────
    # The engine has no drag event, so this builds one from parts it does
    # have: click fires on *press* (drag start), mouse_state streams every
    # move and the release, and margin-left/top are the runtime-settable
    # layout properties that position the card inside the flex-start root.
    page = root.page
    grab_bar = root.grab_bar

    def _mouse_px():
        """Current mouse position in layout px (origin top-left, y down)."""
        w, h = app.canvas_size
        nx, ny = mouse_state.mouse_pos  # NDC: x −1..1 left→right, y −1..1 top→bottom
        return (nx + 1.0) * 0.5 * w, (ny + 1.0) * 0.5 * h

    # pos = the card's applied position; drag = gesture bookkeeping
    pos = {"x": 0.0, "y": 0.0, "applied": None}
    drag = {"on": False, "mouse": (0.0, 0.0), "card": (0.0, 0.0)}

    def place_card(x, y):
        """Clamp (x, y) to the viewport and move the card there via margins."""
        box = node_flat_abs.get(page.id) or {}
        card_w, card_h = box.get("width", 0.0), box.get("height", 0.0)
        view_w, view_h = app.canvas_size
        x = max(0.0, min(x, view_w - card_w))
        y = max(0.0, min(y, view_h - card_h))
        pos["x"], pos["y"] = x, y
        applied = (int(x), int(y))
        if applied == pos["applied"]:
            return  # skip no-op relayouts while the mouse jitters within a px
        pos["applied"] = applied
        page.set_property("margin-left", f"{applied[0]}px")
        page.set_property("margin-top", f"{applied[1]}px")

    def center_card():
        box = node_flat_abs.get(page.id) or {}
        view_w, view_h = app.canvas_size
        place_card((view_w - box.get("width", 0.0)) / 2, (view_h - box.get("height", 0.0)) / 2)

    def on_grab(container):
        # click fires on press — remember where the gesture started
        box = node_flat_abs.get(page.id) or {}
        drag["on"] = True
        drag["mouse"] = _mouse_px()
        drag["card"] = (box.get("x", pos["x"]), box.get("y", pos["y"]))

    def on_mouse(kind, value):
        if _is_stale(root):
            # hot reload replaced the tree — retire outside the notify loop
            set_timeout(lambda: mouse_state.unregister_callback(on_mouse), 0)
            return
        if kind == "click" and not value and drag["on"]:
            drag["on"] = False
            _store.set("card.pos", [pos["x"], pos["y"]])
            console.log(f"[drag] card parked at ({int(pos['x'])}, {int(pos['y'])})")
        elif kind == "mouse" and drag["on"]:
            mx, my = _mouse_px()
            sx, sy = drag["mouse"]
            cx, cy = drag["card"]
            place_card(cx + (mx - sx), cy + (my - sy))

    grab_bar.click.append(on_grab)
    mouse_state.register_callback(on_mouse)

    # First position: wherever the card was left last session, else centered.
    try:
        saved_x, saved_y = _store.get("card.pos", None)
        place_card(float(saved_x), float(saved_y))
    except (TypeError, ValueError):
        center_card()

    # Keep the card reachable when the viewport is resized under it.
    size_state = {"wh": tuple(app.canvas_size)}

    def watch_resize():
        if _is_stale(root):
            clear(resize_timer)
            return
        wh = tuple(app.canvas_size)
        if wh != size_state["wh"]:
            size_state["wh"] = wh
            pos["applied"] = None  # force reapply — same px may now be out of bounds
            place_card(pos["x"], pos["y"])

    resize_timer = set_interval(watch_resize, 500)

    # ── 01 · Pipeline explorer ────────────────────────────────────────
    stage_name = root.stage_name
    stage_num = root.stage_num
    stage_desc = root.stage_desc
    stage_panel = root.stage_panel
    chips = {chip_id: getattr(root, chip_id) for chip_id, _, _, _ in PIPELINE}

    def select_stage(index):
        for i, (chip_id, name, desc, accent) in enumerate(PIPELINE):
            chip = chips[chip_id]
            if i == index:
                chip.set_property("background-color", ACCENT)
                chip.set_property("border-color", ACCENT)
                chip.set_property("color", ACCENT_INK)
                # Keep the selected chip blue while hovered — the SCSS
                # :hover slot would otherwise flip it back to dark.
                chip.set_property("hover-background-color", ACCENT_HI)
            else:
                chip.set_property("background-color", SURFACE)
                chip.set_property("border-color", LINE)
                chip.set_property("color", TXT_DIM)
                chip.set_property("hover-background-color", SURFACE_2)
            chip.mark_dirty()

        chip_id, name, desc, accent = PIPELINE[index]
        stage_name.text = name
        stage_num.text = f"{index + 1} / {len(PIPELINE)}"
        stage_desc.text = desc
        stage_panel.set_property("border-color", accent)
        stage_name.mark_dirty()
        stage_num.mark_dirty()
        stage_desc.mark_dirty()
        stage_panel.mark_dirty()

    def make_stage_handler(index):
        def on_chip(container):
            select_stage(index)
            console.log(f"[pipeline] stage → {PIPELINE[index][1]}")

        return on_chip

    for i, (chip_id, _, _, _) in enumerate(PIPELINE):
        chips[chip_id].click.append(make_stage_handler(i))

    select_stage(0)

    # ── 02 · Layout grid — log hits to the console panel ─────────────
    for cell_key in ("cell_a", "cell_b", "cell_c", "cell_d", "cell_e", "cell_f", "cell_g", "cell_h"):
        cell = getattr(root, cell_key)

        def make_cell_handler(name):
            def on_cell(container):
                console.log(f"[grid] {name} clicked — GPU hit detection found it")

            return on_cell

        cell.click.append(make_cell_handler(cell_key))

    # ── 03 · Interaction — buttons, toggle, stepper ───────────────────
    action_status = root.action_status
    session = {"renders": 0}

    def on_render(container):
        session["renders"] += 1
        n = session["renders"]
        action_status.text = f">> Render queued — {n} click{'s' if n != 1 else ''} this session (demo: watch this line + the N-panel console)."
        action_status.set_property("color", ACCENT_HI)
        action_status.mark_dirty()
        console.log(f"[buttons] render #{n} queued")

    def on_preview(container):
        action_status.text = ">> Preview started — this line and the N-panel console are the buttons' only real effect."
        action_status.set_property("color", ORANGE)
        action_status.mark_dirty()
        console.info("[buttons] preview started")

    root.btn_render.click.append(on_render)
    root.btn_preview.click.append(on_preview)

    # Toggle — a sliding clay switch. State is ours, not the engine's,
    # so it can be restored from storage on the next launch.
    switch_track = root.switch_track
    switch_knob = root.switch_knob
    toggle_state = root.toggle_state
    toggle = {"on": bool(_store.get("toggle.on", False))}

    def apply_toggle():
        if toggle["on"]:
            switch_track.set_property("background-color", ACCENT)
            switch_track.set_property("border-color", ACCENT)
            switch_knob.set_property("background-color", ACCENT_INK)
            switch_knob.set_property("margin-left", "22px")
            toggle_state.text = "ON"
        else:
            switch_track.set_property("background-color", SURFACE_2)
            switch_track.set_property("border-color", LINE_STRONG)
            switch_knob.set_property("background-color", TXT_DIM)
            switch_knob.set_property("margin-left", "0px")
            toggle_state.text = "OFF"
        switch_track.mark_dirty()
        switch_knob.mark_dirty()
        toggle_state.mark_dirty()

    def on_toggle(container):
        toggle["on"] = not toggle["on"]
        _store.set("toggle.on", toggle["on"])
        apply_toggle()
        console.log(f"[toggle] wireframe overlay → {'ON' if toggle['on'] else 'OFF'}")

    switch_track.click.append(on_toggle)
    apply_toggle()

    # Stepper — value persists across restarts via puree.storage.
    step_value = root.step_value
    stepper = {"value": int(_store.get("stepper.value", STEP_DEFAULT))}

    def apply_stepper():
        step_value.text = str(stepper["value"])
        step_value.mark_dirty()

    def bump(delta):
        stepper["value"] = max(STEP_MIN, min(STEP_MAX, stepper["value"] + delta))
        _store.set("stepper.value", stepper["value"])
        apply_stepper()

    root.step_minus.click.append(lambda c: bump(-1))
    root.step_plus.click.append(lambda c: bump(+1))
    apply_stepper()

    # ── 06 · Live data — clock, input, greeting ───────────────────────
    clock_chip = root.clock_chip
    greet_line = root.greet_line
    greet_input = root.greet_input

    def _clear_input(container_id):
        """Empty the <INPUT> field (private registry — see _read_input_text)."""
        try:
            from puree import text_input_op

            for inst in text_input_op._text_input_instances:
                if inst.container_id == container_id:
                    inst.text = ""
                    inst.cursor_pos = 0
        except Exception:
            pass

    # Reset — puts every demo back to its first-run state.
    def on_reset(container):
        session["renders"] = 0
        toggle["on"] = False
        stepper["value"] = STEP_DEFAULT
        _store.set("toggle.on", False)
        _store.set("stepper.value", STEP_DEFAULT)
        apply_toggle()
        apply_stepper()
        select_stage(0)
        _store.set("card.pos", None)
        center_card()
        _clear_input(greet_input.id)
        greet_line.text = "Hello, world."
        greet_line.mark_dirty()
        action_status.text = "Demo state reset — stored values cleared too."
        action_status.set_property("color", TXT_MUTE)
        action_status.mark_dirty()
        console.warn("[reset] demo state cleared")

    root.btn_reset.click.append(on_reset)

    def tick():
        if _is_stale(root):
            clear(clock_timer)  # previous run's timer — retire it
            return
        clock_chip.text = time.strftime("%H:%M:%S")
        clock_chip.mark_dirty()

    clock_chip.text = time.strftime("%H:%M:%S")  # first paint, then tick every second
    clock_timer = set_interval(tick, 1000)

    def greet(container=None):
        name = _read_input_text(greet_input.id) or "world"
        greet_line.text = f"Hello, {name}."
        greet_line.mark_dirty()
        console.log(f"[greet] hello, {name}")

    def greet_key():
        if _is_stale(root):
            try:
                keys.unbind(greet_binding)  # previous run's binding — retire it
            except Exception:
                pass
            return
        greet(None)

    root.greet_btn.click.append(greet)
    try:
        greet_binding = keys.bind("ENTER", greet_key, when="input_focused")
    except Exception:
        greet_binding = None  # shortcut is sugar — the Greet button always works

    console.log("[helloworld] hello, world — page compiled, scripts wired")
    return app
