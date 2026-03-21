# Copilot Instructions for Puree

When generating UI code for Puree, always read `PUREE_SPEC.md` in the repository root first.

Key points:
- Puree uses YAML for structure, SCSS for styling, Python for interactivity
- Use standard CSS property names: `color` (text), `background-color` (fill), `font-size` (text size)
- CSS cascade and specificity work like the web
- Use `:hover` and `:active` pseudo-classes for interactive states
- Puree extensions use `--` prefix: `--text-align-v`, `--img-align-h`, `--background-color-2`
- Node names in YAML must use underscores, not hyphens
- Component params: `"{{param_name, 'default_value'}}"`
- Always call `mark_dirty()` after runtime property changes
- Always `return app` from script.py's `main()` function
