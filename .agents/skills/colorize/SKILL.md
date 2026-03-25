---
name: colorize
description: Add strategic color to Puree UI (YAML/SCSS) that is too monochromatic or lacks visual interest. Makes interfaces more engaging and expressive.
user-invocable: true
argument-hint: 'Describe the component or panel section to add color to (e.g. "status indicators", "sidebar nav")'
---

Strategically introduce color to Puree designs that are too monochromatic, gray, or lacking in visual warmth and personality.

## MANDATORY PREPARATION

Use the frontend-design skill — it contains design principles, anti-patterns, and the **Context Gathering Protocol**. Follow the protocol before proceeding — if no design context exists yet, you MUST run teach-impeccable first. Additionally gather: existing brand colors.

---

## Assess Color Opportunity

Analyze the current state and identify opportunities:

1. **Understand current state**:
   - **Color absence**: Pure grayscale? Limited neutrals? One timid accent?
   - **Missed opportunities**: Where could color add meaning, hierarchy, or delight?
   - **Context**: What's appropriate for this domain and audience?
   - **Brand**: Are there existing brand colors we should use?

2. **Identify where color adds value**:
   - **Semantic meaning**: Success (green), error (red), warning (yellow/orange), info (blue)
   - **Hierarchy**: Drawing attention to important elements
   - **Categorization**: Different sections, types, or states
   - **Emotional tone**: Warmth, energy, trust, creativity
   - **Wayfinding**: Helping users navigate and understand structure
   - **Delight**: Moments of visual interest and personality

If any of these are unclear from the codebase, ask the user directly to clarify what you cannot infer.

**CRITICAL**: More color ≠ better. Strategic color beats rainbow vomit every time. Every color should have a purpose.

## Plan Color Strategy

Create a purposeful color introduction plan:

- **Color palette**: What colors match the brand/context? (Choose 2-4 colors max beyond neutrals)
- **Dominant color**: Which color owns 60% of colored elements?
- **Accent colors**: Which colors provide contrast and highlights? (30% and 10%)
- **Application strategy**: Where does each color appear and why?

Define all colors as SCSS variables for consistency and maintainability:

```scss
// Primary palette
$accent: #3498db;
$accent-hover: lighten($accent, 10%);
$accent-active: darken($accent, 10%);

// Semantic colors
$success: #2ecc71;
$error: #e74c3c;
$warning: #f39c12;
$info: #3498db;

// Neutrals (tinted, not pure gray)
$neutral-100: #f5f5f7;
$neutral-500: #6b6b7b;
$neutral-900: #1a1a2e;
```

**IMPORTANT**: Color should enhance hierarchy and meaning, not create chaos. Less is more when it matters more.

## Introduce Color Strategically

Add color systematically across these dimensions:

### Semantic Color

- **State indicators**:
  - Success: Green tones (`$success`)
  - Error: Red/pink tones (`$error`)
  - Warning: Orange/amber tones (`$warning`)
  - Info: Blue tones (`$info`)
  - Neutral: Gray/slate for inactive states

- **Status badges**: Colored backgrounds or borders for states (active, pending, completed, etc.)

```scss
.status_active {
  background-color: rgba($success, 0.15);
  color: $success;
  border: 1px solid rgba($success, 0.3);
}

.status_error {
  background-color: rgba($error, 0.15);
  color: $error;
  border: 1px solid rgba($error, 0.3);
}
```

### Accent Color Application
- **Primary actions**: Color the most important buttons
- **Interactive text**: Add color to clickable text elements
- **Icons**: Colorize key icons for recognition and personality
- **Headers/titles**: Add color to section headers or key labels
- **Hover states**: Introduce color on interaction via `:hover`

```scss
.primary_btn {
  background-color: $accent;
  color: #fff;
  transition: background-color 0.2s ease;

  &:hover {
    background-color: $accent-hover;
  }
}
```

### Background & Surfaces
- **Tinted backgrounds**: Replace pure gray with warm or cool tinted neutrals
- **Colored sections**: Use subtle background colors to separate areas
- **Gradient backgrounds**: Add depth with intentional `linear-gradient` (not generic purple-blue)
- **Cards & surfaces**: Tint cards or surfaces slightly for warmth

```scss
.panel {
  background: linear-gradient(180deg, $neutral-900, darken($neutral-900, 3%));
}

.section_highlight {
  background-color: rgba($accent, 0.05);
}
```

### Borders & Accents
- **Accent borders**: Add colored left/top borders to cards or sections
- **Colored dividers**: Subtle colored dividers instead of gray lines
- **Border gradients**: Use `border-image: linear-gradient()` for emphasis

```scss
.feature_card {
  border-left: 3px solid $accent;
  border-radius: 8px;
}

.highlight_card {
  border-image: linear-gradient(135deg, $accent, $success);
  border-width: 2px;
}
```

### Typography Color
- **Colored headings**: Use brand colors for section headings (maintain contrast)
- **Highlight text**: Color for emphasis or categories
- **Labels & tags**: Small colored labels for metadata

```scss
.section_title {
  color: $accent;
  font-size: 18px;
  font-weight: bold;
}

.tag {
  color: $accent;
  background-color: rgba($accent, 0.1);
  border-radius: 4px;
  padding: 2px 8px;
}
```

## Balance & Refinement

Ensure color addition improves rather than overwhelms:

### Maintain Hierarchy
- **Dominant color** (60%): Primary brand color or most used accent
- **Secondary color** (30%): Supporting color for variety
- **Accent color** (10%): High contrast for key moments
- **Neutrals** (remaining): Gray/black/white for structure

### Contrast & Readability
- **Contrast ratios**: Ensure text has sufficient contrast against backgrounds (4.5:1 minimum)
- **Don't rely on color alone**: Use opacity, borders, or text alongside color for state
- **Test for color blindness**: Verify red/green combinations work for all users

### Cohesion
- **Consistent palette**: Use colors from SCSS variables only, not arbitrary hex values
- **Systematic application**: Same color meanings throughout (green always = success)
- **Temperature consistency**: Warm palette stays warm, cool stays cool

**NEVER**:
- Use every color in the rainbow (choose 2-4 colors beyond neutrals)
- Apply color randomly without semantic meaning
- Put gray text on colored backgrounds — use a darker shade of the background color or `rgba()` with transparency instead
- Use pure gray for neutrals — add subtle color tint for sophistication
- Use pure black (`#000`) or pure white (`#fff`) for large areas
- Use color as the only state indicator
- Make everything colorful (defeats the purpose)
- Default to purple-blue gradients (AI slop aesthetic)
- Use `oklch()` or `color-mix()` — Puree supports hex, `rgb()`, `rgba()`, and named colors

## Verify Color Addition

Test that colorization improves the experience:

- **Better hierarchy**: Does color guide attention appropriately?
- **Clearer meaning**: Does color help users understand states/categories?
- **More engaging**: Does the interface feel warmer and more inviting?
- **Still readable**: Do all color combinations have sufficient contrast?
- **Not overwhelming**: Is color balanced and purposeful?
- **SCSS variables used**: Are all colors defined as variables, not hard-coded?

Remember: Color is emotional and powerful. Use it to create warmth, guide attention, communicate meaning, and express personality. But restraint and strategy matter more than saturation and variety. Be colorful, but be intentional.
