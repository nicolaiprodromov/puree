<div align="center">

<img src="docs/Asset 1.png" alt="Puree UI Logo" width="100%"/>

<br>

*A declarative UI framework for Blender addons and much more*



</div>

<div align="center">


[![Version](https://img.shields.io/badge/dynamic/toml?url=https://raw.githubusercontent.com/nicolaiprodromov/puree/refs/heads/master/blender_manifest.toml&query=$.version&label=version&color=blue&style=flat)](https://github.com/nicolaiprodromov/puree)
[![Release](https://img.shields.io/github/v/release/nicolaiprodromov/puree?style=flat&color=blue)](https://github.com/nicolaiprodromov/puree/releases)


[![Blender](https://img.shields.io/badge/Blender-4.2%2B-orange?style=flat&logo=blender&logoColor=white)](https://www.blender.org/)
[![ModernGL](https://img.shields.io/badge/ModernGL-5.12.0-blueviolet?style=flat)](https://github.com/moderngl/moderngl)

</div>

*Puree UI* for Blender is a declarative framework that provides a web-inspired API for building user interfaces, addressing the limitations of Blender's native UI system in supporting complex interface architectures and providing enhanced flexibility.

> Puree is built on top of **ModernGL**, **TinyCSS2**, and **Stretchable** to deliver a high-performance, GPU-accelerated UI engine with a familiar web development paradigm.

<div align="center">

## Key Features

</div>

| Feature | Description |
|---------|-------------|
| *Declarative UI Design* | Define your interface structure using TOML configuration files with HTML-like nesting |
| *GPU-Accelerated Rendering* | Leverages ModernGL compute shaders for real-time, high-performance UI rendering |
| *Responsive Layouts* | Automatic layout computation using the Stretchable flexbox engine |
| *Interactive Components* | Built-in support for hover states, click events, scrolling, and toggle interactions |
| *Web-Inspired Architecture* | Familiar paradigm for developers coming from web development |

<div align="center">

## How it works

</div>

Puree follows a render pipeline inspired by modern web browsers:

1. **Parse & Structure** – UI components are defined in TOML files with a hierarchical container structure
2. **Style Application** – CSS files are parsed and styles are applied to containers with support for variables and selectors
3. **Layout Computation** – The Stretchable engine computes flexbox layouts with support for percentage-based sizing, padding, margins, and borders
4. **GPU Rendering** – A compute shader generates the final UI texture with gradients, rounded corners, shadows, and interaction states
5. **Event Handling** – Mouse, scroll, and click events are tracked and propagated through the component tree

This architecture allows for rapid UI prototyping and iteration while maintaining the performance requirements of real-time 3D applications.


<div align="center">

> [!NOTE]
> Read the full [documentation](docs/DOCS.md) for detailed guides, API references, and examples.

## Quick Example

</div>

Here's a minimal example to get you started with Puree:

**1. Download the [latest release](https://github.com/nicolaiprodromov/puree/releases) or clone the [repository](https://github.com/nicolaiprodromov/puree)**

**2. Create your project structure:**
```
my_addon/
    ├── puree/ <-- puree source code
    ├── static/
    │   ├── index.toml
    │   └── style.css
    └── __init__.py <-- your addon entry point
```

**3. Define your addon entrypoint in `__init__.py`:**
```python
import bpy
from .puree import register as xwz_ui_register, unregister as xwz_ui_unregister
bl_info = {
    "name"       : "my first puree addon",
    "author"     : "you",
    "version"    : (0, 0, 2),
    "blender"    : (4, 2, 0),
    "location"   : "3D View > Sidebar > Puree",
    "description": "XWZ Puree UI framework",
    "category"   : "3D View"
}
def register():
    xwz_ui_register()
    wm = bpy.context.window_manager
    wm.xwz_ui_conf_path = "static/index.toml"
    wm.xwz_debug_panel  = True
    wm.xwz_auto_start   = True
def unregister():
    xwz_ui_unregister()
if __name__ == "__main__":
    register()
```

**4. Define your UI in `index.toml`:**
```toml
[app]
    selected_theme = "default"
    default_theme  = "default"
[[app.theme]]
    name         = "default"
    author       = "you"
    version      = "1.0.0"
    default_font = "NeueMontreal-Regular"
    styles       = ["static/style.css"]
    scripts      = []
    components   = ""
    [app.theme.root]
        style = "root"
        [app.theme.root.hello]
            style = "hello_box"
            text  = "Hello, Puree!"
```

**5. Style it in `style.css`:**
```css
root {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
}

hello_box {
    width: 300px;
    height: 100px;
    background-color: #3498db;
    border-radius: 10px;
    text-color: #ffffff;
    text-scale: 24px;
}
```

That's it! You now have a centered blue box with text.