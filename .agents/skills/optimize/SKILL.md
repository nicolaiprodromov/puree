---
name: optimize
description: Improve Puree UI (YAML/SCSS/Python) performance across rendering speed, container efficiency, and resource usage.
user-invocable: true
argument-hint: 'Describe the panel or component to optimize (e.g. "main panel with 200+ containers", "transition-heavy toolbar")'
---

Identify and fix performance issues in Puree UIs. Puree renders via ModernGL compute shaders — performance characteristics differ fundamentally from web browsers.

## Assess Performance Issues

Understand current performance and identify problems:

1. **Measure current state**:
   - **Container count**: Total number of YAML nodes in the tree (each becomes a GPU-rendered container)
   - **Transition count**: Number of active CSS transitions running simultaneously
   - **Image count and size**: Number and resolution of images loaded from `assets/`
   - **Font count**: Number of different fonts loaded from `fonts/`
   - **SCSS complexity**: Depth of selector nesting, number of rules
   - **`mark_dirty()` frequency**: How often relayout is triggered from Python

2. **Identify bottlenecks**:
   - Is the container tree too deep or wide? (Too many nodes = slower GPU rendering)
   - Are there unnecessary containers that could be eliminated?
   - Are `mark_dirty()` calls happening too frequently? (Each triggers a full relayout)
   - Are images oversized for their display area?
   - Are transitions running on elements that don't need them?

**CRITICAL**: Measure before and after. Premature optimization wastes time. Optimize what actually matters.

## Optimization Strategy

Create systematic improvement plan:

### Container Efficiency

**Minimize container count** — every YAML node creates a GPU-rendered container:

```yaml
# ❌ Bad: unnecessary wrapper containers
wrapper:
  inner_wrapper:
    content_wrapper:
      actual_content:
        text: "Hello"

# ✅ Good: flat structure, fewer containers
actual_content:
  text: "Hello"
```

**Flatten the YAML tree** — fewer nesting levels means fewer containers to render:
- Remove wrapper containers that exist only for structure
- Combine containers where one can serve multiple purposes
- Use `padding` and `margin` on the content container instead of adding spacer containers

**Use `display: none` for hidden content**:
```scss
// Hide sections that aren't currently needed
.collapsed_section {
  display: none;
}
```

Containers with `display: none` are excluded from layout calculation and rendering entirely — use this aggressively for tabbed interfaces, conditional panels, and sections the user hasn't opened.

### Component System Efficiency

**Use components to avoid YAML duplication** — but be aware each instance creates its own container subtree:

```yaml
# ❌ Bad: duplicating the same structure 10 times in index.yaml
item_1:
  style: list_item
  icon_1:
    style: item_icon
  label_1:
    style: item_label
    text: "Item 1"
item_2:
  style: list_item
  icon_2:
    style: item_icon
  # ... repeated 10 times

# ✅ Good: use a component, but consider if you need all instances visible
item_1:
  data: '[list_item]'
  item_text: 'Item 1'
  item_icon: 'icon_1'
```

**Limit visible list items** — if you have 50+ items, don't render them all. Use Python to dynamically populate a fixed number of visible containers and hide the rest.

### SCSS Efficiency

**Avoid deeply nested selectors** — Puree's SCSS engine processes every rule against every container:

```scss
// ❌ Bad: deep nesting creates complex selectors
.root {
  .panel {
    .section {
      .subsection {
        .item {
          .label {
            color: #fff;
          }
        }
      }
    }
  }
}

// ✅ Good: flat, targeted selectors
.item_label {
  color: #fff;
}
```

**Use SCSS variables to avoid repetition**:
```scss
$bg-dark: #1a1d24;
$text-muted: rgba(181, 188, 199, 0.9);
$border-radius: 8px;

.card {
  background-color: $bg-dark;
  border-radius: $border-radius;
}

.subtitle {
  color: $text-muted;
}
```

**Use class selectors, not deep descendant chains**:
```scss
// ❌ Slower: engine must trace ancestry
.root .panel .content .label { color: #fff; }

// ✅ Faster: direct class match
.content_label { color: #fff; }
```

### Image Optimization

**Use appropriate image sizes** — don't load a 2000px image for a 50px icon:
- Resize images in `assets/` to match their display size
- Use PNG for icons and UI elements with transparency
- Use JPG for photographic content (smaller file size)
- Keep icon images small (32x32, 64x64 for standard icons)

**Share images across components** — reference the same image name in multiple containers rather than duplicating files.

