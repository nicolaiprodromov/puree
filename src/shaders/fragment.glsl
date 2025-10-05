void main() {
    vec2 flippedTexCoord = vec2(fragTexCoord.x, 1.0 - fragTexCoord.y);
    vec4 texColor = texture(inputTexture, flippedTexCoord);
    fragColor = vec4(texColor.rgb, texColor.a * opacity);
}