---
layout: page
title : 3. API Reference
---

## CSS Properties

All properties are set via SCSS files. Use `container.set_property('css-property', value)` for runtime changes. Both kebab-case (`background-color`) and underscore (`background_color`) are accepted.

> [!CAUTION]
> **Critical Rule**: After ANY property change, call `container.mark_dirty()`. The GPU will not re-render without it.

**Reading style at runtime:** Access via `container.style.field_name`. Enum values are UPPERCASE at runtime — e.g. `container.style.display` returns `'FLEX'` or `'NONE'`.

**Length units:** `px`, `%`, `rem`, `em`, `vw`, `vh`, `vmin`, `vmax`, plus `calc()` expressions (addition and subtraction only, e.g. `calc(100% - 24px)`).

**Selectors:** class, ID, descendant, child (`>`), adjacent sibling (`+`), general sibling (`~`), universal (`*`), comma lists, and the pseudo-classes `:hover`, `:active`, `:first-child`, `:last-child`, `:nth-child(an+b|odd|even)`, `:not()`.

### Colors & Backgrounds

| CSS Property | Description |
|---|---|
| `background-color` | Fill color |
| `background` | Shorthand: solid color or `linear-gradient()` |
| `background-image` | Alias for `background: linear-gradient()` |
| `color` | Text color (inherited by children) |
| `opacity` | Element opacity (0–1) |
| `visibility` | `visible`, `hidden` (hidden keeps layout space) |

**Hover and active states** are set via standard SCSS pseudo-classes. Only these properties are supported in `:hover` / `:active` rules (layout properties like width/padding are ignored):

| Pseudo-class | Supported properties |
|---|---|
| `:hover { }` | `background-color`, `background` (incl. `linear-gradient()`), `color`, `border-color`, `opacity` (only `background-color`, `border-color`, `opacity` are transition-animated; `color` changes instantly) |
| `:active { }` | `background-color`, `background` (incl. `linear-gradient()`), `color`, `border-color`, `opacity` (only `background-color`, `border-color`, `opacity` are transition-animated; `color` changes instantly) |

### Typography

| CSS Property | Description |
|---|---|
| `font-size` | Text size in px |
| `text-align` | `left`, `center`, `right` |
| `--text-align-v` | Vertical alignment: `top`, `center`, `bottom` |
| `--text-x` | Horizontal text offset in px |
| `--text-y` | Vertical text offset in px |
| `font-weight` | `normal`, `bold` |
| `font-style` | `normal`, `italic` |
| `text-decoration` | `none`, `underline`, `overline`, `line-through` |
| `text-transform` | `none`, `uppercase`, `lowercase`, `capitalize` |
| `letter-spacing` | Character spacing in px |
| `line-height` | Unitless multiplier (e.g. `1.2`) |
| `white-space` | `normal` (wrap), `nowrap`, `pre` |
| `text-overflow` | `clip`, `ellipsis` — requires `white-space: nowrap` |
| `text-shadow` | `offset-x offset-y blur color` — single shadow only |
| `text-shadow-color` | Text shadow color (rgba) |
| `text-shadow-offset-x` | Text shadow horizontal offset (px) |
| `text-shadow-offset-y` | Text shadow vertical offset (px) |
| `text-shadow-blur` | Text shadow blur radius (px) |
| `overflow-wrap` | `normal`, `break-word` — whether to break words to prevent overflow |
| `word-break` | `normal`, `break-all` — word breaking rules |

> Font face is selected via YAML `font:` attribute, not CSS `font-family`.

### Box Model