### Transition Optimization

**Only animate what's necessary** — each active transition consumes GPU resources:

```scss
// ❌ Bad: transitioning everything
.button {
  transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease, opacity 0.3s ease;
}

// ✅ Good: only transition what the user will notice
.button {
  transition: background-color 0.2s ease;
}
```

**Keep transition durations short** — Puree transitions run on the GPU, but long durations (>0.5s) keep the animation loop active longer:
- Hover feedback: 0.1s-0.2s
- State changes: 0.2s-0.3s
- Major visual changes: 0.3s-0.5s max

**Don't transition containers that are hidden** — containers with `display: none` skip rendering, but transitioning them before hiding wastes frames.

### mark_dirty() Optimization

**Minimize `mark_dirty()` calls** — each call triggers a full relayout of the container tree:

```python
# ❌ Bad: multiple mark_dirty() calls for related changes
label.text = "New text"
label.mark_dirty()
icon.set_property('opacity', '1.0')
icon.mark_dirty()
status.text = "Updated"
status.mark_dirty()

# ✅ Good: batch changes, then mark dirty on a common ancestor
label.text = "New text"
icon.set_property('opacity', '1.0')
status.text = "Updated"
# Mark the parent dirty once — children update too
parent_container.mark_dirty()
```

**Avoid `mark_dirty()` in loops or high-frequency callbacks**:
```python
# ❌ Bad: marking dirty on every hover event
def on_hover(container):
    counter.text = str(int(counter.text) + 1)
    counter.mark_dirty()  # Triggers relayout on every mouse move

# ✅ Good: throttle updates or batch them
import time
last_update = 0

def on_hover(container):
    nonlocal last_update
    now = time.time()
    if now - last_update < 0.1:  # Throttle to 10 updates/sec
        return
    last_update = now
    counter.text = str(int(counter.text) + 1)
    counter.mark_dirty()
```

### Font Optimization

**Limit font variety** — each font file is loaded into GPU memory:
- Use 1-3 fonts maximum (regular, bold, italic of the same family)
- Set `default_font` in the theme to avoid loading unnecessary fonts
- Place only required font files in `fonts/`

### @media Query Efficiency

**Use `@media` to reduce visible content at smaller sizes**:
```scss
// Hide non-essential panels when space is tight
@media (max-width: 350px) {
  .detail_panel {
    display: none;
  }
  .description_text {
    display: none;
  }
}
```

This reduces the number of containers that need rendering at smaller panel sizes.

### Hot Reload Efficiency

During development, Puree supports hot reload. To maximize development speed:
- Keep YAML files modular (smaller files reload faster)
- Use components for reusable patterns (change once, updates everywhere)
- Keep SCSS organized (easier to find and edit rules)
- Test with hot reload frequently to catch performance issues early

## Performance Monitoring

**What to watch**:
- Container count in the YAML tree (use `grep -c` on YAML to estimate)
- Visual smoothness of transitions (watch for stuttering)
- Responsiveness of click/hover handlers
- Memory usage in Blender's status bar
- Time to render after `mark_dirty()` calls

**Profiling approach**:
- Add timing in Python scripts to measure handler execution time
- Count `mark_dirty()` calls to identify excessive relayouts
- Temporarily remove sections to isolate performance bottlenecks

**IMPORTANT**: Test on the target hardware. Development machines may mask performance issues that appear on lower-spec systems.

**NEVER**:
- Optimize without measuring (premature optimization)
- Add containers "just in case" — every container costs GPU time
- Use deeply nested SCSS selectors when flat classes work
- Call `mark_dirty()` in tight loops or high-frequency events
- Load oversized images for small display areas
- Transition every property when only one or two matter
- Forget that `display: none` is your best friend for performance
- Sacrifice usability for performance (a fast but unusable UI is worthless)

## Verify Improvements

Test that optimizations worked:

- **Container count**: Compare before/after YAML node counts
- **Visual smoothness**: Are transitions smooth? Do hover effects respond instantly?
- **Responsiveness**: Do click handlers execute without visible delay?
- **Panel resize**: Does the UI adapt quickly when Blender panels are resized?
- **No regressions**: Ensure all functionality still works after optimization
- **User perception**: Does it *feel* faster and more responsive?

Remember: Performance in Puree is primarily about container count, `mark_dirty()` frequency, and transition efficiency. Fewer containers, fewer relayouts, and targeted transitions make everything feel snappy.