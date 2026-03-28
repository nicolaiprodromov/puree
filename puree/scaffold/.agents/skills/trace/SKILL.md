---
name: trace
description: 'Trace data flow through the Puree engine for a specific feature or behavior. Use to understand how a CSS property, event, or render feature works end-to-end across Python, Rust, and GLSL layers.'
user-invocable: true
argument-hint: 'Describe what to trace (e.g. "how background-color gets from SCSS to GPU", "how click events reach user callbacks")'
---

Trace the complete data flow for a Puree feature from input to output. Produces a documented path through all engine layers.

## Procedure

### 1. Identify the Trace Target

What are we tracing? Pick one:
- **CSS property flow**: SCSS source → compiled CSS → cascade → Style field → GPU buffer → shader
- **Event flow**: Blender event → operator → hit detection → routing → user callback
- **Render flow**: Container tree → flatten → buffer pack → GPU upload → shader → composite
- **Layout flow**: Style dimensions → Taffy input → Taffy compute → final positions
- **Hot reload flow**: File change → watcher → reparse → recompile → re-render
- **Component flow**: YAML `data: '[name]'` → template load → parameter substitution → tree merge

### 2. Read Each Layer

For the chosen flow, read the relevant source files in order. Document:
- **Entry point**: Where does the data enter this layer?
- **Transformation**: What happens to the data?
- **Output**: Where does it go next?
- **Key variables**: What are the important variable/field names?
- **Edge cases**: What can go wrong at this layer?

### 3. Document the Full Path

Produce a trace document like:

```
[Layer 1: SCSS File]
  Input: .button { background-color: #3498db; }
  Processed by: grass (via SCSSCompiler in native_bindings.py)
  Output: Compiled CSS rule with resolved variables/mixins

[Layer 2: CSS Cascade]
  Input: Compiled CSS rules
  Processed by: Rust cascade engine (SCSSCompiler.apply_cascade)
  Output: Resolved property values per container (specificity-ordered)

[Layer 3: Style Application]
  Input: Cascaded property values
  Processed by: parser.py — applies values to Container.style fields
  Output: Container.style.background_color = (0.204, 0.596, 0.859, 1.0)  # linear space

[Layer 4: GPU Buffer Packing]
  Input: Container.style.background_color
  Processed by: render.py — packs into SSBO at offset N
  Output: 4 floats at buffer[container_index * STRIDE + BG_COLOR_OFFSET]

[Layer 5: GLSL Shader]
  Input: SSBO data at offset
  Processed by: container.glsl — reads vec4 at matching offset
  Output: Fragment color for pixels within container bounds
```

### 4. Identify Extension Points

Note where changes would be needed to:
- Add a new property following this path
- Modify the behavior at each layer
- Debug issues at each layer

### 5. Report

Produce the complete trace with:
- Flow diagram (text-based)
- Per-layer details with file paths and line numbers
- Key data transformations
- Known issues or fragile points in the path
