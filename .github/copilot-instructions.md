# Puree — Copilot Instructions

> These instructions are loaded into every Copilot conversation in this workspace.
> They provide the essential context for any AI working on Puree.

## What Is Puree

Puree is a **GPU-accelerated UI framework for Blender addons**. It lets developers build rich custom interfaces using YAML (structure), SCSS (styling), and Python (interactivity). It renders via ModernGL compute shaders inside Blender panels. Layout uses Taffy/Stretchable (a Rust flexbox/grid engine compiled to native binaries via PyO3).

**It is NOT a web framework.** Many CSS features don't exist. See "What Puree Doesn't Support" below.

## Repository Structure

```
puree/
├── puree/                    # ← THE ENGINE (Python + Rust + GLSL)
│   ├── parser.py             # YAML → Container tree
│   ├── parser_op.py          # Parser state sync operator
│   ├── compiler.py           # Executes user script.py
│   ├── render.py             # GPU rendering pipeline (ModernGL)
│   ├── transition_manager.py # CSS transition animations
│   ├── hit_op.py             # Hit detection modal operator
│   ├── input_router.py       # Event consumption routing
│   ├── hot_reload.py         # File watcher + live reload
│   ├── hot_reload_ops.py     # Hot reload Blender operators
│   ├── reload_server.py      # Built-in TCP server (127.0.0.1:19746) — reload, ping, logs
│   ├── cli.py                # CLI tool: puree init/build/install/link/unlink/reload
│   ├── native_bindings.py    # Rust FFI: HitDetector, SCSSCompiler, ColorProcessor
│   ├── text_op.py            # Text rendering operator
│   ├── text_input_op.py      # Text input handling operator
│   ├── img_op.py             # Image loading operator
│   ├── mouse_op.py           # Mouse state tracking operator
│   ├── scroll_op.py          # Scroll state tracking operator
│   ├── panel.py              # Blender debug panel
│   ├── components/           # Container class, Style class, defaults
│   ├── puree_core/           # Rust source (compiled → native_binaries/)
│   └── shaders/              # GLSL compute/vertex/fragment shaders
├── dist/                     # ← BUILD SCRIPTS & TOOLS
│   ├── dev_reload.py         # Triggers reload in running Blender
│   ├── build.sh / build.bat  # Platform build scripts
│   └── release.py            # Release automation
├── static/                   # ← BUILT-IN UI (example/default panel)
│   ├── index.yaml
│   ├── style.scss
│   ├── script.py
│   └── components/
├── examples/                 # ← EXAMPLE PANELS
├── docs/                     # ← DOCUMENTATION
│   ├── PUREE_SPEC.md         # Full framework specification
│   ├── PUREE_VS_CSS.md       # CSS compatibility reference
│   ├── API.md                # Python API reference
│   └── COMPONENTS.md         # Component system docs
├── assets/                   # Images (PNG, SVG)
├── fonts/                    # Font files (.ttf, .otf) — NeueMontreal family
├── __init__.py               # Blender addon entry point + reload server lifecycle
└── blender_manifest.toml     # Blender extension manifest
```

## Two Kinds of Work

### 1. UI Work (YAML/SCSS/Python panels)
**Agent**: `puree-coder`

Building or modifying end-user interfaces. Files in `static/`, `examples/`, or addon directories.

### 2. Engine Work (Python/Rust/GLSL internals)
**Agent**: `puree-maintainer`

Fixing bugs or extending the framework itself. Files in `puree/`, `puree/puree_core/`, `puree/shaders/`.

## Critical Rules — Always Remember

### YAML
- Node names: **underscores only** (`my_button` ✓ `my-button` ✗) — parser breaks on hyphens
- Component refs: `data: '[component_name]'` — square brackets required
- Parameters: `"{{param_name, 'default_value'}}"` — both quote types, comma required
- Font/image names omit extensions

### SCSS
- **Only 4 animatable properties**: `background-color`, `color`, `border-color`, `opacity`
- Layout properties in `:hover`/`:active` are **silently ignored** (no width/height/padding/margin changes on hover)
- Units: only `px` and `%` (no em, rem, vw, vh, fr, calc)
- Display: only `flex`, `grid`, `block`, `none` (no inline variants)
- Gradients: only `linear-gradient()` (no radial, conic)
- Selectors: no `::before`/`::after`, `nth-child`, `:not()`, attribute selectors
- `--` extension properties need `#{$var}` interpolation for SCSS variables
- Only `color`, `font-size`, `text-align` inherit from parents
- Font selection uses YAML `font:` attribute, not CSS `font-family`

