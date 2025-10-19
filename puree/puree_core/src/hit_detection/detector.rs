use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use rayon::prelude::*;
use crate::types::{Container, MouseState, HitTestResult};

#[pyclass]
pub struct HitDetector {
    containers: Vec<Container>,
    mouse_state: MouseState,
}

#[pymethods]
impl HitDetector {
    #[new]
    pub fn new() -> Self {
        HitDetector {
            containers: Vec::new(),
            mouse_state: MouseState {
                x: 0.0,
                y: 0.0,
                clicked: false,
                scroll_delta: 0.0,
            },
        }
    }
    
    /// Load container data from Python
    pub fn load_containers(&mut self, _py: Python, container_list: &PyList) -> PyResult<()> {
        self.containers.clear();
        
        for item in container_list.iter() {
            let container_dict: &PyDict = item.downcast()?;
            let container = self.parse_container(container_dict)?;
            self.containers.push(container);
        }
        
        Ok(())
    }
    
    /// Update mouse state
    pub fn update_mouse(&mut self, x: f32, y: f32, clicked: bool, scroll_delta: f32) {
        self.mouse_state.x = x;
        self.mouse_state.y = y;
        self.mouse_state.clicked = clicked;
        self.mouse_state.scroll_delta = scroll_delta;
    }
    
    /// Perform hit detection for all containers
    pub fn detect_hits(&mut self, py: Python) -> PyResult<PyObject> {
        let results = self.process_hit_detection();
        
        // Convert results to Python list
        let py_results = PyList::empty(py);
        for result in results {
            let result_dict = PyDict::new(py);
            result_dict.set_item("container_id", result.container_id)?;
            result_dict.set_item("is_hovered", result.is_hovered)?;
            result_dict.set_item("is_clicked", result.is_clicked)?;
            result_dict.set_item("hover_changed", result.hover_changed)?;
            result_dict.set_item("click_changed", result.click_changed)?;
            result_dict.set_item("has_children_hit", result.has_children_hit)?;
            py_results.append(result_dict)?;
        }
        
        Ok(py_results.into())
    }
    
    /// Detect hover for specific container
    pub fn detect_hover(&self, container_index: usize) -> bool {
        if container_index >= self.containers.len() {
            return false;
        }
        
        let container = &self.containers[container_index];
        if container.passive {
            return false;
        }
        
        container.contains_point(self.mouse_state.x, self.mouse_state.y)
    }
    
    /// Detect if any children are hovered
    pub fn any_children_hovered(&self, container_index: usize) -> bool {
        if container_index >= self.containers.len() {
            return false;
        }
        
        let container = &self.containers[container_index];
        
        for &child_index in &container.children {
            if child_index < self.containers.len() {
                let child = &self.containers[child_index];
                if !child.passive && child.contains_point(self.mouse_state.x, self.mouse_state.y) {
                    return true;
                }
            }
        }
        
        false
    }
}

