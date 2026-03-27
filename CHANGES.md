# Recommended Changes to Puree UI

Changes to the Puree framework that would make building apps like Sous dramatically simpler, while benefiting every Puree addon — not just this one.

---

## 1. Built-in HTTP Client with SSE Streaming

**Priority**: Critical
**Affected files**: New module `puree/net.py` + Rust helper in `puree_rust_core`

### Problem

Every Puree app that needs to talk to an API (LLMs, asset libraries, cloud services, analytics) must manually:
1. Import `urllib.request` or bundle `httpx`
2. Spin up a `threading.Thread` for every request (Blender's main thread blocks on I/O)
3. Build a `collections.deque` to ferry data back to the main thread
4. Register a `bpy.app.timers` poller to drain the queue and call `mark_dirty()`

This is ~50 lines of boilerplate per endpoint and is the #1 pain point for any non-trivial addon.

### Proposed API

```python
from puree.net import http, sse

# ─── Simple request (runs in background, callback on main thread) ───
http.get("https://api.example.com/models", 
    headers={"Authorization": f"Bearer {key}"},
    on_success=lambda resp: update_model_list(resp.json()),
    on_error=lambda err: show_error(str(err)))

http.post("https://api.example.com/chat",
    json={"messages": msgs},
    on_success=handle_response,
    on_error=handle_error)

# ─── SSE streaming (each chunk delivered to main thread) ───
stream = sse.connect("https://api.example.com/stream",
    method="POST",
    json={"messages": msgs, "stream": True},
    headers={"Authorization": f"Bearer {key}"},
    on_chunk=lambda event: append_text(event.data),
    on_done=lambda: finalize_message(),
    on_error=lambda err: show_error(str(err)))

# Cancel an in-flight stream
stream.cancel()
```

### Implementation

- **Thread pool** (2-4 workers) managed by Puree, not per-addon — avoids thread explosion
- **Main-thread dispatch** via a single `bpy.app.timers` poller (already exists for transitions — piggyback on it)
- Callbacks are always invoked on the main thread — safe to call `mark_dirty()` directly
- SSE parser: simple line-based protocol (`event:`, `data:`, blank line = dispatch)
- Timeouts, retry, and cancellation built in
- No new dependencies — `urllib.request` under the hood (or optional `httpx` if bundled)

### Benefit to Puree

Every addon that talks to any API gets this for free. Chat apps, asset managers, render farm integrations, analytics dashboards — all become trivial to network.

---

## 2. Dynamic Container Creation & Destruction

**Priority**: Critical  
**Affected files**: `puree/components/container.py`, `puree/parser.py`, `puree/render.py`

### Problem

Puree currently requires all containers to be pre-allocated in YAML at parse time. There is no `add_child()` or `remove_child()`. For a chat app, this means:
- Pre-allocate N message slots and show/hide them (current Sous approach: 15 slots)
- Manual recycling pools in user code
- Can't handle variable content (a message with 3 tool calls vs. one with none)
- Every "dynamic" element is actually a hidden static element being revealed

This is the single biggest architectural limitation for any app with dynamic content.

### Proposed API

```python
# Create a container from a component template
new_msg = parent.add_child("[msg_slot]", id="msg_42", params={
    "role": "assistant",
    "text": "Hello world"
})
new_msg.mark_dirty()

# Remove a container (and its children)
parent.remove_child("msg_42")
parent.mark_dirty()

# Insert at specific position
parent.insert_child(0, "[msg_slot]", id="msg_top")

# Clear all children
scroll_area.clear_children()
```

### Implementation

- Component templates already parsed and cached — `add_child` instantiates from the cached template
- New container gets a layout node inserted into the Taffy tree (stretchable supports `add_child`)
- Render pipeline's flat array (`abs_json_data`) rebuilt on next `compute_layout()` — already happens on dirty
- Hit detector AABB list updated on same cycle
- `remove_child()` detaches from container tree + layout tree, marks parent dirty
- GPU texture needs reallocation if container count grows past current capacity (double-buffer strategy)

### Benefit to Puree

Any app with lists, feeds, dynamic forms, search results, or variable-length content becomes possible. This is the difference between "UI framework" and "static layout renderer."

---

## 3. Built-in JSON Persistence

**Priority**: High  
**Affected files**: New module `puree/storage.py`

### Problem

Every addon needs to save state (chat history, user preferences, project settings). Currently each developer must:
1. Decide where to store files (`~/.config/addon/`, Blender prefs, scene custom properties)
2. Write JSON serialization/deserialization
3. Handle file locking, corruption recovery, migrations
4. Wire up save triggers (on change, on close, periodic)

### Proposed API

```python
from puree.storage import Storage

# App-level storage (persists across sessions, stored in ~/.config/puree/{addon_name}/)
store = Storage("sous")

# Read/write with defaults
store.set("active_model", "claude-sonnet")
model = store.get("active_model", default="ollama-llama3")

# Nested data
store.set("conversations.thread_1", {"title": "Chat 1", "messages": [...]})
convos = store.get("conversations", default={})

# Auto-save on change (debounced, 500ms)
store.auto_save = True

# Manual save/load
store.save()
store.load()

# Project-level storage (saved alongside .blend file)
project_store = Storage("sous", scope="project")
```

### Implementation

- JSON files in `~/.config/puree/{addon_name}/` (follows XDG on Linux, AppData on Windows)
- Debounced writes via `bpy.app.timers` (one write per 500ms max, not per change)
- Atomic writes (write to temp, rename) to prevent corruption
- Optional `scope="project"` stores in `.blend` file's directory
- Thread-safe reads (no lock needed for JSON — write is always main thread via timer)

### Benefit to Puree

Every addon gets persistence for free. No more "all data lost when you close the panel" — which is probably the most common complaint for Puree apps.

---

## 4. Virtual Scrolling

**Priority**: High  
**Affected files**: `puree/scroll_op.py`, `puree/render.py`, `puree/components/container.py`

### Problem

Puree's scroll system renders all children of a scrollable container, even those completely off-screen. With 500+ containers, performance drops. Chat apps, file browsers, and any list-heavy UI hit this wall.

Currently the only workaround is manual slot recycling (pre-allocate N slots, reassign content as user scrolls), which is complex and error-prone.

### Proposed API

```yaml
messages_scroll:
  style: scroll_area
  virtual: true           # Enable virtual scrolling
  item_height: auto       # Or fixed px for uniform items
```

```python
# In script.py — provide data, not containers
scroll = app.get_by_id("messages_scroll")
scroll.set_virtual_data(messages_list)            # List of dicts
scroll.set_item_renderer(render_message_slot)     # Callback per visible item
scroll.mark_dirty()
```

### Implementation

- Calculate visible range from scroll offset + container height + item heights
- Only create/bind containers for visible items (reuse pool internally)
- On scroll: recalculate visible range, rebind containers
- Variable-height items: maintain cumulative height cache (update as items are measured)
- Fixed-height items: trivial calculation, best performance
- Works with dynamic container creation (Change #2) for the internal pool

### Benefit to Puree

Any app with a long list (chat messages, file browsers, asset libraries, log viewers) gets smooth 60fps scrolling regardless of data size.

---

## 5. Rich Text / Basic Markdown Rendering

**Priority**: High  
**Affected files**: `puree/text_op.py`, new `puree/markdown.py`

### Problem

Puree renders text as single-style plain text per container. LLM responses contain markdown (bold, code blocks, headers, lists, links). Without rich text, chat apps look broken — all formatting is lost.

### Proposed Approach

Not full markdown — a **subset** that maps to what Puree can already do:

| Markdown | Puree Rendering |
|----------|----------------|
| `**bold**` | Switch to Bold font variant (NeueMontreal-Bold) |
| `` `inline code` `` | Monospace font + subtle background highlight |
| ```` ```code block``` ```` | Separate container: dark bg, monospace font, full width |
| `# Heading` | Larger font size, bold |
| `- list item` | Indented text with bullet character prefix |
| `> blockquote` | Left border accent + indented text |
| `---` | Horizontal divider container |

### Implementation

- **Parse step**: Python markdown parser (simple regex-based, not a full AST) splits text into segments: `[("text", "Hello "), ("bold", "world"), ("code", "x = 1")]`
- **Render step**: Each segment maps to a text draw call with the appropriate font/size — BLF already supports multiple fonts per draw
- **Code blocks**: Rendered as separate containers (use dynamic container creation from Change #2) with monospace font and dark background
- Shipped as a Puree module, not a dependency — ~200 lines of Python

### Benefit to Puree

Any app rendering LLM output, documentation, or formatted content gets readable text. This is table stakes for modern UI frameworks.

---

## 6. Keyboard Shortcut System

**Priority**: Medium  
**Affected files**: `puree/hit_op.py` or new `puree/keyboard.py`

### Problem

Puree has no keyboard event handling. The hit detection modal only processes `MOUSEMOVE`, `LEFTMOUSE`, and `MOUSEWHEEL`. Every addon that needs shortcuts (Enter to send, Escape to cancel, Ctrl+N for new) must hack around this.

### Proposed API

```python
# In script.py
from puree.keyboard import keys

# Global shortcuts
keys.bind("ENTER", on_send, when="input_focused")
keys.bind("ESCAPE", cancel_stream)
keys.bind("CTRL+N", new_chat)

# Container-scoped shortcuts
input_field.keys.bind("SHIFT+ENTER", insert_newline)
```

### Implementation

- Extend the existing modal operator to also listen to `KEYBOARD` events
- Route keyboard events through same container focus system as text input
- Modifier detection: `event.shift`, `event.ctrl`, `event.alt`
- Focus-aware: shortcuts can be scoped to focused container or global
- Don't conflict with Blender's own shortcuts — only active when Puree has input focus

### Benefit to Puree

Every app gets keyboard interaction without hacking Blender's event system. Forms, chat apps, tools, games — all need this.

---

## 7. Container Collapse/Expand (Disclosure)

**Priority**: Medium  
**Affected files**: `puree/components/container.py`, new CSS property

### Problem

Expanding/collapsing sections is a recurring UI pattern (tool call details, settings groups, sidebar sections). Currently requires manual show/hide of children with height animation — and height isn't animatable in Puree, so it snaps.

### Proposed API

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

```scss
.collapsible_body {
  overflow: hidden;
  // Height animates via Puree's internal mechanism (not CSS transition)
}
```

```python
# Toggle in script.py
details = app.get_by_id("tool_details")
details.toggle_collapse()  # Smooth animated expand/collapse
details.mark_dirty()
```

### Implementation

- `collapsed` property on container: when true, children get `display: NONE` and container height animates to header-only
- Animation handled internally by Puree (similar to transition manager, but for layout properties)
- Expand: measure children, animate height from 0 to measured, then set `display: FLEX`
- This is a special case — Puree can't animate layout in CSS, but can do it internally in the layout engine

### Benefit to Puree

Collapsible sections are used everywhere: settings panels, tree views, detail panes, FAQ sections. Built-in support eliminates a class of complex user code.

---

## 8. Timer / Interval API

**Priority**: Medium  
**Affected files**: New module `puree/timers.py`

### Problem

`bpy.app.timers.register()` works but is low-level. Addons end up with scattered timer registrations that are hard to clean up, can leak on hot reload, and have no cancellation mechanism.

### Proposed API

```python
from puree.timers import set_interval, set_timeout, clear

# Polling (returns handle for cancellation)
poll_handle = set_interval(check_server_health, 5000)  # every 5 seconds

# One-shot delay
timeout_handle = set_timeout(hide_notification, 3000)  # after 3 seconds

# Cancel
clear(poll_handle)

# All timers auto-cleanup on addon disable / hot reload
```

### Implementation

- Thin wrapper over `bpy.app.timers.register()` with:
  - Handle-based cancellation
  - Automatic cleanup registry (all timers cleared on addon reload)
  - Millisecond API (more intuitive than the seconds-based return value)
  - Error handling (timer callback exceptions don't crash Blender)

### Benefit to Puree

Cleaner timer management, no leaked timers on hot reload, easier cancellation. Every addon with polling, animations, or delayed actions benefits.

---

## 9. Focus Management System

**Priority**: Medium  
**Affected files**: `puree/hit_op.py`, `puree/text_input_op.py`

### Problem

Puree has no focus concept beyond text inputs tracking their own `is_focused` state. There's no way to:
- Know which container has focus
- Tab between focusable elements
- Programmatically focus a container
- Blur all focus

Sous currently polls text input focus state every 150ms to detect Enter-to-send — a hack.

### Proposed API

```python
# Programmatic focus
input_field.focus()  # Gives keyboard focus
input_field.blur()   # Removes focus

# Focus events
input_field.on_focus.append(lambda c: ...)
input_field.on_blur.append(lambda c: ...)

# Check focus
if input_field.is_focused:
    ...

# Tab order (optional)
input_field.tab_index = 1
```

### Implementation

- Global `FocusManager` singleton (similar to `MouseState`, `ScrollState`)
- Focus state tracked per-container, only one focused at a time
- Click on focusable container → focus it, blur previous
- Text input integration: `TextInputInstance.is_focused` backed by FocusManager
- `on_focus` / `on_blur` callback lists on Container
- Tab key support: cycle through containers with `tab_index` set

### Benefit to Puree

Forms, search fields, chat inputs, settings panels — all need focus management. Eliminates the focus-polling hack pattern.

---

## Summary & Priority Matrix

| # | Change | Priority | Effort | Sous Impact | General Impact |
|---|--------|----------|--------|-------------|----------------|
| 1 | HTTP Client + SSE | Critical | Medium | Eliminates bridge boilerplate | Every networked addon |
| 2 | Dynamic Containers | Critical | High | Unlimited messages, tool cards | Any app with lists |
| 3 | JSON Persistence | High | Low | Conversation history | Every addon needing state |
| 4 | Virtual Scrolling | High | High | Smooth long conversations | Any list-heavy UI |
| 5 | Markdown Rendering | High | Medium | Readable LLM responses | Any text-heavy app |
| 6 | Keyboard Shortcuts | Medium | Low | Enter-to-send, Escape-to-cancel | Every interactive app |
| 7 | Collapse/Expand | Medium | Medium | Tool call details | Settings, trees |
| 8 | Timer API | Medium | Low | Cleaner polling | Every addon |
| 9 | Focus Management | Medium | Medium | Proper input handling | Every form/input app |

### Recommended Implementation Order

1. **HTTP Client + SSE** — unblocks all networking for Sous and any other connected addon
2. **Dynamic Containers** — unblocks flexible message lists, tool cards, and variable content
3. **JSON Persistence** — small effort, huge impact for any addon
4. **Timer API** — small effort, cleans up existing patterns
5. **Focus Management** — enables proper keyboard interaction
6. **Keyboard Shortcuts** — depends on focus management
7. **Markdown Rendering** — depends on dynamic containers (for code blocks)
8. **Virtual Scrolling** — depends on dynamic containers
9. **Collapse/Expand** — depends on dynamic containers + internal layout animation
