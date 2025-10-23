// Created by XWZ
// ◕‿◕ Distributed for free at:
// https://github.com/nicolaiprodromov/puree
// ╔═════════════════════════════════╗
// ║  ██   ██  ██      ██  ████████  ║
// ║   ██ ██   ██  ██  ██       ██   ║
// ║    ███    ██  ██  ██     ██     ║
// ║   ██ ██   ██  ██  ██   ██       ║
// ║  ██   ██   ████████   ████████  ║
// ╚═════════════════════════════════╝
use serde_yaml;
use crate::space_mapper::SpaceMapper;
use pyo3::prelude::*;

#[pyclass]
#[derive(Debug, Clone)]
pub struct ConfigParser {
    space_mapper: SpaceMapper,
}

#[pymethods]
impl ConfigParser {
    #[new]
    pub fn new() -> Self {
        Self {
            space_mapper: SpaceMapper::new(),
        }
    }

    pub fn parse_yaml(&self, yaml_content: &str) -> PyResult<ConfigParseResult> {
        let parsed: serde_yaml::Value = serde_yaml::from_str(yaml_content)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("YAML parsing error: {}", e)
            ))?;

        let app_value = parsed.get("app")
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing 'app' key"))?;

        let selected_theme = app_value.get("selected_theme")
            .and_then(|v| v.as_str())
            .unwrap_or("xwz_default")
            .to_string();

        let default_theme = app_value.get("default_theme")
            .and_then(|v| v.as_str())
            .unwrap_or("xwz_default")
            .to_string();

        let themes_array = app_value.get("theme")
            .and_then(|v| v.as_sequence())
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing or invalid 'theme' array"))?;

        let mut themes = Vec::new();
        for theme_value in themes_array {
            let name = theme_value.get("name")
                .and_then(|v| v.as_str())
                .unwrap_or("unnamed")
                .to_string();

            let author = theme_value.get("author")
                .and_then(|v| v.as_str())
                .unwrap_or("unknown")
                .to_string();

            let version = theme_value.get("version")
                .and_then(|v| v.as_str())
                .unwrap_or("1.0.0")
                .to_string();

            let space = theme_value.get("space")
                .and_then(|v| v.as_str())
                .map(|s| s.to_string());

            let default_font = theme_value.get("default_font")
                .and_then(|v| v.as_str())
                .unwrap_or("NeueMontreal-Regular")
                .to_string();

            let scripts = theme_value.get("scripts")
                .and_then(|v| v.as_sequence())
                .map(|seq| seq.iter()
                    .filter_map(|v| v.as_str())
                    .map(|s| s.to_string())
                    .collect())
                .unwrap_or_default();

            let styles = theme_value.get("styles")
                .and_then(|v| v.as_sequence())
                .map(|seq| seq.iter()
                    .filter_map(|v| v.as_str())
                    .map(|s| s.to_string())
                    .collect())
                .unwrap_or_default();

            let components = theme_value.get("components")
                .and_then(|v| v.as_str())
                .unwrap_or("components/")
                .to_string();

            let theme_config = ThemeConfigData {
                name,
                author,
                version,
                space,
                default_font,
                scripts,
                styles,
                components,
            };

            themes.push(theme_config);
        }

        Ok(ConfigParseResult {
            selected_theme,
            default_theme,
            themes,
        })
    }

    pub fn validate_space(&self, space_name: Option<&str>) -> PyResult<SpaceValidationResult> {
        match space_name {
            Some(space) => {
                if self.space_mapper.is_valid_area_type(space) {
                    let handler_name = self.space_mapper.get_handler_name(space)
                        .unwrap_or("Unknown")
                        .to_string();
                    Ok(SpaceValidationResult {
                        is_valid: true,
                        area_type: Some(space.to_string()),
                        handler_name: Some(handler_name),
                        error_message: None,
                    })
                } else {
                    Ok(SpaceValidationResult {
                        is_valid: false,
                        area_type: Some(space.to_string()),
                        handler_name: None,
                        error_message: Some(format!("Invalid space type: '{}'", space)),
                    })
                }
            }
            None => Ok(SpaceValidationResult {
                is_valid: true,
                area_type: Some("VIEW_3D".to_string()),
                handler_name: Some("SpaceView3D".to_string()),
                error_message: None,
            })
        }
    }

    pub fn get_supported_spaces(&self) -> Vec<String> {
        self.space_mapper.get_supported_spaces()
            .into_iter()
            .map(|s| s.to_string())
            .collect()
    }
}

#[pyclass]
#[derive(Debug, Clone)]
pub struct ConfigParseResult {
    #[pyo3(get)]
    pub selected_theme: String,
    #[pyo3(get)]
    pub default_theme: String,
    #[pyo3(get)]
    pub themes: Vec<ThemeConfigData>,
}

#[pyclass]
#[derive(Debug, Clone)]
pub struct ThemeConfigData {
    #[pyo3(get)]
    pub name: String,
    #[pyo3(get)]
    pub author: String,
    #[pyo3(get)]
    pub version: String,
    #[pyo3(get)]
    pub space: Option<String>,
    #[pyo3(get)]
    pub default_font: String,
    #[pyo3(get)]
    pub scripts: Vec<String>,
    #[pyo3(get)]
    pub styles: Vec<String>,
    #[pyo3(get)]
    pub components: String,
}

#[pyclass]
#[derive(Debug, Clone)]
pub struct SpaceValidationResult {
    #[pyo3(get)]
    pub is_valid: bool,
    #[pyo3(get)]
    pub area_type: Option<String>,
    #[pyo3(get)]
    pub handler_name: Option<String>,
    #[pyo3(get)]
    pub error_message: Option<String>,
}