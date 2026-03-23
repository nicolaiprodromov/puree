# Puree vs Classic CSS — Exact Differences

This document covers every place where Puree diverges from standard CSS and browser layout. **As of the CSS parity update, SCSS property names are identical to standard CSS** — only YAML structure and Python scripting differ.

---

## 1. Property Names — Now CSS-Standard ✅

### Background / Fill Color

| CSS | Puree SCSS | Notes |
|---|---|---|
| `background-color: red` | `background-color: red` | ✅ Identical |
| `color: red` | `color: red` | ✅ Identical — means **text color** |

Both now work exactly as in standard CSS. Internal property names match CSS — no translation layers.

### Text Properties

| CSS | Puree SCSS | Notes |
|---|---|---|
| `color: #fff` | `color: #fff` | ✅ Text color |
| `font-size: 14px` | `font-size: 14px` | ✅ Identical |
| `text-align: left` | `text-align: left` | ✅ Identical (horizontal) |
| `font-weight: bold` | `font-weight: bold` | ✅ `normal`, `bold` |
| `font-style: italic` | `font-style: italic` | ✅ `normal`, `italic` |
| `text-decoration: underline` | `text-decoration: underline` | ✅ `none`, `underline` |
| `letter-spacing: 2px` | `letter-spacing: 2px` | ✅ Identical |
| `line-height: 1.5` | `line-height: 1.5` | ✅ Unitless multiplier |
| `white-space: nowrap` | `white-space: nowrap` | ✅ `normal`, `nowrap` |
| `text-overflow: ellipsis` | `text-overflow: ellipsis` | ✅ `clip`, `ellipsis` |
| `text-shadow: 1px 1px 3px rgba(0,0,0,0.5)` | `text-shadow: 1px 1px 3px rgba(0,0,0,0.5)` | ✅ Single shadow |

**Puree text extensions (no CSS equivalent):**

| Extension | Purpose | Values |
|---|---|---|
| `--text-align-v` | Vertical text alignment | `top`, `center`, `bottom` |
| `--text-x` | Horizontal text offset | px value |
| `--text-y` | Vertical text offset | px value |

Font selection uses YAML `font:` attribute (not CSS `font-family`). Font weight/style select the closest available font face from loaded fonts.

---

### Puree Extensions (use `--` prefix)

These properties have no CSS equivalent and use the standard custom property `--` prefix:

| Extension Property | Purpose | Accepted Values |
|---|---|---|
| `--text-align-v` | Vertical text alignment | `top`, `center`, `bottom` |
| `--text-x`, `--text-y` | Text position offset | px |
| `--img-align-h` | Image horizontal alignment | `left`, `center`, `right` |
| `--img-align-v` | Image vertical alignment | `top`, `center`, `bottom` |

**SCSS variables in `--` properties require interpolation:** `--text-x: #{$offset};`

---

### Image Opacity

| CSS | Puree SCSS | Notes |
|---|---|---|
| `opacity: 0.9` | `opacity: 0.9` | ✅ Maps to image opacity |

---

### Gradient Fill

| CSS | Puree SCSS |
|---|---|
| `background: linear-gradient(135deg, #f00, #00f)` | `background: linear-gradient(135deg, #f00, #00f)` ✅ |
| `background: linear-gradient(90deg, red, blue 50%, green)` | `background: linear-gradient(90deg, red, blue 50%, green)` ✅ |

The `background: linear-gradient()` shorthand is fully parsed including N-stop gradients with optional `%` positions. `background-image: linear-gradient()` is also supported as a CSS alias. Multi-stop gradients are pre-rendered into a GPU texture; 2-stop gradients use fast GPU-side interpolation.

Hover/click states each support independent gradients:
```scss
.btn:hover { background: linear-gradient(90deg, #3498db, #2ecc71); }
```

No radial or conic gradients.

---

### Box Shadow

| CSS | Puree SCSS |
|---|---|
| `box-shadow: 0px 10px 20px rgba(0,0,0,0.3)` | `box-shadow: 0px 10px 20px rgba(0,0,0,0.3)` ✅ |

The `box-shadow` shorthand is now parsed automatically. Only one shadow per element (no comma-separated list).

---

### Border

| CSS | Puree SCSS |
|---|---|
| `border: 1px solid rgba(255,255,255,0.1)` | `border: 1px solid rgba(255,255,255,0.1)` ✅ |
| `border-width: 1px` | `border-width: 1px` ✅ |
| `border-width: 1px 2px 3px 4px` | `border-width: 1px 2px 3px 4px` ✅ (top right bottom left) |
| `border-top: 2px solid red` | `border-top: 2px solid red` ✅ |
| `border-right: 1px solid blue` | `border-right: 1px solid blue` ✅ |
| `border-bottom: 3px solid green` | `border-bottom: 3px solid green` ✅ |
| `border-left: 4px solid white` | `border-left: 4px solid white` ✅ |
| `border-radius: 16px` | `border-radius: 16px` ✅ |
| `border-top-left-radius: 8px` | `border-top-left-radius: 8px` ✅ |
| `border-top-right-radius: 8px` | `border-top-right-radius: 8px` ✅ |
| `border-bottom-right-radius: 8px` | `border-bottom-right-radius: 8px` ✅ |
| `border-bottom-left-radius: 8px` | `border-bottom-left-radius: 8px` ✅ |
| `border-radius: 8px 16px 4px 12px` | `border-radius: 8px 16px 4px 12px` ✅ |

