---
layout: page
title : 1. Documentation
---

<img src="https://img.shields.io/badge/OpenGL%20Backend-ONLY-orange?style=flat-square" alt="OpenGL Only"/>
<img src="https://img.shields.io/badge/API-UNSTABLE-red?style=flat-square" alt="API Unstable"/>

The *Puree* framework for Blender is a declarative framework that provides a web-inspired API for building user interfaces, addressing the limitations of Blender's native UI system in supporting complex interface architectures and providing enhanced flexibility.

> Puree is built on top of **ModernGL**, **grass** (Rust SCSS compiler), and **Stretchable** to deliver a high-performance, GPU-accelerated UI engine with a familiar web development paradigm.

> **Note:** You may see `XWZ_` prefixes on Blender operator class names (e.g., `XWZ_OT_ui_parser`). This is an internal namespace prefix used to avoid operator name collisions with other Blender addons. It does not affect user-facing functionality.

> [!CAUTION]
> **Critical Rule**: After ANY property change on a container (style, text, children), you must call `container.mark_dirty()`. The GPU will not re-render without it. This is the #1 cause of "my changes aren't showing up" bugs.

## Overview

1. [Installation](#installation)

2. [File Structure](#file-structure)

    1. [`index.yaml` breakdown](#indexyaml-breakdown)
        - [App structure](#app-structure)
        
    2. [`style.scss` breakdown](#stylescss-breakdown)
        - [CSS Custom Properties (Variables)](#css-custom-properties-variables)
        - [Color Space Conversion](#color-space-conversion)

    3. [`script.py` breakdown](#scriptpy-breakdown)
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

5. [Troubleshooting](TROUBLESHOOTING.md)

---

## Installation

**There are 2 ways to start making a user interface using puree:**

### 1. Install with pip (recommended)

Install puree and use the CLI to bootstrap a new project:

```bash
pip install puree-ui
mkdir my_addon && cd my_addon
puree init
```

This creates a complete project structure with all dependencies, a `blender_manifest.toml`, and a starter UI (pink box with "PUREE" in blue).

Then build and install:

```bash
puree build       # Build the extension zip (requires Blender on PATH)
puree install     # Install the extension into Blender
```

For faster development iteration, use symlink mode:

```bash
puree link        # Symlink project into Blender for development
puree reload      # Reload addon in running Blender after code changes
puree unlink      # Remove the development symlink when done
```

### 2. Clone the repo (for framework development)

<details>
<summary>
Click here for installation commands
</summary>

<br>

- Linux:

<pre>
<code class="language-bash">
    sudo apt update
    sudo apt install make
    sudo snap install --edge --classic just
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
</code>
</pre>

- MacOS:
<pre>
<code class="language-bash">
    brew install make
    brew install just
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
</code>
</pre>

- Windows:

<pre>
<code class="language-bash">
    choco install make
    winget install --id Casey.Just
    winget install Rustlang.Rustup
</code>
</pre>
</details>

1. Install the following:

    | Dependencies |
    |-------------|
    | [Blender 5.1+](https://www.blender.org/download/) (must be on PATH) |
    | [Make](https://makefiletutorial.com/) / [Just](https://just.systems/man/en/) |
    | [Rust](https://rust-lang.org/tools/install/) |
    | [Python 3.10+](https://www.python.org/downloads/) |

2. Clone this repository.

    ```plaintext
    git clone https://github.com/nicolaiprodromov/puree
    cd puree
    ```

3. Run `just wheels` to download the python dependencies and add them automatically to the manifest file
4. Run `just build_core` to build the core binaries
5. Run `just link` to symlink the source into Blender's extensions directory (auto-installs deps)
6. Open Blender — the addon is live. A built-in reload server auto-starts on port 19746.
    - Use `just reload` (or `puree reload`) after code changes (triggers reload via TCP server).
    - Use `just tail` to live-follow the log, or `just logs` to see the last 50 lines.
    - Or use `just deploy` as a shortcut for `just link && just reload`.

---

## File Structure

The bare minimum file structure for a project is as follows: 

```
puree_project/
    ├── static/
    │   ├── index.yaml
    │   └── style.scss
    ├── blender_manifest.toml
    └── __init__.py   <-- your addon entry point
```

> Use `puree init` to scaffold this automatically.

---

## `index.yaml` breakdown

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
        - static/style.scss
      scripts:
        - static/script.py
      root:
        style: root
        bg:
          style: bg
```
### App structure

The `app` section defines the application settings, including the selected and default themes. The `theme` section allows you to define multiple layouts, each with its own styles and scripts.

The equivalent of the `body` tag in HTML is the `root` node in Puree. The elements inside the root of the app are called **nodes**.

> Nodes are the building blocks of your UI, and they can represent various UI components such as buttons, panels, text fields, images, etc.

The `root` section contains the nodes that define the hierarchy and properties of your interface. You must nest other nodes within the root nto create your interface.

Each node can have its own properties, styles, and child nodes. In the example above, the `bg` node is a child of the `root` node, and it has its own style defined in the `style.scss` file.

You can also draw images and text by changing the `img` and `text` properties. The images must be stored in a `assets/` folder in the root of your project. Fonts must be stored in a `fonts/` folder in the root of your project.

You can also add custom scripts to your theme. The scripts must be stored in the `static/` folder in the root of your project and then linked in the `scripts` array of your theme.

A more complete file structure would look like this: 

```
puree_project/
    ├── assets/
    │   └── your images (PNG, SVG)
    ├── fonts/
    │   └── your fonts (.ttf, .otf)
    ├── static/
    │   ├── index.yaml
    │   ├── style.scss
    │   ├── script.py
    │   └── components/        <-- reusable components
    ├── blender_manifest.toml
    └── __init__.py              <-- your addon entry point
```

---

## `style.scss` breakdown

You can define custom styles for your app using SCSS (a superset of CSS) to specify styles for your app's nodes.

Puree compiles SCSS via the `grass` Rust crate. Standard SCSS features (variables, nesting, mixins, `!default`) all work. Puree does not implement the full CSS specification, but does implement some new features specific to the framework.

>For more details and the list of supported properties, refer to the [API Reference](API.md).

> *Ultimately, the point is not to replicate CSS, but to provide a familiar syntax for defining styles in a way that is easy to read and write.*

Here is an example of what a `style.scss` file might look like: 

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

### CSS Custom Properties (Variables)

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

### Color Space Conversion

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

---

## `script.py` breakdown

You can add custom Python scripts to your theme to handle events and add interactivity to your UI. The scripts must be stored in the `static/` folder in the root of your project and then linked in the `scripts` array of your theme.

### Basic Structure

The `main` function is the entry point for your script and receives two arguments:

- `self` - The compiler instance
- `app` - The UI application object

You must return the `app` object at the end.

```python
def main(self, app): 
    # Your script logic here
    return app
```

### Event Handlers

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

### Modifying Container Properties

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

### Accessing Container Hierarchy

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

### Multiple Event Handlers

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

### State Management

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

### Integrating with Blender

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

### Threading & Blender Safety

Blender is **not thread-safe** — you cannot call `bpy` APIs from background threads. When performing async work (HTTP requests, heavy computations), use this pattern:

```python
import bpy
import threading

def main(self, app):
    status = app.theme.root.bg.status
    
    def on_click(container):
        def _background_work():
            # OK: pure Python computation in a thread
            result = expensive_calculation()
            
            # NOT OK: bpy calls in a thread — will crash
            # bpy.ops.mesh.primitive_cube_add()  # DON'T DO THIS
            
            # OK: update Puree containers from a thread  
            status.text = f"Result: {result}"
            status.mark_dirty()
            
            # OK: schedule bpy calls on the main thread
            def _deferred():
                bpy.ops.mesh.primitive_cube_add()
                return None  # None = don't repeat
            bpy.app.timers.register(_deferred)
        
        threading.Thread(target=_background_work, daemon=True).start()
    
    app.theme.root.bg.run_btn.click.append(on_click)
    return app
```

**Rules:**
- Puree container updates (`text`, `style`, `mark_dirty()`) are safe from threads
- `bpy.ops.*`, `bpy.data.*`, `bpy.context.*` are **NOT** safe from threads
- Use `bpy.app.timers.register(fn)` to schedule deferred bpy calls on the main thread
- The `puree.net` HTTP module handles this automatically — callbacks run on the main thread

### Target Space Configuration

By default, Puree renders in the **3D Viewport** sidebar (N-panel). You can target other Blender spaces by setting the `space` field in your theme config:

```yaml
app:
  version: 1.0.0
  space: VIEW_3D    # Default — 3D Viewport
  themes:
    - name: my_theme
      style: style.scss
      script: script.py
      config: index.yaml
```

**Supported spaces:**

| Space Value | Blender Area |
|-------------|-------------|
| `VIEW_3D` | 3D Viewport (default) |
| `IMAGE_EDITOR` | UV/Image Editor |
| `NODE_EDITOR` | Shader/Geometry Node Editor |
| `PROPERTIES` | Properties panel |
| `OUTLINER` | Outliner |

The space configuration is handled by `puree/space_config.py` and determines which Blender area type the draw handler attaches to.

### Multi-Theme Support

Puree supports multiple themes within a single addon. Each theme can have its own YAML, SCSS, and Python script:

```yaml
app:
  version: 1.0.0
  themes:
    - name: main_panel
      style: style.scss
      script: script.py
      config: index.yaml
    - name: settings_panel
      style: settings_style.scss
      script: settings_script.py
      config: settings.yaml
```

Each theme's scripts execute in order, and each `script.py` receives the UI instance with access to all themes via `app.theme` (for the current theme) or the theme registry. Components defined in `components/` are shared across all themes.

### Dynamic Container Creation

Create and remove containers at runtime using component templates:

```python
def main(self, app):
    parent = app.theme.root.bg.messages
    
    def add_message(container):
        msg = parent.add_child("[message_slot]", id="msg_1", params={
            "text": "New message",
            "role": "user"
        })
        msg.mark_dirty()
    
    def clear_messages(container):
        parent.clear_children()
        parent.mark_dirty()
    
    app.theme.root.bg.add_btn.click.append(add_message)
    app.theme.root.bg.clear_btn.click.append(clear_messages)
    return app
```

### Using Built-in Modules

Puree provides built-in modules for common tasks:

```python
from puree.storage import Storage
from puree.timers import set_interval, set_timeout, clear
from puree.net import http, sse
from puree.keyboard import keys
from puree.markdown import render_markdown

def main(self, app):
    # Persistence
    store = Storage("my_addon")
    store.set("count", 0)
    store.auto_save = True
    
    # Timers
    handle = set_interval(lambda: poll_status(), 5000)
    
    # HTTP requests (callbacks run on main thread)
    http.get("https://api.example.com/data",
        on_success=lambda resp: update_ui(resp.json()),
        on_error=lambda err: show_error(str(err)))
    
    # Keyboard shortcuts
    keys.bind("CTRL+N", lambda: new_item())
    keys.bind("ESCAPE", lambda: cancel())
    
    # Markdown rendering into a container
    preview = app.theme.root.bg.preview
    preview.set_markdown("# Hello\n\nThis is **bold** text.")
    
    return app
```

See the [API Reference](API.md) for full module documentation.

### Best Practices

1. **Always return the app object** at the end of `main()`
2. **Call `mark_dirty()`** after modifying container properties to trigger GPU sync
3. **Use descriptive function names** for event handlers
4. **Keep handlers focused** - each handler should do one thing well
5. **Handle errors gracefully** - wrap Blender operations in try-except blocks
6. **Use property-based access** - `app.theme.root.bg.button` instead of array indexing
7. **Use `puree.storage`** for persistence instead of rolling your own JSON handling
8. **Use `puree.net`** for HTTP requests — callbacks are main-thread safe
9. **Use `puree.timers`** instead of raw `bpy.app.timers` — auto-cleanup on hot reload

---

|  | Previous Page | Next Page |
|----------|----------|------|
| Puree is under active development. APIs may change between versions. **Special thanks to the open-source community and the developers behind the projects that make puree possible.** | [Home](index.md) | [Components](COMPONENTS.md) |