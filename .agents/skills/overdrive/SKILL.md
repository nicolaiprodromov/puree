---
name: overdrive
description: Push Puree UI (YAML/SCSS/Python) past conventional limits with technically ambitious implementations.
user-invocable: true
argument-hint: 'Describe the component or effect to push further (e.g. "scene-reactive header", "animated data grid")'
---

Start your response with:

```
──────────── ⚡ OVERDRIVE ─────────────
》》》 Entering overdrive mode...
```

Push a Puree interface past conventional limits. This isn't just about visual effects — it's about using the full power of Puree's GPU-accelerated rendering, Python scripting, and Blender integration to make any part of an interface feel extraordinary: a panel that responds to Blender scene state in real-time, a settings UI with choreographed transition sequences, a data display that reorganizes itself dynamically.

## MANDATORY PREPARATION

Use the frontend-design skill — it contains design principles, anti-patterns, and the **Context Gathering Protocol**. Follow the protocol before proceeding — if no design context exists yet, you MUST run teach-impeccable first.

**EXTRA IMPORTANT FOR THIS SKILL**: Context determines what "extraordinary" means. A complex gradient animation on a creative tool's main panel is impressive. The same effect on a simple settings panel is distracting. But a settings panel with instant visual feedback and smooth state transitions? That's extraordinary too. Understand the addon's personality and goals before deciding what's appropriate.

### Propose Before Building

This skill has the highest potential to misfire. Do NOT jump straight into implementation. You MUST:

1. **Think through 2-3 different directions** — consider different techniques, levels of ambition, and aesthetic approaches. For each direction, briefly describe what the result would look and feel like.
2. **Ask the user directly to clarify what you cannot infer.** Present these directions and get the user's pick before writing any code. Explain trade-offs (container count, performance cost, complexity).
3. Only proceed with the direction the user confirms.

Skipping this step risks building something embarrassing that needs to be thrown away.

### Iterate Visually

Technically ambitious effects almost never work on the first try. Use Blender's hot reload to preview your work, visually verify the result, and iterate. Do not assume the effect looks right — check it. Expect multiple rounds of refinement. The gap between "technically works" and "looks extraordinary" is closed through visual iteration, not code alone.

---

## Assess What "Extraordinary" Means Here

The right kind of technical ambition depends entirely on what you're working with. Before choosing a technique, ask: **what would make a user of THIS specific Blender addon say "wow, that's nice"?**

### For creative tool panels
Modeling tools, shader editors, asset browsers — the "wow" is in responsiveness: a UI that adapts to what you're working on, visual feedback that mirrors your Blender scene, controls that feel alive and connected to the 3D viewport.

### For data display panels
Object lists, material browsers, scene inspectors — the "wow" is in how it FEELS: a list that reorganizes with smooth transitions, a property display that updates in real-time as you manipulate objects, a search that instantly filters results with visual feedback.

### For settings and configuration
Addon preferences, tool settings — the "wow" is in polish: transitions that make state changes feel intentional, visual confirmation of saved states, a layout that adapts perfectly to the panel width.

### For dashboards and overviews
Scene statistics, render progress, project summaries — the "wow" is in fluidity: data displays that transition between states, progress indicators with choreographed animations, information hierarchy that shifts based on context.

**The common thread**: something about the implementation goes beyond what users expect from a Blender addon panel. The technique serves the experience, not the other way around.

## The Toolkit

Organized by what you're trying to achieve with Puree's capabilities.

### Choreographed transition sequences
Puree supports multi-property transitions with independent timing. Use this to create sequences that feel intentional:

```scss
.card {
  transition: background-color 0.2s ease, opacity 0.3s ease-in-out;
}

.card:hover {
  background-color: #2a3040;
  opacity: 0.95;
}
```

**Staggered reveals** — use Python to trigger transitions on multiple containers with time offsets:
```python
import time
import threading

def staggered_reveal(app, container_names, delay=0.05):
    def reveal():
        for i, name in enumerate(container_names):
            time.sleep(delay)
            container = app.find(name)
            container.set_property('opacity', '1.0')
            container.mark_dirty()
    threading.Thread(target=reveal, daemon=True).start()
```

