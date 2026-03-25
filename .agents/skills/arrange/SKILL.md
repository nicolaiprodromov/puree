---
name: arrange
description: Improve Puree layout, spacing, and visual rhythm in YAML/SCSS. Fixes monotonous grids, inconsistent spacing, and weak visual hierarchy to create intentional compositions.
user-invocable: true
argument-hint: 'Describe the panel or layout section to improve (e.g. "main toolbar grid", "settings panel spacing")'
---

Assess and improve layout and spacing that feels monotonous, crowded, or structurally weak — turning generic arrangements into intentional, rhythmic compositions.

## MANDATORY PREPARATION

Use the frontend-design skill — it contains design principles, anti-patterns, and the **Context Gathering Protocol**. Follow the protocol before proceeding — if no design context exists yet, you MUST run teach-impeccable first.

---

## Assess Current Layout

Analyze what's weak about the current spatial design:

1. **Spacing**:
   - Is spacing consistent or arbitrary? (Random padding/margin values)
   - Is all spacing the same? (Equal padding everywhere = no rhythm)
   - Are related elements grouped tightly, with generous space between groups?

2. **Visual hierarchy**:
   - Apply the squint test: blur your (metaphorical) eyes — can you still identify the most important element, second most important, and clear groupings?
   - Is hierarchy achieved effectively? (Space and weight alone can be enough — but is the current approach working?)
   - Does whitespace guide the eye to what matters?

3. **Structure**:
   - Is there a clear underlying structure, or does the layout feel random?
   - Are identical card grids used everywhere? (Icon + heading + text, repeated endlessly)
   - Is everything centered? (Left-aligned with asymmetric layouts feels more designed, but not a hard and fast rule)

4. **Rhythm & variety**:
   - Does the layout have visual rhythm? (Alternating tight/generous spacing)
   - Is every section structured the same way? (Monotonous repetition)
   - Are there intentional moments of surprise or emphasis?

5. **Density**:
   - Is the layout too cramped? (Not enough breathing room)
   - Is the layout too sparse? (Excessive whitespace without purpose)
   - Does density match the content type? (Data-dense UIs need tighter spacing; tool panels need more air)

**CRITICAL**: Layout problems are often the root cause of interfaces feeling "off" even when colors and fonts are fine. Space is a design material — use it with intention.

## Plan Layout Improvements

Create a systematic plan:

- **Spacing system**: Define SCSS variables for a consistent scale (`$space-xs` through `$space-xl`). The specific values matter less than consistency.
- **Hierarchy strategy**: How will space communicate importance?
- **Layout approach**: What structure fits the content? Flex for 1D, Grid for 2D.
- **Rhythm**: Where should spacing be tight vs generous?

## Improve Layout Systematically

### Establish a Spacing System

Define SCSS spacing variables and apply them consistently:

```scss
$space-xs: 4px;
$space-sm: 8px;
$space-md: 16px;
$space-lg: 32px;
$space-xl: 64px;
```

- Use these variables throughout — no arbitrary pixel values
- Use `gap` for sibling spacing in flex/grid containers
- Name variables semantically: `$space-section`, `$space-element`, `$space-tight`

### Create Visual Rhythm

- **Tight grouping** for related elements (4-12px between siblings)
- **Generous separation** between distinct sections (32-64px)
- **Varied spacing** within sections — not every row needs the same gap
- **Asymmetric compositions** — break the predictable centered-content pattern when it makes sense

### Choose the Right Layout Tool

Puree supports both Flexbox and Grid via the Taffy layout engine:

- **Use Flexbox for 1D layouts**: Rows of items, nav bars, button groups, component internals. Flex is simpler and appropriate for most layout tasks.
- **Use Grid for 2D layouts**: Dashboards, data-dense interfaces, anything where rows AND columns need coordinated control.
- **Don't default to Grid** when Flexbox with `flex-wrap` would be simpler.

```scss
// Flex row with gap
.toolbar {
  display: flex;
  flex-direction: row;
  gap: $space-sm;
  align-items: center;
}

// Grid for dashboard layout
.dashboard {
  display: grid;
  grid-template-columns: 200px 1fr;
  grid-template-rows: 48px 1fr;
  gap: $space-md;
}
```

### Break Card Grid Monotony

- Don't default to card grids for everything — spacing and alignment create visual grouping naturally
- Use cards only when content is truly distinct and actionable — never nest cards inside cards
- Vary card sizes or mix cards with non-card content to break repetition

### Strengthen Visual Hierarchy

- Use the fewest dimensions needed for clear hierarchy. Space alone can be enough — generous whitespace around an element draws the eye. Add color or size contrast only when simpler means aren't sufficient.
- Create clear content groupings through proximity and separation.

### Manage Depth & Elevation

- Build a consistent shadow scale using SCSS variables — shadows should be subtle
- Use `box-shadow` elevation to reinforce hierarchy, not as decoration

```scss
$shadow-sm: 0px 1px 3px rgba(0, 0, 0, 0.12);
$shadow-md: 0px 4px 12px rgba(0, 0, 0, 0.15);
$shadow-lg: 0px 10px 24px rgba(0, 0, 0, 0.2);
```

Note: Puree does not support `z-index` — use visual cues (shadow, color, opacity) to convey depth.

### Responsive Layout with @media

Use Puree's `@media` queries to adapt layout at different panel widths:

```scss
.sidebar {
  display: none;
}

@media (min-width: 600px) {
  .sidebar {
    display: flex;
    width: 200px;
  }
}
```

Note: Puree supports `@media (min-width)` and `@media (max-width)` only — no container queries, no `clamp()`, no viewport units.

### Optical Adjustments

- If an icon looks visually off-center despite being geometrically centered, nudge it with `--text-x` or `--text-y` offsets — but only if you're confident it actually looks wrong.

**NEVER**:
- Use arbitrary spacing values outside your scale
- Make all spacing equal — variety creates hierarchy
- Wrap everything in cards — not everything needs a container
- Nest cards inside cards — use spacing and dividers for hierarchy within
- Use identical card grids everywhere (icon + heading + text, repeated)
- Center everything — left-aligned with asymmetry feels more designed
- Default to the hero metric layout (big number, small label, stats, gradient) as a template
- Default to Grid when Flexbox would be simpler — use the simplest tool for the job

## Verify Layout Improvements

- **Squint test**: Can you identify primary, secondary, and groupings with blurred vision?
- **Rhythm**: Does the layout have a satisfying beat of tight and generous spacing?
- **Hierarchy**: Is the most important content obvious within 2 seconds?
- **Breathing room**: Does the layout feel comfortable, not cramped or wasteful?
- **Consistency**: Is the SCSS spacing scale applied uniformly?
- **Responsiveness**: Does the layout adapt gracefully at different `@media` breakpoints?

Remember: Space is the most underused design tool. A layout with the right rhythm and hierarchy can make even simple content feel polished and intentional.