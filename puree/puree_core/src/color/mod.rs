use pyo3::prelude::*;
use std::f32::consts::PI;
use palette::{Srgba, LinSrgba};
use csscolorparser::Color as CssColor;

#[pyclass]
#[derive(Clone)]
pub struct ColorProcessor {
    _marker: std::marker::PhantomData<()>,
}

#[pymethods]
impl ColorProcessor {
    #[new]
    pub fn new() -> Self {
        ColorProcessor {
            _marker: std::marker::PhantomData,
        }
    }

    pub fn gamma_correct(&self, value: f32) -> f32 {
        gamma_correct_single(value)
    }

    pub fn apply_gamma_correction(&self, r: f32, g: f32, b: f32, a: f32) -> [f32; 4] {
        apply_gamma_correction_simd(r, g, b, a)
    }

    pub fn parse_color(&self, color_str: &str) -> PyResult<[f32; 4]> {
        parse_color(color_str)
    }

    pub fn interpolate_color(
        &self,
        color1: [f32; 4],
        color2: [f32; 4],
        t: f32,
    ) -> [f32; 4] {
        interpolate_color_simd(color1, color2, t)
    }

    pub fn rotate_gradient(
        &self,
        color1: [f32; 4],
        color2: [f32; 4],
        rotation_deg: f32,
        x: f32,
        y: f32,
        width: f32,
        height: f32,
    ) -> [f32; 4] {
        rotate_gradient_optimized(color1, color2, rotation_deg, x, y, width, height)
    }

    pub fn process_colors_batch(
        &self,
        colors: Vec<(f32, f32, f32, f32)>,
    ) -> Vec<[f32; 4]> {
        process_colors_batch_simd(colors)
    }

    pub fn rgb_to_srgb(&self, r: f32, g: f32, b: f32) -> [f32; 3] {
        rgb_to_srgb(r, g, b)
    }

    pub fn srgb_to_rgb(&self, r: f32, g: f32, b: f32) -> [f32; 3] {
        srgb_to_rgb(r, g, b)
    }
}

#[inline]
pub fn gamma_correct_single(value: f32) -> f32 {
    value.powf(2.2)
}

#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "avx2")]
unsafe fn apply_gamma_correction_avx(r: f32, g: f32, b: f32, a: f32) -> [f32; 4] {
    let gamma = 2.2f32;
    [
        r.powf(gamma),
        g.powf(gamma),
        b.powf(gamma),
        a,
    ]
}

pub fn apply_gamma_correction_simd(r: f32, g: f32, b: f32, a: f32) -> [f32; 4] {
    #[cfg(target_arch = "x86_64")]
    {
        if is_x86_feature_detected!("avx2") {
            unsafe { apply_gamma_correction_avx(r, g, b, a) }
        } else {
            apply_gamma_correction_fallback(r, g, b, a)
        }
    }
    #[cfg(not(target_arch = "x86_64"))]
    {
        apply_gamma_correction_fallback(r, g, b, a)
    }
}

#[inline]
fn apply_gamma_correction_fallback(r: f32, g: f32, b: f32, a: f32) -> [f32; 4] {
    [
        gamma_correct_single(r),
        gamma_correct_single(g),
        gamma_correct_single(b),
        a,
    ]
}

pub fn parse_color(color_str: &str) -> PyResult<[f32; 4]> {
    let trimmed = color_str.trim();
    
    let css_color = CssColor::from_html(trimmed)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid color '{}': {}", trimmed, e)))?;
    
    let [r, g, b, a] = css_color.to_array();
    
    let srgba = Srgba::new(r as f32, g as f32, b as f32, a as f32);
    let linear: LinSrgba = srgba.into_linear();
    
    Ok([linear.red, linear.green, linear.blue, linear.alpha])
}

