# Puree Documentation Audit Report

**Auditor**: Senior Software Engineer & Technical Documentation Auditor  
**Date**: March 28, 2026  
**Scope**: Full repository — `docs/`, `.github/`, `.agents/`, `puree/scaffold/`, `README.md`, all engine source code  
**Codebase**: ~12,000 lines Python + Rust (PyO3) + GLSL across 40+ modules  

---

## 1. Executive Summary

**Overall Documentation Quality: 8.2 / 10**

Puree's documentation is remarkably strong for a project of this complexity and maturity stage. The documentation ecosystem is unusually sophisticated — spanning user-facing docs, AI agent instructions, skill modules, prompt templates, and scaffold templates — and achieves high accuracy across all layers. The KNOWLEDGE_BASE.md is institutional-quality, the PUREE_SPEC.md is comprehensive enough for code generation, and the AI instruction files (.github/instructions/) are best-in-class for framework-specific AI guidance.

However, there is **one critical factual error propagated across 15+ files**: the documentation universally claims only `px` and `%` CSS units are supported, while the actual parser (`puree/parser.py` lines 920-1000) fully implements `rem`, `em`, `vw`, `vh`, `vmin`, `vmax`, and `calc()`. This isn't a minor gap — it actively prevents users and AI agents from using features that exist and work. Beyond this, gaps are primarily in advanced module documentation (keyboard shortcuts, storage edge cases) and missing examples for newer features (markdown, virtual scroll, collapse).

---

## 2. Strengths

### Exceptional AI-Integrated Documentation Ecosystem
The `.github/instructions/`, `.agents/skills/`, and `.github/prompts/` directories represent a documentation strategy at a level of quality rarely seen in open-source. The `puree-shaders.instructions.md` file documents every single one of the 68 float offsets in the GPU buffer — verified against the actual `_build_container_struct()` in `render.py`. This level of precision means AI agents can modify the rendering pipeline without breaking the buffer stride.

### Exceptionally Well-Organized Knowledge Base
`docs/KNOWLEDGE_BASE.md` reads like internal engineering documentation at a mature company. It covers architecture decisions, rendering pipeline internals, parser flow, event mechanics, hot reload design, and includes an 18-item debugging cheat sheet. This is the kind of document that saves engineers hours.

### Strong Scaffold/Template Parity
The `puree/scaffold/` directory — distributed to users via `puree init` — is **perfectly synced** with the main repo's instruction files. All 4 user-facing instruction files, 4 prompts, and 22 design skills are byte-identical between scaffold and repository. Zero content drift.

### Consistent Critical Warnings
The `mark_dirty()` requirement is emphasized in every relevant document: PUREE_SPEC, API.md, DOCS.md, KNOWLEDGE_BASE, TROUBLESHOOTING, copilot-instructions, every instruction file, and every agent definition. This is the correct approach for a framework-breaking gotcha.

### High-Quality Example Code
All 6 examples (example0-5) plus the static/ default panel demonstrate real patterns. The static/ chat panel is production-grade complexity showing dynamic slots, threaded API calls, and multi-model switching.

---

## 3. Critical Issues

### 3.1 CSS Unit Support: Pervasive Factual Error

**Severity: CRITICAL**

**The documentation universally states only `px` and `%` units are supported. The code supports 8 unit types.**

Actual parser implementation at `puree/parser.py` lines 920-1000:
```python
_unit_re = re.compile(r'(-?[\d.]+)\s*(px|%|rem|em|vmin|vmax|vw|vh)?')
# ... full implementation for all 8 units including calc()
```

The parser fully implements:
- `rem` — resolved against root font-size (default 16px)
- `em` — resolved against parent font-size
- `vw` — 1% of viewport width
- `vh` — 1% of viewport height
- `vmin` — 1% of smaller viewport dimension
- `vmax` — 1% of larger viewport dimension
- `calc()` — expression evaluation with + and - operators across mixed units

This false claim appears in **at minimum 15 files** that all need updating:

