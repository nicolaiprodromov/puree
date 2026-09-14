# Fullscreen Plan — Region Presentation Mode

> Design record, agreed 2026-07-20. Companion to MEDIA_PLAN.md (§7 controls).
> Status: SHIPPED — Phase A (engine) + Phase B (API/controls/demo/docs) done 2026-07-20.
> Implementation record: docs/.media_progress.md §"Fullscreen Phase A/B — done".

## Decisions (owner-approved)

1. **Scope: region-only fullscreen** — the element fills the editor region Puree draws in
   ("theater mode"). Blender area-maximize (`screen.screen_full_area`) deferred as a possible
   later opt-in; OS fullscreen permanently out of scope.
2. **Backend: renderer short-circuit (option B)** — fullscreen is a *presentation mode flag*,
   not a document mutation. The main UI tree is never touched; while active, the renderer
   draws only a backdrop + the fullscreen subtree. Enter/exit is trivially reversible.
3. **Generic capability** — ANY container can go fullscreen (`container.request_fullscreen()`);
   video merely uses it via the controls button. Unlocks lightboxes/focus modes later.
4. **Gestures: fullscreen button + ESC only.** No double-click (would require adding
   double-click to the event system — explicitly out of scope).

## Refinement to B (approved rationale): subtree relayout, not geometric scaling

Scaling the subtree's existing layout to region size would stretch text glyphs (blurry,
wrong metrics) and misalign hit zones. Instead, on enter (and on region resize while active):

- The fullscreen element becomes the root of a **private Taffy layout pass** sized to the
  region. The main document's layout tree is untouched.
- Subtree text/image blocks are re-extracted from that private layout (crisp text, correctly
  stretched seek bar, valid hit rects).
- Exit simply drops the private data — the main tree was never modified, nothing to restore.

## Architecture

New module `puree/fullscreen.py` — `FullscreenManager` (singleton, same lifecycle discipline
as MediaManager):

- `enter(container_id)` / `exit()` / `active_id` / `is_active()`; one element at a time
  (entering while active swaps).
- On enter: private subtree layout at region dims → dedicated fullscreen data texture
  (reuses the Phase 5 filtered-packing + flat→local index remap machinery) + subtree
  text/image block sets; media ImageInstances retarget position/mask from these blocks.
- Render integration (`render.py`): when active, the container/image/overlay/text handlers
  skip their normal passes and draw: black backdrop (region rect) → fullscreen containers →
  fullscreen media instance(s) → fullscreen text. Scrollbars skipped. Main-tree data textures
  stay resident (instant exit).
- Hidden-UI behavior while active: transitions/media clocks keep ticking (browser parity:
  other media keep playing; upload gating already skips their textures for free). Dirty-sync
  of the hidden tree continues (cheap, avoids stale state at exit).
- Hit detection: on enter, hot-load ONLY the subtree rects into the Rust HitDetector (same
  hot-sync path scrolling already uses: `load_containers`); restore full set on exit.
- Input: while active, InputRouter consumes all events over the region; ESC bound via
  `puree.keyboard` by the manager (bound on enter, unbound on exit).
- Region resize while active: recompute the private layout (cheap, single subtree).
- Hot reload / reparse / UI stop: force-exit fullscreen (flag reset in the same paths that
  call `MediaManager.shutdown()` + `unwire_video_controls()` — keep the trio together).

## Public API

- `container.request_fullscreen()` / `container.exit_fullscreen()` / `container.fullscreen`
  (read-only bool) — on every Container.
- `container.on_fullscreen_change` handler list (consistent with click/hover convention).
- Video convenience: `media.on("fullscreenchange", fn)` alias so media code stays in one
  event style.
- No new YAML attributes in v1. (Open question recorded: `allow_fullscreen: false` to hide
  the controls button — decide during implementation review.)
  **RESOLVED (Phase B, 2026-07-20): NO `allow_fullscreen` YAML attribute in v1.** The button
  is always present on `controls: true` videos; per-video hiding works from user SCSS via the
  namespaced class — `.{video_id}_puree_vc_fullscreen { display: none; }` (a node created
  display:none never gets a layout box: no draw, no hit target; verified by
  `test_user_scss_can_hide_fullscreen_button` and documented in COMPONENTS.md).

## Controls integration

- New icons: `assets/media_fullscreen.svg`, `assets/media_exit_fullscreen.svg` (hand-written
  glyphs matching the existing media_* set).
- `[video_controls]` gains a fullscreen toggle button (right side, after mute); wired in
  `puree/media/controls.py` via the generic API; icon flips via the established display-swap
  pattern; ESC and the button both exit.
- Controls bar must lay out correctly at region width in the private layout pass (it will —
  it is part of the subtree).

## Edge cases (test targets)

- Enter → exit → re-enter loops; swap between two fullscreen elements.
- Region resize + panel space switch while active.
- Hot reload mid-fullscreen → clean force-exit, no orphaned ESC binding/hit set.
- Scroll-clipped element goes fullscreen (private layout escapes ancestor clipping by design).
- Media keeps playing through enter/exit without frame/audio glitches.
- Non-media container fullscreen (generic path has no media assumptions).

## Delivery phases

| # | Phase | Contents | Acceptance |
|---|-------|----------|------------|
| A ✅ done 2026-07-20 | Engine mode | FullscreenManager, private subtree layout, render short-circuit passes, hit-set swap, ESC, resize, teardown/reload reset + headless sims/tests | Any container enters/exits fullscreen headlessly; main tree byte-identical after exit; zero leaked bindings |
| B ✅ done 2026-07-20 | API + controls + demo + docs | Container API + events, controls button + icons, helloworld demo (video button + one generic "fullscreen this card" script example), PUREE_SPEC/API/KNOWLEDGE_BASE updates | Button + ESC round-trip in helloworld; docs match behavior |
