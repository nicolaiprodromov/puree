---
name: teach-impeccable
description: One-time setup that gathers design context for your Puree UI project and saves it to your AI config file. Run once to establish persistent design guidelines.
user-invocable: true
argument-hint: 'Optionally specify config file path (e.g. ".github/copilot-instructions.md")'
---

Gather design context for this Puree project, then persist it for all future sessions.

## Step 1: Explore the Codebase

Before asking questions, thoroughly scan the project to discover what you can:

- **README and docs**: Project purpose, target audience, any stated goals
- **pyproject.toml, blender_manifest.toml**: Project metadata, Blender version targets, dependencies
- **Existing YAML files**: Current component patterns, layout structure, naming conventions
- **SCSS files**: Current design patterns, spacing, typography, color palette in use
- **assets/ directory**: Images, icons — visual style and brand assets
- **fonts/ directory**: Available fonts, typographic direction
- **SCSS variables and CSS custom properties**: Existing color palettes, spacing scales, reusable values
- **PUREE_VS_CSS.md, PUREE_SPEC.md references**: Framework capabilities and constraints

Note what you've learned and what remains unclear.

## Step 2: Ask UX-Focused Questions

Ask the user directly to clarify what you cannot infer. Focus only on what you couldn't infer from the codebase:

### Users & Purpose
- Who uses this addon? What's their context when using it in Blender?
- What job are they trying to get done?
- What emotions should the interface evoke? (confidence, delight, calm, urgency, etc.)

### Brand & Personality
- How would you describe the addon's personality in 3 words?
- Any reference addons, tools, or apps that capture the right feel? What specifically about them?
- What should this explicitly NOT look like? Any anti-references?

### Aesthetic Preferences
- Any strong preferences for visual direction? (minimal, bold, elegant, playful, technical, organic, etc.)
- Dark theme only, or should it adapt to Blender's theme settings?
- Any colors that must be used or avoided?

### Blender Integration
- Which Blender panels will this appear in? (sidebar, properties, floating?)
- What panel width range should be the primary target?
- Should the UI feel like native Blender, or intentionally distinct?

Skip questions where the answer is already clear from the codebase exploration.

## Step 3: Write Design Context

Synthesize your findings and the user's answers into a `## Design Context` section:

```markdown
## Design Context

### Users
[Who they are, their Blender workflow context, the job to be done]

### Brand Personality
[Voice, tone, 3-word personality, emotional goals]

### Aesthetic Direction
[Visual tone, references, anti-references, theme approach]

### Design Principles
[3-5 principles derived from the conversation that should guide all design decisions]
```

Write this section to `.impeccable.md` in the project root. If the file already exists, update the Design Context section in place.

Then ask the user directly to clarify what you cannot infer. whether they'd also like the Design Context appended to .github/copilot-instructions.md. If yes, append or update the section there as well.

Confirm completion and summarize the key design principles that will now guide all future work.