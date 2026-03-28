# PLAN-FEATURE.md — Puree CHANGES.md Implementation Plan

## Overview

9 features from `CHANGES.md` are being implemented in this plan. Features are ordered by
dependency (easiest/most independent first) and are each committed atomically.

**Codebase baseline research summary:**
- `stretchable.Node` supports `append()`, `insert()`, `remove()`, `clear()` → dynamic children are layout-feasible ✅
- `render.py:update_data_texture()` already recreates the GPU texture when container count changes → dynamic containers work without extra GPU code ✅
- `text_input_op.py:KeyboardHandler` already intercepts keyboard events — shortcuts can extend this ✅
- `parser_op.sync_dirty_containers()` already rebuilds the flat container list from the tree → dynamic add/remove just needs the tree updated ✅
- No new pip dependencies needed: `urllib.request` handles HTTP/SSE, everything else is pure Python ✅

---

## Implementation Order

| # | Feature | Priority in CHANGES.md | Effort | Depends On |
|---|---------|------------------------|--------|------------|
| 1 | JSON Persistence (`puree/storage.py`) | High | Low | — |
| 2 | Timer API (`puree/timers.py`) | Medium | Low | — |
| 3 | HTTP Client + SSE (`puree/net.py`) | Critical | Medium | Timer API |
| 4 | Focus Management (`puree/focus.py`) | Medium | Medium | — |
| 5 | Keyboard Shortcuts (`puree/keyboard.py`) | Medium | Low | Focus Management |
| 6 | Dynamic Containers (container.py, parser.py, new `puree/dynamic.py`) | Critical | High | — |
| 7 | Markdown Rendering (`puree/markdown.py`) | High | Medium | Dynamic Containers |
| 8 | Virtual Scrolling (`puree/virtual_scroll.py`) | High | High | Dynamic Containers |
| 9 | Collapse/Expand (container.py + parser_op.py) | Medium | Medium | Dynamic Containers |

---

## Feature Details

### 1. JSON Persistence — `puree/storage.py`

**Commit**: `feat(storage): add built-in JSON persistence module`

**API** (matching CHANGES.md exactly):
```python
from puree.storage import Storage
store = Storage("addon_name")
store.set("key", value)
store.get("key", default=None)
store.auto_save = True  # debounced 500ms write
store.save()
store.load()
project_store = Storage("addon_name", scope="project")
```

**Implementation**:
- File location:
  - Global: `~/.config/puree/{namespace}/data.json` (Linux/macOS via XDG), `%APPDATA%\puree\{namespace}\data.json` (Windows)
  - Project: `.blend` file directory (derived from `bpy.data.filepath`)
- Dot-notation key support: `"conversations.thread_1"` → nested dict path
- Atomic writes: write to `data.json.tmp`, then `os.replace()` (crash-safe)
- `auto_save`: schedules `bpy.app.timers.register(save, first_interval=0.5)`, idempotent (does not double-schedule)
- Thread-safe reads (writes always on main thread via timer)
- No new dependencies; uses only `json`, `os`, `pathlib`

**Files changed**: `puree/storage.py` (new), `puree/__init__.py` (export `Storage`)

---

### 2. Timer API — `puree/timers.py`

**Commit**: `feat(timers): add timer/interval API with auto-cleanup`

**API** (matching CHANGES.md exactly):
```python
from puree.timers import set_interval, set_timeout, clear
poll_handle = set_interval(fn, 5000)   # ms
timeout_handle = set_timeout(fn, 3000) # ms
clear(poll_handle)
```

**Implementation**:
- `TimerHandle` dataclass: `id: str`, `is_cancelled: bool`
- `_registry: dict[str, TimerHandle]` — all active handles
- `set_interval`: wraps a function so it reschedules itself (returns `interval_ms / 1000` from bpy timer) unless cancelled; registers with `bpy.app.timers.register()`
- `set_timeout`: registers with `first_interval=delay_ms/1000`, runs once
- `clear(handle)`: sets `handle.is_cancelled = True`; the wrapper returns `None` on next call (stops bpy timer)
- `_cleanup_all()`: iterates registry, cancels all — called during addon unregister and on hot reload
- Error handling: callback exceptions are caught and logged, timer continues

