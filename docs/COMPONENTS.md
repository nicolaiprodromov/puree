---
layout: page
title : 2. Components
---

Puree includes a powerful component template system that allows you to create reusable UI components with parameterization. This feature promotes code reuse, maintains consistency, and simplifies complex UI structures.

Component templates are defined as separate `.yaml` files and can be instantiated multiple times throughout your UI with different parameters. Think of them as reusable UI "blueprints" similar to React components or Vue templates.

## Creating Components

### 1. Component Directory Structure

Components are stored in a dedicated directory specified in your theme configuration:

```yaml
app:
  theme:
    - name: xwz_default
      components: static/components/  # Path to components directory
```

Your project structure should look like:

```
puree_project/
    ├── static/
    │   ├── components/
    │   │   ├── header.yaml       # Component structure
    │   │   ├── header.scss       # Component styles (optional)
    │   │   ├── test_button.yaml
    │   │   ├── test_button.scss
    │   │   └── card.yaml
    │   ├── index.yaml
    │   └── style.scss
    └── __init__.py
```

Each component can have a matching `.scss` file alongside its `.yaml` file. Component SCSS files are automatically compiled and included when that component is used. Use `!default` on SCSS variables so they can be overridden by the consuming project:

```scss
// components/card.scss
$card_bg: #1e2028 !default;
$card_radius: 12px !default;

.card {
  background-color: $card_bg;
  border-radius: $card_radius;
  padding: 16px;
}
```

### 2. Component Definition

Create a `.yaml` file in your components directory. The component must have a single root key that matches the filename (without extension):

**Example: `test_button.yaml`**

{% raw %}
```yaml
test_button:
  style: "{{tb_style, 'hover_test'}}"
  tb_text:
    style: "{{tb_text_style, 'ht_text'}}"
    text: "{{tb_text, 'Click Me'}}"
    passive: true
```
{% endraw %}

**Example: `header.yaml`**

{% raw %}
```yaml
header:
  style: header
  text_box:
    style: header_text_box
    text:
      style: header_text
      
      text: "{{title, 'Puree UI Kit'}}"
      font: NeueMontreal-Bold
    subtitle:
      style: header_text1
      text: "{{subtitle, 'Declarative UI for Blender'}}"
      font: NeueMontreal-Italic
  logo:
    style: header_logo
    img: loggoui2
```
{% endraw %}

## Parameter Syntax

Component parameters use a special syntax: {% raw %}`{{parameter_name, 'default_value'}}`{% endraw %}

- **`parameter_name`**: The name of the parameter that can be passed when instantiating the component
- **`default_value`**: The fallback value if no parameter is provided (must be in quotes)

**Format:**

{% raw %}
```yaml
property: "{{param_name, 'default value'}}"
```
{% endraw %}

**Examples:**

{% raw %}
```yaml
text: "{{button_text, 'Submit'}}"      # Text parameter with default
style: "{{button_style, 'default'}}"     # Style parameter with default
img: "{{icon_name, 'icon_default'}}"  # Image parameter with default
```
{% endraw %}

## Using Components

### 1. Reference Components in Your UI

To use a component, set the `data` property to the component reference in square brackets:

```yaml
app:
  theme:
    - root:
        my_container:
          my_button:
            data: '[test_button]'  # References test_button.yaml
```

### 2. Pass Parameters to Components

You can customize component instances by passing parameters as properties:

{% raw %}
```yaml
app:
  theme:
    - root:
        bg:
          body:
            buttons:
              hover_button:
                data: '[test_button]'
                tb_text_style: ht_text
                tb_style: hover_test
                tb_text: Hover me!
              click_button:
                data: '[test_button]'
                tb_text_style: ct_text
                tb_style: click_test
                tb_text: Click me!
```
{% endraw %}

In this example:

- Both buttons use the same `test_button` component template
- Each instance receives different parameter values
- The component's {% raw %}`{{tb_text, ''}}`{% endraw %} parameter gets replaced with "Hover me!" and "Click me!" respectively

### 3. Component Instance with Multiple Parameters

**Component Definition (`header.yaml`):**

{% raw %}
```yaml
header:
  style: header
  title:
    text: "{{title, 'Default Title'}}"
  subtitle:
    text: "{{subtitle, 'Default Subtitle'}}"
```
{% endraw %}

**Usage in `index.yaml`:**

```yaml
app:
  theme:
    - root:
        page:
          top_header:
            data: '[header]'
            title: Welcome to Puree
            subtitle: Build UIs with ease
```

## Component Namespacing

To prevent ID collisions when multiple instances of the same component exist, Puree automatically namespaces child elements:

**Component Definition:**

```yaml
button:
  icon:
    label:
```

**When instantiated as `my_button`:**

```text
my_button
  └── my_button_icon
      └── my_button_icon_label
```

This means each component instance has unique IDs throughout the node tree, using underscore (`_`) as a separator.

## Accessing Component Instances in Scripts

Puree provides an intuitive property-based access system for navigating the container hierarchy. Instead of traversing arrays of children, you can access containers by their ID using dot notation.

```python
def main(self, app):
    # For a component instantiated as "my_card" using "[card]" template:
    # Access namespaced children:
    header = app.theme.root.my_card_card_header
    body = app.theme.root.my_card_card_body
    return app
```

## Dynamic Component Instantiation

Components can be created and destroyed at runtime from `script.py`:

