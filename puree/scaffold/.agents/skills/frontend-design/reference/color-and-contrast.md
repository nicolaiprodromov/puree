# Color & Contrast

## Supported Color Formats in Puree

Puree's color parser supports these formats:

| Format | Example | Notes |
|--------|---------|-------|
| Hex | `#3498db`, `#fff` | 3 or 6 digit |
| `rgb()` | `rgb(52, 152, 219)` | Standard RGB |
| `rgba()` | `rgba(52, 152, 219, 0.8)` | RGB with alpha |
| `hsl()` | `hsl(204, 70%, 53%)` | Hue, saturation, lightness |
| Named | `red`, `white`, `transparent` | CSS named colors |

**Not supported**: `oklch()`, `color-mix()`, `light-dark()`, `hwb()`. Use SCSS color functions or manual hex/rgba values instead.

## Building Palettes with SCSS Variables

### Tinted Neutrals

**Pure gray is dead.** Add a subtle hint of your brand hue to all neutrals:

```scss
// Dead grays — no personality
$gray-100: #f2f2f2;
$gray-900: #1a1a1a;

// Warm-tinted grays (add brand warmth)
$gray-100: #f4f2f0;
$gray-900: #1c1a18;

// Cool-tinted grays (tech, professional)
$gray-100: #f0f2f5;
$gray-900: #181a1f;
```

The tint is subtle but perceptible. It creates subconscious cohesion between your brand color and your UI.

### Palette Structure

Define your palette as SCSS variables at the top of your stylesheet:

```scss
// Primary
$primary: #3498db;
$primary-light: #5dade2;
$primary-dark: #2176ad;

// Surfaces
$surface-1: rgba(15, 16, 20, 0.95);
$surface-2: rgba(26, 29, 36, 0.95);
$surface-3: rgba(37, 40, 48, 0.95);

// Text
$text-primary: rgba(245, 248, 250, 0.95);
$text-secondary: rgba(181, 188, 199, 0.8);
$text-muted: rgba(120, 130, 145, 0.6);

// Semantic
$success: #2ecc71;
$error: #e74c3c;
$warning: #f39c12;
$info: #3498db;

// Borders
$border-subtle: rgba(255, 255, 255, 0.08);
$border-strong: rgba(255, 255, 255, 0.15);
```

A complete system needs:

| Role | Purpose | Example |
|------|---------|---------|
| **Primary** | Brand, CTAs, key actions | 1 color, 3-5 shades |
| **Neutral** | Text, backgrounds, borders | 5-9 shade scale |
| **Semantic** | Success, error, warning, info | 4 colors, 2-3 shades each |
| **Surface** | Panels, cards, overlays | 2-3 elevation levels |

**Skip secondary/tertiary unless you need them.** Most addons work fine with one accent color. Adding more creates decision fatigue and visual noise.

### The 60-30-10 Rule (Applied Correctly)

This rule is about **visual weight**, not pixel count:

- **60%**: Neutral backgrounds, base surfaces
- **30%**: Secondary colors—text, borders, inactive states
- **10%**: Accent—CTAs, highlights, active states

The common mistake: using the accent color everywhere because it's "the brand color." Accent colors work *because* they're rare. Overuse kills their power.

## Contrast & Readability

### Contrast Guidelines

| Content Type | Minimum Ratio | Target |
|--------------|---------------|--------|
| Body text | 4.5:1 | 7:1 |
| Large text (18px+ or 14px bold) | 3:1 | 4.5:1 |
| UI components, icons | 3:1 | 4.5:1 |
| Non-essential decorations | None | None |

### Dangerous Color Combinations

These commonly fail contrast or cause readability issues:

- Light gray text on white (the #1 readability fail)
- **Gray text on any colored background**—gray looks washed out and dead on color. Use a darker shade of the background color, or a tinted transparent
- Red text on green background (or vice versa)—8% of men can't distinguish these
- Blue text on red background (vibrates visually)
- Thin light text on images (unpredictable contrast)

### Never Use Pure Gray or Pure Black

Pure gray (`#808080`) and pure black (`#000`) don't exist in nature—real shadows and surfaces always have a color cast. Even a tiny tint toward your brand hue is enough to feel natural without being obviously colored.

```scss
// Avoid
$bg: #000000;
$text: #808080;

// Better — tinted toward blue
$bg: #0f1014;
$text: #8890a0;
```

## Gradients in Puree

Puree supports `linear-gradient()` for backgrounds and `border-image` for gradient borders:

```scss
// Background gradient
.hero_panel {
  background: linear-gradient(135deg, #1a1d24, #2c3e50);
}

// Multi-stop gradient
.accent_bar {
  background: linear-gradient(90deg, #3498db, #2ecc71 50%, #e74c3c);
}

// Border gradient
.feature_card {
  border-image: linear-gradient(135deg, #3498db, #2ecc71);
  border-width: 1px;
}
```

**Not supported**: radial gradients, conic gradients.

## Theming in Puree

### Multiple Themes via YAML

Puree supports themes through the YAML config. Define multiple themes and switch between them with `selected_theme`:

```yaml
app:
  selected_theme: dark_theme
  default_theme: dark_theme

  theme:
    - name: dark_theme
      default_font: NeueMontreal-Regular
      styles:
        - static/dark.scss
      root:
        class: root_container
        # ... UI structure

    - name: light_theme
      default_font: NeueMontreal-Regular
      styles:
        - static/light.scss
      root:
        class: root_container
        # ... same UI structure, different stylesheet
```

### Dark Mode Design Principles

Most Blender addons use dark themes to match Blender's UI. Dark mode requires specific design decisions:

| Light Theme | Dark Theme |
|-------------|------------|
| Shadows for depth | Lighter surfaces for depth |
| Dark text on light bg | Light text on dark bg (reduce font weight) |
| Vibrant accents | Desaturate accents slightly |
| White backgrounds | Never pure black—use dark gray (#0f1014 to #1a1d24) |

```scss
// Dark theme depth via surface color layers
$surface-base: #0f1014;
$surface-raised: #1a1d24;    // "Higher" = lighter
$surface-overlay: #252830;

// Lighter text on dark — use slightly thinner weight
.body_text {
  color: rgba(220, 225, 235, 0.9);
}
```

## Alpha Transparency as a Tool

In Puree, `rgba()` transparency is useful for layered surfaces and borders:

```scss
$border-subtle: rgba(255, 255, 255, 0.08);
$overlay-bg: rgba(0, 0, 0, 0.6);
$hover-highlight: rgba(52, 152, 219, 0.15);
```

However, heavy use of transparency can create unpredictable contrast. Define explicit colors for each surface level instead of relying on stacked alpha layers.

---

**Avoid**: Relying on color alone to convey information. Creating palettes without clear roles for each color. Using pure black (#000) for large areas. Using unsupported color functions (oklch, color-mix).
