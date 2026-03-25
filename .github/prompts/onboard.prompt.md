---
description: "Quick-start orientation for AI agents new to the Puree codebase. Run this first in any new conversation to get up to speed."
agent: agent
argument-hint: "Optionally specify focus area: 'ui' for panel work, 'engine' for codebase work, or leave blank for overview"
---

Get oriented with the Puree project. Read the key files to understand what Puree is, how it works, and what conventions to follow.

## For UI Work (YAML/SCSS/Python panels)

Read these files in order:
1. `.github/copilot-instructions.md` — Project overview and critical rules
2. `docs/PUREE_SPEC.md` — Complete framework specification with examples
3. `.impeccable.md` — Design context and aesthetic direction
4. An example panel (e.g., `static/index.yaml`, `static/style.scss`, `static/script.py`)
5. Check `fonts/` for available fonts, `assets/` for available images

Then use the `puree-coder` agent for implementation.

## For Engine Work (Python/Rust/GLSL internals)

Read these files in order:
1. `.github/copilot-instructions.md` — Project overview
2. `docs/KNOWLEDGE_BASE.md` — Architecture decisions, patterns, gotchas
3. `.github/agents/puree-maintainer.agent.md` — Module map and pipeline details
4. The specific module you'll be working on (e.g., `puree/render.py`)

Then use the `puree-maintainer` agent for implementation.

## Quick Reference

| Task | Agent | Key Skill |
|------|-------|-----------|
| Build a new panel | `puree-coder` | `/frontend-design` |
| Debug a panel | `puree-coder` | `/review` |
| Create a component | `puree-coder` | Use `new-puree-component` prompt |
| Fix an engine bug | `puree-maintainer` | `/diagnose` |
| Add a CSS property | `puree-maintainer` | `/extend-property` |
| Trace data flow | `puree-maintainer` | `/trace` |
| Profile performance | `puree-maintainer` | `/perf` |
| Audit UI quality | `puree-coder` | `/audit` |
| Polish before shipping | `puree-coder` | `/polish` |
