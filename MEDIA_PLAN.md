# Media Support Plan — GIF, SVG, MP4 & Lottie

> **Status: ✅ implemented 2026-07-19** (phases 0–7 all shipped); see `docs/.media_progress.md`
> for the as-built record including per-phase deviations. This document stays as the design record.

> Implementation plan for animated and vector media in Puree, bringing the framework
> closer to browser parity: `<img src="*.gif">`, `<img src="*.svg">`,
> `<video controls>` with HTML-like default controls, and Lottie animations —
> all rendered natively inside Blender panels.

---

## 1. Vision & Scope

| Format | HTML equivalent | Puree surface | Scope |
|--------|----------------|---------------|-------|
| GIF    | `<img src="spin.gif">` | existing `img:` attribute — just works | Animated playback, per-frame delays, looping |
| SVG    | `<img src="logo.svg">` | existing `img:` attribute — just works | Static SVG 1.1/2 rasterized crisp at layout size (no SMIL/scripting) |
| MP4    | `<video controls autoplay loop muted poster=...>` | new `video:` attribute | H.264/H.265/VP9/AV1 via FFmpeg, audio, seek, full playback API, default controls |
| Lottie | `<lottie-player>` | new `lottie:` attribute | Bodymovin JSON playback, loop/speed control |

**Non-goals (v1):** SVG animation (SMIL/CSS), `.lottie` zip containers, network media URLs,
fullscreen, subtitles/captions, camera/mic capture, DRM.

---

## 2. Where the Engine Is Today

Everything below is verified against the current codebase and shapes the design:

- **Images are an overlay pass, not part of the container shader.** `img_op.py` keeps one
  `gpu.types.GPUTexture` per asset (`ImageManager._load_images`, `img_op.py:60-81`, decoded by
  `bpy.data.images.load` + `gpu.texture.from_image`) and draws each `ImageInstance` as a quad in its
  own `POST_PIXEL` handler (`draw_all_images`, `img_op.py:291-381`) with scissor = mask ∩ scroll-clip.
  **Consequence: animating media = swapping `instance.texture` per tick. No layout, no container
  data-texture rebuild.** This makes video/GIF surprisingly cheap.
- **Format support is a single extension whitelist** at `img_op.py:66`
  (`.png .jpg .jpeg .bmp .tiff .tga .webp`). GIF/SVG/MP4/Lottie are not loadable by
  `bpy.data.images.load`, so each needs its own decode path.
- **The render loop is a ~60 Hz modal timer with on-demand redraw.** `XWZ_OT_start_ui` adds
  `event_timer_add(0.016)`; each TIMER tick runs transitions, dirty-sync, scroll — and only calls
  `tag_redraw()` when something changed (`render.py:2370-2391`). `TransitionManager`
  (`transition_manager.py`, ticked at `render.py:1911-1982`) is the exact precedent for a media
  clock: `has_active()` feeds `needs_redraw`, idle UI costs nothing.
- **Geometry plumbing is already format-agnostic.** `ImageExtractor` (`extract_images.py`) emits
  `image_blocks` keyed by container id (content box, mask, align, opacity); scrolling re-anchors
  them (`render.py:1355-1374`); `render.py:1695` creates one `ImageInstance` per block. Reusing
  this stream means media scrolls/clips correctly for free.
- **Draw order is: containers → images → text → text inputs** (`POST_PIXEL` handlers fire in
  registration order: `render.py:601`, `img_op.py:440`, `text_op.py:727`, `text_input_op.py:693`).
  **Consequence: child containers render *under* the video frame.** Default video controls need an
  overlay container pass (§7.2) — text alone already draws on top.
- **`components/defaults/` is currently passive.** `scrollbar.yaml/.scss` are documentation (the
  scrollbar is drawn programmatically, `render.py:603-700`); `markdown_defaults.scss` injection has
  a **path bug** — `parser.py:641` looks in `puree/` but the file lives in
  `puree/components/defaults/`, so it silently never loads. This plan fixes and generalizes that
  mechanism (§7.1).
