---
description: "Use when editing Puree GLSL shaders. Covers buffer layout, coordinate system, color space, and compute shader patterns."
applyTo: "puree/shaders/*.glsl"
---

# Puree Shaders — GLSL Conventions

Puree renders UI via ModernGL compute shaders targeting OpenGL 4.3. There are two parallel rendering paths: a **compute shader path** (container.glsl + outline.glsl) and a **native draw path** (container_draw.vert + container_draw.frag). Both consume the same 68-float-per-container data layout.

## Shader Files

| File | Purpose | Rendering Path |
|------|---------|---------------|
| `container.glsl` | Main compute shader — renders all containers per-pixel | Compute (SSBO) |
| `outline.glsl` | Debug outline rendering (reads compute output + overlays) | Compute (SSBO) |
| `container_draw.vert` | Vertex shader — expands per-container quads | Native draw (data texture) |
| `container_draw.frag` | Fragment shader — SDF rendering per-container | Native draw (data texture) |

### Compute path vs Native draw path

- **Compute path**: `container.glsl` iterates ALL containers for each pixel (O(pixels × containers)). Uses SSBO (`std430` buffer binding). Used for the outline debug overlay.
- **Native draw path**: `container_draw.vert` + `container_draw.frag` draw one instanced quad per container. Uses an RGBA32F data texture (17 texels per container = 68 floats). This is the primary rendering path.

Both paths read the **same** 68-float struct — the only difference is **how** they access it (SSBO array vs texelFetch).

---

## Buffer Layout — CRITICAL

### Stride

**`CONTAINER_STRIDE = 68`** floats per container (defined in `render.py`).

In the native draw path this is **17 RGBA32F texels** (17 × 4 = 68 floats). In the compute path it is a flat `float[]` SSBO indexed with `offset = index * 68`.

**The unpacking offsets in GLSL MUST match the packing order in `render.py` `_build_container_struct()`.**

If you change the stride, packing order, or add/remove a field in **any** of these files, you MUST update all of them.

### Complete Offset Map (68 floats)

The table below maps every float offset to its meaning. The "Texel" column shows which RGBA32F texel and component it corresponds to in the native draw path.

