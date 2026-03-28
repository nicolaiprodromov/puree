---
description: "Use when editing Puree SCSS/CSS files. Covers supported properties, Puree extensions, selectors, transitions, gradients, and what CSS features are NOT available."
applyTo: "**/*.scss"
---

# Puree SCSS Styling

Puree uses **standard CSS property names** compiled via SCSS (grass). GPU-rendered via ModernGL with Taffy/Stretchable layout engine.

## Puree Extensions (no CSS equivalent)

These use `--` prefix and **require `#{$var}` interpolation** for SCSS variables:

| Property         | Values                        | Purpose                    |
|------------------|-------------------------------|----------------------------|
| `--text-align-v` | `top`, `center`, `bottom`     | Vertical text alignment    |
| `--text-x`       | px value                      | Horizontal text offset     |
| `--text-y`       | px value                      | Vertical text offset       |
| `--img-align-h`  | `left`, `center`, `right`     | Image horizontal alignment |
| `--img-align-v`  | `top`, `center`, `bottom`     | Image vertical alignment   |

```scss
// CORRECT — interpolation required for variables in -- properties
--text-align-v: #{$alignment};
--text-x: #{$offset};

// WRONG — variable won't resolve
--text-align-v: $alignment;
```

## Animatable Properties (ONLY these 3)

`background-color`, `border-color`, `opacity`

`color` (text) changes instantly on hover/active — it is **not** transition-interpolated.

**Layout properties in `:hover`/`:active` are IGNORED** — no reflow on hover. Only visual properties above are respected.

```scss
.button {
  transition: background-color 0.2s ease, opacity 0.15s linear;
  &:hover {
    background-color: #353942;  // ✓ works
    opacity: 0.9;               // ✓ works
    width: 110px;               // ✗ IGNORED
    padding: 15px;              // ✗ IGNORED
  }
}
```

## Supported Selectors

| Selector              | Example            | Supported |
|-----------------------|--------------------|-----------|
| Class                 | `.foo`             | ✓         |
| ID                    | `#foo`             | ✓         |
| Universal             | `*`                | ✓         |
| Descendant            | `.a .b`            | ✓         |
| Child                 | `.a > .b`          | ✓         |
| Adjacent sibling      | `.a + .b`          | ✓         |
| General sibling       | `.a ~ .b`          | ✓         |
| Pseudo-class          | `:hover`, `:active`| ✓         |
| Multiple              | `.a, .b { }`       | ✓         |
| `:first-child`, `:last-child` |            | ✓         |
| `:nth-child(an+b)`   |                    | ✓         |
| `:not()`              |                    | ✓         |
| Attribute, `:is()`, `:where()`, `::before/after` | | ✗ |

## Gradients

```scss
// Linear gradients — N-stop supported
background: linear-gradient(90deg, #3498db, #2ecc71);
background: linear-gradient(135deg, #f00 0%, #00f 50%, #0f0 100%);

// Border gradients
border-image: linear-gradient(135deg, #3498db, #2ecc71);
border-width: 1px;
```

No radial or conic gradients.

## Box Shadow

Single shadow only (no comma-separated list):
```scss
box-shadow: 0px 10px 20px rgba(0,0,0,0.3);
```

## Borders

Per-side width supported. Per-side **colors** NOT supported (uniform `border-color` only).
```scss
border: 1px solid rgba(255,255,255,0.1);
border-bottom: 2px solid red;
border-width: 1px 2px 3px 4px;  // top right bottom left
```

## Inheritance

Only these inherit from parent: `color`, `font-size`, `text-align`, `font-family`, `font-weight`, `font-style`, `pointer-events`, `visibility`, `text-transform`, `line-height`, `letter-spacing`, `white-space`. Everything else must be set explicitly. No `inherit`/`initial`/`unset` keywords.

## Units & Functions

- **Supported**: `px`, `%`, `auto`
- **NOT supported**: `em`, `rem`, `vw`, `vh`, `fr`
- **NOT supported**: `calc()`, `clamp()`, `min()`, `max()`

## Display Values

`flex` (default), `grid`, `block`, `none` — no `inline`, `inline-flex`, `inline-block`

## Layout

Full flexbox: `flex-direction`, `flex-wrap`, `flex-grow/shrink/basis`, `align-items/self/content`, `justify-content/items/self`, `gap`
Grid: `grid-template-rows/columns`, `grid-auto-flow` (including `dense` variants), `grid-row/column`
Positioning: `relative`, `absolute` (no `fixed`, `sticky`)
Media queries: `@media (min-width: Npx)`, `@media (max-width: Npx)`, `@media (min-height: Npx)`, `@media (max-height: Npx)`

## SCSS Features

Variables (`$var`), nesting, mixins, `!default`, `var(--name)` with fallback, `@media` queries — all work.

## NOT Supported

`float`, `clear`, `z-index`, `transform`, `@keyframes`, `animation`, pseudo-elements (`::before`/`::after`), attribute selectors, `:is()`/`:where()`, per-side border colors

For full reference: [PUREE_VS_CSS.md](../../docs/PUREE_VS_CSS.md)