| # | File | Line(s) | Current (incorrect) claim |
|---|------|---------|--------------------------|
| 1 | `.github/copilot-instructions.md` | ~82 | "Units: only `px` and `%` (no em, rem, vw, vh, fr, calc)" |
| 2 | `puree/scaffold/.github/copilot-instructions.md` | ~43 | Same as above |
| 3 | `.github/instructions/puree-scss.instructions.md` | Units section | "only `px` and `%`" |
| 4 | `puree/scaffold/.github/instructions/puree-scss.instructions.md` | Units section | Same (scaffold copy) |
| 5 | `.github/agents/puree-coder.agent.md` | ~299 | "No `calc()`, `em`/`rem`" |
| 6 | `puree/scaffold/.github/agents/puree-coder.agent.md` | ~299 | Same (scaffold copy) |
| 7 | `.github/prompts/new-puree-panel.prompt.md` | ~29 | "Only `px` and `%` units (no em/rem/vw/vh)" |
| 8 | `puree/scaffold/.github/prompts/new-puree-panel.prompt.md` | ~29 | Same (scaffold copy) |
| 9 | `docs/PUREE_VS_CSS.md` | ~188-189 | Lists `calc()`, `em`, `rem`, `vw`, `vh` as unsupported |
| 10 | `docs/SUPPORT.md` | ~56 | "Only `px` and `%` units are supported" |
| 11 | `.agents/skills/frontend-design/SKILL.md` | ~159 | "Only px and % units — no `rem`, `em`, `vw`, `vh`, `fr`" |
| 12 | `puree/scaffold/.agents/skills/frontend-design/SKILL.md` | ~159 | Same (scaffold copy) |
| 13 | `.agents/skills/review/SKILL.md` | ~48 | Flags `em`/`rem`/`vw`/`vh` as "🔴 Critical: Unsupported units" |
| 14 | `puree/scaffold/.agents/skills/review/SKILL.md` | ~48 | Same (scaffold copy) |
| 15 | `.agents/skills/frontend-design/reference/typography.md` | ~25 | "no rem, em, or viewport-relative unit support" |
| 16 | `.agents/skills/frontend-design/reference/responsive-design.md` | ~178 | "no rem, em, vw, vh, or fr units" |
| 17 | `puree/scaffold/.agents/skills/frontend-design/reference/responsive-design.md` | (if exists) | Same (scaffold copy) |

**What to change**: Update all files to state that `px`, `%`, `rem`, `em`, `vw`, `vh`, `vmin`, `vmax`, and `calc()` ARE supported. Note that `fr` units are genuinely unsupported (grid fractional units). Also note that `clamp()`, `min()`, `max()` are NOT supported — only `calc()` with `+` and `-`.

**Important**: The `review/SKILL.md` check that flags `em`/`rem`/`vw`/`vh` as "🔴 Critical: Unsupported units" must be removed or corrected — it currently causes AI agents to flag valid code as broken.

### 3.2 "What Puree Doesn't Support" Lists Contain Working Features

**Severity: CRITICAL**

The copilot-instructions.md (both repo and scaffold) and `PUREE_VS_CSS.md` explicitly list `calc()` in the "What Puree Doesn't Support" section. This is factually wrong. The `calc()` implementation in `parser.py` includes expression tokenization and recursive unit resolution — it handles addition and subtraction of mixed units.

**Files to update**:
- `.github/copilot-instructions.md` — Remove `calc()` from unsupported list
- `puree/scaffold/.github/copilot-instructions.md` — Same
- `docs/PUREE_VS_CSS.md` — Remove `calc()`, `em`, `rem`, `vw`, `vh` from unsupported; keep `clamp()`, `min()`, `max()`, `fr`

---

## 4. Completeness Gaps

### 4.1 Undocumented Container API: `keys` Property

**Files to update**: `docs/API.md` (Container Properties section), `docs/PUREE_SPEC.md` (events section)

The Container class exposes a `.keys` property returning a `ContainerKeyProxy` for scoped keyboard shortcuts:
```python
container.keys.bind("SHIFT+ENTER", my_callback)
```
This exists in `puree/components/container.py` and is wired through `puree/keyboard.py` but is not mentioned in any documentation.

### 4.2 Undocumented Container Properties in API.md

**File to update**: `docs/API.md` (Container Properties table)

- `classes` — Listed in YAML node properties table in PUREE_SPEC but not in API.md Container Properties
- `layer` — Used for z-ordering, only mentioned in passing (PUREE_SPEC Rule 13), not in API.md

### 4.3 Missing Full Examples for Built-in Modules

**File to update**: `docs/PUREE_SPEC.md` (Section 9 — Built-in Modules)

PUREE_SPEC Section 9 lists 8 built-in modules but only provides brief mentions. Complete working examples are needed for:
- Markdown rendering (`set_markdown()` / `render_markdown()`)
- Virtual scrolling (setup + renderer pattern)
- Collapse/expand (header/children convention)
- Keyboard shortcuts (scoped bindings, `when` conditions)

API.md has code snippets for these but they're minimal and missing edge cases.