| Offset | Texel | Component | Field | Python source (`_build_container_struct`) |
|--------|-------|-----------|-------|------------------------------------------|
| 0 | T0.x | R | `display` | `int(container.get('display', False))` — 1=visible, 0=hidden |
| 1 | T0.y | G | `position.x` | `position[0]` |
| 2 | T0.z | B | `position.y` | `position[1]` |
| 3 | T0.w | A | `size.x` (width) | `size[0]` |
| 4 | T1.x | R | `size.y` (height) | `size[1]` |
| 5 | T1.y | G | `color.r` | `bg_color[0]` — background color (linear) |
| 6 | T1.z | B | `color.g` | `bg_color[1]` |
| 7 | T1.w | A | `color.b` | `bg_color[2]` |
| 8 | T2.x | R | `color.a` | `bg_color[3]` |
| 9 | T2.y | G | `color_1.r` | `bg_color_2[0]` — gradient stop 2 |
| 10 | T2.z | B | `color_1.g` | `bg_color_2[1]` |
| 11 | T2.w | A | `color_1.b` | `bg_color_2[2]` |
| 12 | T3.x | R | `color_1.a` | `bg_color_2[3]` |
| 13 | T3.y | G | `color_gradient_rot` | `background_gradient_rot` — degrees |
| 14 | T3.z | B | `hover_color.r` | `hover_bg_color[0]` |
| 15 | T3.w | A | `hover_color.g` | `hover_bg_color[1]` |
| 16 | T4.x | R | `hover_color.b` | `hover_bg_color[2]` |
| 17 | T4.y | G | `hover_color.a` | `hover_bg_color[3]` |
| 18 | T4.z | B | `hover_color_1.r` | `hover_bg_color_2[0]` |
| 19 | T4.w | A | `hover_color_1.g` | `hover_bg_color_2[1]` |
| 20 | T5.x | R | `hover_color_1.b` | `hover_bg_color_2[2]` |
| 21 | T5.y | G | `hover_color_1.a` | `hover_bg_color_2[3]` |
| 22 | T5.z | B | `hover_color_gradient_rot` | `hover_background_gradient_rot` |
| 23 | T5.w | A | `click_color.r` | `click_bg_color[0]` |
| 24 | T6.x | R | `click_color.g` | `click_bg_color[1]` |
| 25 | T6.y | G | `click_color.b` | `click_bg_color[2]` |
| 26 | T6.z | B | `click_color.a` | `click_bg_color[3]` |
| 27 | T6.w | A | `click_color_1.r` | `click_bg_color_2[0]` |
| 28 | T7.x | R | `click_color_1.g` | `click_bg_color_2[1]` |
| 29 | T7.y | G | `click_color_1.b` | `click_bg_color_2[2]` |
| 30 | T7.z | B | `click_color_1.a` | `click_bg_color_2[3]` |
| 31 | T7.w | A | `click_color_gradient_rot` | `click_background_gradient_rot` |
| 32 | T8.x | R | `border_color.r` | `border_color[0]` |
| 33 | T8.y | G | `border_color.g` | `border_color[1]` |
| 34 | T8.z | B | `border_color.b` | `border_color[2]` |
| 35 | T8.w | A | `border_color.a` | `border_color[3]` |
| 36 | T9.x | R | `border_color_1.r` | `border_color_2[0]` — gradient stop 2 |
| 37 | T9.y | G | `border_color_1.g` | `border_color_2[1]` |
| 38 | T9.z | B | `border_color_1.b` | `border_color_2[2]` |
| 39 | T9.w | A | `border_color_1.a` | `border_color_2[3]` |
| 40 | T10.x | R | `border_color_gradient_rot` | `border_gradient_rot` |
| 41 | T10.y | G | `border_radius_tl` | Top-left corner radius |
| 42 | T10.z | B | `border_width` | Uniform border width |
| 43 | T10.w | A | `border_radius_tr` | Top-right corner radius |
| 44 | T11.x | R | `border_radius_br` | Bottom-right corner radius |
| 45 | T11.y | G | `box_shadow_offset.x` | Shadow X offset |
| 46 | T11.z | B | `box_shadow_offset.y` | Shadow Y offset |
| 47 | T11.w | A | `box_shadow_offset.z` / `shadow_spread` | Shadow spread (frag) / Z offset (compute) |
| 48 | T12.x | R | `box_shadow_blur` | Shadow blur radius |
| 49 | T12.y | G | `box_shadow_color.r` | Shadow color (linear) |
| 50 | T12.z | B | `box_shadow_color.g` | |
| 51 | T12.w | A | `box_shadow_color.b` | |
| 52 | T13.x | R | `box_shadow_color.a` | |
| 53 | T13.y | G | `passive` | 1=passive (no hover/click events) |
| 54 | T13.z | B | `visible` | Precomputed: 0 if this or any ancestor is hidden |
| 55 | T13.w | A | `clip_rect.x` | Precomputed clip rectangle X |
| 56 | T14.x | R | `clip_rect.y` | Precomputed clip rectangle Y |
| 57 | T14.y | G | `clip_rect.w` (width) | Precomputed clip rectangle width |
| 58 | T14.z | B | `clip_rect.h` (height) | Precomputed clip rectangle height |
| 59 | T14.w | A | `opacity` | Accumulated opacity (own × ancestors) |
| 60 | T15.x | R | `border_radius_bl` | Bottom-left corner radius |
| 61 | T15.y | G | `grad_row_normal` | Gradient texture row (normal state), -1=no texture |
| 62 | T15.z | B | `grad_row_hover` | Gradient texture row (hover state) |
| 63 | T15.w | A | `grad_row_click` | Gradient texture row (click state) |
| 64 | T16.x | R | `border_width_top` | Per-side border: top |
| 65 | T16.y | G | `border_width_right` | Per-side border: right |
| 66 | T16.z | B | `border_width_bottom` | Per-side border: bottom |
| 67 | T16.w | A | `border_width_left` | Per-side border: left |

