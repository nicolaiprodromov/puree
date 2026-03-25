---
name: perf
description: 'Profile and optimize Puree engine performance. Covers GPU rendering bottlenecks, layout computation, buffer packing, container count, and frame timing.'
user-invocable: true
argument-hint: 'Describe the performance issue (e.g. "rendering drops to 15fps with 200 containers", "layout takes 50ms on reload")'
---

Profile and fix performance bottlenecks in the Puree engine itself. This is for framework-level optimization, not user-level UI simplification (use the `optimize` skill for that).

## Procedure

### 1. Identify the Bottleneck Layer

Performance in Puree breaks down into:

| Phase | Typical Cost | Module |
|-------|-------------|--------|
| SCSS compilation | 5–50ms (cached: <1ms) | `native_bindings.SCSSCompiler` |
| YAML parsing | 5–20ms | `parser.py` |
| CSS cascade | 2–10ms | `native_bindings.SCSSCompiler` |
| Layout (Taffy) | 1–15ms | `stretchable` FFI |
| Script execution | 1–5ms | `compiler.py` |
| Buffer packing | 1–10ms (scales with containers) | `render.py` |
| GPU upload | <1ms | `render.py` (SSBO update) |
| Compute shader | <1ms–5ms (scales with pixels) | `shaders/container.glsl` |
| Text rendering | 2–20ms (scales with text count) | `text_op.py` |
| Image loading | 10–100ms per image (first load) | `img_op.py` |
| Hit detection | <1ms | `native_bindings.HitDetector` |

### 2. Measure

Add timing to the suspected bottleneck:

```python
import time
from puree.log import logger

start = time.perf_counter()
# ... operation ...
elapsed = (time.perf_counter() - start) * 1000
logger.info(f"[PERF] operation_name: {elapsed:.2f}ms")
```

For frame timing, check `render.py` — it may already have timing hooks.

### 3. Common Optimizations

**Buffer packing** (render.py):
- Pre-allocate buffers instead of rebuilding each frame
- Use `array` or `struct.pack_into` instead of Python list concatenation
- Batch buffer updates — only repack changed containers

**Layout** (parser.py / stretchable):
- Minimize container count — each node is a Taffy layout node
- Avoid deep nesting — Taffy's flexbox is O(n) but deep trees add overhead
- Cache layout results — only relayout on `mark_dirty()`

**SCSS compilation** (native_bindings):
- Already cached by mtime — ensure cache hits
- Minimize `@import` chains
- Use variables instead of repeated calculations

**Text rendering** (text_op.py):
- Text is the most expensive per-container operation
- Minimize text containers — use `passive: true` where possible
- Cache rendered text textures

**Shader** (container.glsl):
- Early-exit for `display: none` containers
- Skip transparent containers (opacity == 0)
- Minimize branching in the main loop

### 4. Verify

- Measure again after optimization — confirm improvement
- Test with increasing container counts (50, 100, 200, 500)
- Test hot reload speed
- Verify no visual regressions
