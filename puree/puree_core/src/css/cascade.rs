use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use lightningcss::stylesheet::{ParserOptions, PrinterOptions, StyleSheet};
use std::collections::HashMap;
use crate::color::parse_color;

// ── Owned selector representation ──────────────────────────────────

#[derive(Clone, Debug)]
enum SimpleSelector {
    Class(String),
    Id(String),
    Universal,
    FirstChild,
    LastChild,
    NthChild(i32, i32), // an+b: matches when (index - b) is a non-negative multiple of a
    Not(Vec<SimpleSelector>),
}

#[derive(Clone, Debug)]
enum SelectorPart {
    Simple(SimpleSelector),
    Descendant,         // space combinator
    Child,              // > combinator
    AdjacentSibling,    // + combinator
    GeneralSibling,     // ~ combinator
}

#[derive(Clone, Debug, Default)]
struct MediaCondition {
    min_width: Option<f32>,
    max_width: Option<f32>,
    min_height: Option<f32>,
    max_height: Option<f32>,
}

impl MediaCondition {
    fn matches(&self, viewport_w: f32, viewport_h: f32) -> bool {
        if let Some(mw) = self.min_width {
            if viewport_w < mw { return false; }
        }
        if let Some(mw) = self.max_width {
            if viewport_w > mw { return false; }
        }
        if let Some(mh) = self.min_height {
            if viewport_h < mh { return false; }
        }
        if let Some(mh) = self.max_height {
            if viewport_h > mh { return false; }
        }
        true
    }
    fn is_unconditional(&self) -> bool {
        self.min_width.is_none() && self.max_width.is_none()
            && self.min_height.is_none() && self.max_height.is_none()
    }
}

struct CascadeRule {
    selector_parts: Vec<SelectorPart>, // right-to-left order
    specificity: u32,
    declarations: HashMap<String, String>,
    important_declarations: HashMap<String, String>,
    source_order: usize,
    media: MediaCondition,
}

// ── Container tree node ────────────────────────────────────────────

struct ContainerInfo {
    id: String,
    classes: Vec<String>,
    parent_idx: i64,
    child_index: usize,
    sibling_count: usize,
}

// ── Inherited properties (CSS-standard names) ─────────────────────

const INHERITED_PROPERTIES: &[&str] = &["color", "font-size", "text-align", "font-family", "font-weight", "font-style", "pointer-events", "visibility", "text-transform", "line-height", "letter-spacing", "white-space"];

// ── Strip `--` prefix from custom properties ──────────────────────

fn strip_custom_prefix(css_name: &str) -> String {
    if css_name.starts_with("--") {
        css_name[2..].to_string()
    } else {
        css_name.to_string()
    }
}

/// Parse `border: <width> <style> <color>` shorthand into border-width and border-color.
/// `border-style` is always solid in Puree, so we ignore it.
fn expand_border(value: &str) -> Vec<(String, String)> {
    let value = value.trim();
    if value == "none" || value == "0" || value.is_empty() {
        return vec![
            ("border-width".into(), "0".into()),
            ("border-color".into(), "transparent".into()),
        ];
    }

    let mut parts = Vec::new();
    let mut current = String::new();
    let mut paren_depth = 0;
    for ch in value.chars() {
        if ch == '(' { paren_depth += 1; }
        if ch == ')' { paren_depth -= 1; }
        if ch == ' ' && paren_depth == 0 {
            if !current.is_empty() {
                parts.push(current.clone());
                current.clear();
            }
        } else {
            current.push(ch);
        }
    }
    if !current.is_empty() {
        parts.push(current);
    }

    let mut width = String::new();
    let mut color = String::new();

    for part in &parts {
        // Skip border-style keywords
        if matches!(part.as_str(), "solid" | "dashed" | "dotted" | "double" | "groove" | "ridge" | "inset" | "outset" | "none" | "hidden") {
            continue;
        }
        let trimmed = part.trim_end_matches("px");
        if trimmed.parse::<f64>().is_ok() {
            width = part.clone();
        } else {
            color = part.clone();
        }
    }

    let mut result = Vec::new();
    if !width.is_empty() {
        result.push(("border-width".into(), width));
    }
    if !color.is_empty() {
        result.push(("border-color".into(), color));
    }
    result
}

/// Parse `background: <color>` or `background: linear-gradient(...)` shorthand.
fn expand_background(value: &str) -> Vec<(String, String)> {
    let value = value.trim();
    if value == "none" || value == "transparent" || value.is_empty() {
        return vec![("background-color".into(), "transparent".into())];
    }
    // Handle linear-gradient(angle, color1, color2, ...)
    if value.starts_with("linear-gradient(") && value.ends_with(')') {
        let inner = &value[16..value.len()-1]; // strip "linear-gradient(" and ")"
        // Tokenize by comma, respecting nested parentheses
        let args = split_respecting_parens(inner, ',');
        if args.len() >= 2 {
            let mut result = Vec::new();
            let first = args[0].trim();
            let mut color_start_idx = 0;
            let mut angle_deg: f64 = 180.0;
            // Check if first arg is an angle or direction keyword
            if first.ends_with("deg") || first.ends_with("rad") || first.ends_with("turn")
                || first.starts_with("to ") {
                angle_deg = parse_gradient_angle(first);
                color_start_idx = 1;
            }

            let color_stops = &args[color_start_idx..];

            if color_stops.len() >= 3 {
                // Multi-stop gradient: emit --gradient-stops encoding
                let mut colors = Vec::new();
                let mut positions: Vec<Option<f32>> = Vec::new();
                for stop in color_stops {
                    let (color_str, pos) = parse_color_stop(stop);
                    colors.push(color_str);
                    positions.push(pos);
                }
                auto_distribute_positions(&mut positions);

                let mut parts_str = format!("{}", angle_deg);
                for (i, color_str) in colors.iter().enumerate() {
                    if let Ok(rgba) = parse_color(color_str) {
                        let pos = positions[i].unwrap_or(0.0);
                        parts_str.push_str(&format!(" {} {} {} {} {}",
                            rgba[0], rgba[1], rgba[2], rgba[3], pos));
                    }
                }

                result.push(("gradient-stops".into(), parts_str));
                result.push(("background-color".into(), colors[0].clone()));
                return result;
            }

            // 2-stop gradient (original behavior)
            result.push(("background-gradient-rot".into(), format!("{}deg", angle_deg)));
            if color_start_idx < args.len() {
                result.push(("background-color".into(), args[color_start_idx].trim().to_string()));
            }
            if color_start_idx + 1 < args.len() {
                result.push(("background-color-2".into(), args[color_start_idx + 1].trim().to_string()));
            }
            return result;
        }
    }
    // Solid color fallback
    vec![("background-color".into(), value.to_string())]
}

/// Parse a single color stop into (color_string, optional_position_0_to_1).
fn parse_color_stop(stop_str: &str) -> (String, Option<f32>) {
    let s = stop_str.trim();
    // Find the last space outside parentheses
    let mut last_space = None;
    let mut depth = 0i32;
    for (i, ch) in s.char_indices() {
        if ch == '(' { depth += 1; }
        if ch == ')' { depth -= 1; }
        if ch == ' ' && depth == 0 {
            last_space = Some(i);
        }
    }
    if let Some(sp) = last_space {
        let potential_pos = s[sp + 1..].trim();
        if let Some(pct) = potential_pos.strip_suffix('%') {
            if let Ok(val) = pct.trim().parse::<f32>() {
                return (s[..sp].trim().to_string(), Some(val / 100.0));
            }
        }
    }
    (s.to_string(), None)
}