### 4.4 Scaffold Missing 4 Useful Skills

**Action**: Copy these 4 skill directories from `.agents/skills/` to `puree/scaffold/.agents/skills/`:
- `diagnose/` — Helps users debug rendering issues
- `perf/` — Helps users optimize performance
- `extend-property/` — Helps advanced users add custom CSS properties
- `trace/` — Helps users understand data flow

These have cross-user appeal unlike the engine-only instruction files which are correctly omitted.

---

## 5. Accuracy & Currency Problems

### 5.1 `display: block` Behavior Undefined

**Files to update**: `docs/PUREE_VS_CSS.md`, `docs/PUREE_SPEC.md`

Multiple documents mention `display: block` as a supported value alongside `flex`, `grid`, and `none`. But no documentation explains what `block` does differently from `flex` in Puree's context. The Taffy/Stretchable layout engine treats `block` as a specific layout mode (children stack vertically, fill width), but users have no guidance.

### 5.2 Scrollbar Properties Under-documented

**Files to update**: `docs/PUREE_SPEC.md` (CSS section), `.github/instructions/puree-scss.instructions.md`

`API.md` documents `scrollbar-width` with values `none`, `thin` (6px), `auto` (8px). The code also supports `scrollbar-color`, `scrollbar-thumb-color`, and `scrollbar-track-color` — visible in API.md's CSS property table but not in the SCSS instructions or PUREE_SPEC.

### 5.3 `border` Shorthand Parsing Limitation

**Files to update**: `docs/PUREE_SPEC.md`, `docs/PUREE_VS_CSS.md`, `docs/KNOWLEDGE_BASE.md`

The parser extracts only numeric width from `border: 2px solid #ff0000` — it ignores the color and style components. Code in `parser.py` `parse_border_values()`:
```python
for part in parts:
    if 'px' in part or '%' in part:
        val = parse_css_value(part)
        width_top = width_right = width_bottom = width_left = val
    elif part.startswith('#') or part in ['red', 'blue', ...]:
        setattr(container.style, 'border_color_css', part)
```
It stores the color in `border_color_css` but this may not propagate to the GPU. Users expecting `border: 2px solid red` to set the border color should be warned to use `border-color` separately.

### 5.4 `set_markdown()` vs `render_markdown()` Ambiguity

**File to update**: `docs/API.md` (Markdown section)

API.md shows both `container.set_markdown(text)` and `render_markdown(container, text)` without clarifying when to use which. The Container method `set_markdown()` has the full signature `set_markdown(text, app, fonts=None, classes=None)` — more parameters than shown. Recommend picking `container.set_markdown()` as canonical and noting `render_markdown()` as the underlying function.

### 5.5 `_toggle_value` vs `_toggled` Confusion

**File to update**: `docs/API.md` (Container Properties section)

Both properties are listed without clear distinction:
- `_toggle_value` (bool) — The persistent boolean state of the toggle (True/False)
- `_toggled` (bool) — Whether a toggle event fired THIS frame (transient, resets next frame)

### 5.6 Pipeline Order Inconsistency (Minor)

**Files affected**: `docs/index.md`, `docs/KNOWLEDGE_BASE.md`

`index.md` shows the pipeline as "Parse → Layout → Compile → Render → Event" while `KNOWLEDGE_BASE.md` shows a different, more detailed order. The simplified version in `index.md` should note it's a high-level view, or match the actual order which is: Parse → Compile (scripts) → Layout → Flatten → Render → Event.

---

## 6. Clarity, Structure & Usability Issues

### 6.1 docs-path.md Missing Key Documents

**File to update**: `docs/docs-path.md`

The learning path is missing entries for `API.md` and `PUREE_SPEC.md` — two of the most important reference documents.

### 6.2 Display Value Case Sensitivity Needs Prominent Warning

**Files to update**: `docs/DOCS.md`, `docs/PUREE_SPEC.md`

The case mismatch between CSS (`display: none`) and Python (`style.display = 'NONE'`) is mentioned in multiple docs but never with the visual prominence it deserves. This is one of the top debugging issues. Add a callout/warning block.

### 6.3 Font Selection Process Unclear

**Files to update**: `docs/DOCS.md` or `docs/PUREE_SPEC.md`

