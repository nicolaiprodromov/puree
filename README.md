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

## How it works

</div>

Puree follows a render pipeline inspired by modern web browsers:

1. **Parse & Structure** – UI components are defined in TOML files with a hierarchical container structure
2. **Style Application** – CSS files are parsed and styles are applied to containers with support for variables and selectors
3. **Layout Computation** – The Stretchable engine computes flexbox layouts with support for percentage-based sizing, padding, margins, and borders
4. **GPU Rendering** – A compute shader generates the final UI texture with gradients, rounded corners, shadows, and interaction states
5. **Event Handling** – Mouse, scroll, and click events are tracked and propagated through the component tree

This architecture allows for rapid UI prototyping and iteration while maintaining the performance requirements of real-time 3D applications.

> [!NOTE]
> Read the full [documentation](docs/DOCS.md) for detailed guides, API references, and examples.

<div align="center">

## Quick Example

</div>

Here's a minimal example to get you started with Puree:

1. **Download the [latest release](https://github.com/nicolaiprodromov/puree/releases) or clone the [repository](https://github.com/nicolaiprodromov/puree)**

2. **Create your project structure:**

    ```
    my_addon/
        ├── puree/ <-- puree source code
        ├── static/
        │   ├── index.toml
        │   └── style.css
        └── __init__.py <-- your addon entry point
    ```

3. **Define your addon entrypoint in `__init__.py`:**

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

4. **Define your UI in `index.toml`:**

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

5. **Style it in `style.css`:**

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

6. **Install Make or Just**, [Blender 4.x+](https://www.blender.org/download/), and the [Blender MCP Addon](https://github.com/XWZ/blender-mcp-addon) for the easiest development experience.

    ```bash
    # install make or just
    # windows
    choco install make
    winget install --id Casey.Just
    #linux 
    # for just or both you can just use snap or any package manager
    # or for make run
    sudo apt update
    sudo apt install make
    ```

7. **Run `make build` to build the addon zip file.**
    - You need Blender 4.x+ installed.
    - You need *Python 3.10+* installed on your system.
    - You need *make* installed on your system.
    - You can also manually zip the folder.

8. **Run `make install` to install the addon in Blender.**
    - To run `install` command you must install the [Blender MCP Addon](https://github.com/XWZ/blender-mcp-addon) in Blender and connect to the server.
    - Alternatively, run `make deploy` to build and install in one step.
    - Or just install the zip file manually in Blender preferences: Edit > Preferences > Add-ons > Install from disk

Done. If you open the latest version of Blender you have installed on your system you should see a `puree` tab in the N-panel of the 3D Viewport - click the button and you will see a blue rectangle with text.

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

## Contributing

</div>

We welcome contributions to Puree! Whether you're fixing bugs, adding features, or improving documentation, your help is appreciated.

### Development Setup

1. **Fork and clone the repository:**

    ```bash
    git clone https://github.com/yourusername/puree.git
    cd puree
    ```

2. **Download platform-specific wheels:**

    ```bash
    make wheels
    # or
    just wheels
    ```

### Build Process

Puree uses **Make** or **Just** for build automation. The build system supports Windows, Linux, and macOS:

| Command | Description |
|---------|-------------|
| `make build` / `just build` | Packages the addon into a zip file in `dist/` |
| `make install` / `just install` | Installs the addon to Blender (requires [Blender MCP](https://github.com/XWZ/blender-mcp-addon)) |
| `make uninstall` / `just uninstall` | Removes the addon from Blender |
| `make deploy` / `just deploy` | Full workflow: downloads wheels, builds, uninstalls old version, installs new version |
| `make update_version VERSION=x.y.z` | Updates version in `blender_manifest.toml` and `__init__.py` |

### Contribution Guidelines

1. Create a feature branch from `master`
2. Make your changes with clear, descriptive commits
3. Test your changes with `make deploy` in Blender 4.2+
4. Ensure no regressions in existing functionality
5. Submit a pull request with a clear description of changes

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
