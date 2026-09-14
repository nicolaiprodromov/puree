use pyo3::prelude::*;
use pyo3::types::PyBytes;
use std::fs::File;
use std::io::BufReader;

use image::codecs::gif::GifDecoder;
use image::AnimationDecoder;

use super::flip_scanlines_in_place;

/// `(width, height, frames, delays_ms, loop_count)` as returned to Python.
type DecodedGif = (u32, u32, Vec<Py<PyBytes>>, Vec<u16>, u16);

/// Browsers treat GIF frame delays below 20 ms as 100 ms (Chrome/Firefox/
/// WebKit all normalize `delay < 0.02s` to `0.1s`). Match that exactly.
const MIN_DELAY_MS: u32 = 20;
const NORMALIZED_DELAY_MS: u16 = 100;
const DEFAULT_DELAY_MS: u16 = 100;

fn clamp_delay_ms(delay_ms: u32) -> u16 {
    if delay_ms < MIN_DELAY_MS {
        NORMALIZED_DELAY_MS
    } else {
        delay_ms.min(u16::MAX as u32) as u16
    }
}

/// Premultiply straight-alpha RGBA8 in place (r = r*a/255, rounded).
///
/// The Blender draw path blends image quads with `ALPHA_PREMULT`
/// (img_op.draw_all_images), matching `bpy.data.images` uploads which use
/// `alpha_mode = "PREMUL"` - so decoded frames must be premultiplied too.
fn premultiply_rgba_in_place(pixels: &mut [u8]) {
    // `as_chunks_mut` (stable since 1.88) gives `&mut [u8; 4]` per pixel; the
    // remainder is empty for w*h*4 buffers, exactly like chunks_exact_mut(4).
    for px in pixels.as_chunks_mut::<4>().0 {
        let a = px[3] as u32;
        if a == 255 {
            continue;
        }
        if a == 0 {
            px[0] = 0;
            px[1] = 0;
            px[2] = 0;
            continue;
        }
        // (c * a + 127) / 255 - rounding division
        px[0] = ((px[0] as u32 * a + 127) / 255) as u8;
        px[1] = ((px[1] as u32 * a + 127) / 255) as u8;
        px[2] = ((px[2] as u32 * a + 127) / 255) as u8;
    }
}

/// Read the GIF's Netscape loop count without decoding pixel data.
///
/// The `image` crate does not expose the loop extension, so run a second,
/// cheap metadata pass with the `gif` crate (already a transitive dep of
/// `image`'s gif feature). Returns 0 for "loop forever" (also the browser
/// default when the extension is absent), n for "play n+1 times" mapped to
/// total iteration count like HTML expects.
fn read_loop_count(path: &str) -> u16 {
    let file = match File::open(path) {
        Ok(f) => f,
        Err(_) => return 0,
    };
    let mut options = gif::DecodeOptions::new();
    // Skip palette->RGBA conversion work; we only want metadata.
    options.set_color_output(gif::ColorOutput::Indexed);
    let mut decoder = match options.read_info(BufReader::new(file)) {
        Ok(d) => d,
        Err(_) => return 0,
    };
    // The Netscape application extension is stored ahead of frame data, but
    // the `gif` crate only surfaces `repeat()` once it has been parsed -
    // reading the first frame guarantees that.
    let _ = decoder.read_next_frame();
    match decoder.repeat() {
        // Infinite repeat -> 0 (our "loop forever" sentinel).
        gif::Repeat::Infinite => 0,
        // `Repeat::Finite(n)` means "repeat n more times after the first
        // play". No extension at all decodes as Finite(0) = play once.
        // Report total play count (n + 1) so 0 stays reserved for infinite.
        gif::Repeat::Finite(n) => n.saturating_add(1),
    }
}

