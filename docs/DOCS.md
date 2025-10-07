> ## 🚧 **Puree 0.0.2 beta - WIP** 🚧
> *This project is currently under active development.*
> - Puree currently works **only** with Blender's OpenGL backend because of the ModernGL dependency.
> - The API is not stable and **breaking changes are expected** in future releases.

# Puree Documentation

The *XWZ Puree* framework for Blender is a declarative framework that provides a web-inspired API for building user interfaces, addressing the limitations of Blender's native UI system in supporting complex interface architectures and providing enhanced flexibility.

> Puree is built on top of **ModernGL**, **TinyCSS2**, and **Stretchable** to deliver a high-performance, GPU-accelerated UI engine with a familiar web development paradigm.

## Overview

1. [Installation](#installation)
2. [Getting Started](#getting-started)
3. [API Reference](#api-reference)
    1. [Style Properties](#style-properties)
    2. [Container Properties](#container-properties)
4. [Troubleshooting](#troubleshooting)

---

### Installation

1. Download the [latest release](https://github.com/XWZ/Puree/releases/latest) and extract it or clone this repository.
2. Run `make build` to build the addon zip file.
    - You need Blender 4.x+ installed.
    - You need *Python 3.10+* installed on your system.
    - You need *make* installed on your system.
    - You can also manually zip the folder.
3. Run `make install` to install the addon in Blender.
    - To run `install` command you must install the [Blender MCP Addon](https://github.com/XWZ/blender-mcp-addon) in Blender and connect to the server.
    - Alternatively, run `make deploy` to build and install in one step.
    - Or just install the zip file manually in Blender preferences: Edit > Preferences > Add-ons > Install from disk

---

### Getting Started

The bare minimum file structure for a project is as follows: 

```
puree_project/
    ├── index.toml
    ├── style.css
    ├── __init__.py <-- your addon entry point
```

---

#### `index.toml` breakdown

The `index.toml` file is the entry point for your UI definition, and it should contain the necessary configuration for your UI components, styles, and scripts. Think of it as the index.html of Puree. It is where you will define the hierarchy of your UI elements, their properties, theme, and settings.

Here is a basic example of what an `index.toml` file might look like: 

```toml
[app]
    selected_theme = "xwz_default"
    default_theme  = "xwz_default"
[[app.theme]]
    name    = "xwz_default"
    author  = "xwz"
    version = "1.0.0"
    styles  = ["static/style.css"]
    scripts = ["static/script.py"]
    [app.theme.root]
        style = "root"
        [app.theme.root.bg]
            style = "bg"
```
##### App structure

The `app` section defines the application settings, including the selected and default themes. The `theme` section allows you to define multiple layouts, each with its own styles and scripts.

The equivalent of the `body` tag in HTML is the `root` node in Puree. The elements inside the root of the app are called **nodes**.

> Nodes are the building blocks of your UI, and they can represent various UI components such as buttons, panels, text fields, images, etc.

The `root` section contains the nodes that define the hierarchy and properties of your interface. You must nest other nodes within the root nto create your interface.

Each node can have its own properties, styles, and child nodes. In the example above, the `bg` node is a child of the `root` node, and it has its own style defined in the `style.css` file.

You can also draw images and text by changing the `img` and `text` properties. The images must be stored in a `assets/` folder in the root of your project. Fonts must be stored in a `fonts/` folder in the root of your project.

You can also add custom scripts to your theme. The scripts must be stored in the `static/` folder in the root of your project and then linked in the `scripts` array of your theme.

A more complete file structure would look like this: 

```
puree_project/
    ├── assets/
    │   ├── your images
    ├── fonts/
    │   ├── your fonts
    ├── static/
    │   ├── index.toml
    │   └── style.css
    │   └── script.py
    ├── __init__.py <-- your addon entry point
```

---

#### `style.css` breakdown

You can define custom styles for your app using a CSS-like syntax to specify styles for your app's nodes.

Puree does not implement the full CSS specification, but does implement some new features specific to the framework. 

>For more details and the list of supported properties, refer to the [API Reference](#api-reference).

> *Ultimately, the point is not to replicate CSS, but to provide a familiar syntax for defining styles in a way that is easy to read and write.*

Here is an example of what a `style.css` file might look like: 

```css
root {
    width          : 100%;
    height         : 100%;
    display        : flex;
    flex-direction : column;
    align-items    : center;
    justify-content: center;
    color          : #f0f0f0;
}

bg {
    position: absolute;
    top     : 0;
    left    : 0;
    width   : 100%;
    height  : 100%;
    color   : #e0e0e0;
    z-index : -1;
}
```

#### `script.py` breakdown

You can add custom Python scripts to your theme to handle events and add interactivity to your UI. The scripts must be stored in the `static/` folder in the root of your project and then linked in the `scripts` array of your theme.


```python
def main(self, app): 
    def text_func(container): 
        print("Button Clicked!")

    app.theme.root.children[0].click.append(text_func)
    return app
```

The `main` function is the entry point for your script, and it receives the `app` object as an argument. You can use this object to access and manipulate your UI components.

---

### API Reference

#### Style Properties

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
| `box_shadow_offset` | `List[float]` | Shadow offset (x, y, z) |
| `box_shadow_blur` | `float` | Shadow blur radius |
| `background_image` | `Optional[str]` | Path to background image |
| `background_size` | `str` | Background sizing: `AUTO`, `COVER`, `CONTAIN` |
| `background_position` | `List[float]` | Background position (x, y) |
| `background_repeat` | `str` | Background repeat: `REPEAT`, `NO_REPEAT`, `REPEAT_X`, `REPEAT_Y` |
| `display` | `str` | Display mode               : `NONE`,   `FLEX`,      `GRID`,     `BLOCK` |
| `overflow` | `str` | Overflow behavior |
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

#### Container Properties

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

> **Note:** Properties prefixed with `_` are internal state properties used by the framework for tracking user interactions and should generally not be modified directly by user code.


### Troubleshooting

- *"Failed to get ModernGL context: libGL.so: cannot open shared object file: No such file or directory*" - `sudo apt install libgl1-mesa-dev`
- *"Can't get over 30fps on linux"* - `__GL_SYNC_TO_VBLANK=0 blender` (start blender from terminal without vsync)