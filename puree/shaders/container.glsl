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
};

Container getContainer(int index) {
    int offset = index * 54;
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
    return c;
}

layout(std430, binding = 2) restrict readonly buffer ViewportBuffer {
    vec2 viewportSize;
    float container_count_float;
};

layout(std430, binding = 3) restrict writeonly buffer DebugBuffer {
    float debug_values[];
};

layout(rgba8, binding = 4) restrict writeonly uniform image2D output_texture;

// Interleaved Gradient Noise by Jorge Jimenez
// From Call of Duty: Advanced Warfare presentation
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
    
    // Apply the gradient interpolation
    vec4 gradientColor = mix(color1, color2, t);
    
    // Add Interleaved Gradient Noise to eliminate banding
    // Strength of 1/255 to match 8-bit precision, minus 0.5/255 to keep brightness neutral
    float noise = gradientNoise(pixelPos);
    float ditherStrength = (1.0 / 255.0);
    vec3 dither = vec3(noise * ditherStrength - ditherStrength * 0.5);
    
    return vec4(gradientColor.rgb + dither, gradientColor.a);
}

vec2 getContainerOrigin(int containerIndex) {
    Container container = getContainer(containerIndex);
    return container.position;
}

float containerSDF(vec2 pixelPos, Container container, int containerIndex) {
    vec2 containerOrigin = getContainerOrigin(containerIndex);
    vec2 localPos = pixelPos - containerOrigin;
    vec2 size = container.size;
    float radius = min(container.border_radius, min(size.x, size.y) * 0.5);
    
    vec2 d = abs(localPos - size * 0.5) - size * 0.5 + radius;
    return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0) - radius;
}

bool isPixelInAllParentBounds(vec2 pixelPos, int containerIndex) {
    int container_count = int(container_count_float);
    if (containerIndex < 0 || containerIndex >= container_count) {
        return true;
    }
    
    Container currentContainer = getContainer(containerIndex);
    int parentIndex = currentContainer.parent;
    
    while (parentIndex >= 0 && parentIndex < container_count) {
        Container parent = getContainer(parentIndex);
        
        if (parent.overflow == 0) {
            float parentSDF = containerSDF(pixelPos, parent, parentIndex);
            if (parentSDF > 0.0) {
                return false;
            }
        }
        
        parentIndex = parent.parent;
    }
    
    return true;
}

bool isAnyParentHidden(int containerIndex) {
    int currentIndex = containerIndex;
    int container_count = int(container_count_float);
    
    for (int depth = 0; depth < 10 && depth < container_count; depth++) {
        if (currentIndex < 0 || currentIndex >= container_count) {
            break;
        }
        
        Container container = getContainer(currentIndex);
        
        if (container.display == 0) {
            return true;
        }
        
        if (container.parent < 0) {
            break;
        }
        
        currentIndex = container.parent;
    }
    
    return false;
}

float boxShadowSDF(vec2 pixelPos, Container container, int containerIndex) {
    vec2 containerOrigin = getContainerOrigin(containerIndex);
    vec2 shadowOffset = container.box_shadow_offset.xy;
    vec2 localPos = pixelPos - containerOrigin - shadowOffset;
    vec2 size = container.size;
    float radius = min(container.border_radius, min(size.x, size.y) * 0.5);
    
    vec2 d = abs(localPos - size * 0.5) - size * 0.5 + radius;
    return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0) - radius;
}

float getPixelScale(vec2 coord, vec2 viewportSize) {
    return 1.0;
}

float sdfAntiAlias(float dist, float pixelScale) {
    float edgeWidth = pixelScale * 0.5;
    return clamp(0.5 - dist / edgeWidth, 0.0, 1.0);
}

vec4 renderShadow(vec2 pixelPos, Container container, int containerIndex) {
    if (container.display == 0) {
        return vec4(0.0);
    }
    
    if (isAnyParentHidden(containerIndex)) {
        return vec4(0.0);
    }
    
    if (container.box_shadow_color.a <= 0.0 || container.box_shadow_blur <= 0.0) {
        return vec4(0.0);
    }
    
    if (!isPixelInAllParentBounds(pixelPos, containerIndex)) {
        return vec4(0.0);
    }
    
    float shadowDist = boxShadowSDF(pixelPos, container, containerIndex);
    
    if (shadowDist > container.box_shadow_blur + 3.0) {
        return vec4(0.0);
    }
    
    float containerDist = containerSDF(pixelPos, container, containerIndex);
    if (containerDist <= container.border_width) {
        return vec4(0.0);
    }
    
    float pixelScale = getPixelScale(pixelPos, viewportSize);
    float softness = max(container.box_shadow_blur * 0.5, pixelScale);
    float alpha = 1.0 - smoothstep(-softness, container.box_shadow_blur, shadowDist);
    alpha = clamp(alpha, 0.0, 1.0);
    
    return vec4(container.box_shadow_color.rgb, container.box_shadow_color.a * alpha);
}

