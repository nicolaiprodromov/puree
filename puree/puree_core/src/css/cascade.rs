use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use lightningcss::stylesheet::{ParserOptions, PrinterOptions, StyleSheet};
use std::collections::HashMap;

// ── Owned selector representation ──────────────────────────────────

#[derive(Clone, Debug)]
enum SimpleSelector {
    Class(String),
    Id(String),
    Universal,
}

#[derive(Clone, Debug)]
enum SelectorPart {
    Simple(SimpleSelector),
    Descendant, // space combinator
    Child,      // > combinator
}

struct CascadeRule {
    selector_parts: Vec<SelectorPart>, // right-to-left order
    specificity: u32,
    declarations: HashMap<String, String>,
    important_declarations: HashMap<String, String>,
    source_order: usize,
}

// ── Container tree node ────────────────────────────────────────────

struct ContainerInfo {
    id: String,
    classes: Vec<String>,
    parent_idx: i64,
}

// ── Inherited properties (CSS-standard names) ─────────────────────

const INHERITED_PROPERTIES: &[&str] = &["color", "font-size", "text-align"];

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

/// Parse `background: <color>` shorthand. Only supports solid color for now.
fn expand_background(value: &str) -> Vec<(String, String)> {
    let value = value.trim();
    if value == "none" || value == "transparent" || value.is_empty() {
        return vec![("background-color".into(), "transparent".into())];
    }
    // For now, treat the entire value as a color (no gradient/image parsing)
    vec![("background-color".into(), value.to_string())]
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
    // spread (numbers[3]) is ignored — puree doesn't support it

    vec![
        ("box-shadow-color".into(), if color_str.is_empty() { "#000".into() } else { color_str }),
        ("box-shadow-offset".into(), format!("{} {}", offset_x, offset_y)),
        ("box-shadow-blur".into(), blur),
    ]
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

/// Parse a compound selector like ".foo.bar" or "#id.class" into simple selectors.
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
            _ => {
                // Skip unknown characters (element names, etc.)
                chars.next();
            }
        }
    }

    parts
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
            }
        }
    }

    (ids << 16) | (classes << 8)
}

/// Parse CSS text (normalized by lightningcss) into CascadeRules.
fn parse_css_text_to_rules(css: &str) -> Vec<(CascadeRule, PseudoState)> {
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
                // Unwrap @-rules: re-parse their content
                if !block.is_empty() {
                    for (mut rule, pseudo) in parse_css_text_to_rules(&block) {
                        rule.source_order = source_order;
                        source_order += 1;
                        results.push((rule, pseudo));
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

                    // Expand background shorthand into background-color
                    if prop_name == "background" {
                        for (expanded_prop, expanded_val) in expand_background(&value) {
                            if is_important {
                                important_decls.insert(expanded_prop, expanded_val);
                            } else {
                                decls.insert(expanded_prop, expanded_val);
                            }
                        }
                        continue;
                    }

                    let mapped_name = strip_custom_prefix(prop_name);
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
                };
                source_order += 1;
                results.push((rule, pseudo));
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

    let mut current_ancestor_idx = containers[idx].parent_idx;

    while part_cursor < parts.len() {
        match &parts[part_cursor] {
            SelectorPart::Descendant => {
                part_cursor += 1;
                let mut found = false;
                while current_ancestor_idx >= 0 {
                    let anc = current_ancestor_idx as usize;
                    if anc >= containers.len() {
                        break;
                    }
                    let mut try_cursor = part_cursor;
                    if match_compound(parts, &mut try_cursor, &containers[anc]) {
                        part_cursor = try_cursor;
                        current_ancestor_idx = containers[anc].parent_idx;
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
                if current_ancestor_idx < 0 {
                    return false;
                }
                let anc = current_ancestor_idx as usize;
                if anc >= containers.len() {
                    return false;
                }
                if !match_compound(parts, &mut part_cursor, &containers[anc]) {
                    return false;
                }
                current_ancestor_idx = containers[anc].parent_idx;
            }
            SelectorPart::Simple(_) => {
                return false;
            }
        }
    }

    true
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

        for (rule, pseudo) in parse_css_text_to_rules(&normalized) {
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
    pub fn resolve(
        &self,
        py: Python,
        containers: &PyList,
        state: Option<String>,
    ) -> PyResult<PyObject> {
        let state_str = state.as_deref().unwrap_or("normal");
        let rules = match state_str {
            "hover" => &self.hover_rules,
            "active" => &self.active_rules,
            _ => &self.normal_rules,
        };

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

        // Inheritance pass
        for idx in 0..infos.len() {
            let parent = infos[idx].parent_idx;
            if parent < 0 {
                continue;
            }
            let pidx = parent as usize;
            if pidx >= resolved.len() {
                continue;
            }
            for &prop_name in INHERITED_PROPERTIES {
                if resolved[idx].contains_key(prop_name) {
                    continue;
                }
                if let Some(parent_val) = resolved[pidx].get(prop_name).cloned() {
                    resolved[idx].insert(prop_name.to_string(), parent_val);
                }
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
        });
    }
    Ok(infos)
}
