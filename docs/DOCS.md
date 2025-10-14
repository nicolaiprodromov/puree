---
layout: page
title : Documentation
---

<img src="https://img.shields.io/badge/STATUS-BETA%20%7C%20WIP-ff6b6b?style=for-the-badge&logo=blender&logoColor=white" alt="Beta Status"/>
<br>
<img src="https://img.shields.io/badge/OpenGL%20Backend-ONLY-orange?style=flat-square" alt="OpenGL Only"/>
<img src="https://img.shields.io/badge/API-UNSTABLE-red?style=flat-square" alt="API Unstable"/>

The *XWZ Puree* framework for Blender is a declarative framework that provides a web-inspired API for building user interfaces, addressing the limitations of Blender's native UI system in supporting complex interface architectures and providing enhanced flexibility.

> Puree is built on top of **ModernGL**, **TinyCSS2**, and **Stretchable** to deliver a high-performance, GPU-accelerated UI engine with a familiar web development paradigm.

## Overview

1. [Installation](#installation)
2. [Getting Started](#getting-started)
    1. [Quick Start](#quick-start)
    2. [File Structure](#file-structure)
    3. [`index.yaml` breakdown](#indexyaml-breakdown)
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
3. [Component Template System](COMPONENTS.md)
4. [API Reference](API.md)
5. [Troubleshooting](Troubleshooting.md)

---

### Installation

There are 3 ways to start working with puree:

1. [Install with pip](#install-with-pip) and make your own app directory
2. [Download the latest release](#download-latest-release) and modify & rename the example files
3. [Clone this repo](#install-with-pip), install dependencies, build the addon, and work from there

#### Install with pip

Blender does not recommend installing dependencies with pip in the blender python context, so it's better to download the puree wheel and reference it in the blender manifest file of your addon. This way you will have to build the addon structure yourself from scratch.

```bash
pip download --only-binary=:all: --python-version 3.11 --dest wheels puree-ui
```

#### Download latest release

Go to Releases and download the archive. Unpack it, modify the files, build and install addon. `Edit > Preferences > Add-ons > Install from disk` or simply drag and drop the .zip file in Blender.

#### Clone the repo

1. Clone this repository.

    ```bash
    git clone https://github.com/nicolaiprodromov/puree
    ```

2. Install *Make or Just*, [Blender 4.x+](https://www.blender.org/download/), [Python 3.10+](https://www.python.org/downloads/) and the [Blender MCP Addon](https://github.com/XWZ/blender-mcp-addon) for the easiest development experience.

    - **Linux**:

        ```bash
        sudo apt update
        sudo apt install make

        sudo snap install --edge --classic just
        ```

    - **MacOS**:

        ```bash
        brew install make
        brew install just
        ```

    - **Windows**:

        ```powershell
        choco install make
        winget install --id Casey.Just
        ```

3. Run `just build_package` or `make build_package` to build the python package.
4. Run `just build` or `make build` to build the addon zip file.
    - You can also manually zip the folder.
5. Run `just install` or `make install` to install the addon in Blender.
    - Alternatively, run `just deploy` or `make deploy` to build package, and build and install addon in one step.
    - Or just install the zip file manually in Blender preferences: `Edit > Preferences > Add-ons > Install from disk`

---

### File Structure

The bare minimum file structure for a project is as follows: 

```
puree_project/
    ├── index.yaml
    ├── style.css
    ├── __init__.py <-- your addon entry point
```

---

#### `index.yaml` breakdown

The `index.yaml` file is the entry point for your UI definition, and it should contain the necessary configuration for your UI components, styles, and scripts. Think of it as the index.html of Puree. It is where you will define the hierarchy of your UI elements, their properties, theme, and settings.

Here is a basic example of what an `index.yaml` file might look like: 

```yaml
app:
  selected_theme: xwz_default
  default_theme: xwz_default
  theme:
    - name: xwz_default
      author: xwz
      version: 1.0.0
      styles:
        - static/style.css
      scripts:
        - static/script.py
      root:
        style: root
        bg:
          style: bg
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

<p align="center">
  <img src="images/munky.gif" width="100px" alt="Monkey GIF"/>
</p>

|  | Previous Page | Next Page |
|----------|----------|------|
| Puree is under active development. APIs may change between versions. **Special thanks to the open-source community and the developers behind the projects that make puree possible.** | [Home](index.md) | [Components](COMPONENTS.md) |

---
