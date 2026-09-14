use pyo3::prelude::*;
use pyo3::types::PyBytes;
use std::collections::HashSet;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};

use once_cell::sync::Lazy;
use resvg::tiny_skia;
use resvg::usvg;

use super::flip_scanlines_in_place;

/// Shared font database state: the system fonts are scanned exactly once
/// per process (Lazy) - re-scanning them on every rasterization would cost
/// tens to hundreds of milliseconds. Extra font directories (the addon's
/// `fonts/` dir) are folded in on first sight and remembered.
struct FontState {
    db: Arc<usvg::fontdb::Database>,
    loaded_dirs: HashSet<PathBuf>,
}

static FONTDB: Lazy<Mutex<FontState>> = Lazy::new(|| {
    let mut db = usvg::fontdb::Database::new();
    db.load_system_fonts();
    Mutex::new(FontState {
        db: Arc::new(db),
        loaded_dirs: HashSet::new(),
    })
});

/// The shared fontdb, extended with `fonts_dir` when given and not yet
/// loaded. `usvg::Options` wants an `Arc<Database>`; when a new dir shows
/// up the database is cloned (cheap: faces hold `fontdb::Source` handles,
/// system fonts are memory-mapped file references, not font bytes),
/// extended and swapped in - callers already parsing keep the old Arc.
fn shared_fontdb(fonts_dir: Option<&str>) -> Arc<usvg::fontdb::Database> {
    let mut state = FONTDB
        .lock()
        .unwrap_or_else(|poisoned| poisoned.into_inner());
    if let Some(dir) = fonts_dir {
        let dir_path = PathBuf::from(dir);
        if !state.loaded_dirs.contains(&dir_path) {
            let mut db = (*state.db).clone();
            db.load_fonts_dir(&dir_path);
            state.db = Arc::new(db);
            state.loaded_dirs.insert(dir_path);
        }
    }
    Arc::clone(&state.db)
}

/// Parse an SVG file into a `usvg::Tree` (text already converted to paths).
fn load_tree(path: &str, fonts_dir: Option<&str>) -> PyResult<usvg::Tree> {
    let data = std::fs::read(path).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyIOError, _>(format!(
            "Failed to open SVG '{}': {}",
            path, e
        ))
    })?;

    let options = usvg::Options {
        // Relative hrefs (embedded raster images) resolve against the SVG's own directory.
        resources_dir: Path::new(path).parent().map(Path::to_path_buf),
        fontdb: shared_fontdb(fonts_dir),
        ..usvg::Options::default()
    };

    usvg::Tree::from_data(&data, &options).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
            "Failed to parse SVG '{}': {}",
            path, e
        ))
    })
}

/// Rasterization core, split from the PyO3 wrapper so `cargo test` can
/// exercise it without holding the GIL.
fn rasterize_svg_impl(
    path: &str,
    width: u32,
    height: u32,
    fonts_dir: Option<&str>,
) -> PyResult<Vec<u8>> {
    if width == 0 || height == 0 {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
            "Cannot rasterize SVG '{}' at {}x{} - both dimensions must be >= 1",
            path, width, height
        )));
    }

    let tree = load_tree(path, fonts_dir)?;
    let intrinsic = tree.size(); // usvg::Size is strictly positive

    let mut pixmap = tiny_skia::Pixmap::new(width, height).ok_or_else(|| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
            "Cannot allocate a {}x{} pixmap for SVG '{}'",
            width, height, path
        ))
    })?;

    // Map the document's intrinsic coordinate space onto the full target
    // pixmap. The caller sizes the target to the intrinsic aspect ratio
    // (aspect-fit), so the scale is effectively uniform; computing both
    // axes keeps the output exactly width x height regardless.
    let transform = tiny_skia::Transform::from_scale(
        width as f32 / intrinsic.width(),
        height as f32 / intrinsic.height(),
    );
    resvg::render(&tree, transform, &mut pixmap.as_mut());

    // tiny-skia stores PREMULTIPLIED RGBA8 - `Pixmap` is "a container that
    // owns premultiplied RGBA pixels" and `Pixmap::data()`/`take()` return
    // those bytes as-is (tiny-skia src/pixmap.rs). That is exactly what the
    // ALPHA_PREMULT image overlay pass expects (img_op.draw_all_images),
    // so no premultiply step is needed here, unlike decode_gif.
    let mut pixels = pixmap.take();
    flip_scanlines_in_place(&mut pixels, width, height);
    Ok(pixels)
}

/// Probe an SVG's intrinsic size without rasterizing.
///
/// Returns `(width, height)` in CSS pixels, resolved by usvg from the
/// `width`/`height` attributes with a `viewBox` fallback - feeds
/// aspect-ratio fitting (ImageInstance.get_display_size) before the
/// first rasterization.
#[pyfunction]
pub fn probe_svg(path: &str) -> PyResult<(f32, f32)> {
    let tree = load_tree(path, None)?;
    let size = tree.size();
    Ok((size.width(), size.height()))
}

