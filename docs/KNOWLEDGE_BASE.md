# Puree — Project Knowledge Base

> This file captures institutional knowledge, architectural decisions, lessons learned,
> and patterns that are hard for AI models to infer from code alone.
> Reference it when working on Puree to avoid repeating past mistakes.

## Architecture Decisions

### Why YAML + SCSS + Python (not HTML/CSS/JS)?

YAML was chosen because Blender's ecosystem is Python-native. YAML is easy to parse, human-readable, and avoids the complexity of an HTML parser. SCSS provides familiar CSS syntax with variables/mixins, compiled via the `grass` Rust crate. Python is the only language Blender scripting supports.

### Why GPU rendering (not Blender's native UI)?

Blender's built-in UI system (bpy.types.UILayout) is extremely limited — no custom colors, no animation, no flexible layout. Puree bypasses it entirely by drawing the container tree itself: all containers render in a single batched draw call through Blender's native `gpu` module, using an SDF (signed distance field) fragment shader in a `POST_PIXEL` draw handler. An earlier ModernGL compute-shader pipeline has been replaced by this native path, which makes rendering backend-agnostic (OpenGL/Vulkan/Metal).

### Why Taffy/Stretchable for layout?

A proper flexbox/grid layout engine is needed for CSS-like layout. Taffy is a Rust implementation that's fast and correct. It's compiled to a Python-accessible binary via PyO3 (the `stretchable` package).

### Why Rust for native bindings?

Hit detection and SCSS compilation are performance-critical. Rust gives native speed with memory safety. The `puree_core` Rust crate is compiled per-platform and shipped as a prebuilt binary (`.pyd` on Windows, `.so` on Linux/macOS) under `puree/native_binaries/<platform>/` — one folder per manifest platform, because Linux and macOS share the `.so` suffix. `native_bindings.py` loads the folder matching the running platform.

## Rendering Pipeline — Critical Details

### Buffer Stride

The single most fragile part of the system. Every container is packed into a flat array of floats (`CONTAINER_STRIDE = 68` floats = 17 RGBA texels per container), uploaded to the GPU as an RGBA32F data texture. The fragment shader (`container_draw.frag`) unpacks at fixed texel offsets. **If the Python packing order doesn't match the GLSL unpacking order, containers render incorrectly or not at all.** There are no runtime checks for this mismatch.

### Color Space

Blender's viewport works in **linear color space**. All CSS colors (specified in sRGB in SCSS) must be converted to linear before GPU upload. This conversion happens in the Rust `ColorProcessor`. If you see colors that look "washed out" or "too dark," check the sRGB↔linear conversion.

### Coordinate System

Origin is **top-left**, Y increases **downward** (screen-space convention, matching CSS). This is opposite to OpenGL's default (bottom-left, Y up). Taffy also outputs top-left Y-down coordinates.

### GPU Context & State

Puree does NOT create its own graphics context. All drawing goes through Blender's `gpu` module inside draw handlers, so it shares Blender's context and state machine. This means:
- Draw handlers must save/restore GPU state they touch (blend mode, depth test, scissor)
- Shader compilation happens on Blender's draw thread via `gpu.shader.create_from_info`
- A vestigial ModernGL context is still initialized when available (legacy compute path), but its failure is tolerated and nothing rendered on screen depends on it

## Parser — How YAML Becomes Containers

1. YAML is loaded and validated for structure
2. Theme config extracted (fonts, styles, scripts, components)
3. Component `data: '[name]'` references are resolved — template YAML loaded and merged
4. Parameters `"{{name, 'default'}}"` are substituted
5. Each YAML node becomes a `Container` object with an `id` (the node name)
6. Container tree built with parent-child relationships
7. SCSS compiled via `grass` (Rust SCSSCompiler)
8. CSS cascade applied — class selectors matched to containers
9. Style properties resolved per container (specificity + inheritance)
10. Taffy layout computed (flexbox/grid positions)
11. Container data flattened to JSON for GPU upload

### Class vs Style

Both `style:` and `class:` work in YAML. `style:` assigns a single class name (matched as `.classname` in SCSS). `class:` accepts space-separated multiple classes. Both are commonly used in examples.