/// Decode an animated (or static) GIF into fully composited RGBA8 frames.
///
/// Returns `(width, height, frames, delays_ms, loop_count)`:
/// - `frames`: one `bytes` object per frame, premultiplied RGBA8, bottom-up
///   scanline order (ready for GPUTexture upload in the image overlay
///   pass), each exactly `width * height * 4` bytes.
/// - `delays_ms`: per-frame delay in milliseconds, browser-clamped
///   (`delay < 20ms` is normalized to `100ms`, `0` fallback to `100ms`).
/// - `loop_count`: `0` = loop forever, `n` = play the animation n times.
///
/// Disposal methods: verified against image-0.25 source
/// (src/codecs/gif.rs, `GifFrameIterator::next`) - `into_frames()`
/// composites internally. The iterator keeps a persistent full-canvas
/// `non_disposed_frame` buffer, blends each frame patch at its
/// (left, top) offset, and resolves `DisposalMethod` per pixel:
/// Keep/Any persist the composited pixel, Background restores transparent
/// black, Previous leaves the last kept frame in place. Every yielded
/// frame is `Frame::from_parts(buffer, 0, 0, delay)` with a FULL
/// width x height canvas, so no compositing is needed here; the unit
/// test asserts `len(frame) == w * h * 4` on multi-patch GIFs.
#[pyfunction]
pub fn decode_gif(py: Python, path: &str) -> PyResult<DecodedGif> {
    let file = File::open(path).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyIOError, _>(format!(
            "Failed to open GIF '{}': {}",
            path, e
        ))
    })?;

    let decoder = GifDecoder::new(BufReader::new(file)).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
            "Failed to decode GIF '{}': {}",
            path, e
        ))
    })?;

    let mut width: u32 = 0;
    let mut height: u32 = 0;
    let mut frames: Vec<Py<PyBytes>> = Vec::new();
    let mut delays_ms: Vec<u16> = Vec::new();

    for frame_result in decoder.into_frames() {
        let frame = frame_result.map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Failed to decode GIF frame {} of '{}': {}",
                frames.len(),
                path,
                e
            ))
        })?;

        let (num_ms, den_ms) = frame.delay().numer_denom_ms();
        let raw_ms = num_ms.checked_div(den_ms).unwrap_or(0);
        let delay = if raw_ms == 0 {
            DEFAULT_DELAY_MS
        } else {
            clamp_delay_ms(raw_ms)
        };

        let buffer = frame.into_buffer();
        if frames.is_empty() {
            width = buffer.width();
            height = buffer.height();
        } else if buffer.width() != width || buffer.height() != height {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "GIF '{}' frame {} has size {}x{}, expected the composited canvas {}x{}",
                path,
                frames.len(),
                buffer.width(),
                buffer.height(),
                width,
                height
            )));
        }

        let mut pixels = buffer.into_raw();
        premultiply_rgba_in_place(&mut pixels);
        flip_scanlines_in_place(&mut pixels, width, height);

        frames.push(PyBytes::new(py, &pixels).into());
        delays_ms.push(delay);
    }

    if frames.is_empty() {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
            "GIF '{}' contains no frames",
            path
        )));
    }

    let loop_count = read_loop_count(path);

    Ok((width, height, frames, delays_ms, loop_count))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn delay_below_20ms_normalizes_to_100ms() {
        assert_eq!(clamp_delay_ms(0), 100);
        assert_eq!(clamp_delay_ms(10), 100);
        assert_eq!(clamp_delay_ms(19), 100);
    }

    #[test]
    fn delay_at_or_above_20ms_passes_through() {
        assert_eq!(clamp_delay_ms(20), 20);
        assert_eq!(clamp_delay_ms(70), 70);
        assert_eq!(clamp_delay_ms(1000), 1000);
    }

    #[test]
    fn premultiply_scales_channels_by_alpha() {
        let mut px = vec![255u8, 128, 0, 128, 10, 20, 30, 0, 1, 2, 3, 255];
        premultiply_rgba_in_place(&mut px);
        assert_eq!(&px[0..4], &[128, 64, 0, 128]);
        assert_eq!(&px[4..8], &[0, 0, 0, 0]);
        assert_eq!(&px[8..12], &[1, 2, 3, 255]);
    }
}
