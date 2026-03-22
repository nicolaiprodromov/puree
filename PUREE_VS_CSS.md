# Puree vs Classic CSS — Exact Differences

This document covers every place where Puree diverges from standard CSS and browser layout. **As of the CSS parity update, SCSS property names are identical to standard CSS** — only YAML structure and Python scripting differ.

---

## 1. Property Names — Now CSS-Standard ✅

### Background / Fill Color

| CSS | Puree SCSS | Notes |
|---|---|---|
| `background-color: red` | `background-color: red` | ✅ Identical |
| `color: red` | `color: red` | ✅ Identical — means **text color** |

Both now work exactly as in standard CSS. The cascade engine maps `background-color` → internal `color`, and `color` → internal `text-color`.

---

### Text Properties

| CSS | Puree SCSS | Notes |
|---|---|---|
| `color: #fff` | `color: #fff` | ✅ Text color |
| `font-size: 14px` | `font-size: 14px` | ✅ Identical |
| `text-align: left` | `text-align: left` | ✅ Identical (horizontal) |

---

### Puree Extensions (use `--` prefix)

These properties have no CSS equivalent and use the standard custom property `--` prefix:

| Extension Property | Purpose | Accepted Values |
|---|---|---|
| `--text-align-v` | Vertical text alignment | `top`, `center`, `bottom` |
| `--color-1` | Second gradient stop (fill) | Any color value |
| `--color-gradient-rot` | Gradient angle | Degrees, e.g., `135deg` |
| `--text-color-1` | Text gradient second stop | Any color value |
| `--text-color-gradient-rot` | Text gradient angle | Degrees |
| `--img-align-h` | Image horizontal alignment | `left`, `center`, `right` |
| `--img-align-v` | Image vertical alignment | `top`, `center`, `bottom` |
| `--border-color-1` | Border gradient second stop | Any color value |
| `--border-color-gradient-rot` | Border gradient angle | Degrees |

**SCSS variables in `--` properties require interpolation:** `--color-1: #{$my_var};`

---

### Image Opacity

| CSS | Puree SCSS | Notes |
|---|---|---|
| `opacity: 0.9` | `opacity: 0.9` | ✅ Maps to image opacity |

---

### Gradient Fill

| CSS | Puree SCSS |
|---|---|
| `background: linear-gradient(135deg, #f00, #00f)` | `background-color: #f00; --color-1: #00f; --color-gradient-rot: 135deg` |

Puree gradients are always two-stop linear. `background-color` is stop 1, `--color-1` is stop 2, `--color-gradient-rot` is the angle. No multi-stop or radial gradients.

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
| `border: 1px solid rgba(255,255,255,0.1)` | `border-width: 1px; border-color: rgba(255,255,255,0.1)` |
| `border-radius: 16px` | `border-radius: 16px` ✅ |

No `border-style` — all borders are solid. Border gradients via `--border-color-1`.

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
- `display: flex`, `display: grid`, `display: none`
- `flex-direction`, `flex-wrap`, `flex-grow`, `flex-shrink`, `flex-basis`
- `align-items`, `align-self`, `align-content`
- `justify-content`, `justify-items`, `justify-self`
- `position: relative`, `position: absolute`
- `margin`, `padding` (px and %)
- `width`, `height` (px and %)
- `min-width`, `max-width`, `min-height`, `max-height`
- `overflow: hidden`
- `grid-template-rows`, `grid-template-columns`, `grid-auto-flow`

### What does NOT exist
- `display: block/inline/inline-flex` — only `flex`, `grid`, `none`
- `float`, `clear`, `z-index`, `transform`
- `transition`, `animation`, `@keyframes`
- `calc()`, `var()`, `clamp()`, `min()`, `max()`
- `em`, `rem`, `vw`, `vh`, `fr` units
- Media queries, pseudo-elements
- `text-overflow`, `white-space`, `line-height`, `letter-spacing`
- `font-weight`, `font-style` — use different font face via YAML `font:` attribute

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
| CSS transitions | ❌ Changes are instant |
