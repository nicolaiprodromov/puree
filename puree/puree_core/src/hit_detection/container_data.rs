use crate::types::Container;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::collections::HashMap;

struct ContainerWithHandlers {
    container: Container,
    click_handlers: PyObject,
    toggle_handlers: PyObject,
    scroll_handlers: PyObject,
    hover_handlers: PyObject,
    hoverout_handlers: PyObject,
}

#[pyclass]
pub struct ContainerProcessor {
    containers: Vec<ContainerWithHandlers>,
    id_to_index: HashMap<String, usize>,
}

impl Default for ContainerProcessor {
    fn default() -> Self {
        Self::new()
    }
}

#[pymethods]
impl ContainerProcessor {
    #[new]
    pub fn new() -> Self {
        ContainerProcessor {
            containers: Vec::new(),
            id_to_index: HashMap::new(),
        }
    }

    pub fn flatten_tree(
        &mut self,
        py: Python,
        root_container: &PyDict,
        node_flat_abs: &PyDict,
    ) -> PyResult<PyObject> {
        self.containers.clear();
        self.id_to_index.clear();

        self.build_id_mapping(root_container)?;

        self.flatten_recursive(py, root_container, node_flat_abs, -1)?;

        let result = PyList::empty(py);
        for container in &self.containers {
            let dict = self.container_to_dict(py, container)?;
            result.append(dict)?;
        }

        Ok(result.into())
    }

