# Puree UI Specification for LLMs

> This document is the authoritative reference for generating Puree UI code.
> Puree is a GPU-accelerated UI framework for Blender that uses YAML for structure,
> SCSS/CSS for styling, and Python for interactivity. It follows **standard CSS conventions**
> with a few Blender-specific extensions.

---

## File Structure

```
my_addon/
├── static/
│   ├── index.yaml          # UI hierarchy (like index.html)
│   ├── style.scss           # Styles (standard SCSS/CSS)
│   ├── script.py            # Event handlers & interactivity
│   └── components/          # Reusable components
│       ├── button.yaml
│       ├── button.scss
│       ├── card.yaml
│       └── card.scss
├── assets/                  # Images (PNG, SVG)
├── fonts/                   # Font files (.ttf, .otf)
└── __init__.py              # Blender addon entry point
```

---

## 1. YAML Structure (`index.yaml`)

The YAML file defines the UI tree. Think of it as HTML but in YAML.

### Minimal Example

```yaml
app:
  selected_theme: my_theme
  default_theme: my_theme

  theme:
    - name: my_theme
      author: me
      version: 1.0.0
      default_font: NeueMontreal-Regular
      styles:
        - static/style.scss
      scripts:
        - static/script.py
      components: static/components/

      root:
        style: root
        sidebar:
          style: sidebar
          title:
            style: sidebar_title
            text: "Navigation"
        main:
          style: main_content
          heading:
            style: heading
            text: "Welcome"
          body:
            style: body_text
            text: "Hello from Puree!"
```

### Node Properties

Each YAML node can have these properties:

| Property   | Type   | Description                                        |
|------------|--------|----------------------------------------------------|
| `style`    | string | CSS class name for styling (matched as `.classname` in SCSS) |
| `class`    | string | Space-separated CSS class names (alternative to `style`)     |
| `text`     | string | Text content to display                            |
| `font`     | string | Font name (without extension): `NeueMontreal-Bold` |
| `img`      | string | Image name from `assets/` (without extension)      |
| `data`     | string | Component reference: `'[component_name]'`          |
| `passive`  | bool   | If true, element is non-interactive                |

### Rules
- Node names become the element's tag/ID in the tree
- Node names must use **underscores** (no hyphens): `my_button` ✓, `my-button` ✗
- Nesting creates parent-child relationships (like HTML nesting)
- The `root` node is equivalent to `<body>` in HTML

---

## 2. CSS/SCSS Styling (`style.scss`)

Puree uses **CSS/SCSS** with its own property names. The cascade engine supports selectors, specificity, and inheritance.

### Selectors

Puree supports standard CSS selectors:

```scss
// Class selector (most common)
.sidebar { width: 250px; }

// ID selector
#main_header { font-size: 24px; }

// Descendant selector
.sidebar .nav_item { padding: 8px 16px; }

// Child selector
.sidebar > .title { font-weight: bold; }

// Pseudo-classes
.button:hover { color: #444; }
.button:active { color: #666; }

// Comma-separated (multiple selectors, same rules)
.card, .panel { border-radius: 8px; }
```

### CSS Cascade & Specificity

Rules follow standard CSS cascade:
- More specific selectors override less specific ones
- `#id` (100) > `.class` (10) > `element` (1)
- Later rules override earlier rules at equal specificity
- `!important` overrides all

### Inheritance

These properties **inherit** from parent (same as standard CSS):
- `color` (text color)
- `font-size`
- `text-align`

These do **NOT** inherit:
- `background-color`, `border`, `padding`, `margin`, `width`, `height`, `display`

### Full Property Reference

#### Colors & Backgrounds

| Property                        | Type        | Default         | Description                          |
|---------------------------------|-------------|-----------------|--------------------------------------|
| `background-color`              | color       | `transparent`   | Fill/background color                |
| `background`                    | shorthand   | —               | `linear-gradient()` or solid color   |
| `background-image`              | shorthand   | —               | CSS alias for `background: linear-gradient()` |
| `color`                         | color       | `#ffffff`       | Text color (inherited)               |
| `opacity`                       | float       | `1.0`           | Element opacity (0–1)                |
| `visibility`                    | enum        | `visible`       | `visible`, `hidden` (keeps layout space) |

**Gradient shorthand (preferred):**
```scss
background: linear-gradient(135deg, #f00 0%, #00f 50%, #0f0 100%);
background-image: linear-gradient(90deg, red, blue);  /* CSS alias */
```
2-stop shorthand: `background: linear-gradient(90deg, red, blue)`

**Hover/click gradient:**
```scss
.btn:hover { background: linear-gradient(90deg, #3498db, #2ecc71); }
```

