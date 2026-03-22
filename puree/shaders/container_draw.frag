// Puree — Blender-native container fragment shader
// SDF rendering with data texture lookup. Same visual output as the compute shader.
// Outputs premultiplied alpha for correct hardware blending.
//
// Data texture layout per container (15 RGBA32F texels = 60 floats):
//   Texel 0:  display, pos_x, pos_y, size_x
//   Texel 1:  size_y, color_r, color_g, color_b
//   Texel 2:  color_a, color1_r, color1_g, color1_b
//   Texel 3:  color1_a, gradient_rot, hover_r, hover_g
//   Texel 4:  hover_b, hover_a, hover1_r, hover1_g
//   Texel 5:  hover1_b, hover1_a, hover_grad_rot, click_r
//   Texel 6:  click_g, click_b, click_a, click1_r
//   Texel 7:  click1_g, click1_b, click1_a, click_grad_rot
//   Texel 8:  border_r, border_g, border_b, border_a
//   Texel 9:  border1_r, border1_g, border1_b, border1_a
//   Texel 10: border_grad_rot, border_radius, border_width, parent
//   Texel 11: overflow, shadow_x, shadow_y, shadow_z
//   Texel 12: shadow_blur, shadow_r, shadow_g, shadow_b
//   Texel 13: shadow_a, passive, visible, clip_x
//   Texel 14: clip_y, clip_w, clip_h, opacity

// Interleaved Gradient Noise (Jorge Jimenez) for dithered gradients
float gradientNoise(vec2 coord) {
    return fract(52.9829189 * fract(dot(coord, vec2(0.06711056, 0.00583715))));
}

vec4 getGradientColor(vec4 c1, vec4 c2, float rotDeg, vec2 pixel, vec2 origin, vec2 sz) {
    float rad = radians(rotDeg);
    vec2 dir = vec2(cos(rad), sin(rad));
    vec2 rel = pixel - origin - sz * 0.5;
    float proj = dot(rel, dir);
    float maxProj = abs(dot(sz * 0.5, abs(dir)));
    float t = clamp((proj + maxProj) / (2.0 * maxProj), 0.0, 1.0);
    vec4 gc = mix(c1, c2, t);
    float n = gradientNoise(pixel);
    float ds = 1.0 / 255.0;
    return vec4(gc.rgb + vec3(n * ds - ds * 0.5), gc.a);
}

float containerSDF(vec2 pixel, vec2 pos, vec2 sz, float radius) {
    vec2 local = pixel - pos;
    float r = min(radius, min(sz.x, sz.y) * 0.5);
    vec2 d = abs(local - sz * 0.5) - sz * 0.5 + r;
    return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0) - r;
}

float sdfAA(float dist) {
    return clamp(0.5 - dist * 0.5, 0.0, 1.0);
}

