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
  <a href="https://www.blender.org/"><img src="https://img.shields.io/badge/Blender-5.1%2B-orange?style=flat&logo=blender&logoColor=white" alt="Blender"/></a>
  <a href="https://github.com/nicolaiprodromov/puree/tree/master/puree/puree_core"><img src="https://img.shields.io/badge/Rust-core-blueviolet?style=flat&logo=rust&logoColor=white" alt="Rust core"/></a>
</p>

<p align="center">
    <img src="https://img.shields.io/badge/API-UNSTABLE-red?style=flat-square" alt="API Unstable"/>
</p>

**Puree UI** for Blender is a declarative framework that provides a web-inspired API for building user interfaces, addressing the limitations of Blender's native UI system in supporting complex interface architectures and providing enhanced flexibility.

It's meant for all Blender users that want to enhance their ability to present their creations, models, addons and products inside the software in a streamlined, easy & intuitive way, adaptable to causal users and powerful enough for seasoned programmers.

> Puree is built on top of **Blender's native GPU module**, **grass** (Rust SCSS compiler), and the **Taffy** layout engine to deliver a high-performance, GPU-accelerated UI engine with a familiar web development paradigm.

---

## What is puree good for?

From addon user interfaces to complex object-based tracking in screen space, to interactive tutorials, to markdown rendering directly in Blender, to simple drawing anywhere in Blender, in real-time, using the gpu. Check the [tests](https://github.com/nicolaiprodromov/puree/tree/master/tests) folder for a complete example of what can be accomplished with **puree**.

<p align="center">
  <img src="images/example1.gif" alt="Example 1 UI GIF" width="100%"/>
</p>

## Key Features

| Feature | Description |
|---------|-------------|
| **Declarative UI Design** | Define your interface structure using YAML configuration files with HTML-like nesting |
| **GPU-Accelerated Rendering** | Draws the whole interface in a single batched SDF pass through Blender's native GPU module |
| **Responsive Layouts** | Automatic layout computation using the Taffy flexbox/grid engine |
| **Interactive Components** | Built-in support for hover states, click events, scrolling, keyboard shortcuts, focus management, and collapse/expand |
| **Built-in Modules** | Storage persistence, HTTP/SSE networking, timers, markdown rendering, virtual scrolling, and more |
| **Web-Inspired Architecture** | Familiar paradigm for developers coming from web development |

---

## Quick Start

Here's how to get started with Puree:

> [!IMPORTANT]
> You'll need **Python 3.11+** for the CLI and **Blender 5.1+** available on your system PATH — the CLI drives Blender directly for scaffolding, building, and installing.

1. **Install puree:**

    ```bash
    pip install puree-ui
    ```

2. **Create a new project:**

    ```bash
    mkdir my_addon && cd my_addon
    puree init
    ```

    This creates a complete project with all dependencies, a `blender_manifest.toml`, and a starter UI (a pink page with "PUREE" in blue text).

3. **Build the extension:**

    ```bash
    puree build
    ```

    The packaged extension zip lands in `dist/`.

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

Puree follows a render pipeline inspired by modern web browsers (simplified view — see [Knowledge Base](KNOWLEDGE_BASE.md) for full details):

1. **Parse** – YAML/SCSS files are loaded and parsed into a container tree with styles (SCSS compiled and cascaded in Rust)
2. **Compile** – Python scripts transform the UI tree (event handlers, dynamic content)
3. **Layout** – Taffy computes flexbox/grid layouts with viewport-aware sizing
4. **Render** – Blender's native GPU module draws all containers in one batched pass with an SDF fragment shader
5. **Event** – Mouse/scroll/keyboard events update container states and trigger re-renders (hit detection in Rust)

This architecture enables:

- **Reactive updates** – Layout recomputes on viewport resize
- **GPU acceleration** – The whole interface renders in a single batched SDF draw call
- **Script integration** – Python scripts can modify UI at runtime
- **Event propagation** – Interactions flow through container hierarchy

> Read the full [documentation](DOCS.md) for detailed guides, API references, and examples.

---

## Documentation Guide

New to Puree? Follow this recommended reading order:

| # | Document | Level | What You'll Learn |
|---|----------|-------|-------------------|
| 1 | [Documentation](DOCS.md) | Beginner | File structure, YAML/SCSS/Python walkthrough, installation |
| 2 | [Components](COMPONENTS.md) | Beginner | Component system, parameters, namespacing |
| 3 | [API Reference](API.md) | Intermediate | CSS properties, Container methods, built-in modules |
| 4 | [Puree Spec](PUREE_SPEC.md) | Reference | Authoritative property tables, rules & constraints |
| 5 | [Puree vs CSS](PUREE_VS_CSS.md) | Reference | CSS compatibility, selectors, Puree extensions |
| 6 | [Knowledge Base](KNOWLEDGE_BASE.md) | Intermediate | Architecture decisions, debugging cheat sheet, patterns |
| 7 | [Troubleshooting](TROUBLESHOOTING.md) | All levels | Common problems and solutions |
| 8 | [Support](SUPPORT.md) | All levels | Getting help, reporting issues |

See the full [Documentation Map](docs-path.md) for details on each page.

---

## Built With

- [Blender](https://www.blender.org/) - 3D creation suite (rendering via its native `gpu` module)
- [Python](https://www.python.org/) - Programming language
- [Rust](https://www.rust-lang.org/) - SCSS compilation, CSS cascade, hit detection, and file watching (via puree_core)
- [GLSL](https://www.khronos.org/opengl/wiki/OpenGL_Shading_Language) - Shading language for the SDF container shader
- [Stretchable](https://github.com/mortenwh/stretchable) - Flexbox/grid layout engine (Rust/Taffy)
- [grass](https://github.com/connorskees/grass) - SCSS compiler (Rust, via puree_core)
- [YAML](https://yaml.org/) - Configuration format

---

<p align="center">
  <img src="images/munky.gif" width="100px" alt="Monkey GIF"/>
</p>

|  | Previous Page | Next Page |
|----------|----------|------|
| Puree is under active development. APIs may change between versions. **Special thanks to the open-source community and the developers behind the projects that make puree possible.** || [Documentation](DOCS.md) |