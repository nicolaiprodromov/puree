---
name: extend-property
description: 'Add a new CSS property to the Puree engine. Walks through all layers that need changes: Style class, parser/cascade, GPU buffer, GLSL shader, and optionally transitions.'
user-invocable: true
argument-hint: 'Describe the property to add (e.g. "backdrop-filter blur", "cursor style", "outline property")'
---

Add a new CSS property to Puree's rendering pipeline. This is multi-layer work that touches Python, Rust, and GLSL.

## Procedure

### 1. Design the Property

Before writing code, decide:

- **Property name**: Use standard CSS naming where possible (`outline-width`, not `--puree-outline-width`)
- **Value type**: color, length (px/%), enum, float, shorthand?
- **Default value**: What does "unset" mean for this property?
- **Inheritance**: Should children inherit this? (Only `color`, `font-size`, `text-align` currently inherit)
- **Animatable**: Can it transition? (Currently only `background-color`, `color`, `border-color`, `opacity`)
- **Has hover/active states**: Does it change on interaction?
- **Shorthand**: Is there a shorthand form? (e.g., `border` is shorthand for `border-width` + `border-color` + `border-style`)

### 2. Style Class — `puree/components/style.py`

Add the property field with its default:

```python
# In the Style class
class Style:
    # ... existing properties ...
    new_property: float = 0.0  # or appropriate type and default
```

If it has hover/active variants:
```python
    hover_new_property: Optional[float] = None
    click_new_property: Optional[float] = None
```

### 3. Parser/Cascade — Rust Side

The CSS cascade runs in Rust via `native_bindings.SCSSCompiler`. For the parser to recognize the new property:

1. Read `puree/puree_core/src/` — find where CSS properties are mapped
2. Add the property name → Style field mapping
3. Add the value parser (color parser, length parser, enum parser, etc.)
4. Handle shorthand expansion if applicable
5. Rebuild: `just build_core`

### 4. GPU Buffer — `puree/render.py`

The render pipeline packs containers into a flat buffer for the GPU:

1. Find the buffer packing code in `render.py`
2. Add the new property value at the correct offset
3. Update the stride constant if adding new floats
4. **CRITICAL**: If you change the stride, EVERY container's data shifts. Update ALL offsets.

### 5. GLSL Shader — `puree/shaders/container.glsl`

1. Unpack the new value at the matching offset
2. Use it in the rendering logic
3. **CRITICAL**: Buffer offsets must match Python packing exactly

### 6. Transitions (Optional) — `puree/transition_manager.py`

If the property should be animatable:

1. Add it to the list of animatable properties
2. Implement interpolation (linear for floats, component-wise for colors)
3. Update the animatable property documentation

### 7. Documentation

Update these files:
- `docs/PUREE_SPEC.md` — Full property reference table
- `docs/API.md` — Style class property list
- `docs/PUREE_VS_CSS.md` — CSS compatibility notes
- `.github/agents/puree-coder.agent.md` — Agent knowledge of supported properties
- `.github/instructions/puree-scss.instructions.md` — SCSS instruction file

### 8. Testing

1. Create a test YAML/SCSS that uses the new property
2. Test with default value (no explicit setting)
3. Test with explicit value
4. Test with hover/active states if applicable
5. Test transitions if animatable
6. Test hot reload (change value, save, verify update)

### Checklist

- [ ] Style class field with correct type and default
- [ ] Rust parser recognizes the CSS property name
- [ ] Rust parser handles the value type correctly
- [ ] GPU buffer packing includes the new value
- [ ] GLSL shader unpacks at the correct offset
- [ ] Buffer stride updated if adding floats
- [ ] Hover/active variants if applicable
- [ ] Transition support if animatable
- [ ] Documentation updated (PUREE_SPEC, API, PUREE_VS_CSS)
- [ ] Agent/instruction files updated
- [ ] Tested in Blender
