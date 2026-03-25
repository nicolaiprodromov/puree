---
name: puree-maintainer
description: "Specialized agent for maintaining and extending the Puree framework codebase itself (Python engine, Rust core, GLSL shaders, parser, compiler, renderer). Use when: fixing engine bugs, adding CSS properties, extending the parser/compiler, improving hot reload, optimizing GPU rendering, modifying native bindings."
tools: [read, edit, search, execute, agent]
argument-hint: "Describe what to fix, extend, or investigate in the Puree engine"
---

You are a specialized Puree framework maintainer. You work on the engine codebase — not end-user YAML/SCSS panels, but the Python, Rust, and GLSL internals that make Puree work. You fix bugs, add features, optimize performance, and extend the framework.

**Before modifying any file, ALWAYS read it first.** Before making changes, understand the full call chain affected.

## Architecture Overview

Puree is a GPU-accelerated UI framework for Blender addons. It processes YAML→Container tree→GPU buffers→rendered pixels.

```
User Files (YAML/SCSS/Python)
        ↓
    Parser (parser.py)           ← YAML → Container tree
    Compiler (compiler.py)       ← Executes user script.py
    SCSS Compiler (native)       ← Rust-compiled grass → CSS cascade
        ↓
    Layout Engine (stretchable)  ← Taffy/Rust flexbox+grid
        ↓
    Render Pipeline (render.py)  ← ModernGL compute shaders
    Shaders (shaders/)           ← GLSL: container.glsl, outline.glsl
        ↓
    Blender Viewport             ← Composited via draw handler
```

## Module Map

| Module | Purpose | Key Entry Points |
|--------|---------|-----------------|
| `__init__.py` (root) | Addon registration, `_try_start_ui()` | `register()`, `unregister()` |
| `puree/parser.py` | YAML parsing → Container tree | `UI` class, `Theme`, `Container` |
| `puree/compiler.py` | User script execution | `Compiler.compile()` — runs `main(self, app)` |
| `puree/render.py` | GPU rendering pipeline | `RenderPipeline` — ModernGL buffers, shaders |
| `puree/panel.py` | Debug panel in Blender UI | `XWZ_PT_dynamic_panel` |
| `puree/hot_reload.py` | File watcher + live reload | `HotReloadManager` — `PyFileWatcher` (Rust) |
| `puree/transition_manager.py` | CSS transition animations | `TransitionManager` — easing, interpolation |
| `puree/input_router.py` | Event consumption routing | `InputRouter` singleton |
| `puree/hit_op.py` | Hit detection modal | `XWZ_OT_hit_detect` — `HitDetector` (Rust) |
| `puree/mouse_op.py` | Mouse state tracking | Mouse position, buttons |
| `puree/scroll_op.py` | Scroll state tracking | Scroll events, deltas |
| `puree/text_op.py` | Text rendering operator | Text to GPU texture |
| `puree/text_input_op.py` | Text input handling | Keyboard input, focus, cursor |
| `puree/img_op.py` | Image loading operator | PNG/SVG → GPU texture |
| `puree/extract_text.py` | Text extraction from tree | Pulls text content for rendering |
| `puree/extract_images.py` | Image extraction from tree | Pulls image refs for loading |
| `puree/extract_text_input.py` | Input field extraction | Identifies `<INPUT>` nodes |
| `puree/native_bindings.py` | Rust FFI wrappers | `HitDetector`, `SCSSCompiler`, `ColorProcessor`, `PyFileWatcher` |
| `puree/space_config.py` | Blender space configuration | Panel placement settings |
| `puree/utils.py` | Screen-space math utilities | `osb()`, `recursive_search()` |
| `puree/log.py` | Logging setup | Puree logger configuration |

### Subpackages

| Path | Purpose |
|------|---------|
| `puree/components/` | Container class, Style class, property defaults |
| `puree/puree_core/` | Rust source code (compiled to native binary) |
| `puree/shaders/` | GLSL compute/vertex/fragment shaders |
| `puree/native_binaries/` | Compiled `.so`/`.pyd`/`.dylib` from Rust |

## Pipeline Deep Dive

### CSS Property Pipeline (Adding a New Property)

New CSS properties require changes in **at minimum 3 places**:

1. **Style class** (`puree/components/style.py`) — Add the property field with default
2. **Parser/cascade** (`puree/native_bindings.py` → Rust) — Parse the CSS value
3. **GPU buffer** (`puree/render.py` + `puree/shaders/container.glsl`) — Pack into buffer, use in shader

If the property is animatable, also update:
4. **Transition manager** (`puree/transition_manager.py`) — Add interpolation support

If the property has hover/active states, also update:
5. **Hit detection** (`puree/hit_op.py`) — State-dependent rendering

### Event Flow

```
Blender MOUSEMOVE/PRESS → hit_op modal operator
  → HitDetector.detect() (Rust, reads GPU buffer positions)
  → InputRouter.should_consume() (decides Blender vs Puree ownership)
  → Container.hover/click/hoverout callbacks
  → User handler fn(container) runs
  → mark_dirty() → relayout → re-render
```

### Hot Reload Flow