- **Interaction primitives are sufficient for controls.** Click fires on press
  (`hit_op.py:149-178`), `mouse_state.register_callback` provides the move/release stream,
  `parser.node_flat_abs` provides absolute geometry, and `InputRouter` capture keeps Blender from
  stealing drags (`input_router.py:125-139`). The draggable card in `tests/helloworld/script.py:113-174`
  is the canonical drag pattern a seek bar follows.
- **Deps ship per-platform already**: Rust core as prebuilt `.pyd`/`.so`, Python deps as wheels
  listed in `blender_manifest.toml`. New decoders slot into both mechanisms.

---

## 3. Architecture Overview

One new engine subsystem, `puree/media/`, owning decode, caching, playback state, and GPU upload.
Rendering stays in the existing image overlay pass.

```
                        ┌────────────────────────────────────────────┐
                        │                puree/media/                │
 YAML attrs             │                                            │
 img: spin      ──────► │  MediaManager (singleton)                  │
 img: logo              │   ├─ sources: {container_id: MediaSource}  │
 video: intro           │   ├─ tick(now)  ◄── render modal TIMER     │
 lottie: confetti       │   └─ has_active() ──► needs_redraw         │
                        │                                            │
                        │  MediaSource (per element)                 │
                        │   ├─ MediaClock: play/pause/seek/loop/rate │
                        │   ├─ Decoder (per format, see §5)          │
                        │   ├─ FrameCache (GPU budget, §10)          │
                        │   └─ current GPUTexture ───────────┐       │
                        └────────────────────────────────────┼───────┘
                                                             ▼
                                     img_op.ImageInstance.texture  (swap only)
                                     draw_all_images()             (unchanged)
```

**Tick flow (each 16 ms TIMER tick, alongside `TransitionManager`):**

1. `MediaManager.tick(time.monotonic())` — advance each playing clock; audio-backed sources sync
   to the `aud` handle position instead (§5.3).
2. For each source whose frame index changed: pull decoded RGBA frame (from cache or the decoder
   thread's queue), upload → swap `ImageInstance.texture`.
3. Fire throttled script events (`timeupdate` ≈ 4 Hz, `ended`, …).
4. `has_active()` → `needs_redraw = True` → `tag_redraw()`. Paused/ended/offscreen media costs zero.

**Texture upload path** (Blender `gpu` has no `texture.write()`): recreate per frame —
`gpu.types.Buffer('UBYTE', w*h*4, data)` → `gpu.types.GPUTexture((w, h), format='SRGB8_A8', data=buf)`.
`SRGB8_A8` gives hardware sRGB→linear on sample, matching how `bpy.data.images` uploads behave
today (validate visually in Phase 1 against the same content as PNG). Decoders emit
**premultiplied** RGBA to match `alpha_mode = "PREMUL"` + `ALPHA_PREMULT` blending
(`img_op.py:74,309`). ~8 MB/frame at 1080p30 is well within PCIe budget; the Python-side cost is
one `Buffer` construction (bytes pass through, no per-pixel work).

**Visibility gating:** if a source's effective scissor rect (mask ∩ clip) is empty or the target
space isn't visible, skip decode + upload but keep the clock advancing (browser behavior for
offscreen `<video>`).

---

## 4. Shared Engine Work (prerequisites)

### 4.1 Media-aware asset & attribute plumbing

