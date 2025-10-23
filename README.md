<div align="center">
<img src="https://github.com/nicolaiprodromov/puree/blob/master/docs/images/Asset%204.png?raw=true" alt="Puree UI Logo" width="100%"/>

<br>

*A declarative UI framework for Blender addons and much more*

[![Version](https://img.shields.io/github/v/release/nicolaiprodromov/puree?include_prereleases&style=flat&color=blue)](https://github.com/nicolaiprodromov/puree/releases)
[![Blender](https://img.shields.io/badge/Blender-4.2%2B-orange?style=flat&logo=blender&logoColor=white)](https://www.blender.org/)
[![ModernGL](https://img.shields.io/badge/ModernGL-5.12.0-blueviolet?style=flat)](https://github.com/moderngl/moderngl)

*`puree` UI* for Blender is a declarative framework that provides a web-inspired API for building user interfaces, addressing the limitations of Blender's native UI system in supporting complex interface architectures and providing enhanced flexibility.

It's meant for all Blender users that want to enhance their ability to present their creations, models, addons and products inside the software in a streamlined, easy & intuitive way, adaptable to causal users and powerful enough for seasoned programmers.

> `puree` is built with a **Rust** backend, **ModernGL**, and **Stretchable** to deliver a high-performance, GPU-accelerated UI engine with a familiar web development paradigm.

</div>

---

## Why does Blender need a UI framework?

Blender's native UI excels at tool panels but wasn't designed for complex, stateful interfaces. puree exists because:

### *GPU API Constraints*

Blender's `gpu` module provides Python bindings for GPU rendering, but with architectural limitations that constrain certain rendering approaches.

- The [`gpu.types.GPUShader`](https://docs.blender.org/api/current/gpu.types.html#gpu.types.GPUShader) API enforces vertex + fragment shader pairs for traditional geometry rendering. This works for drawing meshes but requires additional overhead for UI operations like filling thousands of rectangles per frame.

- While Blender 4.2+ added [compute shader support](https://docs.blender.org/api/current/gpu.html#custom-compute-shader-using-image-store-and-vertex-fragment-shader), the Python API currently exposes compute shaders primarily for image-based operations using `imageStore()`. Direct binding of Shader Storage Buffer Objects (SSBOs) for custom data-parallel algorithms is not available through the Python API—this technique is needed for efficient UI rendering where container properties (position, color, border radius) must be processed in parallel.

### *Why Abstraction Matters*

Like browsers evolving from DOM manipulation to high-level frameworks like React, Blender needs higher-level abstractions. Native `bpy.types.UILayout` handles tool panels, but complex UIs need state management and component patterns. puree provides these abstractions with GPU acceleration. Focus on *what* your UI does, not *how* to draw it.

### *Design Patterns*

puree replaces Blender's imperative `bpy.types.Panel` approach with declarative component trees using YAML/SCSS separation. Flexbox layouts via **Stretchable** (Rust) and GPU-accelerated hit detection enable real-time interactivity like hover states and smooth transitions.

### *Developer Ergonomics*

Imperative UI code couples structure with styling, changing a button's color means editing Python logic. puree separates concerns architecturally: YAML defines component hierarchy, SCSS handles presentation via selectors. This mirrors the separation of HTML/CSS, enabling style changes without touching code and true component reusability across contexts.

### *Different Approaches*

Native `bpy.types.Panel` offers API stability; web views (CEF/Electron) provide familiar tech with higher overhead; raw OpenGL gives full control but requires building everything from scratch. puree provides high-level abstractions (YAML/SCSS, flexbox) with direct GPU access.

---

## What is puree good for?

*From addon user interfaces to complex object-based tracking in screen space, to interactive tutorials, to markdown rendering directly in Blender, to simple drawing anywhere in Blender, in real-time, using the gpu.*

Check the [examples](/examples) folder for detailed examples of what can be accomplished with **puree**.

<div align="center">

<video src="docs/images/example1.mp4" controls width="100%">
</video>

^

*Example usage with hot reload for fast iterations*

<video src="docs/images/example2.mp4" controls width="100%">
</video>

^

*Slightly more complex interface*

<video src="docs/images/example3.mp4" controls width="100%">
</video>

^

*Scene object tracking example*

</div>

---

## Quick Start

Here's a short tutorial to get you started with Puree:

<video src="docs/images/example4.mp4" controls width="50%">
</video>

> [!IMPORTANT]
> It's not recommend to install dependencies with pip in the blender python context, so better download the puree wheel and it's dependencies, and reference them in the `blender_manifest.toml` file of your addon.

> [!WARNING]
> ### **puree is in beta - WIP**
> - puree currently works **only** with Blender's OpenGL backend because of the ModernGL dependency.
> - The API is not 90% stable, some breaking changes will happen.


1. **Download the package with pip or download the [latest release](https://github.com/nicolaiprodromov/puree/releases)**

    ```bash
    pip download --only-binary=:all: --python-version 3.11 --dest wheels puree-ui
    ```

2. **Create your project structure:**

    ```bash
    my_addon/x
        ├── static/
        │   ├── index.yaml
        │   └── style.scss
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
    "SPDX:GPL-3.0-or-later",
    ]

    copyright = [
    "your_copyright_year your_name",
    ]

    platforms = [
    "windows-x64",
    "linux-x64",
    "macos-arm64",
    "macos-x64"
    ]

    wheels = [
    "./wheels/PyYAML-6.0.2-cp311-cp311-win_amd64.whl",
    "./wheels/attrs-25.3.0-py3-none-any.whl",
    "./wheels/glcontext-3.0.0-cp311-cp311-win_amd64.whl",
    "./wheels/moderngl-5.12.0-cp311-cp311-win_amd64.whl",
    "./wheels/puree_ui-0.1.2-py3-none-any.whl",
    "./wheels/stretchable-1.1.7-cp38-abi3-win_amd64.whl",
    "./wheels/typing_extensions-4.15.0-py3-none-any.whl",
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
        selected_theme: xwz_default
        default_theme: xwz_default
        theme:
            - name: xwz_default
            author: xwz
            version: 1.0.0

            space: VIEW_3D

            default_font: NeueMontreal-Regular

            scripts:
                - static/script.py
            styles:
                - static/style.scss
            components: static/components/

            root:
                style: root
                test_box:
                    style: test_box
                    text : Red Box
    ```

6. **Style it in `style.scss`:**

    ```scss
    root{
        flex-direction : column;
        justify-content: center;
        align-items    : center;
        width          : 100%;
        height         : 100%;
        color          : rgba(0,0,0,0);
    }

    test_box{
        width       : 300px;
        height      : 300px;
        color       : #ff0000;
        text-color  : #fff;
        text-scale  : 40px;
        text-align-h: center;
        text-align-v: center;
    }
    ```

7. **Zip the files.**

8. **Install in Blender**: `Edit > Preferences > Add-ons > Install from disk`

9. Done. If you open the latest version of Blender you have installed on your system you should see a `puree` tab in the N-panel of the 3D Viewport - click the button and you will see a blue rectangle with text.

---

## How it works

Puree follows a hybrid Rust/Python pipeline optimized for performance:

1. **Parse** – Rust-native parsers process YAML/SCSS into styled container trees
2. **Layout** – Stretchable flexbox engine computes responsive layouts  
3. **Flatten** – Rust optimizes container hierarchy into GPU-ready buffers
4. **Render** – ModernGL compute shaders generate UI texture with full effects
5. **Interact** – Rust hit detection handles all mouse/scroll events in real-time

<br>

```mermaid
graph LR
    A[YAML + SCSS] --> B[Rust Parser]
    B --> C[Container Tree]
    C --> D[Stretchable Layout]
    D --> E[Rust Flattener]
    E --> F[GPU Buffers]
    F --> G[GLSL Compute]
    G --> H[UI Texture]
    
    I[Mouse/Scroll] --> J[Rust Hit Detector]
    J --> C
    
    K[Python Scripts] --> L[Compiler Hook]
    L --> C
    
    M[File Watcher] -.-> B
    H --> N[Blender Viewport]
    
    style B fill:#000
    style E fill:#000
    style G fill:#000
    style J fill:#000
```

<br>

This architecture enables:

- **Native performance** – Critical paths run in compiled Rust code
- **Hot reload** – Rust file watcher auto-updates on YAML/SCSS changes
- **GPU acceleration** – All rendering happens in compute shaders
- **Reactive layouts** – Automatic recompute on viewport resize

| Feature | Description |
|---------|-------------|
| *Declarative UI Design* | Define your interface structure using YAML configuration files with HTML-like nesting |
| *GPU-Accelerated Rendering* | Leverages ModernGL compute shaders for real-time, high-performance UI rendering |
| *Responsive Layouts* | Automatic layout computation using the Stretchable flexbox engine |
| *Interactive Components* | Built-in support for hover states, click events, scrolling, and toggle interactions |
| *Web-Inspired Architecture* | Familiar paradigm for developers coming from web development |


> Read the full [documentation](docs/DOCS.md) for detailed guides, API references, and examples.

## Support & Issues

### Getting Help

For questions and support, check out the [docs](docs/DOCS.md) or [support guide](docs/SUPPORT.md).

### Reporting Issues

Found a bug or have a feature request? [Open an issue](https://github.com/nicolaiprodromov/puree/issues) with:

- Clear description of the problem or feature
- Steps to reproduce (for bugs)
- Blender version and OS
- Relevant error messages or screenshots

## Built With

<a href="https://www.blender.org/"><img src="https://img.shields.io/badge/Blender-2B2B2B?style=flat-square&logo=blender&logoColor=white&logoSize=auto" height="28"/></a> <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-2B2B2B?style=flat-square&logo=python&logoColor=white&logoSize=auto" height="28"/></a> <a href="https://www.rust-lang.org/"><img src="https://img.shields.io/badge/Rust-2B2B2B?style=flat-square&logo=rust&logoColor=white&logoSize=auto" height="28"/></a> <a href="https://www.khronos.org/opengl/wiki/OpenGL_Shading_Language"><img src="https://img.shields.io/badge/GLSL-2B2B2B?style=flat-square&logo=opengl&logoColor=white&logoSize=auto" height="28"/></a> <a href="https://pyo3.rs/"><img src="https://img.shields.io/badge/PyO3-2B2B2B?style=flat-square&logo=rust&logoColor=white&logoSize=auto" height="28"/></a> <a href="https://github.com/moderngl/moderngl"><img src="https://img.shields.io/badge/ModernGL-2B2B2B?style=flat-square&logo=opengl&logoColor=white&logoSize=auto" height="28"/></a> <a href="https://github.com/vislyhq/stretchable"><img src="https://img.shields.io/badge/Stretchable-2B2B2B?style=flat-square&logo=rust&logoColor=white&logoSize=auto" height="28"/></a>

> *Special thanks to the open-source community and the developers behind the projects that make **puree** possible.*

<img src="https://github.com/nicolaiprodromov/puree/blob/master/docs/images/munky.gif?raw=true" width="100px">
