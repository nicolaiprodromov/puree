# Spatial Design

## Spacing Systems

### Use 4pt Base, Not 8pt

8pt systems are too coarse—you'll frequently need 12px (between 8 and 16). Use 4pt for granularity: 4, 8, 12, 16, 24, 32, 48, 64, 96px.

Define spacing as SCSS variables:

```scss
$space-xs: 4px;
$space-sm: 8px;
$space-md: 16px;
$space-lg: 24px;
$space-xl: 32px;
$space-2xl: 48px;
$space-3xl: 64px;
```

### Name Tokens Semantically

Name by relationship (`$space-sm`, `$space-lg`), not value (`$spacing-8`). Use `gap` for sibling spacing in flex/grid containers—it's cleaner than adding margin to each child.

```scss
.toolbar {
  display: flex;
  flex-direction: row;
  gap: $space-sm;
  padding: $space-md;
}
```

## Layout with Flexbox & Grid

### Flexbox Layouts

Puree uses the Taffy/Stretchable engine for flexbox, supporting all standard properties:

```scss
.sidebar_layout {
  display: flex;
  flex-direction: row;
  width: 100%;
  height: 100%;
}

.sidebar {
  width: 200px;
  flex-shrink: 0;
  padding: $space-md;
  background-color: rgba(0, 0, 0, 0.3);
}

.main_content {
  flex-grow: 1;
  padding: $space-lg;
  overflow: hidden;
}
```

### Grid Layouts

Puree supports CSS Grid via `grid-template-rows`, `grid-template-columns`, and `grid-auto-flow`:

```scss
.dashboard_grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  grid-template-rows: auto auto;
  gap: $space-md;
  padding: $space-lg;
}
```

For responsive adaptation, redefine grid columns at different `@media` breakpoints:

```scss
.card_grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: $space-md;
}

@media (min-width: 600px) {
  .card_grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (min-width: 900px) {
  .card_grid {
    grid-template-columns: 1fr 1fr 1fr;
  }
}
```

## Visual Hierarchy

### The Squint Test

Blur your eyes (or screenshot and blur). Can you still identify:
- The most important element?
- The second most important?
- Clear groupings?

If everything looks the same weight blurred, you have a hierarchy problem.

### Hierarchy Through Multiple Dimensions

Don't rely on size alone. Combine:

| Tool | Strong Hierarchy | Weak Hierarchy |
|------|------------------|----------------|
| **Size** | 3:1 ratio or more | <2:1 ratio |
| **Weight** | Bold vs Regular | Medium vs Regular |
| **Color** | High contrast | Similar tones |
| **Position** | Top/left (primary) | Bottom/right |
| **Space** | Surrounded by open space | Crowded |

**The best hierarchy uses 2-3 dimensions at once**: A heading that's larger, bolder, AND has more space above it.

### Cards Are Not Required

Cards are overused. Spacing and alignment create visual grouping naturally. Use cards only when content is truly distinct and actionable, items need visual comparison in a grid, or content needs clear interaction boundaries. **Never nest cards inside cards**—use spacing, typography, and subtle dividers for hierarchy within a card.

```scss
// Card with subtle boundary
.card {
  padding: $space-lg;
  background-color: rgba(26, 29, 36, 0.95);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

// Hierarchy within a card — use spacing, not nested cards
.card_header {
  padding: 0px 0px $space-sm 0px;
  font-size: 18px;
  font-weight: bold;
}

.card_body {
  padding: $space-sm 0px;
  font-size: 14px;
  color: rgba(181, 188, 199, 0.8);
}
```

## Optical Adjustments

Geometrically centered icons often look off-center. In Puree, use `--img-align-h` and `--img-align-v` to optically align images within containers. Use `--text-x` and `--text-y` to nudge text into optical alignment.

```scss
.icon_button {
  width: 40px;
  height: 40px;
  --img-align-h: center;
  --img-align-v: center;
}

// Nudge text to optically align with icon
.label_with_icon {
  --text-x: 2px;
  --text-align-v: center;
}
```

### Click Target Sizing

Interactive elements should be at least 32-40px in height for comfortable clicking. Use padding to expand the interactive area:

```scss
.toolbar_button {
  height: 36px;
  padding: 8px 16px;
  background-color: rgba(37, 40, 48, 0.95);
  border-radius: 6px;
}
```

## Depth & Elevation

Puree supports single `box-shadow` per element. Create a consistent elevation scale:

```scss
$shadow-sm: 0px 1px 3px rgba(0, 0, 0, 0.2);
$shadow-md: 0px 4px 12px rgba(0, 0, 0, 0.3);
$shadow-lg: 0px 10px 24px rgba(0, 0, 0, 0.4);

.floating_panel {
  box-shadow: $shadow-md;
  background-color: rgba(26, 29, 36, 0.98);
  border-radius: 8px;
}
```

**Key insight**: Shadows should be subtle—if you can clearly see it, it's probably too strong. In dark themes, lighter surface colors are often more effective than shadows for conveying elevation.

## Position: Absolute for Overlays

Use `position: absolute` for elements that need to overlay their parent:

```scss
.overlay_container {
  position: relative;
  width: 100%;
  height: 100%;
}

.tooltip {
  position: absolute;
  padding: 8px 12px;
  background-color: rgba(0, 0, 0, 0.9);
  border-radius: 4px;
}
```

**Note**: Puree does not support `z-index`. Render order follows YAML source order — later siblings render on top.

---

**Avoid**: Arbitrary spacing values outside your scale. Making all spacing equal (variety creates hierarchy). Creating hierarchy through size alone — combine size, weight, color, and space. Using `z-index` (not supported).
