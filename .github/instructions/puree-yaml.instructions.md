---
description: "Use when editing Puree YAML UI files. Covers node structure, naming rules, theme config, component instantiation, and parameter syntax."
applyTo: "**/*.yaml"
---

# Puree YAML Structure

Puree YAML defines UI hierarchy (like HTML). Each node becomes a GPU-rendered container.

## Node Properties

| Property  | Type   | Description                                              |
|-----------|--------|----------------------------------------------------------|
| `style`   | string | CSS class name (matched as `.classname` in SCSS)         |
| `class`   | string | Space-separated CSS classes (alternative to `style`)     |
| `text`    | string | Text content to display                                  |
| `font`    | string | Font face name without extension: `NeueMontreal-Bold`   |
| `img`     | string | Image filename from `assets/` with extension: `my_icon.png` (`.gif` animates, `.svg` rasterizes crisp) |
| `video`   | string | Video filename with extension: `intro.mp4` (decoded by PyAV, which ships bundled with Puree) |
| `lottie`  | string | Bodymovin JSON filename: `confetti.json` (decoded by rlottie, which ships bundled with Puree) |
| `controls`| bool   | Video only: `true` injects the default controls bar |
| `autoplay` / `loop` / `muted` | bool | Playback flags — video defaults all `false`, **lottie defaults `autoplay`/`loop` to `true`** |
| `poster` / `preload` / `volume` / `playback_rate` | misc | Video extras: poster image, `none\|metadata\|auto`, 0–1 volume, speed (≠ 1.0 force-mutes audio) |
| `data`    | string | Component ref `'[component_name]'` or input `"<INPUT>"` |
| `passive` | bool   | If true, element ignores hover/click                     |

## Critical Rules

1. **Node names MUST use underscores** — `my_button` ✓ `my-button` ✗ (parser breaks on hyphens)
2. **Nesting = parent-child** — indentation creates the container tree
3. **`root` is the body** — equivalent to `<body>` in HTML
4. **Component data uses brackets** — `data: '[card]'` (square brackets required)
5. **Parameters need both quotes** — `text: "{{param_name, 'default_value'}}"`
6. **Text input syntax** — `data: "<INPUT>|placeholder text"`
7. **Fonts omit extensions, image/media values include them** — `font: NeueMontreal-Bold` but `img: my_icon.png`, `video: intro.mp4`, `lottie: confetti.json` (extensionless media renders nothing + logs a "did you mean" error)

## Theme Config Structure

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
        # UI tree goes here
```

## Component Instantiation

```yaml
# Reference a component (loads components/card.yaml)
my_card:
  data: '[card]'
  title: Custom Title           # overrides {{title, 'default'}}
  content: Custom content text  # overrides {{content, 'default'}}
```

## Parameter Syntax (in component definitions)

```yaml
# components/button.yaml
button:
  style: "{{btn_style, 'default_button'}}"
  btn_label:
    text: "{{btn_text, 'Click Me'}}"
    font: NeueMontreal-Bold
    passive: true
```

- Parameter format: `"{{name, 'default'}}"` — outer double quotes, inner single quotes, comma separator
- SCSS `$variables` with matching names are also overridden by params

## Media Example

```yaml
spinner: { style: spinner, img: loading.gif }      # GIF/SVG ride img: — no new syntax
demo_video:
  style: demo_video
  video: intro.mp4        # assets/intro.mp4
  controls: true          # default play/seek/mute bar
  autoplay: true
  loop: true
  muted: true             # good etiquette for autoplay
celebration:
  style: celebration
  lottie: confetti.json   # autoplay + loop default TRUE for lottie
```

## Minimal Correct Example

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
          title:
            style: title_text
            text: "My Panel"
            font: NeueMontreal-Bold
        content:
          style: content
          my_button:
            style: button
            text: "Click Me"
```

For full reference: [PUREE_SPEC.md](../../docs/PUREE_SPEC.md)
