---
layout: home
title: Home
---

<p align="center">
  <img src="images/Asset 4.png" alt="Puree UI Logo" width="100%"/>
</p>

<p align="center">
  <em>A declarative UI framework for Blender addons and much more</em>
</p>

<p align="center">
  <a href="https://github.com/nicolaiprodromov/puree/releases"><img src="https://img.shields.io/github/v/release/nicolaiprodromov/puree?include_prereleases&style=flat&color=blue" alt="Version"/></a>
  <a href="https://www.blender.org/"><img src="https://img.shields.io/badge/Blender-4.2%2B-orange?style=flat&logo=blender&logoColor=white" alt="Blender"/></a>
  <a href="https://github.com/moderngl/moderngl"><img src="https://img.shields.io/badge/ModernGL-5.12.0-blueviolet?style=flat" alt="ModernGL"/></a>
</p>

**Puree UI** for Blender is a declarative framework that provides a web-inspired API for building user interfaces, addressing the limitations of Blender's native UI system in supporting complex interface architectures and providing enhanced flexibility.

It's meant for all Blender users that want to enhance their ability to present their creations, models, addons and products inside the software in a streamlined, easy & intuitive way, adaptable to causal users and powerful enough for seasoned programmers.

> Puree is built on top of **ModernGL**, **TinyCSS2**, and **Stretchable** to deliver a high-performance, GPU-accelerated UI engine with a familiar web development paradigm.

---

## What is puree good for?

From addon user interfaces to complex object-based tracking in screen space, to interactive tutorials, to markdown-type (and soon true markdown rendering!) rendering directly in Blender, to simple drawing anywhere in Blender, in real-time, using the gpu. Check the [examples](/examples) folder for detailed examples of what can be accomplished with **puree**.

<p align="center">
  <img src="images/example1.gif" alt="Example 1 UI GIF" width="100%"/>
</p>

## Key Features

| Feature | Description |
|---------|-------------|
| **Declarative UI Design** | Define your interface structure using YAML configuration files with HTML-like nesting |
| **GPU-Accelerated Rendering** | Leverages ModernGL compute shaders for real-time, high-performance UI rendering |
| **Responsive Layouts** | Automatic layout computation using the Stretchable flexbox engine |
| **Interactive Components** | Built-in support for hover states, click events, scrolling, and toggle interactions |
| **Web-Inspired Architecture** | Familiar paradigm for developers coming from web development |

---

## Quick Start

Here's a minimal example to get you started with Puree:

> [!IMPORTANT]
> Blender does not recommend installing dependencies with pip in the blender python context, so it's better to download the puree wheel and reference it in the blender manifest file of your addon.