vec4 renderContainer(vec2 pixelPos, vec2 mousePixelPos, vec2 clickPixelPos, bool clicked, Container container, int containerIndex, bool blockClick, bool blockHover) {
    if (container.display == 0) {
        return vec4(0.0);
    }
    
    if (isAnyParentHidden(containerIndex)) {
        return vec4(0.0);
    }
    
    if (!isPixelInAllParentBounds(pixelPos, containerIndex)) {
        return vec4(0.0);
    }
    
    float dist = containerSDF(pixelPos, container, containerIndex);
    float outerBound = container.border_width + 3.0;
    
    if (dist > outerBound) {
        return vec4(0.0);
    }
    
    bool isHovered = !blockHover && containerSDF(mousePixelPos, container, containerIndex) <= 0.0;
    if (isHovered) {
        if (!isPixelInAllParentBounds(mousePixelPos, containerIndex)) {
            isHovered = false;
        }
    }
    
    bool isClicked = clicked && !blockClick && containerSDF(clickPixelPos, container, containerIndex) <= 0.0 && isHovered;
    if (isClicked) {
        if (!isPixelInAllParentBounds(clickPixelPos, containerIndex)) {
            isClicked = false;
        }
    }
    
    // If container is passive, ignore hover and click states
    if (container.passive != 0) {
        isHovered = false;
        isClicked = false;
    }
    
    vec4 baseColor = container.color;
    if (container.color_1.a > 0.0) {
        vec2 containerOrigin = getContainerOrigin(containerIndex);
        baseColor = getGradientColor(container.color, container.color_1, container.color_gradient_rot, pixelPos, containerOrigin, container.size);
    }
    
    if (isClicked && container.click_color.a >= 0.0) {
        baseColor = container.click_color;
        if (container.click_color_1.a > 0.0) {
            vec2 containerOrigin = getContainerOrigin(containerIndex);
            baseColor = getGradientColor(container.click_color, container.click_color_1, container.click_color_gradient_rot, pixelPos, containerOrigin, container.size);
        }
    } else if (isHovered && container.hover_color.a >= 0.0) {
        baseColor = container.hover_color;
        if (container.hover_color_1.a > 0.0) {
            vec2 containerOrigin = getContainerOrigin(containerIndex);
            baseColor = getGradientColor(container.hover_color, container.hover_color_1, container.hover_color_gradient_rot, pixelPos, containerOrigin, container.size);
        }
    }
    
    float pixelScale = getPixelScale(pixelPos, viewportSize);
    
    // Main container area with antialiasing
    if (dist <= 0.0) {
        float alpha = sdfAntiAlias(dist, pixelScale);
        return vec4(baseColor.rgb, baseColor.a * alpha);
    }
    
    // Border with antialiasing
    if (dist <= container.border_width && container.border_color.a > 0.0 && container.border_width > 0.0) {
        vec4 borderColor = container.border_color;
        if (container.border_color_1.a > 0.0) {
            vec2 containerOrigin = getContainerOrigin(containerIndex);
            borderColor = getGradientColor(container.border_color, container.border_color_1, container.border_color_gradient_rot, pixelPos, containerOrigin, container.size);
        }
        
        float borderDist = abs(dist - container.border_width * 0.5) - container.border_width * 0.5;
        float borderAlpha = sdfAntiAlias(borderDist, pixelScale);
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
    
    // SIMPLIFIED: Direct 1:1 mapping since texture = viewport
    vec2 pixelPos = vec2(pixel_coords) + vec2(0.5);
    vec2 viewportPixelPos = pixelPos; // No transformation needed!
    vec2 mousePixelPos = mouse_pos * viewportSize;
    vec2 clickPixelPos = mouse_pos * viewportSize;
    bool isClicked = click_value > 0.0;
    
    int container_count = int(container_count_float);
    
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
    
    int topmostClickIndex = -1;
    if (isClicked) {
        for (int i = container_count - 1; i >= 0; i--) {
            if (i >= 100) continue;
            Container container = getContainer(i);
            if (container.display == 0) continue;
            if (isAnyParentHidden(i)) continue;
            if (container.passive != 0) continue;  // Skip passive containers for click detection
            
            bool childClicked = containerSDF(clickPixelPos, container, i) <= 0.0;
            
            if (childClicked && isPixelInAllParentBounds(clickPixelPos, i)) {
                topmostClickIndex = i;
                break;
            }
        }
    }
    
    int topmostHoverIndex = -1;
    for (int i = container_count - 1; i >= 0; i--) {
        if (i >= 100) continue;
        Container container = getContainer(i);
        if (container.display == 0) continue;
        if (isAnyParentHidden(i)) continue;
        if (container.passive != 0) continue;  // Skip passive containers for hover detection
        
        bool childHovered = containerSDF(mousePixelPos, container, i) <= 0.0;
        
        if (childHovered && isPixelInAllParentBounds(mousePixelPos, i)) {
            topmostHoverIndex = i;
            break;
        }
    }
    
    vec4 finalColor = vec4(0.0);
    
    bool needsHighQuality = false;
    for (int i = 0; i < container_count && i < 100; i++) {
        Container container = getContainer(i);
        float dist = containerSDF(viewportPixelPos, container, i);
        if (abs(dist) < 2.0) {
            needsHighQuality = true;
            break;
        }
    }
    
    if (needsHighQuality) {
        vec2 sampleOffsets[4] = vec2[4](
            vec2(-0.25, -0.25), vec2(0.25, -0.25),
            vec2(-0.25, 0.25),  vec2(0.25, 0.25)
        );
        
        vec4 accumulatedColor = vec4(0.0);
        for (int s = 0; s < 4; s++) {
            vec2 samplePos = viewportPixelPos + sampleOffsets[s];
            
            vec4 sampleColor = vec4(0.0);
            
            for (int i = 0; i < container_count && i < 100; i++) {
                Container container = getContainer(i);
                if (container.parent >= 0) continue;
                vec4 shadowColor = renderShadow(samplePos, container, i);
                if (shadowColor.a > 0.0) {
                    sampleColor.rgb = mix(sampleColor.rgb, shadowColor.rgb, shadowColor.a);
                    sampleColor.a = min(sampleColor.a + shadowColor.a, 1.0);
                }
            }
            
            for (int i = 0; i < container_count && i < 100; i++) {
                Container container = getContainer(i);
                if (container.parent < 0) continue;
                vec4 shadowColor = renderShadow(samplePos, container, i);
                if (shadowColor.a > 0.0) {
                    sampleColor.rgb = mix(sampleColor.rgb, shadowColor.rgb, shadowColor.a);
                    sampleColor.a = min(sampleColor.a + shadowColor.a, 1.0);
                }
            }
            
            for (int i = 0; i < container_count && i < 100; i++) {
                Container container = getContainer(i);
                if (container.parent >= 0) continue;
                bool blockClick = topmostClickIndex >= 0 && topmostClickIndex != i;
                bool blockHover = topmostHoverIndex >= 0 && topmostHoverIndex != i;
                vec4 containerColor = renderContainer(samplePos, mousePixelPos, clickPixelPos, isClicked, container, i, blockClick, blockHover);
                if (containerColor.a > 0.0) {
                    sampleColor = containerColor;
                }
            }
            
            for (int i = 0; i < container_count && i < 100; i++) {
                Container container = getContainer(i);
                if (container.parent < 0) continue;
                bool blockClick = topmostClickIndex >= 0 && topmostClickIndex != i;
                bool blockHover = topmostHoverIndex >= 0 && topmostHoverIndex != i;
                vec4 containerColor = renderContainer(samplePos, mousePixelPos, clickPixelPos, isClicked, container, i, blockClick, blockHover);
                if (containerColor.a > 0.0) {
                    sampleColor = containerColor;
                }
            }
            
            accumulatedColor += sampleColor;
        }
        finalColor = accumulatedColor * 0.25;
    } else {
        for (int i = 0; i < container_count && i < 100; i++) {
            Container container = getContainer(i);
            if (container.parent >= 0) continue;
            vec4 shadowColor = renderShadow(viewportPixelPos, container, i);
            if (shadowColor.a > 0.0) {
                finalColor.rgb = mix(finalColor.rgb, shadowColor.rgb, shadowColor.a);
                finalColor.a = min(finalColor.a + shadowColor.a, 1.0);
            }
        }
        
        for (int i = 0; i < container_count && i < 100; i++) {
            Container container = getContainer(i);
            if (container.parent < 0) continue;
            vec4 shadowColor = renderShadow(viewportPixelPos, container, i);
            if (shadowColor.a > 0.0) {
                finalColor.rgb = mix(finalColor.rgb, shadowColor.rgb, shadowColor.a);
                finalColor.a = min(finalColor.a + shadowColor.a, 1.0);
            }
        }
        
        for (int i = 0; i < container_count && i < 100; i++) {
            Container container = getContainer(i);
            if (container.parent >= 0) continue;
            bool blockClick = topmostClickIndex >= 0 && topmostClickIndex != i;
            bool blockHover = topmostHoverIndex >= 0 && topmostHoverIndex != i;
            vec4 containerColor = renderContainer(viewportPixelPos, mousePixelPos, clickPixelPos, isClicked, container, i, blockClick, blockHover);
            if (containerColor.a > 0.0) {
                finalColor = containerColor;
            }
        }
        
        for (int i = 0; i < container_count && i < 100; i++) {
            Container container = getContainer(i);
            if (container.parent < 0) continue;
            bool blockClick = topmostClickIndex >= 0 && topmostClickIndex != i;
            bool blockHover = topmostHoverIndex >= 0 && topmostHoverIndex != i;
            vec4 containerColor = renderContainer(viewportPixelPos, mousePixelPos, clickPixelPos, isClicked, container, i, blockClick, blockHover);
            if (containerColor.a > 0.0) {
                finalColor = containerColor;
            }
        }
    }
    
    imageStore(output_texture, pixel_coords, finalColor);
}