Docs state "font names omit extensions" and show `font: NeueMontreal-Bold`, but don't explain:
- Where fonts are loaded from (`fonts/` directory in addon root)
- What font variants are available (depends on what .ttf/.otf files exist)
- How `FontManager.resolve_font_variant()` maps weight/style to font files
- Whether system fonts work (they don't — only fonts in `fonts/` directory)

### 6.4 Component Namespace Convention Needs Diagram

**File to update**: `docs/COMPONENTS.md`

The double-naming pattern (`instance_component_child`) deserves a clear table. When a component `button` with child `label` is instantiated as `my_btn`, the child becomes `my_btn_button_label`. Add an explicit example table:

```
Component: button.yaml (root: button, child: label)
Instance ID: my_btn

Result:
  my_btn         ← root container (class remapped to my_btn)
  my_btn_label   ← child (prefixed with instance id)
```

### 6.5 Duplicate Content Between PUREE_SPEC and API.md

**Recommendation** (not a required fix): PUREE_SPEC and API.md both cover CSS properties, container properties, event handlers, and modules with slight variations. Consider having PUREE_SPEC reference API.md for complete property tables rather than duplicating them.

### 6.6 `pointer-events: none` Behavior Unexplained

**Files to update**: `docs/PUREE_VS_CSS.md`, `docs/API.md`

Listed as a supported property but no documentation explains:
- Does it prevent hover/click detection? (Yes)
- Does it affect children? (Yes — children also become non-interactive)
- What's the use case? (Overlay containers that shouldn't block clicks to elements below)

---

## 7. Prioritized Recommendations

### CRITICAL Priority (Must Fix)

| # | Issue | Action | Files to Edit |
|---|-------|--------|---------------|
| 1 | CSS unit support is wrong everywhere | Update all 15+ files to document `rem`, `em`, `vw`, `vh`, `vmin`, `vmax`, `calc()` as supported. Remove from "unsupported" lists. Keep `fr`, `clamp()`, `min()`, `max()` as genuinely unsupported. | See table in Section 3.1 — all 17 files listed |
| 2 | Review skill flags valid code as errors | Remove or correct the check in `review/SKILL.md` that flags `em`/`rem`/`vw`/`vh` as "🔴 Critical: Unsupported units" | `.agents/skills/review/SKILL.md` + scaffold copy |

### HIGH Priority

| # | Issue | Action | Files to Edit |
|---|-------|--------|---------------|
| 3 | `keys` property undocumented | Add `.keys` property to Container Properties section with example: `container.keys.bind("CTRL+N", callback)` | `docs/API.md`, `docs/PUREE_SPEC.md` |
| 4 | Missing complete examples for built-in modules | Add complete working examples for markdown, virtual scroll, collapse, keyboard shortcuts | `docs/PUREE_SPEC.md` (Section 9) |
| 5 | `display: block` behavior undefined | Document what `block` does vs `flex` (children stack vertically, fill parent width, no flex properties) | `docs/PUREE_VS_CSS.md`, `docs/PUREE_SPEC.md` |
| 6 | `border` shorthand limitation | Note that `border: 2px solid red` only reliably sets width; use `border-color` separately for color | `docs/PUREE_SPEC.md`, `docs/PUREE_VS_CSS.md` |
| 7 | Add useful skills to scaffold | Copy `diagnose/`, `perf/`, `extend-property/`, `trace/` skill dirs to scaffold | `puree/scaffold/.agents/skills/` |

### MEDIUM Priority

| # | Issue | Action | Files to Edit |
|---|-------|--------|---------------|
| 8 | Display value case warning | Add prominent warning/callout about CSS lowercase vs Python UPPERCASE | `docs/DOCS.md`, `docs/PUREE_SPEC.md` |
| 9 | `_toggle_value` vs `_toggled` confusion | Add clear distinction: state (persistent) vs event flag (transient) | `docs/API.md` |
| 10 | Font loading process unclear | Add section explaining fonts/ directory, available variants, no system fonts | `docs/DOCS.md` or `docs/PUREE_SPEC.md` |
| 11 | `set_markdown()` vs `render_markdown()` | Pick `container.set_markdown()` as canonical, document full signature | `docs/API.md` |
| 12 | Missing `classes` and `layer` in API.md | Add to Container Properties table | `docs/API.md` |
| 13 | docs-path.md incomplete | Add API.md and PUREE_SPEC.md entries | `docs/docs-path.md` |
| 14 | `pointer-events: none` unexplained | Document behavior (prevents hover/click, affects children, use cases) | `docs/PUREE_VS_CSS.md`, `docs/API.md` |
| 15 | Scrollbar properties under-documented | Add `scrollbar-color`, `scrollbar-thumb-color`, `scrollbar-track-color` to SCSS docs | `docs/PUREE_SPEC.md`, `.github/instructions/puree-scss.instructions.md` (+ scaffold copy) |
| 16 | Component namespace needs diagram | Add explicit naming transformation table | `docs/COMPONENTS.md` |
| 17 | Pipeline order inconsistency | Note `index.md` shows simplified view; actual order is Parse → Compile → Layout → Flatten → Render → Event | `docs/index.md` |