| CSS Property | Description |
|---|---|
| `width` | Element width (`px`, `%`) |
| `height` | Element height (`px`, `%`) |
| `min-width` / `max-width` | Width constraints |
| `min-height` / `max-height` | Height constraints |
| `padding` / `padding-top` / `padding-right` / `padding-bottom` / `padding-left` | Padding (px or %) |
| `margin` / `margin-top` / `margin-right` / `margin-bottom` / `margin-left` | Margin (px or %) |
| `border-radius` | All-corner radius |
| `border-top-left-radius` | Top-left corner |
| `border-top-right-radius` | Top-right corner |
| `border-bottom-right-radius` | Bottom-right corner |
| `border-bottom-left-radius` | Bottom-left corner |
| `border-width` | Uniform width, or `top right bottom left` shorthand |
| `border-top-width` / `border-right-width` / `border-bottom-width` / `border-left-width` | Per-side widths |
| `border-color` | Uniform border color |
| `border` | Shorthand: `1px solid red` |
| `border-top` / `border-right` / `border-bottom` / `border-left` | Per-side shorthand |
| `border-image` | `linear-gradient()` for gradient border. Requires `border-width: Npx` |
| `box-shadow` | `offset-x offset-y blur color` — single shadow only |
| `box-sizing` | `content-box`, `border-box` |

> Per-side border **colors** are not supported — use a uniform `border-color`.

### Layout

| CSS Property | Description |
|---|---|
| `display` | `flex`, `grid`, `block`, `none` |
| `position` | `relative`, `absolute` |
| `top` / `right` / `bottom` / `left` | Position offsets |
| `overflow` | `visible`, `hidden`, `scroll`, `auto` |
| `overflow-x` / `overflow-y` | Per-axis overflow |
| `scrollbar-width` | Scrollbar track width: `none`, `thin` (6px), `auto` (8px), or px value |
| `scrollbar-color` | `<thumb-color> <track-color>` shorthand |
| `scrollbar-thumb-color` | Scrollbar thumb/handle color |
| `scrollbar-track-color` | Scrollbar track background color |
| `pointer-events` | `auto`, `none` — `none` prevents hover/click detection on the element and all children. Use for overlay containers that shouldn't block interaction. |
| `align-items` | `start`, `end`, `center`, `stretch`, `baseline` |
| `justify-items` | `start`, `end`, `center`, `stretch`, `baseline` |
| `align-self` | Per-item alignment override |
| `justify-self` | Per-item justify override |
| `align-content` | `start`, `end`, `center`, `stretch`, `space-between`, `space-around`, `space-evenly` |
| `justify-content` | Same values as `align-content` |
| `flex-direction` | `row`, `column`, `row-reverse`, `column-reverse` |
| `flex-wrap` | `nowrap`, `wrap`, `wrap-reverse` |
| `flex-grow` | Growth factor |
| `flex-shrink` | Shrink factor |
| `flex-basis` | Base size |
| `gap` | Gap between flex/grid items |
| `row-gap` / `column-gap` | Per-axis gap |
| `grid-auto-flow` | `row`, `column`, `row dense`, `column dense` |
| `grid-template-rows` / `grid-template-columns` | Explicit track sizes |
| `grid-auto-rows` / `grid-auto-columns` | Implicit track sizes |
| `grid-row` / `grid-column` | Item placement |

### Image (Extensions)

| CSS Property | Description |
|---|---|
| `--img-align-h` | Image horizontal alignment: `left`, `center`, `right` |
| `--img-align-v` | Image vertical alignment: `top`, `center`, `bottom` |

### Transitions

Only `background-color`, `border-color`, and `opacity` are animatable via transitions. `color` (text color) changes instantly on hover/active state changes.

| CSS Property | Description |
|---|---|
| `transition` | Shorthand: `property duration timing-function` — comma-separated for multiple |
| `transition-property` | Property name to animate |
| `transition-duration` | Duration in seconds (`0.3s`) |
| `transition-timing-function` | `ease`, `linear`, `ease-in`, `ease-out`, `ease-in-out` |
| `transition-delay` | Delay before starting (`0.1s`) |

---

## Container Properties

The `Container` class represents a UI node. Access nodes via dot notation in `script.py`:

```python
button = app.theme.root.sidebar.nav_button
```