/// Auto-distribute positions for color stops following CSS rules:
/// first=0%, last=100%, gaps evenly distributed between neighbors.
fn auto_distribute_positions(positions: &mut [Option<f32>]) {
    let n = positions.len();
    if n == 0 { return; }
    if positions[0].is_none() { positions[0] = Some(0.0); }
    if positions[n - 1].is_none() { positions[n - 1] = Some(1.0); }

    let mut i = 1;
    while i < n {
        if positions[i].is_some() {
            i += 1;
            continue;
        }
        let start = i - 1;
        let mut end = i;
        while end < n && positions[end].is_none() {
            end += 1;
        }
        let start_pos = positions[start].unwrap();
        let end_pos = positions[end].unwrap();
        let gap_count = (end - start) as f32;
        for j in (start + 1)..end {
            let t = (j - start) as f32 / gap_count;
            positions[j] = Some(start_pos + t * (end_pos - start_pos));
        }
        i = end + 1;
    }
}

/// Parse `border-image: linear-gradient(angle, c1, c2)` shorthand.
/// Maps to the same internal border gradient slots. Non-gradient values are ignored.
fn expand_border_image(value: &str) -> Vec<(String, String)> {
    let value = value.trim();
    if !value.starts_with("linear-gradient(") || !value.ends_with(')') {
        return vec![];
    }
    let inner = &value[16..value.len()-1];
    let args = split_respecting_parens(inner, ',');
    if args.len() < 2 {
        return vec![];
    }
    let first = args[0].trim();
    let mut color_start_idx = 0;
    let mut angle_deg: f64 = 180.0;
    if first.ends_with("deg") || first.ends_with("rad") || first.ends_with("turn")
        || first.starts_with("to ") {
        angle_deg = parse_gradient_angle(first);
        color_start_idx = 1;
    }
    let color_stops = &args[color_start_idx..];
    if color_stops.len() < 2 {
        return vec![];
    }
    let c0 = color_stops[0].trim().to_string();
    let c1 = color_stops[1].trim().to_string();
    vec![
        ("border-color".into(), c0),
        ("border-color-2".into(), c1),
        ("border-gradient-rot".into(), format!("{}deg", angle_deg)),
    ]
}


/// Parse gradient angle from CSS syntax.
/// Supports: "135deg", "1.5rad", "0.25turn", "to right", "to bottom left", etc.
fn parse_gradient_angle(s: &str) -> f64 {
    let s = s.trim();
    if let Some(deg) = s.strip_suffix("deg") {
        return deg.trim().parse::<f64>().unwrap_or(180.0);
    }
    if let Some(rad) = s.strip_suffix("rad") {
        return rad.trim().parse::<f64>().unwrap_or(std::f64::consts::PI) * 180.0 / std::f64::consts::PI;
    }
    if let Some(turn) = s.strip_suffix("turn") {
        return turn.trim().parse::<f64>().unwrap_or(0.5) * 360.0;
    }
    // Direction keywords: "to right", "to bottom", "to top left", etc.
    if s.starts_with("to ") {
        let dir = &s[3..].trim().to_lowercase();
        return match dir.as_str() {
            "top" => 0.0,
            "right" => 90.0,
            "bottom" => 180.0,
            "left" => 270.0,
            "top right" | "right top" => 45.0,
            "bottom right" | "right bottom" => 135.0,
            "bottom left" | "left bottom" => 225.0,
            "top left" | "left top" => 315.0,
            _ => 180.0,
        };
    }
    180.0 // CSS default: top-to-bottom
}

/// Split a string by a delimiter, respecting parentheses nesting.
fn split_respecting_parens(s: &str, delim: char) -> Vec<String> {
    let mut parts = Vec::new();
    let mut current = String::new();
    let mut depth = 0;
    for ch in s.chars() {
        if ch == '(' { depth += 1; }
        if ch == ')' { depth -= 1; }
        if ch == delim && depth == 0 {
            parts.push(current.clone());
            current.clear();
        } else {
            current.push(ch);
        }
    }
    if !current.is_empty() {
        parts.push(current);
    }
    parts
}

/// Expand `flex` shorthand: `flex: 1`, `flex: 0 1 auto`, `flex: none`
fn expand_flex(value: &str) -> Vec<(String, String)> {
    let value = value.trim();
    match value {
        "none" => return vec![
            ("flex-grow".into(), "0".into()),
            ("flex-shrink".into(), "0".into()),
            ("flex-basis".into(), "auto".into()),
        ],
        "auto" => return vec![
            ("flex-grow".into(), "1".into()),
            ("flex-shrink".into(), "1".into()),
            ("flex-basis".into(), "auto".into()),
        ],
        "initial" => return vec![
            ("flex-grow".into(), "0".into()),
            ("flex-shrink".into(), "1".into()),
            ("flex-basis".into(), "auto".into()),
        ],
        _ => {}
    }
    let parts: Vec<&str> = value.split_whitespace().collect();
    match parts.len() {
        1 => {
            // flex: <number> → flex-grow: <number>; flex-shrink: 1; flex-basis: 0%
            vec![
                ("flex-grow".into(), parts[0].to_string()),
                ("flex-shrink".into(), "1".into()),
                ("flex-basis".into(), "0%".into()),
            ]
        }
        2 => {
            // flex: <grow> <shrink> OR flex: <grow> <basis>
            let second = parts[1];
            if second.parse::<f64>().is_ok() {
                vec![
                    ("flex-grow".into(), parts[0].to_string()),
                    ("flex-shrink".into(), second.to_string()),
                    ("flex-basis".into(), "0%".into()),
                ]
            } else {
                vec![
                    ("flex-grow".into(), parts[0].to_string()),
                    ("flex-shrink".into(), "1".into()),
                    ("flex-basis".into(), second.to_string()),
                ]
            }
        }
        3 => {
            // flex: <grow> <shrink> <basis>
            vec![
                ("flex-grow".into(), parts[0].to_string()),
                ("flex-shrink".into(), parts[1].to_string()),
                ("flex-basis".into(), parts[2].to_string()),
            ]
        }
        _ => vec![]
    }
}

/// Expand `gap` shorthand: `gap: 10px`, `gap: 10px 20px`
fn expand_gap(value: &str) -> Vec<(String, String)> {
    let parts: Vec<&str> = value.trim().split_whitespace().collect();
    match parts.len() {
        1 => vec![
            ("row-gap".into(), parts[0].to_string()),
            ("column-gap".into(), parts[0].to_string()),
        ],
        2 => vec![
            ("row-gap".into(), parts[0].to_string()),
            ("column-gap".into(), parts[1].to_string()),
        ],
        _ => vec![("row-gap".into(), value.trim().to_string()),
                  ("column-gap".into(), value.trim().to_string())]
    }
}