### Python (script.py)
- Entry: `def main(self, app):` — must `return app`
- After ANY property change: call `mark_dirty()` — GPU won't update without it
- Runtime display values are UPPERCASE: `'FLEX'`, `'NONE'` (CSS uses lowercase)
- Event callbacks: `fn(container)` — all take one argument
- Component children are namespaced: `instance_child_name`
- Blender is NOT thread-safe — use `threading.Thread` for async, `bpy.app.timers` for deferred bpy calls

### Engine (for maintainers)
- New CSS properties require changes in ≥3 places: Style class → Rust parser → GPU buffer → GLSL shader
- Buffer stride in render.py MUST match GLSL unpacking offsets exactly
- All colors in GPU are linear space (sRGB→linear conversion in Python/Rust)
- ModernGL context is shared with Blender — never create a new one
- Rust code needs `just build_core` after changes

## What Puree Doesn't Support

`calc()` · `clamp()` · `min()` · `max()` · `em` · `rem` · `vw` · `vh` · `fr` · `::before` · `::after` · `@keyframes` · `animation` · `transform` · `rotate` · `scale` · `translate` · `float` · `clear` · `z-index` (CSS) · `inline` display · `position: fixed` · `position: sticky` · radial/conic gradients · multiple box-shadows · per-side border colors · `font-family` in CSS · `inherit` · `initial` · `unset` · `:nth-child` · `:not()` · attribute selectors · sibling combinators

## Build Commands

### For users (via `pip install puree-ui`):
```bash
puree init            # Initialize new project in current directory
puree build           # Build extension zip using Blender on PATH
puree install         # Install built extension into Blender
puree link            # Symlink project into Blender for development
puree unlink          # Remove the development symlink
puree reload          # Reload addon in running Blender (via TCP reload server)
```

### For developers (working on puree itself):
```bash
just build_core       # Compile Rust native binary
just build_package    # Build Python package
just build            # Build extension zip using Blender on PATH
just link             # Symlink source into Blender extensions (auto-installs deps)
just unlink           # Remove dev symlinks
just reload           # Reload addon in running Blender (via TCP reload server)
just tail             # Live-follow the Puree log file
just logs             # Print last 50 lines of the log (just logs 100 for more)
just clear-logs       # Delete all log files
just refresh <folder> # Refresh puree_ui wheel in a target project (fixes stale wheels)
just deploy           # Link + reload (quick dev cycle)
just install          # Install puree CLI locally for testing (creates .venv)
just venv             # Create venv and install CLI in editable mode
just install-deps     # Install wheel dependencies into Blender site-packages
just wheels           # Download Python dependency wheels
just bump x.y.z       # Version bump everywhere
just release x.y.z    # Full release workflow
```

> All `just` commands have `make` equivalents (`make deploy`, `make link`, etc.)

## Known Issues & Gotchas

| Issue | Detail |
|-------|--------|
| Dynamic row hide | `height: 0` alone doesn't fully hide — also clear padding and border-width |
| Hot reload + GL | Rapid saves can crash the ModernGL context |
| Reload server | TCP server on 127.0.0.1:19746 auto-starts with addon; commands: `reload`, `ping`, `log_path`, `logs [N]`; sentinel file `.puree_reload` is fallback |
| Hit detection stale | Panel resize can break hit detection — cache needs clearing |
| Display case mismatch | SCSS uses `none`/`flex`, Python runtime uses `NONE`/`FLEX` |
| Text rendering async | Text renders separately from GPU containers, can lag |
| SCSS cache | Uses mtime only — `git checkout` may not invalidate cache |

## Documentation

- [PUREE_SPEC.md](docs/PUREE_SPEC.md) — Complete framework specification
- [PUREE_VS_CSS.md](docs/PUREE_VS_CSS.md) — CSS compatibility and differences
- [API.md](docs/API.md) — Python API reference (Style properties, Container methods)
- [COMPONENTS.md](docs/COMPONENTS.md) — Component system documentation
- [CONTRIBUTING.md](docs/CONTRIBUTING.md) — Development setup and contribution guidelines
