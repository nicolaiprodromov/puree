# Motion Design

## Puree Transition System

Puree supports CSS `transition` for state changes. This is the only animation mechanism — there are no `@keyframes`, no `animation` property, no `transform` animations.

**Animatable properties**: `background-color`, `color` (text), `border-color`, `opacity`
**Timing functions**: `ease`, `linear`, `ease-in`, `ease-out`, `ease-in-out`
**Delay**: `transition-delay` is supported

## Duration: The 100/300/500 Rule

Timing matters more than easing. These durations feel right for most UI transitions:

| Duration | Use Case | Examples |
|----------|----------|----------|
| **100-150ms** | Instant feedback | Button press, color change |
| **200-300ms** | State changes | Hover effects, active states |
| **300-500ms** | Emphasis | Panel reveals via opacity fade |

**Exit transitions should be faster than entrances** — use ~75% of enter duration.

## Easing: Pick the Right Curve

| Curve | Use For | SCSS |
|-------|---------|------|
| **ease-out** | Elements appearing, hover-in | `transition: opacity 0.3s ease-out` |
| **ease-in** | Elements fading, hover-out | `transition: opacity 0.2s ease-in` |
| **ease-in-out** | State toggles (there and back) | `transition: background-color 0.3s ease-in-out` |
| **linear** | Continuous changes, opacity | `transition: opacity 0.5s linear` |
| **ease** | General purpose fallback | `transition: color 0.2s ease` |

## Transition Patterns in Puree

### Hover Feedback

The most common use: change `background-color` and/or `color` on hover.

```scss
.nav_item {
  background-color: rgba(26, 29, 36, 0.95);
  color: rgba(181, 188, 199, 0.8);
  transition: background-color 0.2s ease, color 0.2s ease;
}

.nav_item:hover {
  background-color: rgba(37, 40, 48, 0.95);
  color: rgba(245, 248, 250, 0.95);
}

.nav_item:active {
  background-color: rgba(52, 152, 219, 0.3);
}
```

### Multi-Property Transitions

Combine transitions for richer state changes:

```scss
.card {
  background-color: rgba(26, 29, 36, 0.95);
  border-color: rgba(255, 255, 255, 0.06);
  opacity: 0.9;
  transition: background-color 0.2s ease,
              border-color 0.3s ease,
              opacity 0.3s ease-out;
}

.card:hover {
  background-color: rgba(37, 40, 48, 0.95);
  border-color: rgba(52, 152, 219, 0.4);
  opacity: 1;
}
```

### Active (Press) Feedback

Use `:active` for immediate press feedback. Make it faster than hover:

```scss
.button {
  background-color: #3498db;
  transition: background-color 0.15s ease;
}

.button:hover {
  background-color: #5dade2;
}

.button:active {
  background-color: #2176ad;
}
```

### Fade Patterns via Opacity

Use `opacity` transitions for reveal/hide effects:

```scss
.tooltip {
  opacity: 0;
  transition: opacity 0.2s ease-out;
}

.tooltip:hover {
  opacity: 1;
}
```

### Transition Delay for Sequencing

Use `transition-delay` to create a staggered feel between multiple properties:

```scss
.panel_item {
  background-color: rgba(26, 29, 36, 0.95);
  color: rgba(181, 188, 199, 0.8);
  border-color: rgba(255, 255, 255, 0.06);
  transition: background-color 0.2s ease,
              color 0.15s ease 0.05s,
              border-color 0.3s ease 0.1s;
}
```

## Runtime Transitions via Python

When changing properties through Python scripts, transitions defined in SCSS still apply:

```python
def main(self, app):
    panel = app.find("info_panel")

    def highlight(container):
        container.set_property('background-color', 'rgba(52, 152, 219, 0.3)')
        container.set_property('border-color', 'rgba(52, 152, 219, 0.6)')
        container.mark_dirty()

    def reset(container):
        container.set_property('background-color', 'rgba(26, 29, 36, 0.95)')
        container.set_property('border-color', 'rgba(255, 255, 255, 0.06)')
        container.mark_dirty()

    panel.hover.append(highlight)
    panel.hoverout.append(reset)
    return app
```

If the element has `transition: background-color 0.2s ease, border-color 0.3s ease` in SCSS, the runtime property changes will animate smoothly.

## Motion Tokens

Create SCSS variables for consistent transition durations across your interface:

```scss
$duration-fast: 0.1s;
$duration-normal: 0.2s;
$duration-slow: 0.35s;

$ease-default: ease;
$ease-enter: ease-out;
$ease-exit: ease-in;

// Reusable transition shorthand
.interactive {
  transition: background-color $duration-normal $ease-default,
              color $duration-normal $ease-default;
}
```

---

**Avoid**: Expecting `@keyframes`, `transform`, or `animation` to work. Transitions longer than 500ms for UI feedback. Animating properties other than `background-color`, `color`, `border-color`, `opacity`. Forgetting to call `mark_dirty()` after runtime changes.
