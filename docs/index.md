---
layout: page
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

<p align="center">
    <img src="https://img.shields.io/badge/OpenGL%20Backend-ONLY-orange?style=flat-square" alt="OpenGL Only"/>
    <img src="https://img.shields.io/badge/API-UNSTABLE-red?style=flat-square" alt="API Unstable"/>
</p>

**Puree UI** for Blender is a declarative framework that provides a web-inspired API for building user interfaces, addressing the limitations of Blender's native UI system in supporting complex interface architectures and providing enhanced flexibility.

It's meant for all Blender users that want to enhance their ability to present their creations, models, addons and products inside the software in a streamlined, easy & intuitive way, adaptable to causal users and powerful enough for seasoned programmers.

> Puree is built on top of **ModernGL**, **grass** (Rust SCSS compiler), and **Stretchable** to deliver a high-performance, GPU-accelerated UI engine with a familiar web development paradigm.

---

## What is puree good for?

From addon user interfaces to complex object-based tracking in screen space, to interactive tutorials, to markdown rendering directly in Blender, to simple drawing anywhere in Blender, in real-time, using the gpu. Check the [examples](/examples) folder for detailed examples of what can be accomplished with **puree**.

<p align="center">
  <img src="images/example1.gif" alt="Example 1 UI GIF" width="100%"/>
</p>

## Key Features

| Feature | Description |
|---------|-------------|
| **Declarative UI Design** | Define your interface structure using YAML configuration files with HTML-like nesting |
| **GPU-Accelerated Rendering** | Leverages ModernGL compute shaders for real-time, high-performance UI rendering |
| **Responsive Layouts** | Automatic layout computation using the Stretchable flexbox engine |
| **Interactive Components** | Built-in support for hover states, click events, scrolling, keyboard shortcuts, focus management, and collapse/expand |
| **Built-in Modules** | Storage persistence, HTTP/SSE networking, timers, markdown rendering, virtual scrolling, and more |
| **Web-Inspired Architecture** | Familiar paradigm for developers coming from web development |

---

## Quick Start

Here's how to get started with Puree:

> [!WARNING]
> puree currently works **only** with Blender's OpenGL backend because of the ModernGL dependency.

1. **Install puree:**

    ```bash
    pip install puree-ui
    ```

2. **Create a new project:**

    ```bash
    mkdir my_addon && cd my_addon
    puree init
    ```

    This creates a complete project with all dependencies, a `blender_manifest.toml`, and a starter UI (pink box with "PUREE" in bold blue text).

3. **Build the extension:**

    ```bash
    puree build
    ```

    Requires Blender on your system PATH.

4. **Install into Blender:**

    ```bash
    puree install
    ```

5. **Open Blender** — look for the Puree tab in the N-panel of the 3D Viewport.

6. **For faster development** (optional) — use symlink mode instead of build+install:

    ```bash
    puree link            # Symlink project into Blender (one-time)
    puree reload          # Reload after code changes
    puree unlink          # Remove symlink when done
    ```

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

> Read the full [documentation](DOCS.md) for detailed guides, API references, and examples.

---

## Built With

- [Blender](https://www.blender.org/) - 3D creation suite
- [Python](https://www.python.org/) - Programming language
- [ModernGL](https://github.com/moderngl/moderngl) - Modern OpenGL bindings
- [GLSL](https://www.khronos.org/opengl/wiki/OpenGL_Shading_Language) - OpenGL Shading Language
- [Stretchable](https://github.com/vislyhq/stretchable) - Flexbox layout engine (Rust/Taffy)
- [grass](https://github.com/connorskees/grass) - SCSS compiler (Rust, via puree_core)
- [YAML](https://yaml.org/) - Configuration format

---

<p align="center">
  <img src="images/munky.gif" width="100px" alt="Monkey GIF"/>
</p>

|  | Previous Page | Next Page |
|----------|----------|------|
| Puree is under active development. APIs may change between versions. **Special thanks to the open-source community and the developers behind the projects that make puree possible.** || [Documentation](DOCS.md) |