---
name: onboard
description: Design or improve Puree UI onboarding flows, empty states, and first-time user experiences. Helps users get started successfully and understand value quickly.
user-invocable: true
argument-hint: 'Describe the onboarding flow to design (e.g. "first launch experience", "empty project state")'
---

## MANDATORY PREPARATION

Use the frontend-design skill — it contains design principles, anti-patterns, and the **Context Gathering Protocol**. Follow the protocol before proceeding — if no design context exists yet, you MUST run teach-impeccable first. Additionally gather: the "aha moment" you want users to reach, and users' experience level.

---

Create or improve onboarding experiences that help users understand, adopt, and succeed with the Blender addon quickly.

## Assess Onboarding Needs

Understand what users need to learn and why:

1. **Identify the challenge**:
   - What are users trying to accomplish with this addon?
   - What's confusing or unclear about the current panel experience?
   - Where do users get stuck?
   - What's the "aha moment" we want users to reach?

2. **Understand the users**:
   - What's their Blender experience level? (Beginners, power users, mixed?)
   - What's their motivation? (Excited and exploring? Need it for a project?)
   - What's their time commitment? (5 minutes? 30 minutes?)
   - What similar tools do they know? (Coming from another addon? New to this workflow?)

3. **Define success**:
   - What's the minimum users need to learn to be successful?
   - What's the key action we want them to take? (First use of main feature?)
   - How do we know onboarding worked? (User completes core workflow?)

**CRITICAL**: Onboarding should get users to value as quickly as possible, not teach everything possible.

## Onboarding Principles

Follow these core principles:

### Show, Don't Tell
- Demonstrate with working examples, not just descriptions
- Provide real functionality in onboarding, not a separate tutorial mode
- Use progressive disclosure — teach one thing at a time

### Make It Optional (When Possible)
- Let experienced users skip onboarding
- Don't block access to the addon's features
- Provide "Skip" or "I'll explore on my own" options

### Time to Value
- Get users to their "aha moment" ASAP
- Front-load the most important concepts
- Teach 20% that delivers 80% of value
- Save advanced features for contextual discovery

### Context Over Ceremony
- Teach features when users need them, not upfront
- Empty states are onboarding opportunities
- Hints at point of use within the panel

### Respect User Intelligence
- Don't patronize or over-explain
- Be concise and clear
- Assume users can figure out standard Blender patterns

## Design Onboarding Experiences

Create appropriate onboarding for the context:

### First-Run Experience

**Welcome State**:
- Clear value proposition (what does this addon do?)
- What users will learn/accomplish
- Option to skip (for experienced users)

**Example — first-run panel in YAML**:
```yaml
first_run_panel:
  style: first_run_container
  
  welcome_header:
    style: welcome_title
    text: "Welcome to [Addon Name]"
    font: NeueMontreal-Bold
  
  welcome_description:
    style: welcome_desc
    text: "Create stunning effects in seconds. Let's get started."
    font: NeueMontreal-Regular
  
  get_started_button:
    data: '[button]'
    tb_text_value: "Get Started"
    bg_color: '#3498db'
    hover_bg_color: '#2980b9'
  
  skip_link:
    style: skip_text
    text: "I'll explore on my own"
    font: NeueMontreal-Regular
```

```scss
.first_run_container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 30px 20px;
  height: 100%;
}

.welcome_title {
  font-size: 18px;
  color: #f5f8fa;
  text-align: center;
  padding: 0px 0px 10px 0px;
}

.welcome_desc {
  font-size: 13px;
  color: rgba(181, 188, 199, 0.9);
  text-align: center;
  padding: 0px 0px 20px 0px;
}

.skip_text {
  font-size: 11px;
  color: rgba(181, 188, 199, 0.5);
  text-align: center;
  padding: 10px 0px 0px 0px;
}
.skip_text:hover {
  color: rgba(181, 188, 199, 0.8);
}
```

**First-run detection in Python**:
```python
import bpy

def main(self, app):
    # Use Blender scene properties to track first-run state
    scene = bpy.context.scene
    
    # Check if user has completed onboarding
    has_onboarded = scene.get("addon_onboarded", False)
    
    if has_onboarded:
        # Hide onboarding, show main UI
        app.find("first_run_panel").set_property('display', 'none')
        app.find("main_panel").set_property('display', 'flex')
    else:
        # Show onboarding, hide main UI
        app.find("first_run_panel").set_property('display', 'flex')
        app.find("main_panel").set_property('display', 'none')
    
    def complete_onboarding(container):
        scene["addon_onboarded"] = True
        app.find("first_run_panel").set_property('display', 'none')
        app.find("main_panel").set_property('display', 'flex')
        app.find("main_panel").mark_dirty()
    
    app.find("get_started_button").click.append(complete_onboarding)
    app.find("skip_link").click.append(complete_onboarding)
    
    return app
```

### Feature Discovery & Adoption

**Empty States**:
Instead of blank space, show:
- What will appear here (description)
- Why it's valuable
- Clear call-to-action to create the first item
- Example or template option

**Example — empty state for an object list**:
```yaml
empty_state:
  style: empty_state_container
  empty_icon:
    style: empty_icon
    img: 'no_objects'
  empty_title:
    style: empty_title
    text: 'No objects found'
    font: NeueMontreal-Bold
  empty_description:
    style: empty_desc
    text: 'Select objects in the viewport to see them here.'
    font: NeueMontreal-Regular
  empty_action:
    data: '[button]'
    tb_text_value: 'Select All Objects'
    bg_color: '#252830'
    hover_bg_color: '#353942'
```

