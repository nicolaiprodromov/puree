use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use crate::types::Container;

#[pyclass]
pub struct ContainerProcessor {
    containers: Vec<Container>,
}

#[pymethods]
impl ContainerProcessor {
    #[new]
    pub fn new() -> Self {
        ContainerProcessor {
            containers: Vec::new(),
        }
    }
    
    /// Fast flattening of container hierarchy
    pub fn flatten_tree(&mut self, py: Python, root: &PyDict) -> PyResult<PyObject> {
        self.containers.clear();
        
        // Recursively flatten the tree
        self.flatten_recursive(root)?;
        
        // Convert to Python list
        let result = PyList::empty(py);
        for container in &self.containers {
            let dict = self.container_to_dict(py, container)?;
            result.append(dict)?;
        }
        
        Ok(result.into())
    }
    
    /// Update container positions in bulk
    pub fn update_positions_bulk(
        &mut self,
        py: Python,
        container_indices: &PyList,
        x_offsets: &PyList,
        y_offsets: &PyList,
    ) -> PyResult<()> {
        let len = container_indices.len();
        
        for i in 0..len {
            let index = container_indices.get_item(i)?.extract::<usize>()?;
            let x_offset = x_offsets.get_item(i)?.extract::<f32>()?;
            let y_offset = y_offsets.get_item(i)?.extract::<f32>()?;
            
            if index < self.containers.len() {
                self.containers[index].position[0] += x_offset;
                self.containers[index].position[1] += y_offset;
            }
        }
        
        Ok(())
    }
    
    /// Get containers as Python list
    pub fn get_containers(&self, py: Python) -> PyResult<PyObject> {
        let result = PyList::empty(py);
        
        for container in &self.containers {
            let dict = self.container_to_dict(py, container)?;
            result.append(dict)?;
        }
        
        Ok(result.into())
    }
    
    /// Batch update container states
    pub fn update_states_bulk(
        &mut self,
        container_ids: Vec<String>,
        hovered: Vec<bool>,
        clicked: Vec<bool>,
    ) -> PyResult<()> {
        for (i, id) in container_ids.iter().enumerate() {
            if let Some(container) = self.containers.iter_mut().find(|c| c.id == *id) {
                container.prev_hovered = container.hovered;
                container.prev_clicked = container.clicked;
                
                if i < hovered.len() {
                    container.hovered = hovered[i];
                }
                if i < clicked.len() {
                    container.clicked = clicked[i];
                }
            }
        }
        
        Ok(())
    }
}

impl ContainerProcessor {
    fn flatten_recursive(&mut self, container_dict: &PyDict) -> PyResult<()> {
        // This would implement the actual flattening logic
        // similar to what's in parser.py flatten_node_tree
        Ok(())
    }
    
    fn container_to_dict(&self, py: Python, container: &Container) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        
        dict.set_item("id", &container.id)?;
        
        let pos = PyList::new(py, &[container.position[0], container.position[1]]);
        dict.set_item("position", pos)?;
        
        let size = PyList::new(py, &[container.size[0], container.size[1]]);
        dict.set_item("size", size)?;
        
        dict.set_item("parent", container.parent)?;
        
        let children = PyList::new(py, &container.children);
        dict.set_item("children", children)?;
        
        dict.set_item("passive", container.passive)?;
        dict.set_item("display", container.display)?;
        dict.set_item("overflow", container.overflow)?;
        
        // Add all other properties...
        let color = PyList::new(py, &container.color);
        dict.set_item("color", color)?;
        
        let color_1 = PyList::new(py, &container.color_1);
        dict.set_item("color_1", color_1)?;
        
        dict.set_item("color_gradient_rot", container.color_gradient_rot)?;
        
        // ... (add remaining properties)
        
        dict.set_item("_hovered", container.hovered)?;
        dict.set_item("_prev_hovered", container.prev_hovered)?;
        dict.set_item("_clicked", container.clicked)?;
        dict.set_item("_prev_clicked", container.prev_clicked)?;
        dict.set_item("_toggled", container.toggled)?;
        dict.set_item("_prev_toggled", container.prev_toggled)?;
        dict.set_item("_toggle_value", container.toggle_value)?;
        dict.set_item("_scroll_value", container.scroll_value)?;
        
        Ok(dict.into())
    }
}
