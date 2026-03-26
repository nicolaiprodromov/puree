---
description: "Quick-start orientation for AI agents new to this Puree project. Run this first in any new conversation to get up to speed."
agent: puree-coder
argument-hint: "Optionally specify focus area or leave blank for full orientation"
---

Get oriented with this Puree UI project. Read the key files to understand the addon, how it works, and what conventions to follow.

## Orientation Steps

Read these files in order:
1. `.github/copilot-instructions.md` — Project overview and critical rules
2. `static/index.yaml` — Current UI structure
3. `static/style.scss` — Current styles
4. `static/script.py` — Current event handlers
5. `static/components/` — Available components
6. `fonts/` — Available fonts
7. `assets/` — Available images
8. `docs/.impeccable.md` — Design context (if it exists — run `/teach-impeccable` if not)

Then use the `puree-coder` agent for implementation.

## Quick Reference

| Task | Skill |
|------|-------|
| Build a new panel | `/frontend-design` |
| Debug a panel | `/review` or use `puree-debug` prompt |
| Create a component | Use `new-puree-component` prompt |
| Scaffold a full panel | Use `new-puree-panel` prompt |
| Audit UI quality | `/audit` |
| Polish before shipping | `/polish` |
| Add animations | `/animate` |
| Improve typography | `/typeset` |
| Add color | `/colorize` |
| Fix layout | `/arrange` |
| Extract components | `/extract` |
| Harden for edge cases | `/harden` |
| Optimize performance | `/optimize` |
| Establish design context | `/teach-impeccable` |
