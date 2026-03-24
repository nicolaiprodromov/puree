---
name: frontend-design
description: Create distinctive, production-grade Puree UI interfaces with high design quality. Use this skill when the user asks to build UI panels, dashboards, toolbars, or Blender addon interfaces. Generates creative, polished YAML/SCSS/Python code that avoids generic AI aesthetics.
---

This skill guides creation of distinctive, production-grade Puree UI interfaces for Blender that avoid generic "AI slop" aesthetics. Implement real working YAML/SCSS/Python code with exceptional attention to aesthetic details and creative choices.

**Tech stack**: YAML (structure) + SCSS (styling) + Python (interactivity). Runs inside Blender via GPU-accelerated rendering (ModernGL compute shaders) with Taffy/Stretchable flexbox/grid layout.

## Context Gathering Protocol

Design skills produce generic output without project context. You MUST have confirmed design context before doing any design work.

**Required context** — every design skill needs at minimum:
- **Target audience**: Who uses this addon and in what workflow?
- **Use cases**: What jobs are they trying to get done?
- **Brand personality/tone**: How should the interface feel?

Individual skills may require additional context — check the skill's preparation section for specifics.

**CRITICAL**: You cannot infer this context by reading the codebase. Code tells you what was built, not who it's for or what it should feel like. Only the creator can provide this context.

**Gathering order:**
1. **Check current instructions (instant)**: If your loaded instructions already contain a **Design Context** section, proceed immediately.
2. **Check .impeccable.md (fast)**: If not in instructions, read `.impeccable.md` from the project root. If it exists and contains the required context, proceed.
3. **Run teach-impeccable (REQUIRED)**: If neither source has context, you MUST run the teach-impeccable skill NOW before doing anything else. Do NOT skip this step. Do NOT attempt to infer context from the codebase instead.

---

## Design Direction

Commit to a BOLD aesthetic direction:
- **Purpose**: What problem does this interface solve? Who uses it in Blender?
- **Tone**: Pick an extreme: brutally minimal, maximalist chaos, retro-futuristic, organic/natural, luxury/refined, playful/toy-like, editorial/magazine, brutalist/raw, art deco/geometric, soft/pastel, industrial/utilitarian, etc. There are so many flavors to choose from. Use these for inspiration but design one that is true to the aesthetic direction.
- **Constraints**: Puree's supported properties (flexbox/grid layout, transitions on color/opacity only, px/% units only).
- **Differentiation**: What makes this UNFORGETTABLE? What's the one thing someone will remember?

**CRITICAL**: Choose a clear conceptual direction and execute it with precision. Bold maximalism and refined minimalism both work—the key is intentionality, not intensity.

Then implement working code that is:
- Production-grade and functional (valid YAML structure, compilable SCSS, working Python scripts)
- Visually striking and memorable
- Cohesive with a clear aesthetic point-of-view
- Meticulously refined in every detail
- Correct for Puree (use only supported properties — see `docs/PUREE_VS_CSS.md`)

## Puree Aesthetics Guidelines

### Typography
→ *Consult [typography reference](reference/typography.md) for scales, pairing, and font loading.*

Choose fonts that are beautiful, unique, and interesting. Place font files in the `fonts/` directory and reference them via the YAML `font:` attribute.

**DO**: Use a modular type scale with distinct size steps in px
**DO**: Vary font weights and sizes to create clear visual hierarchy
**DO**: Load display and body fonts from the `fonts/` directory
**DON'T**: Use overused fonts when distinctive alternatives are available in the project
**DON'T**: Use monospace typography as lazy shorthand for "technical/developer" vibes
**DON'T**: Put large icons above every heading—they rarely add value and make interfaces look templated

### Color & Theme
→ *Consult [color reference](reference/color-and-contrast.md) for palettes, SCSS variables, and theming.*

Commit to a cohesive palette. Dominant colors with sharp accents outperform timid, evenly-distributed palettes.

**DO**: Use SCSS variables for a maintainable, consistent palette (`$primary`, `$surface`, `$text`)
**DO**: Use hex, `rgba()`, `rgb()`, `hsl()` for color values — these are what Puree's color parser supports
**DO**: Tint your neutrals toward your brand hue—even a subtle hint creates subconscious cohesion
**DON'T**: Use gray text on colored backgrounds—it looks washed out; use a shade of the background color instead
**DON'T**: Use pure black (#000) or pure white (#fff)—always tint; pure black/white never appears in nature
**DON'T**: Use the AI color palette: cyan-on-dark, purple-to-blue gradients, neon accents on dark backgrounds
**DON'T**: Use gradient text for "impact"—especially on metrics or headings; it's decorative rather than meaningful
**DON'T**: Default to dark mode with glowing accents—it looks "cool" without requiring actual design decisions

### Layout & Space
→ *Consult [spatial reference](reference/spatial-design.md) for grids, rhythm, and spacing systems.*

Create visual rhythm through varied spacing—not the same padding everywhere. Embrace asymmetry and unexpected compositions. Break the grid intentionally for emphasis.

