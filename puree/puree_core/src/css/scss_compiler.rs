use pyo3::prelude::*;
use pyo3::types::PyDict;

#[pyclass]
pub struct SCSSCompiler;

#[pymethods]
impl SCSSCompiler {
    #[new]
    pub fn new() -> PyResult<Self> {
        Ok(SCSSCompiler)
    }
    
    pub fn compile(
        &self,
        scss_content: String,
        namespace: Option<String>,
        param_overrides: Option<&PyDict>,
        component_name: Option<String>,
    ) -> PyResult<String> {
        let mut final_scss = scss_content.clone();
        
        if let Some(overrides) = param_overrides {
            let mut var_defs = Vec::new();
            
            for (key, value) in overrides.iter() {
                let key_str = key.extract::<String>()?;
                let value_str = value.extract::<String>()?;
                
                let var_name = key_str.replace("-", "_");
                let processed_value = self.process_param_value(&value_str);
                
                var_defs.push(format!("${}: {};", var_name, processed_value));
            }
            
            if !var_defs.is_empty() {
                final_scss = format!("{}\n{}", var_defs.join("\n"), final_scss);
            }
        }
        
        let compiled_css = grass::from_string(
            final_scss,
            &grass::Options::default()
        ).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("SCSS compilation error: {}", e)
            )
        })?;
        
        let result = if let Some(ns) = namespace {
            let comp_name = component_name.unwrap_or_else(|| {
                if ns.contains('_') {
                    ns.split('_').last().unwrap_or(&ns).to_string()
                } else {
                    ns.clone()
                }
            });
            
            self.apply_namespace(&compiled_css, &ns, &comp_name)
        } else {
            compiled_css
        };
        
        Ok(result)
    }
    
    pub fn compile_file(
        &self,
        filepath: String,
        namespace: Option<String>,
        param_overrides: Option<&PyDict>,
        component_name: Option<String>,
    ) -> PyResult<String> {
        let scss_content = std::fs::read_to_string(&filepath)
            .map_err(|e| {
                PyErr::new::<pyo3::exceptions::PyIOError, _>(
                    format!("Failed to read SCSS file {}: {}", filepath, e)
                )
            })?;
        
        self.compile(scss_content, namespace, param_overrides, component_name)
    }
}

impl SCSSCompiler {
    fn process_param_value(&self, value: &str) -> String {
        if value.starts_with("rgb(") 
            || value.starts_with("rgba(") 
            || value.starts_with('#')
            || value.starts_with('"')
            || value.starts_with('\'') {
            return value.to_string();
        }
        
        let parts: Vec<&str> = value.split_whitespace().collect();
        
        if parts.len() > 1 {
            let is_css_multi = parts.iter().all(|part| {
                let stripped = part.trim_end_matches(|c: char| {
                    matches!(c, 'p' | 'x' | '%' | 'e' | 'm' | 'r' | 'v' | 'w' | 'h' | 't' | 'c' | 'i' | 'n')
                });
                
                stripped.chars().all(|c| c.is_numeric() || c == '.' || c == '-')
                    || matches!(*part, "auto" | "inherit" | "initial" | "unset")
            });
            
            if is_css_multi {
                return value.to_string();
            } else {
                return format!("\"{}\"", value);
            }
        }
        
        let stripped = value.trim_end_matches(|c: char| {
            matches!(c, 'p' | 'x' | '%' | 'e' | 'm' | 'r' | 'v' | 'w' | 'h' | 't' | 'c' | 'i' | 'n')
        });
        
        if stripped.parse::<f64>().is_ok() {
            value.to_string()
        } else {
            format!("\"{}\"", value)
        }
    }
    
    fn apply_namespace(&self, css: &str, namespace: &str, component_base_name: &str) -> String {
        let mut lines = Vec::new();
        
        for line in css.lines() {
            let trimmed = line.trim();
            
            if trimmed.is_empty() 
                || trimmed.starts_with('@') 
                || trimmed.starts_with("/*") 
                || trimmed == "}" {
                lines.push(line.to_string());
                continue;
            }
            
            if trimmed.contains('{') {
                let parts: Vec<&str> = trimmed.split('{').collect();
                let selector_part = parts[0].trim();
                let selectors: Vec<&str> = selector_part.split(',').collect();
                
                let mut namespaced_selectors = Vec::new();
                
                for selector in selectors {
                    let selector = selector.trim();
                    if !selector.is_empty() {
                        let selector_clean = selector.trim_start_matches('.');
                        
                        let namespaced = if selector_clean == component_base_name {
                            namespace.to_string()
                        } else if selector_clean.starts_with(&format!("{}_", component_base_name)) {
                            selector_clean.replacen(component_base_name, namespace, 1)
                        } else if !selector_clean.starts_with(namespace) {
                            format!("{}_{}", namespace, selector_clean)
                        } else {
                            selector_clean.to_string()
                        };
                        
                        namespaced_selectors.push(namespaced);
                    }
                }
                
                let rest = if parts.len() > 1 {
                    format!(" {{{}", parts[1..].join("{"))
                } else {
                    " {".to_string()
                };
                
                lines.push(format!("{}{}", namespaced_selectors.join(", "), rest));
            } else {
                lines.push(line.to_string());
            }
        }
        
        lines.join("\n")
    }
}