- **Breaking change (decided): `img:` values must be full filenames with extension**
  (`img: logo.png`, `img: spinner.gif`). Rationale: with `.svg`/`.gif` joining the asset scan,
  extensionless names become ambiguous (`logo` → `logo.png` or `logo.svg`?); requiring the
  extension makes collisions structurally impossible instead of resolved by precedence rules —
  and fixes today's latent `logo.png` vs `logo.webp` last-scanned-wins ambiguity too.
  - `ImageManager` (`img_op.py`) keys `images`/`textures` by **full filename** instead of
    `os.path.splitext(...)[0]`; subfolders allowed (`img: icons/play.svg`).
  - Extensionless (or unresolvable) values render nothing and log an actionable error:
    `img: 'logo' has no extension — did you mean logo.png or logo.svg?` (suggestions from the
    scanned asset list).
  - Migration (all in Phase 0): `tests/helloworld/index.yaml:274` (`img: loggoui2` →
    `img: loggoui2.png`), docs (`PUREE_SPEC.md:86,947`, `API.md:157`), skill/instruction files
    (`.agents/skills/review/SKILL.md:35`, `frontend-design/reference/interaction-design.md:195`,
    scaffold copies), and a changelog/release note entry. The `puree init` CLI emits no `img:`
    today — nothing to change there. `font:` keeps its extensionless convention (fonts are a
    separate registry and out of scope).
- `ImageManager._load_images` (`img_op.py:66`): add `.gif`, `.svg` to the scan with format
  dispatch — static formats keep the current path; GIF/SVG register a `MediaSource` factory
  instead of eagerly decoding.
- `Container` (`components/container.py`): new attributes `video`, `lottie`, `poster`,
  `controls`, `autoplay`, `loop`, `muted`, `volume`, `playback_rate`, `preload` + additions to the
  `__setattr__` whitelist (`container.py:224-260`). YAML already routes scalar node keys through
  `set_container_attr` (`parser.py:173-180`), so no parser syntax work is needed.
- `ImageExtractor` (`extract_images.py`): also emit blocks for `video:` / `lottie:` elements, and
  tag every block with `media_kind: image|gif|svg|video|lottie` plus the playback attrs. Keeping
  **one** `image_blocks` stream means scroll offset/clip logic (`render.py:1237-1374`) and
  instance creation (`render.py:1695`) work untouched.
- `render.py` start-up: after the `draw_image` loop, call `MediaManager.attach(image_blocks,
  _image_instances)` — seeds each media instance with its first frame / poster texture
  (synchronously decoded so aspect-ratio fitting via `get_display_size()` is correct immediately),
  then registers the tick with the modal.

### 4.2 Defaults infrastructure (bug fix + generalization)

Fix `parser.py:641` to point at `puree/components/defaults/`, then generalize into a defaults
loader used by both markdown and video controls:

- **SCSS**: prepend every `components/defaults/*.scss` (compiled) to the user's style string in
  `UI.parse_css()` — user styles keep winning by cascade order; `!default` vars stay overridable.
- **YAML components**: register `components/defaults/*.yaml` into `UI._component_registry` under a
  reserved `puree_` prefix (e.g. `[puree_video_controls]`) so engine code and users can
  `add_child()` them. Real templates this time — unlike the virtual scrollbar.

### 4.3 Overlay container pass (containers above images)

Needed so control containers (seek track, buttons, gradient scrim) can sit **on top of** the video
frame. Design that avoids touching the fragile 68-float stride entirely:

- New `overlay: true` container flag (set automatically on injected controls subtrees).
- `render.py` packs **two data textures with the same packing code**: main (non-overlay) and
  overlay containers. No GLSL change — the shader just gets bound to a different, smaller data
  texture in a second handler.
- Register the overlay handler **between** the image loop and text loop in
  `XWZ_OT_start_ui.execute` (`render.py:~1712`), yielding: containers → images/video → overlay
  containers → text → inputs. Time labels and icons already draw above via the text/image passes.
- Hit detection is position-based (Rust `HitDetector` reads the container buffer, not draw order)
  — no changes.

This is the highest-risk item in the plan (it touches `draw_texture` and data-texture caching),
but it is also reusable groundwork for tooltips, dropdowns, and toasts over images.

---

## 5. Per-Format Design

### 5.1 GIF — `img: spinner.gif`

- **Decoder:** Rust, in `puree_core` — the `image` crate with only the `gif` feature. New PyO3 fn:
  `decode_gif(path) -> (width, height, frames: Vec<Bytes>, delays_ms: Vec<u16>)`, frames
  premultiplied RGBA8, GIF disposal methods resolved to full frames at decode time.
