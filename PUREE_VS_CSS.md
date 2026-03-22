# Puree vs Classic CSS — Exact Differences

This document covers every place where Puree diverges from standard CSS and browser layout. Use it as a translation guide.

---

## 1. Property Names

### Background / Fill Color

| Classic CSS | Puree |
|---|---|
| `background-color: red` | `background-color: red` ✅ (mapped automatically) |
| `color: red` | ⚠️ **DO NOT use** — in Puree `color` means background fill, not text color |

**Rule:** Use `background-color` in SCSS. Never use bare `color` for text. The cascade engine maps `background-color → color` internally.

---

### Text Color

| Classic CSS | Puree |
|---|---|
| `color: #fff` | `text-color: #fff` |

**Rule:** Text color is always `text-color`. The CSS `color` property is reserved for background fill.

---

### Font Size

| Classic CSS | Puree |
|---|---|
| `font-size: 14px` | `text-scale: 14px` |
| `font-size: 14px` | `font-size: 14px` ✅ (mapped automatically) |

Both work in SCSS. `font-size` is aliased to `text-scale` by the cascade engine.

---

### Text Alignment

| Classic CSS | Puree |
|---|---|
| `text-align: left` | `text-align-h: left` |
| `text-align: left` | `text-align: left` ✅ (mapped automatically) |
| *(no equivalent)* | `text-align-v: center` — vertical text alignment (`top`, `center`, `bottom`) |

**Rule:** Horizontal alignment maps automatically. Vertical alignment is Puree-only — use `text-align-v`.

---

### Image Alignment

| Classic CSS | Puree |
|---|---|
| `object-fit` / `object-position` | `img-align-h: center` (`left`, `center`, `right`) |
| *(no direct equivalent)* | `img-align-v: center` (`top`, `center`, `bottom`) |
| `opacity` on img | `img-opacity: 0.9` |

---

### Gradient Fill

| Classic CSS | Puree |
|---|---|
| `background: linear-gradient(135deg, #f00, #00f)` | `background-color: #f00; color-1: #00f; color-gradient-rot: 135deg` |

Puree gradients are always two-stop linear. `color` is stop 1, `color-1` is stop 2, `color-gradient-rot` is the angle in degrees. No multi-stop or radial gradients.

---

### Box Shadow

| Classic CSS | Puree |
|---|---|
| `box-shadow: 0px 10px 20px rgba(0,0,0,0.3)` | `box-shadow-color: rgba(0,0,0,0.3); box-shadow-offset: 0px 10px; box-shadow-blur: 20px` |

Shadow is split into three separate properties. Only one shadow per element (no comma-separated list).

---

### Border

| Classic CSS | Puree |
|---|---|
| `border: 1px solid rgba(255,255,255,0.1)` | `border-width: 1px; border-color: rgba(255,255,255,0.1)` |
| `border-radius: 16px` | `border-radius: 16px` ✅ same |
| `border-radius: 999px` | `border-radius: 999px` ✅ (pill shape) |

No `border-style` property — all borders are solid. Border color also supports gradients via `border-color-1` and `border-color-gradient-rot`.

---

### Hover & Active States

| Classic CSS | Puree |
|---|---|
| `.foo:hover { background-color: red }` | `.foo:hover { background-color: red }` ✅ same |
| `.foo:active { background-color: blue }` | `.foo:active { background-color: blue }` ✅ same |

**Only `background-color`, `color-1`, and `border-color` are respected in `:hover`/`:active` rules.** Layout properties (width, padding, margin) in `:hover` are ignored — Puree does not reflow on hover.

---

## 2. Layout Engine

