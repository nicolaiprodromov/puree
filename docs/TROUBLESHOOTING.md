---
layout: page
title : 6. Troubleshooting
---

## Linux

- *"Failed to get ModernGL context: libGL.so: cannot open shared object file: No such file or directory*" — `sudo apt install libgl1-mesa-dev`
- *"Can't get over 30fps on linux"* — `__GL_SYNC_TO_VBLANK=0 blender` (start blender from terminal without vsync)

## Hot Reload

- **Changes not appearing after save** — The SCSS cache uses mtime only. After `git checkout`, touch the file: `touch style.scss`
- **ModernGL crash on rapid saves** — The GL context is shared with Blender. Rapid file saves during hot reload can crash it. Save once and wait for the reload to finish.
- **Reload server not responding** — Check `just logs` or `puree reload` output. The TCP server on `127.0.0.1:19746` auto-starts with the addon. Restart Blender if it's stuck.

## Rendering

- **Container not updating after property change** — Call `mark_dirty()` on the container after any style or text change. **Root cause:** Puree uses a dirty-flagging optimization — the GPU only re-packs and re-uploads container data when at least one container is marked dirty. Without this flag, the render loop skips the buffer update entirely, so your changes exist in Python but never reach the shader.
- **Hit detection broken after panel resize** — The hit detection cache can become stale. Trigger a full re-render by resizing the panel slightly.
- **Text rendering lagging behind containers** — Text renders in a separate pass from GPU containers. This is normal for the first frame after a change.

## Dynamic Containers

- **`add_child()` not showing new container** — Always call `parent.mark_dirty()` after adding/removing children.
- **Component template not found** — Ensure the component exists in `components/` and use the `[component_name]` bracket syntax.

## Focus & Keyboard

- **`focus()` not working** — The container must have `focusable: true` and `tab_index` set in YAML.
- **Keyboard shortcut not firing** — Check the `when` parameter. Container-scoped shortcuts only fire when that container has focus.

## Networking

- **HTTP callback not executing** — The HTTP drain timer must be registered. Check `just logs` for errors. Remember callbacks run on the main thread via `bpy.app.timers`.
- **SSE stream not receiving events** — Verify the URL and that the server sends `text/event-stream` content type.

## Storage

- **Data not persisting between sessions** — Ensure `auto_save=True` or call `storage.save()` explicitly. Check the storage scope (`"global"` vs `"project"`).

## Virtual Scroll

- **Virtual scroll showing nothing** — You must call both `set_virtual_data(items)` and `set_item_renderer(fn)` before it renders.

## Collapse

- **Collapse not animating** — The first child of a collapsible container acts as the header (always visible). The remaining children are collapsed. Call `mark_dirty()` after toggle.

## Debugging Methodology

When your UI isn't behaving as expected, follow this systematic approach:

### Step 1: Check the logs
```bash
just logs          # or: just tail (live-follow)
puree reload       # also prints any errors
```
Look for Python exceptions, SCSS compilation errors, or YAML parse failures.

### Step 2: Verify the basics
- Is `mark_dirty()` called after every property change?
- Are display values uppercase in Python? (`'FLEX'` not `'flex'`)
- Are YAML node names using underscores? (`my_button` not `my-button`)
- Does the component exist in `components/` with matching name?

### Step 3: Isolate the layer
- **YAML issue?** — Check node IDs, component references (`[name]`), parameter syntax (`"{{name, 'default'}}"`)
- **SCSS issue?** — Try `touch style.scss` to clear cache. Check selector specificity.
- **Python issue?** — Add `print()` calls in handlers. Check `just logs` for output.
- **Rendering issue?** — Enable debug outlines in the panel. Check if container is at the right position.

### Step 4: Minimal reproduction
Strip your UI down to the simplest case that reproduces the issue. This often reveals the problem immediately.

See the [Knowledge Base](KNOWLEDGE_BASE.md#debugging-cheat-sheet) for a comprehensive 18-item debugging cheat sheet.

---

|  | Previous Page | Next Page |
|----------|----------|------|
| Puree is under active development. APIs may change between versions. **Special thanks to the open-source community and the developers behind the projects that make puree possible.** | [Puree vs CSS](PUREE_VS_CSS.md) | [Get Help](SUPPORT.md) |