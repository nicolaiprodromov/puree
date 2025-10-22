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
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct SpaceMapper {
    area_type_to_handler: HashMap<String, String>,
}

impl SpaceMapper {
    pub fn new() -> Self {
        let mut area_type_to_handler = HashMap::new();

        let mappings = vec![
            ("VIEW_3D", "SpaceView3D"),
            ("IMAGE_EDITOR", "SpaceImageEditor"),
            ("NODE_EDITOR", "SpaceNodeEditor"),
            ("SEQUENCE_EDITOR", "SpaceSequenceEditor"),
            ("CLIP_EDITOR", "SpaceClipEditor"),
            ("DOPESHEET_EDITOR", "SpaceDopeSheetEditor"),
            ("GRAPH_EDITOR", "SpaceGraphEditor"),
            ("NLA_EDITOR", "SpaceNLA"),
            ("TEXT_EDITOR", "SpaceTextEditor"),
            ("CONSOLE", "SpaceConsole"),
            ("INFO", "SpaceInfo"),
            ("TOPBAR", "SpaceTopBar"),
            ("STATUSBAR", "SpaceStatusBar"),
            ("OUTLINER", "SpaceOutliner"),
            ("PROPERTIES", "SpaceProperties"),
            ("FILE_BROWSER", "SpaceFileBrowser"),
            ("SPREADSHEET", "SpaceSpreadsheet"),
            ("PREFERENCES", "SpacePreferences"),
        ];

        for (area_type, handler_name) in mappings {
            area_type_to_handler.insert(area_type.to_string(), handler_name.to_string());
        }

        Self {
            area_type_to_handler,
        }
    }

    pub fn get_handler_name(&self, area_type: &str) -> Option<&str> {
        self.area_type_to_handler.get(area_type).map(|s| s.as_str())
    }

    pub fn is_valid_area_type(&self, area_type: &str) -> bool {
        self.area_type_to_handler.contains_key(area_type)
    }

    pub fn get_supported_spaces(&self) -> Vec<&str> {
        self.area_type_to_handler.keys().map(|s| s.as_str()).collect()
    }
}

impl Default for SpaceMapper {
    fn default() -> Self {
        Self::new()
    }
}