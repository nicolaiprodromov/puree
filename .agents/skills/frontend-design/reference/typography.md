# Typography

## Classic Typography Principles

### Vertical Rhythm

Your `line-height` should be the base unit for ALL vertical spacing. If body text has `line-height: 1.5` on `16px` type (= 24px), spacing values should be multiples of 24px. This creates subconscious harmony—text and space share a mathematical foundation.

### Modular Scale & Hierarchy

The common mistake: too many font sizes that are too close together (14px, 15px, 16px, 18px...). This creates muddy hierarchy.

**Use fewer sizes with more contrast.** A 5-size system covers most needs:

| Role | Size (px) | Use Case |
|------|-----------|----------|
| xs | 10-11px | Captions, metadata |
| sm | 12-13px | Secondary UI, labels |
| base | 14-16px | Body text |
| lg | 20-24px | Subheadings, lead text |
| xl+ | 32-64px | Headlines, display text |

Popular ratios: 1.25 (major third), 1.333 (perfect fourth), 1.5 (perfect fifth). Pick one and commit.

**Puree supports `px`, `rem`, and `em` for font sizes.** `rem` resolves against root font-size (default 16px), `em` against parent font-size. Viewport units (`vw`, `vh`, `vmin`, `vmax`) and `calc()` also work.

### Readability & Measure

Constrain text containers to a comfortable reading width using `max-width` in px (roughly 500-650px for body text). Line-height scales inversely with line length—narrow columns need tighter leading, wide columns need more.

**Non-obvious**: Increase `line-height` for light text on dark backgrounds. The perceived weight is lighter, so text needs more breathing room. Add 0.05-0.1 to your normal line-height.

## Font Selection & Pairing

### Loading Fonts in Puree

Puree loads fonts from the `fonts/` directory in your project root. Each font variant (weight, style) is a separate file. Reference fonts in YAML via the `font:` attribute on any node:

```yaml
title:
  class: heading
  text: "Welcome"
  font: NeueMontreal-Bold

subtitle:
  class: subheading
  text: "A Puree Interface"
  font: NeueMontreal-Italic
```

The `default_font` in your theme config sets the fallback for all text:

```yaml
app:
  theme:
    - name: my_theme
      default_font: NeueMontreal-Regular
```

Font weight and style (`font-weight: bold`, `font-style: italic`) in SCSS select the closest available font face from loaded fonts. For best results, include Regular, Bold, and Italic variants at minimum.

### Choosing Distinctive Fonts

Place `.ttf` or `.otf` files in the `fonts/` directory. Choose fonts that match your interface's personality.

**Font pairing suggestions by aesthetic:**
- **Clean/modern**: Instrument Sans + Source Serif
- **Editorial/premium**: Fraunces + DM Sans
- **Technical/precise**: JetBrains Mono + Inter
- **Warm/friendly**: Nunito Sans + Lora

### Pairing Principles

**The non-obvious truth**: You often don't need a second font. One well-chosen font family in multiple weights creates cleaner hierarchy than two competing typefaces. Only add a second font when you need genuine contrast (e.g., display headlines + body serif).

When pairing, contrast on multiple axes:
- Serif + Sans (structure contrast)
- Geometric + Humanist (personality contrast)
- Condensed display + Wide body (proportion contrast)

**Never pair fonts that are similar but not identical** (e.g., two geometric sans-serifs). They create visual tension without clear hierarchy.

## Typography in SCSS

### Defining a Type Scale

Use SCSS variables to create a consistent type scale:

```scss
$text-xs: 11px;
$text-sm: 13px;
$text-base: 15px;
$text-lg: 20px;
$text-xl: 28px;
$text-2xl: 40px;

.body_text {
  font-size: $text-base;
  line-height: 1.5;
  color: rgba(200, 205, 215, 0.95);
}

.heading {
  font-size: $text-xl;
  font-weight: bold;
  letter-spacing: -0.5px;
  color: rgba(245, 248, 250, 1);
}

.caption {
  font-size: $text-xs;
  color: rgba(140, 148, 160, 0.8);
  text-transform: uppercase;
  letter-spacing: 1px;
}
```

### Supported Text Properties

Puree supports these standard CSS text properties:

| Property | Example | Notes |
|----------|---------|-------|
| `font-size` | `font-size: 16px` | px only |
| `font-weight` | `font-weight: bold` | `normal`, `bold` |
| `font-style` | `font-style: italic` | `normal`, `italic` |
| `color` | `color: rgba(255,255,255,0.9)` | Text color |
| `text-align` | `text-align: center` | Horizontal alignment |
| `text-decoration` | `text-decoration: underline` | `none`, `underline` |
| `letter-spacing` | `letter-spacing: 2px` | px value |
| `line-height` | `line-height: 1.5` | Unitless multiplier |
| `white-space` | `white-space: nowrap` | `normal`, `nowrap` |
| `text-overflow` | `text-overflow: ellipsis` | `clip`, `ellipsis` |
| `text-shadow` | `text-shadow: 1px 1px 3px rgba(0,0,0,0.5)` | Single shadow |
| `text-transform` | `text-transform: uppercase` | `uppercase`, `lowercase` |

**Puree extensions** (no CSS equivalent):
- `--text-align-v: center` — vertical text alignment (`top`, `center`, `bottom`)
- `--text-x: 5px` — horizontal text offset
- `--text-y: -2px` — vertical text offset

### Token Architecture

Use SCSS variables named semantically (`$text-body`, `$text-heading`), not by value (`$font-16`). Include size scale, weights, line-heights, and letter-spacing in your variable system.

## Readability Considerations

- **Minimum 14px body text** in Blender panels — smaller strains eyes at typical monitor distances.
- **Use adequate line-height**: 1.4-1.6 for body text, 1.1-1.3 for headings.
- **Increase line-height on dark backgrounds**: Light text on dark needs more breathing room — add 0.05-0.1 to normal line-height.
- **Use `text-overflow: ellipsis` with `white-space: nowrap`** for text that may overflow narrow panels.

---

**Avoid**: More than 2-3 font families per project. Using decorative fonts for body text. Identical font sizes with no hierarchy. Forgetting to set `default_font` in the theme config.