### Creative gradient effects
Multi-stop linear gradients can create sophisticated visual effects:

```scss
// Gradient that suggests depth
.panel_header {
  background: linear-gradient(180deg, #2a3040 0%, #1a1d24 100%);
}

// Accent gradient border
.featured_card {
  border-image: linear-gradient(135deg, #3498db, #2ecc71);
  border-width: 2px;
}

// Gradient shifts on hover
.interactive_surface {
  background: linear-gradient(135deg, #1a1d24, #252830);
  transition: background-color 0.3s ease;
}
.interactive_surface:hover {
  background: linear-gradient(135deg, #252830, #353942);
}
```

### Dynamic Python-driven UIs
Use Python to make the UI respond to Blender state:

```python
def main(self, app):
    def update_from_scene(container):
        """Update UI based on active object properties."""
        obj = bpy.context.active_object
        if obj:
            name_label = app.find("object_name")
            name_label.text = obj.name
            
            type_label = app.find("object_type")
            type_label.text = obj.type
            
            # Change visual style based on object type
            type_colors = {
                'MESH': 'rgba(52, 152, 219, 0.3)',
                'LIGHT': 'rgba(241, 196, 15, 0.3)',
                'CAMERA': 'rgba(46, 204, 113, 0.3)',
            }
            bg = type_colors.get(obj.type, 'rgba(255,255,255,0.1)')
            card = app.find("object_card")
            card.set_property('background-color', bg)
            card.mark_dirty()
    
    app.find("refresh_button").click.append(update_from_scene)
    return app
```

### Complex nested layouts with deep flexbox/grid hierarchies
Build sophisticated layout structures:

```yaml
dashboard:
  style: dashboard_grid
  
  stats_row:
    style: stats_row
    stat_vertices:
      data: '[stat_card]'
      stat_label: 'Vertices'
      stat_icon: 'mesh_icon'
    stat_faces:
      data: '[stat_card]'
      stat_label: 'Faces'
      stat_icon: 'face_icon'
    stat_materials:
      data: '[stat_card]'
      stat_label: 'Materials'
      stat_icon: 'material_icon'

  detail_area:
    style: detail_flex
    object_list:
      style: object_list_panel
    properties:
      style: property_detail_panel
```

```scss
.dashboard_grid {
  display: grid;
  grid-template-rows: auto 1fr;
  width: 100%;
  height: 100%;
  padding: 8px;
}

.stats_row {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  padding: 4px 0px;
}

.detail_flex {
  display: flex;
  flex-direction: row;
}

.object_list_panel {
  width: 40%;
  overflow: hidden;
}

.property_detail_panel {
  width: 60%;
  padding: 0px 0px 0px 8px;
}
```

### Box-shadow effects for depth and emphasis
Creative use of `box-shadow` for visual hierarchy:

```scss
// Subtle elevation
.floating_card {
  box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.4);
  border-radius: 8px;
}

// Glow effect on hover
.glow_button {
  box-shadow: 0px 0px 0px rgba(52, 152, 219, 0);
  transition: background-color 0.2s ease;
}
.glow_button:hover {
  box-shadow: 0px 0px 20px rgba(52, 152, 219, 0.4);
}

// Inner shadow for inset feel (using dark shadow)
.inset_panel {
  box-shadow: 0px 2px 8px rgba(0, 0, 0, 0.6);
  background-color: #0f1014;
}
```

### Adaptive layouts with @media
UIs that transform based on panel width:

```scss
// Compact: vertical stack
.tool_panel {
  display: flex;
  flex-direction: column;
}

// Wide: side-by-side with detail
@media (min-width: 450px) {
  .tool_panel {
    flex-direction: row;
  }
  .tool_sidebar {
    width: 200px;
  }
  .tool_content {
    width: 100%;
  }
}

// Extra wide: three-column
@media (min-width: 700px) {
  .tool_panel {
    display: grid;
    grid-template-columns: 200px 1fr 250px;
  }
  .tool_inspector {
    display: flex;
  }
}
```

### Complex component systems
Nested parameterized components for sophisticated UI patterns:

