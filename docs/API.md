---
layout: page
title : API Reference
---

## Style Properties

The `Style` class defines the visual appearance and layout behavior of UI nodes. Below is a comprehensive list of all available properties: 

| Property | Type | Description |
|----------|------|-------------|
| `id` | `str` | Unique identifier for the style |
| `width` | `float` | Width of the element |
| `height` | `float` | Height of the element |
| `color` | `List[float]` | Background color (RGBA) |
| `color_1` | `List[float]` | Secondary color for gradient (RGBA) |
| `color_gradient_rot` | `float` | Gradient rotation angle |
| `hover_color` | `List[float]` | Background color on hover (RGBA) |
| `hover_color_1` | `List[float]` | Secondary hover color for gradient (RGBA) |
| `hover_color_gradient_rot` | `float` | Hover gradient rotation angle |
| `click_color` | `List[float]` | Background color on click (RGBA) |
| `click_color_1` | `List[float]` | Secondary click color for gradient (RGBA) |
| `click_color_gradient_rot` | `float` | Click gradient rotation angle |
| `text_x` | `float` | Text horizontal offset |
| `text_y` | `float` | Text vertical offset |
| `text_scale` | `float` | Text font size |
| `text_color` | `List[float]` | Text color (RGBA) |
| `text_color_1` | `List[float]` | Secondary text color for gradient (RGBA) |
| `text_color_gradient_rot` | `float` | Text gradient rotation angle |
| `border_radius` | `float` | Corner radius for rounded borders |
| `border_width` | `float` | Width of the border |
| `border_color` | `List[float]` | Border color (RGBA) |
| `border_color_1` | `List[float]` | Secondary border color for gradient (RGBA) |
| `border_color_gradient_rot` | `float` | Border gradient rotation angle |
| `box_shadow_color` | `List[float]` | Shadow color (RGBA) |
| `box_shadow_offset` | `List[float]` | Shadow offset (x, y) in pixels |
| `box_shadow_blur` | `float` | Shadow blur radius |
| `toggle_color` | `List[float]` | Background color when toggled (RGBA) |
| `toggle_color_1` | `List[float]` | Secondary toggle color for gradient (RGBA) |
| `toggle_color_gradient_rot` | `float` | Toggle gradient rotation angle |
| `text_align_h` | `str` | Horizontal text alignment: `LEFT`, `CENTER`, `RIGHT` |
| `text_align_v` | `str` | Vertical text alignment: `TOP`, `CENTER`, `BOTTOM` |
| `padding` | `str` | Padding (shorthand CSS-style: "10px", "10px 20px", etc.) |
| `padding_top` | `str` | Top padding |
| `padding_right` | `str` | Right padding |
| `padding_bottom` | `str` | Bottom padding |
| `padding_left` | `str` | Left padding |
| `margin` | `str` | Margin (shorthand CSS-style: "10px", "10px 20px", etc.) |
| `margin_top` | `str` | Top margin |
| `margin_right` | `str` | Right margin |
| `margin_bottom` | `str` | Bottom margin |
| `margin_left` | `str` | Left margin |
| `border` | `str` | Border shorthand (e.g., "2px #ff0000") |
| `background_image` | `Optional[str]` | Path to background image |
| `background_size` | `str` | Background sizing: `AUTO`, `COVER`, `CONTAIN` |
| `background_position` | `List[float]` | Background position (x, y) |
| `background_repeat` | `str` | Background repeat: `REPEAT`, `NO_REPEAT`, `REPEAT_X`, `REPEAT_Y` |
| `display` | `str` | Display mode               : `NONE`,   `FLEX`,      `GRID`,     `BLOCK` |
| `overflow` | `str` | Overflow behavior: `HIDDEN`, `VISIBLE` |
| `scrollbar_width` | `float` | Width of scrollbar |
| `position` | `str` | Position mode         : `RELATIVE`, `ABSOLUTE` |
| `align_items` | `str` | Align items        : `START`,    `END`, `FLEX_START`, `FLEX_END`, `CENTER`, `BASELINE`, `STRETCH` |
| `justify_items` | `str` | Justify items    : `START`,    `END`, `FLEX_START`, `FLEX_END`, `CENTER`, `BASELINE`, `STRETCH` |
| `align_self` | `str` | Align self          : `START`,    `END`, `FLEX_START`, `FLEX_END`, `CENTER`, `BASELINE`, `STRETCH` |
| `justify_self` | `str` | Justify self      : `START`,    `END`, `FLEX_START`, `FLEX_END`, `CENTER`, `BASELINE`, `STRETCH` |
| `align_content` | `str` | Align content    : `START`,    `END`, `FLEX_START`, `FLEX_END`, `CENTER`, `STRETCH`,  `SPACE_BETWEEN`, `SPACE_EVENLY`, `SPACE_AROUND` |
| `justify_content` | `str` | Justify content: `START`,    `END`, `FLEX_START`, `FLEX_END`, `CENTER`, `STRETCH`,  `SPACE_BETWEEN`, `SPACE_EVENLY`, `SPACE_AROUND` |
| `size` | `List[float]` | Size (width, height) |
| `min_size` | `List[float]` | Minimum size (width, height) |
| `max_size` | `List[float]` | Maximum size (width, height) |
| `aspect_ratio` | `bool` | Maintain aspect ratio |
| `flex_wrap` | `str` | Flex wrap          : `NO_WRAP`, `WRAP`,   `WRAP_REVERSE` |
| `flex_direction` | `str` | Flex direction: `ROW`,     `COLUMN`, `ROW_REVERSE`, `COLUMN_REVERSE` |
| `flex_grow` | `float` | Flex grow factor |
| `flex_shrink` | `float` | Flex shrink factor |
| `flex_basis` | `float` | Flex basis size |
| `grid_auto_flow` | `str` | Grid auto flow: `ROW`, `COLUMN`, `ROW_DENSE`, `COLUMN_DENSE` |
| `grid_template_rows` | `Optional[List]` | Grid template rows definition |
| `grid_template_columns` | `Optional[List]` | Grid template columns definition |
| `grid_auto_rows` | `Optional[List]` | Grid auto rows definition |
| `grid_auto_columns` | `Optional[List]` | Grid auto columns definition |
| `grid_row` | `str` | Grid row placement |
| `grid_column` | `str` | Grid column placement |

