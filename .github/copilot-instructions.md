# Copilot Instructions for Puree

When generating UI code for Puree, always read `PUREE_SPEC.md` in the repository root first.

Key points:
- Puree uses YAML for structure, SCSS for styling, Python for interactivity
- `color` means **background/fill** (NOT text). Use `text-color` for text.
- `text-scale` for text size, `text-align-h` for horizontal alignment
- `font-size` and `text-align` are accepted aliases mapped by the cascade engine
- Use `style: classname` in YAML to assign CSS classes (matched as `.classname` in SCSS)
- CSS cascade and specificity work: selectors, combinators, `!important`
- Use `:hover` and `:active` pseudo-classes for interactive states
- Puree extensions use `--` prefix: `--text-align-v`, `--img-align-h`, `--background-color-2`
- Node names in YAML must use underscores, not hyphens
- Component params: `"{{param_name, 'default_value'}}"`
- Always call `mark_dirty()` after runtime property changes
- Always `return app` from script.py's `main()` function