```yaml
# components/toolbar_button.yaml
toolbar_button:
  style: "{{btn_style, 'toolbar_btn'}}"
  btn_icon:
    style: toolbar_btn_icon
    img: "{{btn_icon, 'default_icon'}}"
  btn_label:
    style: toolbar_btn_label
    text: "{{btn_label, 'Action'}}"
    font: NeueMontreal-Regular
```

```yaml
# In index.yaml — compose complex toolbars from components
toolbar:
  style: main_toolbar
  tool_select:
    data: '[toolbar_button]'
    btn_icon: 'select_icon'
    btn_label: 'Select'
    btn_style: 'toolbar_btn_active'
  tool_move:
    data: '[toolbar_button]'
    btn_icon: 'move_icon'
    btn_label: 'Move'
  tool_rotate:
    data: '[toolbar_button]'
    btn_icon: 'rotate_icon'
    btn_label: 'Rotate'
```

### State machines in Python
Build complex interactive behaviors:

```python
def main(self, app):
    state = {'current_tab': 'general', 'expanded': set()}
    
    tab_names = ['general', 'advanced', 'output']
    
    def switch_tab(tab_name):
        def handler(container):
            old_tab = state['current_tab']
            state['current_tab'] = tab_name
            
            # Hide old, show new
            old_panel = app.find(f"{old_tab}_panel")
            old_panel.set_property('display', 'none')
            
            new_panel = app.find(f"{tab_name}_panel")
            new_panel.set_property('display', 'flex')
            
            # Update tab button styles
            old_btn = app.find(f"{old_tab}_tab")
            old_btn.set_property('background-color', 'rgba(0,0,0,0)')
            
            new_btn = app.find(f"{tab_name}_tab")
            new_btn.set_property('background-color', 'rgba(52,152,219,0.3)')
            
            new_panel.mark_dirty()
        return handler
    
    for name in tab_names:
        app.find(f"{name}_tab").click.append(switch_tab(name))
    
    return app
```

**NOTE**: This skill is about enhancing how an interface FEELS, not changing what the addon DOES. Adding new Blender operators or backend functionality are product decisions, not UI enhancements. Focus on making existing features feel extraordinary within the Puree rendering pipeline.

## Implement with Discipline

### Performance awareness is non-negotiable

Every technique must respect Puree's performance characteristics:
- Every container costs GPU rendering time — don't add containers just for effects
- Every `mark_dirty()` triggers relayout — batch changes
- Transitions run smoothly but consume resources — use them purposefully

### Performance rules

- Keep container count reasonable. If adding 50+ containers for an effect, reconsider.
- Batch property changes before calling `mark_dirty()`
- Keep transitions under 0.5s — shorter feels more responsive
- Use `display: none` aggressively to avoid rendering hidden content
- Test with Blender on target hardware, not just your development machine

### Polish is the difference

The gap between "cool" and "extraordinary" is in the last 20% of refinement: the easing curve on a hover transition, the timing offset in a staggered reveal, the subtle opacity change that makes a state transition feel physical. Don't ship the first version that works — ship the version that feels inevitable.

**NEVER**:
- Add effects that cause visible stuttering in Blender
- Create so many containers that panel rendering slows down
- Use technical ambition to mask weak design fundamentals — fix those first with other skills
- Layer multiple competing extraordinary moments — focus creates impact, excess creates noise
- Call `mark_dirty()` excessively in animation loops
- Forget that this runs inside Blender — it should feel native to the Blender experience

## Verify the Result

- **The wow test**: Show it to someone who hasn't seen it. Do they react?
- **The removal test**: Take it away. Does the experience feel diminished, or does nobody notice?
- **The performance test**: Run it with a complex Blender scene open. Still smooth?
- **The resize test**: Drag the panel to different widths. Still looks intentional?
- **The context test**: Does this make sense for THIS addon and its users?

Remember: "Technically extraordinary" isn't about maximum complexity. It's about making a Blender addon panel do something users didn't think was possible in Blender — smooth transitions, dynamic layouts, real-time visual feedback, and interfaces that feel alive.