impl HitDetector {
    fn parse_container(&self, dict: &PyDict) -> PyResult<Container> {
        let id = dict.get_item("id")?.unwrap().extract::<String>()?;
        
        let pos = dict.get_item("position")?.unwrap().downcast::<PyList>()?;
        let position = [
            pos.get_item(0)?.extract::<f32>()?,
            pos.get_item(1)?.extract::<f32>()?,
        ];
        
        let sz = dict.get_item("size")?.unwrap().downcast::<PyList>()?;
        let size = [
            sz.get_item(0)?.extract::<f32>()?,
            sz.get_item(1)?.extract::<f32>()?,
        ];
        
        let parent = dict.get_item("parent")?.unwrap().extract::<i32>()?;
        let passive = dict.get_item("passive")?.unwrap().extract::<bool>()?;
        let display = dict.get_item("display")?.unwrap().extract::<bool>()?;
        let overflow = dict.get_item("overflow")?.unwrap().extract::<bool>()?;
        
        let children_list = dict.get_item("children")?.unwrap().downcast::<PyList>()?;
        let mut children = Vec::new();
        for child_item in children_list.iter() {
            children.push(child_item.extract::<usize>()?);
        }
        
        // Extract color arrays
        let color = self.extract_color_array(dict, "color")?;
        let color_1 = self.extract_color_array(dict, "color_1")?;
        let hover_color = self.extract_color_array(dict, "hover_color")?;
        let hover_color_1 = self.extract_color_array(dict, "hover_color_1")?;
        let click_color = self.extract_color_array(dict, "click_color")?;
        let click_color_1 = self.extract_color_array(dict, "click_color_1")?;
        let border_color = self.extract_color_array(dict, "border_color")?;
        let border_color_1 = self.extract_color_array(dict, "border_color_1")?;
        let text_color = self.extract_color_array(dict, "text_color")?;
        let text_color_1 = self.extract_color_array(dict, "text_color_1")?;
        let box_shadow_color = self.extract_color_array(dict, "box_shadow_color")?;
        
        let box_shadow_offset_list = dict.get_item("box_shadow_offset")?.unwrap().downcast::<PyList>()?;
        let box_shadow_offset = [
            box_shadow_offset_list.get_item(0)?.extract::<f32>()?,
            box_shadow_offset_list.get_item(1)?.extract::<f32>()?,
            box_shadow_offset_list.get_item(2)?.extract::<f32>()?,
        ];
        
        Ok(Container {
            id,
            style_id: dict.get_item("style")?.unwrap().extract::<String>()?,
            position,
            size,
            parent,
            children,
            passive,
            display,
            overflow,
            color,
            color_1,
            color_gradient_rot: dict.get_item("color_gradient_rot")?.unwrap().extract::<f32>()?,
            hover_color,
            hover_color_1,
            hover_color_gradient_rot: dict.get_item("hover_color_gradient_rot")?.unwrap().extract::<f32>()?,
            click_color,
            click_color_1,
            click_color_gradient_rot: dict.get_item("click_color_gradient_rot")?.unwrap().extract::<f32>()?,
            border_color,
            border_color_1,
            border_color_gradient_rot: dict.get_item("border_color_gradient_rot")?.unwrap().extract::<f32>()?,
            border_radius: dict.get_item("border_radius")?.unwrap().extract::<f32>()?,
            border_width: dict.get_item("border_width")?.unwrap().extract::<f32>()?,
            text: dict.get_item("text")?.unwrap().extract::<String>()?,
            font: dict.get_item("font")?.unwrap().extract::<String>()?,
            text_color,
            text_color_1,
            text_color_gradient_rot: dict.get_item("text_color_gradient_rot")?.unwrap().extract::<f32>()?,
            text_scale: dict.get_item("text_scale")?.unwrap().extract::<f32>()?,
            text_x: dict.get_item("text_x")?.unwrap().extract::<f32>()?,
            text_y: dict.get_item("text_y")?.unwrap().extract::<f32>()?,
            box_shadow_color,
            box_shadow_offset,
            box_shadow_blur: dict.get_item("box_shadow_blur")?.unwrap().extract::<f32>()?,
            img: dict.get_item("img")?.unwrap().extract::<String>()?,
            aspect_ratio: dict.get_item("aspect_ratio")?.unwrap().extract::<bool>()?,
            data: dict.get_item("data")?.unwrap().extract::<String>()?,
            scroll_value: dict.get_item("_scroll_value")?.unwrap().extract::<f32>()?,
            hovered: dict.get_item("_hovered")?.unwrap().extract::<bool>()?,
            prev_hovered: dict.get_item("_prev_hovered")?.unwrap().extract::<bool>()?,
            clicked: dict.get_item("_clicked")?.unwrap().extract::<bool>()?,
            prev_clicked: dict.get_item("_prev_clicked")?.unwrap().extract::<bool>()?,
            toggled: dict.get_item("_toggled")?.unwrap().extract::<bool>()?,
            prev_toggled: dict.get_item("_prev_toggled")?.unwrap().extract::<bool>()?,
            toggle_value: dict.get_item("_toggle_value")?.unwrap().extract::<bool>()?,
        })
    }
    
    fn extract_color_array(&self, dict: &PyDict, key: &str) -> PyResult<[f32; 4]> {
        let color_list = dict.get_item(key)?.unwrap().downcast::<PyList>()?;
        Ok([
            color_list.get_item(0)?.extract::<f32>()?,
            color_list.get_item(1)?.extract::<f32>()?,
            color_list.get_item(2)?.extract::<f32>()?,
            color_list.get_item(3)?.extract::<f32>()?,
        ])
    }
    
    fn process_hit_detection(&mut self) -> Vec<HitTestResult> {
        let mut results = Vec::new();
        
        // Use parallel processing for large container lists
        if self.containers.len() > 100 {
            results = (0..self.containers.len())
                .into_par_iter()
                .map(|i| self.process_container_hit(i))
                .collect();
        } else {
            for i in 0..self.containers.len() {
                results.push(self.process_container_hit(i));
            }
        }
        
        // Update container states
        for (i, result) in results.iter().enumerate() {
            if i < self.containers.len() {
                self.containers[i].update_hover_state(result.is_hovered);
                self.containers[i].update_click_state(result.is_clicked);
            }
        }
        
        results
    }
    
    fn process_container_hit(&self, index: usize) -> HitTestResult {
        if index >= self.containers.len() {
            return HitTestResult {
                container_id: String::new(),
                is_hovered: false,
                is_clicked: false,
                hover_changed: false,
                click_changed: false,
                has_children_hit: false,
            };
        }
        
        let container = &self.containers[index];
        
        if container.passive || !container.display {
            return HitTestResult {
                container_id: container.id.clone(),
                is_hovered: false,
                is_clicked: false,
                hover_changed: false,
                click_changed: false,
                has_children_hit: false,
            };
        }
        
        let is_in_bounds = container.contains_point(self.mouse_state.x, self.mouse_state.y);
        let has_children_hit = self.any_children_hovered(index);
        
        let is_hovered = is_in_bounds && !has_children_hit;
        let is_clicked = is_hovered && self.mouse_state.clicked;
        
        HitTestResult {
            container_id: container.id.clone(),
            is_hovered,
            is_clicked,
            hover_changed: is_hovered != container.prev_hovered,
            click_changed: is_clicked != container.prev_clicked,
            has_children_hit,
        }
    }
}

#[pyclass]
pub struct HitResult {
    #[pyo3(get)]
    pub container_id: String,
    #[pyo3(get)]
    pub is_hovered: bool,
    #[pyo3(get)]
    pub is_clicked: bool,
}
