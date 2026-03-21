// Created by XWZ
// ◕‿◕ Distributed for free at:
// https://github.com/nicolaiprodromov/puree
// ╔═════════════════════════════════╗
// ║  ██   ██  ██      ██  ████████  ║
// ║   ██ ██   ██  ██  ██       ██   ║
// ║    ███    ██  ██  ██     ██     ║
// ║   ██ ██   ██  ██  ██   ██       ║
// ║  ██   ██   ████████   ████████  ║
// ╚═════════════════════════════════╝
#version 430

layout(local_size_x = 16, local_size_y = 16, local_size_z = 1) in;

layout(std430, binding = 0) restrict readonly buffer MouseBuffer {
    vec2 mouse_pos;
    float time;
    float scroll_value;
    float click_value;
    float padding;
};

layout(std430, binding = 1) restrict readonly buffer ContainerBuffer {
    float container_data[];
};

struct Container {
    int display;
    vec2 position;
    vec2 size;
    vec4 color;
    vec4 color_1;
    float color_gradient_rot;
    vec4 hover_color;
    vec4 hover_color_1;
    float hover_color_gradient_rot;
    vec4 click_color;
    vec4 click_color_1;
    float click_color_gradient_rot;
    vec4 border_color;
    vec4 border_color_1;
    float border_color_gradient_rot;
    float border_radius;
    float border_width;
    int parent;
    int overflow;
    vec3 box_shadow_offset;
    float box_shadow_blur;
    vec4 box_shadow_color;
    int passive;
    // Precomputed on CPU — eliminates per-pixel parent chain walks
    int visible;         // 0 if this or any ancestor is hidden
    vec4 clip_rect;      // (x, y, w, h) intersection of all ancestor bounds
};

Container getContainer(int index) {
    int offset = index * 59;
    Container c;
    c.display = int(container_data[offset + 0]);
    c.position = vec2(container_data[offset + 1], container_data[offset + 2]);
    c.size = vec2(container_data[offset + 3], container_data[offset + 4]);
    c.color = vec4(container_data[offset + 5], container_data[offset + 6], container_data[offset + 7], container_data[offset + 8]);
    c.color_1 = vec4(container_data[offset + 9], container_data[offset + 10], container_data[offset + 11], container_data[offset + 12]);
    c.color_gradient_rot = container_data[offset + 13];
    c.hover_color = vec4(container_data[offset + 14], container_data[offset + 15], container_data[offset + 16], container_data[offset + 17]);
    c.hover_color_1 = vec4(container_data[offset + 18], container_data[offset + 19], container_data[offset + 20], container_data[offset + 21]);
    c.hover_color_gradient_rot = container_data[offset + 22];
    c.click_color = vec4(container_data[offset + 23], container_data[offset + 24], container_data[offset + 25], container_data[offset + 26]);
    c.click_color_1 = vec4(container_data[offset + 27], container_data[offset + 28], container_data[offset + 29], container_data[offset + 30]);
    c.click_color_gradient_rot = container_data[offset + 31];
    c.border_color = vec4(container_data[offset + 32], container_data[offset + 33], container_data[offset + 34], container_data[offset + 35]);
    c.border_color_1 = vec4(container_data[offset + 36], container_data[offset + 37], container_data[offset + 38], container_data[offset + 39]);
    c.border_color_gradient_rot = container_data[offset + 40];
    c.border_radius = container_data[offset + 41];
    c.border_width = container_data[offset + 42];
    c.parent = int(container_data[offset + 43]);
    c.overflow = int(container_data[offset + 44]);
    c.box_shadow_offset = vec3(container_data[offset + 45], container_data[offset + 46], container_data[offset + 47]);
    c.box_shadow_blur = container_data[offset + 48];
    c.box_shadow_color = vec4(container_data[offset + 49], container_data[offset + 50], container_data[offset + 51], container_data[offset + 52]);
    c.passive = int(container_data[offset + 53]);
    c.visible = int(container_data[offset + 54]);
    c.clip_rect = vec4(container_data[offset + 55], container_data[offset + 56],
                       container_data[offset + 57], container_data[offset + 58]);
    return c;
}

layout(std430, binding = 2) restrict readonly buffer ViewportBuffer {
    vec2 viewportSize;
    float container_count_float;
    float hover_index_float;
    float click_index_float;
};

layout(std430, binding = 3) restrict writeonly buffer DebugBuffer {
    float debug_values[];
};

layout(rgba8, binding = 4) restrict writeonly uniform image2D output_texture;