- **Caching:** decode once per *file* (shared across elements); each element gets its own clock
  (independent playback, like browsers). Pre-upload all frames as GPUTextures when total ≤ budget
  (e.g. 32 MB per file); above that, keep CPU frames and upload-on-demand into a small texture ring.
- **Playback:** honors per-frame delays (min clamp 20 ms like browsers), loops per the GIF loop
  count (∞ default). No user-facing API needed — parity with `<img>`. Scripts can still reach
  `container.media` (pause/play) as a bonus.

### 5.2 SVG — `img: logo.svg`

- **Rasterizer:** Rust, in `puree_core` — `resvg`/`usvg`/`tiny-skia` (pure Rust, ~2-3 MB binary
  cost). New PyO3 fn: `rasterize_svg(path, width, height) -> Bytes` (premultiplied RGBA8).
  Fonts: `usvg` `fontdb` loading system fonts + the addon's `fonts/` dir once at startup.
- **Crispness:** rasterize at the element's **content-box size** (known from `image_blocks`), not
  the SVG's intrinsic size; re-rasterize when the layout size changes beyond ±1 px, debounced
  ~150 ms through the media tick. Cache keyed by `(path, w, h)`. Intrinsic aspect ratio from
  `viewBox` feeds `get_display_size()`.
- Static only — no clock; a rasterized SVG behaves exactly like a PNG afterwards (zero per-frame
  cost).

### 5.3 MP4/WebM — `video: intro.mp4`

- **Decoder:** **PyAV** (`av` wheel, bundles FFmpeg; abi3 wheels cover Blender's Python 3.13 on
  all four manifest platforms). Runs in a **daemon decoder thread** per playing video: seek-aware
  packet loop → RGB(A) frames into a bounded queue (4–8 frames, drop-oldest). Only the main thread
  touches GPU. `preload: none|metadata|auto` controls whether we probe only (duration/size) or
  decode the first frame eagerly; `poster: name` shows a static asset until first play.
- **Optional dependency by design:** `av` is imported lazily. If missing, the element renders its
  poster with a logged warning and `media.ready_state == 'unsupported'` — addon authors choose
  whether to ship the (~25-40 MB/platform) wheel in *their* manifest. `puree init --with-video`
  scaffolds it.
- **Audio + sync:** Blender's built-in **`aud`** module (audaspace, FFmpeg-backed — zero new deps)
  plays the file's audio track directly: `aud.Device().play(aud.Sound(path))`, with `pause()`,
  `resume()`, `position`, `volume`. When unmuted, **audio is the master clock** (video frames
  chase `handle.position`, dropping/holding as needed); when muted, the monotonic clock drives.
  Verify `aud` container support on all platforms in Phase 4 spike; fallback is video-clock only.
- **Behavior parity:** `autoplay`, `loop`, `muted` attributes; `ended` state; seeking clamps to
  duration; `playback_rate` (video-clock only in v1 — `aud` pitch-preserving rate is out of scope).

### 5.4 Lottie — `lottie: confetti.json`

- **Renderer:** `rlottie-python` (ctypes wheel over Samsung rlottie, prebuilt for win/mac/linux,
  ~1 MB). Optional dependency, lazy-imported like `av`. Render-on-demand per frame at the
  element's content-box size into premultiplied RGBA, driven by the shared clock at the
  animation's native fps; loops fully cached when small (same budget rule as GIF).
- `autoplay` (default true, like `lottie-player`), `loop`, `playback_rate` supported;
  `container.media` API identical to video minus audio.
- **Future option (recorded, not planned):** vendor ThorVG/dotlottie-rs into `puree_core` for
  spec-complete rendering and `.lottie` container support — heavier C++ build per platform.

---

## 6. Authoring Surface

### 6.1 YAML

