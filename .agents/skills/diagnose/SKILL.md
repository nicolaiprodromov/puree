---
name: diagnose
description: 'Diagnose and fix bugs in the Puree engine (renderer, parser, layout, events, hot reload). Use when something is broken in the framework itself, not in user UI code.'
user-invocable: true
argument-hint: 'Describe the symptom (e.g. "containers disappear after resize", "hover events stop firing", "hot reload crashes")'
---

Systematically diagnose and fix bugs in the Puree engine. This is for framework-level issues, not user YAML/SCSS problems.

## Procedure

### 1. Classify the Symptom

Determine which subsystem is likely affected:

| Symptom | Likely Subsystem | Start Reading |
|---------|-----------------|---------------|
| Visual: nothing renders, wrong colors, missing elements | **Render pipeline** | `render.py`, `shaders/container.glsl` |
| Visual: wrong position, overlapping, clipped | **Layout engine** | `parser.py` (Taffy/stretchable calls) |
| Visual: text missing, wrong font, cut off | **Text system** | `text_op.py`, `extract_text.py` |
| Visual: images missing, wrong size | **Image system** | `img_op.py`, `extract_images.py` |
| Interactive: hover/click not working | **Event system** | `hit_op.py`, `input_router.py` |
| Interactive: scroll broken | **Scroll system** | `scroll_op.py`, `hit_op.py` |
| Interactive: text input broken | **Input system** | `text_input_op.py`, `extract_text_input.py` |
| Crash: on reload | **Hot reload** | `hot_reload.py`, `native_bindings.py` |
| Crash: on startup | **Registration** | `__init__.py`, `parser_op.py` |
| Crash: ModernGL error | **GL context** | `render.py` context creation |
| Performance: slow render | **GPU pipeline** | `render.py` buffer packing, `container.glsl` |
| Performance: slow layout | **Layout engine** | Container count, Taffy calls |
| Style: CSS not applying | **Cascade/parser** | `native_bindings.SCSSCompiler`, `parser.py` |
| Style: transitions broken | **Transitions** | `transition_manager.py` |

### 2. Trace the Data Flow

Read the relevant modules and trace the data from input to output:

**For render issues:**
```
parser.py (Container tree) → render.py (buffer packing) → container.glsl (unpacking + drawing)
```
Check: Are container values correct in Python? Are they packed at the right offsets? Does GLSL unpack at matching offsets?

**For event issues:**
```
mouse_op (position) → hit_op (detection) → input_router (consume?) → container callbacks
```
Check: Is the mouse position correct? Does hit detection find the right container? Is the event consumed?

**For style issues:**
```
SCSS file → SCSSCompiler (Rust/grass) → CSS rules → parser.py cascade application → Container.style fields
```
Check: Does the compiled CSS contain the rule? Is specificity correct? Is the property actually applied to the container?

**For layout issues:**
```
Container.style (dimensions) → stretchable/Taffy (layout compute) → Container.layout (final positions)
```
Check: Are style values correct before layout? Does Taffy produce expected results? Are final positions reasonable?

### 3. Add Diagnostic Output

When the bug isn't obvious from code reading:

```python
# Temporary debugging — add to the suspected module
from .log import get_logger
logger = get_logger(__name__)
logger.debug(f"Container {container.id}: pos=({container.layout.x}, {container.layout.y}), size=({container.layout.width}, {container.layout.height})")
logger.debug(f"Style: bg={container.style.background_color}, display={container.style.display}")
```

Output goes to `<addon_root>/logs/puree.log`. Use `just tail` to live-follow it, or `just logs` to see recent output.
Set `PUREE_DEBUG=1` environment variable to also echo to Blender's system console.

### 4. Fix and Verify

1. Make the minimal fix
2. Check if the fix affects other subsystems (buffer stride changes affect ALL rendering)
3. Test with `just link && just reload` for fast iteration
4. Test edge cases: empty tree, deep nesting, rapid hot reload, panel resize

### 5. Common Root Causes

| Bug Pattern | Common Cause |
|-------------|-------------|
| Containers render at wrong position | Buffer stride mismatch between Python and GLSL |
| Colors wrong | sRGB vs linear conversion missing or doubled |
| Hover works on wrong element | Hit detection using stale layout positions |
| Properties don't apply | CSS specificity — more specific rule overriding |
| Hot reload crashes | ModernGL context lost during reload cycle |
| Elements overlap | Taffy layout not accounting for border-box sizing |
| Transitions jerk/snap | Transition manager interpolating wrong start value |
| Text position wrong | `--text-x`/`--text-y` offsets not applied after layout |
| Scroll doesn't work | Overflow not set to `scroll`/`auto`, or nested scroll |
| Panel blank on startup | `_try_start_ui()` retry exhausted, space not ready |