#### Typography

| Property            | Type   | Default    | Description                                                   |
|---------------------|--------|------------|---------------------------------------------------------------|
| `font-size`         | length | `12px`     | Text size                                                     |
| `text-align`        | enum   | `left`     | Horizontal: `left`, `center`, `right`                         |
| `--text-align-v`    | enum   | `center`   | Vertical: `top`, `center`, `bottom`                           |
| `--text-x`          | length | `0`        | Text horizontal offset                                        |
| `--text-y`          | length | `0`        | Text vertical offset                                          |
| `font-weight`       | enum   | `normal`   | `normal`, `bold`                                              |
| `font-style`        | enum   | `normal`   | `normal`, `italic`                                            |
| `text-decoration`   | enum   | `none`     | `none`, `underline`                                           |
| `text-transform`    | enum   | `none`     | `none`, `uppercase`, `lowercase`, `capitalize`                |
| `letter-spacing`    | length | `0`        | Character spacing in px                                       |
| `line-height`       | float  | `1.2`      | Line height multiplier (unitless)                             |
| `white-space`       | enum   | `normal`   | `normal` (wrap), `nowrap`                                     |
| `text-overflow`     | enum   | `clip`     | `clip`, `ellipsis` (requires `white-space: nowrap`)           |
| `text-shadow`       | short  | none       | `offset-x offset-y blur color` — single shadow only          |

Font face selection uses YAML `font:` attribute (e.g., `font: NeueMontreal-Bold`), not CSS `font-family`. `font-weight` and `font-style` select the closest loaded variant.

#### Box Model

| CSS Property              | Type   | Default       | Description                                       |
|---------------------------|--------|---------------|---------------------------------------------------|
| `width`                   | length | `0`           | Element width (`px`, `%`, `auto`)                 |
| `height`                  | length | `0`           | Element height                                    |
| `padding`                 | short  | `0`           | Padding (shorthand: `10px`, `10px 20px`)          |
| `margin`                  | short  | `0`           | Margin (shorthand)                                |
| `border-radius`           | length | `0`           | All-corner radius (shorthand)                     |
| `border-radius: a b c d`  | short  | `0`           | Per-corner: top-left top-right bottom-right bottom-left |
| `border-top-left-radius`  | length | `0`           | Individual corner radius                          |
| `border-top-right-radius` | length | `0`           | Individual corner radius                          |
| `border-bottom-right-radius` | length | `0`        | Individual corner radius                          |
| `border-bottom-left-radius`  | length | `0`        | Individual corner radius                          |
| `border-width`            | length | `0`           | Uniform border width (or shorthand `t r b l`)     |
| `border-top-width`        | length | `0`           | Top border width                                  |
| `border-right-width`      | length | `0`           | Right border width                                |
| `border-bottom-width`     | length | `0`           | Bottom border width                               |
| `border-left-width`       | length | `0`           | Left border width                                 |
| `border-color`            | color  | `transparent` | Border color (uniform)                            |
| `border`                  | short  | none          | `border: 1px solid red` shorthand                 |
| `border-top`              | short  | none          | `border-top: 2px solid red`                       |
| `border-right`            | short  | none          | Per-side border shorthand                         |
| `border-bottom`           | short  | none          | Per-side border shorthand                         |
| `border-left`             | short  | none          | Per-side border shorthand                         |
| `border-image`            | short  | none          | `border-image: linear-gradient(angle, c1, c2)`    |
| `overflow`                | enum   | `visible`     | `hidden`, `visible`, `scroll`, `auto`             |
| `overflow-x`              | enum   | `visible`     | `hidden`, `visible`, `scroll`, `auto`             |
| `overflow-y`              | enum   | `visible`     | `hidden`, `visible`, `scroll`, `auto`             |
| `box-sizing`              | enum   | `content-box` | `content-box`, `border-box`                       |
| `pointer-events`          | enum   | `auto`        | `auto`, `none`                                    |

**Border gradient** (CSS standard):
```scss
.card { border-image: linear-gradient(135deg, #3498db, #2ecc71); border-width: 1px; }
```

Per-side border **colors** are not currently supported — use a uniform `border-color`.

#### Transitions

| Property                    | Type     | Default  | Description                              |
|-----------------------------|----------|----------|------------------------------------------|
| `transition`                | shorthand| none     | `property duration timing-function` — comma-separated for multiple |
| `transition-property`       | string   | `none`   | Animatable property name                 |
| `transition-duration`       | time     | `0s`     | Duration in seconds (e.g. `0.3s`)        |
| `transition-timing-function`| enum     | `ease`   | `ease`, `linear`, `ease-in`, `ease-out`, `ease-in-out` |
| `transition-delay`          | time     | `0s`     | Delay before starting                    |