/// Expand `font` shorthand: `font: [style] [weight] size[/line-height] family`
fn expand_font(value: &str) -> Vec<(String, String)> {
    let value = value.trim();
    let parts = split_respecting_parens(value, ' ');
    if parts.is_empty() { return vec![]; }

    let style_keywords = ["italic", "oblique", "normal"];
    let weight_keywords = ["bold", "bolder", "lighter", "normal",
        "100", "200", "300", "400", "500", "600", "700", "800", "900"];

    let mut result = Vec::new();
    let mut i = 0;

    // Optional font-style
    if i < parts.len() && style_keywords.contains(&parts[i].to_lowercase().as_str()) {
        result.push(("font-style".into(), parts[i].to_string()));
        i += 1;
    }
    // Optional font-weight
    if i < parts.len() && weight_keywords.contains(&parts[i].to_lowercase().as_str()) {
        result.push(("font-weight".into(), parts[i].to_string()));
        i += 1;
    }
    // Required: font-size (possibly with /line-height)
    if i < parts.len() {
        let size_part = &parts[i];
        if let Some(slash) = size_part.find('/') {
            result.push(("font-size".into(), size_part[..slash].to_string()));
            result.push(("line-height".into(), size_part[slash+1..].to_string()));
        } else {
            result.push(("font-size".into(), size_part.to_string()));
        }
        i += 1;
    }
    // Remaining: font-family (may be multi-word)
    if i < parts.len() {
        let family = parts[i..].join(" ");
        result.push(("font-family".into(), family));
    }
    result
}

/// Expand `overflow` shorthand: `overflow: hidden`, `overflow: hidden visible`
fn expand_overflow(value: &str) -> Vec<(String, String)> {
    let parts: Vec<&str> = value.trim().split_whitespace().collect();
    match parts.len() {
        1 => vec![
            ("overflow-x".into(), parts[0].to_string()),
            ("overflow-y".into(), parts[0].to_string()),
        ],
        2 => vec![
            ("overflow-x".into(), parts[0].to_string()),
            ("overflow-y".into(), parts[1].to_string()),
        ],
        _ => vec![
            ("overflow-x".into(), value.trim().to_string()),
            ("overflow-y".into(), value.trim().to_string()),
        ]
    }
}
/// Parse `border-radius` shorthand into per-corner radius properties.
/// Follows CSS spec: 1 value → all, 2 → TL+BR / TR+BL, 3 → TL / TR+BL / BR, 4 → TL TR BR BL.
/// Also handles individual CSS longhands (border-top-left-radius, etc.).
fn expand_border_radius(value: &str) -> Vec<(String, String)> {
    let value = value.trim();
    if value.is_empty() || value == "0" || value == "0px" {
        return vec![
            ("border-radius-tl".into(), "0".into()),
            ("border-radius-tr".into(), "0".into()),
            ("border-radius-br".into(), "0".into()),
            ("border-radius-bl".into(), "0".into()),
        ];
    }

    let parts: Vec<&str> = value.split_whitespace().collect();
    let (tl, tr, br, bl) = match parts.len() {
        1 => (parts[0], parts[0], parts[0], parts[0]),
        2 => (parts[0], parts[1], parts[0], parts[1]),
        3 => (parts[0], parts[1], parts[2], parts[1]),
        4 => (parts[0], parts[1], parts[2], parts[3]),
        _ => (parts[0], parts[0], parts[0], parts[0]),
    };

    vec![
        ("border-radius-tl".into(), tl.to_string()),
        ("border-radius-tr".into(), tr.to_string()),
        ("border-radius-br".into(), br.to_string()),
        ("border-radius-bl".into(), bl.to_string()),
    ]
}

/// Expand `border-width` shorthand into per-side border-width properties.
/// Follows CSS spec: 1 value → all, 2 → top+bottom / left+right, 3 → top / left+right / bottom, 4 → top right bottom left.
fn expand_border_width(value: &str) -> Vec<(String, String)> {
    let value = value.trim();
    let parts: Vec<&str> = value.split_whitespace().collect();
    let (top, right, bottom, left) = match parts.len() {
        1 => (parts[0], parts[0], parts[0], parts[0]),
        2 => (parts[0], parts[1], parts[0], parts[1]),
        3 => (parts[0], parts[1], parts[2], parts[1]),
        4 => (parts[0], parts[1], parts[2], parts[3]),
        _ => (parts[0], parts[0], parts[0], parts[0]),
    };

    vec![
        ("border-top-width".into(), top.to_string()),
        ("border-right-width".into(), right.to_string()),
        ("border-bottom-width".into(), bottom.to_string()),
        ("border-left-width".into(), left.to_string()),
    ]
}

/// Returns vec of (property_name, value) pairs.
fn expand_box_shadow(value: &str) -> Vec<(String, String)> {
    let value = value.trim();
    if value == "none" || value.is_empty() {
        return vec![
            ("box-shadow-color".into(), "transparent".into()),
            ("box-shadow-offset".into(), "0px 0px".into()),
            ("box-shadow-blur".into(), "0".into()),
        ];
    }

    // Tokenize respecting parentheses (for rgba(...) etc)
    let mut parts = Vec::new();
    let mut current = String::new();
    let mut paren_depth = 0;

    for ch in value.chars() {
        if ch == '(' { paren_depth += 1; }
        if ch == ')' { paren_depth -= 1; }
        if ch == ' ' && paren_depth == 0 {
            if !current.is_empty() {
                parts.push(current.clone());
                current.clear();
            }
        } else {
            current.push(ch);
        }
    }
    if !current.is_empty() {
        parts.push(current);
    }

    // Separate numeric parts (offsets/blur/spread) from color
    let mut numbers = Vec::new();
    let mut color_str = String::new();

    for part in &parts {
        if part == "inset" {
            continue;
        }
        let trimmed = part.trim_end_matches("px");
        if trimmed.parse::<f64>().is_ok() {
            numbers.push(part.clone());
        } else {
            color_str = part.clone();
        }
    }

    // Standard: offset-x offset-y [blur-radius] [spread-radius] color
    let offset_x = numbers.first().cloned().unwrap_or_else(|| "0px".into());
    let offset_y = numbers.get(1).cloned().unwrap_or_else(|| "0px".into());
    let blur = numbers.get(2).cloned().unwrap_or_else(|| "0px".into());
    let spread = numbers.get(3).cloned().unwrap_or_else(|| "0px".into());

    vec![
        ("box-shadow-color".into(), if color_str.is_empty() { "#000".into() } else { color_str }),
        ("box-shadow-offset".into(), format!("{} {} {}", offset_x, offset_y, spread)),
        ("box-shadow-blur".into(), blur),
    ]
}

/// Expand `text-shadow: offset-x offset-y [blur-radius] [color]`
fn expand_text_shadow(value: &str) -> Vec<(String, String)> {
    let value = value.trim();
    if value == "none" || value.is_empty() {
        return vec![
            ("text-shadow-color".into(), "transparent".into()),
            ("text-shadow-offset-x".into(), "0".into()),
            ("text-shadow-offset-y".into(), "0".into()),
            ("text-shadow-blur".into(), "0".into()),
        ];
    }

    // Tokenize respecting parentheses (for rgba(...) etc)
    let mut parts = Vec::new();
    let mut current = String::new();
    let mut paren_depth = 0;

    for ch in value.chars() {
        if ch == '(' { paren_depth += 1; }
        if ch == ')' { paren_depth -= 1; }
        if ch == ' ' && paren_depth == 0 {
            if !current.is_empty() {
                parts.push(current.clone());
                current.clear();
            }
        } else {
            current.push(ch);
        }
    }
    if !current.is_empty() {
        parts.push(current);
    }

    let mut numbers = Vec::new();
    let mut color_str = String::new();

    for part in &parts {
        let trimmed = part.trim_end_matches("px");
        if trimmed.parse::<f64>().is_ok() {
            numbers.push(part.clone());
        } else {
            color_str = part.clone();
        }
    }

    let offset_x = numbers.first().cloned().unwrap_or_else(|| "0".into());
    let offset_y = numbers.get(1).cloned().unwrap_or_else(|| "0".into());
    let blur = numbers.get(2).cloned().unwrap_or_else(|| "0".into());

    vec![
        ("text-shadow-color".into(), if color_str.is_empty() { "#000".into() } else { color_str }),
        ("text-shadow-offset-x".into(), offset_x),
        ("text-shadow-offset-y".into(), offset_y),
        ("text-shadow-blur".into(), blur),
    ]
}

