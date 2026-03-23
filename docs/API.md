---
layout: page
title : 3. API Reference
---

## Style Properties

The `Style` class defines the visual appearance and layout behavior of UI nodes. All properties are set via CSS/SCSS — do not modify `Style` fields directly. Use `container.set_property('css-property', value)` for runtime changes.

### Colors & Backgrounds

| Property | CSS Equivalent | Description |
|----------|---------------|-------------|
| `background_color` | `background-color` | Fill color (RGBA) |
| `background_color_2` | *(internal)* | 2nd gradient stop — set via `background: linear-gradient()` |
| `background_gradient_rot` | *(internal)* | Gradient angle — set via `background: linear-gradient()` |
| `gradient_stops` | *(internal)* | Multi-stop gradient — set via `background: linear-gradient()` |
| `hover_background_color` | `:hover { background-color }` | Hover fill color |
| `hover_background_color_2` | *(internal)* | Hover gradient 2nd stop |
| `hover_background_gradient_rot` | *(internal)* | Hover gradient angle |
| `hover_gradient_stops` | *(internal)* | Hover multi-stop gradient |
| `click_background_color` | `:active { background-color }` | Click fill color |
| `click_background_color_2` | *(internal)* | Click gradient 2nd stop |
| `click_background_gradient_rot` | *(internal)* | Click gradient angle |
| `click_gradient_stops` | *(internal)* | Click multi-stop gradient |
| `color` | `color` | Text color (RGBA, inherited) |
| `hover_color` | `:hover { color }` | Hover text color |
| `click_color` | `:active { color }` | Click text color |
| `opacity` | `opacity` | Element opacity (0–1) |
| `hover_opacity` | `:hover { opacity }` | Hover opacity |
| `click_opacity` | `:active { opacity }` | Click opacity |

### Typography

| Property | CSS Equivalent | Description |
|----------|---------------|-------------|
| `font_size` | `font-size` | Text size in px |
| `font_family` | *(YAML `font:`)* | Font face name |
| `font_weight` | `font-weight` | `NORMAL`, `BOLD` |
| `font_style` | `font-style` | `NORMAL`, `ITALIC` |
| `text_align` | `text-align` | `LEFT`, `CENTER`, `RIGHT` |
| `text_align_v` | `--text-align-v` | `TOP`, `CENTER`, `BOTTOM` |
| `text_transform` | `text-transform` | `NONE`, `UPPERCASE`, `LOWERCASE`, `CAPITALIZE` |
| `text_decoration` | `text-decoration` | `NONE`, `UNDERLINE` |
| `text_overflow` | `text-overflow` | `CLIP`, `ELLIPSIS` |
| `white_space` | `white-space` | `NORMAL`, `NOWRAP` |
| `line_height` | `line-height` | Multiplier (unitless) |
| `letter_spacing` | `letter-spacing` | Spacing in px |
| `text_x` | `--text-x` | Horizontal text offset |
| `text_y` | `--text-y` | Vertical text offset |
| `text_shadow_color` | `text-shadow` | Shadow color |
| `text_shadow_offset_x` | `text-shadow` | Shadow X offset |
| `text_shadow_offset_y` | `text-shadow` | Shadow Y offset |
| `text_shadow_blur` | `text-shadow` | Shadow blur |

### Box Model

| Property | CSS Equivalent | Description |
|----------|---------------|-------------|
| `width` | `width` | Element width |
| `height` | `height` | Element height |
| `min_width` | `min-width` | Minimum width |
| `max_width` | `max-width` | Maximum width |
| `min_height` | `min-height` | Minimum height |
| `max_height` | `max-height` | Maximum height |
| `border_radius` | `border-radius` | All-corner radius |
| `border_radius_tl/tr/br/bl` | `border-*-*-radius` | Per-corner radii |
| `border_width` | `border-width` | Uniform border width |
| `border_width_top/right/bottom/left` | `border-*-width` | Per-side widths |
| `border_color` | `border-color` | Border color |
| `border_color_2` | *(internal)* | Border gradient 2nd stop — set via `border-image: linear-gradient()` |
| `border_gradient_rot` | *(internal)* | Border gradient angle — set via `border-image: linear-gradient()` |
| `hover_border_color` | `:hover { border-color }` | Hover border color |
| `click_border_color` | `:active { border-color }` | Click border color |
| `box_shadow_color` | `box-shadow` | Shadow color |
| `box_shadow_offset` | `box-shadow` | Shadow offset (x, y) |
| `box_shadow_blur` | `box-shadow` | Shadow blur |

### Layout