### Precomputed fields (offsets 54–59)

These are written as defaults in `_build_container_struct()` and then **overwritten** by `_precompute_visibility_and_clips()` before GPU upload. They eliminate costly per-pixel parent chain walks in the shader:

- **visible** (54): 0 if the container or any ancestor has `display: none` or `visibility: hidden`
- **clip_rect** (55–58): intersection of all ancestor bounds (for overflow clipping)
- **opacity** (59): product of own opacity × all ancestor opacities

### How to read the Python packing side

In `render.py`, `_build_container_struct(container)` returns a flat Python list of 68 values. The return statement lists them in exact offset order:

```python
return [
    int(display),                    # 0: display
    position[0], position[1],        # 1-2: position
    size[0], size[1],                # 3-4: size
    bg_color[0..3],                  # 5-8: background color
    bg_color_2[0..3],                # 9-12: background gradient stop 2
    background_gradient_rot,         # 13: gradient rotation
    hover_bg_color[0..3],            # 14-17: hover background
    hover_bg_color_2[0..3],          # 18-21: hover gradient stop 2
    hover_background_gradient_rot,   # 22: hover gradient rotation
    click_bg_color[0..3],            # 23-26: click background
    click_bg_color_2[0..3],          # 27-30: click gradient stop 2
    click_background_gradient_rot,   # 31: click gradient rotation
    border_color[0..3],              # 32-35: border color
    border_color_2[0..3],            # 36-39: border gradient stop 2
    border_gradient_rot,             # 40: border gradient rotation
    border_radius_tl,                # 41: border radius TL
    border_width,                    # 42: uniform border width
    border_radius_tr,                # 43: border radius TR
    border_radius_br,                # 44: border radius BR
    shadow_offset[0..2],             # 45-47: shadow offset (x, y, spread)
    box_shadow_blur,                 # 48: shadow blur
    shadow_color[0..3],              # 49-52: shadow color
    int(passive),                    # 53: passive flag
    visible,                         # 54: precomputed visible
    clip_x, clip_y,                  # 55-56: precomputed clip origin
    clip_w, clip_h,                  # 57-58: precomputed clip size
    accumulated_opacity,             # 59: precomputed accumulated opacity
    border_radius_bl,                # 60: border radius BL
    grad_row_normal,                 # 61: gradient texture row (normal)
    grad_row_hover,                  # 62: gradient texture row (hover)
    grad_row_click,                  # 63: gradient texture row (click)
    bw_top, bw_right,               # 64-65: per-side border widths
    bw_bottom, bw_left,             # 66-67: per-side border widths
]
```

### How to read the GLSL unpacking side

**Compute path** (`container.glsl`, `outline.glsl`): reads from flat SSBO

```glsl
int offset = index * 68;
c.display  = int(container_data[offset + 0]);
c.position = vec2(container_data[offset + 1], container_data[offset + 2]);
c.size     = vec2(container_data[offset + 3], container_data[offset + 4]);
c.color    = vec4(container_data[offset + 5], ..., container_data[offset + 8]);
// ... every field at its exact offset
```

**Native draw path** (`container_draw.frag`): reads from RGBA32F data texture via `texelFetch`

```glsl
int texBase = idx * 17;
vec4 t0  = texelFetch(containerData, ivec2(texBase + 0,  0), 0);
vec4 t1  = texelFetch(containerData, ivec2(texBase + 1,  0), 0);
// ... 17 texel fetches total
// Then unpack: display = t0.x, pos = vec2(t0.y, t0.z), etc.
```

---

## Container Struct Fields

