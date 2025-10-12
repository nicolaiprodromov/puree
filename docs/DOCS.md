> ### 🚧 **Puree 0.0.2 beta - WIP** 🚧
> - Puree currently works **only** with Blender's OpenGL backend because of the ModernGL dependency.
> - The API is not stable and **breaking changes are expected** in future releases.

# Puree Documentation

The *XWZ Puree* framework for Blender is a declarative framework that provides a web-inspired API for building user interfaces, addressing the limitations of Blender's native UI system in supporting complex interface architectures and providing enhanced flexibility.

> Puree is built on top of **ModernGL**, **TinyCSS2**, and **Stretchable** to deliver a high-performance, GPU-accelerated UI engine with a familiar web development paradigm.

## Overview

1. [Installation](#installation)
2. [Getting Started](#getting-started)
    1. [Quick Start](#quick-start)
    2. [File Structure](#file-structure)
    3. [`index.toml` breakdown](#indextoml-breakdown)
        - [App structure](#app-structure)
    4. [`style.css` breakdown](#stylecss-breakdown)
        - [CSS Custom Properties (Variables)](#css-custom-properties-variables)
        - [Color Space Conversion](#color-space-conversion)
    5. [`script.py` breakdown](#scriptpy-breakdown)
        - [Basic Structure](#basic-structure)
        - [Event Handlers](#event-handlers)
        - [Modifying Container Properties](#modifying-container-properties)
        - [Accessing Container Hierarchy](#accessing-container-hierarchy)
        - [Multiple Event Handlers](#multiple-event-handlers)
        - [State Management](#state-management)
        - [Integrating with Blender](#integrating-with-blender)
        - [Best Practices](#best-practices)
3. [Component Template System](#component-template-system)
    1. [Overview](#overview-1)
    2. [Creating Components](#creating-components)
    3. [Parameter Syntax](#parameter-syntax)
    4. [Using Components](#using-components)
    5. [Component Namespacing](#component-namespacing)
    6. [Accessing Component Instances in Scripts](#accessing-component-instances-in-scripts)
    7. [Best Practices](#best-practices-1)
    8. [Complete Example](#complete-example)
4. [API Reference](#api-reference)
    1. [Style Properties](#style-properties)
    2. [Container Properties](#container-properties)
5. [Troubleshooting](#troubleshooting)

---

### Installation

Install Make or Just, [Blender 4.x+](https://www.blender.org/download/), and the [Blender MCP Addon](https://github.com/XWZ/blender-mcp-addon) for the easiest development experience.
```bash
# install make or just
# windows
choco install make
# linux
winget install --id Casey.Just

```

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

### File Structure

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
    
    /* CSS Custom Properties (Variables) */
    --bg_col       : #121212;
    --header_col   : #f64720;
    --text_col     : #FFFFFF;
    --accent_col   : #fafc86;
    --border_radii : 28px;
}

bg {
    width           : 500px;
    height          : 500px;
    background-color: var(--bg_col);      /* Using CSS variable */
    border-radius   : var(--border_radii);
}
```

##### CSS Custom Properties (Variables)

Puree supports CSS custom properties (variables) for maintaining consistent theming:

**Defining Variables:**
```css
root {
    --primary-color: #3498db;
    --spacing-unit : 10px;
    --border-radius: 8px;
}
```

**Using Variables:**
```css
button {
    background-color: var(--primary-color);
    padding         : var(--spacing-unit);
    border-radius   : var(--border-radius);
}
```

Variables are resolved at parse time and support nesting. Define variables in the `root` selector for global access.

##### Color Space Conversion

> **Important:** Puree automatically converts CSS colors from sRGB color space to linear color space for accurate rendering in Blender's viewport.

When you specify colors in CSS using hex codes, `rgba()`, or named colors, they are automatically converted from sRGB (standard for displays and CSS) to linear color space (used by Blender's rendering engine). This ensures colors appear as expected and lighting calculations are physically accurate.

**Example:**
```css
button {
    background-color: #ff6600;  /* Specified in sRGB */
    /* Automatically converted to linear for GPU rendering */
}
```

You don't need to do anything special—just use standard CSS color formats and the conversion happens automatically.

#### `script.py` breakdown

You can add custom Python scripts to your theme to handle events and add interactivity to your UI. The scripts must be stored in the `static/` folder in the root of your project and then linked in the `scripts` array of your theme.

##### Basic Structure

The `main` function is the entry point for your script and receives two arguments:
- `self` - The compiler instance
- `app` - The UI application object

You must return the `app` object at the end.

```python
def main(self, app): 
    # Your script logic here
    return app
```

##### Event Handlers

Puree supports several event types that you can attach to containers:

**1. Click Events**

Triggered when a user clicks on a container:

```python
def main(self, app):
    button = app.theme.root.bg.my_button
    
    def on_button_click(container):
        print(f"Button {container.id} was clicked!")
    
    button.click.append(on_button_click)
    return app
```

**2. Hover Events**

Triggered when the mouse enters or leaves a container:

```python
def main(self, app):
    card = app.theme.root.bg.card
    
    def on_hover(container):
        print(f"Mouse entered {container.id}")
    
    def on_hover_out(container):
        print(f"Mouse left {container.id}")
    
    card.hover.append(on_hover)
    card.hoverout.append(on_hover_out)
    return app
```

**3. Toggle Events**

For buttons that maintain on/off state:

```python
def main(self, app):
    toggle_btn = app.theme.root.bg.toggle_button
    
    def on_toggle(container):
        if container._toggle_value:
            print("Toggle is ON")
        else:
            print("Toggle is OFF")
    
    toggle_btn.toggle.append(on_toggle)
    return app
```

**4. Scroll Events**

Triggered when scrolling within a scrollable container:

```python
def main(self, app):
    scrollable = app.theme.root.bg.scroll_area
    
    def on_scroll(container):
        print(f"Scroll position: {container._scroll_value}")
    
    scrollable.scroll.append(on_scroll)
    return app
```

##### Modifying Container Properties

You can dynamically change container properties at runtime:

**Changing Text Content:**

```python
def main(self, app):
    label = app.theme.root.bg.label
    counter = [0]  # Use list to maintain state across function calls
    
    def increment_counter(container):
        counter[0] += 1
        label.text = f"Count: {counter[0]}"
        label.mark_dirty()  # Signal that GPU sync is needed
    
    button = app.theme.root.bg.increment_btn
    button.click.append(increment_counter)
    
    return app
```

**Showing/Hiding Elements:**

```python
def main(self, app):
    modal = app.theme.root.bg.modal
    open_btn = app.theme.root.bg.open_modal_btn
    close_btn = app.theme.root.bg.modal.close_btn
    
    def show_modal(container):
        modal.style.display = 'FLEX'
        modal.mark_dirty()
    
    def hide_modal(container):
        modal.style.display = 'NONE'
        modal.mark_dirty()
    
    open_btn.click.append(show_modal)
    close_btn.click.append(hide_modal)
    
    return app
```

##### Accessing Container Hierarchy

Use dot notation to access containers by their ID:

```python
def main(self, app):
    # Direct access by ID
    header = app.theme.root.header
    button = app.theme.root.bg.body.buttons.submit_btn
    
    # Access component children (with namespace)
    card_title = app.theme.root.bg.my_card_header
    
    # Iterate through children
    buttons_container = app.theme.root.bg.buttons
    for child in buttons_container.children:
        print(f"Found button: {child.id}")
    
    return app
```

##### Multiple Event Handlers

You can attach multiple handlers to the same event:

```python
def main(self, app):
    button = app.theme.root.bg.multi_action_btn
    
    def log_click(container):
        print("Action logged")
    
    def update_ui(container):
        print("UI updated")
    
    def play_sound(container):
        print("Sound played")
    
    # All three handlers will be called in order
    button.click.append(log_click)
    button.click.append(update_ui)
    button.click.append(play_sound)
    
    return app
```

##### State Management

Manage application state using closures or external variables:

```python
def main(self, app):
    # Application state
    state = {
        'selected_item': None,
        'is_editing': False,
        'items': []
    }
    
    def select_item(container):
        state['selected_item'] = container.id
        print(f"Selected: {state['selected_item']}")
    
    def toggle_edit_mode(container):
        state['is_editing'] = not state['is_editing']
        edit_label = app.theme.root.bg.edit_status
        edit_label.text = "Editing" if state['is_editing'] else "Viewing"
        edit_label.mark_dirty()
    
    # Attach handlers
    item1 = app.theme.root.bg.item1
    item2 = app.theme.root.bg.item2
    edit_btn = app.theme.root.bg.edit_toggle
    
    item1.click.append(select_item)
    item2.click.append(select_item)
    edit_btn.click.append(toggle_edit_mode)
    
    return app
```

##### Integrating with Blender

Access Blender's API within your event handlers:

```python
import bpy

def main(self, app):
    add_cube_btn = app.theme.root.bg.add_cube
    status_label = app.theme.root.bg.status
    
    def add_cube(container):
        bpy.ops.mesh.primitive_cube_add()
        cube_count = len([obj for obj in bpy.data.objects if obj.type == 'MESH'])
        status_label.text = f"Cubes: {cube_count}"
        status_label.mark_dirty()
    
    def delete_selected(container):
        bpy.ops.object.delete()
        status_label.text = "Deleted selected objects"
        status_label.mark_dirty()
    
    delete_btn = app.theme.root.bg.delete_btn
    
    add_cube_btn.click.append(add_cube)
    delete_btn.click.append(delete_selected)
    
    return app
```

##### Best Practices

1. **Always return the app object** at the end of `main()`
2. **Call `mark_dirty()`** after modifying container properties to trigger GPU sync
3. **Use descriptive function names** for event handlers
4. **Keep handlers focused** - each handler should do one thing well
5. **Handle errors gracefully** - wrap Blender operations in try-except blocks
6. **Use property-based access** - `app.theme.root.bg.button` instead of array indexing

---

## Component Template System

Puree includes a powerful component template system that allows you to create reusable UI components with parameterization. This feature promotes code reuse, maintains consistency, and simplifies complex UI structures.

### Overview

Component templates are defined as separate `.toml` files and can be instantiated multiple times throughout your UI with different parameters. Think of them as reusable UI "blueprints" similar to React components or Vue templates.

### Creating Components

#### 1. Component Directory Structure

Components are stored in a dedicated directory specified in your theme configuration:

```toml
[[app.theme]]
    name       = "xwz_default"
    components = "static/components/"  # Path to components directory
```

Your project structure should look like:

```
puree_project/
    ├── static/
    │   ├── components/
    │   │   ├── header.toml       # Component definition
    │   │   ├── test_button.toml  # Component definition
    │   │   └── card.toml         # Component definition
    │   ├── index.toml
    │   └── style.css
    └── __init__.py
```

#### 2. Component Definition

Create a `.toml` file in your components directory. The component must have a single root key that matches the filename (without extension):

**Example: `test_button.toml`**

```toml
[test_button]
    style = "{{tb_style, 'hover_test'}}"
    [test_button.tb_text]
        style   = "{{tb_text_style, 'ht_text'}}"
        text    = "{{tb_text, 'Click Me'}}"
        passive = true
```

**Example: `header.toml`**

```toml
[header]
    style = "header"
    [header.text_box]
        style = "header_text_box"
        [header.text_box.text]
            style = "header_text"
            text  = "{{title, 'Puree UI Kit'}}"
            font  = "NeueMontreal-Bold"
        [header.text_box.subtitle]
            style = "header_text1"
            text  = "{{subtitle, 'Declarative UI for Blender'}}"
            font  = "NeueMontreal-Italic"
    [header.logo]
        style = "header_logo"
        img   = "loggoui2"
```

### Parameter Syntax

Component parameters use a special syntax: `{{parameter_name, 'default_value'}}`

- **`parameter_name`**: The name of the parameter that can be passed when instantiating the component
- **`default_value`**: The fallback value if no parameter is provided (must be in quotes)

**Format:**
```toml
property = "{{param_name, 'default value'}}"
```

**Examples:**
```toml
text  = "{{button_text, 'Submit'}}"      # Text parameter with default
style = "{{button_style, 'default'}}"     # Style parameter with default
img   = "{{icon_name, 'icon_default'}}"  # Image parameter with default
```

### Using Components

#### 1. Reference Components in Your UI

To use a component, set the `data` property to the component reference in square brackets:

```toml
[app.theme.root.my_container.my_button]
    data = "[test_button]"  # References test_button.toml
```

#### 2. Pass Parameters to Components

You can customize component instances by passing parameters as properties:

```toml
[app.theme.root.bg.body.buttons.hover_button]
    data          = "[test_button]"
    tb_text_style = "ht_text"
    tb_style      = "hover_test"
    tb_text       = "Hover me!"

[app.theme.root.bg.body.buttons.click_button]
    data          = "[test_button]"
    tb_text_style = "ct_text"
    tb_style      = "click_test"
    tb_text       = "Click me!"
```

In this example:
- Both buttons use the same `test_button` component template
- Each instance receives different parameter values
- The component's `{{tb_text, ''}}` parameter gets replaced with "Hover me!" and "Click me!" respectively

#### 3. Component Instance with Multiple Parameters

**Component Definition (`header.toml`):**
```toml
[header]
    style = "header"
    [header.title]
        text = "{{title, 'Default Title'}}"
    [header.subtitle]
        text = "{{subtitle, 'Default Subtitle'}}"
```

**Usage in `index.toml`:**
```toml
[app.theme.root.page.top_header]
    data     = "[header]"
    title    = "Welcome to Puree"
    subtitle = "Build UIs with ease"
```

### Component Namespacing

To prevent ID collisions when multiple instances of the same component exist, Puree automatically namespaces child elements:

**Component Definition:**
```toml
[button]
    [button.icon]
        [button.icon.label]
```

**When instantiated as `my_button`:**
```
my_button
  └── my_button_icon
      └── my_button_icon_label
```

This means each component instance has unique IDs throughout the node tree, using underscore (`_`) as a separator.

### Accessing Component Instances in Scripts

Puree provides an intuitive property-based access system for navigating the container hierarchy. Instead of traversing arrays of children, you can access containers by their ID using dot notation.

#### Property-Based Access

```python
def main(self, app):
    # Access containers by ID using dot notation
    # This is much cleaner than: app.theme.root.children[0].children[1]
    hover_button = app.theme.root.bg.body.buttons.hover_button
    
    # Access nested children (with namespace)
    button_text = app.theme.root.bg.body.buttons.hover_button_tb_text
    
    # Attach event handlers
    def on_click(container):
        print("Button clicked!")
    
    hover_button.click.append(on_click)
    
    return app
```

#### How It Works

The `Container` class implements a custom `__getattr__` method that:
1. Searches through the container's children
2. Finds a child whose `id` matches the requested attribute name
3. Returns that child container

**Example:**
```python
# These are equivalent:
button = app.theme.root.bg.my_button

# Is the same as finding the child manually:
button = None
for child in app.theme.root.bg.children:
    if child.id == "my_button":
        button = child
        break
```

This makes your script code much more readable and maintainable, especially when working with deeply nested UI structures.

### Best Practices

1. **Keep Components Focused**: Each component should represent a single, reusable UI pattern
2. **Use Meaningful Parameter Names**: Choose descriptive names like `button_text` rather than `txt`
3. **Provide Sensible Defaults**: Always include default values that make sense
4. **Document Your Components**: Add comments in component files explaining parameters
5. **Style Separation**: Define component-specific styles in your CSS file, pass style names as parameters
6. **Avoid Deep Nesting**: Keep component hierarchies shallow for better maintainability

### Complete Example

**File: `static/components/card.toml`**
```toml
[card]
    style = "{{card_style, 'default_card'}}"
    [card.header]
        style = "card_header"
        text  = "{{card_title, 'Title'}}"
    [card.body]
        style = "card_body"
        text  = "{{card_content, 'Content'}}"
    [card.footer]
        style = "card_footer"
        [card.footer.button]
            style = "card_button"
            text  = "{{action_text, 'Action'}}"
```

**File: `static/style.css`**
```css
default_card {
    width: 300px;
    height: 400px;
    background-color: #ffffff;
    border-radius: 8px;
    padding: 20px;
}

card_header {
    text-scale: 24px;
    text-color: #333333;
}

card_body {
    text-scale: 16px;
    text-color: #666666;
}
```

**File: `static/index.toml`**
```toml
[app.theme.root.dashboard.product_card]
    data         = "[card]"
    card_style   = "product_card_style"
    card_title   = "Product Name"
    card_content = "Product description goes here"
    action_text  = "Buy Now"

[app.theme.root.dashboard.profile_card]
    data         = "[card]"
    card_title   = "User Profile"
    card_content = "User bio and information"
    action_text  = "Edit Profile"
```

This creates two different cards from the same template with different content and styling.

---

## API Reference

### Style Properties

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

### Container Properties

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

> **Note:** Properties prefixed with `_` are internal state properties used by the framework for tracking user interactions and should generally not be modified directly by user code.

---

### Troubleshooting

- *"Failed to get ModernGL context: libGL.so: cannot open shared object file: No such file or directory*" - `sudo apt install libgl1-mesa-dev`
- *"Can't get over 30fps on linux"* - `__GL_SYNC_TO_VBLANK=0 blender` (start blender from terminal without vsync)