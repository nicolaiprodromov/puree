# Responsive Design

## Adaptive Layout in Puree

Puree interfaces run inside Blender panels, which can vary in size as users resize regions. Puree supports `@media` queries to adapt layout to different panel widths.

**Supported queries**:
- `@media (min-width: Npx)` — apply styles when panel is at least N pixels wide
- `@media (max-width: Npx)` — apply styles when panel is at most N pixels wide

**Not supported**: `pointer`, `hover`, `prefers-reduced-motion`, `prefers-color-scheme`, `orientation` media features. No `env()`, no container queries.

## Content-Driven Breakpoints

Don't pick arbitrary breakpoints — let your content tell you where the layout breaks. Start narrow, stretch until the design breaks, add a breakpoint there. Three breakpoints usually suffice for Blender panel layouts:

```scss
// Narrow panel — single column
.content_grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

// Medium panel — two columns
@media (min-width: 500px) {
  .content_grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }
}

// Wide panel — three columns with sidebar
@media (min-width: 800px) {
  .content_grid {
    grid-template-columns: 200px 1fr 1fr;
    gap: 20px;
  }
}
```

## Layout Adaptation Patterns

### Sidebar Collapse

At narrow widths, collapse a sidebar into vertical stacking:

```scss
.app_layout {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
}

@media (min-width: 600px) {
  .app_layout {
    flex-direction: row;
  }
}

.sidebar {
  width: 100%;
  padding: 8px;
}

@media (min-width: 600px) {
  .sidebar {
    width: 220px;
    flex-shrink: 0;
    padding: 16px;
  }
}
```

### Content Reflow

Adapt content density — wider panels can show more detail:

```scss
.item_label {
  font-size: 12px;
  white-space: nowrap;
  text-overflow: ellipsis;
}

@media (min-width: 500px) {
  .item_label {
    font-size: 14px;
    white-space: normal;
  }
}
```

### Grid Column Adaptation

Use grid with breakpoints to change column count:

```scss
.card_grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  padding: 12px;
}

@media (min-width: 450px) {
  .card_grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (min-width: 700px) {
  .card_grid {
    grid-template-columns: 1fr 1fr 1fr;
    gap: 16px;
    padding: 16px;
  }
}
```

## Flexbox as the Primary Layout Tool

Flexbox handles most responsive needs without breakpoints. `flex-wrap: wrap` allows items to reflow naturally:

```scss
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px;
}

.toolbar_item {
  flex-grow: 1;
  min-width: 80px;
  height: 36px;
}
```

Use `flex-grow`, `flex-shrink`, and `flex-basis` to control how elements distribute space:

```scss
.panel_left {
  flex-basis: 200px;
  flex-shrink: 0;
}

.panel_main {
  flex-grow: 1;
  min-width: 0; // Prevent overflow
}
```

## Images in Different Panel Sizes

Puree loads images via the `img:` YAML attribute. Images don't have `srcset` or responsive variants — use `--img-align-h` and `--img-align-v` for positioning, and constrain the container size:

```scss
.logo {
  width: 48px;
  height: 48px;
  --img-align-h: center;
  --img-align-v: center;
}

@media (min-width: 600px) {
  .logo {
    width: 80px;
    height: 80px;
  }
}
```

## Units

Puree supports `px`, `%`, `rem`, `em`, `vw`, `vh`, `vmin`, `vmax`, and `calc()` units. `fr`, `clamp()`, `min()`, `max()` are NOT supported.

- `rem` resolves against root font-size (default 16px), `em` against parent font-size
- `vw`/`vh` = 1% of viewport width/height; `vmin`/`vmax` = 1% of smaller/larger dimension
- `calc()` supports `+` and `-` operators with mixed units (e.g. `calc(100% - 20px)`)

- Use `%` for fluid widths that adapt to parent size (`width: 100%`, `width: 50%`)
- Use `px` for fixed sizes, spacing, font sizes, and borders
- Combine both: `width: 100%` with `max-width: 800px` and `min-width: 300px`

## Testing Panel Sizes

Test your interface at different panel widths in Blender by resizing the addon's region. Key widths to verify:
- **Narrow** (~250-350px): Minimum usable size
- **Medium** (~500-600px): Comfortable single-column
- **Wide** (~800px+): Multi-column layouts

---

**Avoid**: Assuming a fixed panel width. Hiding critical functionality at narrow widths — adapt the layout instead. Using unsupported units (`fr`). Using unsupported media features (pointer, hover).