---

## 8. Implementation Checklist

For the implementing agent, here's the exact order of operations:

### Step 1: Fix Critical Unit Documentation (all 17 files)
For each file listed in Section 3.1:
1. Find the incorrect claim about units
2. Replace with accurate information: `px`, `%`, `rem`, `em`, `vw`, `vh`, `vmin`, `vmax`, and `calc()` are supported. `fr`, `clamp()`, `min()`, `max()` are NOT supported.
3. In "What Puree Doesn't Support" lists: remove `calc()`, `em`, `rem`, `vw`, `vh` — keep `clamp()`, `min()`, `max()`, `fr`

### Step 2: Fix Review Skill (2 files)
- `.agents/skills/review/SKILL.md` — Change the unsupported units check
- `puree/scaffold/.agents/skills/review/SKILL.md` — Same change

### Step 3: Update docs/API.md
- Add `keys` property to Container Properties
- Add `classes` and `layer` to Container Properties  
- Clarify `_toggle_value` vs `_toggled`
- Clarify `set_markdown()` full signature
- Document `pointer-events: none` behavior

### Step 4: Update docs/PUREE_SPEC.md
- Add `keys` property mention in events section
- Add complete examples for markdown, virtual scroll, collapse, keyboard
- Document `display: block` behavior
- Add display case sensitivity warning
- Document `border` shorthand limitation
- Document scrollbar customization properties

### Step 5: Update docs/PUREE_VS_CSS.md
- Fix unsupported features list (remove units that ARE supported)
- Document `display: block` behavior
- Document `border` shorthand limitation
- Document `pointer-events: none` behavior

### Step 6: Update other docs
- `docs/DOCS.md` — Add display case warning, font loading section
- `docs/SUPPORT.md` — Fix unit FAQ answer
- `docs/docs-path.md` — Add missing document entries
- `docs/index.md` — Note simplified pipeline view
- `docs/COMPONENTS.md` — Add namespace transformation diagram

### Step 7: Update AI instruction files (+ scaffold copies)
- `.github/instructions/puree-scss.instructions.md` — Fix units, add scrollbar props
- `.github/agents/puree-coder.agent.md` — Fix units reference
- `.github/prompts/new-puree-panel.prompt.md` — Fix units reference
- All corresponding files in `puree/scaffold/`

### Step 8: Copy skills to scaffold
- Copy `.agents/skills/diagnose/` → `puree/scaffold/.agents/skills/diagnose/`
- Copy `.agents/skills/perf/` → `puree/scaffold/.agents/skills/perf/`
- Copy `.agents/skills/extend-property/` → `puree/scaffold/.agents/skills/extend-property/`
- Copy `.agents/skills/trace/` → `puree/scaffold/.agents/skills/trace/`

---

## 9. Reference: What the Code Actually Supports

For the implementing agent's reference, here is the verified ground truth from `puree/parser.py`:

### Supported CSS Units
| Unit | Implementation | Notes |
|------|---------------|-------|
| `px` | Direct pixel value | Default if no unit specified |
| `%` | Percentage of parent | Passed through to Taffy layout engine |
| `rem` | `value × root_font_size` | Root font-size defaults to 16px |
| `em` | `value × parent_font_size` | Parent font-size defaults to 16px |
| `vw` | `value × (viewport_width / 100)` | Viewport-relative |
| `vh` | `value × (viewport_height / 100)` | Viewport-relative |
| `vmin` | `value × (min(vw, vh) / 100)` | Smaller viewport dimension |
| `vmax` | `value × (max(vw, vh) / 100)` | Larger viewport dimension |
| `calc()` | Expression with `+` and `-` | Supports mixed units: `calc(100% - 20px)` |

### NOT Supported CSS Units
| Unit | Status |
|------|--------|
| `fr` | Not implemented (grid fractional) |
| `clamp()` | Not implemented |
| `min()` | Not implemented |
| `max()` | Not implemented |
| `ch` | Not implemented |
| `ex` | Not implemented |
| `cap` | Not implemented |

### Calc Limitations
- Only `+` and `-` operators (no `*` or `/`)
- Percentages inside `calc()` are resolved to pixels immediately (not passed as % to Taffy) — this means `calc(100% - 20px)` resolves based on viewport size, not parent size