/// Expand `inset: top right bottom left` (same 1-4 value logic as margin/padding).
fn expand_inset(value: &str) -> Vec<(String, String)> {
    let parts: Vec<&str> = value.split_whitespace().collect();
    let (top, right, bottom, left) = match parts.len() {
        1 => (parts[0], parts[0], parts[0], parts[0]),
        2 => (parts[0], parts[1], parts[0], parts[1]),
        3 => (parts[0], parts[1], parts[2], parts[1]),
        4 => (parts[0], parts[1], parts[2], parts[3]),
        _ => return vec![],
    };
    vec![
        ("top".into(), top.to_string()),
        ("right".into(), right.to_string()),
        ("bottom".into(), bottom.to_string()),
        ("left".into(), left.to_string()),
    ]
}

/// Expand `place-items: align-items justify-items`.
fn expand_place_items(value: &str) -> Vec<(String, String)> {
    let parts: Vec<&str> = value.split_whitespace().collect();
    if parts.len() >= 2 {
        vec![
            ("align-items".into(), parts[0].to_string()),
            ("justify-items".into(), parts[1].to_string()),
        ]
    } else if parts.len() == 1 {
        vec![
            ("align-items".into(), parts[0].to_string()),
            ("justify-items".into(), parts[0].to_string()),
        ]
    } else {
        vec![]
    }
}

/// Expand `place-content: align-content justify-content`.
fn expand_place_content(value: &str) -> Vec<(String, String)> {
    let parts: Vec<&str> = value.split_whitespace().collect();
    if parts.len() >= 2 {
        vec![
            ("align-content".into(), parts[0].to_string()),
            ("justify-content".into(), parts[1].to_string()),
        ]
    } else if parts.len() == 1 {
        vec![
            ("align-content".into(), parts[0].to_string()),
            ("justify-content".into(), parts[0].to_string()),
        ]
    } else {
        vec![]
    }
}

/// Expand `place-self: align-self justify-self`.
fn expand_place_self(value: &str) -> Vec<(String, String)> {
    let parts: Vec<&str> = value.split_whitespace().collect();
    if parts.len() >= 2 {
        vec![
            ("align-self".into(), parts[0].to_string()),
            ("justify-self".into(), parts[1].to_string()),
        ]
    } else if parts.len() == 1 {
        vec![
            ("align-self".into(), parts[0].to_string()),
            ("justify-self".into(), parts[0].to_string()),
        ]
    } else {
        vec![]
    }
}

/// Expand `border-{side}: width style color` into uniform border-width + border-color.
fn expand_border_side(value: &str) -> Vec<(String, String)> {
    let value = value.trim();
    if value == "none" || value == "0" || value.is_empty() {
        return vec![
            ("border-width".into(), "0".into()),
            ("border-color".into(), "transparent".into()),
        ];
    }

    let mut parts = Vec::new();
    let mut current = String::new();
    let mut paren_depth = 0;
    for ch in value.chars() {
        if ch == '(' { paren_depth += 1; }
        if ch == ')' { paren_depth -= 1; }
        if ch == ' ' && paren_depth == 0 {
            if !current.is_empty() {
                parts.push(current.clone());
                current.clear();
            }
        } else {
            current.push(ch);
        }
    }
    if !current.is_empty() {
        parts.push(current);
    }

    let mut width = String::new();
    let mut color = String::new();

    for part in &parts {
        if matches!(part.as_str(), "solid" | "dashed" | "dotted" | "double" | "groove" | "ridge" | "inset" | "outset" | "none" | "hidden") {
            continue;
        }
        let trimmed = part.trim_end_matches("px");
        if trimmed.parse::<f64>().is_ok() {
            width = part.clone();
        } else {
            color = part.clone();
        }
    }

    let mut result = Vec::new();
    if !width.is_empty() {
        result.push(("border-width".into(), width));
    }
    if !color.is_empty() {
        result.push(("border-color".into(), color));
    }
    result
}

// ── Pseudo-class category ──────────────────────────────────────────

#[derive(Clone, Copy, PartialEq, Eq)]
enum PseudoState {
    Normal,
    Hover,
    Active,
}

// ── Text-based selector parsing ────────────────────────────────────

/// Parse a single CSS selector string into our owned representation.
/// Returns (parts in right-to-left matching order, pseudo state).
fn parse_selector_string(sel: &str) -> (Vec<SelectorPart>, PseudoState) {
    let sel = sel.trim();
    let mut pseudo = PseudoState::Normal;

    // Strip pseudo-classes and detect state
    let base_sel = if let Some(idx) = sel.find(":active") {
        pseudo = PseudoState::Active;
        format!("{}{}", &sel[..idx], &sel[idx + 7..])
    } else if let Some(idx) = sel.find(":hover") {
        pseudo = PseudoState::Hover;
        format!("{}{}", &sel[..idx], &sel[idx + 6..])
    } else {
        sel.to_string()
    };
    let base_sel = base_sel.trim();

    // Tokenize: split on whitespace and `>`
    let mut tokens: Vec<String> = Vec::new();
    let mut current = String::new();

    for ch in base_sel.chars() {
        match ch {
            '>' => {
                let t = current.trim().to_string();
                if !t.is_empty() {
                    tokens.push(t);
                }
                tokens.push(">".to_string());
                current.clear();
            }
            '+' => {
                let t = current.trim().to_string();
                if !t.is_empty() {
                    tokens.push(t);
                }
                tokens.push("+".to_string());
                current.clear();
            }
            '~' => {
                let t = current.trim().to_string();
                if !t.is_empty() {
                    tokens.push(t);
                }
                tokens.push("~".to_string());
                current.clear();
            }
            ' ' | '\t' => {
                let t = current.trim().to_string();
                if !t.is_empty() {
                    tokens.push(t);
                }
                current.clear();
            }
            _ => {
                current.push(ch);
            }
        }
    }
    let t = current.trim().to_string();
    if !t.is_empty() {
        tokens.push(t);
    }

    // Build parts in right-to-left order (reverse the tokens).
    // Insert Descendant combinators between adjacent compound selectors.
    let mut parts = Vec::new();
    let mut last_was_compound = false;

    for token in tokens.iter().rev() {
        if token == ">" {
            parts.push(SelectorPart::Child);
            last_was_compound = false;
        } else if token == "+" {
            parts.push(SelectorPart::AdjacentSibling);
            last_was_compound = false;
        } else if token == "~" {
            parts.push(SelectorPart::GeneralSibling);
            last_was_compound = false;
        } else {
            if last_was_compound {
                parts.push(SelectorPart::Descendant);
            }
            let compound = parse_compound_selector(token);
            if !compound.is_empty() {
                parts.extend(compound);
                last_was_compound = true;
            }
        }
    }

    (parts, pseudo)
}

