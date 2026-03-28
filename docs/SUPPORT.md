---
layout: page
title: 7. Support
---

<img src="https://img.shields.io/badge/OpenGL%20Backend-ONLY-orange?style=flat-square" alt="OpenGL Only"/>
<img src="https://img.shields.io/badge/API-UNSTABLE-red?style=flat-square" alt="API Unstable"/>

If you need help with this project, please try the following:

### Documentation

- Check the [README](README.md) for setup and usage instructions
- Check the [Full Documentation](https://nicolaiprodromov.github.io/puree/) for a deep dive into puree.

### Issues

- Search [existing issues](../../issues) to see if your question has been answered
- Create a [new issue](../../issues/new) if you've found a bug or have a feature request

### Discussions

- Use [GitHub Discussions](../../discussions) for questions and community support

## Reporting Security Issues

If you discover a security vulnerability, please **do not** open a public issue. Instead, please report it privately through GitHub's Security Advisory feature or by contacting the maintainers directly.

## Contributing

Interested in contributing? Please refer to [Contributing](CONTRIBUTING.md) for guidelines.

---

## Frequently Asked Questions

**Q: My container isn't updating after I change a property. What's wrong?**
A: You must call `container.mark_dirty()` after every property change. The GPU doesn't re-render without it. This is the #1 most common issue.

**Q: Why are my display values not working in Python?**
A: Runtime display values must be **UPPERCASE**: `'FLEX'`, `'NONE'`, `'BLOCK'`, `'GRID'`. SCSS uses lowercase (`flex`, `none`), but Python runtime uses uppercase.

**Q: Can I use `font-family` in my SCSS?**
A: No. Font selection is done via the YAML `font:` attribute on the container node, not through CSS. Specify the font name without file extension.

**Q: Why doesn't my hover change the width/height?**
A: Layout properties (`width`, `height`, `padding`, `margin`) are **silently ignored** in `:hover` and `:active` states. Only `background-color`, `border-color`, `opacity`, and `color` can change on hover.

**Q: Does Puree work with Blender's Vulkan/Metal backends?**
A: No. Puree requires the **OpenGL backend** due to its ModernGL dependency. Blender must be running with OpenGL.

**Q: How do I call Blender `bpy` APIs from event handlers?**
A: Simple `bpy` calls work directly in click/hover handlers since they run on the main thread. For background threads, use `bpy.app.timers.register(fn)` to schedule calls on the main thread. See the [Threading & Blender Safety](DOCS.md#threading--blender-safety) section.

**Q: Can I use `calc()`, `clamp()`, or viewport units (`vw`, `vh`)?**
A: No. Only `px` and `%` units are supported. Use fixed values or restructure your layout with flexbox (`flex-grow`, `flex-shrink`).

**Q: How do I hide a container completely?**
A: Set `display: 'NONE'` and call `mark_dirty()`. If using `height: 0`, you must also clear `padding` and `border-width` to fully hide the element.

**Q: What Blender version do I need?**
A: Blender **5.1+** is required. Earlier versions are not supported.

**Q: How does hot reload work?**
A: Save your YAML/SCSS file — the file watcher detects changes automatically and triggers reparse/re-render. For Python changes, run `puree reload` (which sends a TCP command to the running Blender instance). See the [Knowledge Base](KNOWLEDGE_BASE.md#hot-reload--how-it-works-and-breaks) for details.

---

|  | Previous Page | Next Page |
|----------|----------|------|
| Puree is under active development. APIs may change between versions. **Special thanks to the open-source community and the developers behind the projects that make puree possible.** | [Troubleshooting](TROUBLESHOOTING.md) | [Home](index.md) |