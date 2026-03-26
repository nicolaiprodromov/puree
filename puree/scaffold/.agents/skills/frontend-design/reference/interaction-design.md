# Interaction Design

## Interactive States in Puree

Puree supports two CSS pseudo-classes for interactive states: `:hover` and `:active`. Design these states for every interactive element:

| State | When | Visual Treatment |
|-------|------|------------------|
| **Default** | At rest | Base styling |
| **Hover** | Pointer over element | Subtle color shift, lighter background |
| **Active** | Being pressed/clicked | Darker or accent color, "pressed in" feel |
| **Disabled** | Not interactive | Reduced opacity via SCSS, `pointer-events: none` |

```scss
.button {
  background-color: rgba(37, 40, 48, 0.95);
  color: rgba(220, 225, 235, 0.9);
  padding: 8px 16px;
  border-radius: 6px;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.button:hover {
  background-color: rgba(52, 58, 70, 0.95);
  color: rgba(245, 248, 250, 1);
}

.button:active {
  background-color: rgba(52, 152, 219, 0.4);
}

.button_disabled {
  opacity: 0.4;
  pointer-events: none;
}
```

**Note**: Puree does not support `:focus` or `:focus-visible` — the interface runs in Blender's viewport where keyboard focus management differs from browsers.

## Python Event Handlers

Puree's interactivity is driven by Python scripts. Events are attached via list callbacks:

### Available Events

| Event | How to Attach | When Fired |
|-------|---------------|------------|
| **Click** | `container.click.append(fn)` | Element is clicked |
| **Hover in** | `container.hover.append(fn)` | Pointer enters element |
| **Hover out** | `container.hoverout.append(fn)` | Pointer leaves element |
| **Toggle** | `container.toggle.append(fn)` | Element toggled (has `_toggle_value`) |
| **Scroll** | `container.scroll.append(fn)` | Scroll event on element |

### Event Handler Pattern

Every handler receives the container as its argument. Always call `mark_dirty()` after modifying properties:

```python
def main(self, app):
    btn = app.find("action_button")

    def on_click(container):
        container.set_property('background-color', 'rgba(52, 152, 219, 0.8)')
        container.text = "Clicked!"
        container.mark_dirty()

    def on_hover(container):
        container.set_property('background-color', 'rgba(52, 58, 70, 0.95)')
        container.mark_dirty()

    def on_hoverout(container):
        container.set_property('background-color', 'rgba(37, 40, 48, 0.95)')
        container.mark_dirty()

    btn.click.append(on_click)
    btn.hover.append(on_hover)
    btn.hoverout.append(on_hoverout)

    return app
```

### Toggle Pattern

Toggles provide a built-in `_toggle_value` boolean:

```python
def on_toggle(container):
    if container['_toggle_value']:
        container.set_property('background-color', 'rgba(46, 204, 113, 0.3)')
    else:
        container.set_property('background-color', 'rgba(37, 40, 48, 0.95)')
    container.mark_dirty()

toggle_btn.toggle.append(on_toggle)
```

### Accessing Other Elements

Navigate the container tree using dot notation or `app.find()` / `app.get_by_id()`:

```python
def main(self, app):
    # Dot notation access
    status = app.theme.root.sidebar.status_label

    # find by ID
    panel = app.find("info_panel")
    # or
    panel = app.get_by_id("info_panel")

    def update_status(container):
        status.text = "Active"
        status.set_property('color', 'rgba(46, 204, 113, 0.9)')
        status.mark_dirty()

    panel.click.append(update_status)
    return app
```

## Designing Interactive Patterns

### Button Hierarchy

Not every button should look the same. Create a visual hierarchy:

```scss
// Primary action — bold, accent color
.btn_primary {
  background-color: #3498db;
  color: rgba(255, 255, 255, 0.95);
  padding: 10px 20px;
  border-radius: 6px;
  transition: background-color 0.15s ease;
}
.btn_primary:hover { background-color: #5dade2; }
.btn_primary:active { background-color: #2176ad; }

// Secondary action — subtle, outlined
.btn_secondary {
  background-color: transparent;
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: rgba(200, 205, 215, 0.9);
  padding: 10px 20px;
  border-radius: 6px;
  transition: background-color 0.15s ease, border-color 0.15s ease;
}
.btn_secondary:hover {
  background-color: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.25);
}

// Ghost action — minimal, text-only feel
.btn_ghost {
  background-color: transparent;
  color: rgba(181, 188, 199, 0.7);
  padding: 8px 12px;
  transition: color 0.15s ease, background-color 0.15s ease;
}
.btn_ghost:hover {
  color: rgba(245, 248, 250, 0.95);
  background-color: rgba(255, 255, 255, 0.05);
}
```

### Progressive Disclosure

Start simple, reveal complexity through interaction. Use visibility and opacity to show/hide advanced sections:

```python
def main(self, app):
    toggle = app.find("show_advanced")
    advanced = app.find("advanced_panel")

    def on_toggle(container):
        if container['_toggle_value']:
            advanced.set_property('display', 'flex')
            advanced.set_property('opacity', '1')
        else:
            advanced.set_property('display', 'none')
        advanced.mark_dirty()

    toggle.toggle.append(on_toggle)
    return app
```

### Empty States

Empty states are onboarding moments. Design them to teach, not just acknowledge:

```yaml
empty_state:
  class: empty_state
  icon:
    class: empty_icon
    img: folder_empty
  message:
    class: empty_message
    text: "No projects yet"
  action_hint:
    class: empty_hint
    text: "Create your first project to get started"
```

### Loading States

Show specific feedback during operations:

```python
def on_export(container):
    container.text = "Exporting..."
    container.set_property('opacity', '0.6')
    container.set_property('pointer-events', 'none')
    container.mark_dirty()
```

### Destructive Actions: Undo Over Confirm

Undo is better than confirmation dialogs — users click through confirmations mindlessly. For reversible actions, perform the action immediately and offer undo. Reserve confirmation dialogs for truly irreversible operations.

---

**Avoid**: Forgetting `mark_dirty()` after property changes. Forgetting to `return app` from `main()`. Attaching events to passive elements. Using hover for critical functionality (not all users can hover).