/// Parse a compound selector like ".foo.bar" or "#id.class:first-child" into simple selectors.
fn parse_compound_selector(s: &str) -> Vec<SelectorPart> {
    let mut parts = Vec::new();
    let mut chars = s.chars().peekable();

    while chars.peek().is_some() {
        match chars.peek().copied() {
            Some('.') => {
                chars.next();
                let mut name = String::new();
                while let Some(&c) = chars.peek() {
                    if c == '.' || c == '#' || c == ':' || c == '[' {
                        break;
                    }
                    name.push(c);
                    chars.next();
                }
                if !name.is_empty() {
                    parts.push(SelectorPart::Simple(SimpleSelector::Class(name)));
                }
            }
            Some('#') => {
                chars.next();
                let mut name = String::new();
                while let Some(&c) = chars.peek() {
                    if c == '.' || c == '#' || c == ':' || c == '[' {
                        break;
                    }
                    name.push(c);
                    chars.next();
                }
                if !name.is_empty() {
                    parts.push(SelectorPart::Simple(SimpleSelector::Id(name)));
                }
            }
            Some('*') => {
                chars.next();
                parts.push(SelectorPart::Simple(SimpleSelector::Universal));
            }
            Some(':') => {
                chars.next();
                // Read pseudo-class name
                let mut pseudo_name = String::new();
                while let Some(&c) = chars.peek() {
                    if c == '(' || c == '.' || c == '#' || c == ':' || c == '[' || c == ' ' {
                        break;
                    }
                    pseudo_name.push(c);
                    chars.next();
                }
                // Read optional arguments in parentheses
                let mut args = String::new();
                if chars.peek() == Some(&'(') {
                    chars.next(); // consume '('
                    let mut depth = 1;
                    while let Some(&c) = chars.peek() {
                        chars.next();
                        if c == '(' { depth += 1; }
                        if c == ')' {
                            depth -= 1;
                            if depth == 0 { break; }
                        }
                        args.push(c);
                    }
                }
                match pseudo_name.as_str() {
                    "first-child" => {
                        parts.push(SelectorPart::Simple(SimpleSelector::FirstChild));
                    }
                    "last-child" => {
                        parts.push(SelectorPart::Simple(SimpleSelector::LastChild));
                    }
                    "nth-child" => {
                        let (a, b) = parse_nth_args(&args);
                        parts.push(SelectorPart::Simple(SimpleSelector::NthChild(a, b)));
                    }
                    "not" => {
                        let inner = parse_compound_selector(&args);
                        let simple_sels: Vec<SimpleSelector> = inner.into_iter().filter_map(|p| {
                            if let SelectorPart::Simple(s) = p { Some(s) } else { None }
                        }).collect();
                        if !simple_sels.is_empty() {
                            parts.push(SelectorPart::Simple(SimpleSelector::Not(simple_sels)));
                        }
                    }
                    _ => {} // skip hover/active (handled separately)
                }
            }
            _ => {
                // Skip unknown characters (element names, etc.)
                chars.next();
            }
        }
    }

    parts
}

/// Parse `an+b` notation from :nth-child() argument.
fn parse_nth_args(s: &str) -> (i32, i32) {
    let s = s.trim().to_lowercase();
    if s == "odd" {
        return (2, 1);
    }
    if s == "even" {
        return (2, 0);
    }
    // Try "an+b", "an-b", "an", "b", "-n+b", "n+b"
    if let Some(n_pos) = s.find('n') {
        let a_part = &s[..n_pos].trim();
        let a: i32 = if a_part.is_empty() || *a_part == "+" {
            1
        } else if *a_part == "-" {
            -1
        } else {
            a_part.parse().unwrap_or(1)
        };
        let rest = s[n_pos + 1..].trim().to_string();
        let b: i32 = if rest.is_empty() {
            0
        } else {
            rest.replace(' ', "").parse().unwrap_or(0)
        };
        (a, b)
    } else {
        // Just a number
        let b: i32 = s.parse().unwrap_or(0);
        (0, b)
    }
}

/// Calculate specificity from selector parts.
/// Packed as id_count * 0x10000 + class_count * 0x100.
fn calculate_specificity(parts: &[SelectorPart]) -> u32 {
    let mut ids: u32 = 0;
    let mut classes: u32 = 0;

    for part in parts {
        if let SelectorPart::Simple(sel) = part {
            match sel {
                SimpleSelector::Id(_) => ids += 1,
                SimpleSelector::Class(_) => classes += 1,
                SimpleSelector::Universal => {}
                SimpleSelector::FirstChild | SimpleSelector::LastChild | SimpleSelector::NthChild(_, _) => classes += 1,
                SimpleSelector::Not(inner) => {
                    // :not() specificity = highest specificity of its argument
                    for s in inner {
                        match s {
                            SimpleSelector::Id(_) => ids += 1,
                            SimpleSelector::Class(_) => classes += 1,
                            _ => classes += 1,
                        }
                    }
                }
            }
        }
    }

    (ids << 16) | (classes << 8)
}

/// Parse CSS text (normalized by lightningcss) into CascadeRules.
/// Parse @media condition string, e.g. "@media (min-width: 800px) and (max-height: 600px)"
fn parse_media_condition(text: &str) -> MediaCondition {
    let mut cond = MediaCondition::default();
    // Extract everything after "@media"
    let rest = text.strip_prefix("@media").unwrap_or("").trim();
    // Parse (property: value) pairs
    let re_like = |s: &str, prop: &str| -> Option<f32> {
        if let Some(pos) = s.find(prop) {
            let after = &s[pos + prop.len()..];
            let after = after.trim().trim_start_matches(':').trim();
            // Read number+px
            let num_str: String = after.chars().take_while(|c| c.is_ascii_digit() || *c == '.').collect();
            num_str.parse().ok()
        } else {
            None
        }
    };
    cond.min_width = re_like(rest, "min-width");
    cond.max_width = re_like(rest, "max-width");
    cond.min_height = re_like(rest, "min-height");
    cond.max_height = re_like(rest, "max-height");
    cond
}

