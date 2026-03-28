---
description: "Add a new CSS property to and trace it through all layers of the Puree engine (Style → Rust → GPU → GLSL)."
agent: puree-maintainer
argument-hint: "Describe the CSS property to add (e.g. 'text-indent', 'outline', 'backdrop-filter')"
---

Add a new CSS property to the Puree rendering pipeline. This requires coordinated changes across multiple layers.

## Checklist

### 1. Style Class (`puree/components/style.py`)
- [ ] Add property field with correct type and default value
- [ ] Add hover/active variants if needed
- [ ] Document the property

### 2. Rust Parser (`puree/puree_core/src/`)
- [ ] Add CSS property name → field mapping
- [ ] Add value parser (color, length, enum, etc.)
- [ ] Handle shorthand if applicable
- [ ] Run `just build_core`

### 3. GPU Buffer (`puree/render.py`)
- [ ] Add property value to buffer packing
- [ ] Update stride constant if adding new floats
- [ ] Verify all other offsets still correct

### 4. GLSL Shader (`puree/shaders/container.glsl`)
- [ ] Unpack property at matching offset
- [ ] Implement rendering logic
- [ ] Test with display: none (should be skipped)

### 5. Optional: Transitions (`puree/transition_manager.py`)
- [ ] If animatable: add interpolation support
- [ ] Update the "3 animatable properties" documentation

### 6. Documentation
- [ ] `docs/PUREE_SPEC.md` — property reference table
- [ ] `docs/API.md` — Style class property list
- [ ] `docs/PUREE_VS_CSS.md` — compatibility notes
- [ ] `.github/agents/puree-coder.agent.md` — supported properties
- [ ] `.github/instructions/puree-scss.instructions.md` — SCSS conventions

### 7. Testing
- [ ] Create test YAML/SCSS using the new property
- [ ] Test default value, explicit value, hover/active states
- [ ] Test transitions if animatable
- [ ] Test hot reload

Use the `/extend-property` skill for detailed guidance on each step.