| Property | Type | Description |
|---|---|---|
| `id` | `str` | Element ID, auto-generated from YAML path |
| `parent` | `Container` | Parent container |
| `children` | `List[Container]` | Child containers |
| `text` | `str` | Text content |
| `img` | `str` | Image asset name (no extension) |
| `font` | `str` | Font face name (no extension) |
| `data` | `str` | Component reference (`'[component_name]'`) or text-input marker (`'<INPUT> \| placeholder'`) |
| `classes` | `list` | CSS class names applied to this container |
| `layer` | `int` | **Deprecated — no effect.** Defined on the container but never read by the renderer. Draw order comes from CSS `z-index` sorting (stable sort — tree order is preserved within the same `z-index`). |
| `passive` | `bool` | If `True`, element ignores all interaction events |
| `focusable` | `bool` | If `True`, element can receive keyboard focus |
| `tab_index` | `int` | Tab order for keyboard navigation (`-1` = not in tab order) |
| `collapsed` | `bool` | If `True`, container starts in collapsed state |
| `virtual` | `bool` | If `True`, enables virtual scrolling for this container |
| `item_height` | `int\|str` | Virtual scroll item height in px, or `'auto'` for variable height |
| `style` | `Style` | Resolved style object — read via `container.style.property_name` |
| `click` | `List` | Click event handler list |
| `toggle` | `List` | Toggle event handler list |
| `scroll` | `List` | Scroll event handler list |
| `hover` | `List` | Hover-in event handler list |
| `hoverout` | `List` | Hover-out event handler list |
| `on_focus` | `List` | Focus-in event handler list |
| `on_blur` | `List` | Focus-out event handler list |
| `_toggled` | `bool` | Whether a toggle event fired THIS frame (transient — resets next frame) |
| `_clicked` | `bool` | Whether currently clicked (read-only) |
| `_hovered` | `bool` | Whether currently hovered (read-only) |
| `_toggle_value` | `bool` | The persistent boolean state of the toggle (True/False — persists across frames) |
| `_scroll_value` | `float` | Current scroll offset in px (read-only) |

**Text-input nodes:** setting `data: "<INPUT> | placeholder text"` on a YAML node turns it into an editable text input — the text after the `|` becomes the placeholder. The input uses the node's font, `font-size`, `color`, and text alignment.

---

## Container Methods

| Method | Signature | Description |
|---|---|---|
| `mark_dirty()` | `() -> None` | Flag container for GPU re-render. **Must be called after any property change.** |
| `get_by_id(target_id)` | `(str) -> Container \| None` | Find a descendant container by ID |
| `set_property(name, value)` | `(str, Any) -> None` | Set a CSS property at runtime. Accepts CSS names (`background-color`) or underscore equivalents. Handles color parsing, gradient parsing, and layout recalculation automatically. |
| `add_child(template, id, params)` | `(str, str \| None, dict \| None) -> Container` | Create and append a child from a component template (e.g. `"[card]"`). |
| `insert_child(index, template, id, params)` | `(int, str, str \| None, dict \| None) -> Container` | Insert a child at a specific position from a component template. |
| `remove_child(id_or_container)` | `(str \| Container) -> bool` | Remove a child by ID string or Container reference. |
| `clear_children()` | `() -> None` | Remove all children from this container. |
| `focus()` | `() -> None` | Give this container keyboard focus. Works on any container — `focusable: true` and `tab_index` are only needed for Tab/Shift+Tab cycling (`focus_manager.tab_next()` / `tab_prev()`). |
| `blur()` | `() -> None` | Remove keyboard focus from this container. |
| `is_focused` | `-> bool` | Property — returns `True` if this container currently has keyboard focus. |
| `collapse()` | `() -> None` | Collapse instantly to header-only height (children after the first are hidden). |
| `expand()` | `() -> None` | Expand instantly to full height (all children shown). |
| `toggle_collapse()` | `() -> None` | Toggle between collapsed and expanded states. |
| `is_collapsed` | `-> bool` | Property — returns `True` if this container is currently collapsed. |
| `set_markdown(text, fonts, classes)` | `(str, dict \| None, dict \| None) -> None` | Render markdown text as child containers. Clears existing children first. `fonts` maps `'regular'` / `'bold'` / `'mono'` to font names; `classes` maps markdown elements to CSS classes. |
| `keys` | `ContainerKeyProxy` | Property — scoped keyboard shortcut binding. Use `container.keys.bind("SHIFT+ENTER", callback)` for container-scoped shortcuts. |
| `set_virtual_data(data_list)` | `(list) -> None` | Assign a data list for virtual scrolling. Requires `virtual: true`. |
| `set_item_renderer(fn)` | `(Callable[[Container, Any, int], None]) -> None` | Set the callback to render each virtual scroll item. The callback receives `(container, item, index)`. |

