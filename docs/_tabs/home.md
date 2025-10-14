---
layout: home
icon: fas fa-home
order: 1
---

<p align="center">
  <img src="/puree/images/Asset 4.png" alt="Puree UI Logo" width="100%"/>
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
{: .prompt-tip }

---

## What is puree good for?

From addon user interfaces to complex object-based tracking in screen space, to interactive tutorials, to markdown-type (and soon true markdown rendering!) rendering directly in Blender, to simple drawing anywhere in Blender, in real-time, using the gpu. Check the [examples](https://github.com/nicolaiprodromov/puree/tree/master/examples) folder for detailed examples of what can be accomplished with **puree**.

<p align="center">
  <img src="/puree/images/example1.gif" alt="Example 1 UI GIF" width="100%"/>
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

> Blender does not recommend installing dependencies with pip in the blender python context, so it's better to download the puree wheel and reference it in the blender manifest file of your addon.
{: .prompt-warning }

1. **Download the package with pip or download the [latest release](https://github.com/nicolaiprodromov/puree/releases)**

    ```bash
    pip download --only-binary=:all: --python-version 3.11 --dest wheels puree-ui
    ```

2. **Create your project structure:**

    ```bash
    my_addon/
        ├── static/
        │   ├── index.yaml
        │   └── style.css
        └── __init__.py
    ```

3. **Define your addon manifest in `blender_manifest.toml`:**

    ```toml
    schema_version = "1.0.0"
    id = "your_addon_id"
    version = "your_addon_version"
    name = "your_addon_name"
    tagline = "your_addon_tagline"
    maintainer = "your_name"
    type = "add-on"
    blender_version_min = "4.2.0"
    ```

4. **Define your addon entrypoint in `__init__.py`:**

    ```python
    import bpy
    import os
    from puree import register as xwz_ui_register, unregister as xwz_ui_unregister
    from puree import set_addon_root

    def register():
        set_addon_root(os.path.dirname(os.path.abspath(__file__)))
        xwz_ui_register()
        wm = bpy.context.window_manager
        wm.xwz_ui_conf_path = "static/index.yaml"
    ```

5. **Define your UI in `index.yaml`:**

    ```yaml
    app:
      selected_theme: default
      default_theme: default
      theme:
        - name: default
          root:
            style: root
            hello:
              style: hello_box
              text: Hello, Puree!
    ```

6. **Install in Blender**: `Edit > Preferences > Add-ons > Install from disk`

---

## How it works

Puree follows a render pipeline inspired by modern web browsers:

1. **Parse** – YAML/CSS files are loaded and parsed into container tree with styles
2. **Layout** – Stretchable computes flexbox layouts with viewport-aware sizing
3. **Compile** – Optional Python scripts transform the UI tree
4. **Render** – ModernGL compute shader generates GPU texture with all visual effects
5. **Event** – Mouse/scroll events update container states and trigger re-renders

---

## Support & Issues

> **puree is in beta - WIP**
>
> - puree currently works **only** with Blender's OpenGL backend because of the ModernGL dependency.
> - The API is not stable and **breaking changes are expected** in future releases.
{: .prompt-danger }

### Getting Help

For questions and support, check out the [documentation](/puree/documentation) or [support guide](/puree/support).

### Reporting Issues

Found a bug or have a feature request? [Open an issue](https://github.com/nicolaiprodromov/puree/issues).

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
