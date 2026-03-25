# Puree — Agent & Skill Registry

> This file documents all available AI agents, skills, prompts, and instructions
> for working with the Puree project. It serves as the discovery index.

## Agents

| Agent | Purpose | Use When |
|-------|---------|----------|
| `puree-coder` | Build and modify Puree UI (YAML/SCSS/Python) | Creating panels, components, styling, event handlers |
| `puree-maintainer` | Fix and extend the Puree engine (Python/Rust/GLSL) | Engine bugs, new CSS properties, renderer, parser |

## Skills

### UI Design & Quality (puree-coder)

| Skill | Purpose |
|-------|---------|
| `/frontend-design` | Create production-grade Puree UI with high design quality |
| `/review` | Code review for correctness and best practices |
| `/audit` | Comprehensive audit across theming, layout, consistency |
| `/critique` | Holistic design evaluation from UX perspective |
| `/polish` | Final quality pass — alignment, spacing, details |
| `/harden` | Resilience — text overflow, error states, edge cases |
| `/optimize` | UI-level performance — container count, transitions |

### Visual & Aesthetic (puree-coder)

| Skill | Purpose |
|-------|---------|
| `/colorize` | Add strategic color to monochromatic designs |
| `/bolder` | Amplify safe designs with visual interest |
| `/quieter` | Tone down overly aggressive designs |
| `/typeset` | Improve typography — hierarchy, sizing, weights |

### Layout & Composition (puree-coder)

| Skill | Purpose |
|-------|---------|
| `/arrange` | Improve layout, spacing, visual rhythm |
| `/distill` | Strip to essence — remove unnecessary complexity |
| `/adapt` | Work across different panel sizes |

### Interaction & UX (puree-coder)

| Skill | Purpose |
|-------|---------|
| `/animate` | Add purposeful transitions and state changes |
| `/delight` | Add moments of joy and personality |
| `/clarify` | Improve UX copy, labels, instructions |
| `/onboard` | Design onboarding flows and empty states |

### Consistency & Maintenance (puree-coder)

| Skill | Purpose |
|-------|---------|
| `/normalize` | Align with SCSS variables and component patterns |
| `/extract` | Create reusable components, consolidate patterns |
| `/teach-impeccable` | One-time setup: persist design context to `.impeccable.md` |

### Engine Maintenance (puree-maintainer)

| Skill | Purpose |
|-------|---------|
| `/diagnose` | Diagnose and fix engine bugs (renderer, parser, events) |
| `/extend-property` | Add new CSS property through all engine layers |
| `/trace` | Trace data flow end-to-end through the engine |
| `/perf` | Profile and optimize engine performance |

### Advanced (puree-coder)

| Skill | Purpose |
|-------|---------|
| `/overdrive` | Push past conventional limits with ambitious implementations |

## Prompts

| Prompt | Purpose |
|--------|---------|
| `onboard` | Quick-start orientation for new agents |
| `new-puree-panel` | Scaffold a complete working panel |
| `new-puree-component` | Scaffold a reusable component |
| `puree-debug` | Debug a user-facing panel issue |
| `puree-engine-debug` | Debug an engine-level issue |
| `add-css-property` | Checklist for adding a new CSS property |

## Instruction Files

| File | Applies To | Covers |
|------|-----------|--------|
| `puree-yaml.instructions.md` | `**/*.yaml` | YAML structure, naming, theme config |
| `puree-scss.instructions.md` | `**/*.scss` | SCSS properties, selectors, limitations |
| `puree-script.instructions.md` | `**/script.py` | Python API, events, mark_dirty() |
| `puree-components.instructions.md` | `**/components/**` | Component YAML/SCSS, parameters |
| `puree-engine.instructions.md` | `puree/*.py` | Engine modules, operators, threading |
| `puree-shaders.instructions.md` | `puree/shaders/*.glsl` | GPU buffers, coords, color space |
| `puree-rust.instructions.md` | `puree/puree_core/**` | PyO3, Rust components, build workflow |

## Context Files

| File | Purpose | Loaded By |
|------|---------|-----------|
| `.github/copilot-instructions.md` | Global project context | Every Copilot conversation (automatic) |
| `.impeccable.md` | Design context and aesthetics | Design skills (automatic) |
| `docs/KNOWLEDGE_BASE.md` | Institutional knowledge, gotchas | Manual reference |
| `/memories/repo/puree-notes.md` | Running notes and discoveries | Memory system |