### Component Namespacing

When `my_card: data: '[card]'` is processed, ALL children of the card component get prefixed: `card_header` becomes `my_card_card_header`. This prevents ID collisions but means Python access must use the full namespaced path.

## Event System — How Clicks Work

1. Blender's window manager dispatches events to modal operators
2. `hit_op.py` runs as a modal operator, receiving ALL events
3. On MOUSEMOVE/LEFTMOUSE, it calls `HitDetector.detect()` (Rust)
4. HitDetector reads the container position buffer to find which container the mouse is over
5. `InputRouter` decides if Puree should consume the event or pass it to Blender
6. If consumed: container's `hover`/`click`/`hoverout`/`toggle` callback lists are invoked
7. Each callback receives `fn(container)` — the container that was interacted with

### Event Consumption Rule

Puree only consumes events when the mouse is over a Puree container. This allows Blender's normal UI (menu, viewport, etc.) to work when the mouse is outside the panel.

## Hot Reload — How It Works and Breaks

### File Watcher (SCSS/YAML changes)

- `PyFileWatcher` (Rust) polls watched directories every ~300ms
- On file change: full reparse + recompile + relayout + re-render
- **Known fragility**: Rapid saves (e.g., save-all in editor) can trigger multiple reloads before the first finishes, tearing down GPU resources mid-frame and causing crashes.
- **SCSS cache**: Uses file mtime for invalidation. `git checkout` doesn't always update mtime, so cached SCSS may be stale after branch switches.

### Dev Reload Server (Python code changes)

For Python code changes (which need a full module purge + re-register), Puree has a built-in TCP reload server:

1. **ReloadServer** (`puree/reload_server.py`) — listens on `127.0.0.1:19746`, accepts `reload`, `ping`, `log_path`, and `logs [N]` commands
2. **Auto-starts** with the addon — no manual activation needed. Starts in `__init__.py register()`, stops in `unregister()`.
3. **Triggered by** `just reload` / `make reload` / `puree reload` → runs `tools/dev_reload.py` (or CLI equivalent)
4. **Reload flow**: Stop server → unregister addon → purge all `puree.*` modules from `sys.modules` → clear `__pycache__` → re-import + re-register (fresh server starts)
5. **Sentinel fallback**: If TCP isn't reachable, `dev_reload.py` writes `.puree_reload` file. A Blender timer (`_check_reload_sentinel`, 2s interval) picks it up.
6. **Thread-safe**: Server runs in a daemon thread; reload is scheduled via `bpy.app.timers.register()` on Blender's main thread.

## Transitions — What Animates and What Doesn't

Only 3 properties can be animated via CSS transitions:
- `background-color`
- `border-color`
- `opacity`

`color` (text color) is supported in `:hover`/`:active` rules but changes **instantly** — it is not transition-interpolated.

This is a deliberate limitation — layout properties (width, height, padding, margin) are computed by Taffy, and re-running Taffy every frame would be too expensive. The transition manager interpolates these 3 properties between states using named easing functions (ease, linear, ease-in, ease-out, ease-in-out). Custom `cubic-bezier()` curves are NOT supported.

## Media Pipeline (GIF / SVG / Video / Lottie)

