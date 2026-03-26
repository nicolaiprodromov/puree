# Puree UI — Copilot Instructions

> These instructions are loaded into every Copilot conversation in this workspace.
> They provide the essential context for AI working on this Puree addon.

## What Is Puree

Puree is a **GPU-accelerated UI framework for Blender addons**. It lets developers build rich custom interfaces using YAML (structure), SCSS (styling), and Python (interactivity). It renders via ModernGL compute shaders inside Blender panels. Layout uses Taffy/Stretchable (a Rust flexbox/grid engine).

**It is NOT a web framework.** Many CSS features don't exist. See "What Puree Doesn't Support" below.

## Project Structure

```
my_addon/
├── static/
│   ├── index.yaml          # UI tree (structure)
│   ├── style.scss          # Styles
│   ├── script.py           # Event handlers + interactivity
│   └── components/         # Reusable components
│       ├── button.yaml
│       └── button.scss
├── assets/                 # Images (PNG, SVG)
├── fonts/                  # Fonts (.ttf, .otf)
├── wheels/                 # Python dependency wheels
├── __init__.py             # Blender addon entry point
├── blender_manifest.toml   # Blender extension manifest
├── .agents/                # AI skills for design work
└── .github/                # AI instructions, agents, prompts
```

## Critical Rules — Always Remember

### YAML
- Node names: **underscores only** (`my_button` ✓ `my-button` ✗) — parser breaks on hyphens
- Component refs: `data: '[component_name]'` — square brackets required
- Parameters: `"{{param_name, 'default_value'}}"` — both quote types, comma required
- Font/image names omit extensions

### SCSS
- **Only 4 animatable properties**: `background-color`, `color`, `border-color`, `opacity`
- Layout properties in `:hover`/`:active` are **silently ignored** (no width/height/padding/margin changes on hover)
- Units: only `px` and `%` (no em, rem, vw, vh, fr, calc)
- Display: only `flex`, `grid`, `block`, `none` (no inline variants)
- Gradients: only `linear-gradient()` (no radial, conic)
- Selectors: no `::before`/`::after`, `nth-child`, `:not()`, attribute selectors
- `--` extension properties need `#{$var}` interpolation for SCSS variables
- Only `color`, `font-size`, `text-align` inherit from parents
- Font selection uses YAML `font:` attribute, not CSS `font-family`

### Python (script.py)
- Entry: `def main(self, app):` — must `return app`
- After ANY property change: call `mark_dirty()` — GPU won't update without it
- Runtime display values are UPPERCASE: `'FLEX'`, `'NONE'` (CSS uses lowercase)
- Event callbacks: `fn(container)` — all take one argument
- Component children are namespaced: `instance_child_name`
- Blender is NOT thread-safe — use `threading.Thread` for async, `bpy.app.timers` for deferred bpy calls

## What Puree Doesn't Support

`calc()` · `clamp()` · `min()` · `max()` · `em` · `rem` · `vw` · `vh` · `fr` · `::before` · `::after` · `@keyframes` · `animation` · `transform` · `rotate` · `scale` · `translate` · `float` · `clear` · `z-index` (CSS) · `inline` display · `position: fixed` · `position: sticky` · radial/conic gradients · multiple box-shadows · per-side border colors · `font-family` in CSS · `inherit` · `initial` · `unset` · `:nth-child` · `:not()` · attribute selectors · sibling combinators

## Build Commands

```bash
puree build           # Build extension zip using Blender on PATH
puree install         # Install built extension into Blender
puree link            # Symlink project into Blender for development
puree unlink          # Remove the development symlink
puree reload          # Reload addon in running Blender (via TCP reload server)
```

## AI Agents & Skills

This project includes AI configuration for the `puree-coder` agent, which specializes in building Puree interfaces. Available skills include:

| Skill | Purpose |
|-------|---------|
| `/frontend-design` | Create distinctive, production-grade UI interfaces |
| `/review` | Check code quality, common mistakes, best practices |
| `/audit` | Comprehensive quality audit with severity ratings |
| `/polish` | Final quality pass before shipping |
| `/animate` | Add purposeful transitions and state changes |
| `/colorize` | Add strategic color to monochromatic designs |
| `/typeset` | Improve typography hierarchy and readability |
| `/arrange` | Fix layout, spacing, and visual rhythm |
| `/extract` | Extract reusable components and SCSS variables |
| `/harden` | Improve resilience and edge case handling |
| `/optimize` | Performance improvements |
| `/critique` | Design effectiveness evaluation |
| `/teach-impeccable` | One-time design context setup |

## Known Issues & Gotchas

| Issue | Detail |
|-------|--------|
| Dynamic row hide | `height: 0` alone doesn't fully hide — also clear padding and border-width |
| Hot reload + GL | Rapid saves can crash the ModernGL context |
| Hit detection stale | Panel resize can break hit detection — cache needs clearing |
| Display case mismatch | SCSS uses `none`/`flex`, Python runtime uses `NONE`/`FLEX` |
| Text rendering async | Text renders separately from GPU containers, can lag |
| SCSS cache | Uses mtime only — `git checkout` may not invalidate cache |