pub fn interpolate_color_simd(
    color1: [f32; 4],
    color2: [f32; 4],
    t: f32,
) -> [f32; 4] {
    use palette::Mix;
    
    let t_clamped = t.clamp(0.0, 1.0);
    
    let c1 = LinSrgba::new(color1[0], color1[1], color1[2], color1[3]);
    let c2 = LinSrgba::new(color2[0], color2[1], color2[2], color2[3]);
    
    let mixed = c1.mix(c2, t_clamped);
    
    [mixed.red, mixed.green, mixed.blue, mixed.alpha]
}

pub fn rotate_gradient_optimized(
    color1: [f32; 4],
    color2: [f32; 4],
    rotation_deg: f32,
    x: f32,
    y: f32,
    width: f32,
    height: f32,
) -> [f32; 4] {
    let rotation_rad = rotation_deg * PI / 180.0;
    let cos_rot = rotation_rad.cos();
    let sin_rot = rotation_rad.sin();
    
    let center_x = width * 0.5;
    let center_y = height * 0.5;
    
    let rel_x = x - center_x;
    let rel_y = y - center_y;
    
    let rotated_x = rel_x * cos_rot - rel_y * sin_rot;
    
    let t = (rotated_x / width + 0.5).max(0.0).min(1.0);
    
    interpolate_color_simd(color1, color2, t)
}

#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "avx2")]
unsafe fn process_colors_batch_avx(
    colors: Vec<(f32, f32, f32, f32)>,
) -> Vec<[f32; 4]> {
    colors
        .into_iter()
        .map(|(r, g, b, a)| apply_gamma_correction_avx(r, g, b, a))
        .collect()
}

pub fn process_colors_batch_simd(
    colors: Vec<(f32, f32, f32, f32)>,
) -> Vec<[f32; 4]> {
    #[cfg(target_arch = "x86_64")]
    {
        if is_x86_feature_detected!("avx2") {
            unsafe { process_colors_batch_avx(colors) }
        } else {
            process_colors_batch_fallback(colors)
        }
    }
    #[cfg(not(target_arch = "x86_64"))]
    {
        process_colors_batch_fallback(colors)
    }
}

fn process_colors_batch_fallback(
    colors: Vec<(f32, f32, f32, f32)>,
) -> Vec<[f32; 4]> {
    colors
        .into_iter()
        .map(|(r, g, b, a)| apply_gamma_correction_fallback(r, g, b, a))
        .collect()
}

pub fn rgb_to_srgb(r: f32, g: f32, b: f32) -> [f32; 3] {
    let linear = LinSrgba::new(r, g, b, 1.0);
    let srgb: Srgba = linear.into_encoding();
    [srgb.red, srgb.green, srgb.blue]
}

pub fn srgb_to_rgb(r: f32, g: f32, b: f32) -> [f32; 3] {
    let srgb = Srgba::new(r, g, b, 1.0);
    let linear: LinSrgba = srgb.into_linear();
    [linear.red, linear.green, linear.blue]
}

#[pyfunction]
pub fn gamma_correct(value: f32) -> f32 {
    gamma_correct_single(value)
}

#[pyfunction]
pub fn apply_gamma_correction_py(r: f32, g: f32, b: f32, a: f32) -> [f32; 4] {
    apply_gamma_correction_simd(r, g, b, a)
}

#[pyfunction]
pub fn parse_color_py(color_str: &str) -> PyResult<[f32; 4]> {
    parse_color(color_str)
}

#[pyfunction]
pub fn interpolate_color_py(
    color1: [f32; 4],
    color2: [f32; 4],
    t: f32,
) -> [f32; 4] {
    interpolate_color_simd(color1, color2, t)
}

#[pyfunction]
pub fn rotate_gradient_py(
    color1: [f32; 4],
    color2: [f32; 4],
    rotation_deg: f32,
    x: f32,
    y: f32,
    width: f32,
    height: f32,
) -> [f32; 4] {
    rotate_gradient_optimized(color1, color2, rotation_deg, x, y, width, height)
}