**Animatable properties:** `background-color`, `color`, `border-color`, `opacity`

```scss
// Single property
.button {
  background-color: #252830;
  transition: background-color 0.2s ease;
  &:hover { background-color: #353942; }
}

// Multi-property
.card {
  background-color: #1e2028;
  opacity: 1;
  transition: background-color 0.2s ease, opacity 0.15s ease-out;
  &:hover { background-color: #252830; opacity: 0.9; }
}
```

#### Box Shadow

| CSS Property        | Type        | Default | Description                         |
|---------------------|-------------|---------|-------------------------------------|
| `box-shadow`        | shorthand   | none    | `offsetX offsetY blur color`        |

Example: `box-shadow: 4px 4px 10px rgba(0,0,0,0.5);`

#### Layout (Flexbox)

| CSS Property      | Type  | Default    | Values                                                         |
|-------------------|-------|------------|----------------------------------------------------------------|
| `display`         | enum  | `flex`     | `flex`, `grid`, `block`, `none`                                |
| `flex-direction`  | enum  | `row`      | `row`, `column`, `row-reverse`, `column-reverse`               |
| `justify-content` | enum  | `start`    | `start`, `end`, `center`, `space-between`, `space-around`, `space-evenly` |
| `align-items`     | enum  | `start`    | `start`, `end`, `center`, `baseline`, `stretch`                |
| `align-content`   | enum  | `start`    | `start`, `end`, `center`, `stretch`, `space-between`, `space-around` |
| `flex-wrap`       | enum  | `nowrap`   | `nowrap`, `wrap`, `wrap-reverse`                               |
| `flex-grow`       | float | `0`        | Growth factor                                                  |
| `flex-shrink`     | float | `1`        | Shrink factor                                                  |
| `flex-basis`      | length| `0`        | Base size                                                      |
| `gap`             | length| `0`        | Gap between flex/grid items                                    |

#### Layout (Grid)

| CSS Property             | Type   | Default  | Description                    |
|--------------------------|--------|----------|--------------------------------|
| `grid-template-rows`     | list   | none     | Row track sizes                |
| `grid-template-columns`  | list   | none     | Column track sizes             |
| `grid-auto-flow`         | enum   | `row`    | `row`, `column`                |
| `grid-row`               | string | `auto`   | Row placement                  |
| `grid-column`            | string | `auto`   | Column placement               |

#### Positioning

| CSS Property  | Type  | Default    | Values                  |
|---------------|-------|------------|-------------------------|
| `position`    | enum  | `relative` | `relative`, `absolute`  |

#### Image (Extensions)

| CSS Property     | Type  | Default | Description                          |
|------------------|-------|---------|--------------------------------------|
| `--img-align-h`  | enum  | `left`  | Image horizontal: `left`, `center`, `right` |
| `--img-align-v`  | enum  | `top`   | Image vertical: `top`, `center`, `bottom`   |

### Pseudo-Classes for Interactivity

Instead of separate hover/click color properties, use standard pseudo-classes:

```scss
.button {
  background-color: #252830;
  color: #f0f3f6;
  border-radius: 8px;
  padding: 8px 15px;
  transition: background-color 0.15s ease;

  &:hover {
    background-color: #353942;
  }

  &:active {
    background-color: #4a5664;
  }
}
```

**Supported pseudo-classes:**
- `:hover` — mouse is over the element
- `:active` — element is being clicked/pressed

### SCSS Features

All standard SCSS is supported (compiled via `grass`):
- Variables: `$primary: #3498db;`
- Nesting: `.parent { .child { } }`
- Mixins: `@mixin`, `@include`
- Partials & imports
- `!default` for overridable component variables
- `var(--name)` CSS custom properties (with optional fallback: `var(--name, default)`)
- `@media (min-width: Npx)` / `@media (max-width: Npx)` queries

### Color Formats

All standard CSS color formats work:
```scss
color: #ff6600;
color: rgb(255, 102, 0);
color: rgba(255, 102, 0, 0.8);
color: red;
```

> Colors are automatically converted from sRGB to linear color space for Blender's viewport.

---

## 3. Components

Components are reusable YAML+SCSS templates with parameters.

### Defining a Component

**`components/card.yaml`:**
```yaml
card:
  style: card
  card_header:
    style: card_header
    text: "{{title, 'Card Title'}}"
    font: NeueMontreal-Bold
  card_body:
    style: card_body
    text: "{{content, 'Card content goes here.'}}"
  card_footer:
    style: card_footer
    action_btn:
      style: card_action
      text: "{{action_text, 'Action'}}"
```