### Geometry
- **display** (offset 0): 1 = render this container, 0 = skip (`display: none`). Hidden containers are also culled at the vertex stage in the native path.
- **position** (1–2): top-left corner in CSS pixel space (x, y). Computed by the Taffy layout engine.
- **size** (3–4): width and height in pixels.

### Background colors (3 states × 2 gradient stops)
Each state has a primary color and a secondary gradient stop color:
- **color / color_1** (5–12, 13): Normal state. If `color_1.a > 0`, render as a linear gradient rotated by `color_gradient_rot` degrees.
- **hover_color / hover_color_1** (14–21, 22): Hover state. Applied when this container is the topmost hovered element and `passive == 0`. Includes `hover_color_gradient_rot`.
- **click_color / click_color_1** (23–30, 31): Active/click state. Applied when this container is clicked. Includes `click_color_gradient_rot`.

Priority: click > hover > normal. If the hover/click alpha is negative (`< 0`), the state is treated as "unset" and falls through to normal.

### Gradient rendering
Two-stop gradients use the inline `color`/`color_1` pairs with a rotation angle. Multi-stop gradients (3+ stops) are pre-rasterized into a 1D gradient texture; the row index is stored at offsets 61–63 (`grad_row_normal`, `grad_row_hover`, `grad_row_click`). A value of `-1` means "no gradient texture; use 2-color mix or solid."

### Border
- **border_color / border_color_1** (32–39, 40): Border color with optional gradient (same 2-stop pattern). `border_color_gradient_rot` at offset 40.
- **border_radius** (41, 43, 44, 60): Per-corner radii — TL (41), TR (43), BR (44), BL (60). The compute path only reads TL as a uniform radius; the native frag path uses all four for per-corner rounding.
- **border_width** (42): Uniform border width. The native path also reads per-side widths from texel 16.
- **border_width_top/right/bottom/left** (64–67): Per-side border widths. If any is > 0, overrides the uniform `border_width`. Only used by `container_draw.frag`.

### Box shadow
- **box_shadow_offset** (45–47): X, Y, and spread/Z offset. In the frag shader, offset 47 is interpreted as **spread** (expands the shadow shape). In the compute shader, it is treated as a Z component of a vec3.
- **box_shadow_blur** (48): Gaussian blur radius for the shadow.
- **box_shadow_color** (49–52): Shadow color (RGBA, linear space). Shadows are only rendered when `box_shadow_color.a > 0` AND `box_shadow_blur > 0` (or spread ≠ 0 in frag path).

### Flags & precomputed data
- **passive** (53): 1 = this container doesn't receive hover/click events. The shader forces `isHovered = false` and `isClicked = false` when passive.
- **visible** (54): CPU-precomputed. 0 if this container or any ancestor is hidden (`display: none` or `visibility: hidden`). Allows O(1) skip instead of walking the parent chain.
- **clip_rect** (55–58): CPU-precomputed intersection of all ancestor bounds. Used for overflow clipping with a simple `isPixelInClipRect()` test.
- **opacity** (59): Accumulated opacity — product of this container's opacity with all ancestor opacities.

---

## Coordinate System

- Origin: **top-left** of the panel
- X: increases rightward
- Y: increases **downward** (matches CSS convention, NOT OpenGL default)
- Positions and sizes are in **pixels** (screen space)
- The vertex shader converts from CSS pixel space (Y-down) to NDC (Y-up): `ndc.y = 1.0 - worldPos.y / viewportHeight * 2.0`

## Color Space

- All colors in the buffer are **linear** (not sRGB)
- sRGB→linear conversion happens in Python/Rust before GPU upload (via `ColorProcessor`)
- Shader output is linear — Blender handles final display transform
- When blending colors (e.g., alpha compositing), operations are correct in linear space
- The native draw path outputs **premultiplied alpha** for correct hardware blending

## Compute Shader Patterns

