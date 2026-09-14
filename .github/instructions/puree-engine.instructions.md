---
description: "Use when editing Puree engine Python files (parser, compiler, render, operators). Covers module responsibilities, registration patterns, ModernGL usage, and Blender operator conventions."
applyTo: "puree/*.py"
---

# Puree Engine — Python Conventions

These files are the Puree framework engine. They run inside Blender's Python environment.

## Module Responsibilities

| File | Does | Never Do |
|------|------|----------|
| `parser.py` | Parse YAML, build Container tree, apply CSS cascade | Render anything, handle events |
| `parser_op.py` | Sync dirty containers, flatten node tree for GPU | Parse YAML, render |
| `compiler.py` | Execute user `script.py` files | Parse YAML, modify styles |
| `render.py` | Pack GPU buffers, manage shaders, composite to viewport | Parse YAML, handle user events |
| `hit_op.py` | Detect which container is under mouse, fire callbacks | Render, parse, modify styles |
| `transition_manager.py` | Interpolate animatable properties over time | Any layout or event work |
| `hot_reload.py` | Watch files, trigger reparse on change | Render directly |
| `hot_reload_ops.py` | Blender operators for hot reload actions | File watching, rendering |
| `reload_server.py` | TCP server for `just reload` / `puree reload`, log access (`log_path`, `logs`) | Rendering, parsing, layout |
| `cli.py` | CLI tool (`puree init/build/install/link/unlink/reload`) | Blender API calls (runs outside Blender) |
| `native_bindings.py` | Wrap Rust FFI calls | Pure Python implementations of native functions |
| `media/` | Media decode + playback: `MediaManager`, per-format sources, `MediaClock`, `container.media` controller, default-controls wiring | Layout work, container data-texture rebuilds |

## Media Subsystem (`puree/media/`)

One subsystem owns decode → clock → GPU upload; rendering stays in the existing image overlay
pass — playback only swaps `ImageInstance.texture`. The `media_manager` singleton is reconciled
by `attach(image_blocks, instances)` after render creates the image instances (and on hot
reload), ticked from the render modal's TIMER (`tick()` returns "any texture changed", folded
into `needs_redraw` — paused/ended media costs zero redraws), and torn down by `shutdown()` on UI
stop/restart/unregister (joins video decoder threads, stops `aud` audio). Sources are duck-typed
per format under `decoders/` — adding a format = one source module + one `SOURCE_FACTORIES`
entry (the asset scan, `is_media_name()` and dispatch all derive from the registry). GIF/SVG
decode in the Rust core; video (PyAV) and Lottie (rlottie-python) ship bundled with Puree but
stay lazy-imported as a safety net, degrading to `ready_state 'unsupported'` + one warning. Rules: only the main thread touches `gpu`
(uploads go through `puree.media.upload.upload_texture`), `bpy`/`gpu` imports live inside
functions so the package imports cleanly outside Blender, and frames are premultiplied RGBA
flipped bottom-up.

## Blender Operator Patterns

All operators inherit `bpy.types.Operator`:
```python
class XWZ_OT_my_operator(bpy.types.Operator):
    bl_idname = "xwz.my_operator"
    bl_label = "My Operator"
    
    def execute(self, context):
        # one-shot
        return {'FINISHED'}
    
    def modal(self, context, event):
        # continuous (hit_op, mouse_op, scroll_op)
        return {'RUNNING_MODAL'}  # or {'FINISHED'}, {'CANCELLED'}
    
    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
```

## Threading Rules

- **Blender API is NOT thread-safe** — never call `bpy.*` from a thread
- Use `bpy.app.timers.register(fn)` to defer bpy calls from threads
- `threading.Thread` is fine for I/O, network, computation
- Timer functions return `None` to run once, or a float (seconds) to repeat

## ModernGL Rules

- Context: `moderngl.create_context(require=430)` — attaches to Blender's existing GL context
- Never create a standalone context — Blender owns the GL state
- Buffer operations must use the correct stride and offset
- Shader compilation errors show in Blender's system console
- All textures shared with Blender must use compatible formats

## Property Changes

When modifying a container's properties at runtime:
```python
container.text = "new text"
container.mark_dirty()  # ALWAYS — triggers relayout + rerender
```

Without `mark_dirty()`, the GPU buffer isn't updated. This is the single most common bug.

## Logging

```python
from .log import get_logger
logger = get_logger(__name__)

logger.debug("detail message")
logger.info("status message")
logger.error("error message")
```

All output goes to `<addon_root>/logs/puree.log` (rotating, 5 MB, 3 backups).
Console is silent by default; set `PUREE_DEBUG=1` for stderr output.

To capture user script `print()` output into the log:
```python
from .log import capture_output
with capture_output("user"):
    module.main(self, app)
```

To get the current log file path at runtime:
```python
from .log import get_log_path
path = get_log_path()  # e.g. /home/user/.config/blender/5.1/.../logs/puree.log
```

The reload server also exposes log access via TCP:
- `log_path` command → returns the log file path
- `logs N` command → returns last N lines of the log

Dev commands: `just tail` (live follow), `just logs` (last 50 lines), `just clear-logs`.