---

## Modules

Puree provides built-in modules for common addon tasks. Import them in your `script.py`:

### Storage — `puree.storage`

JSON-backed key-value persistence with automatic save.

```python
from puree.storage import Storage

store = Storage(namespace="my_addon")               # global scope (survives across sessions)
project_store = Storage(namespace="my_addon", scope="project")  # stored next to .blend file

store.set("active_model", "claude-sonnet")
model = store.get("active_model", default="ollama-llama3")

store.set("conversations.thread_1", {"title": "Chat 1", "messages": [...]})  # dot-notation keys

store.auto_save = True   # debounced 500ms writes
store.save()             # manual save
store.load()             # manual load
store.delete("key")      # delete a key
store.clear()            # clear all data
```

### Timers — `puree.timers`

Managed timer/interval API with auto-cleanup on hot reload.

```python
from puree.timers import set_interval, set_timeout, clear

poll_handle = set_interval(check_health, 5000)    # every 5 seconds (ms)
timeout_handle = set_timeout(hide_toast, 3000)     # one-shot after 3 seconds (ms)

clear(poll_handle)       # cancel a timer
poll_handle.cancel()     # alternative: cancel via handle
```

All timers are automatically cleaned up on addon disable or hot reload.

### HTTP & SSE — `puree.net`

Built-in HTTP client with SSE streaming. Callbacks run on Blender's main thread (safe to call `mark_dirty()`).

```python
from puree.net import http, sse

# Simple requests (background thread, callback on main thread)
http.get("https://api.example.com/models",
    headers={"Authorization": f"Bearer {key}"},
    on_success=lambda resp: update_list(resp.json()),
    on_error=lambda err: show_error(str(err)))

http.post("https://api.example.com/chat",
    json={"messages": msgs},
    on_success=handle_response,
    on_error=handle_error)

# SSE streaming (each chunk delivered on main thread)
stream = sse.connect("https://api.example.com/stream",
    method="POST",
    json={"messages": msgs, "stream": True},
    headers={"Authorization": f"Bearer {key}"},
    on_chunk=lambda event: append_text(event.data),
    on_done=lambda: finalize(),
    on_error=lambda err: show_error(str(err)))

stream.cancel()   # cancel in-flight stream
```

**Response objects:**

| Class | Properties |
|---|---|
| `HttpResponse` | `.status_code`, `.headers`, `.text`, `.json()`, `.ok` |
| `SSEEvent` | `.event`, `.data`, `.id` |
| `HttpError` | `.status_code`, `.reason`, `.body`, `.text` |

### Focus — `puree.focus`

Programmatic focus management with Tab/Shift+Tab keyboard navigation.

```python
from puree.focus import focus_manager

input_field.focus()       # give keyboard focus
input_field.blur()        # remove focus

if input_field.is_focused:
    ...

# Focus events
input_field.on_focus.append(lambda c: highlight(c))
input_field.on_blur.append(lambda c: unhighlight(c))

# Tab navigation works automatically for containers with tab_index >= 0
```

`container.focus()` works on any container. `focusable: true` in YAML (or `container.focusable = True` at runtime) and `tab_index >= 0` are only required for Tab/Shift+Tab keyboard cycling (`focus_manager.tab_next()` / `tab_prev()`); `tab_index` controls the Tab order.

### Keyboard — `puree.keyboard`

Keyboard shortcut system with global and container-scoped bindings.

```python
from puree.keyboard import keys

# Global shortcuts
keys.bind("ENTER", on_send, when="input_focused")
keys.bind("ESCAPE", cancel_stream)
keys.bind("CTRL+N", new_chat)

# Container-scoped shortcuts
input_field.keys.bind("SHIFT+ENTER", insert_newline)

# Unbind
binding = keys.bind("CTRL+S", save_action)
keys.unbind(binding)

# Remove all bindings
keys.clear()
```

**Callbacks receive zero arguments** — bind zero-arg callables (`keys.bind("CTRL+N", new_chat)` or `keys.bind("CTRL+N", lambda: new_chat())`). A callback that expects arguments will raise `TypeError` when the shortcut fires.