```scss
.empty_state_container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 30px 20px;
  height: 100%;
}

.empty_icon {
  width: 48px;
  height: 48px;
  opacity: 0.4;
  --img-align-h: center;
  --img-align-v: center;
}

.empty_title {
  font-size: 14px;
  color: rgba(181, 188, 199, 0.8);
  text-align: center;
  padding: 12px 0px 4px 0px;
}

.empty_desc {
  font-size: 12px;
  color: rgba(181, 188, 199, 0.5);
  text-align: center;
  padding: 0px 0px 16px 0px;
}
```

**Contextual Hints**:
- Appear at relevant moment (first time user encounters a feature)
- Brief explanation + benefit
- Dismissable (hide via Python and remember state)

**Example — contextual hint**:
```yaml
hint_container:
  style: hint_box
  hint_text:
    style: hint_text
    text: 'Tip: Right-click objects to see more options.'
    font: NeueMontreal-Regular
  hint_dismiss:
    style: hint_dismiss
    text: '✕'
    font: NeueMontreal-Regular
```

```scss
.hint_box {
  display: flex;
  flex-direction: row;
  align-items: center;
  background-color: rgba(52, 152, 219, 0.15);
  border: 1px solid rgba(52, 152, 219, 0.3);
  border-radius: 6px;
  padding: 8px 12px;
  margin: 8px 0px;
}

.hint_text {
  font-size: 12px;
  color: rgba(52, 152, 219, 0.9);
  width: 100%;
}

.hint_dismiss {
  font-size: 12px;
  color: rgba(181, 188, 199, 0.5);
  width: 20px;
  text-align: center;
}
.hint_dismiss:hover {
  color: rgba(181, 188, 199, 0.9);
}
```

**Dismissal tracking in Python**:
```python
def main(self, app):
    scene = bpy.context.scene
    
    # Check if hint was already dismissed
    if scene.get("hint_rightclick_seen", False):
        app.find("hint_container").set_property('display', 'none')
    
    def dismiss_hint(container):
        scene["hint_rightclick_seen"] = True
        hint = app.find("hint_container")
        hint.set_property('display', 'none')
        hint.mark_dirty()
    
    app.find("hint_dismiss").click.append(dismiss_hint)
    return app
```

**Progressive Feature Unlock**:
- Show basic controls first
- Reveal advanced options as users demonstrate competence
- Use `display: none` / `display: flex` toggling to show/hide sections

### Guided Highlights

**When to use**:
- Complex addon interfaces with many features
- Tools requiring domain knowledge

**How to design in Puree**:
- Highlight specific containers by changing their `background-color` or `border-color`
- Dim other sections with reduced `opacity`
- Show explanatory text in a dedicated hint container
- Step through with Python-driven state management

**Example — spotlight a feature**:
```python
def spotlight_feature(app, target_name, hint_text):
    """Highlight a container and show a hint."""
    target = app.find(target_name)
    target.set_property('border-color', 'rgba(52, 152, 219, 0.8)')
    
    hint = app.find("spotlight_hint")
    hint.text = hint_text
    hint.set_property('display', 'flex')
    hint.mark_dirty()

def clear_spotlight(app, target_name):
    """Remove highlight."""
    target = app.find(target_name)
    target.set_property('border-color', 'rgba(0, 0, 0, 0)')
    
    hint = app.find("spotlight_hint")
    hint.set_property('display', 'none')
    hint.mark_dirty()
```

## Empty State Design

Every empty state needs:

### What Will Be Here
"Your selected objects will appear here"

### Why It Matters
"Organize and manage objects without switching between panels"

### How to Get Started
Button or instruction to populate the panel

### Visual Interest
Icon or subtle styling (not just text on a blank background)

**Empty state types**:
- **First use**: Never used this feature (emphasize value, guide to first action)
- **No matching data**: Filter/search returned nothing (suggest different criteria, offer to clear filters)
- **No Blender data**: No objects/materials in scene (explain what's needed)
- **Error state**: Failed to load data (explain what happened, offer retry)

## State Management Patterns

### Tracking "seen" states with Blender properties

```python
import bpy

def get_onboard_state(key, default=False):
    """Get onboarding state from scene properties."""
    return bpy.context.scene.get(f"addon_onboard_{key}", default)

def set_onboard_state(key, value):
    """Save onboarding state to scene properties."""
    bpy.context.scene[f"addon_onboard_{key}"] = value
```

### Tracking states with addon preferences (persists across scenes)

```python
# In your addon's preferences class
class AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = "your_addon"
    
    onboarding_complete: bpy.props.BoolProperty(default=False)
    hint_seen_tooltips: bpy.props.BoolProperty(default=False)
```

**Use scene properties** for per-scene onboarding state. **Use addon preferences** for global onboarding state that persists across scenes and files.

**IMPORTANT**: Don't show the same onboarding twice (annoying). Track completion and respect dismissals.

**NEVER**:
- Force users through long onboarding before they can use the addon
- Patronize users with obvious explanations
- Show the same hint repeatedly (respect dismissals)
- Block the entire panel during a walkthrough (let users explore)
- Create a separate tutorial mode disconnected from the real addon
- Overwhelm with information upfront (progressive disclosure!)
- Hide "Skip" or make it hard to find
- Forget about returning users (don't show initial onboarding again)
- Store onboarding state in a way that gets lost easily

## Verify Onboarding Quality

Test with users:

- **Time to completion**: Can users complete onboarding quickly?
- **Comprehension**: Do users understand after completing?
- **Action**: Do users take the desired next step?
- **Skip rate**: Are too many users skipping? (Maybe it's too long/not valuable)
- **Completion rate**: Are users completing? (If low, simplify)
- **Time to value**: How long until users get first value from the addon?
- **Panel resize**: Does onboarding content look good at different panel widths?

Remember: You're a product educator with excellent teaching instincts. Get users to their "aha moment" as quickly as possible. Teach the essential, make it contextual, respect user time and intelligence.