fn parse_css_text_to_rules(css: &str) -> Vec<(CascadeRule, PseudoState, MediaCondition)> {
    let mut results = Vec::new();
    let mut source_order: usize = 0;
    let mut chars = css.chars().peekable();
    let mut current_text = String::new();

    while chars.peek().is_some() {
        let ch = chars.next().unwrap();

        if ch == '{' {
            let selector_text = current_text.trim().to_string();
            current_text.clear();

            // Read declaration block (handling nested braces)
            let mut depth = 1;
            let mut block = String::new();
            for c in chars.by_ref() {
                if c == '{' {
                    depth += 1;
                    block.push(c);
                } else if c == '}' {
                    depth -= 1;
                    if depth == 0 {
                        break;
                    }
                    block.push(c);
                } else {
                    block.push(c);
                }
            }

            if selector_text.is_empty() || selector_text.starts_with('@') {
                // Parse @media conditions
                let media_cond = if selector_text.starts_with("@media") {
                    parse_media_condition(&selector_text)
                } else {
                    MediaCondition::default()
                };
                if !block.is_empty() {
                    for (mut rule, pseudo, inner_media) in parse_css_text_to_rules(&block) {
                        // Merge media conditions (inner overrides if set)
                        if inner_media.is_unconditional() {
                            rule.media = media_cond.clone();
                        } else {
                            rule.media = inner_media;
                        }
                        rule.source_order = source_order;
                        source_order += 1;
                        results.push((rule, pseudo, MediaCondition::default()));
                    }
                }
                continue;
            }

            // Parse declarations
            let mut decls = HashMap::new();
            let mut important_decls = HashMap::new();

            for decl_text in block.split(';') {
                let decl_text = decl_text.trim();
                if decl_text.is_empty() || decl_text.contains('{') {
                    continue;
                }
                if let Some(colon_pos) = decl_text.find(':') {
                    let prop_name = decl_text[..colon_pos].trim();
                    let mut value = decl_text[colon_pos + 1..].trim().to_string();
                    let is_important = value.contains("!important");
                    if is_important {
                        value = value.replace("!important", "").trim().to_string();
                    }

                    // Expand box-shadow shorthand into multiple properties
                    if prop_name == "box-shadow" {
                        for (expanded_prop, expanded_val) in expand_box_shadow(&value) {
                            if is_important {
                                important_decls.insert(expanded_prop, expanded_val);
                            } else {
                                decls.insert(expanded_prop, expanded_val);
                            }
                        }
                        continue;
                    }

                    // Expand border shorthand into border-width + border-color
                    if prop_name == "border" {
                        for (expanded_prop, expanded_val) in expand_border(&value) {
                            if is_important {
                                important_decls.insert(expanded_prop, expanded_val);
                            } else {
                                decls.insert(expanded_prop, expanded_val);
                            }
                        }
                        continue;
                    }

                    // Expand border-radius shorthand into per-corner radii
                    if prop_name == "border-radius" && value.contains(' ') {
                        for (expanded_prop, expanded_val) in expand_border_radius(&value) {
                            if is_important {
                                important_decls.insert(expanded_prop, expanded_val);
                            } else {
                                decls.insert(expanded_prop, expanded_val);
                            }
                        }
                        continue;
                    }

                    // Expand background shorthand into background-color (+ gradient props)
                    if prop_name == "background" || prop_name == "background-image" {
                        for (expanded_prop, expanded_val) in expand_background(&value) {
                            if is_important {
                                important_decls.insert(expanded_prop, expanded_val);
                            } else {
                                decls.insert(expanded_prop, expanded_val);
                            }
                        }
                        continue;
                    }

                    // Expand border-image: linear-gradient() into border gradient slots
                    if prop_name == "border-image" {
                        for (expanded_prop, expanded_val) in expand_border_image(&value) {
                            if is_important {
                                important_decls.insert(expanded_prop, expanded_val);
                            } else {
                                decls.insert(expanded_prop, expanded_val);
                            }
                        }
                        continue;
                    }

                    // Expand flex shorthand into flex-grow + flex-shrink + flex-basis
                    if prop_name == "flex" {
                        for (expanded_prop, expanded_val) in expand_flex(&value) {
                            if is_important {
                                important_decls.insert(expanded_prop, expanded_val);
                            } else {
                                decls.insert(expanded_prop, expanded_val);
                            }
                        }
                        continue;
                    }

                    // Expand gap shorthand into row-gap + column-gap
                    if prop_name == "gap" {
                        for (expanded_prop, expanded_val) in expand_gap(&value) {
                            if is_important {
                                important_decls.insert(expanded_prop, expanded_val);
                            } else {
                                decls.insert(expanded_prop, expanded_val);
                            }
                        }
                        continue;
                    }

                    // Expand font shorthand into individual properties
                    if prop_name == "font" {
                        for (expanded_prop, expanded_val) in expand_font(&value) {
                            if is_important {
                                important_decls.insert(expanded_prop, expanded_val);
                            } else {
                                decls.insert(expanded_prop, expanded_val);
                            }
                        }
                        continue;
                    }

                    // Expand overflow shorthand into overflow-x + overflow-y
                    if prop_name == "overflow" && value.contains(' ') {
                        for (expanded_prop, expanded_val) in expand_overflow(&value) {
                            if is_important {
                                important_decls.insert(expanded_prop, expanded_val);
                            } else {
                                decls.insert(expanded_prop, expanded_val);
                            }
                        }
                        continue;
                    }

                    // Expand text-shadow shorthand
                    if prop_name == "text-shadow" {
                        for (expanded_prop, expanded_val) in expand_text_shadow(&value) {
                            if is_important {
                                important_decls.insert(expanded_prop, expanded_val);
                            } else {
                                decls.insert(expanded_prop, expanded_val);
                            }
                        }
                        continue;
                    }

                    // Expand inset shorthand into top/right/bottom/left
                    if prop_name == "inset" {
                        for (expanded_prop, expanded_val) in expand_inset(&value) {
                            if is_important {
                                important_decls.insert(expanded_prop, expanded_val);
                            } else {
                                decls.insert(expanded_prop, expanded_val);
                            }
                        }
                        continue;
                    }

                    // Expand place-items shorthand
                    if prop_name == "place-items" {
                        for (expanded_prop, expanded_val) in expand_place_items(&value) {
                            if is_important {
                                important_decls.insert(expanded_prop, expanded_val);
                            } else {
                                decls.insert(expanded_prop, expanded_val);
                            }
                        }
                        continue;
                    }

                    // Expand place-content shorthand
                    if prop_name == "place-content" {
                        for (expanded_prop, expanded_val) in expand_place_content(&value) {
                            if is_important {
                                important_decls.insert(expanded_prop, expanded_val);
                            } else {
                                decls.insert(expanded_prop, expanded_val);
                            }
                        }
                        continue;
                    }

                    // Expand place-self shorthand
                    if prop_name == "place-self" {
                        for (expanded_prop, expanded_val) in expand_place_self(&value) {
                            if is_important {
                                important_decls.insert(expanded_prop, expanded_val);
                            } else {
                                decls.insert(expanded_prop, expanded_val);
                            }
                        }
                        continue;
                    }

                    // Expand border-top/right/bottom/left shorthands
                    if matches!(prop_name, "border-top" | "border-right" | "border-bottom" | "border-left") {
                        for (expanded_prop, expanded_val) in expand_border_side(&value) {
                            if is_important {
                                important_decls.insert(expanded_prop, expanded_val);
                            } else {
                                decls.insert(expanded_prop, expanded_val);
                            }
                        }
                        continue;
                    }

                    // Expand border-width shorthand into per-side widths
                    if prop_name == "border-width" && value.contains(' ') {
                        for (expanded_prop, expanded_val) in expand_border_width(&value) {
                            if is_important {
                                important_decls.insert(expanded_prop, expanded_val);
                            } else {
                                decls.insert(expanded_prop, expanded_val);
                            }
                        }
                        continue;
                    }

                    // Map CSS longhand border-radius property names to internal short names
                    let mapped_name = match prop_name {
                        "border-top-left-radius" => "border-radius-tl".to_string(),
                        "border-top-right-radius" => "border-radius-tr".to_string(),
                        "border-bottom-right-radius" => "border-radius-br".to_string(),
                        "border-bottom-left-radius" => "border-radius-bl".to_string(),
                        _ => strip_custom_prefix(prop_name),
                    };
                    if is_important {
                        important_decls.insert(mapped_name, value);
                    } else {
                        decls.insert(mapped_name, value);
                    }
                }
            }

            // Handle comma-separated selectors
            for sel_str in selector_text.split(',') {
                let sel_str = sel_str.trim();
                if sel_str.is_empty() {
                    continue;
                }

                let (parts, pseudo) = parse_selector_string(sel_str);
                let specificity = calculate_specificity(&parts);

                let rule = CascadeRule {
                    selector_parts: parts,
                    specificity,
                    declarations: decls.clone(),
                    important_declarations: important_decls.clone(),
                    source_order,
                    media: MediaCondition::default(),
                };
                source_order += 1;
                results.push((rule, pseudo, MediaCondition::default()));
            }
        } else {
            current_text.push(ch);
        }
    }

    results
}