// Interleaved Gradient Noise by Jorge Jimenez
float gradientNoise(vec2 coord) {
    return fract(52.9829189 * fract(dot(coord, vec2(0.06711056, 0.00583715))));
}

vec4 getGradientColor(vec4 color1, vec4 color2, float rotationDegrees, vec2 pixelPos, vec2 containerOrigin, vec2 containerSize) {
    float rotationRad = radians(rotationDegrees);
    vec2 direction = vec2(cos(rotationRad), sin(rotationRad));
    
    vec2 localPos = pixelPos - containerOrigin;
    vec2 center = containerSize * 0.5;
    vec2 relativePos = localPos - center;
    
    float projectedLength = dot(relativePos, direction);
    float maxProjection = abs(dot(containerSize * 0.5, abs(direction)));
    
    float t = (projectedLength + maxProjection) / (2.0 * maxProjection);
    t = clamp(t, 0.0, 1.0);
    
    vec4 gradientColor = mix(color1, color2, t);
    
    float noise = gradientNoise(pixelPos);
    float ditherStrength = (1.0 / 255.0);
    vec3 dither = vec3(noise * ditherStrength - ditherStrength * 0.5);
    
    return vec4(gradientColor.rgb + dither, gradientColor.a);
}

float containerSDFDirect(vec2 pixelPos, vec2 containerPos, vec2 containerSize, float borderRadius) {
    vec2 localPos = pixelPos - containerPos;
    float radius = min(borderRadius, min(containerSize.x, containerSize.y) * 0.5);
    vec2 d = abs(localPos - containerSize * 0.5) - containerSize * 0.5 + radius;
    return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0) - radius;
}

// O(1) clip test using precomputed clip rectangle (replaces parent chain walk)
bool isPixelInClipRect(vec2 pixelPos, vec4 clipRect) {
    return pixelPos.x >= clipRect.x && pixelPos.x <= clipRect.x + clipRect.z &&
           pixelPos.y >= clipRect.y && pixelPos.y <= clipRect.y + clipRect.w;
}

float sdfAntiAlias(float dist) {
    return clamp(0.5 - dist * 0.5, 0.0, 1.0);
}

vec4 renderShadow(vec2 pixelPos, Container container) {
    if (container.box_shadow_color.a <= 0.0 || container.box_shadow_blur <= 0.0) {
        return vec4(0.0);
    }
    
    vec2 shadowOffset = container.box_shadow_offset.xy;
    float shadowDist = containerSDFDirect(pixelPos, container.position + shadowOffset, container.size, container.border_radius);
    
    if (shadowDist > container.box_shadow_blur + 3.0) {
        return vec4(0.0);
    }
    
    float containerDist = containerSDFDirect(pixelPos, container.position, container.size, container.border_radius);
    if (containerDist <= container.border_width) {
        return vec4(0.0);
    }
    
    float softness = max(container.box_shadow_blur * 0.5, 0.5);
    float alpha = 1.0 - smoothstep(-softness, container.box_shadow_blur, shadowDist);
    alpha = clamp(alpha, 0.0, 1.0);
    
    return vec4(container.box_shadow_color.rgb, container.box_shadow_color.a * alpha);
}

vec4 renderContainer(vec2 pixelPos, Container container, bool isHovered, bool isClicked) {
    float dist = containerSDFDirect(pixelPos, container.position, container.size, container.border_radius);
    float outerBound = container.border_width + 1.5;
    
    if (dist > outerBound) {
        return vec4(0.0);
    }
    
    if (container.passive != 0) {
        isHovered = false;
        isClicked = false;
    }
    
    vec4 baseColor = container.color;
    if (container.color_1.a > 0.0) {
        baseColor = getGradientColor(container.color, container.color_1, container.color_gradient_rot, pixelPos, container.position, container.size);
    }
    
    if (isClicked && container.click_color.a >= 0.0) {
        baseColor = container.click_color;
        if (container.click_color_1.a > 0.0) {
            baseColor = getGradientColor(container.click_color, container.click_color_1, container.click_color_gradient_rot, pixelPos, container.position, container.size);
        }
    } else if (isHovered && container.hover_color.a >= 0.0) {
        baseColor = container.hover_color;
        if (container.hover_color_1.a > 0.0) {
            baseColor = getGradientColor(container.hover_color, container.hover_color_1, container.hover_color_gradient_rot, pixelPos, container.position, container.size);
        }
    }
    
    if (dist <= 0.0) {
        float alpha = sdfAntiAlias(dist);
        return vec4(baseColor.rgb, baseColor.a * alpha);
    }
    
    if (dist <= container.border_width && container.border_color.a > 0.0 && container.border_width > 0.0) {
        vec4 borderColor = container.border_color;
        if (container.border_color_1.a > 0.0) {
            borderColor = getGradientColor(container.border_color, container.border_color_1, container.border_color_gradient_rot, pixelPos, container.position, container.size);
        }
        
        float borderDist = abs(dist - container.border_width * 0.5) - container.border_width * 0.5;
        float borderAlpha = sdfAntiAlias(borderDist);
        return vec4(borderColor.rgb, borderColor.a * borderAlpha);
    }
    
    return vec4(0.0);
}