No `border-style` — all borders are solid. Per-side border **colors** are not yet supported (use a uniform `border-color`). Border gradients use `border-image: linear-gradient()`:

```scss
.card { border-image: linear-gradient(135deg, #3498db, #2ecc71); border-width: 1px; }
```

---

### Transitions

| CSS | Puree SCSS |
|---|---|
| `transition: background-color 0.2s ease` | `transition: background-color 0.2s ease` ✅ |
| `transition: color 0.3s ease-in-out` | `transition: color 0.3s ease-in-out` ✅ |
| `transition: background-color 0.2s ease, opacity 0.3s linear` | ✅ Multi-property transitions supported |

**Animatable properties:** `background-color`, `color` (text), `border-color`, `opacity`

**Timing functions:** `ease`, `linear`, `ease-in`, `ease-out`, `ease-in-out`

`transition-delay` is supported. Full CSS animations (`@keyframes`, `animation`) are not supported.

---

### Hover & Active States

| CSS | Puree SCSS |
|---|---|
| `.foo:hover { background-color: red }` | `.foo:hover { background-color: red }` ✅ |
| `.foo:active { background-color: blue }` | `.foo:active { background-color: blue }` ✅ |

**Only visual properties are respected in `:hover`/`:active` rules.** Layout properties (width, padding, margin) in `:hover` are ignored — Puree does not reflow on hover.

---

## 2. Layout Engine

Puree uses [Taffy](https://github.com/DioxusLabs/taffy) (via `stretchable`), a Rust Flexbox/Grid engine.

### What works the same
- `display: flex`, `display: grid`, `display: block`, `display: none`
- `flex-direction`, `flex-wrap`, `flex-grow`, `flex-shrink`, `flex-basis`
- `align-items`, `align-self`, `align-content`
- `justify-content`, `justify-items`, `justify-self`
- `position: relative`, `position: absolute`
- `margin`, `padding` (px and %)
- `width`, `height` (px and %)
- `min-width`, `max-width`, `min-height`, `max-height`
- `overflow: hidden`
- `overflow-x`, `overflow-y`
- `box-sizing: border-box/content-box`
- `visibility: hidden/visible`
- `pointer-events: none/auto`
- `text-transform: uppercase/lowercase`
- `var(--name)` / `var(--name, fallback)` — CSS custom properties resolved by the cascade
- `@media (min-width: Npx)`, `@media (max-width: Npx)` queries
- `grid-template-rows`, `grid-template-columns`, `grid-auto-flow`

### What does NOT exist
- `display: inline`, `display: inline-flex` — only `flex`, `grid`, `block`, `none`
- `float`, `clear`, `z-index`, `transform`
- `@keyframes` animations — use `transition` for simple state changes
- `calc()`, `clamp()`, `min()`, `max()`
- `em`, `rem`, `vw`, `vh`, `fr` units
- Pseudo-elements (`::before`, `::after`)
- Per-side border colors (uniform `border-color` only)
- Radial/conic gradients

---

## 3. CSS Selector Support

| Feature | Supported |
|---|---|
| `.foo` class selector | ✅ |
| `#foo` ID selector | ✅ |
| `*` universal | ✅ |
| `.a .b` descendant | ✅ |
| `.a > .b` child | ✅ |
| `:hover`, `:active` | ✅ |
| `.a, .b { }` multiple selectors | ✅ |
| Attribute selectors, `:nth-child`, sibling combinators | ❌ |
| `:not()`, `:is()`, `:where()` | ❌ |

---

## 4. Inheritance

Inherited properties (same as CSS):
- `color` (text color)
- `font-size`
- `text-align`

Everything else must be set explicitly. No `inherit`/`initial`/`unset` keywords.

---

## 5. YAML Structure vs HTML

| HTML | Puree YAML |
|---|---|
| `<div class="foo">` | `my_node:` with `class: foo` |
| `class="foo bar"` | `class: foo bar` |
| `id="foo"` | Auto-generated from YAML path |
| `<div style="...">` | Not supported — use SCSS only |
| `data-*` attributes | `data:` for component reference only |

---

## 6. Runtime / Interactivity

| Browser | Puree |
|---|---|
| `element.style.backgroundColor = 'red'` | `container.set_property('background-color', 'rgba(...)')` |
| `element.style.color = 'red'` | `container.set_property('color', 'rgba(...)')` |
| `element.textContent = 'hi'` | `container.text = 'hi'; container.mark_dirty()` |
| `addEventListener('click', fn)` | `container.click.append(fn)` |
| `addEventListener('mouseover', fn)` | `container.hover.append(fn)` |
| DOM reflow on property change | `mark_dirty()` triggers relayout |
| CSS transitions | ✅ Supported for `background-color`, `color`, `border-color`, `opacity` — multi-property via `transition: a 0.2s, b 0.3s` |
| `element.style.background = 'linear-gradient(...)'` | `container.set_property('background', 'linear-gradient(90deg, rgba(0,0,0,0.8), rgba(0,0,0,0))')` |