```yaml
# GIF & SVG ride the existing img: attribute — no new syntax.
# NOTE: all media values are full filenames incl. extension (§4.1 breaking change).
spinner:
  style: spinner
  img: loading.gif          # assets/loading.gif → animated automatically

logo:
  style: logo
  img: brand.svg            # assets/brand.svg → crisp at any panel size

# Video, HTML-flavored
demo_video:
  style: demo_video
  video: clips/intro.mp4    # assets/clips/intro.mp4
  controls: true            # inject default controls (§7)
  autoplay: false
  loop: false
  muted: true
  poster: intro_poster.png  # assets/intro_poster.png

# Lottie
celebration:
  style: celebration
  lottie: confetti.json     # assets/confetti.json
  loop: true
```

### 6.2 SCSS

Media elements are containers — all existing properties apply (`--img-align-h/v`,
`aspect-ratio`, `opacity`, radius/border/shadow on the container). Controls theming via
`!default` variables in `video_controls.scss` (§7.3).

### 6.3 Python — `container.media` controller

```python
video = app.theme.root.demo_video

video.media.play()
video.media.pause()
video.media.toggle()
video.media.seek(12.5)                 # seconds
video.media.current_time               # float, seconds
video.media.duration                   # float | None until metadata ready
video.media.paused / .ended / .loop / .muted / .volume / .playback_rate
video.media.ready_state                # 'none'|'metadata'|'ready'|'unsupported'|'error'

video.media.on("play", fn)             # play, pause, ended, seeked, error
video.media.on("timeupdate", fn)       # throttled ~250 ms, like browsers
```

Names are pythonic (`current_time`), semantics are HTMLMediaElement. The controller lives on
`MediaSource`; `Container.media` resolves through `MediaManager` by container id (and raises a
clear error on non-media containers).

---

## 7. Default Video Controls (`components/defaults/`)

### 7.1 Files

```
puree/components/defaults/
  video_controls.yaml     # real component template: [puree_video_controls]
  video_controls.scss     # themable via !default vars
  markdown_defaults.scss  # (existing — injection path fixed in Phase 0)
```

### 7.2 Structure & injection

```
video container (user's YAML node)
└── {id}_puree_vc              overlay bar (overlay: true, auto-hide)
    ├── ..._scrim              bottom gradient scrim
    ├── ..._play               play/pause toggle (icon imgs: play.svg / pause.svg)
    ├── ..._time               "0:12 / 1:30" text label
    ├── ..._track              seek track
    │   └── ..._fill           progress fill (width % updated on tick)
    └── ..._mute               mute toggle (icon imgs)
```

- When the parser sees `controls: true` on a `video:` node, it instantiates
  `[puree_video_controls]` as the node's last child through the **existing component machinery**
  (`load_component` / `_instantiate_component_into`) — so namespacing, CSS cascade, hit detection,
  and dynamic rebuilds all behave like any user component. The subtree is marked `overlay: true`
  (§4.3).
- `puree/media/controls.py` wires behavior after parse (engine-level, same lifecycle as user
  scripts, with the stale-root guard pattern from `tests/helloworld/script.py:86-98`):
  - play/pause/mute: `click` handlers → `media.play()/pause()`, icon swap via
    `instance.update_image(...)`.
  - **seek drag**: the proven helloworld pattern — `click` (press) starts the gesture,
    `mouse_state.register_callback` streams moves/release, `node_flat_abs[track_id]` maps
    mouse-x → 0..1, `InputRouter` capture holds the gesture; scrubbing calls `media.seek()`
    (throttled), fill width via `set_property("width", f"{pct}%")`.
  - time label: updated from the `timeupdate` event (4 Hz — text relayout is not per-frame).
  - auto-hide: show on `hover`, fade via `opacity` transition on `hoverout` while playing
    (opacity is one of the three transition-animatable properties — no new engine work).
  - keyboard: when the video container is focused, `keys.bind("SPACE", toggle)` via
    `puree.keyboard`.

### 7.3 Theming

`video_controls.scss` exposes `!default` vars (`$vc-bar-height`, `$vc-accent`, `$vc-bg`,
`$vc-radius`, icon sizes). Users override by defining the vars or restyling the namespaced
classes — defaults are prepended so user SCSS always wins (§4.2).

---

## 8. File-by-File Change Map

