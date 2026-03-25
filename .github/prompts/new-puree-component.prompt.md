---
description: "Scaffold a new reusable Puree component with parameterized YAML and matching SCSS."
agent: agent
argument-hint: "Describe the component (e.g. 'status badge with icon, label, and color')"
---

Create a reusable Puree component from the user's description. Generate both the YAML definition and SCSS stylesheet.

## Generate Two Files

### 1. `components/{name}.yaml` — Component Definition

- **Root key MUST match filename** (e.g., `status_badge.yaml` → `status_badge:`)
- Use parameters for customizable values: `"{{param_name, 'default_value'}}"`
- Parameter format: outer double quotes, inner single quotes, comma separator
- Node names use underscores only
- Mark text-only children as `passive: true`

```yaml
# Example: components/status_badge.yaml
status_badge:
  style: "{{badge_style, 'status_badge'}}"
  badge_icon:
    style: badge_icon
    img: "{{badge_icon, 'info'}}"
  badge_label:
    style: badge_label
    text: "{{badge_text, 'Status'}}"
    passive: true
```

### 2. `components/{name}.scss` — Component Styles

- Use `$variable: value !default;` for all overridable values
- Variable names should match parameter names where applicable
- Include `:hover`/`:active` states if the component is interactive
- Only animate `background-color`, `color`, `border-color`, `opacity`
- Use `transition:` for smooth state changes

```scss
// Example: components/status_badge.scss
$badge_bg: rgba(255, 255, 255, 0.05) !default;
$badge_radius: 6px !default;

.status_badge {
  display: flex;
  flex-direction: row;
  align-items: center;
  background-color: $badge_bg;
  border-radius: $badge_radius;
  padding: 6px 12px;
  gap: 8px;
}

.badge_label {
  font-size: 13px;
  color: rgba(240, 243, 246, 0.9);
  --text-align-v: center;
}
```

## Show Usage Example

After generating the component, show how to instantiate it in `index.yaml`:

```yaml
my_badge:
  data: '[status_badge]'
  badge_text: Online
  badge_icon: check_circle
  badge_bg: 'rgba(46, 204, 113, 0.15)'
```

## Conventions

- Read [COMPONENTS.md](../../docs/COMPONENTS.md) for the full component system reference
- Children get namespaced: `my_badge` → `my_badge_badge_icon`, `my_badge_badge_label`
- Keep components focused (5-15 nodes, one concern)
- Use meaningful parameter names: `card_title` not `t1`
