---
name: review
description: 'Review Puree UI code (YAML/SCSS/Python) for correctness, common mistakes, and best practices. Use when checking code quality, debugging render issues, or validating before shipping.'
user-invocable: true
argument-hint: 'Describe what to review (e.g. "my settings panel", "component library", "full project audit")'
---

Review Puree UI code for correctness, common mistakes, and adherence to framework constraints. Produces a structured report with severity-rated findings.

## Procedure

### 1. Gather Context

Read all target files before checking anything:
- All `.yaml` files (index.yaml + components)
- All `.scss` files (main styles + component styles)
- All `script.py` files
- Check `fonts/` directory for available fonts
- Check `assets/` directory for available images
- Check `components/` directory for component files

### 2. YAML Review

Check every YAML file for these issues:

| Check | Severity | What to Look For |
|-------|----------|------------------|
| **Node name hyphens** | 🔴 Critical | Any node name with `-` instead of `_` breaks the parser |
| **Theme config missing** | 🔴 Critical | `app > selected_theme > default_theme > theme[]` structure |
| **Theme fields missing** | 🔴 Critical | `name`, `styles`, `scripts`, `root` required in theme |
| **Component data syntax** | 🔴 Critical | Must be `data: '[name]'` with square brackets |
| **Parameter syntax** | 🔴 Critical | Must be `"{{name, 'default'}}"` — both quote types + comma |
| **Style paths exist** | 🟡 Warning | Paths in `styles:` and `scripts:` point to real files |
| **Font names valid** | 🟡 Warning | Font values match files in `fonts/` (no extension) |
| **Image names valid** | 🟡 Warning | Image values match files in `assets/` (no extension) |
| **Orphan style classes** | 🟢 Info | `style:` values not matched by any `.classname` in SCSS |
| **Deep nesting** | 🟢 Info | Nesting >8 levels deep (performance concern) |
| **Component root key** | 🔴 Critical | Root key in component YAML must match filename |

### 3. SCSS Review

Check every SCSS file:

| Check | Severity | What to Look For |
|-------|----------|------------------|
| **Unsupported properties** | 🔴 Critical | `float`, `clear`, `z-index`, `transform`, `@keyframes`, `animation`, pseudo-elements |
| **Unsupported functions** | 🔴 Critical | `calc()`, `clamp()`, `min()`, `max()` |
| **Unsupported units** | 🔴 Critical | `em`, `rem`, `vw`, `vh`, `fr` — only `px` and `%` work |
| **Unsupported display** | 🔴 Critical | `inline`, `inline-flex`, `inline-block` — only `flex`, `grid`, `block`, `none` |
| **Unsupported selectors** | 🔴 Critical | Attribute selectors, `:nth-child`, `::before`/`::after`, `:not()`, `:is()`, siblings |
| **Layout in hover/active** | 🔴 Critical | `width`, `height`, `padding`, `margin`, `flex-*`, `gap` in `:hover`/`:active` — IGNORED |
| **Non-animatable transition** | 🔴 Critical | `transition` targeting anything other than `background-color`, `color`, `border-color`, `opacity` |
| **Extension interpolation** | 🔴 Critical | `--text-align-v: $var` instead of `--text-align-v: #{$var}` |
| **Per-side border colors** | 🟡 Warning | `border-top-color` etc. — only uniform `border-color` works |
| **Radial/conic gradient** | 🔴 Critical | Only `linear-gradient()` supported |
| **Multiple box-shadows** | 🟡 Warning | Only single `box-shadow` per element |
| **Unsupported position** | 🟡 Warning | `fixed`, `sticky` — only `relative` and `absolute` |
| **Missing root layout** | 🟡 Warning | `.root` should have `width: 100%; height: 100%` |
| **Inheritance assumptions** | 🟢 Info | Only `color`, `font-size`, `text-align` inherit. Everything else explicit. |
| **Font-family usage** | 🟡 Warning | `font-family` in CSS is ignored — use YAML `font:` attribute |
| **Unused CSS classes** | 🟢 Info | `.classname` rules not referenced by any YAML `style:`/`class:` |

### 4. Python Review

Check every script.py:

| Check | Severity | What to Look For |
|-------|----------|------------------|
| **Missing return app** | 🔴 Critical | `main()` must end with `return app` |
| **Wrong main signature** | 🔴 Critical | Must be `def main(self, app):` |
| **Missing mark_dirty()** | 🔴 Critical | Any `.text =`, `.style.display =`, `.set_property()` without `mark_dirty()` |
| **Wrong display values** | 🔴 Critical | Runtime display must be uppercase: `'FLEX'`, `'NONE'` not `'flex'`, `'none'` |
| **Blocking calls** | 🟡 Warning | Network I/O, file I/O, `time.sleep()` in event handlers without threading |
| **Wrong handler signature** | 🟡 Warning | Event handlers must accept `fn(container)` |
| **Direct style field access** | 🟢 Info | Prefer `set_property('css-name', value)` over direct `style.field = value` |
| **Dead container paths** | 🟡 Warning | Dot-notation paths that don't match YAML tree |
| **Namespaced access** | 🟡 Warning | Component children need namespace prefix: `instance_child` not just `child` |

### 5. Cross-File Review

| Check | Severity | What to Look For |
|-------|----------|------------------|
| **Style/class mismatch** | 🟡 Warning | YAML `style:`/`class:` values without matching SCSS `.classname` |
| **SCSS without YAML** | 🟢 Info | SCSS `.classname` rules not used by any YAML node |
| **Component file mismatch** | 🔴 Critical | `data: '[name]'` but `components/name.yaml` doesn't exist |
| **Param name mismatch** | 🟡 Warning | Parameters passed in YAML not defined in component |
| **Font file missing** | 🟡 Warning | `font:` values without matching file in `fonts/` |
| **Image file missing** | 🟡 Warning | `img:` values without matching file in `assets/` |
| **Script path mismatch** | 🟡 Warning | Container paths in script.py don't match YAML tree |

### 6. Performance Review

| Check | Severity | What to Look For |
|-------|----------|------------------|
| **High container count** | 🟡 Warning | >200 YAML nodes (each = GPU container) |
| **Many transitions** | 🟡 Warning | >20 elements with transitions |
| **Large images** | 🟡 Warning | Images >1024px that aren't thumbnailed |
| **Frequent mark_dirty** | 🟢 Info | `mark_dirty()` called in tight loops or timers |
| **Deep nesting** | 🟢 Info | >8 levels of container nesting |

### 7. Output Format

For each issue, report in this format:

```
🔴 CRITICAL | style.scss:42 | Layout property in :hover
   Found: `width: 110px` inside `.button:hover { }`
   Fix: Remove `width` from :hover — only background-color, color, border-color, opacity work in hover states

🟡 WARNING | index.yaml:15 | Font name not found
   Found: `font: HelveticaNeue` but fonts/ contains: NeueMontreal-Regular, NeueMontreal-Bold
   Fix: Use `font: NeueMontreal-Regular` or add the font file to fonts/

🟢 INFO | style.scss:88 | Unused CSS class
   Found: `.old_panel` not referenced by any YAML node
   Fix: Remove if unused, or add to YAML if intended
```

### 8. Summary

End with a summary:
- Total issues by severity (🔴 Critical / 🟡 Warning / 🟢 Info)
- Top 3 most impactful issues to fix first
- Overall assessment: "Ready to ship" / "Needs fixes" / "Major issues"

For reference: Puree documentation — PUREE_VS_CSS.md, PUREE_SPEC.md, API.md (see https://github.com/nicprod/puree/tree/main/docs)
