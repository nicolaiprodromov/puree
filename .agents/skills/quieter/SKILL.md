---
name: quieter
description: Tone down overly bold or visually aggressive Puree designs. Reduces intensity while maintaining design quality and impact.
user-invocable: true
argument-hint: [TARGET=<component or panel section>]
---

Reduce visual intensity in Puree designs that are too bold, aggressive, or overstimulating, creating a more refined and approachable aesthetic without losing effectiveness.

## MANDATORY PREPARATION

Use the frontend-design skill — it contains design principles, anti-patterns, and the **Context Gathering Protocol**. Follow the protocol before proceeding — if no design context exists yet, you MUST run teach-impeccable first.

---

## Assess Current State

Analyze what makes the design feel too intense:

1. **Identify intensity sources**:
   - **Color saturation**: Overly bright or saturated colors
   - **Contrast extremes**: Too much high-contrast juxtaposition
   - **Visual weight**: Too many bold, heavy elements competing
   - **Transition excess**: Too many transitions or overly dramatic color shifts
   - **Complexity**: Too many visual elements, patterns, or decorations
   - **Scale**: Everything is large and loud with no hierarchy

2. **Understand the context**:
   - What's the purpose? (Creative tool vs data panel vs utility)
   - Who's the audience? (Some contexts need energy)
   - What's working? (Don't throw away good ideas)
   - What's the core message? (Preserve what matters)

If any of these are unclear from the codebase, ask the user directly to clarify what you cannot infer.

**CRITICAL**: "Quieter" doesn't mean boring or generic. It means refined, sophisticated, and easier on the eyes. Think luxury, not laziness.

## Plan Refinement

Create a strategy to reduce intensity while maintaining impact:

- **Color approach**: Desaturate or shift to more sophisticated tones?
- **Hierarchy approach**: Which elements should stay bold (very few), which should recede?
- **Simplification approach**: What can be removed entirely?
- **Sophistication approach**: How can we signal quality through restraint?

**IMPORTANT**: Great quiet design is harder than great bold design. Subtlety requires precision.

## Refine the Design

Systematically reduce intensity across these dimensions:

### Color Refinement
- **Reduce saturation**: Shift from fully saturated to 70-85% saturation in SCSS variables
- **Soften palette**: Replace bright colors with muted, sophisticated tones
- **Reduce color variety**: Use fewer SCSS color variables more thoughtfully
- **Neutral dominance**: Let neutrals do more work, use color as accent (10% rule)
- **Gentler contrasts**: High contrast only where it matters most
- **Tinted grays**: Use warm or cool tinted grays instead of pure gray — adds sophistication without loudness
- **Never gray on color**: If you have gray text on a colored background, use a darker shade of that color or `rgba()` transparency instead

```scss
// Before: too intense
$accent: #ff3333;
$surface: #000000;

// After: refined
$accent: #c0392b;
$surface: #1a1a2e;
```

### Visual Weight Reduction
- **Typography**: Reduce font weights (bold → normal where appropriate), decrease sizes where they're excessive
- **Hierarchy through subtlety**: Use weight, size, and space instead of color and boldness
- **White space**: Increase breathing room, reduce density
- **Borders & lines**: Reduce thickness, decrease opacity, or remove entirely

```scss
// Before: heavy
.heading {
  font-size: 32px;
  font-weight: bold;
  color: $accent;
}

// After: refined
.heading {
  font-size: 24px;
  font-weight: bold;
  color: $text-primary;
}
```

### Simplification
- **Remove decorative elements**: Gradients, shadows, backgrounds that don't serve hierarchy or function
- **Simplify shapes**: Reduce extreme `border-radius` values
- **Reduce layering**: Flatten visual hierarchy where possible
- **Clean up effects**: Reduce or remove `box-shadow`, multiple borders, intense gradients

### Transition Reduction
- **Shorten durations**: Use shorter, more subtle timing (150-200ms instead of 400ms)
- **Reduce scope**: Only transition what needs transitioning — remove decorative transitions
- **Subtle color shifts**: Smaller color differences on `:hover` (5-10% shift, not 30%)
- **Remove transitions entirely** if they're not serving a clear purpose

```scss
// Before: dramatic
.card {
  transition: background-color 0.4s ease, border-color 0.4s ease, opacity 0.4s ease;

  &:hover {
    background-color: lighten($surface, 15%);
    border-color: $accent;
  }
}

// After: subtle
.card {
  transition: background-color 0.2s ease;

  &:hover {
    background-color: lighten($surface, 3%);
  }
}
```

### Composition Refinement
- **Reduce scale jumps**: Smaller contrast between sizes creates calmer feeling
- **Even out spacing**: Replace extreme spacing variations with consistent rhythm
- **Consistent alignment**: Remove asymmetric flourishes that feel random

**NEVER**:
- Make everything the same size/weight (hierarchy still matters)
- Remove all color (quiet ≠ grayscale)
- Eliminate all personality (maintain character through refinement)
- Sacrifice usability for aesthetics (functional elements still need clear affordances)
- Make everything small and light (some anchors needed)

## Verify Quality

Ensure refinement maintains quality:

- **Still functional**: Can users still accomplish tasks easily?
- **Still distinctive**: Does it have character, or is it generic now?
- **Better for extended use**: Is it easier on the eyes for long sessions?
- **Sophistication**: Does it feel more refined and premium?

Remember: Quiet design is confident design. It doesn't need to shout. Less is more, but less is also harder. Refine with precision and maintain intentionality.