**`components/card.scss`:**
```scss
$card_bg: #1e2028 !default;
$card_radius: 12px !default;

.card {
  display: flex;
  flex-direction: column;
  width: 300px;
  background-color: $card_bg;
  border-radius: $card_radius;
  padding: 16px;
  gap: 8px;
  transition: background-color 0.15s ease;

  &:hover {
    background-color: lighten($card_bg, 5%);
  }
}

.card_header {
  font-size: 18px;
  color: #f0f3f6;
}

.card_body {
  font-size: 14px;
  color: rgba(181, 188, 199, 0.9);
}

.card_action {
  background-color: #3498db;
  color: white;
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 14px;
  text-align: center;
  transition: background-color 0.15s ease;

  &:hover {
    background-color: #2980b9;
  }

  &:active {
    background-color: #1f6da3;
  }
}
```

### Using Components

```yaml
root:
  style: root
  my_card:
    data: '[card]'
    title: User Profile
    content: View and edit your profile settings.
    action_text: Edit
    card_bg: '#2a2d35'
```

### Parameter Syntax

`{{parameter_name, 'default_value'}}`

- Parameter names must be alphanumeric + underscores
- Default value is **required** and must be **quoted**
- YAML params override SCSS `$variables` of the same name

### Namespacing

When instantiated, component children get prefixed with the instance name:

```yaml
profile_card:
  data: '[card]'
# Creates: profile_card, profile_card_card_header, profile_card_card_body, etc.
```

This prevents ID collisions when using the same component multiple times.

---

## 4. Script (`script.py`)

### Structure

```python
def main(self, app):
    # Access elements via dot notation from root
    button = app.theme.root.sidebar.nav_button

    def on_click(container):
        print(f"Clicked: {container.id}")

    button.click.append(on_click)
    return app  # MUST return app
```

### Event Types

| Event       | Usage                            | Callback signature         |
|-------------|----------------------------------|----------------------------|
| `click`     | `el.click.append(fn)`            | `fn(container)`            |
| `hover`     | `el.hover.append(fn)`            | `fn(container)`            |
| `hoverout`  | `el.hoverout.append(fn)`         | `fn(container)`            |
| `toggle`    | `el.toggle.append(fn)`           | `fn(container)`            |
| `scroll`    | `el.scroll.append(fn)`           | `fn(container)`            |

### Modifying Properties at Runtime

```python
def on_click(container):
    label = app.theme.root.main.status_label
    label.text = "Updated!"
    label.mark_dirty()  # REQUIRED after property changes
```

### Showing/Hiding Elements

```python
def toggle_modal(container):
    modal = app.theme.root.modal
    modal.style.display = 'FLEX' if modal.style.display == 'NONE' else 'NONE'
    modal.mark_dirty()
```

### Accessing Component Children

```python
# Component "my_card" using "[card]" template:
# Access namespaced children:
header = app.theme.root.my_card_card_header
body = app.theme.root.my_card_card_body
```

---

## 5. Complete Example

### `index.yaml`
```yaml
app:
  selected_theme: demo
  default_theme: demo
  theme:
    - name: demo
      author: example
      version: 1.0.0
      default_font: NeueMontreal-Regular
      styles:
        - static/style.scss
      scripts:
        - static/script.py
      components: static/components/
      root:
        style: root
        header:
          style: header
          logo:
            style: logo
            img: my_logo
          title:
            style: header_title
            text: "My Application"
            font: NeueMontreal-Bold
        content:
          style: content
          sidebar:
            style: sidebar
            nav_home:
              style: nav_item
              text: "Home"
            nav_settings:
              style: nav_item
              text: "Settings"
          main:
            style: main
            welcome_card:
              data: '[card]'
              title: Welcome
              content: Get started with Puree UI.
              action_text: Learn More
```

