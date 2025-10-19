use pyo3::prelude::*;
use pyo3::types::PyDict;
use lightningcss::stylesheet::{StyleSheet, ParserOptions, PrinterOptions};
use std::collections::HashMap;
use regex::Regex;
use once_cell::sync::Lazy;

static VAR_PATTERN: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"var\(([^)]+)\)").unwrap()
});

#[pyclass]
pub struct CSSParser {
    styles: HashMap<String, HashMap<String, String>>,
    variables: HashMap<String, String>,
}

#[pymethods]
impl CSSParser {
    #[new]
    pub fn new() -> Self {
        CSSParser {
            styles: HashMap::new(),
            variables: HashMap::new(),
        }
    }
    
    pub fn parse(&mut self, css_string: String) -> PyResult<PyObject> {
        self.styles.clear();
        
        let parse_options = ParserOptions::default();
        
        let stylesheet = match StyleSheet::parse(&css_string, parse_options) {
            Ok(s) => s,
            Err(e) => {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("CSS parse error: {:?}", e)
                ));
            }
        };
        
        let print_options = PrinterOptions::default();
        let result = stylesheet.to_css(print_options);
        
        let css_output = match result {
            Ok(r) => r.code,
            Err(e) => {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("CSS print error: {:?}", e)
                ));
            }
        };
        
        self.parse_css_rules(&css_output);
        
        self.variables = self.extract_variables();
        
        self.resolve_all_variables();
        
        Python::with_gil(|py| {
            let result_dict = PyDict::new(py);
            
            for (selector, declarations) in &self.styles {
                let decl_dict = PyDict::new(py);
                for (prop, value) in declarations {
                    decl_dict.set_item(prop, value)?;
                }
                result_dict.set_item(selector, decl_dict)?;
            }
            
            Ok(result_dict.into())
        })
    }
    
    pub fn get_styles(&self, py: Python) -> PyResult<PyObject> {
        let result_dict = PyDict::new(py);
        
        for (selector, declarations) in &self.styles {
            let decl_dict = PyDict::new(py);
            for (prop, value) in declarations {
                decl_dict.set_item(prop, value)?;
            }
            result_dict.set_item(selector, decl_dict)?;
        }
        
        Ok(result_dict.into())
    }
    
    pub fn get_variables(&self, py: Python) -> PyResult<PyObject> {
        let result_dict = PyDict::new(py);
        
        for (var_name, var_value) in &self.variables {
            result_dict.set_item(var_name, var_value)?;
        }
        
        Ok(result_dict.into())
    }
}

impl CSSParser {
    fn parse_css_rules(&mut self, css_string: &str) {
        let mut current_selector = String::new();
        let mut in_rule = false;
        let mut buffer = String::new();
        
        for line in css_string.lines() {
            let trimmed = line.trim();
            
            if trimmed.is_empty() || trimmed.starts_with("/*") {
                continue;
            }
            
            if trimmed.contains('{') {
                let parts: Vec<&str> = trimmed.split('{').collect();
                if !parts.is_empty() {
                    current_selector = parts[0].trim().to_string();
                    in_rule = true;
                    
                    self.styles.entry(current_selector.clone())
                        .or_insert_with(HashMap::new);
                    
                    if parts.len() > 1 && !parts[1].trim().is_empty() {
                        buffer = parts[1].to_string();
                    }
                }
            } else if trimmed.contains('}') {
                if in_rule {
                    if !buffer.is_empty() {
                        self.parse_declaration(&current_selector, &buffer);
                        buffer.clear();
                    }
                    
                    let parts: Vec<&str> = trimmed.split('}').collect();
                    if !parts.is_empty() && !parts[0].trim().is_empty() {
                        self.parse_declaration(&current_selector, parts[0]);
                    }
                }
                in_rule = false;
                current_selector.clear();
            } else if in_rule {
                buffer.push_str(trimmed);
                buffer.push(' ');
                
                if trimmed.ends_with(';') {
                    self.parse_declaration(&current_selector, &buffer);
                    buffer.clear();
                }
            }
        }
    }
    
    fn parse_declaration(&mut self, selector: &str, declaration: &str) {
        let parts: Vec<&str> = declaration.split(':').collect();
        if parts.len() >= 2 {
            let prop = parts[0].trim().to_string();
            let value = parts[1..].join(":").trim().trim_end_matches(';').to_string();
            
            if let Some(styles) = self.styles.get_mut(selector) {
                styles.insert(prop, value);
            }
        }
    }
    
    fn extract_variables(&self) -> HashMap<String, String> {
        let mut variables = HashMap::new();
        
        for declarations in self.styles.values() {
            for (prop, value) in declarations {
                if prop.starts_with("--") {
                    variables.insert(prop.clone(), value.clone());
                }
            }
        }
        
        variables
    }
    
    fn resolve_all_variables(&mut self) {
        let variables = self.variables.clone();
        
        let mut updated_values = Vec::new();
        
        for (selector, declarations) in self.styles.iter() {
            for (prop, value) in declarations.iter() {
                if !prop.starts_with("--") {
                    let resolved = Self::resolve_variables_static(value, &variables);
                    if &resolved != value {
                        updated_values.push((selector.clone(), prop.clone(), resolved));
                    }
                }
            }
        }
        
        for (selector, prop, value) in updated_values {
            if let Some(declarations) = self.styles.get_mut(&selector) {
                declarations.insert(prop, value);
            }
        }
    }
    
    fn resolve_variables_static(value: &str, variables: &HashMap<String, String>) -> String {
        let mut result = value.to_string();
        let mut visited = std::collections::HashSet::new();
        
        loop {
            let mut changed = false;
            let temp_result = result.clone();
            
            for cap in VAR_PATTERN.captures_iter(&temp_result) {
                if let Some(var_match) = cap.get(1) {
                    let var_name = var_match.as_str().trim();
                    
                    if visited.contains(var_name) {
                        continue;
                    }
                    
                    if let Some(var_value) = variables.get(var_name) {
                        visited.insert(var_name.to_string());
                        result = result.replace(&format!("var({})", var_name), var_value);
                        changed = true;
                    }
                }
            }
            
            if !changed {
                break;
            }
        }
        
        result.split_whitespace().collect::<Vec<_>>().join(" ")
    }
}