**Key combo format:** Modifier keys (`CTRL`, `SHIFT`, `ALT`) joined with `+` before the key name. Key names use Blender conventions (`RET` for Enter, `ESC` for Escape, etc.) but common aliases (`ENTER`, `ESCAPE`, `DELETE`, `BACKSPACE`) are auto-mapped.

**`when` parameter:** `None` (always active), `"input_focused"` (only when a text input has focus), or a container ID.

### Markdown — `puree.markdown`

Render a subset of Markdown as child containers. Requires dynamic container support.

**Preferred** — use the Container method `set_markdown()`:
```python
# Recommended: Container method (full signature)
container.set_markdown(text, fonts=None, classes=None)

# fonts: dict mapping font roles to font names — keys: 'regular', 'bold', 'mono'
#        (e.g. {"mono": "JetBrainsMono"})
# classes: dict mapping markdown elements to CSS classes — keys: 'paragraph',
#          'heading_1', 'heading_2', 'heading_3', 'heading_n', 'code_block',
#          'code_inline', 'list_item', 'blockquote', 'divider', 'inline_row',
#          'bold', 'text_span' (e.g. {"heading_1": "custom_heading"})
```

The underlying function `render_markdown()` is also available with the same parameters:
```python
from puree.markdown import render_markdown
render_markdown(container, markdown_text, fonts=None, classes=None)
```

**Supported Markdown:**

| Syntax | Rendering |
|---|---|
| `**bold**` / `__bold__` | Bold font variant |
| `` `inline code` `` | Monospace font + background |
| ```` ```code block``` ```` | Child container with dark bg, monospace font |
| `# Heading` | Larger font size, bold (h1–h6) |
| `- list item` / `* list item` | Indented text with bullet prefix |
| `> blockquote` | Left border accent + indented text |
| `---` | Horizontal divider container |

**Not supported:** italics, links, images, tables, and nested lists.

Each rendered block gets a default CSS class (`.md_paragraph`, `.md_h1`, `.md_code_block`, etc. — see `puree/components/defaults/markdown_defaults.scss`). Override the styling by targeting those classes in your SCSS, or remap elements to your own classes via the `classes` parameter.

### Virtual Scrolling — `puree.virtual_scroll`

Efficient rendering for long lists. Only visible items are rendered; off-screen items are recycled.

```yaml
messages_scroll:
  style: scroll_area
  virtual: true
  item_height: 60          # fixed px, or omit for 'auto'
```

```python
scroll = app.theme.root.messages_scroll
scroll.set_virtual_data(messages_list)
scroll.set_item_renderer(render_message)
scroll.mark_dirty()

def render_message(container, item, index):
    container.text = item["text"]
    container.mark_dirty()
```

The renderer callback receives `(container, item, index)` — the recycled item container, the data entry, and its index in the data list.

### Collapse / Expand — `puree.collapse`

Collapse/expand for disclosure sections. The state change is instant (not animated).

```yaml
tool_details:
  style: collapsible
  collapsed: true
  tool_header:
    text: "Details"
  tool_body:
    style: collapsible_body
    text: "Hidden content"
```

```python
details = app.theme.root.tool_details
details.toggle_collapse()   # instant expand/collapse
details.mark_dirty()

# Or explicitly:
details.collapse()
details.expand()
```

The first child acts as the header and is always visible; the remaining children are hidden while collapsed.

### Console — `puree.console`

Browser-style logging that surfaces in Blender. Messages appear in the debug panel's **Console** tab (N-panel → puree) and are mirrored to `logs/puree.log`.

```python
console.log("value:", value)     # general output
console.info("loaded 42 items")  # informational
console.warn("slow response")    # warning
console.error("request failed")  # error
console.clear()                  # clear the console tab
```

The `console` object is **auto-injected as a global into your theme scripts** — no import needed. Outside theme scripts, import it with `from puree import console`. The console keeps the most recent 500 messages.

---

|  | Previous Page | Next Page |
|----------|----------|------|
| Puree is under active development. APIs may change between versions. **Special thanks to the open-source community and the developers behind the projects that make puree possible.** | [Components](COMPONENTS.md) | [Puree Specification](PUREE_SPEC.md) |