void main() {
    int idx = int(vContainerIdx);
    int texBase = idx * 15;

    // Batch-read all 15 texels
    vec4 t0  = texelFetch(containerData, ivec2(texBase + 0,  0), 0);
    vec4 t1  = texelFetch(containerData, ivec2(texBase + 1,  0), 0);
    vec4 t2  = texelFetch(containerData, ivec2(texBase + 2,  0), 0);
    vec4 t3  = texelFetch(containerData, ivec2(texBase + 3,  0), 0);
    vec4 t4  = texelFetch(containerData, ivec2(texBase + 4,  0), 0);
    vec4 t5  = texelFetch(containerData, ivec2(texBase + 5,  0), 0);
    vec4 t6  = texelFetch(containerData, ivec2(texBase + 6,  0), 0);
    vec4 t7  = texelFetch(containerData, ivec2(texBase + 7,  0), 0);
    vec4 t8  = texelFetch(containerData, ivec2(texBase + 8,  0), 0);
    vec4 t9  = texelFetch(containerData, ivec2(texBase + 9,  0), 0);
    vec4 t10 = texelFetch(containerData, ivec2(texBase + 10, 0), 0);
    vec4 t11 = texelFetch(containerData, ivec2(texBase + 11, 0), 0);
    vec4 t12 = texelFetch(containerData, ivec2(texBase + 12, 0), 0);
    vec4 t13 = texelFetch(containerData, ivec2(texBase + 13, 0), 0);
    vec4 t14 = texelFetch(containerData, ivec2(texBase + 14, 0), 0);

    // Unpack container properties
    float display  = t0.x;
    vec2  pos      = vec2(t0.y, t0.z);
    vec2  sz       = vec2(t0.w, t1.x);
    vec4  color    = vec4(t1.y, t1.z, t1.w, t2.x);
    vec4  color1   = vec4(t2.y, t2.z, t2.w, t3.x);
    float gradRot  = t3.y;
    vec4  hColor   = vec4(t3.z, t3.w, t4.x, t4.y);
    vec4  hColor1  = vec4(t4.z, t4.w, t5.x, t5.y);
    float hGradRot = t5.z;
    vec4  cColor   = vec4(t5.w, t6.x, t6.y, t6.z);
    vec4  cColor1  = vec4(t6.w, t7.x, t7.y, t7.z);
    float cGradRot = t7.w;
    vec4  bColor   = vec4(t8.x, t8.y, t8.z, t8.w);
    vec4  bColor1  = vec4(t9.x, t9.y, t9.z, t9.w);
    float bGradRot = t10.x;
    float bRadius  = t10.y;
    float bWidth   = t10.z;
    vec2  shOff    = t11.yz;
    float shBlur   = t12.x;
    vec4  shColor  = vec4(t12.y, t12.z, t12.w, t13.x);
    float passive  = t13.y;
    float visible  = t13.z;
    float clipX    = t13.w;
    float clipY    = t14.x;
    float clipW    = t14.y;
    float clipH    = t14.z;
    float opacity  = t14.w;

    // Early-out for hidden containers (safety net — vertex shader already culls these)
    if (display < 0.5 || visible < 0.5) discard;

    // Clip test (precomputed intersection of all ancestor bounds)
    vec2 px = vPixelPos;
    if (px.x < clipX || px.x > clipX + clipW ||
        px.y < clipY || px.y > clipY + clipH) discard;

    // --- Shadow ---
    vec4 shResult = vec4(0.0);
    if (shColor.a > 0.0 && shBlur > 0.0) {
        float sDist = containerSDF(px, pos + shOff, sz, bRadius);
        if (sDist <= shBlur + 3.0) {
            float cDist = containerSDF(px, pos, sz, bRadius);
            if (cDist > bWidth) {
                float soft = max(shBlur * 0.5, 0.5);
                float sA = clamp(1.0 - smoothstep(-soft, shBlur, sDist), 0.0, 1.0);
                float finalA = shColor.a * sA;
                shResult = vec4(shColor.rgb * finalA, finalA);
            }
        }
    }

    // --- Container body + border ---
    float dist = containerSDF(px, pos, sz, bRadius);
    float outerBound = bWidth + 1.5;
    vec4 bodyResult = vec4(0.0);

    if (dist <= outerBound) {
        bool isHovered = (int(hoverIndex) == idx) && (passive < 0.5);
        bool isClicked = (int(clickIndex) == idx) && (passive < 0.5);

        vec4 baseColor = color;
        if (color1.a > 0.0) {
            baseColor = getGradientColor(color, color1, gradRot, px, pos, sz);
        }

        if (isClicked && cColor.a >= 0.0) {
            baseColor = cColor;
            if (cColor1.a > 0.0) {
                baseColor = getGradientColor(cColor, cColor1, cGradRot, px, pos, sz);
            }
        } else if (isHovered && hColor.a >= 0.0) {
            baseColor = hColor;
            if (hColor1.a > 0.0) {
                baseColor = getGradientColor(hColor, hColor1, hGradRot, px, pos, sz);
            }
        }

        if (dist <= 0.0) {
            float a = sdfAA(dist);
            float fa = baseColor.a * a;
            bodyResult = vec4(baseColor.rgb * fa, fa);
        } else if (dist <= bWidth && bColor.a > 0.0 && bWidth > 0.0) {
            vec4 bc = bColor;
            if (bColor1.a > 0.0) {
                bc = getGradientColor(bColor, bColor1, bGradRot, px, pos, sz);
            }
            float bd = abs(dist - bWidth * 0.5) - bWidth * 0.5;
            float ba = sdfAA(bd);
            float fba = bc.a * ba;
            bodyResult = vec4(bc.rgb * fba, fba);
        }
    }

    // Composite body over shadow (both premultiplied)
    vec4 result = bodyResult + shResult * (1.0 - bodyResult.a);

    // Apply accumulated opacity (premultiplied alpha)
    result *= opacity;

    if (result.a < 0.004) discard;
    fragColor = result;
}
