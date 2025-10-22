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
use notify::{Watcher, RecursiveMode, Result as NotifyResult, Event, EventKind};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use std::collections::{HashMap, HashSet};
use std::time::{SystemTime, Duration, Instant};
use crossbeam_channel::{unbounded, Receiver, Sender};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

/// Represents the type of file change detected
#[derive(Debug, Clone, PartialEq)]
pub enum ChangeType {
    YamlModified,
    StyleModified,
    ScriptModified,
    ComponentAdded,
    ComponentRemoved,
    AssetModified,
}

/// Represents a file change event with metadata
#[derive(Debug, Clone)]
pub struct FileChange {
    pub path: PathBuf,
    pub change_type: ChangeType,
    pub timestamp: SystemTime,
}

/// Configuration for the file watcher
#[derive(Debug, Clone)]
pub struct WatcherConfig {
    pub debounce_ms: u64,
    pub watch_yaml: bool,
    pub watch_styles: bool,
    pub watch_scripts: bool,
    pub watch_components: bool,
    pub watch_assets: bool,
}

impl Default for WatcherConfig {
    fn default() -> Self {
        Self {
            debounce_ms: 300,
            watch_yaml: true,
            watch_styles: true,
            watch_scripts: true,
            watch_components: true,
            watch_assets: true,
        }
    }
}

pub struct FileWatcher {
    watcher: Option<Box<dyn Watcher + Send>>,
    config: WatcherConfig,
    watched_paths: HashSet<PathBuf>,
    event_sender: Sender<FileChange>,
    event_receiver: Receiver<FileChange>,
    last_events: Arc<Mutex<HashMap<PathBuf, Instant>>>,
}

impl FileWatcher {
    pub fn new(config: WatcherConfig) -> Self {
        let (tx, rx) = unbounded();
        
        Self {
            watcher: None,
            config,
            watched_paths: HashSet::new(),
            event_sender: tx,
            event_receiver: rx,
            last_events: Arc::new(Mutex::new(HashMap::new())),
        }
    }
    
    /// Start watching a directory path
    pub fn watch_path(&mut self, path: impl AsRef<Path>) -> NotifyResult<()> {
        let path = path.as_ref().to_path_buf();
        
        if self.watched_paths.contains(&path) {
            return Ok(());
        }
        
        if self.watcher.is_none() {
            let tx = self.event_sender.clone();
            let last_events = Arc::clone(&self.last_events);
            let debounce_duration = Duration::from_millis(self.config.debounce_ms);
            let config = self.config.clone();
            
            let watcher = notify::recommended_watcher(move |res: NotifyResult<Event>| {
                if let Ok(event) = res {
                    Self::handle_event(event, &tx, &last_events, debounce_duration, &config);
                }
            })?;
            
            self.watcher = Some(Box::new(watcher));
        }
        
        if let Some(watcher) = &mut self.watcher {
            watcher.watch(&path, RecursiveMode::Recursive)?;
            self.watched_paths.insert(path);
        }
        
        Ok(())
    }
    
    /// Stop watching a directory path
    pub fn unwatch_path(&mut self, path: impl AsRef<Path>) -> NotifyResult<()> {
        let path = path.as_ref().to_path_buf();
        
        if let Some(watcher) = &mut self.watcher {
            watcher.unwatch(&path)?;
            self.watched_paths.remove(&path);
        }
        
        Ok(())
    }
    
    pub fn process_events(&self) -> Vec<FileChange> {
        let mut processed_changes = Vec::new();
        
        while let Ok(change) = self.event_receiver.try_recv() {
            processed_changes.push(change);
        }
        
        processed_changes
    }
    
    /// Internal event handler with debouncing
    fn handle_event(
        event: Event,
        sender: &Sender<FileChange>,
        last_events: &Arc<Mutex<HashMap<PathBuf, Instant>>>,
        debounce_duration: Duration,
        config: &WatcherConfig,
    ) {
        let now = Instant::now();
        
        for path in event.paths {
            if !path.is_file() {
                continue;
            }
            
            {
                let mut last_events_map = last_events.lock().unwrap();
                if let Some(last_time) = last_events_map.get(&path) {
                    if now.duration_since(*last_time) < debounce_duration {
                        continue;
                    }
                }
                last_events_map.insert(path.clone(), now);
            }
            
            let change_type = Self::classify_change(&path, &event.kind, config);
            
            if let Some(change_type) = change_type {
                let change = FileChange {
                    path: path.clone(),
                    change_type,
                    timestamp: SystemTime::now(),
                };
                
                let _ = sender.send(change);
            }
        }
    }
    
