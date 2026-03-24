# UX Writing

## The Button Label Problem

**Never use "OK", "Submit", or "Yes/No".** These are lazy and ambiguous. Use specific verb + object patterns:

| Bad | Good | Why |
|-----|------|-----|
| OK | Save changes | Says what will happen |
| Submit | Create project | Outcome-focused |
| Yes | Delete mesh | Confirms the action |
| Cancel | Keep editing | Clarifies what "cancel" means |

**For destructive actions**, name the destruction:
- "Delete" not "Remove" (delete is permanent, remove implies recoverable)
- "Delete 5 items" not "Delete selected" (show the count)

## Error Messages: The Formula

Every error message should answer: (1) What happened? (2) Why? (3) How to fix it? Example: "File path not found. Check the path exists and try again." not "Invalid input".

### Error Message Templates

| Situation | Template |
|-----------|----------|
| **Format error** | "[Field] needs to be [format]. Example: [example]" |
| **Missing required** | "Please enter [what's missing]" |
| **File not found** | "Couldn't find [path]. Check the file exists and the path is correct." |
| **Permission denied** | "Can't access [thing]. [What to do instead]" |
| **Operation failed** | "Something went wrong. [Alternative action or retry suggestion]" |

### Don't Blame the User

Reframe errors: "Please enter a value between 0 and 100" not "You entered an invalid number".

## Empty States Are Opportunities

Empty states are onboarding moments: (1) Acknowledge briefly, (2) Explain the value of filling it, (3) Provide a clear action. "No projects yet. Create your first one to get started." not just "No items".

## Voice vs Tone

**Voice** is your addon's personality—consistent everywhere.
**Tone** adapts to the moment.

| Moment | Tone Shift |
|--------|------------|
| Success | Brief, confirming: "Done. Changes saved." |
| Error | Helpful, clear: "That didn't work. Here's what to try..." |
| Loading | Reassuring: "Exporting mesh..." |
| Destructive confirm | Serious, clear: "Delete this project? This can't be undone." |

**Never use humor for errors.** Users are already frustrated. Be helpful, not cute.

## Consistency: The Terminology Problem

Pick one term and stick with it:

| Inconsistent | Consistent |
|--------------|------------|
| Delete / Remove / Trash | Delete |
| Settings / Preferences / Options | Settings |
| Create / Add / New | Create |
| Save / Apply / Confirm | Save |

Build a terminology glossary and enforce it. Variety creates confusion.

## Avoid Redundant Copy

If the heading explains it, the intro is redundant. If the button is clear, don't explain it again. Say it once, say it well.

## Loading States

Be specific: "Exporting scene..." not "Loading...". For long waits, set expectations ("This usually takes a few seconds") or show progress.

## Confirmation Dialogs: Use Sparingly

Most confirmation dialogs are design failures—consider undo instead. When you must confirm: name the action, explain consequences, use specific button labels ("Delete project" / "Keep project", not "Yes" / "No").

## Form Instructions

For non-obvious fields, explain why you're asking. Use descriptive labels — in Puree, labels are typically separate text nodes above or beside input elements:

```yaml
form_section:
  class: form_group
  label:
    class: field_label
    text: "Export Path"
  input_field:
    class: text_input
    text: "//"
  hint:
    class: field_hint
    text: "Relative path from project root"
```

---

**Avoid**: Jargon without explanation. Blaming users ("You made an error" → "This field is required"). Vague errors ("Something went wrong" with no guidance). Varying terminology for variety. Humor for errors.