**Files changed**: `puree/timers.py` (new), `puree/__init__.py` (call `_cleanup_all()` on unregister)

---

### 3. HTTP Client + SSE — `puree/net.py`

**Commit**: `feat(net): add built-in HTTP client with SSE streaming`

**API** (matching CHANGES.md exactly):
```python
from puree.net import http, sse

http.get(url, headers=None, on_success=None, on_error=None, timeout=30)
http.post(url, json=None, data=None, headers=None, on_success=None, on_error=None, timeout=30)

stream = sse.connect(url, method="POST", json=None, headers=None,
                     on_chunk=None, on_done=None, on_error=None)
stream.cancel()
```

**Implementation**:
- `HttpResponse` dataclass: `.json()`, `.text`, `.status_code`, `.headers`
- `SSEEvent` dataclass: `.event`, `.data`, `.id`
- `SSEStream`: wraps a thread; `cancel()` sets a stop event
- `HttpClient` (singleton `http`): thread pool with `ThreadPoolExecutor(max_workers=4)`
  - Workers call `urllib.request.urlopen()`
  - Successful/failed responses pushed to `collections.deque` callback queue
  - Queue is drained on main thread via a single `bpy.app.timers` registered in `register()`
- `SSEClient` (singleton `sse`): spawns a dedicated thread per stream
  - SSE protocol: read line by line, parse `event:`, `data:`, blank line = dispatch chunk to callback queue
  - `on_done` dispatched to callback queue on clean end-of-stream
- Callback queue drainer registered in `puree/__init__.py` as a persistent timer; uses `timers.set_interval` from Feature 2
- No new deps: `urllib.request`, `urllib.error`, `json`, `threading`, `collections`

**Files changed**: `puree/net.py` (new), `puree/__init__.py` (register/unregister drain timer)

---

### 4. Focus Management — `puree/focus.py`

**Commit**: `feat(focus): add focus management system`

**API** (matching CHANGES.md exactly):
```python
input_field.focus()
input_field.blur()
input_field.on_focus.append(lambda c: ...)
input_field.on_blur.append(lambda c: ...)
if input_field.is_focused: ...
input_field.tab_index = 1
```

**Implementation**:
- `FocusManager` singleton (`focus_manager`):
  - `_focused: Optional[Container]`
  - `focus(container)`: blurs previous, sets `_focused`, calls `container.on_focus` callbacks
  - `blur(container=None)`: if `container` is None or is the currently focused container, calls `on_blur` callbacks, sets `_focused = None`
  - `get_focused() → Optional[Container]`
  - `is_focused(container) → bool`
- `Container` additions in `container.py`:
  - `on_focus: List` — new event list (like `click`)
  - `on_blur: List` — new event list
  - `tab_index: int = -1` — negative = not in tab order
  - `focusable: bool = False` — opt-in
  - `focus()` method → calls `focus_manager.focus(self)`
  - `blur()` method → calls `focus_manager.blur(self)`
  - `is_focused` property → `focus_manager.is_focused(self)`
- `TextInputInstance.focus()/blur()` in `text_input_op.py` updated to also call `focus_manager`
- `hit_op.py`: on LEFTMOUSE PRESS, if hit container has `focusable=True`, call `focus_manager.focus(container)`
- Tab key support: add to `KeyboardHandler.modal()` — when TAB pressed and not in text input, cycle through containers with `tab_index >= 0` in ascending order

**Files changed**: `puree/focus.py` (new), `puree/components/container.py`, `puree/text_input_op.py`, `puree/hit_op.py`, `puree/__init__.py` (export)

---

### 5. Keyboard Shortcuts — `puree/keyboard.py`

**Commit**: `feat(keyboard): add keyboard shortcut system`

