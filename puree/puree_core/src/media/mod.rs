pub mod gif;
pub mod svg;

pub use gif::decode_gif;
pub use svg::{probe_svg, rasterize_svg};

/// Flip scanlines top-down -> bottom-up in place.
///
/// Decoders/rasterizers produce top-down scanline order, but the image
/// overlay pass samples uv (0,0) at the quad's bottom-left (matching
/// `bpy.data.images` storage, which is bottom-up) - flipping once at
/// decode time keeps the Python upload path a straight passthrough.
/// Shared by every media decoder (gif.rs, svg.rs, ...).
pub(crate) fn flip_scanlines_in_place(pixels: &mut [u8], width: u32, height: u32) {
    let row_len = (width as usize) * 4;
    if row_len == 0 || height < 2 {
        return;
    }
    let (mut top, mut bottom) = (0usize, height as usize - 1);
    while top < bottom {
        let (head, tail) = pixels.split_at_mut(bottom * row_len);
        head[top * row_len..top * row_len + row_len].swap_with_slice(&mut tail[..row_len]);
        top += 1;
        bottom -= 1;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn flip_scanlines_reverses_row_order() {
        // 1x3 image: rows A, B, C (RGBA each)
        let mut px = vec![
            1u8, 1, 1, 1, // row A
            2, 2, 2, 2, // row B
            3, 3, 3, 3, // row C
        ];
        flip_scanlines_in_place(&mut px, 1, 3);
        assert_eq!(px, vec![3u8, 3, 3, 3, 2, 2, 2, 2, 1, 1, 1, 1]);
    }
}