| Layer | File | Change |
|-------|------|--------|
| Python | `puree/media/__init__.py` | **new** — `MediaManager`, budgets, attach/tick/shutdown |
| Python | `puree/media/clock.py` | **new** — playback state machine, loop/rate/ended logic |
| Python | `puree/media/controller.py` | **new** — `container.media` API + events |
| Python | `puree/media/decoders/{gif,svg,video,lottie}.py` | **new** — per-format sources (Rust/PyAV/rlottie bindings) |
| Python | `puree/media/controls.py` | **new** — default controls wiring |
| Python | `puree/img_op.py` | key assets by full filename + extension validation/error hints (§4.1); extend format scan/dispatch (`:66`); allow manager-driven texture swap on `ImageInstance` |
| Python | `puree/extract_images.py` | emit `media_kind` + playback attrs; handle `video:`/`lottie:` nodes |
| Python | `puree/components/container.py` | new media attributes + whitelist; `.media` property |
| Python | `puree/parser.py` | fix defaults path (`:641`) → generalized defaults loader; `controls: true` injection; register default components |
| Python | `puree/render.py` | media tick in modal TIMER (beside transitions `:1911`); `MediaManager.attach` after image ops (`:1695`); overlay container pass (`:601`, `draw_texture`); teardown hooks |
| Python | `puree/components/defaults/video_controls.{yaml,scss}` | **new** — default controls component |
| Rust | `puree_core/src/media/{mod,gif,svg}.rs` | **new** — `decode_gif`, `rasterize_svg` (PyO3); deps: `image` (gif feature), `resvg` |
| Rust | `puree_core/src/lib.rs`, `Cargo.toml` | register module + deps; rebuild via `just build_core` |
| Packaging | `blender_manifest.toml`, `dist/update_wheels.py`, `pyproject.toml` | optional `av` / `rlottie-python` wheels; `puree-ui[video,lottie]` extras; CLI scaffold flags |
| Docs | `docs/PUREE_SPEC.md`, `API.md`, `COMPONENTS.md`, `KNOWLEDGE_BASE.md`, instruction files | new attributes, media API, controls theming, gotchas, extension-required convention |
| Examples | `tests/helloworld/index.yaml:274`, `.agents/skills/**` refs | migrate `img:` values to full filenames (Phase 0) |

---

## 9. Dependencies, Size & Licensing

| Dependency | Kind | Size | License | Required? |
|-----------|------|------|---------|-----------|
| `image` crate (gif only) | Rust, in `puree_core` | ~small | MIT/Apache-2.0 | yes (built-in) |
| `resvg`/`usvg`/`tiny-skia` | Rust, in `puree_core` | +2-3 MB binary | MPL-2.0 / MIT | yes (built-in) |
| `av` (PyAV 18.x, FFmpeg bundled) | Python wheel | ~25-40 MB/platform | BSD wrapper, FFmpeg LGPL build | ~~**optional** (video)~~ **bundled with core** (superseded 2026-07-20 — see note below + §12 decision 1) |
| `rlottie-python` | Python wheel | ~1 MB | MIT (rlottie: MIT) | ~~**optional** (lottie)~~ **bundled with core** (superseded 2026-07-20 — see note below + §12 decision 1) |
| `aud` (audaspace) | ships with Blender | 0 | — | yes (audio) |

Puree is GPL-3.0-or-later (`blender_manifest.toml`) — all of the above are GPL-compatible.
GIF + SVG land with **zero new runtime dependencies** for end users (Rust core already ships).
Video/Lottie degrade gracefully when their wheel is absent (§5.3), so the core extension zip
doesn't balloon for addons that don't use them.

> **Note (2026-07-20)** — the optional-wheel policy above is superseded: `av` 18.0.0 and
> `rlottie-python` 1.3.8 now **ship with Puree core** (Puree's own `blender_manifest.toml`
> `wheels[]` + pyproject/setup.py dependencies; one wheel per manifest platform). The lazy
> imports and graceful degrade in §5.3/§5.4 stay as the safety net. Actual wheel sizes:
> av 18.2–35.5 MB/platform, rlottie-python 0.4–1.0 MB/platform (~19–37 MB added per platform).