Media is `puree/media/` (manager, per-format sources, MediaClock, controller) feeding the
existing image overlay pass: playback = swapping `ImageInstance.texture` per tick. No layout
work, no container data-texture rebuild, ever. Decoders: Rust `decode_gif`/`rasterize_svg` in
`puree_core` (built in), PyAV (`av` wheel) for video, `rlottie-python` for Lottie — the Python
two **ship bundled with Puree core** (in Puree's own manifest/dependency tree since 2026-07-20);
the lazy-import degrade stays as a safety net: a missing package ⇒ `ready_state 'unsupported'`,
poster/blank, one logged warning, never a crash (in a normal install that warning means a
broken/unrefreshed Puree extension). Asset keys are full filenames with extension,
posix-relative to `assets/` (`icons/play.svg`).

### Overlay pass (containers above images/video)

Needed so the injected controls bar draws on top of the video frame. Design deliberately avoids
the fragile 68-float stride: `render.py` packs **two data textures with the same packing code**
— main (non-overlay) and overlay containers — and binds the same shader to each in two handlers.
Zero GLSL changes. Key facts:

- `overlay: true` is a **subtree flag** propagated at flatten time; the flat container list is
  never reordered — only the GPU packing filters by flag, so hit detection, scroll offsets,
  transitions and dirty-sync keep flat indexing untouched.
- **Handler order** (`POST_PIXEL` handlers fire in registration order): containers →
  images/video → **overlay containers** → text → text inputs. The image/text handlers
  self-register lazily on their first operator call; the overlay handler registers between them
  in `XWZ_OT_start_ui.execute`.
- **hoverIndex remap discovery**: the fragment shader compares `hoverIndex`/`clickIndex` against
  each quad's LOCAL index within its pass, so the packer builds flat→local index maps per pass
  and both draw calls translate the uniforms through them (other-pass containers get `-1`).
  Forgetting this makes hover highlight the wrong container in the other pass.
- Hit detection needed no change — the Rust detector reads the full flat container buffer
  (position-based, not draw-order-based).
- A UI with zero overlay containers takes the exact pre-overlay path (no second texture/batch).

### Media budgets & idle rule

- **Idle rule (non-negotiable)**: paused/ended/static media triggers zero redraws. The media tick
  returns "did any visible texture change" and that folds into `needs_redraw` — a 10 fps GIF
  redraws ~10×/s, a paused video 0×/s.
- **32 MB per-file budget**: GIFs at/under it pre-upload every frame as GPUTextures (playback =
  pure swaps); over it they keep CPU frames + a 2-texture upload-on-demand ring. Lottie applies
  the same rule at the element's current raster size with a progressive per-element cache (first
  loop renders, later loops swap). Video always streams: decoder thread → bounded queue (6
  frames, drop-oldest) → 3-texture ring on the main thread.
- One decoder thread per **playing** video only; pause parks it and after ~2 s grace it exits
  (play restarts it at the clock position). `MediaManager.shutdown()` joins all threads and stops
  audio — wired into UI stop/restart, unregister and hot reload, so nothing leaks.
- SVG is static: rasterized once at content-box size, re-rasterized only after the box changes
  > 1 px and settles for ~150 ms (drag-resize churn is free).
- rlottie facts (hard-won): buffers are BGRA, premultiplied, top-down (engine swizzles + flips);
  its frame count is inclusive (`op - ip + 1`), so `duration = frames/fps` reads one frame-time
  longer than the authoring tool. Some AE features are outside rlottie's coverage — test exports;
  ThorVG is the recorded future upgrade path.
- Audio (video) rides Blender's built-in `aud`: one shared device per session, one handle per
  playing video; when unmuted at rate 1.0 **audio is the master clock** (video resyncs when drift
  > 80 ms); muted/rate≠1/no-track falls back to the monotonic clock. `playback_rate != 1.0`
  force-mutes audio (v1 decision).

### Fullscreen (region "theater mode")

Fullscreen is a **renderer short-circuit, not a document mutation**: while active, the draw
passes skip the normal document and render only a black backdrop plus the fullscreen subtree —
the main tree, its layout nodes and data textures stay resident and untouched, so exit is
instant and byte-exact. The subtree is **re-laid-out in a private Taffy pass** pinned to the
region box (crisp text, correctly stretched seek bar, valid hit rects — never a geometric scale
of the old layout), rebuilt on region resize/dirty-sync; hit detection is hot-swapped to the
subtree rects and ESC is bound for the mode's lifetime. Any container can enter
(`container.request_fullscreen()`); one element at a time; hot reload/reparse/UI stop
**force-exit by design** (wired with the `MediaManager.shutdown()` + `unwire_video_controls()`
teardown trio); controls seek math reads `fullscreen_manager.box_abs(track_id)` while active
because the main-tree box is stale inside the mode.

## Built-in Modules

Puree ships 11 built-in modules (all implemented, see API.md for full reference):