Puree uses [Taffy](https://github.com/DioxusLabs/taffy) (via the `stretchable` Python binding), a Rust Flexbox/Grid engine. It is NOT the browser's layout engine.

### What works the same
- `display: flex`, `display: grid`, `display: none`
- `flex-direction`, `flex-wrap`, `flex-grow`, `flex-shrink`, `flex-basis`
- `align-items`, `align-self`, `align-content`
- `justify-content`, `justify-items`, `justify-self`
- `position: relative`, `position: absolute`
- `margin`, `padding` (px and % values, shorthand supported)
- `width`, `height` (px and %)
- `min-width`, `max-width`, `min-height`, `max-height`
- `overflow: hidden`
- `grid-template-rows`, `grid-template-columns`, `grid-auto-flow`

### What does NOT exist in Puree

| Classic CSS | Puree |
|---|---|
| `display: block`, `display: inline`, `display: inline-flex` | Only `flex`, `grid`, `none` |
| `float`, `clear` | ❌ Not supported |
| `z-index` | ❌ Not supported — draw order is strictly tree order |
| `transform`, `translate`, `rotate`, `scale` | ❌ Not supported |
| `transition`, `animation`, `@keyframes` | ❌ Not supported — no CSS animations |
| `overflow: scroll`, `overflow: auto`, `overflow: visible` | Only `hidden` |
| `calc()` | ❌ Not supported |
| `var(--custom-property)` | ❌ Use SCSS variables instead |
| `clamp()`, `min()`, `max()` | ❌ Not supported |
| `gap`, `row-gap`, `column-gap` | ❌ Not yet wired into the layout node |
| `text-overflow: ellipsis`, `white-space: nowrap` | ❌ Text always clips to the container |
| `line-height` | ❌ Line height is fixed at `text-scale × 1.2` |
| `letter-spacing` | ❌ Not supported |
| `font-weight`, `font-style` | ❌ Use a different font face via the `font:` YAML attribute |
| `text-decoration` | ❌ Not supported |
| `cursor` | ❌ Not supported |
| Multiple box shadows | ❌ Only one shadow per container |
| Multi-stop gradients, radial gradients | ❌ Only two-stop linear |
| Pseudo-elements `::before`, `::after` | ❌ Not supported |
| Media queries `@media` | ❌ Not supported |

---

## 3. CSS Selector Support

| Feature | Supported |
|---|---|
| Class selector `.foo` | ✅ |
| ID selector `#foo` | ✅ |
| Universal selector `*` | ✅ |
| Descendant combinator `.a .b` | ✅ |
| Child combinator `.a > .b` | ✅ |
| `:hover` pseudo-class | ✅ |
| `:active` pseudo-class | ✅ |
| Multiple selectors `.a, .b { }` | ✅ |
| Attribute selectors `[type="text"]` | ❌ |
| `:nth-child`, `:first-child`, etc. | ❌ |
| `:focus`, `:disabled`, `:checked` | ❌ |
| `::before`, `::after` | ❌ |
| `:not()`, `:is()`, `:where()` | ❌ |
| Sibling combinators `~`, `+` | ❌ |

---

## 4. Inheritance

Only three properties inherit from parent to child automatically:

- `text-color`
- `text-scale`
- `text-align-h`

Everything else must be set explicitly. There is no `inherit`, `initial`, or `unset` keyword.

---

## 5. Units

| Unit | Supported |
|---|---|
| `px` | ✅ |
| `%` | ✅ (relative to parent) |
| `auto` | ✅ (for margins/sizes) |
| `em`, `rem` | ❌ |
| `vw`, `vh`, `vmin`, `vmax` | ❌ |
| `fr` (grid fraction) | ❌ |

---

## 6. YAML Structure vs HTML

Containers are declared in YAML, not HTML. Key differences:

| HTML / CSS | Puree YAML |
|---|---|
| `<div class="foo">` | `my_node:` with `style: foo` in SCSS |
| `class="foo bar"` (multiple classes) | `class: foo bar` or `style: foo` + YAML key auto-added as class |
| Inline styles `style="color:red"` | Not supported — use SCSS only |
| `data-*` attributes | `data:` field for component reference only |
| `id="foo"` | Node IDs are auto-generated from YAML path: `shell_topbar_brand_copy` |

Every YAML key becomes part of its container's ID path AND is added as a CSS class automatically. So a YAML key `nav_overview` nested under `action_strip` → id `action_strip_nav_overview`, classes `[nav_overview, <namespace>]`.

---

## 7. Components

Puree components are YAML + SCSS pairs. They work like a scoped custom element:

```yaml
# Instantiate
my_button:
  data: '[action_chip]'
  chip_text: Click me
  chip_bg: rgba(100, 200, 255, 0.2)
```

```scss
// Component SCSS uses $variables with !default
$chip_bg: rgba(255,255,255,0.1) !default;
.action_chip { background-color: $chip_bg; }
```

- Selectors are **namespaced** at compile time — `.action_chip` becomes `.my_button` in the output
- SCSS `$variables` map to YAML params (passed at instantiation)
- No slot/template system — structure is fixed in the component YAML

---

## 8. Runtime / Interactivity

| Browser | Puree |
|---|---|
| `element.style.color = 'red'` | `container.set_property('color', 'rgba(...)`)` |
| `element.textContent = 'hi'` | `container.text = 'hi'; container.mark_dirty()` |
| `element.classList.add('active')` | ❌ No runtime class toggling |
| `addEventListener('click', fn)` | `container.click.append(fn)` |
| `addEventListener('mouseover', fn)` | `container.hover.append(fn)` |
| `addEventListener('scroll', fn)` | `container.scroll.append(fn)` |
| DOM reflow on property change | `mark_dirty()` triggers relayout on next frame |
| CSS transitions on property change | ❌ Changes are instant |
