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
| `compiler.py` | Execute user `script.py` files | Parse YAML, modify styles |
| `render.py` | Pack GPU buffers, manage shaders, composite to viewport | Parse YAML, handle user events |
| `hit_op.py` | Detect which container is under mouse, fire callbacks | Render, parse, modify styles |
| `transition_manager.py` | Interpolate animatable properties over time | Any layout or event work |
| `hot_reload.py` | Watch files, trigger reparse on change | Render directly |
| `native_bindings.py` | Wrap Rust FFI calls | Pure Python implementations of native functions |

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
from puree.log import logger
logger.debug("detail message")
logger.info("status message")
logger.error("error message")
```

Output goes to Blender's system console (terminal on Linux/Mac, Window → Toggle System Console on Windows).