---

## Container Properties

The `Container` class represents an individual UI node/element in the interface hierarchy. Below is a comprehensive list of all available properties: 

| Property | Type | Description |
|----------|------|-------------|
| `id` | `str` | Unique identifier for the container |
| `parent` | `Optional[Container]` | Reference to parent container |
| `children` | `Optional[List[Container]]` | List of child containers |
| `style` | `Optional[str]` | Reference to style definition |
| `data` | `Optional[str]` | Custom data attached to container |
| `img` | `Optional[str]` | Path to image to display in container |
| `text` | `Optional[str]` | Text content to display |
| `font` | `Optional[str]` | Font family for text rendering |
| `click` | `List` | List of click event handlers |
| `toggle` | `List` | List of toggle event handlers |
| `scroll` | `List` | List of scroll event handlers |
| `hover` | `List` | List of hover event handlers |
| `hoverout` | `List` | List of hover-out event handlers |
| `_toggle_value` | `bool` | Current toggle state value |
| `_toggled` | `bool` | Whether element is currently toggled |
| `_clicked` | `bool` | Whether element is currently clicked |
| `_hovered` | `bool` | Whether element is currently hovered |
| `_prev_toggled` | `bool` | Previous toggle state for state tracking |
| `_prev_clicked` | `bool` | Previous click state for state tracking |
| `_prev_hovered` | `bool` | Previous hover state for state tracking |
| `_scroll_value` | `float` | Current scroll position value |
| `_dirty` | `bool` | Whether container state has changed and needs GPU sync |
| `passive` | `bool` | Whether the container is passive (non-interactive) |
| `layer` | `int` | Z-index/rendering layer for the container |

> Properties prefixed with `_` are internal state properties used by the framework for tracking user interactions and should generally not be modified directly by user code.

---

|  | Previous Page | Next Page |
|----------|----------|------|
| Puree is under active development. APIs may change between versions. **Special thanks to the open-source community and the developers behind the projects that make puree possible.** | [Components](COMPONENTS.md) | [Troubleshooting](TROUBLESHOOTING.md) |

---
