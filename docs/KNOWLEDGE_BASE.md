# Puree — Project Knowledge Base

> This file captures institutional knowledge, architectural decisions, lessons learned,
> and patterns that are hard for AI models to infer from code alone.
> Reference it when working on Puree to avoid repeating past mistakes.

## Architecture Decisions

### Why YAML + SCSS + Python (not HTML/CSS/JS)?

YAML was chosen because Blender's ecosystem is Python-native. YAML is easy to parse, human-readable, and avoids the complexity of an HTML parser. SCSS provides familiar CSS syntax with variables/mixins, compiled via the `grass` Rust crate. Python is the only language Blender scripting supports.

### Why GPU rendering (not Blender's native UI)?

Blender's built-in UI system (bpy.types.UILayout) is extremely limited — no custom colors, no animation, no flexible layout. Puree bypasses it entirely by rendering to a GPU texture via ModernGL compute shaders, then compositing that texture into the Blender viewport via a draw handler.

### Why Taffy/Stretchable for layout?

A proper flexbox/grid layout engine is needed for CSS-like layout. Taffy is a Rust implementation that's fast and correct. It's compiled to a Python-accessible binary via PyO3 (the `stretchable` package).

### Why Rust for native bindings?

Hit detection and SCSS compilation are performance-critical. Rust gives native speed with memory safety. The `puree_core` Rust crate is compiled per-platform and shipped as `.so` / `.pyd` / `.dylib`.

## Rendering Pipeline — Critical Details

### Buffer Stride

The single most fragile part of the system. Every container is packed into a flat array of floats, sent to the GPU as an SSBO. The GLSL shader unpacks at fixed offsets. **If the Python buffer packing order doesn't match the GLSL unpacking order, containers render incorrectly or not at all.** There are no runtime checks for this mismatch.

### Color Space

Blender's viewport works in **linear color space**. All CSS colors (specified in sRGB in SCSS) must be converted to linear before GPU upload. This conversion happens in the Rust `ColorProcessor`. If you see colors that look "washed out" or "too dark," check the sRGB↔linear conversion.

### Coordinate System

Origin is **top-left**, Y increases **downward** (screen-space convention, matching CSS). This is opposite to OpenGL's default (bottom-left, Y up). Taffy also outputs top-left Y-down coordinates.

### ModernGL Shared Context

Puree does NOT create its own OpenGL context. It uses `moderngl.create_context(require=430)` which attaches to Blender's existing GL context. This means:
- We can't use features above GL 4.3 (Blender's guaranteed minimum)
- Context operations must be careful not to corrupt Blender's state
- Shader compilation happens in Blender's GL thread

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
- **Known fragility**: Rapid saves (e.g., save-all in editor) can trigger multiple reloads before the first finishes. The ModernGL context can be invalidated mid-reload, causing crashes.
- **SCSS cache**: Uses file mtime for invalidation. `git checkout` doesn't always update mtime, so cached SCSS may be stale after branch switches.

### Dev Reload Server (Python code changes)

For Python code changes (which need a full module purge + re-register), Puree has a built-in TCP reload server:

1. **ReloadServer** (`puree/reload_server.py`) — listens on `127.0.0.1:19746`, accepts `reload`, `ping`, `log_path`, and `logs [N]` commands
2. **Auto-starts** with the addon — no manual activation needed. Starts in `__init__.py register()`, stops in `unregister()`.
3. **Triggered by** `just reload` / `make reload` / `puree reload` → runs `dist/dev_reload.py` (or CLI equivalent)
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

## Built-in Modules

Puree ships 9 built-in modules (all implemented, see API.md for full reference):

| Module | Purpose |
|--------|--------|
| `puree.storage` | JSON persistence (`Storage` class, global/project scope, auto-save) |
| `puree.timers` | `set_interval()`, `set_timeout()`, `clear()` with auto-cleanup |
| `puree.net` | HTTP client (`http.get/post`) + SSE streaming (`sse.connect`) |
| `puree.focus` | Focus management, `focus()`, `blur()`, Tab/Shift+Tab navigation |
| `puree.keyboard` | Keyboard shortcuts (`keys.bind("CTRL+N", fn)`), global & container-scoped |
| `puree.dynamic` | Dynamic container creation/removal (exposed via Container methods) |
| `puree.markdown` | Markdown rendering into child containers |
| `puree.virtual_scroll` | Virtual scrolling for large lists |
| `puree.collapse` | Animated collapse/expand for disclosure sections |

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
| `calc(100% - 20px)` | `calc()` not supported — use fixed values or restructure layout |
| `font-family: "MyFont"` in CSS | Font selection only works via YAML `font:` attribute |
| `transform: scale(1.1)` | No transform support — only layout + color changes |
| `my-button:` in YAML | Hyphens break the parser — use `my_button:` |
| `modal.style.display = 'flex'` | Runtime display values must be UPPERCASE: `'FLEX'` |
| Nested scroll containers | Only one scroll container per viewport |
| `border-left-color: red` | Per-side border colors not supported — use uniform `border-color` |
| `transition-timing-function: cubic-bezier(...)` | Custom cubic-bezier not implemented — only named functions |
| `text-align: justify` | Only `left`, `center`, `right` supported |
| `visibility: collapse` | Only `visible` and `hidden` supported |

## Debugging Cheat Sheet

| Problem | Check |
|---------|-------|
| Blank panel | Is `_try_start_ui()` called? Check `just logs` or `just tail` for errors. |
| Wrong colors | sRGB→linear conversion. Check if color is doubled or missing. |
| Container at wrong position | Buffer stride mismatch between Python and GLSL. |
| Hover on wrong element | Hit detection cache stale after resize. |
| Text not showing | `extract_text.py` — is the text node being found? Font file exists? |
| Hot reload crash | ModernGL context invalidated. Restart Blender. |
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
| Collapse not animating | Ensure first child acts as header; call `mark_dirty()` after toggle |

## Version History Context

- Puree targets Blender 5.1+ (the minimum version enforced in `blender_manifest.toml` and `__init__.py`)
- The extension format uses `blender_manifest.toml` (Blender's new extension system)
- Python target: 3.10+ (matching Blender's bundled Python)
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
