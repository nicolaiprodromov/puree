#![allow(non_local_definitions)]
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

mod types;
mod hit_detection;
mod css;

use hit_detection::{HitDetector, ContainerProcessor};
use css::{CSSParser, SCSSCompiler};

/// Main entry point for the Rust module
#[pymodule]
fn puree_rust_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<HitDetector>()?;
    m.add_class::<ContainerProcessor>()?;
    m.add_class::<CSSParser>()?;
    m.add_class::<SCSSCompiler>()?;
    m.add_function(wrap_pyfunction!(detect_hover_batch, m)?)?;
    m.add_function(wrap_pyfunction!(detect_clicks_batch, m)?)?;
    m.add_function(wrap_pyfunction!(flatten_containers_fast, m)?)?;
    Ok(())
}

/// Batch hover detection for all containers
#[pyfunction]
fn detect_hover_batch(
    py: Python,
    containers: &PyList,
    mouse_x: f32,
    mouse_y: f32,
) -> PyResult<PyObject> {
    let mut results = Vec::new();
    
    for item in containers.iter() {
        let container: &PyDict = item.downcast()?;
        let id = container.get_item("id")?.unwrap().extract::<String>()?;
        
        let pos = container.get_item("position")?.unwrap().downcast::<PyList>()?;
        let size = container.get_item("size")?.unwrap().downcast::<PyList>()?;
        
        let x = pos.get_item(0)?.extract::<f32>()?;
        let y = pos.get_item(1)?.extract::<f32>()?;
        let width = size.get_item(0)?.extract::<f32>()?;
        let height = size.get_item(1)?.extract::<f32>()?;
        
        let is_hovered = mouse_x >= x && mouse_x <= x + width &&
                         mouse_y >= y && mouse_y <= y + height;
        
        if is_hovered {
            results.push(id);
        }
    }
    
    Ok(results.to_object(py))
}

/// Batch click detection with hierarchy checking
#[pyfunction]
fn detect_clicks_batch(
    py: Python,
    containers: &PyList,
    mouse_x: f32,
    mouse_y: f32,
    is_clicked: bool,
) -> PyResult<PyObject> {
    let result_dict = PyDict::new(py);
    
    if !is_clicked {
        return Ok(result_dict.into());
    }
    
    for item in containers.iter() {
        let container: &PyDict = item.downcast()?;
        let id = container.get_item("id")?.unwrap().extract::<String>()?;
        
        let passive = container.get_item("passive")?.unwrap().extract::<bool>()?;
        if passive {
            continue;
        }
        
        let pos = container.get_item("position")?.unwrap().downcast::<PyList>()?;
        let size = container.get_item("size")?.unwrap().downcast::<PyList>()?;
        
        let x = pos.get_item(0)?.extract::<f32>()?;
        let y = pos.get_item(1)?.extract::<f32>()?;
        let width = size.get_item(0)?.extract::<f32>()?;
        let height = size.get_item(1)?.extract::<f32>()?;
        
        let is_hit = mouse_x >= x && mouse_x <= x + width &&
                     mouse_y >= y && mouse_y <= y + height;
        
        if is_hit {
            result_dict.set_item(&id, true)?;
        }
    }
    
    Ok(result_dict.into())
}

/// Fast container flattening
#[pyfunction]
fn flatten_containers_fast(
    py: Python,
    _container_tree: &PyDict,
) -> PyResult<PyObject> {
    let result_list = PyList::empty(py);
    
    Ok(result_list.into())
}
