---
name: delight
description: Add moments of joy, personality, and unexpected touches that make Puree UI (YAML/SCSS/Python) memorable and enjoyable to use. Elevates functional to delightful.
user-invocable: true
argument-hint: 'Describe the component or interaction to add delight to (e.g. "empty state", "success confirmation")'
---

Identify opportunities to add moments of joy, personality, and unexpected polish that transform functional Puree interfaces into delightful experiences.

## MANDATORY PREPARATION

Use the frontend-design skill — it contains design principles, anti-patterns, and the **Context Gathering Protocol**. Follow the protocol before proceeding — if no design context exists yet, you MUST run teach-impeccable first. Additionally gather: what's appropriate for the domain (playful vs professional vs quirky vs elegant).

---

## Assess Delight Opportunities

Identify where delight would enhance (not distract from) the experience:

1. **Find natural delight moments**:
   - **Success states**: Completed actions (save, export, publish)
   - **Empty states**: First-time experiences, onboarding
   - **Loading states**: Waiting periods that could feel more engaging
   - **Interactions**: Hover states, clicks, state changes
   - **Errors**: Softening frustrating moments
   - **Discovery**: Hidden touches for curious users

2. **Understand the context**:
   - What's the brand personality? (Playful? Professional? Quirky? Elegant?)
   - Who's the audience? (Tech-savvy Blender users? Creative professionals?)
   - What's the emotional context? (Accomplishment? Exploration? Frustration?)
   - What's appropriate? (Data tool ≠ creative tool)

3. **Define delight strategy**:
   - **Subtle sophistication**: Refined hover transitions (luxury brands)
   - **Playful personality**: Whimsical illustrations and copy (consumer apps)
   - **Helpful surprises**: Anticipating needs before users ask (productivity tools)
   - **Sensory richness**: Satisfying color transitions, smooth state changes (creative tools)

If any of these are unclear from the codebase, ask the user directly to clarify what you cannot infer.

**CRITICAL**: Delight should enhance usability, never obscure it. If users notice the delight more than accomplishing their goal, you've gone too far.

## Delight Principles

Follow these guidelines:

### Delight Amplifies, Never Blocks
- Delight moments should be quick (transitions under 300ms)
- Never delay core functionality for delight
- Make delight subtle and unintrusive
- Respect user's time and task focus

### Surprise and Discovery
- Hide delightful details for users to discover
- Reward exploration and curiosity
- Don't announce every delight moment
- Let users share discoveries with others

### Appropriate to Context
- Match delight to emotional moment (celebrate success, empathize with errors)
- Respect the user's state (don't be playful during critical errors)
- Match brand personality and audience expectations

### Compound Over Time
- Delight should remain fresh with repeated use
- Vary responses (not same feedback every time)
- Build anticipation through patterns

## Delight Techniques

Add personality and joy through these methods:

### Hover & Click Transitions

Puree's transition system is your primary tool for micro-delight:

```scss
// Satisfying button feedback via color and opacity
.action_btn {
  background-color: $accent;
  color: #fff;
  opacity: 1.0;
  transition: background-color 0.15s ease-out, opacity 0.1s ease;

  &:hover {
    background-color: lighten($accent, 8%);
  }

  &:active {
    background-color: darken($accent, 12%);
    opacity: 0.85;
  }
}

// Subtle glow on hover via border-color
.card {
  border: 1px solid rgba(255, 255, 255, 0.05);
  transition: border-color 0.25s ease, background-color 0.25s ease;

  &:hover {
    border-color: rgba($accent, 0.3);
    background-color: rgba($accent, 0.03);
  }
}
```

### State Change Delight

Use Python + transitions for satisfying state changes:

```python
def on_complete(container):
    # Smooth transition to success color (SCSS transition handles the animation)
    container.set_property('background-color', 'rgba(46, 204, 113, 0.15)')
    container.set_property('border-color', 'rgba(46, 204, 113, 0.5)')
    container.text = "Done!"
    container.mark_dirty()
```

```scss
.task_item {
  background-color: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: background-color 0.3s ease-out, border-color 0.3s ease-out, color 0.3s ease-out;
}
```

### Personality in Copy

**Playful error messages** (when appropriate for the brand):
```
"No results found"
→ "Nothing here yet. Time to create something."

"Export failed"
→ "Export hit a snag. Check your file path and try again."
```

**Encouraging empty states**:
```
"No projects"
→ "Your workspace is ready. Create your first project."
```

**IMPORTANT**: Match copy personality to brand. Serious tools can be warm without being wacky.

### Opacity Reveals

Use opacity transitions for content that appears on demand:

```scss
.tooltip_content {
  opacity: 0;
  transition: opacity 0.2s ease-in;
}
```

```python
def show_tooltip(container):
    tooltip = app.find("tooltip_content")
    tooltip.set_property('opacity', '1.0')
    tooltip.mark_dirty()
```

### Visual Personality
- **Custom illustrations**: Use `img:` in YAML for empty states, error states, branding
- **Background gradients**: Subtle, intentional `linear-gradient` for warmth and depth
- **Color themes**: Time-of-day or contextual color shifts via Python runtime

### Celebration Moments

**Success celebrations** using color transitions:

```scss
.success_flash {
  background-color: transparent;
  transition: background-color 0.3s ease-out;
}
```

```python
def celebrate(container):
    container.set_property('background-color', 'rgba(46, 204, 113, 0.2)')
    container.mark_dirty()
    # A separate timer callback could reset it back to transparent
```

### Loading & Waiting States

**Make waiting feel intentional**:
- Rotate loading messages that are specific to your product (not generic AI filler)
- Use opacity transitions to smoothly reveal content when ready
- Show progress indication through color changes

**WARNING**: Avoid cliched loading messages like "Herding pixels" or "Teaching robots to dance." Write messages specific to what your product actually does.

**NEVER**:
- Delay core functionality for delight
- Force users through delightful moments (keep them subtle)
- Use delight to hide poor UX
- Overdo it (less is more)
- Make every interaction delightful (special moments should be special)
- Sacrifice performance for delight
- Be inappropriate for context (read the room)
- Try to use `@keyframes`, `transform`, or JS animation libraries — Puree only supports `transition`

## Verify Delight Quality

Test that delight actually delights:

- **Doesn't annoy**: Still pleasant after the 100th time?
- **Doesn't block**: Can users proceed without waiting?
- **Performant**: Transitions are smooth, no lag
- **Appropriate**: Matches brand and context
- **Enhances**: Makes the experience better, not just different

Remember: Delight is the difference between a tool and an experience. Add personality, surprise users positively, and create moments worth noticing. But always respect usability — delight should enhance, never obstruct.
