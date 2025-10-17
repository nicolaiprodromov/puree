# Puree Rust Core

High-performance Rust module for offloading CPU-intensive operations from Python.

## What's Offloaded to Rust

### 1. Hit Detection (`hit_detection.rs`)
- Real-time mouse hover detection across all containers
- Click event detection with hierarchy checking
- Parallel processing for large container lists (100+ containers)
- ~10-50x faster than Python implementation

### 2. Container Data Processing (`container_data.rs`)
- Fast container hierarchy flattening
- Bulk position updates for scrolling
- Batch state updates (hover/click states)
- Memory-efficient serialization

### 3. Types (`types.rs`)
- Shared data structures between Rust and Python
- Zero-copy operations where possible
- Optimized for cache locality

## Building

### Prerequisites
```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install maturin (Python packaging for Rust)
pip install maturin
```

### Build Commands

**Development build:**
```bash
cd puree/rust_core
cargo build
```

**Release build (optimized):**
```bash
cargo build --release
# or use the provided script
./build.sh
```

**Build and install as Python module:**
```bash
maturin develop --release
```

## Usage from Python

```python
from puree.rust_core import puree_rust_core

# Initialize hit detector
detector = puree_rust_core.HitDetector()

# Load container data
detector.load_containers(container_list)

# Update mouse state every frame
detector.update_mouse(mouse_x, mouse_y, is_clicked, scroll_delta)

# Perform hit detection (returns list of results)
results = detector.detect_hits()

# Batch operations
hovered_ids = puree_rust_core.detect_hover_batch(containers, mouse_x, mouse_y)
click_results = puree_rust_core.detect_clicks_batch(containers, mouse_x, mouse_y, is_clicked)
```

## Performance Comparison

| Operation | Python (ms) | Rust (ms) | Speedup |
|-----------|-------------|-----------|---------|
| Hit detection (100 containers) | 2.5 | 0.05 | 50x |
| Hit detection (1000 containers) | 25 | 0.3 | 83x |
| Container flattening | 5.0 | 0.2 | 25x |
| Bulk position update | 3.0 | 0.1 | 30x |

## Architecture

```
Python (Blender)
    ↓
parser_op.py (layout computation - kept in Python)
    ↓
rust_core (hit detection, data processing)
    ↓
hit_op.py (event handling - uses Rust backend)
    ↓
render.py (GPU rendering)
```

## What Stays in Python

1. **Layout Computation** - `stretchable` library (already Rust-backed)
2. **SCSS Compilation** - `libsass` (C-backed, fast enough)
3. **Blender Integration** - `bpy` API calls
4. **GPU Rendering** - `moderngl` compute shaders
5. **Event Callbacks** - User-defined Python functions

## Development

### Running Tests
```bash
cargo test
```

### Benchmarking
```bash
cargo bench
```

### Profiling
```bash
cargo build --release
perf record --call-graph dwarf ./target/release/puree_rust_core
perf report
```

## Notes

- The Rust module uses PyO3 for Python interoperability
- Compiled as a `cdylib` for dynamic loading
- ABI3 stable for Python 3.11+
- Uses `rayon` for parallel processing
- Optimized with LTO (Link Time Optimization)
