---
name: harden
description: Improve Puree interface resilience through text overflow handling, error states, and edge case management.
user-invocable: true
argument-hint: [TARGET=<component or panel to harden>]
---

Strengthen Puree interfaces against edge cases, errors, missing resources, and real-world usage scenarios that break idealized designs.

## Assess Hardening Needs

Identify weaknesses and edge cases:

1. **Test with extreme inputs**:
   - Very long text (names, descriptions, titles)
   - Very short text (empty, single character)
   - Special characters (emoji, accented characters, Unicode)
   - Large numbers (millions, billions)
   - Many items (100+ list items, 50+ options in a panel)
   - No data (empty states)

2. **Test error scenarios**:
   - Python exceptions in script.py
   - Missing Blender objects or scene data
   - Invalid property values
   - Missing image assets
   - Missing font files
   - Blender state changes (scene switch, object deletion)

3. **Test resource scenarios**:
   - Missing images in `assets/` directory
   - Missing fonts in `fonts/` directory
   - Corrupted or invalid YAML
   - SCSS compilation errors
   - Component files not found

**CRITICAL**: Designs that only work with perfect data aren't production-ready. Harden against reality.

## Hardening Dimensions

Systematically improve resilience:

### Text Overflow & Wrapping

**Long text handling in Puree**:
```scss
// Single line with ellipsis — works in Puree
.truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
```

Puree supports `text-overflow: ellipsis` and `white-space: nowrap`. Use these on any container that displays dynamic text.

**Flex/Grid overflow**:
```scss
// Prevent flex items from overflowing
.flex_item {
  min-width: 0;
  overflow: hidden;
}

// Prevent grid items from overflowing
.grid_item {
  min-width: 0;
  min-height: 0;
}
```

**Text sizing considerations**:
- Set minimum readable sizes (11px minimum, 13px+ preferred)
- Use `@media` breakpoints to adjust `font-size` for different panel widths
- Ensure containers have enough height for text at the chosen font size

**Example — safe text container**:
```scss
.dynamic_label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  min-width: 0;
}
```

### Error Handling in Python

**Wrap Blender data access in try/except**:
```python
def main(self, app):
    def on_click(container):
        try:
            obj = bpy.context.active_object
            if obj is None:
                status_label = app.find("status_label")
                status_label.text = "No active object selected"
                status_label.mark_dirty()
                return

            name_label = app.find("object_name")
            name_label.text = obj.name
            name_label.mark_dirty()
        except Exception as e:
            error_label = app.find("error_text")
            error_label.text = f"Error: {str(e)}"
            error_label.mark_dirty()

    app.find("refresh_button").click.append(on_click)
    return app
```

**Guard against missing containers**:
```python
def safe_find(app, name):
    """Find a container, return None if not found."""
    try:
        return app.find(name)
    except:
        return None

def on_click(container):
    label = safe_find(app, "status_label")
    if label:
        label.text = "Updated"
        label.mark_dirty()
```

**Handle Blender state changes**:
- Active object may be `None`
- Scene data may change between frames
- Objects referenced by name may be deleted
- Always validate Blender data before using it in UI updates

### mark_dirty() Resilience

**Always call `mark_dirty()` after property changes**:
```python
# ❌ Bad: text changes but UI doesn't update
container.text = "New value"

# ✅ Good: UI updates to reflect new text
container.text = "New value"
container.mark_dirty()
```

**Batch property changes before marking dirty**:
```python
# ✅ Good: one mark_dirty() for multiple changes
container.text = "Updated"
container.set_property('background-color', 'rgba(255,0,0,0.2)')
container.mark_dirty()
```

### Missing Resource Handling

**Missing images**:
- Always verify image files exist in `assets/` before referencing them
- Design fallback states: use a solid `background-color` that looks intentional even without an image
- In Python, check file existence before setting image properties

**Missing fonts**:
- Puree falls back to the theme's `default_font` — ensure it's always available
- Don't rely on a specific font for layout correctness (different fonts have different metrics)
- Keep required fonts in the `fonts/` directory and reference them correctly

**Example — fallback styling**:
```scss
// Looks acceptable even without background image
.card_with_image {
  background-color: #2a2d35;
  border-radius: 8px;
  padding: 16px;
}
```

