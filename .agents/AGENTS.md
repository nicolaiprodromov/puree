# Puree AI Agent Ecosystem

This document catalogs all agents, skills, prompts, and instruction files available for working with Puree.

---

## Agents

| Agent | Purpose | Use When |
|-------|---------|----------|
| **puree-coder** | Build, modify, or debug Puree UI (YAML/SCSS/Python) | Creating panels, adding components, writing event handlers, fixing render issues, styling |
| **puree-maintainer** | Maintain and extend the Puree engine (Python, Rust, GLSL) | Fixing engine bugs, adding CSS properties, extending parser/compiler, optimizing rendering |

---

## Skills (26 total)

### UI Design & Creation
| Skill | Purpose |
|-------|---------|
| `/frontend-design` | Create distinctive, production-grade Puree interfaces. Anti-"AI slop" design guidance. |
| `/onboard` | Design onboarding flows, empty states, and first-time user experiences |

### Visual & Aesthetic
| Skill | Purpose |
|-------|---------|
| `/colorize` | Add strategic color to monochromatic UIs |
| `/typeset` | Improve font choices, hierarchy, sizing, weight, readability |
| `/animate` | Add purposeful transitions and state changes (200–500ms range) |
| `/bolder` | Amplify safe or boring designs to be more visually interesting |
| `/quieter` | Tone down overly bold or aggressive designs |
| `/delight` | Add moments of joy, personality, and memorable touches |

### Layout & Structure
| Skill | Purpose |
|-------|---------|
| `/arrange` | Improve layout, spacing, and visual rhythm |
| `/adapt` | Make designs work across different panel sizes and workspaces |
| `/distill` | Strip designs to their essence — remove unnecessary complexity |

### Interaction & Robustness
| Skill | Purpose |
|-------|---------|
| `/harden` | Improve resilience: text overflow, error states, edge cases |
| `/optimize` | Improve rendering speed, container efficiency, resource usage |
| `/clarify` | Improve UX copy, error messages, labels, instructions |

### Quality & Consistency
| Skill | Purpose |
|-------|---------|
| `/audit` | Comprehensive quality audit across theming, layout, and design |
| `/review` | Code review for correctness, common mistakes, best practices |
| `/critique` | Evaluate design effectiveness from a UX perspective |
| `/polish` | Final quality pass — alignment, spacing, consistency, details |
| `/normalize` | Ensure consistency with SCSS variables and component patterns |
| `/extract` | Consolidate reusable components, SCSS variables, and patterns |

### Engine & Advanced (maintainer-only)
| Skill | Purpose |
|-------|---------|
| `/diagnose` | Diagnose and fix bugs in the Puree engine (renderer, parser, layout, events) |
| `/extend-property` | Add a new CSS property across all engine layers (Style → Rust → GPU → GLSL) |
| `/trace` | Trace data flow through the engine for a specific feature end-to-end |
| `/perf` | Profile and optimize engine performance (GPU, layout, buffers, frames) |
| `/overdrive` | Push beyond conventional limits with technically ambitious implementations |

### Setup
| Skill | Purpose |
|-------|---------|
| `/teach-impeccable` | One-time setup to gather and save design context for your project |

---

## Skill Workflows

Common skill combinations for different goals:

| Goal | Workflow |
|------|---------|
| **Design a new panel** | `/frontend-design` → `/review` → `/polish` |
| **Full quality audit** | `/audit` → `/normalize` → `/polish` → `/review` |
| **Visual refresh** | `/critique` → `/colorize` → `/typeset` → `/arrange` |
| **Production hardening** | `/harden` → `/optimize` → `/review` |
| **Add a CSS property** | `/trace` → `/extend-property` → `/diagnose` (if issues) |
| **Debug engine issue** | `/diagnose` → `/trace` → `/perf` (if performance-related) |

---

## Prompts

Reusable prompt templates in `.github/prompts/`:

| Prompt | Purpose |
|--------|---------|
| `new-puree-panel` | Scaffold a new Puree panel (YAML + SCSS + Python + __init__.py) |
| `new-puree-component` | Create a new reusable component |
| `puree-debug` | Systematic YAML/SCSS/Python debugging checklist |
| `puree-engine-debug` | Engine-level debugging (renderer, parser, hit detection) |
| `add-css-property` | Step-by-step guide to add a new CSS property to the engine |
| `implement-feature` | Plan and implement a new engine feature |
| `onboard` | Generate onboarding content for new Puree users |

---

## Instruction Files

Context files loaded automatically based on file type:

| File | Applies To | Content |
|------|-----------|---------|
| `puree-yaml.instructions.md` | `**/*.yaml` | YAML syntax, theme config, node structure, naming rules |
| `puree-scss.instructions.md` | `**/*.scss` | Supported properties, transitions, selectors, extensions |
| `puree-script.instructions.md` | `**/script.py` | `main()` signature, events, `mark_dirty()`, container API |
| `puree-components.instructions.md` | `**/components/**` | Component structure, parameters, namespacing, instantiation |
| `puree-engine.instructions.md` | `puree/*.py` | Module map, registration, ModernGL, Blender operators |
| `puree-rust.instructions.md` | `puree/puree_core/**` | PyO3, HitDetector, SCSSCompiler, build workflow |
| `puree-shaders.instructions.md` | `puree/shaders/*.glsl` | Buffer layout (68-float stride), coordinate system, color space |

---

## Context Files

Persistent knowledge loaded into every conversation:

| File | Purpose |
|------|---------|
| `.github/copilot-instructions.md` | High-level framework overview, repository structure, critical rules |
| `docs/KNOWLEDGE_BASE.md` | Architecture decisions, debugging cheat sheet, patterns |