```python
def main(self, app):
    parent = app.theme.root.bg.cards
    
    def add_card(container):
        new_card = parent.add_child("[card]", id="card_1", params={
            "title": "Dynamic Card",
            "content": "Created at runtime"
        })
        new_card.mark_dirty()
    
    def remove_card(container):
        parent.remove_child("card_1")
        parent.mark_dirty()
    
    app.theme.root.bg.add_btn.click.append(add_card)
    app.theme.root.bg.remove_btn.click.append(remove_card)
    return app
```

Available methods: `add_child(template, id, params)`, `insert_child(index, template, id, params)`, `remove_child(id_or_container)`, `clear_children()`. See the [API Reference](API.md) for details.

### Nested Components

Components can use other components. For example, a `card` component might use a `badge` component internally:

**components/badge.yaml:**

{% raw %}
```yaml
badge:
  class: badge
  text: "{{badge_text, 'Default'}}"
```
{% endraw %}

**components/card.yaml:**

{% raw %}
```yaml
card:
  class: card
  card_header:
    class: card_header
    text: "{{title, 'Card Title'}}"
  card_badge:
    data: '[badge]'
    badge_text: "{{status, 'Active'}}"
  card_body:
    class: card_body
    text: "{{body, 'Card content'}}"
```
{% endraw %}

**Usage in index.yaml:**

```yaml
my_card:
  data: '[card]'
  title: "Settings"
  status: "Beta"
  body: "Configure your preferences"
```

**Accessing nested component children in Python:**

```python
# Access the badge inside the card
# Naming: instance_id + component_child_id
badge = app.theme.root.my_card.card_badge
badge_inner = badge.badge  # The inner badge container
badge_inner.text = "v2.0"
badge_inner.mark_dirty()
```

**Important:** Component SCSS is scoped by component name. If the `badge` component defines `.badge { ... }` styles and the `card` component also defines `.badge { ... }`, the badge's own SCSS takes precedence for containers instantiated from the badge component. Keep class names unique across components to avoid confusion.

### SCSS Variable Precedence

When a component is instantiated, its SCSS is compiled with the component's own variables as defaults. Parameters passed from the parent use SCSS variable overrides:

```scss
// components/button.scss
$btn-bg: #333 !default;    // !default means "use this unless overridden"
$btn-color: #fff !default;

.button {
  background-color: $btn-bg;
  color: $btn-color;
}
```

The `!default` flag is key — it allows parent contexts to override these values via component parameters, while providing sensible defaults when no override is given.

---

|  | Previous Page | Next Page |
|----------|----------|------|
| Puree is under active development. APIs may change between versions. **Special thanks to the open-source community and the developers behind the projects that make puree possible.** | [Documentation](DOCS.md) | [API Reference](API.md) |

### Property-Based Access

```python
def main(self, app):
    # Access containers by ID using dot notation
    # This is much cleaner than: app.theme.root.children[0].children[1]
    hover_button = app.theme.root.bg.body.buttons.hover_button
    
    # Access nested children (with namespace)
    button_text = app.theme.root.bg.body.buttons.hover_button_tb_text
    
    # Attach event handlers
    def on_click(container):
        print("Button clicked!")
    
    hover_button.click.append(on_click)
    
    return app
```

## How It Works

The `Container` class implements a custom `__getattr__` method that:

1. Searches through the container's children
2. Finds a child whose `id` matches the requested attribute name
3. Returns that child container

**Example:**

```python
# These are equivalent:
button = app.theme.root.bg.my_button

# Is the same as finding the child manually:
button = None
for child in app.theme.root.bg.children:
    if child.id == "my_button":
        button = child
        break
```

This makes your script code much more readable and maintainable, especially when working with deeply nested UI structures.

## Best Practices

1. **Keep Components Focused**: Each component should represent a single, reusable UI pattern
2. **Use Meaningful Parameter Names**: Choose descriptive names like `button_text` rather than `txt`
3. **Provide Sensible Defaults**: Always include default values that make sense
4. **Document Your Components**: Add comments in component files explaining parameters
5. **Style Separation**: Define component-specific styles in your CSS file, pass style names as parameters
6. **Avoid Deep Nesting**: Keep component hierarchies shallow for better maintainability

## Complete Example

**File: `static/components/card.yaml`**

{% raw %}
```yaml
card:
  style: "{{card_style, 'default_card'}}"
  header:
    style: card_header
    text: "{{card_title, 'Title'}}"
  body:
    style: card_body
    text: "{{card_content, 'Content'}}"
  footer:
    style: card_footer
    button:
      style: card_button
      text: "{{action_text, 'Action'}}"
```
{% endraw %}

**File: `static/style.scss`**

```css
default_card {
    width: 300px;
    height: 400px;
    background-color: #ffffff;
    border-radius: 8px;
    padding: 20px;
}

card_header {
    text-scale: 24px;
    text-color: #333333;
}

card_body {
    text-scale: 16px;
    text-color: #666666;
}
```

**File: `static/index.yaml`**

```yaml
app:
  theme:
    - root:
        dashboard:
          product_card:
            data: '[card]'
            card_style: product_card_style
            card_title: Product Name
            card_content: Product description goes here
            action_text: Buy Now
          profile_card:
            data: '[card]'
            card_title: User Profile
            card_content: User bio and information
            action_text: Edit Profile
```

This creates two different cards from the same template with different content and styling.

---

|  | Previous Page | Next Page |
|----------|----------|------|
| Puree is under active development. APIs may change between versions. **Special thanks to the open-source community and the developers behind the projects that make puree possible.** | [Documentation](DOCS.md) | [API Reference](API.md) |