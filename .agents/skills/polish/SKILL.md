---
name: polish
description: Final quality pass before shipping. Fixes alignment, spacing, consistency, and detail issues that separate good from great.
user-invocable: true
argument-hint: [TARGET=<panel or component to polish>]
---

## MANDATORY PREPARATION

Use the frontend-design skill — it contains design principles, anti-patterns, and the **Context Gathering Protocol**. Follow the protocol before proceeding — if no design context exists yet, you MUST run teach-impeccable first. Additionally gather: quality bar (MVP vs flagship).

---

Perform a meticulous final pass to catch all the small details that separate good work from great work. The difference between shipped and polished.

## Pre-Polish Assessment

Understand the current state and goals:

1. **Review completeness**:
   - Is it functionally complete?
   - Are there known issues to preserve (mark with TODOs)?
   - What's the quality bar? (MVP vs flagship feature?)
   - When does it ship? (How much time for polish?)

2. **Identify polish areas**:
   - Visual inconsistencies
   - Spacing and alignment issues
   - Interaction state gaps
   - Copy inconsistencies
   - Edge cases and error states
   - Transition smoothness

**CRITICAL**: Polish is the last step, not the first. Don't polish work that's not functionally complete.

## Polish Systematically

Work through these dimensions methodically:

### Visual Alignment & Spacing

- **Pixel-perfect alignment**: Everything lines up consistently
- **Consistent spacing**: All gaps use SCSS spacing variables (no random 13px gaps)
- **Optical alignment**: Adjust for visual weight (use `--text-x`/`--text-y` offsets for optical centering)
- **Responsive consistency**: Spacing works at all `@media` breakpoints

**Check**:
- Review SCSS for arbitrary pixel values outside the spacing scale
- Test at multiple panel widths
- Look for elements that "feel" off

### Typography Refinement

- **Hierarchy consistency**: Same elements use same SCSS font-size variables throughout
- **Line length**: 45-75 characters for body text where possible
- **Line height**: Appropriate for font size and context
- **Kerning**: Adjust `letter-spacing` where needed (especially headlines)

### Color & Contrast

- **Contrast ratios**: All text has sufficient contrast against backgrounds
- **Consistent variable usage**: No hard-coded colors — all use SCSS variables
- **Color meaning**: Same colors mean same things throughout
- **Tinted neutrals**: No pure gray or pure black — add subtle color tint
- **Gray on color**: Never put gray text on colored backgrounds — use a shade of that color or transparency

### Interaction States

Every interactive element needs these states where applicable:

- **Default**: Resting state
- **Hover**: Subtle feedback via `:hover` (color shift, border change)
- **Active**: Click feedback via `:active` (darker color, slight opacity change)
- **Disabled**: Clearly non-interactive (reduced opacity, muted colors)

```scss
.interactive_item {
  background-color: $surface;
  transition: background-color 0.2s ease, border-color 0.2s ease;

  &:hover {
    background-color: lighten($surface, 5%);
  }

  &:active {
    background-color: darken($surface, 3%);
  }
}

.interactive_item_disabled {
  background-color: $surface;
  opacity: 0.4;
}
```

**Missing states create confusion and broken experiences.**

### Transitions

- **Smooth transitions**: All state changes on animatable properties use appropriate transitions (150-300ms)
- **Consistent easing**: Use `ease-out` or `ease-in-out` consistently
- **Appropriate scope**: Only transition `background-color`, `color`, `border-color`, `opacity`
- **Purpose**: Transitions serve function, not decoration

### Content & Copy

- **Consistent terminology**: Same things called same names throughout
- **Consistent capitalization**: Title Case vs Sentence case applied consistently
- **Grammar & spelling**: No typos
- **Appropriate length**: Not too wordy, not too terse
- **Punctuation consistency**: Periods on sentences, not on labels

### Images & Icons

- **Consistent style**: All images referenced via `img:` attribute match aesthetically
- **Appropriate sizing**: Images and icons sized consistently for context
- **Proper alignment**: Use `--img-align-h` and `--img-align-v` for positioning

### Edge Cases & Error States

- **Loading states**: All async actions have loading feedback
- **Empty states**: Helpful empty states, not just blank space
- **Error states**: Clear error messages with recovery paths
- **Success states**: Confirmation of successful actions
- **Long content**: Handles very long names/descriptions (use `text-overflow: ellipsis` and `white-space: nowrap`)
- **No content**: Handles missing data gracefully

### Responsive Layout

- **All breakpoints**: Test at various `@media` widths
- **Readable text**: No text smaller than 12px at any width
- **No overflow**: Content fits within containers (use `overflow: hidden` if needed)
- **Appropriate reflow**: Content adapts logically

### Code Quality

- **Remove debug logging**: No print statements or debug output in production (use logger instead)
- **Remove commented code**: Clean up dead SCSS and Python code
- **Consistent naming**: YAML nodes use underscores, SCSS classes follow conventions
- **`mark_dirty()` calls**: Every `set_property()` and `.text =` has a corresponding `mark_dirty()`
- **`return app`**: Every `script.py` `main()` returns `app`

## Polish Checklist

Go through systematically:

- [ ] Visual alignment consistent across all panels
- [ ] Spacing uses SCSS variables consistently
- [ ] Typography hierarchy consistent
- [ ] All interactive elements have `:hover` and `:active` states
- [ ] All transitions are smooth (only animatable properties)
- [ ] Copy is consistent and polished
- [ ] Images properly aligned and sized
- [ ] Error states are helpful
- [ ] Loading states are clear
- [ ] Empty states are welcoming
- [ ] Contrast ratios are sufficient
- [ ] No hard-coded colors (all SCSS variables)
- [ ] No debug print statements in Python
- [ ] YAML node names all use underscores
- [ ] All `set_property()` calls followed by `mark_dirty()`
- [ ] `script.py` `main()` returns `app`
- [ ] Code is clean (no TODOs, commented code, unused styles)

**IMPORTANT**: Polish is about details. Zoom in. Squint at it. Use it yourself. The little things add up.

**NEVER**:
- Polish before it's functionally complete
- Spend hours on polish if it ships in 30 minutes (triage)
- Introduce bugs while polishing (test thoroughly)
- Ignore systematic issues (if spacing is off everywhere, fix the system)
- Perfect one thing while leaving others rough (consistent quality level)

## Final Verification

Before marking as done:

- **Use it yourself**: Actually interact with the feature in Blender
- **Test all states**: Don't just test happy path
- **Compare to design**: Match intended design
- **Check at multiple widths**: If using `@media` breakpoints

Remember: You have impeccable attention to detail and exquisite taste. Polish until it feels effortless, looks intentional, and works flawlessly. Sweat the details — they matter.
