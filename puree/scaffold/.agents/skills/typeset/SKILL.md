---
name: typeset
description: Improve Puree typography by fixing font choices, hierarchy, sizing, weight consistency, and readability in YAML/SCSS. Makes text feel intentional and polished.
user-invocable: true
argument-hint: 'Describe the panel or text-heavy component to improve (e.g. "info panel typography", "sidebar labels")'
---

Assess and improve typography that feels generic, inconsistent, or poorly structured — turning default-looking text into intentional, well-crafted type.

## MANDATORY PREPARATION

Use the frontend-design skill — it contains design principles, anti-patterns, and the **Context Gathering Protocol**. Follow the protocol before proceeding — if no design context exists yet, you MUST run teach-impeccable first.

---

## Assess Current Typography

Analyze what's weak or generic about the current type:

1. **Font choices**:
   - Are we using invisible defaults or generic fonts?
   - Does the font match the brand personality? (A playful brand shouldn't use a corporate typeface)
   - Are there too many font families? (More than 2-3 is almost always a mess)
   - Are fonts being loaded correctly via YAML `font:` attribute from the `fonts/` directory?

2. **Hierarchy**:
   - Can you tell headings from body from captions at a glance?
   - Are font sizes too close together? (14px, 15px, 16px = muddy hierarchy)
   - Are weight contrasts strong enough? (normal vs bold is the primary tool)

3. **Sizing & scale**:
   - Is there a consistent type scale, or are sizes arbitrary?
   - Does body text meet minimum readability? (14px+ for Puree panels)
   - Are SCSS variables used for font sizes, or are values scattered as raw pixels?

4. **Readability**:
   - Are line lengths comfortable? (45-75 characters ideal where possible)
   - Is `line-height` appropriate for the font and context?
   - Is there enough contrast between text and background?

5. **Consistency**:
   - Are the same elements styled the same way throughout?
   - Are font weights used consistently? (Not bold in one section, normal in another for the same role)
   - Is `letter-spacing` intentional or default everywhere?

**CRITICAL**: The goal isn't to make text "fancier" — it's to make it clearer, more readable, and more intentional. Good typography is invisible; bad typography is distracting.

## Plan Typography Improvements

Create a systematic plan:

- **Font selection**: Do fonts need replacing? What fits the brand/context? Check what's available in the `fonts/` directory.
- **Type scale**: Establish a modular scale (e.g., 1.25 ratio) with clear hierarchy using SCSS variables
- **Weight strategy**: Which weights serve which roles? (normal for body, bold for headings — or whatever fits)
- **Spacing**: `line-height`, `letter-spacing`, and margins between typographic elements

## Improve Typography Systematically

### Font Selection

If fonts need replacing:
- Choose fonts from the `fonts/` directory that reflect the brand personality
- Load fonts via the YAML `font:` attribute on text nodes
- Pair with genuine contrast (serif + sans, geometric + humanist) — or use a single family in multiple weights

```yaml
# Heading with distinctive font
section_title:
  font: NeueMontreal-Bold
  class: section_title

# Body with readable font
description:
  font: NeueMontreal-Regular
  class: body_text
```

### Establish Hierarchy

Build a clear type scale using SCSS variables:

```scss
// Type scale (1.25 ratio)
$font-size-xs: 11px;   // captions, metadata
$font-size-sm: 12px;   // secondary text
$font-size-md: 14px;   // body text
$font-size-lg: 18px;   // subheadings
$font-size-xl: 24px;   // headings
$font-size-xxl: 36px;  // display / hero text

.heading { font-size: $font-size-xl; font-weight: bold; }
.subheading { font-size: $font-size-lg; font-weight: bold; }
.body_text { font-size: $font-size-md; font-weight: normal; }
.caption { font-size: $font-size-xs; color: $text-secondary; }
```

- **5 sizes cover most needs**: caption, secondary, body, subheading, heading
- **Use a consistent ratio** between levels (1.25, 1.333, or 1.5)
- **Combine dimensions**: Size + weight + color + space for strong hierarchy — don't rely on size alone
- All sizes in **px** — Puree does not support `em`, `rem`, `clamp()`, or viewport units

### Fix Readability

- Adjust `line-height` per context: tighter for headings (1.1-1.2), looser for body (1.5-1.7)
- Increase `line-height` slightly for light-on-dark text
- Ensure body text is at least 14px for Puree panel readability

```scss
.body_text {
  font-size: $font-size-md;
  line-height: 1.6;
  color: $text-primary;
}

.heading {
  font-size: $font-size-xl;
  line-height: 1.15;
  letter-spacing: -0.5px;
  color: $text-primary;
}
```

### Refine Details

- Apply `letter-spacing`: slightly open for uppercase text, default or tight for large display text
- Use semantic SCSS variable names (`$font-size-body`, `$font-size-heading`), not value names (`$font-16`)
- Use `text-transform: uppercase` for labels that need it
- Leverage `text-shadow` sparingly for depth on critical text

### Weight Consistency

- Define clear roles for each weight and stick to them
- Don't use more than 2-3 weights (normal and bold cover most needs in Puree)
- Load only the font files you actually use (each file adds to addon size)

```scss
// Clear weight roles
.label { font-weight: bold; font-size: $font-size-sm; letter-spacing: 0.5px; text-transform: uppercase; }
.body { font-weight: normal; font-size: $font-size-md; }
.emphasis { font-style: italic; }
```

**NEVER**:
- Use more than 2-3 font families
- Pick sizes arbitrarily — commit to a scale defined in SCSS variables
- Set body text below 12px (hard to read in Blender panels)
- Use decorative/display fonts for body text
- Default to generic fonts when personality matters
- Pair fonts that are similar but not identical (two geometric sans-serifs)
- Use `em`, `rem`, `clamp()`, or `vw` units — Puree only supports `px` and unitless `line-height`
- Reference `font-family` in SCSS — fonts are loaded via YAML `font:` attribute

## Verify Typography Improvements

- **Hierarchy**: Can you identify heading vs body vs caption instantly?
- **Readability**: Is body text comfortable to read?
- **Consistency**: Are same-role elements styled identically throughout?
- **Personality**: Does the typography reflect the brand?
- **Scale compliance**: Are all sizes from the SCSS variable scale?

Remember: Typography is the foundation of interface design — it carries the majority of information. Getting it right is the highest-leverage improvement you can make.