// ── Selector matching ──────────────────────────────────────────────

fn selector_matches(
    parts: &[SelectorPart],
    idx: usize,
    containers: &[ContainerInfo],
) -> bool {
    if parts.is_empty() {
        return false;
    }

    let mut part_cursor = 0;

    if !match_compound(parts, &mut part_cursor, &containers[idx]) {
        return false;
    }

    let mut current_idx = idx;

    while part_cursor < parts.len() {
        match &parts[part_cursor] {
            SelectorPart::Descendant => {
                part_cursor += 1;
                let mut current_ancestor_idx = containers[current_idx].parent_idx;
                let mut found = false;
                while current_ancestor_idx >= 0 {
                    let anc = current_ancestor_idx as usize;
                    if anc >= containers.len() {
                        break;
                    }
                    let mut try_cursor = part_cursor;
                    if match_compound(parts, &mut try_cursor, &containers[anc]) {
                        part_cursor = try_cursor;
                        current_idx = anc;
                        found = true;
                        break;
                    }
                    current_ancestor_idx = containers[anc].parent_idx;
                }
                if !found {
                    return false;
                }
            }
            SelectorPart::Child => {
                part_cursor += 1;
                let parent = containers[current_idx].parent_idx;
                if parent < 0 {
                    return false;
                }
                let anc = parent as usize;
                if anc >= containers.len() {
                    return false;
                }
                if !match_compound(parts, &mut part_cursor, &containers[anc]) {
                    return false;
                }
                current_idx = anc;
            }
            SelectorPart::AdjacentSibling => {
                part_cursor += 1;
                // Find immediate previous sibling
                let ci = containers[current_idx].child_index;
                if ci == 0 {
                    return false;
                }
                let parent = containers[current_idx].parent_idx;
                if let Some(prev_idx) = find_sibling(containers, parent, ci - 1) {
                    if !match_compound(parts, &mut part_cursor, &containers[prev_idx]) {
                        return false;
                    }
                    current_idx = prev_idx;
                } else {
                    return false;
                }
            }
            SelectorPart::GeneralSibling => {
                part_cursor += 1;
                let ci = containers[current_idx].child_index;
                let parent = containers[current_idx].parent_idx;
                let mut found = false;
                for target_ci in (0..ci).rev() {
                    if let Some(sib_idx) = find_sibling(containers, parent, target_ci) {
                        let mut try_cursor = part_cursor;
                        if match_compound(parts, &mut try_cursor, &containers[sib_idx]) {
                            part_cursor = try_cursor;
                            current_idx = sib_idx;
                            found = true;
                            break;
                        }
                    }
                }
                if !found {
                    return false;
                }
            }
            SelectorPart::Simple(_) => {
                return false;
            }
        }
    }

    true
}

/// Find a sibling container given parent index and child_index.
fn find_sibling(containers: &[ContainerInfo], parent_idx: i64, child_index: usize) -> Option<usize> {
    if parent_idx < 0 {
        return None;
    }
    containers.iter().position(|c| c.parent_idx == parent_idx && c.child_index == child_index)
}

fn match_compound(
    parts: &[SelectorPart],
    cursor: &mut usize,
    container: &ContainerInfo,
) -> bool {
    let start = *cursor;
    while *cursor < parts.len() {
        match &parts[*cursor] {
            SelectorPart::Simple(sel) => {
                if !match_simple(sel, container) {
                    *cursor = start;
                    return false;
                }
                *cursor += 1;
            }
            _ => break,
        }
    }
    *cursor > start
}

fn match_simple(sel: &SimpleSelector, container: &ContainerInfo) -> bool {
    match sel {
        SimpleSelector::Class(name) => container.classes.iter().any(|c| c == name),
        SimpleSelector::Id(name) => container.id == *name,
        SimpleSelector::Universal => true,
        SimpleSelector::FirstChild => container.child_index == 0,
        SimpleSelector::LastChild => container.child_index == container.sibling_count.saturating_sub(1),
        SimpleSelector::NthChild(a, b) => {
            let index = (container.child_index + 1) as i32; // 1-based
            if *a == 0 {
                index == *b
            } else {
                let diff = index - b;
                diff % a == 0 && diff / a >= 0
            }
        }
        SimpleSelector::Not(inner_sels) => {
            !inner_sels.iter().all(|s| match_simple(s, container))
        }
    }
}

// ── PyO3 class ─────────────────────────────────────────────────────

#[pyclass]
pub struct CSSCascade {
    normal_rules: Vec<CascadeRule>,
    hover_rules: Vec<CascadeRule>,
    active_rules: Vec<CascadeRule>,
}

#[pymethods]
impl CSSCascade {
    #[new]
    pub fn new() -> Self {
        CSSCascade {
            normal_rules: Vec::new(),
            hover_rules: Vec::new(),
            active_rules: Vec::new(),
        }
    }

