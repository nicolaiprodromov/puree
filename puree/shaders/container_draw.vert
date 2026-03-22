// Puree — Blender-native container vertex shader
// Reads container position/size/shadow from RGBA32F data texture.
// Expands quad to cover container + shadow extent.
// Transforms from CSS pixel space (Y-down) to NDC (Y-up).

void main() {
    int idx = int(containerIdx);
    int texBase = idx * 16;

    // Texel 0: display, pos_x, pos_y, size_x
    vec4 t0 = texelFetch(containerData, ivec2(texBase, 0), 0);
    // Texel 1: size_y, ...
    vec4 t1 = texelFetch(containerData, ivec2(texBase + 1, 0), 0);
    // Texel 10: border_grad_rot, radius_tl, border_width, radius_tr
    vec4 t10 = texelFetch(containerData, ivec2(texBase + 10, 0), 0);
    // Texel 11: radius_br, shadow_x, shadow_y, shadow_z
    vec4 t11 = texelFetch(containerData, ivec2(texBase + 11, 0), 0);
    // Texel 12: shadow_blur, ...
    vec4 t12 = texelFetch(containerData, ivec2(texBase + 12, 0), 0);
    // Texel 13: shadow_a, passive, visible, clip_x
    vec4 t13 = texelFetch(containerData, ivec2(texBase + 13, 0), 0);

    float display = t0.x;
    float visible = t13.z;

    // Hidden containers: collapse quad to off-screen degenerate point
    if (display < 0.5 || visible < 0.5) {
        gl_Position = vec4(2.0, 2.0, 0.0, 1.0);
        vContainerIdx = containerIdx;
        vPixelPos = vec2(0.0);
        return;
    }

    vec2 pos = vec2(t0.y, t0.z);
    vec2 size = vec2(t0.w, t1.x);
    float borderWidth = t10.z;
    vec2 shadowOffset = t11.yz;
    float shadowBlur = t12.x;

    // Expand quad to cover shadow + border + AA margin
    float shadowExtent = shadowBlur + max(abs(shadowOffset.x), abs(shadowOffset.y)) + 3.0;
    float extent = max(borderWidth + 2.0, shadowExtent);

    vec2 expandedPos = pos - vec2(extent);
    vec2 expandedSize = size + vec2(extent * 2.0);

    // Vertex position in CSS pixel space
    vec2 worldPos = expandedPos + quadCorner * expandedSize;

    // CSS pixel space (Y-down) → NDC (Y-up)
    vec2 ndc;
    ndc.x = worldPos.x / viewportWidth * 2.0 - 1.0;
    ndc.y = 1.0 - worldPos.y / viewportHeight * 2.0;

    gl_Position = vec4(ndc, 0.0, 1.0);
    vContainerIdx = containerIdx;
    vPixelPos = worldPos;
}
