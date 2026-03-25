---
name: distill
description: Strip Puree UI designs to their essence by removing unnecessary complexity. Great design is simple, powerful, and clean.
user-invocable: true
argument-hint: 'Describe the component or panel to simplify (e.g. "settings panel", "toolbar layout")'
---

Remove unnecessary complexity from Puree designs, revealing the essential elements and creating clarity through ruthless simplification.

## MANDATORY PREPARATION

Use the frontend-design skill — it contains design principles, anti-patterns, and the **Context Gathering Protocol**. Follow the protocol before proceeding — if no design context exists yet, you MUST run teach-impeccable first.

---

## Assess Current State

Analyze what makes the design feel complex or cluttered:

1. **Identify complexity sources**:
   - **Too many elements**: Competing buttons, redundant information, visual clutter
   - **Excessive variation**: Too many colors, fonts, sizes, styles without purpose
   - **Information overload**: Everything visible at once, no progressive disclosure
   - **Visual noise**: Unnecessary borders, shadows, backgrounds, decorations
   - **Confusing hierarchy**: Unclear what matters most
   - **Feature creep**: Too many options, actions, or paths forward

2. **Find the essence**:
   - What's the primary user goal? (There should be ONE)
   - What's actually necessary vs nice-to-have?
   - What can be removed, hidden, or combined?
   - What's the 20% that delivers 80% of value?

If any of these are unclear from the codebase, ask the user directly to clarify what you cannot infer.

**CRITICAL**: Simplicity is not about removing features — it's about removing obstacles between users and their goals. Every element should justify its existence.

## Plan Simplification

Create a ruthless editing strategy:

- **Core purpose**: What's the ONE thing this should accomplish?
- **Essential elements**: What's truly necessary to achieve that purpose?
- **Progressive disclosure**: What can be hidden until needed?
- **Consolidation opportunities**: What can be combined or integrated?

**IMPORTANT**: Simplification is hard. It requires saying no to good ideas to make room for great execution. Be ruthless.

## Simplify the Design

Systematically remove complexity across these dimensions:

### Information Architecture
- **Reduce scope**: Remove secondary actions, optional features, redundant information
- **Progressive disclosure**: Hide complexity behind clear entry points (use `display: none` + Python to reveal on demand)
- **Combine related actions**: Merge similar buttons, consolidate options, group related content
- **Clear hierarchy**: ONE primary action, few secondary actions, everything else tertiary or hidden
- **Remove redundancy**: If it's said elsewhere, don't repeat it here

### Visual Simplification
- **Reduce color palette**: Use 1-2 SCSS color variables plus neutrals, not 5-7 colors
- **Limit typography**: One font family, 3-4 sizes maximum, 2-3 weights
- **Remove decorations**: Eliminate borders, shadows, backgrounds that don't serve hierarchy
- **Flatten structure**: Reduce YAML nesting, remove unnecessary container nodes — never nest cards inside cards
- **Remove unnecessary cards**: Cards aren't needed for basic layout; use spacing and alignment instead
- **Consistent spacing**: Use SCSS spacing variables, remove arbitrary gaps

```scss
// Before: cluttered
.panel {
  background-color: #2a2a3e;
  border: 1px solid rgba(255, 255, 255, 0.15);
  box-shadow: 0px 8px 24px rgba(0, 0, 0, 0.3);
  border-radius: 12px;
}

// After: clean
.panel {
  background-color: $surface;
  border-radius: 8px;
}
```

### Layout Simplification
- **Linear flow**: Replace complex grids with simple vertical flex where possible
- **Full-width**: Use available space generously instead of complex multi-column layouts
- **Consistent alignment**: Pick left or center, stick with it
- **Generous whitespace**: Let content breathe, don't pack everything tight

```yaml
# Before: over-nested
content_wrapper:
  inner_wrapper:
    content_container:
      actual_content:
        text: "Hello"

# After: flat
content:
  class: content
  text: "Hello"
```

### Interaction Simplification
- **Reduce choices**: Fewer buttons, fewer options, clearer path forward
- **Smart defaults**: Make common choices automatic, only ask when necessary
- **Clear CTAs**: ONE obvious next step, not five competing actions

### Content Simplification
- **Shorter copy**: Cut every sentence in half, then do it again
- **Active voice**: "Save changes" not "Changes will be saved"
- **Remove jargon**: Plain language always wins
- **Essential information only**: Remove fluff and hedging
- **Remove redundant copy**: No headers restating intros, say it once

### Code Simplification
- **Remove unused YAML nodes**: Dead nodes that have no visible purpose
- **Remove unused SCSS**: Styles that aren't applied to any node
- **Flatten YAML trees**: Reduce nesting depth
- **Consolidate SCSS**: Merge similar styles, use SCSS variables consistently
- **Reduce component variants**: Does that component need 12 parameter options, or can 3 cover 90% of cases?

**NEVER**:
- Remove necessary functionality (simplicity ≠ feature-less)
- Make things so simple they're unclear (mystery ≠ minimalism)
- Remove information users need to make decisions
- Eliminate hierarchy completely (some things should stand out)
- Oversimplify complex domains (match complexity to actual task complexity)

## Verify Simplification

Ensure simplification improves usability:

- **Faster task completion**: Can users accomplish goals more quickly?
- **Reduced cognitive load**: Is it easier to understand what to do?
- **Still complete**: Are all necessary features still accessible?
- **Clearer hierarchy**: Is it obvious what matters most?

## Document Removed Complexity

If you removed features or options:
- Document why they were removed
- Consider if they need alternative access points
- Note any user feedback to monitor

Remember: Simplification is an act of confidence — knowing what to keep and courage to remove the rest. As Antoine de Saint-Exupéry said: "Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away."
