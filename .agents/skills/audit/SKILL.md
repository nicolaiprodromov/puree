---
name: audit
description: Perform comprehensive audit of Puree interface quality across theming, layout, and design consistency. Generates detailed report of issues with severity ratings and recommendations.
user-invocable: true
argument-hint: [AREA=<e.g. color, layout, typography, theming>]
---

Run systematic quality checks on a Puree interface and generate a comprehensive audit report with prioritized issues and actionable recommendations. Don't fix issues — document them for other commands to address.

**First**: Use the frontend-design skill for design principles and anti-patterns.

## Diagnostic Scan

Run comprehensive checks across multiple dimensions:

1. **Theming & Style Consistency** - Check for:
   - **Hard-coded colors**: Colors not using SCSS variables (e.g., raw `#ff0000` instead of `$error`)
   - **Inconsistent SCSS variables**: Using wrong variables, mixing unrelated tokens
   - **Missing theme support**: Values that don't adapt across themes
   - **Contrast issues**: Text contrast ratios < 4.5:1 against backgrounds
   - **Color misuse**: Gray text on colored backgrounds, pure black/white in large areas

2. **Layout & Structure** - Check for:
   - **Fixed widths**: Hard-coded widths that break at different panel sizes
   - **Missing `@media` breakpoints**: No adaptation for narrow/wide panels
   - **Arbitrary spacing**: Pixel values not from a consistent SCSS spacing scale
   - **Overcrowded layout**: Elements packed too tightly without breathing room
   - **Deep YAML nesting**: Excessively nested node hierarchies that could be flattened

3. **YAML & Component Quality** - Check for:
   - **Unused YAML nodes**: Nodes that exist in YAML but have no visible purpose
   - **Missing `class:` attributes**: Nodes that should have SCSS classes but don't
   - **Inconsistent naming**: Node names not using underscores, or mixing naming patterns
   - **Component duplication**: Repeated YAML patterns that should be extracted into components
   - **Missing component params**: Hard-coded values in components that should use `{{param, 'default'}}` syntax

4. **Python / Interactivity** - Check for:
   - **Missing `mark_dirty()` calls**: Property changes via `set_property()` or `.text =` without `mark_dirty()`
   - **Unused event handlers**: Click/hover handlers that don't do anything meaningful
   - **Missing `return app`**: Script `main()` functions that don't return `app`
   - **Hard-coded colors in Python**: Raw color strings instead of referencing SCSS-defined values
   - **Missing error handling**: Event handlers without try/except for robustness

5. **Transitions** - Check for:
   - **Missing hover states**: Interactive elements without `:hover` feedback
   - **Missing active states**: Clickable elements without `:active` feedback
   - **Non-animatable properties in transitions**: Trying to transition properties Puree can't animate (only `background-color`, `color`, `border-color`, `opacity`)
   - **Excessive transition durations**: Transitions over 500ms for interactive feedback

6. **Anti-Patterns (CRITICAL)** - Check against ALL the **DON'T** guidelines in the frontend-design skill. Look for AI slop tells (AI color palette, gradient text, glassmorphism, hero metrics, card grids, generic fonts) and general design anti-patterns (gray on color, nested cards, redundant copy).

**CRITICAL**: This is an audit, not a fix. Document issues thoroughly with clear explanations of impact. Use other commands to fix issues after audit.

## Generate Comprehensive Report

Create a detailed audit report with the following structure:

### Anti-Patterns Verdict
**Start here.** Pass/fail: Does this look AI-generated? List specific tells from the skill's Anti-Patterns section. Be brutally honest.

### Executive Summary
- Total issues found (count by severity)
- Most critical issues (top 3-5)
- Recommended next steps

### Detailed Findings by Severity

For each issue, document:
- **Location**: Where the issue occurs (file, YAML node, SCSS rule, Python function)
- **Severity**: Critical / High / Medium / Low
- **Category**: Theming / Layout / YAML / Python / Transitions / Anti-Pattern
- **Description**: What the issue is
- **Impact**: How it affects the interface
- **Recommendation**: How to fix it
- **Suggested command**: Which command to use (prefer: /animate, /quieter, /clarify, /distill, /delight, /onboard, /normalize, /audit, /harden, /polish, /extract, /bolder, /arrange, /typeset, /critique, /colorize, /overdrive — or other installed skills you're sure exist)

#### Critical Issues
[Issues that break functionality or violate core design principles]

#### High-Severity Issues
[Significant usability or consistency impact]

#### Medium-Severity Issues
[Quality issues, inconsistencies, missed opportunities]

#### Low-Severity Issues
[Minor inconsistencies, optimization opportunities]

### Patterns & Systemic Issues

Identify recurring problems:
- "Hard-coded colors appear in 15+ SCSS rules — should use SCSS variables"
- "No `:hover` states on any interactive elements"
- "Missing `mark_dirty()` after all `set_property()` calls in script.py"

### Positive Findings

Note what's working well:
- Good practices to maintain
- Exemplary implementations to replicate elsewhere

### Recommendations by Priority

Create actionable plan:
1. **Immediate**: Critical blockers to fix first
2. **Short-term**: High-severity issues
3. **Medium-term**: Quality improvements
4. **Long-term**: Nice-to-haves and polish

### Suggested Commands for Fixes

Map issues to available commands. Prefer these: /animate, /quieter, /clarify, /distill, /delight, /onboard, /normalize, /audit, /harden, /polish, /extract, /bolder, /arrange, /typeset, /critique, /colorize, /overdrive. You may also suggest other installed skills you're sure exist, but never invent commands.

Examples:
- "Use `/normalize` to align SCSS variables with design system (addresses N theming issues)"
- "Use `/extract` to create reusable components (addresses N duplication issues)"
- "Use `/animate` to add missing hover/active transitions (addresses N feedback issues)"

**IMPORTANT**: Be thorough but actionable. Too many low-priority issues creates noise. Focus on what actually matters.

**NEVER**:
- Report issues without explaining impact (why does this matter?)
- Mix severity levels inconsistently
- Skip positive findings (celebrate what works)
- Provide generic recommendations (be specific and actionable)
- Forget to prioritize (everything can't be critical)
- Report false positives without verification
- Suggest web-specific fixes (ARIA, keyboard nav, screen readers, Lighthouse) — this is Puree, not a browser

Remember: You're a quality auditor with exceptional attention to detail. Document systematically, prioritize ruthlessly, and provide clear paths to improvement. A good audit makes fixing easy.