---
description: "Use when editing Puree script.py files. Covers main() signature, event handlers, mark_dirty(), container API, runtime property changes, and show/hide patterns."
applyTo: "**/script.py"
---

# Puree Python Scripting (script.py)

## Entry Point — CRITICAL

```python
def main(self, app):
    # Your code here
    return app  # MUST return app — forgetting this breaks everything
```

## Accessing Containers

```python
# Dot notation through the tree (preferred)
button = app.theme.root.sidebar.my_button

# By ID (alternative)
button = app.get_by_id("my_button")
```

For component instances, children are namespaced with the instance name:
```python
# If my_card uses [card] component with child card_header:
header = app.theme.root.my_card_card_header
```

## Event Handlers

All callbacks receive `fn(container)`:

| Event      | Registration                  | Trigger                    |
|------------|-------------------------------|----------------------------|
| `click`    | `el.click.append(fn)`         | Element clicked            |
| `hover`    | `el.hover.append(fn)`         | Mouse enters element       |
| `hoverout` | `el.hoverout.append(fn)`      | Mouse leaves element       |
| `toggle`   | `el.toggle.append(fn)`        | Element toggled            |
| `scroll`   | `el.scroll.append(fn)`        | Element scrolled           |

```python
def on_click(container):
    print(f"Clicked: {container.id}")

button.click.append(on_click)
```

## Modifying Properties at Runtime — ALWAYS mark_dirty()

```python
def on_click(container):
    label = app.theme.root.main.status_label
    label.text = "Updated!"
    label.mark_dirty()  # REQUIRED — without this, GPU won't sync
```

**Every time you change a container property, call `mark_dirty()` on that container.**

## Runtime Style Changes

```python
# Use set_property with CSS property names
container.set_property('background-color', 'rgba(52, 152, 219, 1.0)')
container.set_property('color', 'rgba(255, 255, 255, 1.0)')
container.set_property('opacity', '0.8')
container.set_property('background', 'linear-gradient(90deg, rgba(0,0,0,0.8), rgba(0,0,0,0))')
container.mark_dirty()
```

## Show/Hide Elements

```python
def toggle_panel(container):
    panel = app.theme.root.modal
    if panel.style.display == 'NONE':
        panel.style.display = 'FLEX'
    else:
        panel.style.display = 'NONE'
    panel.mark_dirty()
```

Note: runtime `display` values are uppercase strings: `'FLEX'`, `'NONE'`, `'GRID'`, `'BLOCK'`.

## Container Properties

| Property   | Type              | Description                          |
|------------|-------------------|--------------------------------------|
| `id`       | `str`             | Unique identifier                    |
| `parent`   | `Container/None`  | Parent container                     |
| `children` | `List[Container]` | Child containers                     |
| `style`    | `Style`           | Resolved style object                |
| `text`     | `str/None`        | Text content                         |
| `img`      | `str/None`        | Image asset name                     |
| `font`     | `str/None`        | Font face name                       |
| `passive`  | `bool`            | Non-interactive flag                 |
| `_hovered` | `bool`            | Currently hovered (read-only)        |
| `_toggled` | `bool`            | Currently toggled (read-only)        |
| `_toggle_value` | `bool`       | Toggle state (read-only)             |
| `_scroll_value` | `float`      | Scroll position (read-only)          |

## Async Operations

Use threading for network calls or long operations — never block `main()`:

```python
import threading

def fetch_data(container):
    def _do_fetch():
        result = some_api_call()
        label.text = result
        label.mark_dirty()
    threading.Thread(target=_do_fetch).start()
```

## Complete Example

```python
def main(self, app):
    nav_home = app.theme.root.content.sidebar.nav_home
    nav_settings = app.theme.root.content.sidebar.nav_settings
    status = app.theme.root.content.main.status_text

    def go_home(container):
        status.text = "Home selected"
        status.mark_dirty()

    def go_settings(container):
        status.text = "Settings selected"
        status.mark_dirty()

    nav_home.click.append(go_home)
    nav_settings.click.append(go_settings)
    return app
```

For full API reference: [API.md](../../docs/API.md)