1. **Download the package with pip or download the [latest release](https://github.com/nicolaiprodromov/puree/releases)**

```bash
pip download --only-binary=:all: --python-version 3.11 --dest wheels puree-ui
```

2. **Create your project structure:**

```bash
my_addon/x
    ├── static/
    │   ├── index.yaml
    │   └── style.css
    └── __init__.py <-- your addon entry point
```

3. **Define your addon manifest in `blender_manifest.toml`:**

Rename the `blender_manifest.example.toml` to `blender_manifest.toml` and modify to fit your addons metadata.

```toml
schema_version = "1.0.0"

id         = "your_addon_id"
version    = "your_addon_version"
name       = "your_addon_name"
tagline    = "your_addon_tagline"
maintainer = "your_name"
type       = "add-on"

blender_version_min = "your_addon_version_blend_min"

license = [
"your_addon_license",
]

platforms = [
"windows-x64",
"linux-x64",
"macos-arm64",
"macos-x64"
]

wheels = [
"./wheels/attrs-25.3.0-py3-none-any.whl",
"./wheels/glcontext-3.0.0-cp311-cp311-win_amd64.whl",
"./wheels/linkify_it_py-2.0.3-py3-none-any.whl",
"./wheels/markdown_it_py-4.0.0-py3-none-any.whl",
"./wheels/mdit_py_plugins-0.5.0-py3-none-any.whl",
"./wheels/mdurl-0.1.2-py3-none-any.whl",
"./wheels/moderngl-5.12.0-cp311-cp311-win_amd64.whl",
"./wheels/platformdirs-4.5.0-py3-none-any.whl",
"./wheels/puree_ui-0.0.8-py3-none-any.whl",
"./wheels/pygments-2.19.2-py3-none-any.whl",
"./wheels/PyYAML-6.0.2-cp311-cp311-win_amd64.whl",
"./wheels/rich-14.1.0-py3-none-any.whl",
"./wheels/stretchable-1.1.7-cp38-abi3-win_amd64.whl",
"./wheels/textual-6.2.1-py3-none-any.whl",
"./wheels/tinycss2-1.4.0-py3-none-any.whl",
"./wheels/typing_extensions-4.15.0-py3-none-any.whl",
"./wheels/uc_micro_py-1.0.3-py3-none-any.whl",
"./wheels/webencodings-0.5.1-py2.py3-none-any.whl"
]

[build]
paths_exclude_pattern = [
"__pycache__/",
"*.zip",
"*.pyc",
".gitignore",
".vscode/",
".git/",
]
```

4. **Define your addon entrypoint in `__init__.py`:**

Rename the `__init__.example.py` to `__init__.py` and modify to fit your addons metadata.

```python
import bpy
import os
from puree import register as xwz_ui_register, unregister as xwz_ui_unregister
from puree import set_addon_root

bl_info = {
    "name"       : "your_addon_name",
    "author"     : "your_name",
    "version"    : (1, 0, 0),
    "blender"    : (4, 2, 0),
    "location"   : "3D View > Sidebar > Your Addon",
    "description": "Your addon description",
    "category"   : "Your Addon Category"
}

def register():
    # Set the addon root directory so puree knows where to find resources
    set_addon_root(os.path.dirname(os.path.abspath(__file__)))
    # Register the framework
    xwz_ui_register()
    # Set default properties
    # ui_conf_path is relative to the addon root directory and
    # is required to point puree to the main configuration file of your UI
    wm = bpy.context.window_manager
    wm.xwz_ui_conf_path = "static/index.yaml"
    wm.xwz_debug_panel  = True
    wm.xwz_auto_start   = True

def unregister():
    # Unregister the framework
    xwz_ui_unregister()
    
if __name__ == "__main__":
    register()
```

5. **Define your UI in `index.yaml`:**

```yaml
app:
    selected_theme: default
    default_theme: default
    theme:
    - name: default
        author: you
        version: 1.0.0
        default_font: NeueMontreal-Regular
        styles:
        - static/style.css
        scripts: []
        components: ""
        root:
        style: root
        hello:
            style: hello_box
            text: Hello, Puree!
```

6. **Style it in `style.css`:**

```css
root {
    width          : 100%;
    height         : 100%;
    display        : flex;
    align-items    : center;
    justify-content: center;
}

hello_box {
    width           : 300px;
    height          : 100px;
    background-color: #3498db;
    border-radius   : 10px;
    text-color      : #ffffff;
    text-scale      : 24px;
}
```

7. **Zip the files.**

8. **Install in Blender**: `Edit > Preferences > Add-ons > Install from disk`

9. Done. If you open the latest version of Blender you have installed on your system you should see a `puree` tab in the N-panel of the 3D Viewport - click the button and you will see a blue rectangle with text.

---

## How it works

Puree follows a render pipeline inspired by modern web browsers:

1. **Parse** – YAML/CSS files are loaded and parsed into container tree with styles
2. **Layout** – Stretchable computes flexbox layouts with viewport-aware sizing
3. **Compile** – Optional Python scripts transform the UI tree
4. **Render** – ModernGL compute shader generates GPU texture with all visual effects
5. **Event** – Mouse/scroll events update container states and trigger re-renders

This architecture enables:

- **Reactive updates** – Layout recomputes on viewport resize
- **GPU acceleration** – All rendering in compute shaders
- **Script integration** – Python scripts can modify UI at runtime
- **Event propagation** – Interactions flow through container hierarchy

> **TIP:** Read the full [documentation]({{ site.baseurl }}/DOCS) for detailed guides, API references, and examples.

---

## Built With

- [Blender](https://www.blender.org/) - 3D creation suite
- [Python](https://www.python.org/) - Programming language
- [ModernGL](https://github.com/moderngl/moderngl) - Modern OpenGL bindings
- [GLSL](https://www.khronos.org/opengl/wiki/OpenGL_Shading_Language) - OpenGL Shading Language
- [Stretchable](https://github.com/vislyhq/stretchable) - Flexbox layout engine
- [TinyCSS2](https://github.com/Kozea/tinycss2) - CSS parser
- [YAML](https://yaml.org/) - Configuration format

---

**Special thanks to the open-source community and the developers behind the projects that make puree possible.**

<p align="center">
  <img src="images/munky.gif" width="100px" alt="Monkey GIF"/>
</p>

---

**[Next: Full Documentation →]({{ site.baseurl }}/DOCS)**
