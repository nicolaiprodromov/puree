---
name: extract
description: Extract and consolidate reusable Puree components, SCSS variables, and patterns. Identifies opportunities for systematic reuse and enriches your component library.
user-invocable: true
argument-hint: 'Describe the YAML pattern or SCSS tokens to extract (e.g. "repeated button styles", "color variables")'
---

Identify reusable patterns, components, and SCSS variables in a Puree project, then extract and consolidate them for systematic reuse.

## Discover

Analyze the target area to identify extraction opportunities:

1. **Find the component library**: Locate your components directory (specified via `components:` in the theme config). Understand its structure:
   - Component YAML files and naming conventions
   - SCSS variable organization
   - Parameter patterns (`{{param, 'default'}}`)
   
   **CRITICAL**: If no component directory exists, ask before creating one. Understand the preferred location and structure first.

2. **Identify patterns**: Look for:
   - **Repeated YAML structures**: Similar node hierarchies used multiple times (buttons, cards, list items, etc.)
   - **Hard-coded values**: Colors, spacing, font sizes that should be SCSS variables
   - **Inconsistent variations**: Multiple implementations of the same concept (3 different button styles in SCSS)
   - **Reusable patterns**: Layout patterns, interaction patterns worth systematizing

3. **Assess value**: Not everything should be extracted. Consider:
   - Is this used 3+ times, or likely to be reused?
   - Would systematizing this improve consistency?
   - Is this a general pattern or context-specific?
   - What's the maintenance cost vs benefit?

## Plan Extraction

Create a systematic extraction plan:

- **Components to extract**: Which YAML structures become reusable `.yaml` component files?
- **SCSS variables to create**: Which hard-coded values become variables?
- **Variants to support**: What parameters does each component need?
- **Naming conventions**: Component names, parameter names, SCSS variable names that match existing patterns
- **Migration path**: How to refactor existing YAML to use the new components via `data: '[component_name]'`

**IMPORTANT**: Component libraries grow incrementally. Extract what's clearly reusable now, not everything that might someday be reusable.

## Extract & Enrich

Build improved, reusable versions:

### Components

Create well-designed `.yaml` component files:

```yaml
# static/components/action_button.yaml
action_button:
  class: "{{btn_class, 'btn_primary'}}"
  btn_label:
    class: "{{label_class, 'btn_label'}}"
    text: "{{btn_text, 'Action'}}"
    passive: true
```

With corresponding SCSS:

```scss
.btn_primary {
  background-color: $accent;
  border-radius: 6px;
  padding: 8px 16px;
  transition: background-color 0.2s ease;

  &:hover {
    background-color: $accent-hover;
  }

  &:active {
    background-color: $accent-active;
  }
}

.btn_label {
  color: #fff;
  font-size: 14px;
  text-align: center;
}
```

Usage in YAML:

```yaml
toolbar:
  save_button:
    data: '[action_button]'
    btn_text: Save
    btn_class: btn_primary
  cancel_button:
    data: '[action_button]'
    btn_text: Cancel
    btn_class: btn_secondary
```

### SCSS Variables

Create organized variable definitions:

```scss
// Colors
$accent: #3498db;
$accent-hover: lighten($accent, 10%);
$accent-active: darken($accent, 10%);
$surface: #1e1e2e;
$text-primary: rgba(255, 255, 255, 0.9);
$text-secondary: rgba(255, 255, 255, 0.6);

// Spacing
$space-xs: 4px;
$space-sm: 8px;
$space-md: 16px;
$space-lg: 32px;

// Typography
$font-size-sm: 12px;
$font-size-md: 14px;
$font-size-lg: 18px;
$font-size-xl: 24px;

// Borders
$border-radius-sm: 4px;
$border-radius-md: 8px;
$border-radius-lg: 12px;
$border-subtle: 1px solid rgba(255, 255, 255, 0.08);
```

### Patterns

Document reusable layout and interaction patterns:
- When to use each component
- Parameter options and defaults
- Combinations and compositions

**NEVER**:
- Extract one-off, context-specific implementations without generalization
- Create components so generic they're useless
- Extract without considering existing component conventions
- Create SCSS variables for every single value (variables should have semantic meaning)
- Use hyphens in YAML node names (use underscores)
- Forget to add `passive: true` to text-only child nodes in components

## Migrate

Replace existing uses with the new shared versions:

- **Find all instances**: Search for the YAML patterns you've extracted
- **Replace systematically**: Update each use to reference the component via `data: '[component_name]'` with appropriate params
- **Test thoroughly**: Ensure visual and functional parity
- **Delete dead code**: Remove the old inline YAML structures and unused SCSS rules

## Document

Update project documentation:

- Add new components to any component catalog or README
- Document parameter options, defaults, and usage examples
- Note SCSS variable organization and naming conventions

Remember: A good component system is a living system. Extract patterns as they emerge, enrich them thoughtfully, and maintain them consistently.
