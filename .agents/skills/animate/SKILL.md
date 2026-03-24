---
name: animate
description: Review a Puree feature and enhance it with purposeful transitions and state changes that improve usability.
user-invocable: true
argument-hint: [TARGET=<component or interaction, e.g. "nav_bar hover">]
---

Analyze a Puree feature and strategically add transitions and state changes that enhance understanding, provide feedback, and create delight.

## MANDATORY PREPARATION

Use the frontend-design skill — it contains design principles, anti-patterns, and the **Context Gathering Protocol**. Follow the protocol before proceeding — if no design context exists yet, you MUST run teach-impeccable first.

---

## Understand Puree's Animation Model

Puree supports **CSS transitions only** — no `@keyframes`, no programmatic animation libraries. Work within these constraints:

- **Animatable properties**: `background-color`, `color` (text), `border-color`, `opacity`
- **Timing functions**: `ease`, `linear`, `ease-in`, `ease-out`, `ease-in-out`
- **Multi-property transitions**: `transition: background-color 0.2s ease, opacity 0.3s linear`
- **Transition delay**: Supported via `transition-delay`
- **State triggers**: `:hover` and `:active` pseudo-classes
- **Runtime triggers**: `container.set_property()` + `mark_dirty()` from Python

Layout properties (`width`, `padding`, `margin`) **cannot** be animated and are ignored in `:hover`/`:active` rules.

## Assess Transition Opportunities

Analyze where transitions would improve the experience:

1. **Identify static areas**:
   - **Missing feedback**: Buttons and interactive elements with no hover/active states
   - **Jarring state changes**: Instant color or visibility swaps that feel abrupt
   - **Unclear interactivity**: Elements that don't signal they're clickable
   - **Lack of polish**: Functional but lifeless interactions

2. **Understand the context**:
   - What's the personality? (Playful vs serious, energetic vs calm)
   - Who's the audience? (Power users who want speed? New users who need guidance?)
   - What matters most? (One signature interaction vs consistent micro-feedback?)

If any of these are unclear from the codebase, ask the user directly to clarify what you cannot infer.

## Plan Transition Strategy

Create a purposeful transition plan:

- **Feedback layer**: Which interactive elements need hover/active acknowledgment?
- **State layer**: Which color or opacity changes need smoothing?
- **Hierarchy layer**: Can transitions guide attention to what matters?

**IMPORTANT**: A few well-tuned transitions beat scattered effects everywhere. Focus on high-impact moments.

## Implement Transitions

Add motion systematically across these categories:

### Hover State Feedback

Provide visual acknowledgment when users hover over interactive elements:

```scss
// Subtle background shift on hover
.nav_item {
  background-color: transparent;
  transition: background-color 0.2s ease;

  &:hover {
    background-color: rgba(255, 255, 255, 0.08);
  }
}

// Color shift for text links
.action_link {
  color: $text-secondary;
  transition: color 0.2s ease;

  &:hover {
    color: $accent;
  }
}
```

### Click/Active Feedback

Give tactile feedback when elements are pressed:

```scss
// Button press feedback via opacity and color
.btn_primary {
  background-color: $accent;
  opacity: 1.0;
  transition: background-color 0.1s ease, opacity 0.1s ease;

  &:hover {
    background-color: lighten($accent, 8%);
  }

  &:active {
    background-color: darken($accent, 10%);
    opacity: 0.85;
  }
}
```

### State Color Transitions

Smooth out color changes triggered by Python at runtime:

```scss
// Status indicator with smooth color change
.status_badge {
  background-color: $neutral;
  transition: background-color 0.3s ease-out, color 0.3s ease-out;
}
```

```python
# In script.py — transition happens automatically via SCSS
def update_status(container, status):
    colors = {'ok': 'rgba(46,204,113,1)', 'error': 'rgba(231,76,60,1)'}
    container.set_property('background-color', colors.get(status, 'rgba(149,165,166,1)'))
    container.mark_dirty()
```

### Opacity Transitions

Use opacity for smooth show/reveal effects:

```scss
// Fade-in effect for content
.panel_content {
  opacity: 0.0;
  transition: opacity 0.3s ease-in-out;
}

// Python sets opacity to 1.0 when ready — the transition does the rest
```

### Border Feedback

Use border-color transitions for input-like elements or selection states:

```scss
.input_field {
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: border-color 0.2s ease;

  &:hover {
    border-color: rgba(255, 255, 255, 0.3);
  }

  &:active {
    border-color: $accent;
  }
}
```

### Multi-Property Transitions

Combine multiple animatable properties for richer effects:

```scss
.card {
  background-color: $surface;
  border: 1px solid rgba(255, 255, 255, 0.05);
  opacity: 1.0;
  transition: background-color 0.2s ease, border-color 0.2s ease, opacity 0.2s ease;

  &:hover {
    background-color: lighten($surface, 5%);
    border-color: rgba(255, 255, 255, 0.15);
  }
}
```

## Timing & Easing Guidelines

**Durations by purpose:**
- **100-150ms**: Instant feedback (button press, active state)
- **200-300ms**: State changes (hover, color shifts)
- **300-500ms**: Larger state transitions (panel reveals, status changes)

**Easing choices:**
- `ease-out` — best default, natural deceleration
- `ease-in-out` — good for color transitions that feel smooth
- `linear` — use for opacity fades
- `ease-in` — rarely needed, feels sluggish for most UI

**Exit transitions should be faster than entrances.** Use ~75% of enter duration.

**NEVER**:
- Use durations over 500ms for interactive feedback — it feels laggy
- Add transitions without purpose — every transition needs a reason
- Transition everything — transition fatigue makes interfaces feel sluggish
- Forget `mark_dirty()` after runtime property changes — the transition won't trigger
- Try to animate layout properties (width, height, padding) — Puree ignores them in `:hover`/`:active`
- Attempt `@keyframes` or `animation` — Puree only supports `transition`

## Verify Quality

Test transitions thoroughly:

- **Feels natural**: Timing and easing feel organic, not robotic
- **Appropriate timing**: Not too fast (jarring) or too slow (laggy)
- **Consistent**: Similar interactions have similar transition timing
- **Doesn't block**: Users can interact during/after transitions
- **Adds value**: Makes the interface clearer or more polished

Remember: In Puree, transitions are your only animation tool — use them with precision. A well-timed 200ms color transition on hover communicates more than flashy effects ever could. Animate with purpose and restraint.