    /// Classify a file change based on path and event kind
    fn classify_change(path: &Path, kind: &EventKind, config: &WatcherConfig) -> Option<ChangeType> {
        let extension = path.extension()?.to_str()?;
        
        match kind {
            EventKind::Modify(_) | EventKind::Create(_) => {
                match extension {
                    "yaml" | "yml" if config.watch_yaml => {
                        if Self::is_component_path(path) && matches!(kind, EventKind::Create(_)) {
                            Some(ChangeType::ComponentAdded)
                        } else {
                            Some(ChangeType::YamlModified)
                        }
                    }
                    "css" | "scss" if config.watch_styles => Some(ChangeType::StyleModified),
                    "py" if config.watch_scripts => Some(ChangeType::ScriptModified),
                    "png" | "jpg" | "jpeg" | "svg" if config.watch_assets => Some(ChangeType::AssetModified),
                    _ => None,
                }
            }
            EventKind::Remove(_) => {
                if config.watch_components && Self::is_component_path(path) {
                    Some(ChangeType::ComponentRemoved)
                } else {
                    None
                }
            }
            _ => None,
        }
    }
    
    /// Check if a path belongs to a component directory
    fn is_component_path(path: &Path) -> bool {
        path.components().any(|c| {
            c.as_os_str().to_str().map_or(false, |s| s == "components")
        })
    }
}

/// Python binding for FileWatcher
#[pyclass]
pub struct PyFileWatcher {
    watcher: Arc<Mutex<FileWatcher>>,
    pending_changes: Arc<Mutex<Vec<FileChange>>>,
}

#[pymethods]
impl PyFileWatcher {
    #[new]
    pub fn new(
        debounce_ms: Option<u64>,
        watch_yaml: Option<bool>,
        watch_styles: Option<bool>,
        watch_scripts: Option<bool>,
    ) -> PyResult<Self> {
        let config = WatcherConfig {
            debounce_ms: debounce_ms.unwrap_or(300),
            watch_yaml: watch_yaml.unwrap_or(true),
            watch_styles: watch_styles.unwrap_or(true),
            watch_scripts: watch_scripts.unwrap_or(true),
            watch_components: true,
            watch_assets: true,
        };
        
        Ok(Self {
            watcher: Arc::new(Mutex::new(FileWatcher::new(config))),
            pending_changes: Arc::new(Mutex::new(Vec::new())),
        })
    }
    
    /// Watch a directory path
    pub fn watch_path(&self, path: String) -> PyResult<bool> {
        let mut watcher = self.watcher.lock().unwrap();
        match watcher.watch_path(path) {
            Ok(_) => Ok(true),
            Err(e) => {
                eprintln!("Error watching path: {:?}", e);
                Ok(false)
            }
        }
    }
    
    /// Stop watching a directory path
    pub fn unwatch_path(&self, path: String) -> PyResult<bool> {
        let mut watcher = self.watcher.lock().unwrap();
        match watcher.unwatch_path(path) {
            Ok(_) => Ok(true),
            Err(e) => {
                eprintln!("Error unwatching path: {:?}", e);
                Ok(false)
            }
        }
    }
    
    /// Check if there are pending file changes
    pub fn has_changes(&self) -> PyResult<bool> {
        let watcher = self.watcher.lock().unwrap();
        let changes = watcher.process_events();
        
        if !changes.is_empty() {
            let mut pending = self.pending_changes.lock().unwrap();
            pending.extend(changes);
            Ok(true)
        } else {
            Ok(false)
        }
    }
    
    /// Get all pending changes as Python dictionary list
    pub fn get_changes(&self, py: Python) -> PyResult<PyObject> {
        let mut pending = self.pending_changes.lock().unwrap();
        let changes = std::mem::take(&mut *pending);
        
        let result = PyList::empty(py);
        for change in changes {
            let dict = PyDict::new(py);
            dict.set_item("path", change.path.to_string_lossy().to_string())?;
            dict.set_item("type", format!("{:?}", change.change_type))?;
            dict.set_item("timestamp", {
                let duration = change.timestamp
                    .duration_since(SystemTime::UNIX_EPOCH)
                    .unwrap_or_default();
                duration.as_secs_f64()
            })?;
            result.append(dict)?;
        }
        
        Ok(result.into())
    }
    
    /// Clear all pending changes without processing
    pub fn clear_changes(&self) -> PyResult<()> {
        let mut pending = self.pending_changes.lock().unwrap();
        pending.clear();
        Ok(())
    }
}