    /// Parse CSS string and store rules (call after SCSS compilation).
    pub fn parse_css(&mut self, css_string: String) -> PyResult<()> {
        self.normal_rules.clear();
        self.hover_rules.clear();
        self.active_rules.clear();

        // Use lightningcss to normalize CSS (resolve nesting, clean up).
        let normalized = {
            let stylesheet =
                StyleSheet::parse(&css_string, ParserOptions::default()).map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                        "CSS parse error: {:?}",
                        e
                    ))
                })?;
            stylesheet
                .to_css(PrinterOptions::default())
                .map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                        "CSS print error: {:?}",
                        e
                    ))
                })?
                .code
        };

        for (rule, pseudo, _media) in parse_css_text_to_rules(&normalized) {
            match pseudo {
                PseudoState::Normal => self.normal_rules.push(rule),
                PseudoState::Hover => self.hover_rules.push(rule),
                PseudoState::Active => self.active_rules.push(rule),
            }
        }

        Ok(())
    }

    /// Resolve styles for all containers.
    /// Returns dict of `{container_id: {prop: value}}`.
    /// `state`: `"normal"` (default), `"hover"`, or `"active"`.
    /// `viewport`: `(width, height)` for @media query evaluation.
    pub fn resolve(
        &self,
        py: Python,
        containers: &PyList,
        state: Option<String>,
        viewport: Option<(f32, f32)>,
    ) -> PyResult<PyObject> {
        let state_str = state.as_deref().unwrap_or("normal");
        let rules = match state_str {
            "hover" => &self.hover_rules,
            "active" => &self.active_rules,
            _ => &self.normal_rules,
        };

        let (vp_w, vp_h) = viewport.unwrap_or((99999.0, 99999.0));

        let include_normal = state_str != "normal";

        let infos = parse_containers(containers)?;

        let mut resolved: Vec<HashMap<String, String>> = Vec::with_capacity(infos.len());
        for idx in 0..infos.len() {
            let mut matching: Vec<(bool, u32, usize, &str, &str)> = Vec::new();

            let rule_sets: Vec<&Vec<CascadeRule>> = if include_normal {
                vec![&self.normal_rules, rules]
            } else {
                vec![rules]
            };

            for rule_set in &rule_sets {
                for rule in *rule_set {
                    // Skip rules whose @media condition doesn't match
                    if !rule.media.is_unconditional() && !rule.media.matches(vp_w, vp_h) {
                        continue;
                    }
                    if selector_matches(&rule.selector_parts, idx, &infos) {
                        for (prop, value) in &rule.declarations {
                            matching.push((
                                false,
                                rule.specificity,
                                rule.source_order,
                                prop.as_str(),
                                value.as_str(),
                            ));
                        }
                        for (prop, value) in &rule.important_declarations {
                            matching.push((
                                true,
                                rule.specificity,
                                rule.source_order,
                                prop.as_str(),
                                value.as_str(),
                            ));
                        }
                    }
                }
            }

            // Sort: !important first, then specificity desc, then source order desc
            matching.sort_by(|a, b| {
                b.0.cmp(&a.0)
                    .then(b.1.cmp(&a.1))
                    .then(b.2.cmp(&a.2))
            });

            let mut props: HashMap<String, String> = HashMap::new();
            for (_imp, _spec, _order, prop, value) in &matching {
                props
                    .entry(prop.to_string())
                    .or_insert_with(|| value.to_string());
            }

            resolved.push(props);
        }

        // Keyword resolution + inheritance pass
        // Parents are always before children so we can resolve in order.
        let inherited_set: std::collections::HashSet<&str> =
            INHERITED_PROPERTIES.iter().copied().collect();

        for idx in 0..infos.len() {
            let parent = infos[idx].parent_idx;
            let pidx = if parent >= 0 && (parent as usize) < resolved.len() {
                Some(parent as usize)
            } else {
                None
            };

            // Resolve inherit / initial / unset keywords
            let keywords: Vec<(String, String)> = resolved[idx]
                .iter()
                .filter(|(_, v)| {
                    let lv = v.trim();
                    lv == "inherit" || lv == "initial" || lv == "unset"
                })
                .map(|(k, v)| (k.clone(), v.trim().to_string()))
                .collect();

            for (prop, kw) in keywords {
                match kw.as_str() {
                    "initial" => {
                        resolved[idx].remove(&prop);
                    }
                    "inherit" => {
                        resolved[idx].remove(&prop);
                        if let Some(pi) = pidx {
                            if let Some(pv) = resolved[pi].get(&prop).cloned() {
                                resolved[idx].insert(prop, pv);
                            }
                        }
                    }
                    "unset" => {
                        resolved[idx].remove(&prop);
                        if inherited_set.contains(prop.as_str()) {
                            if let Some(pi) = pidx {
                                if let Some(pv) = resolved[pi].get(&prop).cloned() {
                                    resolved[idx].insert(prop, pv);
                                }
                            }
                        }
                    }
                    _ => {}
                }
            }

            // Normal CSS inheritance for inherited properties
            if let Some(pi) = pidx {
                for &prop_name in INHERITED_PROPERTIES {
                    if resolved[idx].contains_key(prop_name) {
                        continue;
                    }
                    if let Some(parent_val) = resolved[pi].get(prop_name).cloned() {
                        resolved[idx].insert(prop_name.to_string(), parent_val);
                    }
                }
                // Custom properties (--*) are inherited by default in CSS
                let parent_customs: Vec<(String, String)> = resolved[pi]
                    .iter()
                    .filter(|(k, _)| k.starts_with("--"))
                    .map(|(k, v)| (k.clone(), v.clone()))
                    .collect();
                for (k, v) in parent_customs {
                    resolved[idx].entry(k).or_insert(v);
                }
            }
        }

        // var() resolution pass
        for idx in 0..resolved.len() {
            let props_snapshot: Vec<(String, String)> = resolved[idx]
                .iter()
                .filter(|(_, v)| v.contains("var("))
                .map(|(k, v)| (k.clone(), v.clone()))
                .collect();
            for (prop, value) in props_snapshot {
                let resolved_value = resolve_var(&value, &resolved[idx]);
                resolved[idx].insert(prop, resolved_value);
            }
        }

        let result = PyDict::new(py);
        for (idx, props) in resolved.iter().enumerate() {
            if props.is_empty() {
                continue;
            }
            let prop_dict = PyDict::new(py);
            for (k, v) in props {
                prop_dict.set_item(k, v)?;
            }
            result.set_item(&infos[idx].id, prop_dict)?;
        }

        Ok(result.into())
    }
}

// ── var() resolution ───────────────────────────────────────────────

fn resolve_var(value: &str, props: &HashMap<String, String>) -> String {
    let mut result = value.to_string();
    // Iteratively resolve var() references (max 10 depth to prevent cycles)
    for _ in 0..10 {
        if !result.contains("var(") {
            break;
        }
        let mut new_result = String::new();
        let mut chars = result.chars().peekable();
        let mut changed = false;

        while let Some(ch) = chars.next() {
            if ch == 'v' {
                let rest: String = std::iter::once(ch).chain(chars.clone()).take(4).collect();
                if rest.starts_with("var(") {
                    // consume "ar("
                    chars.next(); chars.next(); chars.next();
                    // read until matching )
                    let mut depth = 1;
                    let mut inner = String::new();
                    while let Some(c) = chars.next() {
                        if c == '(' { depth += 1; }
                        if c == ')' {
                            depth -= 1;
                            if depth == 0 { break; }
                        }
                        inner.push(c);
                    }
                    // inner = "--name" or "--name, fallback"
                    let (var_name, fallback) = if let Some(comma_pos) = inner.find(',') {
                        let name = inner[..comma_pos].trim().to_string();
                        let fb = inner[comma_pos + 1..].trim().to_string();
                        (name, Some(fb))
                    } else {
                        (inner.trim().to_string(), None)
                    };
                    if let Some(val) = props.get(&var_name) {
                        new_result.push_str(val);
                    } else if let Some(fb) = fallback {
                        new_result.push_str(&fb);
                    }
                    changed = true;
                    continue;
                }
            }
            new_result.push(ch);
        }
        if !changed { break; }
        result = new_result;
    }
    result
}

// ── Helper: parse Python container list ────────────────────────────

fn parse_containers(containers: &PyList) -> PyResult<Vec<ContainerInfo>> {
    let mut infos = Vec::with_capacity(containers.len());
    for item in containers.iter() {
        let dict: &PyDict = item.downcast()?;

        let id = dict
            .get_item("id")?
            .ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyKeyError, _>("missing 'id' in container dict")
            })?
            .extract::<String>()?;

        let classes: Vec<String> = dict
            .get_item("classes")?
            .ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyKeyError, _>(
                    "missing 'classes' in container dict",
                )
            })?
            .extract()?;

        let parent_idx: i64 = dict
            .get_item("parent_idx")?
            .ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyKeyError, _>(
                    "missing 'parent_idx' in container dict",
                )
            })?
            .extract()?;

        infos.push(ContainerInfo {
            id,
            classes,
            parent_idx,
            child_index: 0,
            sibling_count: 0,
        });
    }
    
    // Compute child_index and sibling_count
    // Group children by parent
    let mut parent_children: HashMap<i64, Vec<usize>> = HashMap::new();
    for (i, info) in infos.iter().enumerate() {
        parent_children.entry(info.parent_idx).or_default().push(i);
    }
    for (_parent, children) in &parent_children {
        let count = children.len();
        for (ci, &child_idx) in children.iter().enumerate() {
            infos[child_idx].child_index = ci;
            infos[child_idx].sibling_count = count;
        }
    }
    
    Ok(infos)
}