    pub fn update_positions_bulk(
        &mut self,
        _py: Python,
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
                self.containers[index].container.position[0] += x_offset;
                self.containers[index].container.position[1] += y_offset;
            }
        }

        Ok(())
    }

    pub fn get_containers(&self, py: Python) -> PyResult<PyObject> {
        let result = PyList::empty(py);

        for container in &self.containers {
            let dict = self.container_to_dict(py, container)?;
            result.append(dict)?;
        }

        Ok(result.into())
    }

    pub fn update_states_bulk(
        &mut self,
        container_ids: Vec<String>,
        hovered: Vec<bool>,
        clicked: Vec<bool>,
    ) -> PyResult<()> {
        for (i, id) in container_ids.iter().enumerate() {
            if let Some(container_with_handlers) =
                self.containers.iter_mut().find(|c| c.container.id == *id)
            {
                let container = &mut container_with_handlers.container;
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
    fn build_id_mapping(&mut self, container_dict: &PyDict) -> PyResult<()> {
        let id = container_dict
            .get_item("id")?
            .unwrap()
            .extract::<String>()?;
        self.id_to_index.insert(id, self.id_to_index.len());

        if let Some(children_item) = container_dict.get_item("children")? {
            let children_list: &PyList = children_item.downcast()?;
            for child_item in children_list.iter() {
                let child_dict: &PyDict = child_item.downcast()?;
                self.build_id_mapping(child_dict)?;
            }
        }

        Ok(())
    }

    fn flatten_recursive(
        &mut self,
        py: Python,
        container_dict: &PyDict,
        node_flat_abs: &PyDict,
        parent_index: i32,
    ) -> PyResult<()> {
        let id = container_dict
            .get_item("id")?
            .unwrap()
            .extract::<String>()?;

        if let Some(node_item) = node_flat_abs.get_item(&id)? {
            let node_dict: &PyDict = node_item.downcast()?;

            let x = node_dict.get_item("x")?.unwrap().extract::<f32>()?;
            let y = node_dict.get_item("y")?.unwrap().extract::<f32>()?;
            let width = node_dict.get_item("width")?.unwrap().extract::<f32>()?;
            let height = node_dict.get_item("height")?.unwrap().extract::<f32>()?;

            let style_dict: &PyDict = container_dict.get_item("style")?.unwrap().downcast()?;
            let style_id = style_dict.get_item("id")?.unwrap().extract::<String>()?;

            let display_str = style_dict
                .get_item("display")?
                .unwrap()
                .extract::<String>()?;
            let display = display_str != "NONE";

            let overflow_str = style_dict
                .get_item("overflow")?
                .unwrap()
                .extract::<String>()?;
            let overflow = overflow_str != "HIDDEN";

            let data = container_dict
                .get_item("data")?
                .unwrap()
                .extract::<String>()?;
            let img = container_dict
                .get_item("img")?
                .unwrap()
                .extract::<String>()?;
            let aspect_ratio = style_dict
                .get_item("aspect_ratio")?
                .unwrap()
                .extract::<bool>()?;
            let text = container_dict
                .get_item("text")?
                .unwrap()
                .extract::<String>()?;
            let font = container_dict
                .get_item("font")?
                .unwrap()
                .extract::<String>()?;
            let passive = container_dict
                .get_item("passive")?
                .unwrap()
                .extract::<bool>()?;

            let click_handlers = container_dict.get_item("click")?.unwrap().to_object(py);
            let toggle_handlers = container_dict.get_item("toggle")?.unwrap().to_object(py);
            let scroll_handlers = container_dict.get_item("scroll")?.unwrap().to_object(py);
            let scroll_value = container_dict
                .get_item("_scroll_value")?
                .unwrap()
                .extract::<f32>()?;
            let hover_handlers = container_dict.get_item("hover")?.unwrap().to_object(py);
            let hoverout_handlers = container_dict.get_item("hoverout")?.unwrap().to_object(py);

            let children_indices =
                if let Some(children_item) = container_dict.get_item("children")? {
                    let children_list: &PyList = children_item.downcast()?;
                    let mut indices = Vec::new();
                    for child_item in children_list.iter() {
                        let child_dict: &PyDict = child_item.downcast()?;
                        let child_id = child_dict.get_item("id")?.unwrap().extract::<String>()?;
                        if let Some(&child_index) = self.id_to_index.get(&child_id) {
                            indices.push(child_index);
                        }
                    }
                    indices
                } else {
                    Vec::new()
                };

            let container = Container {
                id: id.clone(),
                style_id,
                display,
                overflow,
                data,
                img,
                aspect_ratio,
                text,
                font,
                position: [x, y],
                size: [width, height],
                background_color: self.extract_color_array(style_dict, "background_color")?,
                background_color_2: self.extract_color_array(style_dict, "background_color_2")?,
                background_gradient_rot: style_dict
                    .get_item("background_gradient_rot")?
                    .unwrap()
                    .extract::<f32>()?,
                hover_background_color: self
                    .extract_color_array(style_dict, "hover_background_color")?,
                hover_background_color_2: self
                    .extract_color_array(style_dict, "hover_background_color_2")?,
                hover_background_gradient_rot: style_dict
                    .get_item("hover_background_gradient_rot")?
                    .unwrap()
                    .extract::<f32>()?,
                click_background_color: self
                    .extract_color_array(style_dict, "click_background_color")?,
                click_background_color_2: self
                    .extract_color_array(style_dict, "click_background_color_2")?,
                click_background_gradient_rot: style_dict
                    .get_item("click_background_gradient_rot")?
                    .unwrap()
                    .extract::<f32>()?,
                border_color: self.extract_color_array(style_dict, "border_color")?,
                border_color_2: self.extract_color_array(style_dict, "border_color_2")?,
                border_gradient_rot: style_dict
                    .get_item("border_gradient_rot")?
                    .unwrap()
                    .extract::<f32>()?,
                border_radius: style_dict
                    .get_item("border_radius")?
                    .unwrap()
                    .extract::<f32>()?,
                border_radius_tl: style_dict
                    .get_item("border_radius_tl")?
                    .unwrap()
                    .extract::<f32>()?,
                border_radius_tr: style_dict
                    .get_item("border_radius_tr")?
                    .unwrap()
                    .extract::<f32>()?,
                border_radius_br: style_dict
                    .get_item("border_radius_br")?
                    .unwrap()
                    .extract::<f32>()?,
                border_radius_bl: style_dict
                    .get_item("border_radius_bl")?
                    .unwrap()
                    .extract::<f32>()?,
                border_width: style_dict
                    .get_item("border_width")?
                    .unwrap()
                    .extract::<f32>()?,
                border_width_top: style_dict
                    .get_item("border_width_top")
                    .ok()
                    .and_then(|v| v.and_then(|v| v.extract::<f32>().ok()))
                    .unwrap_or(0.0),
                border_width_right: style_dict
                    .get_item("border_width_right")
                    .ok()
                    .and_then(|v| v.and_then(|v| v.extract::<f32>().ok()))
                    .unwrap_or(0.0),
                border_width_bottom: style_dict
                    .get_item("border_width_bottom")
                    .ok()
                    .and_then(|v| v.and_then(|v| v.extract::<f32>().ok()))
                    .unwrap_or(0.0),
                border_width_left: style_dict
                    .get_item("border_width_left")
                    .ok()
                    .and_then(|v| v.and_then(|v| v.extract::<f32>().ok()))
                    .unwrap_or(0.0),
                gradient_stops: style_dict
                    .get_item("gradient_stops")
                    .ok()
                    .and_then(|v| v.and_then(|v| v.extract::<String>().ok()))
                    .unwrap_or_default(),
                color: self.extract_color_array(style_dict, "color")?,
                font_size: style_dict
                    .get_item("font_size")?
                    .unwrap()
                    .extract::<f32>()?,
                text_x: style_dict.get_item("text_x")?.unwrap().extract::<f32>()?,
                text_y: style_dict.get_item("text_y")?.unwrap().extract::<f32>()?,
                box_shadow_color: self.extract_color_array(style_dict, "box_shadow_color")?,
                box_shadow_offset: self.extract_vec3_array(style_dict, "box_shadow_offset")?,
                box_shadow_blur: style_dict
                    .get_item("box_shadow_blur")?
                    .unwrap()
                    .extract::<f32>()?,
                parent: parent_index,
                passive,
                children: children_indices.clone(),
                scroll_value,
                hovered: false,
                prev_hovered: false,
                clicked: false,
                prev_clicked: false,
                toggled: false,
                prev_toggled: false,
                toggle_value: false,
            };

            let container_with_handlers = ContainerWithHandlers {
                container,
                click_handlers,
                toggle_handlers,
                scroll_handlers,
                hover_handlers,
                hoverout_handlers,
            };

            let current_index = self.containers.len() as i32;
            self.containers.push(container_with_handlers);

            if let Some(children_item) = container_dict.get_item("children")? {
                let children_list: &PyList = children_item.downcast()?;
                for child_item in children_list.iter() {
                    let child_dict: &PyDict = child_item.downcast()?;
                    self.flatten_recursive(py, child_dict, node_flat_abs, current_index)?;
                }
            }
        }

        Ok(())
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

    fn extract_vec3_array(&self, dict: &PyDict, key: &str) -> PyResult<[f32; 3]> {
        let vec_list = dict.get_item(key)?.unwrap().downcast::<PyList>()?;
        Ok([
            vec_list.get_item(0)?.extract::<f32>()?,
            vec_list.get_item(1)?.extract::<f32>()?,
            vec_list.get_item(2)?.extract::<f32>()?,
        ])
    }

    fn container_to_dict(
        &self,
        py: Python,
        container_with_handlers: &ContainerWithHandlers,
    ) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        let container = &container_with_handlers.container;

        dict.set_item("id", &container.id)?;
        dict.set_item("style", &container.style_id)?;
        dict.set_item("display", container.display)?;
        dict.set_item("overflow", container.overflow)?;
        dict.set_item("data", &container.data)?;
        dict.set_item("img", &container.img)?;
        dict.set_item("aspect_ratio", container.aspect_ratio)?;
        dict.set_item("text", &container.text)?;
        dict.set_item("font", &container.font)?;

        let pos = PyList::new(py, [container.position[0], container.position[1]]);
        dict.set_item("position", pos)?;

        let size = PyList::new(py, [container.size[0], container.size[1]]);
        dict.set_item("size", size)?;

        let background_color = PyList::new(py, container.background_color);
        dict.set_item("background_color", background_color)?;

        let background_color_2 = PyList::new(py, container.background_color_2);
        dict.set_item("background_color_2", background_color_2)?;

        dict.set_item("background_gradient_rot", container.background_gradient_rot)?;

        let hover_background_color = PyList::new(py, container.hover_background_color);
        dict.set_item("hover_background_color", hover_background_color)?;

        let hover_background_color_2 = PyList::new(py, container.hover_background_color_2);
        dict.set_item("hover_background_color_2", hover_background_color_2)?;

        dict.set_item(
            "hover_background_gradient_rot",
            container.hover_background_gradient_rot,
        )?;

        let click_background_color = PyList::new(py, container.click_background_color);
        dict.set_item("click_background_color", click_background_color)?;

        let click_background_color_2 = PyList::new(py, container.click_background_color_2);
        dict.set_item("click_background_color_2", click_background_color_2)?;

        dict.set_item(
            "click_background_gradient_rot",
            container.click_background_gradient_rot,
        )?;

        let border_color = PyList::new(py, container.border_color);
        dict.set_item("border_color", border_color)?;

        let border_color_2 = PyList::new(py, container.border_color_2);
        dict.set_item("border_color_2", border_color_2)?;

        dict.set_item("border_gradient_rot", container.border_gradient_rot)?;
        dict.set_item("border_radius", container.border_radius)?;
        dict.set_item("border_radius_tl", container.border_radius_tl)?;
        dict.set_item("border_radius_tr", container.border_radius_tr)?;
        dict.set_item("border_radius_br", container.border_radius_br)?;
        dict.set_item("border_radius_bl", container.border_radius_bl)?;
        dict.set_item("border_width", container.border_width)?;
        dict.set_item("border_width_top", container.border_width_top)?;
        dict.set_item("border_width_right", container.border_width_right)?;
        dict.set_item("border_width_bottom", container.border_width_bottom)?;
        dict.set_item("border_width_left", container.border_width_left)?;
        dict.set_item("gradient_stops", &container.gradient_stops)?;

        let color = PyList::new(py, container.color);
        dict.set_item("color", color)?;

        dict.set_item("font_size", container.font_size)?;
        dict.set_item("text_x", container.text_x)?;
        dict.set_item("text_y", container.text_y)?;

        let box_shadow_color = PyList::new(py, container.box_shadow_color);
        dict.set_item("box_shadow_color", box_shadow_color)?;

        let box_shadow_offset = PyList::new(py, container.box_shadow_offset);
        dict.set_item("box_shadow_offset", box_shadow_offset)?;

        dict.set_item("box_shadow_blur", container.box_shadow_blur)?;

        dict.set_item("parent", container.parent)?;
        dict.set_item("passive", container.passive)?;

        let children = PyList::new(py, &container.children);
        dict.set_item("children", children)?;

        dict.set_item("click", &container_with_handlers.click_handlers)?;
        dict.set_item("toggle", &container_with_handlers.toggle_handlers)?;
        dict.set_item("scroll", &container_with_handlers.scroll_handlers)?;
        dict.set_item("_scroll_value", container.scroll_value)?;
        dict.set_item("hover", &container_with_handlers.hover_handlers)?;
        dict.set_item("hoverout", &container_with_handlers.hoverout_handlers)?;

        dict.set_item("_clicked", container.clicked)?;
        dict.set_item("_prev_clicked", container.prev_clicked)?;
        dict.set_item("_toggle_value", container.toggle_value)?;
        dict.set_item("_toggled", container.toggled)?;
        dict.set_item("_prev_toggled", container.prev_toggled)?;
        dict.set_item("_hovered", container.hovered)?;
        dict.set_item("_prev_hovered", container.prev_hovered)?;

        Ok(dict.into())
    }
}