| Property | CSS Equivalent | Description |
|----------|---------------|-------------|
| `display` | `display` | `FLEX`, `GRID`, `BLOCK`, `NONE` |
| `position` | `position` | `RELATIVE`, `ABSOLUTE` |
| `top/right/bottom/left` | `top/right/bottom/left` | Position offsets |
| `overflow` | `overflow` | `VISIBLE`, `HIDDEN`, `SCROLL`, `AUTO` |
| `overflow_x` | `overflow-x` | Horizontal overflow |
| `overflow_y` | `overflow-y` | Vertical overflow |
| `box_sizing` | `box-sizing` | `CONTENT_BOX`, `BORDER_BOX` |
| `visibility` | `visibility` | `VISIBLE`, `HIDDEN` |
| `pointer_events` | `pointer-events` | `AUTO`, `NONE` |
| `z_index` | *(internal)* | Rendering layer |
| `align_items` | `align-items` | `START`, `END`, `CENTER`, `STRETCH`, `BASELINE` |
| `justify_items` | `justify-items` | `START`, `END`, `CENTER`, `STRETCH`, `BASELINE` |
| `align_self` | `align-self` | Per-item alignment override |
| `justify_self` | `justify-self` | Per-item justify override |
| `align_content` | `align-content` | `START`, `END`, `CENTER`, `STRETCH`, `SPACE_BETWEEN`, `SPACE_AROUND`, `SPACE_EVENLY` |
| `justify_content` | `justify-content` | Same values as `align-content` |
| `flex_direction` | `flex-direction` | `ROW`, `COLUMN`, `ROW_REVERSE`, `COLUMN_REVERSE` |
| `flex_wrap` | `flex-wrap` | `NO_WRAP`, `WRAP`, `WRAP_REVERSE` |
| `flex_grow` | `flex-grow` | Growth factor |
| `flex_shrink` | `flex-shrink` | Shrink factor |
| `flex_basis` | `flex-basis` | Base size |
| `gap` | `gap` | Gap between items |
| `row_gap` | `row-gap` | Row gap |
| `column_gap` | `column-gap` | Column gap |
| `grid_auto_flow` | `grid-auto-flow` | `ROW`, `COLUMN` |
| `grid_template_rows` | `grid-template-rows` | Row track sizes |
| `grid_template_columns` | `grid-template-columns` | Column track sizes |
| `grid_row` | `grid-row` | Row placement |
| `grid_column` | `grid-column` | Column placement |

### Image

| Property | CSS Equivalent | Description |
|----------|---------------|-------------|
| `img_align_h` | `--img-align-h` | `LEFT`, `CENTER`, `RIGHT` |
| `img_align_v` | `--img-align-v` | `TOP`, `CENTER`, `BOTTOM` |

### Transitions

| Property | CSS Equivalent | Description |
|----------|---------------|-------------|
| `transition_property` | `transition-property` | Animatable property name |
| `transition_duration` | `transition-duration` | Duration in seconds |
| `transition_timing_function` | `transition-timing-function` | `ease`, `linear`, `ease-in`, `ease-out`, `ease-in-out` |
| `transition_delay` | `transition-delay` | Delay in seconds |
| `transitions` | `transition: a, b, ...` | List of parsed transition dicts for multi-property |

---

## Container Properties

The `Container` class represents an individual UI node in the interface hierarchy.

| Property | Type | Description |
|----------|------|-------------|
| `id` | `str` | Unique identifier |
| `parent` | `Optional[Container]` | Reference to parent container |
| `children` | `Optional[List[Container]]` | List of child containers |
| `style` | `Style` | Resolved style object |
| `data` | `Optional[str]` | Custom data string |
| `img` | `Optional[str]` | Image asset name (no extension) |
| `text` | `Optional[str]` | Text content |
| `font` | `Optional[str]` | Font face name (no extension) |
| `click` | `List` | Click event handler list |
| `toggle` | `List` | Toggle event handler list |
| `scroll` | `List` | Scroll event handler list |
| `hover` | `List` | Hover-in event handler list |
| `hoverout` | `List` | Hover-out event handler list |
| `passive` | `bool` | Non-interactive (no hover/click) |
| `_toggle_value` | `bool` | Current toggle state |
| `_toggled` | `bool` | Whether currently toggled |
| `_clicked` | `bool` | Whether currently clicked |
| `_hovered` | `bool` | Whether currently hovered |
| `_scroll_value` | `float` | Current scroll position |
| `_dirty` | `bool` | Needs GPU sync — set `True` then call `mark_dirty()` |

> Properties prefixed with `_` are internal state — do not modify directly. Use `mark_dirty()` after any runtime property changes.

---

|  | Previous Page | Next Page |
|----------|----------|------|
| Puree is under active development. APIs may change between versions. **Special thanks to the open-source community and the developers behind the projects that make puree possible.** | [Components](COMPONENTS.md) | [Troubleshooting](TROUBLESHOOTING.md) |