---

## 10. Performance Budgets & Memory Policy

- **Idle rule (non-negotiable):** paused/ended/static media triggers zero redraws —
  `MediaManager.has_active()` mirrors `transitions.has_active()`.
- **Targets:** 1080p30 video ≤ ~2 ms main-thread per tick (Buffer + texture create + swap);
  128 px GIF spinner ≤ 0.2 ms; SVG zero after raster; Lottie 512 px ≤ 3 ms (rlottie CPU raster).
- **GPU budget:** global media budget (default 256 MB) tracked by `MediaManager`; per-file GIF
  pre-upload cap 32 MB (else texture ring); video uses a 3-4 texture ring; LRU eviction of paused
  offscreen sources.
- **Decode threads:** one per *playing* video, joined on pause-after-grace/teardown; queue
  drop-oldest keeps latency bounded on slow machines.
- **No layout work from playback:** frame swaps never touch Taffy, the container data texture
  (except the separate overlay texture when controls change state), or `sync_dirty_containers`.
  Time-label text updates ride the existing dirty-sync at 4 Hz.

---

## 11. Delivery Phases

Each phase is independently shippable and reviewable (engine phases end with `just build_core` +
`just reload` + helloworld verification).

| # | Phase | Size | Contents | Acceptance criteria | Status |
|---|-------|------|----------|---------------------|--------|
| 0 | Groundwork | S | Fix `parser.py:641` path bug; generalized defaults SCSS prepend + default-component registry; **`img:` full-filename migration** (§4.1: filename keys, error + suggestions, helloworld/docs/skills updates, release note) | Markdown defaults actually load; user overrides still win; helloworld renders with `img: loggoui2.png`; extensionless `img:` logs the did-you-mean error | ✅ done |
| 1 | Media core + GIF | M | `puree/media/` skeleton (manager/clock/tick/upload), `image_blocks.media_kind`, Rust `decode_gif`, budget/caching | `img: spinner` animates with correct delays & loop; multiple instances independent; idle when paused/offscreen; hot reload leak-free | ✅ done |
| 2 | SVG | M | Rust `rasterize_svg`, size-change re-raster (debounced), fontdb setup | SVG crisp at any panel size incl. resize; `viewBox` aspect respected; text-in-SVG renders | ✅ done |
| 3 | Video element | L | PyAV optional decoder thread, `video:`/`poster`/`autoplay`/`loop`/`muted`/`preload`, `container.media` API + events | mp4 plays/loops/seeks via script API; poster shown pre-play & when `av` missing; scroll/clip correct; teardown clean | ✅ done |
| 4 | Audio + sync | M | `aud` playback, mute/volume, audio-master clock, drift correction | A/V stays in sync ≥ 5 min; mute/unmute seamless; no orphaned audio after reload/unregister (platform spike first) | ✅ done |
| 5 | Overlay pass + default controls | L | §4.3 overlay container pass; `video_controls` component + injection + `controls.py` wiring; auto-hide; SPACE binding | Controls render above video, drag-seek accurate, time label updates, themable via `!default` vars, hover auto-hide fades | ✅ done (theming = class overrides / shadow copy, see progress log) |
| 6 | Lottie | M | `rlottie-python` optional source, `lottie:` attribute, shared clock/budget | Bodymovin JSON plays at native fps with loop/speed; graceful degrade without wheel | ✅ done |
| 7 | Docs + polish | S | Spec/API/COMPONENTS/KNOWLEDGE_BASE updates, instruction files, helloworld demo page, `puree init` extras | Docs match behavior; demo page exercises all four formats | ✅ done |

Suggested order: 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7. Phases 2 and 3 can proceed in parallel after 1;
Phase 6 anytime after 1.

---

## 12. Risks & Open Questions

**Risks**