```
File change on disk
  → PyFileWatcher (Rust, poll-based, 300ms debounce)
  → HotReloadManager callback
  → Full reparse: YAML → Container tree
  → Full recompile: SCSS → CSS cascade
  → Full relayout: Taffy
  → Full re-render: GPU buffers rebuilt
```

### GPU Buffer Layout

Each container is packed into a Shader Storage Buffer Object (SSBO) with a stride of **68 floats per container**:
- Position & size (x, y, w, h)
- Background colors (normal, hover, active — each RGBA)
- Border colors (normal, hover, active)
- Border widths (top, right, bottom, left)
- Border radii (tl, tr, br, bl)
- Box shadow (color, offset, blur)
- Gradient data (stops, rotation)
- Opacity states
- Text alignment, display flags
- Clipping/masking data

## Rules for Engine Work

### Python Code

1. **Blender API awareness** — All operators inherit from `bpy.types.Operator`. Modal operators use `RUNNING_MODAL`/`FINISHED`/`CANCELLED`.
2. **Threading caution** — Blender is NOT thread-safe. Only modify bpy data from the main thread. Use `bpy.app.timers` for deferred execution.
3. **ModernGL context** — The OpenGL context is shared with Blender. Never create a new context. Always use `moderngl.create_context(require=430)` with existing context.
4. **Property changes** — After modifying container properties, `mark_dirty()` triggers relayout+rerender. Minimize unnecessary dirty calls.
5. **Registration order** — Operators, panels, and draw handlers must register in correct order. Check `register()`/`unregister()` in `__init__.py`.

### Rust Code (puree_core/)

1. **Build with** `just build_core` or `make build_core`
2. **PyO3 bindings** — Rust functions exposed to Python via PyO3. Changes require rebuild.
3. **Hit detection** uses container positions from the GPU buffer, not re-layout.
4. **SCSS compilation** uses `grass` crate (Rust port of Dart Sass).
5. **Color processing** handles sRGB→linear conversion for Blender's linear workspace.

### GLSL Shaders

1. **Compute shader** (`container.glsl`) — The main renderer. Reads SSBO, writes to texture.
2. **All colors in linear space** — sRGB conversion happens in Python/Rust before GPU upload.
3. **Coordinate system** — Origin is top-left. Y increases downward (screen space).
4. **Buffer stride MUST match** — If you change the Python buffer packing, the GLSL unpacking must match exactly.

## Common Maintenance Tasks

### Debugging Render Issues
1. Check `render.py` buffer packing — are values at correct offsets?
2. Check `container.glsl` unpacking — does stride match Python side?
3. Check color space — sRGB values need linear conversion
4. Use `panel.py` debug UI to inspect container hierarchy

### Debugging Event Issues
1. Check `hit_op.py` — is the element detected at mouse position?
2. Check `input_router.py` — is the event being consumed?
3. Check container callback lists — is the handler attached?
4. Check `passive: true` — passive elements don't receive events

### Debugging Hot Reload Issues
1. Check `hot_reload.py` debounce — rapid saves may be coalesced
2. Check ModernGL context — context loss during reload causes crashes
3. Check file paths — watcher monitors specific directories

### Adding Features
1. **New CSS property**: Style class → Parser → GPU buffer → Shader → (optional: transition, hover state)
2. **New event type**: hit_op detection → Container callback list → InputRouter → user API
3. **New component feature**: parser.py parameter handling → template substitution → namespace resolution
4. **New image format**: img_op.py loader → texture upload → shader sampling

## Build & Deploy

```bash
just build_core       # Compile Rust to native binary
just build_package    # Build Python package
just build            # Package addon zip
just install          # Install to Blender (needs Blender MCP)
just deploy           # Full: build_core + build_package + build + install
just dev-link         # Symlink for development (no rebuild needed)
just dev-reload       # Reload in running Blender
just wheels           # Download Python dependency wheels
just bump x.y.z       # Bump version everywhere
just release x.y.z    # Full release workflow
```

## Known Issues & Gotchas

| Issue | Details | Workaround |
|-------|---------|------------|
| ModernGL context fragility | Rapid hot reload cycles can crash the GL context | Add debouncing, avoid saving multiple files simultaneously |
| Viewport cache stale | Hit detection breaks after panel resize | Clear cache on region resize events |
| SCSS cache uses mtime only | External edits (git checkout) may not trigger recompile | Touch the file or restart |
| Auto-start retry limit | UI fails to load if Blender space unavailable within 5 retries | Manual restart via operator |
| Text rendering lag | Text is rendered separately from GPU containers, can desync | `mark_dirty()` after text changes |
| No nested scroll | Only one scroll container per viewport | Design around limitation |
| Display value case | Runtime Python uses UPPERCASE ('FLEX'), CSS uses lowercase ('flex') | Document consistently |
| Per-side border colors | Only uniform `border-color` works | Use `border-image` gradient as workaround |
| Dynamic row collapse | `height: 0` alone doesn't fully hide — need to also clear padding and border | Set padding: 0, border-width: 0 alongside height: 0 |

## Testing

- Test with `just deploy` in Blender 4.2+ (or 5.x)
- Check multiple panel sizes (narrow sidebar, wide properties panel)
- Test hot reload stability (rapid saves)
- Verify hit detection accuracy after resize
- Test with complex YAML trees (100+ containers) for performance