```glsl
layout(local_size_x = 16, local_size_y = 16) in;

// Mouse/time data
layout(std430, binding = 0) restrict readonly buffer MouseBuffer {
    vec2 mouse_pos;
    float time;
    float scroll_value;
    float click_value;
    float padding;
};

// Container data SSBO — flat array, stride = 68 floats
layout(std430, binding = 1) restrict readonly buffer ContainerBuffer {
    float container_data[];
};

// Viewport + state
layout(std430, binding = 2) restrict readonly buffer ViewportBuffer {
    vec2 viewportSize;
    float container_count_float;
    float hover_index_float;
    float click_index_float;
};

// Debug output
layout(std430, binding = 3) restrict writeonly buffer DebugBuffer {
    float debug_values[];
};

// Output texture
layout(rgba8, binding = 4) restrict writeonly uniform image2D output_texture;

void main() {
    ivec2 pixel = ivec2(gl_GlobalInvocationID.xy);
    // Loop over all containers back-to-front, composite
}
```

### Container retrieval in compute path
```glsl
Container getContainer(int index) {
    int offset = index * 68;
    Container c;
    c.display = int(container_data[offset + 0]);
    c.position = vec2(container_data[offset + 1], container_data[offset + 2]);
    // ... each field at its exact offset
    return c;
}
```

## Common Operations

### SDF-based rounded rectangle
All container shapes use a Signed Distance Field (SDF) for the rounded rectangle. This enables anti-aliased edges and smooth border rendering:

```glsl
float containerSDF(vec2 pixel, vec2 pos, vec2 sz, vec4 radii) {
    vec2 rel = pixel - pos - sz * 0.5;
    // Select corner radius based on quadrant: radii = (TL, TR, BR, BL)
    vec2 r_pair = (rel.x > 0.0) ? radii.yz : radii.xw;
    float r = (rel.y > 0.0) ? r_pair.y : r_pair.x;
    r = min(r, min(sz.x, sz.y) * 0.5);
    vec2 d = abs(rel) - sz * 0.5 + r;
    return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0) - r;
}
```

The compute path uses a simpler single-radius variant: `containerSDFDirect()`.

### Anti-aliasing
```glsl
float sdfAA(float dist) {
    return clamp(0.5 - dist * 0.5, 0.0, 1.0);
}
```

### Alpha blending (compute path)
Containers are drawn back-to-front. Use standard alpha compositing:
```glsl
finalColor.rgb = finalColor.rgb * (1.0 - src.a) + src.rgb * src.a;
finalColor.a   = finalColor.a + src.a * (1.0 - finalColor.a);
```

The native draw path uses **premultiplied alpha** output with hardware blending instead.

### Gradient dithering
Both paths apply Interleaved Gradient Noise (Jorge Jimenez) to prevent banding in gradients:
```glsl
float noise = gradientNoise(pixelPos);  // per-pixel noise
float ditherStrength = 1.0 / 255.0;     // 8-bit dither
```

### Display: none
Containers with `display == 0` should be skipped entirely. In the compute path, check `container.visible == 0` (which also covers ancestor hiding). In the native draw path, the vertex shader collapses hidden quads to a degenerate off-screen point.

### Clip testing (overflow)
```glsl
// O(1) — uses CPU-precomputed clip rectangle
if (px.x < clipX || px.x > clipX + clipW ||
    px.y < clipY || px.y > clipY + clipH) discard;
```

---

## Modifying the Buffer Layout — Step-by-Step Checklist

Adding a new field or changing the layout requires updating **every** file that reads or writes the 68-float struct. Follow these steps in order:

### 1. Update `CONTAINER_STRIDE` in `render.py`
Change the constant at the top of the file if the total float count changes:
```python
CONTAINER_STRIDE = 68  # ← update this
```

### 2. Update `_build_container_struct()` in `render.py`
Add the new field(s) to the returned list at the correct position. Remember the list is in exact offset order. If inserting in the middle, **every subsequent offset shifts** — this is extremely error-prone. Prefer appending to the end (before the per-side border widths at T16, or adding a new T17).