### `style.scss`
```scss
$bg-dark: #0f1014;
$bg-card: #1a1d24;
$text-primary: #f0f3f6;
$text-secondary: rgba(181, 188, 199, 0.9);
$accent: #3498db;
$radius: 8px;

.root {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  background-color: transparent;
}

.header {
  display: flex;
  flex-direction: row;
  align-items: center;
  width: 100%;
  height: 60px;
  background-color: $bg-dark;
  padding: 0 20px;
  gap: 12px;
}

.logo {
  width: 32px;
  height: 32px;
  --img-align-h: center;
  --img-align-v: center;
}

.header_title {
  font-size: 20px;
  color: $text-primary;
}

.content {
  display: flex;
  flex-direction: row;
  width: 100%;
  height: 100%;
}

.sidebar {
  display: flex;
  flex-direction: column;
  width: 200px;
  height: 100%;
  background-color: $bg-card;
  padding: 10px;
  gap: 4px;
}

.nav_item {
  width: 100%;
  height: 36px;
  background-color: transparent;
  color: $text-secondary;
  font-size: 14px;
  text-align: left;
  --text-align-v: center;
  border-radius: $radius;
  padding: 0 12px;
  transition: background-color 0.15s ease;

  &:hover {
    background-color: rgba(255, 255, 255, 0.05);
    color: $text-primary;
  }

  &:active {
    background-color: rgba(255, 255, 255, 0.1);
  }
}

.main {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  padding: 20px;
  background-color: transparent;
}
```

### `script.py`
```python
def main(self, app):
    nav_home = app.theme.root.content.sidebar.nav_home
    nav_settings = app.theme.root.content.sidebar.nav_settings

    def go_home(container):
        print("Navigate to Home")

    def go_settings(container):
        print("Navigate to Settings")

    nav_home.click.append(go_home)
    nav_settings.click.append(go_settings)
    return app
```

---

## 6. Puree-Specific Extensions (Custom Properties)

Properties prefixed with `--` are Puree extensions not found in standard CSS:

| Extension                        | Purpose                          |
|----------------------------------|----------------------------------|
| `--text-align-v`                 | Vertical text alignment          |
| `--text-x`, `--text-y`          | Text position offsets            |
| `--img-align-h`, `--img-align-v`| Image alignment within container |

For background gradients, use `background: linear-gradient(...)` — standard CSS.
For border gradients, use `border-image: linear-gradient(...)` — standard CSS.

---

## 7. Common Patterns

### Centered Container
```scss
.centered {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}
```

### Scrollable List
```scss
.scroll_list {
  display: flex;
  flex-direction: column;
  overflow: scroll;   // enables vertical scrolling
  width: 100%;
  height: 300px;
  gap: 4px;
}
```

### Modal Overlay
```scss
.modal_overlay {
  position: absolute;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal_box {
  width: 400px;
  height: 300px;
  background-color: #1e2028;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}
```

### Gradient Button
```scss
.gradient_button {
  background: linear-gradient(90deg, #3498db, #2ecc71);
  border-radius: 8px;
  padding: 10px 20px;
  color: white;
  font-size: 16px;
  text-align: center;
  transition: opacity 0.2s ease;

  &:hover {
    opacity: 0.85;
  }
}
```

### Transition
```scss
// Single property
.animated_card {
  background-color: #1e2028;
  border-color: rgba(255,255,255,0.08);
  transition: background-color 0.2s ease;

  &:hover {
    background-color: #252830;
  }
}

// Multi-property
.animated_card_multi {
  background-color: #1e2028;
  opacity: 1;
  transition: background-color 0.2s ease, opacity 0.15s ease-out;

  &:hover {
    background-color: #252830;
    opacity: 0.9;
  }
}
```

### CSS Custom Properties (`var()`)
```scss
// Define in :root or any parent
:root {
  --brand-color: #3498db;
  --radius: 8px;
}

.button {
  background-color: var(--brand-color);
  border-radius: var(--radius);
  color: var(--text-color, #ffffff);  // fallback value
}
```

### Responsive Layout (`@media`)
```scss
.sidebar {
  width: 250px;

  @media (max-width: 768px) {
    width: 100%;
  }
}

.card {
  padding: 24px;

  @media (min-width: 1200px) {
    padding: 40px;
  }
}
```

### Per-Side Border
```scss
.underlined {
  border-bottom: 2px solid rgba(255,255,255,0.2);
  border-radius: 0;
}

.pill_badge {
  border-width: 1px 2px 1px 2px;  // top right bottom left
  border-color: rgba(255,255,255,0.1);
}
```

---

## 8. Rules & Constraints

1. **Node names use underscores**: `my_button` ✓, `my-button` ✗
2. **Always return `app`** from `script.py`'s `main()` function
3. **Call `mark_dirty()`** after modifying container properties at runtime
4. **Component params need defaults**: `"{{name, 'default'}}"` — both quotes required
5. **Component `data` uses brackets**: `data: '[card]'` — square brackets required
6. **Font names omit extensions**: `font: NeueMontreal-Bold` (not `.ttf`)
7. **Image names omit extensions**: `img: my_icon` (not `.png`)
8. **Colors auto-convert**: sRGB in CSS → linear in Blender (automatic)
9. **`passive: true`** makes an element completely non-interactive (no hover/click)
10. **`display: none`** hides an element and removes it from layout