### Edge Cases & Boundary Conditions

**Empty states**:
- No items in a list — show a message explaining what will appear
- No Blender objects matching criteria — show clear feedback
- No data to display — provide a meaningful placeholder

**Example — empty state in YAML**:
```yaml
object_list:
  style: object_list
  empty_message:
    style: empty_state
    text: 'No objects found. Select objects in the viewport.'
    font: NeueMontreal-Regular
```

```scss
.empty_state {
  color: rgba(180, 180, 180, 0.6);
  font-size: 13px;
  text-align: center;
  --text-align-v: center;
  padding: 20px;
}
```

**Loading states**:
- Long-running Blender operations (mesh analysis, file export)
- Show what's happening ("Processing mesh...")
- Use Python to update a status label during operations

**Large datasets**:
- Many Blender objects (100+ items in a list)
- Use `display: none` to hide off-screen items
- Limit visible items and provide scroll or pagination controls
- Consider the container count impact on GPU rendering

**Concurrent operations**:
- Prevent double-clicks on action buttons (disable in click handler, re-enable after)
- Handle rapid hover/click sequences gracefully

```python
is_processing = False

def on_click(container):
    global is_processing
    if is_processing:
        return
    is_processing = True
    
    try:
        # ... do work ...
        pass
    finally:
        is_processing = False
```

### Input Validation

**Validate data in Python before displaying**:
- Check string lengths before setting text
- Validate numeric ranges before displaying values
- Sanitize Blender object names (they can contain any Unicode)

```python
def safe_display_name(name, max_length=30):
    """Truncate long names for display."""
    if len(name) > max_length:
        return name[:max_length - 3] + "..."
    return name
```

### SCSS Defensive Patterns

**Always constrain containers**:
```scss
// ❌ Bad: content can overflow
.label {
  font-size: 14px;
}

// ✅ Good: overflow handled gracefully
.label {
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
```

**Use percentage widths with constraints**:
```scss
.panel_content {
  width: 100%;
  max-width: 600px;
  min-width: 150px;
}
```

**Handle visibility for conditional content**:
```scss
.error_message {
  display: none;
  color: #e74c3c;
  font-size: 12px;
}
```

Then show/hide via Python:
```python
def show_error(app, message):
    error = app.find("error_message")
    error.text = message
    error.set_property('display', 'flex')
    error.mark_dirty()

def hide_error(app):
    error = app.find("error_message")
    error.set_property('display', 'none')
    error.mark_dirty()
```

## Testing Strategies

**Manual testing**:
- Test with extreme text (100+ character object names, single character names)
- Test with empty Blender scenes (no objects, no materials)
- Test with many objects (100+ items populating a list)
- Test panel at minimum width
- Test after Blender undo/redo operations
- Test after switching scenes
- Test with missing asset files

**Edge case checklist**:
- Delete an object that the UI references — does it crash?
- Set text to empty string — does the layout break?
- Set very long text — does it overflow or truncate?
- Remove an image file — does the panel still render?
- Rapidly click buttons — does state get corrupted?

**IMPORTANT**: Hardening is about expecting the unexpected. Real Blender users will do things you never imagined.

**NEVER**:
- Assume Blender data is always available (objects get deleted, scenes change)
- Leave error messages generic ("Error occurred") — explain what happened
- Use fixed widths for text containers (text length varies)
- Forget `mark_dirty()` after property changes (silent failure)
- Block the entire panel when one component errors
- Assume images or fonts will always be present
- Ignore empty states (no objects, no data)
- Let Python exceptions propagate uncaught (crashes the panel)

## Verify Hardening

Test thoroughly with edge cases:

- **Long text**: Try Blender object names with 100+ characters
- **Special characters**: Use emoji and Unicode in all text fields
- **Empty scene**: Remove all objects, test with no data
- **Missing assets**: Temporarily remove image/font files, verify graceful fallback
- **Rapid interaction**: Click buttons rapidly, hover quickly across elements
- **State changes**: Undo/redo in Blender, switch scenes, delete referenced objects
- **Narrow panels**: Test at minimum panel width
- **Many items**: Populate lists with 100+ items

Remember: You're hardening for production reality, not demo perfection. Expect users to have unexpected Blender configurations, missing files, and edge-case data. Build resilience into every container and every Python handler.