**DO**: Create visual rhythm through varied spacing—tight groupings, generous separations
**DO**: Use `display: flex` and `display: grid` for layout (Puree supports both via Taffy)
**DO**: Use asymmetry and unexpected compositions; break the grid intentionally for emphasis
**DO**: Use `gap` for consistent sibling spacing in flex/grid containers
**DON'T**: Wrap everything in cards—not everything needs a container
**DON'T**: Nest cards inside cards—visual noise, flatten the hierarchy
**DON'T**: Use identical card grids—same-sized cards with icon + heading + text, repeated endlessly
**DON'T**: Center everything—left-aligned text with asymmetric layouts feels more designed
**DON'T**: Use the same spacing everywhere—without rhythm, layouts feel monotonous

### Visual Details
**DO**: Use intentional, purposeful decorative elements that reinforce brand
**DO**: Use `border-image: linear-gradient()` for accent borders
**DO**: Use `box-shadow` for subtle depth (one shadow per element)
**DON'T**: Use rounded elements with thick colored border on one side—a lazy accent that almost never looks intentional
**DON'T**: Use rounded rectangles with generic drop shadows—safe, forgettable, could be any AI output

### Motion
→ *Consult [motion reference](reference/motion-design.md) for timing and easing.*

Puree supports `transition` on `background-color`, `color`, `border-color`, and `opacity`. Use these four animatable properties to create responsive, alive-feeling interfaces.

**DO**: Use transitions to convey state changes—hover feedback, active states, visibility shifts
**DO**: Use `ease-out` for elements appearing, `ease-in` for elements fading
**DO**: Combine multiple transitions: `transition: background-color 0.2s ease, opacity 0.3s linear`
**DON'T**: Expect `@keyframes`, `transform`, or `animation` to work — Puree only supports `transition`
**DON'T**: Use bounce or elastic easing—Puree supports `ease`, `linear`, `ease-in`, `ease-out`, `ease-in-out`

### Interaction
→ *Consult [interaction reference](reference/interaction-design.md) for events, hover/active states, and Python scripting.*

Make interactions feel fast and responsive. Use Python event handlers to update UI state.

**DO**: Use progressive disclosure—start simple, reveal sophistication through interaction
**DO**: Design empty states that teach the interface, not just say "nothing here"
**DO**: Make every interactive surface feel intentional with `:hover` and `:active` SCSS states
**DO**: Always call `mark_dirty()` after changing properties at runtime
**DON'T**: Repeat the same information—redundant headers, intros that restate the heading
**DON'T**: Make every button primary—use ghost buttons, text links, secondary styles; hierarchy matters

### Adaptive Layout
→ *Consult [responsive reference](reference/responsive-design.md) for `@media` queries in Puree.*

**DO**: Use `@media (min-width: Npx)` and `@media (max-width: Npx)` to adapt to different panel sizes
**DO**: Adapt the interface for different Blender panel widths—don't just shrink it
**DON'T**: Hide critical functionality at narrow widths—adapt the layout, don't amputate it

### UX Writing
→ *Consult [ux-writing reference](reference/ux-writing.md) for labels, errors, and empty states.*

**DO**: Make every word earn its place
**DON'T**: Repeat information users can already see

---

## The AI Slop Test

**Critical quality check**: If you showed this interface to someone and said "AI made this," would they believe you immediately? If yes, that's the problem.

A distinctive interface should make someone ask "how was this made?" not "which AI made this?"

Review the DON'T guidelines above—they are the fingerprints of AI-generated work from 2024-2025.

---

## Implementation Principles

Match implementation complexity to the aesthetic vision. Maximalist designs need elaborate SCSS with rich color palettes, gradient borders, and layered transitions. Minimalist or refined designs need restraint, precision, and careful attention to spacing, typography, and subtle details.

Interpret creatively and make unexpected choices that feel genuinely designed for the context. No design should be the same. Vary between light and dark themes, different fonts, different aesthetics. NEVER converge on common choices across generations.

### Puree-Specific Reminders
- **YAML node names** must use underscores, not hyphens (`sidebar_panel`, not `sidebar-panel`)
- **SCSS variables** inside `--` extension properties need interpolation: `--text-align-v: #{$var};`
- **Component params** use `"{{param_name, 'default_value'}}"` syntax
- **Always `return app`** from `script.py`'s `main()` function
- **Always call `mark_dirty()`** after runtime property changes
- **Only px and % units** are supported — no `rem`, `em`, `vw`, `vh`, `fr`
- **Supported color formats**: hex, `rgb()`, `rgba()`, `hsl()`, named colors
- **Unsupported**: `oklch()`, `color-mix()`, `light-dark()`, `calc()`, `clamp()`, `@keyframes`, `transform`, `z-index`, pseudo-elements

Remember: the model is capable of extraordinary creative work. Don't hold back—show what can truly be created when thinking outside the box and committing fully to a distinctive vision.