| Module | Purpose |
|--------|--------|
| `puree.storage` | JSON persistence (`Storage` class, global/project scope, auto-save) |
| `puree.timers` | `set_interval()`, `set_timeout()`, `clear()` with auto-cleanup |
| `puree.net` | HTTP client (`http.get/post`) + SSE streaming (`sse.connect`) |
| `puree.focus` | Focus management, `focus()`, `blur()`, Tab/Shift+Tab navigation |
| `puree.keyboard` | Keyboard shortcuts (`keys.bind("CTRL+N", fn)`, zero-arg callbacks), global & container-scoped |
| `puree.dynamic` | Dynamic container creation/removal (exposed via Container methods) |
| `puree.markdown` | Markdown rendering into child containers |
| `puree.virtual_scroll` | Virtual scrolling for large lists |
| `puree.collapse` | Instant collapse/expand for disclosure sections (not animated) |
| `puree.console` | Browser-style `console.log/warn/error/info` — auto-injected into user scripts, shown in the debug panel's Console tab |
| `puree.media` | GIF/SVG/video/Lottie playback — `MediaManager` singleton, per-format sources, `container.media` controller (play/pause/seek + events), default video controls wiring |

## Patterns That Work

### Show/Hide Elements
```python
panel.style.display = 'NONE'   # hide (uppercase!)
panel.mark_dirty()
panel.style.display = 'FLEX'   # show
panel.mark_dirty()
```

### Dynamic Row Collapse
```python
# Just height: 0 leaves a visible "capsule" — must also clear padding/border
row.style.height = 0
row.style.padding_top = 0
row.style.padding_bottom = 0
row.style.border_width_top = 0
row.style.border_width_bottom = 0
row.mark_dirty()
```

### Async Work in Handlers
```python
def on_click(container):
    def _work():
        result = expensive_operation()
        label.text = str(result)
        label.mark_dirty()
    threading.Thread(target=_work).start()
```

### Deferred bpy Calls from Threads
```python
import bpy
def deferred():
    bpy.ops.some.operator()
    return None  # None = don't repeat
bpy.app.timers.register(deferred)
```

### Dynamic Container Creation
```python
# Add child from component template
new_msg = parent.add_child("[msg_slot]", id="msg_42", params={"text": "Hello"})
new_msg.mark_dirty()

# Remove a child
parent.remove_child("msg_42")
parent.mark_dirty()

# Clear all children
parent.clear_children()
parent.mark_dirty()
```

### HTTP Requests (Main-Thread Safe)
```python
from puree.net import http, sse

http.get("https://api.example.com/data",
    on_success=lambda resp: update_ui(resp.json()),
    on_error=lambda err: show_error(str(err)))

# SSE streaming
stream = sse.connect(url, method="POST", json=payload,
    on_chunk=lambda event: append_text(event.data),
    on_done=lambda: finalize())
stream.cancel()  # cancel in-flight stream
```

### Managed Timers
```python
from puree.timers import set_interval, set_timeout, clear

handle = set_interval(poll_fn, 5000)   # every 5 seconds
clear(handle)                          # cancel
```

### Keyboard Shortcuts
```python
from puree.keyboard import keys
keys.bind("ENTER", on_send, when="input_focused")
keys.bind("CTRL+N", new_item)
input_field.keys.bind("SHIFT+ENTER", insert_newline)
```

### Markdown Rendering
```python
container.set_markdown("# Title\n\nSome **bold** text and `code`.")
```

### Collapse / Expand
```python
details.toggle_collapse()
details.mark_dirty()
```

## Patterns That Don't Work

