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
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Container {
    pub id      : String,
    pub style_id: String,
    pub position: [f32; 2],
    pub size    : [f32; 2],
    pub parent  : i32,
    pub children: Vec<usize>,
    pub passive : bool,
    pub display : bool,
    pub overflow: bool,
    
    pub color                    : [f32; 4],
    pub color_1                  : [f32; 4],
    pub color_gradient_rot       : f32,
    pub hover_color              : [f32; 4],
    pub hover_color_1            : [f32; 4],
    pub hover_color_gradient_rot : f32,
    pub click_color              : [f32; 4],
    pub click_color_1            : [f32; 4],
    pub click_color_gradient_rot : f32,
    pub border_color             : [f32; 4],
    pub border_color_1           : [f32; 4],
    pub border_color_gradient_rot: f32,
    pub border_radius            : f32,
    pub border_width             : f32,
    
    pub text                   : String,
    pub font                   : String,
    pub text_color             : [f32; 4],
    pub text_color_1           : [f32; 4],
    pub text_color_gradient_rot: f32,
    pub text_scale             : f32,
    pub text_x                 : f32,
    pub text_y                 : f32,
    
    pub box_shadow_color : [f32; 4],
    pub box_shadow_offset: [f32; 3],
    pub box_shadow_blur  : f32,
    
    pub img         : String,
    pub aspect_ratio: bool,
    pub data        : String,
    
    pub scroll_value: f32,
    
    pub hovered     : bool,
    pub prev_hovered: bool,
    pub clicked     : bool,
    pub prev_clicked: bool,
    pub toggled     : bool,
    pub prev_toggled: bool,
    pub toggle_value: bool,
}

#[derive(Debug, Clone, Copy)]
pub struct MouseState {
    pub x: f32,
    pub y: f32,
    pub clicked: bool,
    pub scroll_delta: f32,
}

impl Container {
    pub fn contains_point(&self, x: f32, y: f32) -> bool {
        x >= self.position[0] 
            && x <= self.position[0] + self.size[0]
            && y >= self.position[1]
            && y <= self.position[1] + self.size[1]
    }
    
    pub fn update_hover_state(&mut self, is_hovered: bool) {
        self.prev_hovered = self.hovered;
        self.hovered = is_hovered;
    }
    
    pub fn update_click_state(&mut self, is_clicked: bool) {
        self.prev_clicked = self.clicked;
        self.clicked = is_clicked;
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HitTestResult {
    pub container_id    : String,
    pub is_hovered      : bool,
    pub is_clicked      : bool,
    pub hover_changed   : bool,
    pub click_changed   : bool,
    pub has_children_hit: bool,
}
