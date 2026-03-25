---
description: "Debug a Puree panel that isn't rendering correctly. Runs a structured checklist of common issues."
agent: agent
argument-hint: "Describe the problem (e.g. 'panel is blank', 'hover not working', 'text not showing')"
---

A Puree UI panel isn't working correctly. Run this systematic debugging checklist to find the issue.

## Step 1: Read the Files

Read the user's `index.yaml`, `style.scss`, and `script.py` files before checking anything. Understand the full context.

## Step 2: YAML Checks

- [ ] **Node names** — Any hyphens? Must be underscores only (`my_button` ✓ `my-button` ✗)
- [ ] **Theme config** — Has `app > selected_theme > default_theme > theme[]`?
- [ ] **Theme fields** — Has `name`, `styles`, `scripts`, `root`?
- [ ] **Style paths** — Do paths in `styles:` and `scripts:` point to existing files?
- [ ] **Component path** — Does `components:` directory exist?
- [ ] **Component refs** — `data: '[name]'` uses square brackets and quotes?
- [ ] **Parameter syntax** — `"{{name, 'default'}}"` has both quote types and comma?
- [ ] **Font names** — Match files in `fonts/` directory (no extension)?
- [ ] **Image names** — Match files in `assets/` directory (no extension)?
- [ ] **YAML syntax** — Valid YAML? No tabs (spaces only)? Proper indentation?

## Step 3: SCSS Checks

- [ ] **Class names match** — Every `style:` and `class:` in YAML has a matching `.classname` in SCSS?
- [ ] **Unsupported properties** — Any `calc()`, `em`/`rem`/`vw`/`vh`, `transform`, `float`, `z-index`?
- [ ] **Hover/active** — Only `background-color`, `color`, `border-color`, `opacity` in `:hover`/`:active`? (layout props are ignored)
- [ ] **Transitions** — Target only animatable properties? (`background-color`, `color`, `border-color`, `opacity`)
- [ ] **Puree extensions** — `--text-align-v`, `--img-align-h` etc. use `#{$var}` interpolation for variables?
- [ ] **Display values** — Only `flex`, `grid`, `block`, `none`? (no `inline`, `inline-flex`)
- [ ] **Gradients** — `linear-gradient()` only? (no radial, conic)
- [ ] **Box shadow** — Single shadow only? (no comma-separated list)
- [ ] **Selectors** — No attribute selectors, `:nth-child`, `::before`/`::after`, `:not()`?
- [ ] **Border colors** — No per-side border colors? (uniform `border-color` only)
- [ ] **Root layout** — `.root` has `width: 100%; height: 100%;`?

## Step 4: Python Checks

- [ ] **main signature** — `def main(self, app):`?
- [ ] **return app** — `main()` returns `app` at the end?
- [ ] **mark_dirty()** — Called after EVERY property change (`text`, `style.display`, `set_property`)?
- [ ] **Container access** — Dot notation path matches YAML tree? (`app.theme.root.path.to.node`)
- [ ] **Event signatures** — All handlers take `fn(container)`?
- [ ] **Display values** — Runtime display uses uppercase strings: `'FLEX'`, `'NONE'`?
- [ ] **Blocking calls** — No synchronous network/file I/O in handlers? (use threading)

## Step 5: Cross-File Checks

- [ ] **Style/class consistency** — YAML `style:` values exist as `.classname` in SCSS
- [ ] **Component files** — `data: '[name]'` corresponds to `components/name.yaml`
- [ ] **Component root keys** — YAML root key matches filename
- [ ] **Font files** — `font:` values match files in `fonts/` (without extension)
- [ ] **Image files** — `img:` values match files in `assets/` (without extension)
- [ ] **Script paths** — Container paths in script.py match actual YAML hierarchy

## Step 6: Report

For each issue found, report:
- **File**: which file has the problem
- **Issue**: what's wrong
- **Fix**: exact correction needed

Reference: [PUREE_VS_CSS.md](../../docs/PUREE_VS_CSS.md) | [PUREE_SPEC.md](../../docs/PUREE_SPEC.md) | [API.md](../../docs/API.md)