| Pattern | Why It Fails |
|---------|-------------|
| `element:hover { width: 120px; }` | Layout properties in hover states are silently ignored |
| `calc(100% - 20px)` | `calc()` IS supported with `+` and `-` operators. Note: `%` inside `calc()` resolves to pixels based on viewport, not parent. `clamp()`, `min()`, `max()` are NOT supported. |
| `font-family: "MyFont"` in CSS | Font selection only works via YAML `font:` attribute |
| `transform: scale(1.1)` | No transform support — only layout + color changes |
| `my-button:` in YAML | Hyphens break the parser — use `my_button:` |
| `modal.style.display = 'flex'` | Runtime display values must be UPPERCASE: `'FLEX'` |
| Nested scroll containers | Only one scroll container per viewport |
| `border-left-color: red` | Per-side border colors not supported — use uniform `border-color` |
| `transition-timing-function: cubic-bezier(...)` | Custom cubic-bezier not implemented — only named functions |
| `text-align: justify` | Only `left`, `center`, `right` supported |
| `visibility: collapse` | Only `visible` and `hidden` supported |
| `img: my_icon` (extensionless) | **Breaking change (media groundwork, 2026-07)**: `img:` requires the full filename with extension — `img: my_icon.png` (subfolders under `assets/` allowed: `img: icons/x.png`). Extensionless values render nothing and log a one-time "did you mean" error. `font:` keeps its extensionless convention. Same rule for `video:`/`lottie:`. |
| `transform`/`filter` on a `video:` frame | Media frames are plain image quads — layout size/position, opacity, radius/border on the container apply; no transforms, no filters (same as everywhere else in Puree). |
| Unmuted autoplay + `playback_rate: 1.5` expecting audio | A rate ≠ 1.0 **force-mutes** video audio until the rate returns to 1.0 (v1 decision). The `muted` attribute is not flipped; the suppression is logged once. |
| `controls: true` on `lottie:`/`img:` nodes | Controls are a `<video>` feature — injection only happens for `video:` nodes; elsewhere the flag is ignored (debug log). Don't nest another media node inside the injected bar either. |
| `lottie:` pointing at a non-Bodymovin `.json` | Validated on open (`v`/`fr`/`w`/`h`/`layers` keys required) — config JSONs render nothing with one warning per file. `.lottie` zip containers are not supported (v1). |
| SPACE to toggle video in a UI with no text input | Key dispatch runs inside the text-input keyboard modal — container-scoped SPACE only works when the UI contains ≥ 1 text input (pre-existing engine constraint). |
| Comma-grouped selectors in **component** SCSS | The namespacer re-dots only the first selector of a group — `.a, .b {}` leaves `.b` dead. One block per class (share via `@mixin`). |
| `display: none` in SCSS for a node you'll show later | A node *created* display:none bakes `Display.NONE` into Taffy and never gets a layout box. Create it visible and hide at runtime (`style.display = 'NONE'`), like the controls icon wraps do. |
| Hot-**adding** a media node / `controls: true` via YAML hot reload | New containers appear but their image/text GPU instances don't exist until UI restart — hot reload only updates existing instances. Attribute edits on existing media nodes reload fine. |

## Debugging Cheat Sheet

| Problem | Check |
|---------|-------|
| Blank panel | Is `_try_start_ui()` called? Check `just logs` or `just tail` for errors. |
| Wrong colors | sRGB→linear conversion. Check if color is doubled or missing. |
| Container at wrong position | Data-texture stride mismatch between Python packing and GLSL unpacking. |
| Hover on wrong element | Hit detection cache stale after resize. |
| Text not showing | `extract_text.py` — is the text node being found? Font file exists? |
| Hot reload crash | GPU resources torn down mid-reload (rapid saves). Restart Blender. |
| CSS not applying | Specificity issue — more specific rule in cascade wins. |
| Transition jerky | Wrong start value in transition manager. |
| Component children inaccessible | Use namespaced path: `instance_child_name` |
| `mark_dirty()` not updating | Is the container actually in the active tree? |
| Dynamic child not appearing | Did you call `mark_dirty()` on the parent after `add_child()`? |
| Markdown not rendering | Container needs to support dynamic children; ensure `clear_children()` works |
| Keyboard shortcut not firing | Is the container focused? Check `when` parameter |
| Timer leaking on reload | Use `puree.timers` instead of raw `bpy.app.timers` — auto-cleanup |
| HTTP callback not running | Is the HTTP drain timer registered? Check `just logs` |
| Virtual scroll empty | Did you call both `set_virtual_data()` and `set_item_renderer()`? |
| Collapse not working | Ensure first child acts as header; call `mark_dirty()` after toggle (collapse is instant by design) |
| Video shows only its poster (or nothing) | PyAV (`av`) unavailable even though it ships bundled with Puree (`media.ready_state == 'unsupported'`, one warning in `just logs`) — a broken/unrefreshed Puree install: refresh/reinstall the extension (Preferences → Extensions) or restart Blender. Or `preload: none` without `autoplay` — nothing decodes until `play()`/`seek()`. |
| Lottie element inert/blank | `rlottie-python` unavailable despite shipping bundled with Puree (one session warning — refresh/reinstall the Puree extension or restart Blender), or the `.json` isn't a Bodymovin document (one warning per file naming it). |
| Media not animating | Paused/ended media idles **by design** (zero redraws) — check `container.media.paused`/`.ended`. Also: video/lottie default `autoplay` differs (false vs true), and offscreen media keeps its clock running without decoding. |
| Controls bar invisible | `controls: true` missing on the `video:` node? Bar hot-ADDED via YAML reload (needs UI restart)? Icons blank ⇒ the six `media_*.svg` assets aren't in the addon's `assets/`. Bar renders in the overlay pass — if other overlay content also vanished, check `just logs` for overlay-pass errors. |
| Fullscreen exits unexpectedly | A reparse/hot reload (any YAML/SCSS save) or UI stop **force-exits fullscreen by design** — the private pass is rebuilt from the parsed tree, so a fresh parse can't stay in the mode. Re-enter via `container.request_fullscreen()` (an `on_fullscreen_change` handler received the `False` event). ESC needs ≥ 1 text input in the UI (key-dispatch constraint) — the controls button and the API always work. |

