#version 430

layout(local_size_x = 16, local_size_y = 16) in;

layout(rgba8, binding = 0) uniform readonly image2D input_texture;
layout(rgba8, binding = 1) uniform writeonly image2D output_texture;

layout(std430, binding = 2) readonly buffer ContainerData {
    float container_data[];
};

layout(std430, binding = 3) readonly buffer ViewportData {
    vec2 viewportSize;
    float container_count_float;
};

layout(std430, binding = 4) readonly buffer DebugOutlineData {
    int outlined_container_ids[];
};

layout(std430, binding = 5) readonly buffer DebugOutlineCount {
    int outlined_count;
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

bool isContainerOutlined(int container_index) {
    for (int i = 0; i < outlined_count && i < 100; i++) {
        if (outlined_container_ids[i] == container_index) {
            return true;
        }
    }
    return false;
}

float sdBox(vec2 p, vec2 center, vec2 size, float radius) {
    vec2 halfSize = size * 0.5;
    vec2 d = abs(p - center) - halfSize + radius;
    return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0) - radius;
}

void main() {
    ivec2 pixel_coords = ivec2(gl_GlobalInvocationID.xy);
    
    if (pixel_coords.x >= int(viewportSize.x) || pixel_coords.y >= int(viewportSize.y)) {
        return;
    }
    
    vec4 inputColor = imageLoad(input_texture, pixel_coords);
    vec4 outputColor = inputColor;
    
    vec2 pixelPos = vec2(pixel_coords);
    int container_count = int(container_count_float);
    
    const vec4 debugBlue = vec4(0.3, 0.5, 1.0, 1.0);
    const float outlineWidth = 2.0;
    
    for (int i = 0; i < container_count && i < 100; i++) {
        if (!isContainerOutlined(i)) {
            continue;
        }
        
        Container container = getContainer(i);
        if (container.display == 0) {
            continue;
        }
        
        vec2 containerCenter = container.position + container.size * 0.5;
        float sdf = sdBox(pixelPos, containerCenter, container.size, container.border_radius);
        
        if (sdf >= -outlineWidth && sdf <= 0.0) {
            outputColor = debugBlue;
        }
    }
    
    imageStore(output_texture, pixel_coords, outputColor);
}
