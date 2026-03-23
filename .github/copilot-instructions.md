# Copilot Instructions for Puree

When generating UI code for Puree, always read [PUREE_VS_CSS.md](../PUREE_VS_CSS.md) first for the full reference.

Key points:
- Puree uses YAML for structure, SCSS for styling, Python for interactivity
- **SCSS is standard CSS** — `color` means text color, `background-color` means fill
- `font-size` for text size, `text-align` for horizontal alignment (standard CSS names)
- Puree extensions use `--` prefix: `--text-align-v`, `--img-align-h`
- SCSS variables inside `--` properties need interpolation: `--text-align-v: #{$var};`
- Use `class: classname` in YAML to assign CSS classes (matched as `.classname` in SCSS)
- CSS cascade and specificity work: selectors, combinators, `!important`
- Use `:hover` and `:active` pseudo-classes for interactive states
- Background gradients: `background: linear-gradient(90deg, #3498db, #2ecc71)`
- Border gradients: `border-image: linear-gradient(135deg, #3498db, #2ecc71)`
- Multi-property transitions: `transition: background-color 0.2s ease, opacity 0.3s linear`
- Node names in YAML must use underscores, not hyphens
- Component params: `"{{param_name, 'default_value'}}"`
- `box-shadow` shorthand works: `box-shadow: 0px 10px 20px rgba(0,0,0,0.3)`
- Always call `mark_dirty()` after runtime property changes
- Always `return app` from script.py's `main()` function
