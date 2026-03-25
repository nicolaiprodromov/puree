---
description: "Debug a Puree engine issue. Systematically traces through the rendering pipeline, event system, or parser to find root cause."
agent: puree-maintainer
argument-hint: "Describe the engine-level symptom (e.g. 'containers render at wrong position', 'hit detection misses elements near edges')"
---

A Puree engine-level issue needs debugging. This is for framework internals, not user YAML/SCSS problems.

## Step 1: Classify the Issue

Determine the subsystem:
- **Rendering** (wrong visuals) → `render.py`, `shaders/container.glsl`
- **Layout** (wrong positions/sizes) → `parser.py`, stretchable/Taffy
- **Events** (wrong/missing interactions) → `hit_op.py`, `input_router.py`
- **Text** (missing/wrong text) → `text_op.py`, `extract_text.py`
- **Images** (missing/wrong images) → `img_op.py`, `extract_images.py`
- **Hot reload** (crashes/stale) → `hot_reload.py`, `native_bindings.py`
- **Styles** (CSS not applying) → `native_bindings.SCSSCompiler`, `parser.py`

## Step 2: Trace the Data Flow

Read the relevant modules and trace data from input to output:
1. Where does the data enter the pipeline?
2. What transformations occur?
3. Where does the output go?
4. At which step does the behavior diverge from expected?

## Step 3: Check Common Causes

- **Buffer stride mismatch**: Python packing ↔ GLSL unpacking offsets
- **Color space**: sRGB vs linear conversion missing/doubled
- **Stale cache**: SCSS mtime cache, hit detection position cache
- **Context loss**: ModernGL context invalidated during hot reload
- **Threading**: bpy API called from non-main thread
- **Coordinate system**: Y-down convention not applied consistently

## Step 4: Fix and Verify

1. Make the minimal fix
2. Run `just dev-link && just dev-reload`
3. Verify the fix doesn't break other subsystems
4. Update documentation if the fix reveals a broader pattern

Reference: [KNOWLEDGE_BASE.md](../../docs/KNOWLEDGE_BASE.md) | [API.md](../../docs/API.md)
