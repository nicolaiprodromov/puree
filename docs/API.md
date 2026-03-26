---
layout: page
title : 3. API Reference
---

## CSS Properties

All properties are set via SCSS files. Use `container.set_property('css-property', value)` for runtime changes. Both kebab-case (`background-color`) and underscore (`background_color`) are accepted.

**Reading style at runtime:** Access via `container.style.field_name`. Enum values are UPPERCASE at runtime — e.g. `container.style.display` returns `'FLEX'` or `'NONE'`.

### Colors & Backgrounds

| CSS Property | Description |
|---|---|
| `background-color` | Fill color |
| `background` | Shorthand: solid color or `linear-gradient()` |
| `background-image` | Alias for `background: linear-gradient()` |
| `color` | Text color (inherited by children) |
| `opacity` | Element opacity (0–1) |
| `visibility` | `visible`, `hidden` (hidden keeps layout space) |

**Hover and active states** are set via standard SCSS pseudo-classes. Only these four properties are supported in `:hover` / `:active` rules (layout properties like width/padding are ignored):

| Pseudo-class | Animatable properties |
|---|---|
| `:hover { }` | `background-color`, `color`, `border-color`, `opacity` |
| `:active { }` | `background-color`, `color`, `border-color`, `opacity` |

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
| `text-decoration` | `none`, `underline` |
| `text-transform` | `none`, `uppercase`, `lowercase`, `capitalize` |
| `letter-spacing` | Character spacing in px |
| `line-height` | Unitless multiplier (e.g. `1.2`) |
| `white-space` | `normal` (wrap), `nowrap` |
| `text-overflow` | `clip`, `ellipsis` — requires `white-space: nowrap` |
| `text-shadow` | `offset-x offset-y blur color` — single shadow only |

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
| `pointer-events` | `auto`, `none` |
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
| `grid-auto-flow` | `row`, `column` |
| `grid-template-rows` / `grid-template-columns` | Explicit track sizes |
| `grid-auto-rows` / `grid-auto-columns` | Implicit track sizes |
| `grid-row` / `grid-column` | Item placement |

### Image (Extensions)

| CSS Property | Description |
|---|---|
| `--img-align-h` | Image horizontal alignment: `left`, `center`, `right` |
| `--img-align-v` | Image vertical alignment: `top`, `center`, `bottom` |

### Transitions

Only `background-color`, `color`, `border-color`, and `opacity` are animatable.

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
| `data` | `str` | Component reference string |
| `passive` | `bool` | If `True`, element ignores all interaction events |
| `style` | `Style` | Resolved style object — read via `container.style.property_name` |
| `click` | `List` | Click event handler list |
| `toggle` | `List` | Toggle event handler list |
| `scroll` | `List` | Scroll event handler list |
| `hover` | `List` | Hover-in event handler list |
| `hoverout` | `List` | Hover-out event handler list |
| `_toggled` | `bool` | Whether currently toggled (read-only) |
| `_clicked` | `bool` | Whether currently clicked (read-only) |
| `_hovered` | `bool` | Whether currently hovered (read-only) |
| `_toggle_value` | `bool` | Current toggle state value (read-only) |
| `_scroll_value` | `float` | Current scroll offset in px (read-only) |

---

## Container Methods

| Method | Description |
|---|---|
| `mark_dirty()` | Flags the container for GPU re-sync on the next frame. **Required** after any runtime property change. |
| `set_property(name, value)` | Set a CSS property at runtime. Accepts CSS names (`background-color`) or underscore equivalents. Handles color parsing, gradient parsing, and layout recalculation automatically. |
| `get_by_id(target_id)` | Search this subtree for a container by ID. Returns `Container` or `None`. |

---

|  | Previous Page | Next Page |
|----------|----------|------|
| Puree is under active development. APIs may change between versions. **Special thanks to the open-source community and the developers behind the projects that make puree possible.** | [Components](COMPONENTS.md) | [Puree Specification](PUREE_SPEC.md) |