/// Rasterize an SVG file to exactly `width x height` RGBA8 bytes.
///
/// - Output is PREMULTIPLIED RGBA8 (native tiny-skia pixel format, see
///   `rasterize_svg_impl`) in bottom-up scanline order (flipped once here,
///   like `decode_gif` - ready for GPUTexture upload in the image overlay
///   pass), exactly `width * height * 4` bytes.
/// - The caller computes `width x height` from the intrinsic size
///   (`probe_svg`) to preserve aspect; the document is scaled to fill the
///   target exactly.
/// - `fonts_dir`: optional extra font directory (the addon's `fonts/`)
///   loaded into the shared system-font database on first use, so
///   `<text>` elements resolve bundled UI fonts too.
#[pyfunction]
#[pyo3(signature = (path, width, height, fonts_dir = None))]
pub fn rasterize_svg(
    py: Python,
    path: &str,
    width: u32,
    height: u32,
    fonts_dir: Option<&str>,
) -> PyResult<Py<PyBytes>> {
    let pixels = rasterize_svg_impl(path, width, height, fonts_dir)?;
    Ok(PyBytes::new(py, &pixels).into())
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Write an inline SVG to a unique temp file; removed on drop.
    struct TempSvg(PathBuf);

    impl TempSvg {
        fn new(name: &str, content: &str) -> Self {
            let path = std::env::temp_dir().join(format!(
                "puree_svg_test_{}_{}.svg",
                std::process::id(),
                name
            ));
            std::fs::write(&path, content).expect("temp svg written");
            TempSvg(path)
        }

        fn path(&self) -> &str {
            self.0.to_str().unwrap()
        }
    }

    impl Drop for TempSvg {
        fn drop(&mut self) {
            let _ = std::fs::remove_file(&self.0);
        }
    }

    fn px(pixels: &[u8], width: u32, x: u32, y: u32) -> [u8; 4] {
        let i = ((y * width + x) * 4) as usize;
        [pixels[i], pixels[i + 1], pixels[i + 2], pixels[i + 3]]
    }

    #[test]
    fn probe_reads_intrinsic_size_from_viewbox() {
        // No width/height attributes: usvg falls back to the viewBox size.
        let svg = TempSvg::new(
            "probe",
            r##"<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 60"><rect width="80" height="60" fill="#123456"/></svg>"##,
        );
        let (w, h) = probe_svg(svg.path()).expect("probe ok");
        assert_eq!((w, h), (80.0, 60.0));
    }

    #[test]
    fn rasterize_flips_bottom_up_and_stays_premultiplied() {
        // Top half opaque red, bottom half 50% green. After the bottom-up
        // flip the buffer must START with green rows and END with red rows.
        let svg = TempSvg::new(
            "flip",
            r##"<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8" viewBox="0 0 8 8"><rect x="0" y="0" width="8" height="4" fill="#ff0000"/><rect x="0" y="4" width="8" height="4" fill="#00ff00" fill-opacity="0.5"/></svg>"##,
        );
        let pixels = rasterize_svg_impl(svg.path(), 8, 8, None).expect("raster ok");
        assert_eq!(pixels.len(), 8 * 8 * 4);

        // Buffer row 1 = image bottom half = translucent green.
        let bottom = px(&pixels, 8, 4, 1);
        assert_eq!(bottom[0], 0, "no red in the bottom half");
        assert!(bottom[1] > 0, "green present");
        assert!(bottom[3] < 255, "translucent");
        // Buffer row 6 = image top half = opaque red.
        let top = px(&pixels, 8, 4, 6);
        assert_eq!(top, [255, 0, 0, 255]);

        // Premultiplied output: no channel may exceed its alpha.
        for p in pixels.chunks_exact(4) {
            assert!(
                p[0] <= p[3] && p[1] <= p[3] && p[2] <= p[3],
                "straight alpha pixel: {:?}",
                p
            );
        }
    }

    #[test]
    fn rasterize_scales_to_exact_target_size() {
        let svg = TempSvg::new(
            "scale",
            r##"<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 60"><rect width="80" height="60" fill="#4772b3"/></svg>"##,
        );
        // 2x the intrinsic size, aspect preserved by the caller.
        let pixels = rasterize_svg_impl(svg.path(), 160, 120, None).expect("raster ok");
        assert_eq!(pixels.len(), 160 * 120 * 4);
        assert_eq!(px(&pixels, 160, 80, 60), [0x47, 0x72, 0xb3, 255]);
    }

    #[test]
    fn rasterize_error_paths() {
        assert!(rasterize_svg_impl("does_not_exist.svg", 8, 8, None).is_err());

        let not_svg = TempSvg::new("bad", "this is not an svg document");
        assert!(rasterize_svg_impl(not_svg.path(), 8, 8, None).is_err());

        let ok = TempSvg::new(
            "zero",
            r##"<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8"/>"##,
        );
        assert!(rasterize_svg_impl(ok.path(), 0, 8, None).is_err());
        assert!(rasterize_svg_impl(ok.path(), 8, 0, None).is_err());
    }
}
