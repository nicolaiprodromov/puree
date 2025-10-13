<div align="center">

<img src="docs/Asset 1.png" alt="Puree UI Logo" width="100%"/>

<br>

*A declarative UI framework for Blender addons and much more*



</div>

<div align="center">


[![Version](https://img.shields.io/badge/dynamic/toml?url=https://raw.githubusercontent.com/nicolaiprodromov/puree/refs/heads/master/blender_manifest.toml&query=$.version&label=version&color=blue&style=flat)](https://github.com/nicolaiprodromov/puree)
[![Release](https://img.shields.io/github/v/release/nicolaiprodromov/puree?include_prereleases&style=flat&color=blue)](https://github.com/nicolaiprodromov/puree/releases)


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

## Quick Example

</div>

Here's a minimal example to get you started with Puree:

> [!IMPORTANT]
> Blender does not recommend installing dependencies with pip in the blender python context, so it's better to download the puree wheel and reference it in the blender manifest file of your addon.

1. **Download the package with pip or download the [latest release](https://github.com/nicolaiprodromov/puree/releases)**

    ```bash
    pip download --only-binary=:all: --no-deps --dest wheels puree-ui
    ```

2. **Create your project structure:**

    ```bash
    my_addon/x
        ├── static/
        │   ├── index.toml
        │   └── style.css
        └── __init__.py <-- your addon entry point
    ```

3. **Define your addon manifest in `blender_manifest.toml`:**

    Rename the `blender_manifest.example.toml` to `blender_manifest.toml` and modify to fit your addons metadata.

    ```toml
    schema_version      = "1.0.0"
    id                  = "your_addon_id"
    version             = "your_addon_version"
    name                = "your_addon_name"
    tagline             = "your_addon_tagline"
    maintainer          = "your_name"
    type                = "add-on"
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
    "./wheels/puree_ui-0.0.7-py3-none-any.whl"
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
        wm.xwz_ui_conf_path = "static/index.toml"
        wm.xwz_debug_panel  = True
        wm.xwz_auto_start   = True

    def unregister():
        # Unregister the framework
        xwz_ui_unregister()
        
    if __name__ == "__main__":
        register()
    ```

5. **Define your UI in `index.toml`:**

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

<div align="center">

## How it works

</div>

Puree follows a render pipeline inspired by modern web browsers:

1. **Parse** – TOML/CSS files are loaded and parsed into container tree with styles
2. **Layout** – Stretchable computes flexbox layouts with viewport-aware sizing
3. **Compile** – Optional Python scripts transform the UI tree
4. **Render** – ModernGL compute shader generates GPU texture with all visual effects
5. **Event** – Mouse/scroll events update container states and trigger re-renders

```mermaid
graph LR
    A[TOML + CSS] --> B[Parser]
    B --> C[Container Tree]
    C --> D[Stretchable Layout]
    D --> E[Flattened Data]
    E --> F[GPU Buffers]
    F --> G[Compute Shader]
    G --> H[UI Texture]
    
    I[Mouse/Scroll] --> J[Event Handlers]
    J --> K[Hit Detection]
    K --> C
    
    L[Python Scripts] --> M[Compiler]
    M --> C
    
    H --> N[Blender Viewport]
    
    style A fill:#e3f2fd
    style C fill:#fff3e0
    style D fill:#f3e5f5
    style G fill:#e8f5e9
    style H fill:#fce4ec
    style K fill:#fff9c4
```

This architecture enables:
- **Reactive updates** – Layout recomputes on viewport resize
- **GPU acceleration** – All rendering in compute shaders
- **Script integration** – Python scripts can modify UI at runtime
- **Event propagation** – Interactions flow through container hierarchy

> [!TIP]
> Read the full [documentation](docs/DOCS.md) for detailed guides, API references, and examples.

<div align="center">

## Support & Issues

</div>

### Getting Help

For questions and support, check out the [docs](docs/DOCS.md) or [support guide](docs/SUPPORT.md).

### Reporting Issues

Found a bug or have a feature request? [Open an issue](https://github.com/nicolaiprodromov/puree/issues) with:

- Clear description of the problem or feature
- Steps to reproduce (for bugs)
- Blender version and OS
- Relevant error messages or screenshots

<div align="center">

## Built With

</div>

<p align="center">
  <a href="https://www.blender.org/"><img src="https://img.shields.io/badge/Blender-E87D0D?style=flat-square&logo=blender&logoColor=white&logoSize=auto" height="28"/></a>
  &nbsp;&nbsp;&nbsp;
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white&logoSize=auto" height="28"/></a>
</p>

<p align="center">
  <a href="https://github.com/moderngl/moderngl"><img src="https://img.shields.io/badge/ModernGL-5C2D91?style=flat-square&logo=opengl&logoColor=white&logoSize=auto" height="28"/></a>
  &nbsp;&nbsp;&nbsp;
  <a href="https://www.khronos.org/opengl/wiki/OpenGL_Shading_Language"><img src="https://img.shields.io/badge/GLSL-5586A4?style=flat-square&logo=opengl&logoColor=white&logoSize=auto" height="28"/></a>
</p>

<p align="center">
  <a href="https://github.com/vislyhq/stretchable"><img src="https://img.shields.io/badge/Stretchable-FF6B6B?style=flat-square&logo=rust&logoColor=white&logoSize=auto" height="28"/></a>
  &nbsp;&nbsp;&nbsp;
  <a href="https://github.com/Kozea/tinycss2"><img src="https://img.shields.io/badge/TinyCSS2-264DE4?style=flat-square&logo=css3&logoColor=white&logoSize=auto" height="28"/></a>
  &nbsp;&nbsp;&nbsp;
  <a href="https://toml.io/"><img src="https://img.shields.io/badge/TOML-9C4121?style=flat-square&logo=toml&logoColor=white&logoSize=auto" height="28"/></a>
</p>

<div align="center">

*Special thanks to the open-source community and the developers behind the projects that make **puree** possible.*

</div>

</div>
