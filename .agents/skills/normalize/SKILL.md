---
name: normalize
description: Normalize Puree UI (YAML/SCSS) design to match your SCSS variables and component patterns, ensuring consistency
user-invocable: true
argument-hint: 'Describe the component or pattern to normalize (e.g. "button styles", "spacing tokens")'
---

Analyze and align a Puree feature to perfectly match your established SCSS variables, component patterns, and design conventions.

## MANDATORY PREPARATION

Use the frontend-design skill — it contains design principles, anti-patterns, and the **Context Gathering Protocol**. Follow the protocol before proceeding — if no design context exists yet, you MUST run teach-impeccable first.

---

## Plan

Before making changes, deeply understand the context:

1. **Discover the design conventions**: Search for SCSS variable definitions, component files, and style patterns. Study them until you understand:
   - Core design principles and aesthetic direction
   - SCSS variables (colors, spacing, typography, borders)
   - Component patterns (naming, parameter conventions)
   - Layout conventions (flex vs grid usage, spacing rhythm)
   
   **CRITICAL**: If something isn't clear, ask. Don't guess at design conventions.

2. **Analyze the current feature**: Assess what works and what doesn't:
   - Where does it deviate from established SCSS variable usage?
   - Which inconsistencies are cosmetic vs. functional?
   - What's the root cause — missing variables, one-off implementations, or conceptual misalignment?

3. **Create a normalization plan**: Define specific changes that will align the feature:
   - Which SCSS rules should use existing variables instead of hard-coded values?
   - Which YAML structures can use existing components via `data: '[component]'`?
   - How can interaction patterns match established conventions?
   
   **IMPORTANT**: Great design is effective design. Prioritize UX consistency and usability over visual polish alone.

## Execute

Systematically address all inconsistencies across these dimensions:

- **Typography**: Use SCSS font-size variables and consistent weights. Replace hard-coded values with variables. Ensure fonts are loaded via YAML `font:` attribute.

```scss
// Before: inconsistent
.title { font-size: 18px; color: #e0e0e0; }
.subtitle { font-size: 15px; color: #bbb; }

// After: normalized
.title { font-size: $font-size-lg; color: $text-primary; }
.subtitle { font-size: $font-size-md; color: $text-secondary; }
```

- **Color & Theme**: Apply SCSS color variables. Remove one-off color choices that break the palette.

```scss
// Before: hard-coded
.panel { background-color: #2a2a3e; border: 1px solid rgba(255, 255, 255, 0.1); }

// After: using variables
.panel { background-color: $surface; border: $border-subtle; }
```

- **Spacing & Layout**: Use SCSS spacing variables (margins, padding, gaps). Align with layout patterns used elsewhere.
- **Components**: Replace repeated YAML structures with component references. Ensure parameter values match established patterns.
- **Transitions**: Match transition timing, easing, and property choices to other features. Only transition `background-color`, `color`, `border-color`, `opacity`.
- **Responsive Behavior**: Ensure `@media` breakpoints align with conventions used elsewhere.

**NEVER**:
- Create new one-off styles when SCSS variables exist for the same purpose
- Hard-code values that should use SCSS variables
- Introduce new patterns that diverge from established conventions
- Use properties Puree doesn't support (`transform`, `z-index`, `@keyframes`, `calc()`, `em`, `rem`)

This is not an exhaustive list — apply judgment to identify all areas needing normalization.

## Clean Up

After normalization, ensure code quality:

- **Consolidate reusable components**: If you created new components that should be shared, move them to the components directory.
- **Remove orphaned code**: Delete unused SCSS rules, YAML nodes, or Python handlers made obsolete by normalization.
- **Verify quality**: Ensure normalization didn't introduce visual regressions.
- **Ensure DRYness**: Look for duplication introduced during refactoring and consolidate.

Remember: You are a brilliant UI designer with impeccable taste. Your attention to detail and eye for end-to-end user experience is world class. Execute with precision and thoroughness.