**API** (matching CHANGES.md exactly):
```python
from puree.keyboard import keys
keys.bind("ENTER", on_send, when="input_focused")
keys.bind("ESCAPE", cancel_stream)
keys.bind("CTRL+N", new_chat)
input_field.keys.bind("SHIFT+ENTER", insert_newline)
```

**Implementation**:
- `KeyManager` singleton (`keys`):
  - `_bindings: list[Binding]` where `Binding = (key_combo, callback, when, container_id)`
  - `bind(key_combo, callback, when=None, container_id=None) → handle`
  - `unbind(handle) → None`
  - `clear() → None`
  - `dispatch(event, focused_container) → consumed: bool` — called from `KeyboardHandler`
  - Key combo parsing: `"CTRL+N"` → `{ctrl: True, key: "N"}`; `"SHIFT+ENTER"` → `{shift: True, key: "RET"}` (Blender's event.type names)
  - `when` values: `None` (always), `"input_focused"` (a text input has focus), or a container ID
  - Container-scoped `keys` accessor: property on `Container` that returns a `ContainerKeyManager(container_id)` proxy
- `KeyboardHandler.modal()` in `text_input_op.py`: at the end, before `PASS_THROUGH`, call `keys.dispatch(event, active_input_container)` and consume if handled

**Blender key name mapping** (normalized in `bind()`):
`ENTER → RET`, `ESCAPE → ESC`, `DELETE → DEL`, `BACKSPACE → BACK_SPACE`

**Files changed**: `puree/keyboard.py` (new), `puree/text_input_op.py` (dispatch in KeyboardHandler), `puree/components/container.py` (`.keys` property)

---

### 6. Dynamic Containers — multi-file

**Commit**: `feat(containers): add dynamic container creation and destruction`

**API** (matching CHANGES.md exactly):
```python
new_msg = parent.add_child("[msg_slot]", id="msg_42", params={"role": "assistant"})
new_msg.mark_dirty()
parent.remove_child("msg_42")
parent.mark_dirty()
parent.insert_child(0, "[msg_slot]", id="msg_top")
scroll_area.clear_children()
```

**Implementation**:

**`puree/parser.py`** changes:
- Add `_component_registry: dict` on `UI`:
  - Populated during `parse_toml()` when components are loaded
  - Key: component name (e.g. `"msg_slot"`)
  - Value: `{yaml_data: dict, scss_path: str, base_dir: str, compiled_css: str}`
- Extract the inline component loading closure into `UI._load_component(component_name, parent_container, params, namespace)` method
- Extract CSS application into `UI._apply_css_to_container(container)` method  
- Expose `UI.create_layout_nodes_for(container, parent_node)` for a single subtree

**`puree/dynamic.py`** (new):
- `DynamicContainerManager` singleton:
  - `_ui_ref: Optional[UI]` — set when UI is parsed
  - `create_child(parent, template_name, child_id, params) → Container`:
    1. Lookup `template_name` in `_ui_ref._component_registry`
    2. Call `_ui_ref._load_component()` to build the Container subtree
    3. Call `_ui_ref._apply_css_to_container()` on each new container
    4. Call `_ui_ref.create_layout_nodes_for()` to create Stretchable nodes
    5. Append the new container to `parent.children`
    6. Append the new layout node to `parent._layout_node`
    7. Mark parent dirty
    8. Return new container
  - `remove_child(parent, child_id) → bool`:
    1. Find child by ID in `parent.children`
    2. Remove from `parent.children`
    3. Remove layout node from `parent._layout_node` (stretchable `remove()`)
    4. Mark parent dirty
  - `insert_child(parent, index, template_name, child_id, params) → Container`:
    - Like `create_child` but uses `parent._layout_node.insert(index, ...)`
  - `clear_children(parent) → None`:
    - Clear `parent.children`, clear `parent._layout_node`

**`puree/components/container.py`** changes:
- Add `add_child(template, id=None, params=None) → Container`
- Add `remove_child(id_or_container) → bool`
- Add `insert_child(index, template, id=None, params=None) → Container`
- Add `clear_children() → None`
- All delegate to `dynamic_manager` singleton
- Auto-generate ID if not provided: `f"{self.id}_child_{len(self.children)}"`

**`puree/parser_op.py`** changes:
- `recompute_layout()` already rebuilds from the tree → works automatically
- `sync_dirty_containers()` already rebuilds flat list on dirty → works automatically
- Set `dynamic_manager._ui_ref = XWZ_UI` after parse in `execute()`

**Render pipeline**: `update_data_texture()` already handles count changes (recreates texture) → no changes needed

**Files changed**: `puree/dynamic.py` (new), `puree/parser.py` (component registry + extracted methods), `puree/components/container.py` (add/remove/insert/clear), `puree/parser_op.py` (wire dynamic manager)

---

### 7. Markdown Rendering — `puree/markdown.py`

**Commit**: `feat(markdown): add rich text and basic markdown rendering`

**API**:
```python
from puree.markdown import render_markdown

# In script.py
render_markdown(container, text, app)
# Or via Container method:
container.set_markdown(text, app)
```

**Supported Markdown Subset** (per CHANGES.md):
| Markdown | Puree Rendering |
|----------|----------------|
| `**bold**` | NeueMontreal-Bold font variant |
| `` `inline code` `` | Monospace font + background color |
| ` ```code block``` ` | Child container: dark bg, monospace |
| `# Heading` | Larger font size, bold |
| `- list item` | Indented text with `• ` prefix |
| `> blockquote` | Left border accent + indented text |
| `---` | Horizontal divider container |

**Implementation**:
- `parse_markdown(text) → list[dict]`: regex-based line/inline parser
  - Block-level: headings (`#`), list items (`-`), blockquotes (`>`), HR (`---`), code blocks (` ``` `)
  - Inline: bold (`**...**`), inline code (`` `...` `` )
  - Each segment: `{type, content, level}` dict
- `render_markdown(container, text, app)`:
  - First calls `container.clear_children()` (requires Feature 6)
  - Then for each segment, calls `container.add_child()` with appropriate text/font/style
  - Uses pre-defined CSS classes (`.md_text`, `.md_bold`, `.md_code_inline`, `.md_code_block`, etc.) that users can override in their SCSS
  - Built-in default styles injected into the CSS pipeline
- `Container.set_markdown(text, app)`: convenience method

**Default CSS classes provided** (`puree/markdown_defaults.scss`):
- `.md_text`, `.md_bold`, `.md_h1/.md_h2/.md_h3`, `.md_code_block`, `.md_list_item`, `.md_blockquote`, `.md_hr`
- Designed to be overridable in user SCSS

**Files changed**: `puree/markdown.py` (new), `puree/markdown_defaults.scss` (new), `puree/components/container.py` (`.set_markdown()` method), `puree/parser.py` (inject default markdown CSS), `puree/__init__.py` (export)

---

### 8. Virtual Scrolling — `puree/virtual_scroll.py`

**Commit**: `feat(scroll): add virtual scrolling for large lists`

**API** (matching CHANGES.md exactly):
```yaml
messages_scroll:
  style: scroll_area
  virtual: true
  item_height: auto   # or fixed px
```

```python
scroll = app.get_by_id("messages_scroll")
scroll.set_virtual_data(messages_list)
scroll.set_item_renderer(render_message_slot)
scroll.mark_dirty()
```

**Implementation**:
- `VirtualScrollManager` singleton: manages one `VirtualList` per container ID
- `VirtualList`:
  - `data`: list of items
  - `item_renderer`: callback `fn(container, item)` — binds data to a container
  - `item_height`: `"auto"` or int px
  - `_pool`: list of reusable containers (created via `add_child`)
  - `_scroll_offset`: current scroll position
  - `_visible_range`: `(start_idx, end_idx)` of currently rendered items
  - `_heights`: cumulative height cache for variable-height items
- On `set_virtual_data()` / `set_item_renderer()`:
  - Clears pool
  - Calculates how many items fit in the visible area
  - Creates that many containers via `add_child`
  - Calls `item_renderer` for each visible item
- On scroll event (registered in `scroll` callback):
  - Recalculates visible range
  - Rebinds visible containers without creating new ones (slot recycling)
  - For variable height: updates `_heights` cache as items are measured
- `Container` additions:
  - `set_virtual_data(data_list)`
  - `set_item_renderer(fn)`
  - `_virtual_manager` reference
- YAML `virtual: true` and `item_height: N` parsed in `parser.py` → stored on container

**Files changed**: `puree/virtual_scroll.py` (new), `puree/components/container.py` (virtual methods), `puree/parser.py` (parse `virtual` attribute), `puree/__init__.py` (export)

---

### 9. Container Collapse/Expand — `puree/collapse.py`

**Commit**: `feat(collapse): add container collapse/expand with animation`

**API** (matching CHANGES.md exactly):
```yaml
tool_details:
  style: collapsible
  collapsed: true
  children:
    tool_header:
      text: "web_search"
    tool_body:
      style: collapsible_body
      text: "Results..."
```
```python
details = app.get_by_id("tool_details")
details.toggle_collapse()
details.mark_dirty()
```

**Implementation**:
- `CollapseManager` singleton:
  - Manages active collapse animations: `{container_id: CollapseAnimation}`
  - `CollapseAnimation`: `start_height, target_height, start_time, duration=0.2s`
  - Tick function called from `sync_dirty_containers()` or the render timer
- `Container` additions:
  - `collapsed: bool = False` — initial state (parsed from YAML)
  - `_collapse_header_id: Optional[str]` — ID of first child (header, always visible)
  - `toggle_collapse()`: flips `collapsed` state, starts animation via `CollapseManager`
  - `is_collapsed: bool` property
- Animation mechanism:
  - On collapse: record `current_height`, target = header child height
  - Set children (except header) to `display: NONE` after animation completes
  - During animation: set explicit `height` on the container (interpolated)
  - On expand: set children to `display: FLEX`, animate height from header height to full height, then clear explicit height
  - Uses `bpy.app.timers` loop (piggyback on existing render timer or use `set_interval`)
- YAML `collapsed: true` → parsed in `parser.py` → sets `container.collapsed = True` and hides non-header children initially

**Caveat**: Puree can't animate layout properties via CSS transitions. The collapse animation works by
calling `container.set_property('height', ...)` each frame, which updates the Stretchable node.
This is intentionally an internal mechanism (not CSS) as described in CHANGES.md.

**Files changed**: `puree/collapse.py` (new), `puree/components/container.py` (collapse methods/props), `puree/parser.py` (parse `collapsed`), `puree/parser_op.py` (tick collapse animations), `puree/__init__.py` (export)

---

## Documentation Updates

After all features are implemented, update:
- `docs/PUREE_SPEC.md` — add sections for all 9 new APIs
- `docs/API.md` — document new Container methods, new modules
- `docs/PUREE_VS_CSS.md` — note markdown subset, virtual scrolling
- `README.md` — mention new capabilities (HTTP, persistence, markdown, etc.)
- `.github/copilot-instructions.md` (if exists) — update framework capabilities
- `puree/scaffold/` templates (if any) — consider adding examples

---

## Notes / Open Questions

1. **Feature 6 (Dynamic Containers)**: The component registry caching needs to also re-apply CSS from `_component_css` string to new containers. The current CSS cascade is batch-applied to the entire tree. For dynamic children, we need `_apply_css_to_container()` to handle scoped/namespaced component CSS. This is the highest-risk part of the implementation.

2. **Feature 8 (Virtual Scrolling)**: Variable-height items require measuring container height after layout. This might cause a one-frame delay where items are measured then repositioned. Fixed-height mode avoids this entirely.

3. **Feature 9 (Collapse/Expand)**: Setting explicit `height` each frame while animating may interact with other dirty flags. We should ensure the animation loop uses a dedicated timer that marks dirty without triggering full re-parse.

4. **Feature 3 (HTTP)**: `project` scope for Storage requires `bpy.data.filepath` which may be empty for unsaved files. Need a fallback (fall back to global scope or raise a clear error).
