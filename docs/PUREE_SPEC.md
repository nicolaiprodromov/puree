---
layout: page
title : 4. Puree Specification
---

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

Each `theme:` entry may also set a `space:` key selecting which Blender editor the UI renders in (e.g. `space: VIEW_3D` — the default when omitted). Supported values: `VIEW_3D`, `IMAGE_EDITOR`, `NODE_EDITOR`, `SEQUENCE_EDITOR`, `CLIP_EDITOR`, `DOPESHEET_EDITOR`, `GRAPH_EDITOR`, `NLA_EDITOR`, `TEXT_EDITOR`, `CONSOLE`, `INFO`, `TOPBAR`, `STATUSBAR`, `OUTLINER`, `PROPERTIES`, `FILE_BROWSER`, `SPREADSHEET`, `PREFERENCES`.

### Node Properties

Each YAML node can have these properties:

| Property     | Type   | Description                                        |
|--------------|--------|----------------------------------------------------|
| `style`      | string | CSS class name for styling (matched as `.classname` in SCSS) |
| `class`      | string | Space-separated CSS class names (alternative to `style`)     |
| `text`       | string | Text content to display                            |
| `font`       | string | Font name (without extension): `NeueMontreal-Bold` |
| `img`        | string | Image filename from `assets/`, including extension (e.g. `my_icon.png`; subfolders allowed: `icons/x.png`). Also accepts `.gif` (plays animated) and `.svg` (vector — rasterized crisp at the element's layout size) |
| `video`      | string | Video filename from `assets/` (`.mp4`, `.webm`, `.mkv`, `.mov`). Decoded by PyAV (`av`), bundled with Puree — see [Media Elements](#10-media-elements) |
| `lottie`     | string | Lottie/Bodymovin `.json` filename from `assets/`. Decoded by `rlottie-python`, bundled with Puree — see [Media Elements](#10-media-elements) |
| `poster`     | string | Video only: raster asset shown until the first decoded frame (and if video decode is unavailable). Default `""` |
| `controls`   | bool   | Video only: `true` injects the default playback controls bar (`[video_controls]`). Default `false` |
| `autoplay`   | bool   | Start playing on load. Default `false` for `video:`, **`true` for `lottie:`** |
| `loop`       | bool   | Loop playback. Default `false` for `video:`, **`true` for `lottie:`** |
| `muted`      | bool   | Video only: start with audio muted. Default `false` (examples still set `muted: true` — good etiquette) |
| `volume`     | float  | Video only: audio volume `0.0`–`1.0`. Default `1.0` |
| `playback_rate` | float | Playback speed. Default `1.0`. On video, a rate ≠ `1.0` force-mutes audio (v1 limitation) |
| `preload`    | enum   | Video only: `none` \| `metadata` (default) \| `auto` |
| `data`       | string | Component reference: `'[component_name]'`          |
| `data`       | string | Text input: `'<INPUT> \| placeholder text'` turns the node into an editable text input |
| `passive`    | bool   | If true, element is non-interactive                |
| `focusable`  | bool   | If true, element can receive keyboard focus        |
| `tab_index`  | int    | Tab order for keyboard navigation (`-1` = not in tab order) |
| `collapsed`  | bool   | If true, container starts in collapsed state       |
| `virtual`    | bool   | If true, enables virtual scrolling for this container |
| `item_height` | int\|string | Virtual scroll item height in px, or `'auto'` for variable height |
| `overlay`    | bool   | Renders this container **and its whole subtree** in the overlay pass, above images/video (used automatically by the injected video controls) |

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

// Universal selector
* { letter-spacing: 0; }

// Sibling combinators
.label + .value { color: #999; }          // adjacent sibling
.item ~ .item { border-top-width: 1px; }  // general sibling

// Structural pseudo-classes
.list_item:first-child { border-radius: 8px 8px 0 0; }
.list_item:last-child { border-radius: 0 0 8px 8px; }
.row:nth-child(odd) { background-color: rgba(255,255,255,0.03); }  // odd, even, an+b
.nav_item:not(.active) { opacity: 0.7; }

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
- `font-family`
- `font-weight`
- `font-style`
- `pointer-events`
- `visibility`
- `text-transform`
- `line-height`
- `letter-spacing`
- `white-space`

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
| `text-decoration`   | enum   | `none`     | `none`, `underline`, `overline`, `line-through`               |
| `text-transform`    | enum   | `none`     | `none`, `uppercase`, `lowercase`, `capitalize`                |
| `letter-spacing`    | length | `0`        | Character spacing in px                                       |
| `line-height`       | float  | `1.2`      | Line height multiplier (unitless)                             |
| `white-space`       | enum   | `normal`   | `normal` (wrap), `nowrap`, `pre`                              |
| `text-overflow`     | enum   | `clip`     | `clip`, `ellipsis` (requires `white-space: nowrap`)           |
| `text-shadow`       | short  | none       | `offset-x offset-y blur color` — single shadow only          |
| `text-shadow-color`        | color  | `transparent` | Text shadow color (rgba)                               |
| `text-shadow-offset-x`    | length | `0`        | Text shadow horizontal offset (px)                            |
| `text-shadow-offset-y`    | length | `0`        | Text shadow vertical offset (px)                              |
| `text-shadow-blur`         | length | `0`        | Text shadow blur radius (px)                                  |
| `overflow-wrap`     | enum   | `normal`   | `normal`, `break-word` — whether to break words to prevent overflow |
| `word-break`        | enum   | `normal`   | `normal`, `break-all` — word breaking rules                   |
| `scrollbar-width`   | length/enum | `auto` | Scrollbar track width (`px`, or `none` / `thin` / `auto`)     |
| `scrollbar-color`   | color pair  | —      | `<thumb-color> <track-color>` shorthand                       |
| `scrollbar-thumb-color` | color   | —      | Scrollbar thumb/handle color                                  |
| `scrollbar-track-color` | color   | —      | Scrollbar track background color                              |

Font face selection uses YAML `font:` attribute (e.g., `font: NeueMontreal-Bold`), not CSS `font-family`. `font-weight` and `font-style` select the closest loaded variant.

#### Box Model

**Units:** length values accept `px`, `%`, `rem`, `em`, `vw`, `vh`, `vmin`, and `vmax`, plus `calc()` expressions with `+` and `-` only (e.g. `calc(100% - 40px)`).

| CSS Property              | Type   | Default       | Description                                       |
|---------------------------|--------|---------------|---------------------------------------------------|
| `width`                   | length | `0`           | Element width (`px`, `%`, `rem`, `em`, `vw`/`vh`/`vmin`/`vmax`, `calc()`, `auto`) |
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
| `border`                  | short  | none          | `border: 1px solid red` shorthand. **Note**: the `border` shorthand reliably sets width; use `border-color` separately for reliable color setting. |
| `border-top`              | short  | none          | `border-top: 2px solid red`                       |
| `border-right`            | short  | none          | Per-side border shorthand                         |
| `border-bottom`           | short  | none          | Per-side border shorthand                         |
| `border-left`             | short  | none          | Per-side border shorthand                         |
| `border-image`            | short  | none          | `border-image: linear-gradient(angle, c1, c2)`    |
| `overflow`                | enum   | `visible`     | `hidden`, `visible`, `scroll`, `auto`             |
| `overflow-x`              | enum   | `visible`     | `hidden`, `visible`, `scroll`, `auto`             |
| `overflow-y`              | enum   | `visible`     | `hidden`, `visible`, `scroll`, `auto`             |
| `box-sizing`              | enum   | `border-box`  | `content-box`, `border-box`                       |
| `pointer-events`          | enum   | `auto`        | `auto`, `none`. `none` prevents hover/click detection on the element and all children — use for overlay containers that shouldn't block interaction. |

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

**Animatable properties:** `background-color`, `border-color`, `opacity`

> Note: `color` (text color) changes are applied instantly on hover/active — they are **not** transition-interpolated.

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
| `display`         | enum  | `flex`     | `flex`, `grid`, `block`, `none`. `block`: children stack vertically and fill parent width (no flex properties like `flex-grow` apply). `flex`: standard flexbox. `grid`: CSS grid. `none`: hidden + removed from layout. |
| `flex-direction`  | enum  | `row`      | `row`, `column`, `row-reverse`, `column-reverse`               |
| `justify-content` | enum  | `start`    | `start`, `end`, `center`, `space-between`, `space-around`, `space-evenly` |
| `align-items`     | enum  | `stretch`  | `start`, `end`, `center`, `baseline`, `stretch`                |
| `align-content`   | enum  | `start`    | `start`, `end`, `center`, `stretch`, `space-between`, `space-around` |
| `flex-wrap`       | enum  | `nowrap`   | `nowrap`, `wrap`, `wrap-reverse`                               |
| `flex-grow`       | float | `0`        | Growth factor                                                  |
| `flex-shrink`     | float | `1`        | Shrink factor                                                  |
| `flex-basis`      | length| `auto`     | Base size                                                      |
| `gap`             | length| `0`        | Gap between flex/grid items                                    |

#### Layout (Grid)

| CSS Property             | Type   | Default  | Description                    |
|--------------------------|--------|----------|--------------------------------|
| `grid-template-rows`     | list   | none     | Row track sizes (e.g., `80px auto 1fr`)  |
| `grid-template-columns`  | list   | none     | Column track sizes (e.g., `1fr 1fr 1fr`) |
| `grid-auto-rows`         | size   | `auto`   | Size of implicitly created rows          |
| `grid-auto-columns`      | size   | `auto`   | Size of implicitly created columns       |
| `grid-auto-flow`         | enum   | `row`    | `row`, `column`, `row dense`, `column dense` |
| `grid-row`               | string | `auto`   | Row placement (`auto`, `span N`, `N / M`)    |
| `grid-column`            | string | `auto`   | Column placement (`auto`, `span N`, `N / M`) |
| `row-gap`                | length | `0`      | Space between grid rows                  |
| `column-gap`             | length | `0`      | Space between grid columns               |

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

**Supported state pseudo-classes:**
- `:hover` — mouse is over the element
- `:active` — element is being clicked/pressed

Structural pseudo-classes (`:first-child`, `:last-child`, `:nth-child()`, `:not()`) are also supported — see the Selectors section above.

### SCSS Features

All standard SCSS is supported (compiled via `grass`):
- Variables: `$primary: #3498db;`
- Nesting: `.parent { .child { } }`
- Mixins: `@mixin`, `@include`
- Partials & imports
- `!default` for overridable component variables
- `var(--name)` CSS custom properties (with optional fallback: `var(--name, default)`)
- `@media (min-width: Npx)` / `@media (max-width: Npx)` / `@media (min-height: Npx)` / `@media (max-height: Npx)` queries

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
| `on_focus`  | `el.on_focus.append(fn)`         | `fn(container)`            |
| `on_blur`   | `el.on_blur.append(fn)`          | `fn(container)`            |

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
            img: my_logo.png
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

> Note: `min-width`, `max-width`, `min-height`, and `max-height` media queries are supported. Width values are matched against the panel width; height values against the panel height.

### Grid Layout

Puree supports CSS Grid layout via the Taffy engine:

**YAML:**
```yaml
grid_container:
  class: photo_grid
  photo1:
    class: photo_item
    text: "Photo 1"
  photo2:
    class: photo_item
    text: "Photo 2"
  photo3:
    class: photo_item
    text: "Photo 3"
  photo4:
    class: photo_item
    text: "Photo 4"
  photo5:
    class: photo_item
    text: "Photo 5"
  photo6:
    class: photo_item
    text: "Photo 6"
```

**SCSS:**
```scss
.photo_grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;   // 3 equal columns
  grid-auto-rows: 80px;                  // each row 80px tall
  gap: 8px;                              // gap between cells
  padding: 12px;
}

.photo_item {
  background-color: #2a2a2a;
  border-radius: 8px;
  // Items auto-place into the grid in row order
}
```

**Supported grid properties:**

| Property | Values | Description |
|----------|--------|-------------|
| `display: grid` | — | Enable grid layout |
| `grid-template-columns` | Track list (e.g., `1fr 1fr 1fr`, `100px auto 1fr`) | Define column tracks |
| `grid-template-rows` | Track list | Define row tracks |
| `grid-auto-rows` | Size (e.g., `80px`, `auto`) | Size of implicitly created rows |
| `grid-auto-columns` | Size | Size of implicitly created columns |
| `grid-auto-flow` | `row` \| `column` \| `row dense` \| `column dense` | How auto-placed items flow |
| `grid-row` | `auto` \| `span N` \| `N / M` | Item row placement |
| `grid-column` | `auto` \| `span N` \| `N / M` | Item column placement |
| `gap` / `row-gap` / `column-gap` | px | Space between grid cells |

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
7. **Image values include the file extension**: `img: my_icon.png` (subfolders allowed: `img: icons/x.png`)
8. **Colors auto-convert**: sRGB in CSS → linear in Blender (automatic)
9. **`passive: true`** makes an element completely non-interactive (no hover/click)
10. **`display: none`** hides an element and removes it from layout
11. **Runtime display values are UPPERCASE**: `'FLEX'`, `'NONE'`, `'GRID'` (CSS uses lowercase)

    > ⚠️ **Common debugging issue**: SCSS uses lowercase (`display: none`, `display: flex`) but Python runtime requires UPPERCASE (`style.display = 'NONE'`, `style.display = 'FLEX'`). Mismatched case will silently fail.

12. **Only 3 animatable properties**: `background-color`, `border-color`, `opacity` (`color` changes instantly on hover)
13. **Draw order**: Containers are drawn in tree order (depth-first), then sorted by CSS `z-index` — higher values draw later/on top. The sort is stable, so tree order is preserved among elements with equal `z-index`. Use CSS `z-index` for stacking. The YAML `layer:` attribute is **deprecated** and has no effect (it is never read by the engine).
14. **Container `.keys` property**: Use `container.keys.bind("SHIFT+ENTER", callback)` for container-scoped keyboard shortcuts. See the [Keyboard section in API Reference](API.md#keyboard--pureekeyboard).
15. **`video:` / `lottie:` decoders ship with Puree**: the PyAV (`av`) and `rlottie-python` wheels are bundled in Puree's own manifest — your addon ships nothing extra. If a package is somehow missing (exotic platform / broken install) the element degrades gracefully (poster / nothing + one logged warning), never a crash. See [Media Elements](#10-media-elements).

---

## 9. Built-in Modules

Puree provides built-in modules for common addon tasks. Import them in `script.py`.

### Dynamic Container Creation

```python
# Create child from component template
new_item = parent.add_child("[card]", id="card_1", params={"title": "Hello"})
new_item.mark_dirty()

# Insert at specific position
parent.insert_child(0, "[card]", id="card_top")

# Remove by ID or reference
parent.remove_child("card_1")

# Clear all children
parent.clear_children()
```

### Markdown Rendering

```python
from puree.markdown import render_markdown

# Preferred: Container method with full options
container.set_markdown(
    "# Title\n\nSome **bold** text and `code`.",
    fonts={"mono": "JetBrainsMono"},            # optional: custom fonts per element
    classes={"heading_1": "custom_heading"}     # optional: custom CSS classes per element
)

# Or use the function directly
render_markdown(container, markdown_text)
```

Supports: headings (h1-h6), bold, inline code, code blocks, list items, blockquotes, horizontal rules. Not supported: italics, links, images, tables, nested lists.
Each rendered block gets a default CSS class (`.md_paragraph`, `.md_h1`, `.md_code_block`, etc.) — style those classes in your SCSS, or remap elements to your own classes via the `classes` parameter.
Valid `fonts` keys: `regular`, `bold`, `mono`. Valid `classes` keys: `paragraph`, `heading_1`, `heading_2`, `heading_3`, `heading_n`, `code_block`, `code_inline`, `list_item`, `blockquote`, `divider`, `inline_row`, `bold`, `text_span`.

### Virtual Scrolling

```yaml
messages:
  style: scroll_area
  virtual: true
  item_height: 60
```

```python
def main(self, app):
    scroll = app.theme.root.messages
    
    # Provide data list
    items = [{"text": f"Message {i}", "sender": "user"} for i in range(1000)]
    scroll.set_virtual_data(items)
    
    # Define how each item renders
    def render_item(container, item, index):
        container.text = item['text']
        container.mark_dirty()
    
    scroll.set_item_renderer(render_item)
    return app
```

Only visible items are rendered; off-screen items are recycled automatically. Use `item_height: 'auto'` for variable-height items.

### Collapse / Expand

```yaml
details:
  collapsed: true
  header:
    text: "Click to expand"
  body:
    text: "Hidden content"
```

```python
def main(self, app):
    details = app.theme.root.details
    header = app.theme.root.details.header
    
    def toggle(container):
        details.toggle_collapse()
        details.mark_dirty()
    
    header.click.append(toggle)
    
    # You can also check state:
    # details.is_collapsed  → True/False
    # details.collapse()    → collapse instantly
    # details.expand()      → expand instantly
    return app
```

The first child of a collapsible container is the **header** (always visible); remaining children form the collapsible **body**. Collapse/expand is an **instant** visibility change — it is not animated.

### Keyboard Shortcuts

```python
from puree.keyboard import keys

def main(self, app):
    input_field = app.theme.root.input_field
    
    # Global shortcuts (always active)
    keys.bind("CTRL+N", lambda: new_chat())
    keys.bind("ESCAPE", lambda: cancel())
    
    # Conditional: only when a text input has focus
    keys.bind("ENTER", lambda: send_message(), when="input_focused")
    
    # Container-scoped: only when this specific container is focused
    input_field.keys.bind("SHIFT+ENTER", lambda: insert_newline())
    
    # Unbind when no longer needed
    binding = keys.bind("CTRL+S", lambda: save())
    keys.unbind(binding)
    return app
```

Key names use Blender conventions but common aliases (`ENTER`, `ESCAPE`, `DELETE`, `BACKSPACE`) are auto-mapped. Key callbacks are invoked with **no arguments** — bind zero-argument callables.

### Storage, Timers, HTTP, Focus

See the [API Reference](API.md) for full module documentation on these built-in modules.

---

## 10. Media Elements

Puree plays four media formats natively inside panels — HTML parity: `<img>` for GIF/SVG,
`<video>` for MP4/WebM, `<lottie-player>` for Bodymovin JSON. Media elements are ordinary
containers: all layout, radius/border/shadow, `opacity`, `--img-align-h/v` and scroll clipping
apply. Playback swaps GPU textures only — the layout never recomputes while media plays, and
paused/ended media costs zero redraws.

**All media values are full filenames with extension** (same rule as `img:`): `video: clips/intro.mp4`,
`lottie: confetti.json`. Extensionless values render nothing and log a one-time "did you mean" error.

### GIF & SVG — the `img:` attribute

No new syntax. Any `img:` value ending in `.gif` animates automatically (per-frame delays,
GIF loop count honored); `.svg` rasterizes at the element's **content-box size** and re-rasterizes
(debounced ~150 ms) when the layout size changes, so vectors stay crisp at any panel size.
Both work out of the box — the decoders ship in Puree's Rust core.

```yaml
spinner:
  style: spinner
  img: loading.gif          # assets/loading.gif → plays automatically

logo:
  style: logo
  img: brand.svg            # assets/brand.svg → crisp at any panel size
```

### Video — the `video:` attribute

H.264/H.265/VP9/AV1 etc. via PyAV/FFmpeg (`.mp4`, `.webm`, `.mkv`, `.mov`), with audio through
Blender's built-in `aud` module when the file has an audio track.

```yaml
demo_video:
  style: demo_video
  video: demo_clip.mp4      # assets/demo_clip.mp4
  controls: true            # inject the default controls bar
  autoplay: true
  loop: true
  muted: true               # good etiquette for autoplay
  poster: intro_poster.png  # shown until the first frame (and if decode is unavailable)
  preload: metadata         # none | metadata (default) | auto
```

- `preload: metadata` (default) probes duration/size only; `auto` also decodes and shows frame 0;
  `none` does nothing until `play()`/`seek()` (the `poster` shows if set).
- **Unmuted autoplay is allowed** but sound on panel-open surprises users — default your examples
  to `muted: true` like browsers force you to.
- `playback_rate != 1.0` **force-mutes audio** while the rate stays off 1.0 (v1 limitation; the
  `muted` attribute itself is not flipped — audio returns when the rate returns to `1.0`).
- `controls: true` injects the `[video_controls]` component as the node's last child — play/pause,
  drag-to-seek, time labels, mute toggle, hover auto-hide — drawn in the overlay pass **above**
  the frame. Theming and internals: [COMPONENTS.md](COMPONENTS.md#default-component-video_controls).
  SPACE toggles playback while the video container is focused (click it first; key dispatch
  requires at least one text input in the UI — engine constraint).

### Lottie — the `lottie:` attribute

Bodymovin/lottie-web JSON via `rlottie` (`.lottie` zip containers are **not** supported in v1).
Frames render at the element's content-box size and re-render on resize like SVG.

```yaml
celebration:
  style: celebration
  lottie: confetti.json     # assets/confetti.json
  # autoplay/loop default TRUE for lottie (lottie-player parity) —
  # write `autoplay: false` / `loop: false` explicitly to opt out
  playback_rate: 1.0
```

- **`autoplay` and `loop` default `true` for `lottie:`** (vs `false` for `video:`).
- `controls`, `muted`, `volume`, `poster` and `preload` have **no effect** on lottie elements
  (`controls: true` logs a debug note and is ignored; muted/volume are inert stored values).
- The `.json` must actually be a Bodymovin document (`v`/`fr`/`w`/`h`/`layers` keys) — anything
  else renders nothing with one warning per file. `img: anim.json` also plays, but `lottie:` is
  the canonical surface. Some After Effects features are outside rlottie's coverage — test your
  export.

### Fullscreen — region presentation mode

**Any container** can present fullscreen — it fills the **editor region** Puree draws in
("theater mode"; not Blender's area-maximize, not OS fullscreen). Video merely uses it via the
controls button; lightboxes/focus modes on plain containers work the same way. **One element at
a time** — entering while another is active swaps (the old one exits first). The main UI tree
is never touched: fullscreen is a renderer presentation flag with a private region-sized
relayout of the subtree, so exiting restores everything exactly — and a **hot reload / reparse
/ UI stop force-exits the mode by design**.

```python
tile = app.theme.root.media_tile

tile.request_fullscreen()   # -> bool; the subtree re-lays-out at region size
tile.exit_fullscreen()      # -> bool; only exits when THIS container is the active one
print(tile.fullscreen)      # read-only property

def on_fs(container, is_fullscreen):
    console.log(f"{container.id} fullscreen: {is_fullscreen}")

tile.on_fullscreen_change.append(on_fs)   # fires for button/ESC/scripts/swaps too
```

- **Exits:** `exit_fullscreen()`, the `[video_controls]` fullscreen button (present on every
  `controls: true` video), and **ESC** (key dispatch needs ≥ 1 text input in the UI — the same
  engine constraint as SPACE; the button/API always work). There is no `allow_fullscreen` YAML
  attribute (v1 decision) — hide the button per video from your SCSS via the namespaced class
  (see [COMPONENTS.md](COMPONENTS.md#default-component-video_controls)).
- `on_fullscreen_change` handlers fire as `fn(container, is_fullscreen)` after the change
  commits; a swap fires `False` for the old element, then `True` for the new one. Media
  containers additionally get `media.on("fullscreenchange", fn)` (the container list fires
  first).
- While active: other media keep playing hidden (browser parity), scrolling is disabled, and a
  scroll-clipped element escapes its ancestor clipping (the private layout has no scroll
  context). Animated style transitions inside the fullscreen subtree settle without
  interpolating (v1 limitation).

### Dependencies

GIF and SVG ship built in (Rust core). Video and Lottie decoders **ship bundled with Puree**
(the `av` and `rlottie-python` wheels are in Puree's own manifest since 2026-07-20) — your
addon ships **nothing extra**; `video:`/`lottie:` work out of the box:

| Feature | Package | Size | Behavior if the package is missing (exotic platform / broken install) |
|---------|---------|------|------------------------------------------------------------------------|
| `video:` | `av` (PyAV, bundles FFmpeg) — **bundled** | ~18–36 MB/platform | element shows its `poster` (or nothing), `media.ready_state == 'unsupported'`, one logged warning |
| `lottie:` | `rlottie-python` — **bundled** | ~0.4–1 MB/platform | element renders nothing, `ready_state == 'unsupported'`, one logged warning |

The lazy-import degrade path stays as a safety net: a missing package degrades gracefully
(poster/blank + ONE logged warning) — never a crash. If you see that warning in a normal
install, refresh/reinstall the Puree extension (Preferences → Extensions) or restart Blender.
Audio needs nothing extra (`aud` ships with Blender).

### Scripting

Every media container exposes `container.media` — an HTMLMediaElement-flavored controller
(`play()/pause()/toggle()/seek()/stop()`, `current_time`, `duration`, `paused`, `ended`, events
via `media.on("play"|"pause"|"ended"|"seeked"|"timeupdate"|"error", fn)`). Full reference:
[API.md — Media Playback](API.md#media-playback--containermedia).

**Known limitation:** hot-*adding* a new media node (or `controls: true`) via YAML hot reload
shows containers but not their images/labels until a UI restart — hot reload only updates
existing GPU instances. Editing attributes of existing media nodes hot-reloads fine.

---

|  | Previous Page | Next Page |
|----------|----------|------|
| Puree is under active development. APIs may change between versions. **Special thanks to the open-source community and the developers behind the projects that make puree possible.** | [API Reference](API.md) | [Puree vs CSS](PUREE_VS_CSS.md) |