void main() {
    ivec2 pixel_coords = ivec2(gl_GlobalInvocationID.xy);
    ivec2 texture_size = imageSize(output_texture);
    
    if (pixel_coords.x >= texture_size.x || pixel_coords.y >= texture_size.y) {
        return;
    }
    
    vec2 pixelPos = vec2(pixel_coords) + vec2(0.5);
    
    int container_count = int(container_count_float);
    // Hover/click indices computed on CPU (via Rust HitDetector)
    int topmostHoverIndex = int(hover_index_float);
    int topmostClickIndex = int(click_index_float);
    
    if (pixel_coords.x == 0 && pixel_coords.y == 0) {
        debug_values[0] = viewportSize.x;
        debug_values[1] = viewportSize.y;
        debug_values[2] = container_count_float;
        debug_values[3] = mouse_pos.x;
        debug_values[4] = mouse_pos.y;
        if (container_count > 0) {
            Container first_container = getContainer(0);
            debug_values[5] = float(first_container.display);
            debug_values[6] = first_container.position.x;
            debug_values[7] = first_container.position.y;
            debug_values[8] = first_container.size.x;
            debug_values[9] = first_container.size.y;
            debug_values[10] = first_container.color.r;
            debug_values[11] = first_container.color.g;
            debug_values[12] = first_container.color.b;
            debug_values[13] = first_container.color.a;
            debug_values[14] = first_container.hover_color.r;
            debug_values[15] = first_container.hover_color.g;
            debug_values[16] = first_container.hover_color.b;
            debug_values[17] = first_container.hover_color.a;
        }
    }
    
    if (container_count <= 0 || container_count > 1000) {
        float r = min(1.0, float(container_count) / 10.0);
        imageStore(output_texture, pixel_coords, vec4(r, 0.0, 0.0, 1.0));
        return;
    }
    
    // Single rendering pass — no hover/click detection loop needed (done on CPU)
    // Visibility and clip rects are precomputed on CPU: O(1) per container
    vec4 finalColor = vec4(0.0);
    
    for (int i = 0; i < container_count && i < 100; i++) {
        Container container = getContainer(i);
        
        // Precomputed visibility replaces isAnyParentHidden() parent chain walk
        if (container.visible == 0) continue;
        
        // AABB early-out: skip if pixel is far from this container
        vec2 localPos = pixelPos - container.position;
        vec2 halfSize = container.size * 0.5;
        float extent = max(container.border_width, container.box_shadow_blur) + 5.0;
        if (abs(localPos.x - halfSize.x) > halfSize.x + extent ||
            abs(localPos.y - halfSize.y) > halfSize.y + extent) {
            continue;
        }
        
        // O(1) clip test replaces isPixelInAllParentBounds() parent chain walk
        if (!isPixelInClipRect(pixelPos, container.clip_rect)) {
            continue;
        }
        
        // Shadow
        vec4 shadowColor = renderShadow(pixelPos, container);
        if (shadowColor.a > 0.0) {
            finalColor.rgb = finalColor.rgb * (1.0 - shadowColor.a) + shadowColor.rgb * shadowColor.a;
            finalColor.a = finalColor.a + shadowColor.a * (1.0 - finalColor.a);
        }
        
        // Container body + border (hover/click from CPU-computed indices)
        bool hovered = (topmostHoverIndex == i);
        bool clicked = (topmostClickIndex == i);
        vec4 containerColor = renderContainer(pixelPos, container, hovered, clicked);
        if (containerColor.a > 0.0) {
            finalColor.rgb = finalColor.rgb * (1.0 - containerColor.a) + containerColor.rgb * containerColor.a;
            finalColor.a = finalColor.a + containerColor.a * (1.0 - finalColor.a);
        }
    }
    
    imageStore(output_texture, pixel_coords, finalColor);
}