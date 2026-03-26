---
name: adapt
description: Adapt Puree UI (YAML/SCSS) designs to work across different Blender panel sizes and workspace configurations.
user-invocable: true
argument-hint: 'Describe the panel or component and target context (e.g. "toolbar for narrow sidebar", "settings panel for wide viewport")'
---

Adapt existing Puree designs to work effectively across different Blender panel sizes, workspace configurations, and monitor resolutions.

## MANDATORY PREPARATION

Use the frontend-design skill — it contains design principles, anti-patterns, and the **Context Gathering Protocol**. Follow the protocol before proceeding — if no design context exists yet, you MUST run teach-impeccable first. Additionally gather: target panel sizes and workspace contexts.

---

## Assess Adaptation Challenge

Understand what needs adaptation and why:

1. **Identify the source context**:
   - What panel size was it designed for originally? (Wide sidebar? Narrow properties panel?)
   - What assumptions were made? (Fixed width? Specific workspace layout?)
   - What works well in the current context?

2. **Understand target context**:
   - **Panel type**: Sidebar, properties panel, floating panel, full-region panel?
   - **Panel width range**: Narrow (200-300px), medium (300-500px), wide (500px+)?
   - **Monitor resolution**: Standard 1080p, high-DPI 4K, ultrawide?
   - **Workspace layout**: Single panel visible, split workspace, multiple monitors?
   - **User workflow**: Quick glance while modeling, focused configuration, data entry?

3. **Identify adaptation challenges**:
   - What won't fit in narrow panels? (Multi-column layouts, wide content)
   - What wastes space in wide panels? (Single-column layouts stretched too wide)
   - What information hierarchy changes with panel size?

**CRITICAL**: Adaptation is not just scaling — it's rethinking the layout for each panel context. Blender users resize panels constantly.

## Plan Adaptation Strategy

Create context-appropriate strategy:

### Narrow Panel Adaptation (< 300px)

**Layout Strategy**:
- Single column, vertical stacking
- Full-width containers instead of fixed widths
- Collapse secondary information
- Use `display: none` to hide non-essential sections

**Content Strategy**:
- Progressive disclosure (show primary controls only)
- Truncate labels with `text-overflow: ellipsis`
- Use icons where text labels are too long
- Smaller font sizes where readable (minimum 11px)

**Example SCSS**:
```scss
@media (max-width: 300px) {
  .sidebar_content {
    flex-direction: column;
  }
  .detail_panel {
    display: none;
  }
  .label_text {
    white-space: nowrap;
    text-overflow: ellipsis;
    overflow: hidden;
  }
}
```

### Medium Panel Adaptation (300-500px)

**Layout Strategy**:
- Two-column layouts where content supports it
- Side-by-side controls (label + value)
- Balanced use of space

**Content Strategy**:
- Show most controls and information
- Use shorter label text where needed
- Group related controls together

### Wide Panel Adaptation (500px+)

**Layout Strategy**:
- Multi-column layouts to use horizontal space
- Side-by-side panels (list + detail)
- More generous padding and spacing
- Don't stretch single elements to fill extreme widths — use `max-width`

**Content Strategy**:
- Show all information upfront (less progressive disclosure)
- Display descriptions and help text inline
- Use wider data displays

**Example SCSS**:
```scss
@media (min-width: 500px) {
  .tool_panel {
    display: flex;
    flex-direction: row;
  }
  .tool_list {
    width: 40%;
  }
  .tool_detail {
    width: 60%;
  }
}
```

### High-DPI / 4K Monitor Adaptation

**Layout Strategy**:
- Ensure text remains readable at high resolutions
- Use appropriate font sizes (Blender already handles DPI scaling, but verify)
- Test that fixed `px` sizes still look correct

## Implement Adaptations

Apply changes systematically:

### Content-Driven Breakpoints

Choose breakpoints based on where the design breaks, not arbitrary numbers:
- Narrow: where labels start truncating or columns collapse
- Medium: where two-column layout becomes comfortable
- Wide: where additional content panels can appear

Puree supports `@media (min-width: Npx)` and `@media (max-width: Npx)`.

### Layout Adaptation Techniques

- **Flex direction switching**: Change `flex-direction: row` to `column` at breakpoints
- **`display: none`**: Hide non-essential sections in narrow panels
- **Percentage widths**: Use `%` for fluid container sizing
- **`min-width` / `max-width`**: Constrain containers to comfortable ranges
- **Grid layouts**: Use `display: grid` with `grid-template-columns` for adaptive grids

**Example — responsive two-column layout**:
```scss
.settings_panel {
  display: flex;
  flex-direction: column;
}

@media (min-width: 400px) {
  .settings_panel {
    flex-direction: row;
  }
  .settings_sidebar {
    width: 40%;
  }
  .settings_content {
    width: 60%;
  }
}
```

### Text Adaptation

- Use `text-overflow: ellipsis` with `white-space: nowrap` for labels that may overflow
- Adjust `font-size` at breakpoints if needed
- Use shorter text variants for narrow contexts via component parameters

**Example — truncating labels in narrow panels**:
```scss
.control_label {
  font-size: 13px;
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
}

@media (min-width: 400px) {
  .control_label {
    font-size: 14px;
  }
}
```

### Visibility Toggling

Use `display: none` to hide sections that don't fit:

```scss
.help_text {
  display: flex;
}

@media (max-width: 300px) {
  .help_text {
    display: none;
  }
}
```

### Component-Based Adaptation

Use Puree's component system to create variants:

```yaml
# Compact variant for narrow panels
compact_control:
  data: '[control]'
  show_label: 'false'
  show_description: 'false'

# Full variant for wide panels
full_control:
  data: '[control]'
  show_label: 'true'
  show_description: 'true'
```

Then toggle visibility in SCSS based on breakpoints.

**NEVER**:
- Hide core functionality in narrow panels (if it matters, make it work at every size)
- Use different information hierarchy across panel sizes (confusing)
- Use generic breakpoints blindly (use content-driven breakpoints where the design breaks)
- Assume all users have wide panels (Blender panels are often narrow)
- Forget that users constantly resize Blender panels
- Hard-code pixel widths that prevent any flexibility

## Verify Adaptations

Test thoroughly across Blender workspace configurations:

- **Narrow sidebar**: Drag Blender panel to minimum width (~200px)
- **Medium panel**: Test at typical properties panel width (~350px)
- **Wide panel**: Test in a maximized or floating panel (~600px+)
- **Multiple monitors**: Test with different monitor resolutions (1080p, 1440p, 4K)
- **Different workspaces**: Test in Blender's built-in workspace presets (Modeling, Sculpting, UV Editing, etc.)
- **Edge cases**: Very narrow panels, very wide panels
- **Content extremes**: Long text, empty states, many items

Remember: Blender users work in highly customized workspace layouts. Your UI must adapt gracefully to whatever panel size the user gives it. Design for the narrowest comfortable width first, then enhance for wider panels.