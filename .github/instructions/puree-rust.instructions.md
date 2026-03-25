---
description: "Use when editing Puree Rust core (puree_core/). Covers PyO3 bindings, HitDetector, SCSSCompiler, ColorProcessor, and build workflow."
applyTo: "puree/puree_core/**"
---

# Puree Core — Rust Conventions

The `puree_core` crate provides native performance for hot paths: hit detection, SCSS compilation, color processing, and file watching.

## Build Workflow

```bash
just build_core     # Compile and copy to native_binaries/
```

After ANY Rust change, rebuild before testing. The compiled binary (`.so`/`.pyd`/`.dylib`) is loaded at Blender startup.

## PyO3 Bindings

All public functions are exposed to Python via PyO3:

```rust
use pyo3::prelude::*;

#[pyclass]
struct HitDetector {
    // ...
}

#[pymethods]
impl HitDetector {
    #[new]
    fn new() -> Self { ... }
    
    fn detect(&self, x: f32, y: f32, containers: Vec<f32>) -> Option<String> { ... }
}
```

Python side (`native_bindings.py`) wraps these classes.

## Key Components

### HitDetector
- Takes mouse position + container buffer
- Returns the container ID under the cursor
- Uses the same position data as the GPU (must stay in sync)
- Performance-critical: called on every mouse move

### SCSSCompiler
- Wraps the `grass` crate (Dart Sass port in Rust)
- Compiles SCSS → CSS
- Applies CSS cascade (specificity, inheritance)
- Caches compiled results by file mtime

### ColorProcessor
- Converts sRGB → linear color space
- Parses CSS color formats (#hex, rgb(), rgba(), named colors)
- All colors sent to GPU must go through this

### PyFileWatcher
- Poll-based file watcher (not inotify/FSEvents)
- ~300ms debounce interval
- Monitors configured directories for changes
- Triggers callbacks on file modify/create/delete

## Color Space Rules

Blender's viewport uses **linear color space**. CSS colors are in sRGB. Every color must be converted:

```rust
fn srgb_to_linear(c: f32) -> f32 {
    if c <= 0.04045 {
        c / 12.92
    } else {
        ((c + 0.055) / 1.055).powf(2.4)
    }
}
```

## Error Handling

- Rust panics become Python exceptions via PyO3
- Use `PyResult<T>` for functions that can fail gracefully
- Log warnings for recoverable issues, panic for invariant violations

## Platform Considerations

- Linux: `.so` binary
- Windows: `.pyd` binary  
- macOS: `.dylib` binary
- Compile for the target platform's Python version (must match Blender's bundled Python)
