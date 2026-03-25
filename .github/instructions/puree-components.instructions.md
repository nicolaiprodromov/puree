---
description: "Use when editing Puree component files (YAML/SCSS in components/ directories). Covers component structure, parameter syntax, SCSS defaults, namespacing, and instantiation."
applyTo: "**/components/**"
---

# Puree Components

Reusable YAML+SCSS templates with parameterization. Like React components but in YAML.

## File Structure

```
components/
├── button.yaml       # Component definition
├── button.scss       # Component styles
├── card.yaml
└── card.scss
```

**Root key MUST match filename** — `button.yaml` must have `button:` as root key.

## Defining a Component

**`components/button.yaml`:**
```yaml
button:
  style: "{{btn_style, 'default_button'}}"
  btn_icon:
    style: btn_icon
    img: "{{btn_icon, 'star_on'}}"
  btn_label:
    style: btn_label
    text: "{{btn_text, 'Click Me'}}"
    passive: true
```

**`components/button.scss`:**
```scss
$btn_bg: #252830 !default;      // overridable via component params
$btn_radius: 8px !default;

.default_button {
  display: flex;
  flex-direction: row;
  align-items: center;
  background-color: $btn_bg;
  border-radius: $btn_radius;
  padding: 8px 16px;
  gap: 8px;
  transition: background-color 0.15s ease;

  &:hover { background-color: lighten($btn_bg, 8%); }
  &:active { background-color: lighten($btn_bg, 12%); }
}

.btn_label {
  font-size: 14px;
  color: #f0f3f6;
}
```

## Parameter Syntax

Format: `"{{parameter_name, 'default_value'}}"`

- **Outer double quotes** required in YAML
- **Inner single quotes** around default value required
- **Comma separator** between name and default required
- Parameter names: alphanumeric + underscores only

SCSS `$variables` with `!default` and matching parameter names are automatically overridden.

## Instantiating Components

```yaml
# In index.yaml — references components/button.yaml
my_submit_btn:
  data: '[button]'
  btn_text: Submit Form
  btn_icon: check_icon
  btn_bg: '#3498db'        # overrides $btn_bg in SCSS

my_cancel_btn:
  data: '[button]'
  btn_text: Cancel
  btn_style: cancel_button  # different style class
```

## Namespacing

Children get prefixed with instance name + underscore:

```
my_submit_btn              → my_submit_btn
  └── btn_icon             → my_submit_btn_btn_icon
  └── btn_label            → my_submit_btn_btn_label
```

This prevents ID collisions when using the same component multiple times.

## Accessing in Scripts

```python
def main(self, app):
    # Access through namespaced path
    submit_label = app.theme.root.my_submit_btn_btn_label
    submit_label.text = "Submitting..."
    submit_label.mark_dirty()

    # Or by ID
    cancel = app.get_by_id("my_cancel_btn")
    cancel.click.append(on_cancel)
    return app
```

## Text Input Components

```yaml
my_input:
  data: "<INPUT>|Type here..."   # Creates text input with placeholder
```

## Best Practices

- **One concern per component** — button, card, nav_item, not "entire sidebar"
- **Meaningful parameter names** — `btn_text` not `txt`
- **Use `!default`** on all SCSS variables so they can be overridden
- **Keep components focused** — 5-15 nodes each, not 50+
- **Document parameters** — use clear default values that show expected content

For full reference: [COMPONENTS.md](../../docs/COMPONENTS.md)
