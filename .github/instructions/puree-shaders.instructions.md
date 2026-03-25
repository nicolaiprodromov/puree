---
description: "Use when editing Puree GLSL shaders. Covers buffer layout, coordinate system, color space, and compute shader patterns."
applyTo: "puree/shaders/*.glsl"
---

# Puree Shaders — GLSL Conventions

Puree renders UI via ModernGL compute shaders targeting OpenGL 4.3.

## Shader Files

| File | Purpose |
|------|---------|
| `container.glsl` | Main compute shader — renders all containers |
| `outline.glsl` | Debug outline rendering |
| `container_draw.vert` | Vertex shader for final composite |
| `container_draw.frag` | Fragment shader for final composite |

## Buffer Layout — CRITICAL

Container data arrives as a flat SSBO (Shader Storage Buffer Object). Each container is a fixed-stride block of floats. **The unpacking offsets in GLSL MUST match the packing order in `render.py`.**

If you change the stride or order in either file, you MUST update the other.

## Coordinate System

- Origin: **top-left** of the panel
- X: increases rightward
- Y: increases **downward** (matches CSS convention, NOT OpenGL default)
- Positions and sizes are in **pixels** (screen space)

## Color Space

- All colors in the buffer are **linear** (not sRGB)
- sRGB→linear conversion happens in Python/Rust before GPU upload
- Shader output is linear — Blender handles final display transform
- When blending colors (e.g., alpha compositing), operations are correct in linear space

## Compute Shader Patterns

```glsl
layout(local_size_x = 16, local_size_y = 16) in;

// Container data SSBO
layout(std430, binding = 0) buffer ContainerData {
    float data[];
};

// Output texture
layout(rgba32f, binding = 0) uniform image2D outputImage;

void main() {
    ivec2 pixel = ivec2(gl_GlobalInvocationID.xy);
    // ... process each pixel against all containers
}
```

## Common Operations

### Point-in-rectangle test (with border radius)
Containers can have rounded corners. Check if a pixel is inside the rounded rect, not just the bounding box.

### Alpha blending
Containers are drawn back-to-front. Use standard alpha compositing:
```glsl
vec4 blend(vec4 src, vec4 dst) {
    float a = src.a + dst.a * (1.0 - src.a);
    vec3 c = (src.rgb * src.a + dst.rgb * dst.a * (1.0 - src.a)) / max(a, 0.001);
    return vec4(c, a);
}
```

### Display: none
Containers with `display: none` should be skipped entirely — don't process them.

## Performance Notes

- Minimize branching per-pixel — GPU threads diverge on branches
- Early-exit for hidden containers
- The compute shader processes ALL containers for each pixel — O(pixels × containers)
- Reducing container count has quadratic impact on shader time
