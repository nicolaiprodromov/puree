---
name: bolder
description: Amplify safe or boring designs to make them more visually interesting and stimulating. Increases impact while maintaining usability.
user-invocable: true
argument-hint: [TARGET=<component or panel section>]
---

Increase visual impact and personality in designs that are too safe, generic, or visually underwhelming, creating more engaging and memorable Puree interfaces.

## MANDATORY PREPARATION

Use the frontend-design skill — it contains design principles, anti-patterns, and the **Context Gathering Protocol**. Follow the protocol before proceeding — if no design context exists yet, you MUST run teach-impeccable first.

---

## Assess Current State

Analyze what makes the design feel too safe or boring:

1. **Identify weakness sources**:
   - **Generic choices**: Default fonts, basic colors, standard layouts
   - **Timid scale**: Everything is medium-sized with no drama
   - **Low contrast**: Everything has similar visual weight
   - **Static**: No hover states, no transitions, no life
   - **Predictable**: Standard patterns with no surprises
   - **Flat hierarchy**: Nothing stands out or commands attention

2. **Understand the context**:
   - What's the brand personality? (How far can we push?)
   - What's the purpose? (Creative tools can be bolder than data panels)
   - Who's the audience? (What will resonate?)
   - What are the constraints? (Blender addon context, panel sizes)

If any of these are unclear from the codebase, ask the user directly to clarify what you cannot infer.

**CRITICAL**: "Bolder" doesn't mean chaotic or garish. It means distinctive, memorable, and confident. Think intentional drama, not random chaos.

**WARNING - AI SLOP TRAP**: When making things "bolder," AI defaults to the same tired tricks: cyan/purple gradients, glassmorphism, neon accents on dark backgrounds, gradient text on metrics. These are the OPPOSITE of bold—they're generic. Review ALL the DON'T guidelines in the frontend-design skill before proceeding. Bold means distinctive, not "more effects."

## Plan Amplification

Create a strategy to increase impact while maintaining coherence:

- **Focal point**: What should be the hero moment? (Pick ONE, make it amazing)
- **Personality direction**: Maximalist chaos? Elegant drama? Playful energy? Dark moody? Choose a lane.
- **Risk budget**: How experimental can we be? Push boundaries within constraints.
- **Hierarchy amplification**: Make big things BIGGER, small things smaller (increase contrast)

**IMPORTANT**: Bold design must still be usable. Impact without function is just decoration.

## Amplify the Design

Systematically increase impact across these dimensions:

### Typography Amplification
- **Replace generic fonts**: Swap default fonts for distinctive choices loaded via YAML `font:` attribute from the `fonts/` directory
- **Extreme scale**: Create dramatic size jumps (3x-5x differences, not 1.5x)
- **Weight contrast**: Pair bold with light weights, not semibold with regular
- **Unexpected choices**: Display fonts for headlines, condensed/extended widths

```yaml
# Bold headline with dramatic scale
hero_title:
  font: NeueMontreal-Bold
  class: hero_title
```

```scss
.hero_title {
  font-size: 64px;
  color: $accent;
  letter-spacing: -1px;
}

.body_text {
  font-size: 14px;
  font-weight: normal;
  color: $text-secondary;
}
```

### Color Intensification
- **Increase saturation**: Shift to more vibrant, energetic colors (but not neon)
- **Bold palette**: Introduce unexpected color combinations — avoid the purple-blue gradient AI slop
- **Dominant color strategy**: Let one bold color own 60% of the design
- **Sharp accents**: High-contrast accent colors that pop
- **Tinted neutrals**: Replace pure grays with tinted grays that harmonize with your palette
- **Rich gradients**: Intentional multi-stop gradients (not generic purple-to-blue)

```scss
$bold-accent: #e74c3c;
$surface-tinted: #1a1a2e;

.feature_card {
  background: linear-gradient(135deg, $surface-tinted, darken($surface-tinted, 5%));
  border: 2px solid $bold-accent;
  border-radius: 12px;
}
```

### Spatial Drama
- **Extreme scale jumps**: Make important elements 3-5x larger than surroundings
- **Asymmetric layouts**: Replace centered, balanced layouts with tension-filled asymmetry
- **Generous space**: Use whitespace dramatically (64-128px gaps, not 8-16px)

### Visual Effects
- **Dramatic shadows**: Large, soft `box-shadow` for elevation

```scss
.hero_panel {
  box-shadow: 0px 20px 60px rgba(0, 0, 0, 0.4);
  border-radius: 16px;
}
```

- **Background treatments**: Gradients, colored surfaces, intentional contrast
- **Borders & frames**: Thick borders, decorative `border-image` gradients
- **Custom elements**: Illustrative imagery that reinforces brand

### Transitions & State Changes
- **Confident hover states**: Noticeable color shifts on hover, not timid 5% changes

```scss
.action_btn {
  background-color: $bold-accent;
  color: #fff;
  transition: background-color 0.2s ease, opacity 0.15s ease;

  &:hover {
    background-color: lighten($bold-accent, 10%);
  }

  &:active {
    background-color: darken($bold-accent, 15%);
    opacity: 0.9;
  }
}
```

- **Opacity reveals**: Use opacity transitions for content that appears on interaction

### Composition Boldness
- **Hero moments**: Create clear focal points with dramatic treatment
- **Unexpected proportions**: Try 70/30, 80/20 splits instead of safe 50/50
- **Full-bleed elements**: Use full container width for impact

**NEVER**:
- Add effects randomly without purpose (chaos ≠ bold)
- Sacrifice readability for aesthetics (body text must be readable)
- Make everything bold (then nothing is bold — need contrast)
- Overwhelm with transitions (transition fatigue is real)
- Copy trendy aesthetics blindly (bold means distinctive, not derivative)
- Try to use `transform`, `@keyframes`, or `z-index` — they don't exist in Puree

## Verify Quality

Ensure amplification maintains usability and coherence:

- **NOT AI slop**: Does this look like every other AI-generated "bold" design? If yes, start over.
- **Still functional**: Can users accomplish tasks without distraction?
- **Coherent**: Does everything feel intentional and unified?
- **Memorable**: Will users remember this experience?
- **Performant**: Do transitions run smoothly?

**The test**: If you showed this to someone and said "AI made this bolder," would they believe you immediately? If yes, you've failed. Bold means distinctive, not "more AI effects."

Remember: Bold design is confident design. It takes risks, makes statements, and creates memorable experiences. But bold without strategy is just loud. Be intentional, be dramatic, be unforgettable.