| Risk | Mitigation |
|------|------------|
| Overlay pass touches `draw_texture` + data-texture caching (most fragile subsystem per KNOWLEDGE_BASE) | Two-texture design avoids stride/GLSL changes entirely; land behind the `overlay:` flag with controls as the only consumer initially |
| Color-space mismatch (raw uploads vs `bpy.data.images` path) | `SRGB8_A8` texture format + premultiplied decode; Phase 1 includes side-by-side PNG-vs-GIF visual check |
| Per-frame `GPUTexture` recreation too slow on weak GPUs | Measured in Phase 1; fallback: cap video fps to 30, decode-size clamp (e.g. ≤ 1080p), texture ring reuse |
| Hot-reload teardown with live decoder threads / audio handles | `MediaManager.shutdown()` called from both `unregister()` and pre-reparse; threads joined with timeout; follows `puree.timers` auto-cleanup precedent |
| `aud` mp4 audio support varies by platform build | Phase 4 starts with a 1-day spike on win/linux/mac; fallback: video-clock only + documented limitation |
| rlottie spec gaps (some AE features unsupported) | Document limitations; ThorVG vendoring recorded as future upgrade path |

**Decisions (resolved 2026-07-19)**

1. **Wheel policy** — ✅ optional extras. `av`/`rlottie-python` are never bundled with core;
   `puree init --with-video/--with-lottie` scaffolds the manifest entries; missing wheel degrades
   to poster + logged warning.
   **SUPERSEDED 2026-07-20**: owner decided to bundle `av` + `rlottie-python` with Puree core
   (dev-experience friction; installing into Blender's Python directly is not acceptable UX).
   The `--with-video`/`--with-lottie` init flags are retired; the lazy-import graceful degrade
   stays as a safety net. See §9 note.
2. **Autoplay policy** — ✅ unmuted autoplay allowed. Docs and scaffold examples still default to
   `muted: true` as good practice.
3. **`img:` collision precedence** — ✅ superseded by a stronger decision: **`img:` (and all new
   media attributes) require the full filename with extension** (`img: logo.png`). Collisions
   become structurally impossible; extensionless values log an actionable error. Breaking change
   — see §4.1 and Phase 0.
4. **`playback_rate` with audio** — ✅ v1 limitation: setting `playback_rate != 1.0` on an
   unmuted video forces mute for the duration (documented).
5. **Event naming** — ✅ `media.on("event", fn)` is the canonical (and only) media event API.

---

## 13. Test Plan

- **Assets** (tiny, committed under `tests/helloworld/assets/`): 2-frame + 30-frame GIFs
  (disposal-method variants), SVG with viewBox/text/gradients, ~5 s 480p H.264+AAC mp4,
  simple Lottie JSON.
- **Unit (pytest, no bpy):** clock math (loop/rate/seek/ended), extension validation + error
  suggestions ("did you mean…"), GIF delay clamping, budget/eviction accounting, Rust decoders
  golden-tested against reference RGBA dumps.
- **In-Blender (helloworld demo page + `just reload`):** playback of all four formats, seek-drag
  accuracy, controls theming override, scroll-clip while playing, panel resize (SVG re-raster),
  space switch, N simultaneous videos, hot reload mid-playback, unregister → zero leaked
  threads/handles/textures (assert via `just logs`).
- **Perf gate:** frame-time deltas logged by the existing FPS counter with a 10-video stress page;
  budgets from §10 asserted manually before each phase ships.

---

## 14. Documentation Updates (Phase 7 checklist)

- `PUREE_SPEC.md` — `video:`/`lottie:` attributes, media attrs table, `img:` GIF/SVG note,
  **extension-required convention** (flips spec line 86 and gotcha #7 at line 947; migration
  itself lands in Phase 0).
- `API.md` — `container.media` controller reference + events.
- `COMPONENTS.md` — `[puree_video_controls]` theming (`!default` vars).
- `KNOWLEDGE_BASE.md` — overlay pass rationale, media budgets, "patterns that don't work"
  additions (e.g. expecting `transform` on video, nested controls).
- Instruction files (`puree-yaml`, `puree-script`, `puree-engine`) + scaffold templates.