### 3. Update `_precompute_visibility_and_clips()` in `render.py`
If the new field is a precomputed value, write it into the struct array at the correct offset index after `_build_container_struct()` returns.

### 4. Update `_pack_container_data_texture()` in `render.py`
This method packs the struct into a numpy array for the data texture. If the stride changed, verify `data = np.zeros(n * NEW_STRIDE, ...)` and `data[offset:offset + NEW_STRIDE]`.

### 5. Update the `Container` struct and `getContainer()` in `container.glsl`
Add the new field to the struct definition and unpack it at the correct offset in `getContainer()`.

### 6. Update the `Container` struct and `getContainer()` in `outline.glsl`
The outline shader has its **own copy** of the struct and unpacking function. It may skip some fields (e.g., it doesn't read precomputed visibility) but the offsets must still be consistent. If you added a field before offset 53, outline.glsl offsets shift too.

### 7. Update the texel layout comment and unpacking in `container_draw.frag`
The fragment shader reads data via `texelFetch`. Update:
- The layout comment at the top of the file (Texel 0 through Texel N)
- The unpacking code that reads from `t0` through `tN`
- If you added a new texel, add a new `texelFetch` call

### 8. Update `container_draw.vert` if it reads the affected texels
The vertex shader reads texels 0, 1, 10, 11, 12, 13, and 16 for position, size, border, shadow extent, and visibility. If your new field affects any of these, update the vert shader too.

### 9. Test with debug outlines enabled
Run with outline debugging on to verify the outline shader still reads positions and sizes correctly. A misaligned outline is a strong indicator of offset mismatch.

### 10. Verify `update_container_buffer_full()` in `render.py`
This method rebuilds the SSBO for the compute path. It calls `_build_container_struct()` so it should auto-update, but confirm the buffer size matches.

---

## Cross-File Coordination Table

These files **must stay in sync** whenever the buffer layout changes:

| File | What it does with the buffer | What to update |
|------|------------------------------|----------------|
| `puree/render.py` | **Packs** the 68-float struct (`_build_container_struct`) | `CONTAINER_STRIDE`, field order in return list, `_precompute_visibility_and_clips`, `_pack_container_data_texture` |
| `puree/shaders/container.glsl` | **Unpacks** from SSBO via `offset + N` | `Container` struct fields, `getContainer()` offset indices, `main()` if new fields affect rendering |
| `puree/shaders/outline.glsl` | **Unpacks** from SSBO (same offsets, may skip tail fields) | `Container` struct fields, `getContainer()` offset indices |
| `puree/shaders/container_draw.frag` | **Unpacks** from data texture via `texelFetch` | Texel layout comment, `tN` fetch calls, unpacking assignments |
| `puree/shaders/container_draw.vert` | **Reads** select texels for geometry (pos, size, shadow, border, visibility) | `texelFetch` calls if affected texels change |
| `puree/hit_op.py` | Reads container positions/sizes for hit detection (via Rust `HitDetector`) | Only if position/size offsets change |

### Secondary files that may need updates

| File | When to update |
|------|---------------|
| `puree/components/style.py` | Adding a new CSS property (add the Style class field + default) |
| `puree/transition_manager.py` | If the new property should be animatable |
| `puree/native_bindings.py` | If the new property needs Rust-side parsing (SCSS → value) |

---

## Performance Notes

- **Minimize branching per-pixel** — GPU threads diverge on branches
- **Early-exit for hidden containers** — check `visible == 0` before any SDF math
- **AABB early-out** — skip containers whose bounding box (expanded by shadow/border extent) doesn't cover the current pixel
- The compute shader processes ALL containers for each pixel — **O(pixels × containers)** — reducing container count has a significant impact
- The native draw path is **O(containers)** with per-fragment SDF — much faster for large panels
- **Data texture width** = `container_count × 17` texels — must fit in a single texture row (GPU max texture width is typically 16384, so ~964 containers max)
- Gradient dithering adds negligible cost but prevents visible banding artifacts
