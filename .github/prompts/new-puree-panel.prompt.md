---
description: "Scaffold a new Puree UI panel with correct boilerplate. Generates index.yaml, style.scss, script.py, and __init__.py."
agent: agent
argument-hint: "Describe the panel to build (e.g. 'render settings panel with dark theme')"
---

Create a complete, working Puree UI panel from the user's description. Generate all required files with correct structure and conventions.

## Required Files

Generate these 4 files in the target directory:

### 1. `index.yaml` — UI Structure
- Must include full theme config (`app > selected_theme > default_theme > theme[]`)
- Theme must have: `name`, `author`, `version`, `default_font`, `styles`, `scripts`, `components`, `root`
- All node names use **underscores** (never hyphens): `my_button` ✓ `my-button` ✗
- Use `style:` or `class:` to assign CSS classes
- Use `text:` for text content, `font:` for font face, `img:` for images
- Components via `data: '[component_name]'`

### 2. `style.scss` — Styling
- Define SCSS variables at top for colors, spacing, radii
- Use dark theme defaults suitable for Blender (dark backgrounds, light text)
- `.root` should be `display: flex; width: 100%; height: 100%;`
- Add `:hover` and `:active` states for interactive elements
- Add `transition: background-color 0.15s ease` for smooth interactions
- Only `background-color`, `color`, `border-color`, `opacity` are animatable
- Use `--text-align-v: center` for vertical text centering
- Only `px` and `%` units (no em/rem/vw/vh)

### 3. `script.py` — Interactivity
```python
def main(self, app):
    # Wire up event handlers
    return app  # MUST return app
```
- Access containers via `app.theme.root.path.to.element`
- Event handlers: `el.click.append(fn)`, `el.hover.append(fn)`
- Always call `mark_dirty()` after modifying properties

### 4. `__init__.py` — Blender Addon Entry Point
```python
# Puree addon entry point
```

## Design Quality

Use the `/frontend-design` skill principles — avoid generic "AI slop" aesthetics. Make intentional design choices:
- Purposeful color palette (not just gray everywhere)
- Clear visual hierarchy with font sizes and weight
- Consistent spacing rhythm
- Appropriate use of border-radius, shadows, gradients

Read [PUREE_VS_CSS.md](../../docs/PUREE_VS_CSS.md) for the full property reference and [PUREE_SPEC.md](../../docs/PUREE_SPEC.md) for the complete spec.
