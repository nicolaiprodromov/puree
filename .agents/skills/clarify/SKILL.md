---
name: clarify
description: Improve unclear UX copy, error messages, microcopy, labels, and instructions. Makes Puree interfaces easier to understand and use.
user-invocable: true
argument-hint: 'Describe the label, message, or UI text to improve (e.g. "error messages", "tooltip copy")'
---

Identify and improve unclear, confusing, or poorly written interface text to make the product easier to understand and use.

## MANDATORY PREPARATION

Use the frontend-design skill — it contains design principles, anti-patterns, and the **Context Gathering Protocol**. Follow the protocol before proceeding — if no design context exists yet, you MUST run teach-impeccable first. Additionally gather: audience technical level and users' mental state in context.

---

## Assess Current Copy

Identify what makes the text unclear or ineffective:

1. **Find clarity problems**:
   - **Jargon**: Technical terms users won't understand
   - **Ambiguity**: Multiple interpretations possible
   - **Passive voice**: "Your file has been uploaded" vs "We uploaded your file"
   - **Length**: Too wordy or too terse
   - **Assumptions**: Assuming user knowledge they don't have
   - **Missing context**: Users don't know what to do or why
   - **Tone mismatch**: Too formal, too casual, or inappropriate for situation

2. **Understand the context**:
   - Who's the audience? (Technical Blender users? General? First-time addon users?)
   - What's the user's mental state? (Stressed during error? Confident during success?)
   - What's the action? (What do we want users to do?)
   - What's the constraint? (Character limits? Panel space limitations?)

**CRITICAL**: Clear copy helps users succeed. Unclear copy creates frustration and confusion.

## Plan Copy Improvements

Create a strategy for clearer communication:

- **Primary message**: What's the ONE thing users need to know?
- **Action needed**: What should users do next (if anything)?
- **Tone**: How should this feel? (Helpful? Apologetic? Encouraging?)
- **Constraints**: Length limits, brand voice, Blender addon context

**IMPORTANT**: Good UX writing is invisible. Users should understand immediately without noticing the words.

## Improve Copy Systematically

Refine text across these common areas:

### Error Messages
**Bad**: "Error: Operation failed"
**Good**: "Couldn't save changes. Check that the file path is valid and try again."

**Bad**: "Invalid input"
**Good**: "Enter a number between 0 and 100."

**Principles**:
- Explain what went wrong in plain language
- Suggest how to fix it
- Don't blame the user
- Include examples when helpful

### Labels & Instructions
**Bad**: "Enter value"
**Good**: "Width (px)" or "Asset name"

**Principles**:
- Use clear, specific labels
- Show format expectations with examples
- Explain why you're asking (when not obvious)

### Button & Action Text
**Bad**: "OK" | "Submit" | "Go"
**Good**: "Save Changes" | "Export" | "Apply Settings"

**Principles**:
- Describe the action specifically
- Use active voice (verb + noun)
- Match user's mental model
- Be specific ("Save" is better than "OK")

```yaml
# Good: specific action text
save_btn:
  class: btn_primary
  text: "Save Changes"

# Bad: vague
ok_btn:
  class: btn_primary
  text: "OK"
```

### Empty States
**Bad**: "No items"
**Good**: "No projects yet. Create your first project to get started."

**Principles**:
- Explain why it's empty (if not obvious)
- Show next action clearly
- Make it welcoming, not a dead-end

### Success Messages
**Bad**: "Success"
**Good**: "Settings saved! Changes take effect immediately."

**Principles**:
- Confirm what happened
- Explain what happens next (if relevant)
- Be brief but complete

### Loading States
**Bad**: "Loading..."
**Good**: "Processing your data... this usually takes a few seconds"

**Principles**:
- Set expectations (how long?)
- Explain what's happening (when it's not obvious)
- Show progress when possible

### Confirmation Dialogs
**Bad**: "Are you sure?"
**Good**: "Delete 'Project Alpha'? This can't be undone."

**Principles**:
- State the specific action
- Explain consequences (especially for destructive actions)
- Use clear button labels ("Delete project" not "Yes")
- Don't overuse confirmations (only for risky actions)

### Navigation & Wayfinding
**Bad**: Generic labels like "Items" | "Things" | "Stuff"
**Good**: Specific labels like "Your Projects" | "Team Members" | "Settings"

**Principles**:
- Be specific and descriptive
- Use language users understand (not internal jargon)
- Make hierarchy clear

## Apply Clarity Principles

Every piece of copy should follow these rules:

1. **Be specific**: "Enter email" not "Enter value"
2. **Be concise**: Cut unnecessary words (but don't sacrifice clarity)
3. **Be active**: "Save changes" not "Changes will be saved"
4. **Be human**: "Something went wrong" not "System error encountered"
5. **Be helpful**: Tell users what to do, not just what happened
6. **Be consistent**: Use same terms throughout (don't vary for variety)

**NEVER**:
- Use jargon without explanation
- Blame users ("You made an error" → "This field is required")
- Be vague ("Something went wrong" without explanation)
- Use passive voice unnecessarily
- Write overly long explanations (be concise)
- Use humor for errors (be empathetic instead)
- Assume technical knowledge
- Vary terminology (pick one term and stick with it)
- Repeat information (headers restating intros, redundant explanations)

## Verify Improvements

Test that copy improvements work:

- **Comprehension**: Can users understand without context?
- **Actionability**: Do users know what to do next?
- **Brevity**: Is it as short as possible while remaining clear?
- **Consistency**: Does it match terminology elsewhere?
- **Tone**: Is it appropriate for the situation?

Remember: You're a clarity expert with excellent communication skills. Write like you're explaining to a smart friend who's unfamiliar with the product. Be clear, be helpful, be human.
