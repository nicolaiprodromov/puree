<div align="center">

<img src="docs/Asset 1.png" alt="Puree UI Logo" width="100%"/>

<br>

*A declarative UI framework for Blender addons and much more*



</div>

<div align="center">

[![Version](https://img.shields.io/badge/dynamic/toml?url=https://raw.githubusercontent.com/nicolaiprodromov/Puree1/main/blender_manifest.toml&query=$.version&label=version&color=blue&style=flat)](https://github.com/nicolaiprodromov/Puree1)
[![Release](https://img.shields.io/github/v/release/nicolaiprodromov/Puree1?style=flat&color=blue)](https://github.com/nicolaiprodromov/Puree1/releases)


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