## Version History Context

- Puree targets Blender 5.1+ (the minimum version enforced in `blender_manifest.toml` and `__init__.py`)
- The extension format uses `blender_manifest.toml` (Blender's new extension system)
- Python target: 3.11+ for the CLI; wheels ship for Blender's bundled Python (3.13)
- Rust edition: 2021

## Development Workflow

For UI work (fast iteration):
```bash
just link             # One-time: symlink source into Blender extensions
just reload           # After changes: reload in running Blender (TCP server)
just tail             # Live-follow the Puree log file
just logs             # Print last 50 lines of the log (just logs 100 for more)
just clear-logs       # Delete all log files
just deploy           # Shortcut: link + reload
```

For addon development (using puree CLI):
```bash
puree link            # One-time: symlink addon into Blender extensions
puree reload          # After changes: reload in running Blender (TCP server)
puree unlink          # Remove the development symlink
```

For engine work (requires rebuild):
```bash
just build_core       # After Rust changes
just build_package    # Rebuild the puree_ui wheel
just refresh <folder> # Push fresh wheel into a target addon project
just reload           # Reload in running Blender
```

For CLI testing:
```bash
just venv             # Create venv + install CLI in editable mode
source .venv/bin/activate
puree --version
```

For hot reload during UI development: Just save the file. `PyFileWatcher` detects changes and triggers reparse/rerender automatically.

## CLI Tool

Puree ships a CLI tool (`puree`) for end users, installed via `pip install puree-ui`:

```bash
puree init            # Scaffold a new project (YAML, SCSS, script.py, manifest)
puree build           # Build extension zip using Blender on PATH
puree install         # Install built extension into Blender
puree link            # Symlink project into Blender for development
puree unlink          # Remove the development symlink
puree reload          # Reload addon in running Blender (via TCP reload server)
```

The CLI lives in `puree/cli.py` and is exposed via `[project.scripts]` in `pyproject.toml`.

## Reload Server Security

Puree includes a built-in TCP reload server (`puree/reload_server.py`) for development use:

- **Binds to `127.0.0.1:19746`** — loopback only, not accessible from other machines on the network
- **No authentication** — any local process can send `reload`, `ping`, `log_path`, or `logs [N]` commands
- **Development-only** — the server is intended for the dev workflow (`puree reload`, `just reload`). It auto-starts when the addon registers and auto-stops on unregister.
- **Production addons**: If you are shipping an addon to end users, the reload server still starts automatically. This is harmless on loopback but unnecessary. To disable it, remove the `ReloadServer` start/stop calls from your addon's `register()`/`unregister()` functions.
- **No remote code execution** — the `reload` command triggers a pre-defined internal reload sequence, not arbitrary code. The server does not accept or evaluate arbitrary Python.
- **Sentinel fallback** — if TCP is unavailable, the CLI writes a `.puree_reload` sentinel file. A Blender timer picks it up on the main thread.
