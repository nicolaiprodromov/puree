#!/usr/bin/env python3
"""
Puree Render Pipeline Benchmark & Simulation
=============================================
Standalone simulation of the puree render pipeline (no Blender required).
Decomposes the render frame into pure atomic functions, benchmarks each,
and compares current vs proposed architectural changes.

Usage:
    python tests/render_benchmark.py [--sample-rate N] [--viewport WxH] [--iterations N]

Example:
    python tests/render_benchmark.py --sample-rate 8 --viewport 1574x882 --iterations 5
"""

import math
import time
import argparse
import sys
from dataclasses import dataclass, field
from typing import Optional
import numpy as np


# =============================================================================
# Section 1: Container Data Structures
# =============================================================================

CONTAINER_STRIDE = 54  # floats per container in the GPU buffer

@dataclass
class Container:
    """Mirror of the GLSL Container struct — 54 floats per container."""
    display: int = 1
    position: tuple = (0.0, 0.0)
    size: tuple = (100.0, 100.0)
    background_color: tuple = (0.0, 0.0, 0.0, 1.0)
    background_color_2: tuple = (0.0, 0.0, 0.0, 0.0)
    background_gradient_rot: float = 0.0
    hover_background_color: tuple = (0.0, 0.0, 0.0, -1.0)
    hover_background_color_2: tuple = (0.0, 0.0, 0.0, 0.0)
    hover_background_gradient_rot: float = 0.0
    click_background_color: tuple = (0.0, 0.0, 0.0, -1.0)
    click_background_color_2: tuple = (0.0, 0.0, 0.0, 0.0)
    click_background_gradient_rot: float = 0.0
    border_color: tuple = (0.0, 0.0, 0.0, 0.0)
    border_color_2: tuple = (0.0, 0.0, 0.0, 0.0)
    border_gradient_rot: float = 0.0
    border_radius: float = 0.0
    border_width: float = 0.0
    parent: int = -1
    overflow: int = 0
    box_shadow_offset: tuple = (0.0, 0.0, 0.0)
    box_shadow_blur: float = 0.0
    box_shadow_color: tuple = (0.0, 0.0, 0.0, 0.0)
    passive: int = 0
    name: str = ""  # for debugging only, not in GPU buffer


@dataclass
class FrameReport:
    """Timing and metric results from a single frame simulation."""
    # Timing (nanoseconds)
    mouse_buffer_ns: int = 0
    change_detect_ns: int = 0
    container_pack_ns: int = 0
    visibility_precompute_ns: int = 0
    shader_hover_ns: int = 0
    shader_render_ns: int = 0
    readback_pbo_ns: int = 0
    readback_numpy_ns: int = 0
    readback_upload_ns: int = 0

    # Counters
    total_container_loads: int = 0
    total_parent_chain_loads: int = 0
    total_sdf_evals: int = 0
    total_gradient_evals: int = 0
    total_shadow_evals: int = 0
    aabb_tests: int = 0
    aabb_passes: int = 0
    pixels_sampled: int = 0
    containers_changed: int = 0

    # Bandwidth estimates
    buffer_reads_bytes: int = 0
    readback_bytes: int = 0

    @property
    def total_ns(self) -> int:
        return (self.mouse_buffer_ns + self.change_detect_ns +
                self.container_pack_ns + self.visibility_precompute_ns +
                self.shader_hover_ns + self.shader_render_ns +
                self.readback_pbo_ns + self.readback_numpy_ns +
                self.readback_upload_ns)

    @property
    def total_ms(self) -> float:
        return self.total_ns / 1_000_000

    @property
    def aabb_hit_rate(self) -> float:
        return self.aabb_passes / max(self.aabb_tests, 1)

    @property
    def bandwidth_gb(self) -> float:
        return self.buffer_reads_bytes / 1e9


# =============================================================================
# Section 2: Container Dataset (Static Example - 69 containers)
# =============================================================================

def hex_to_rgba(hex_str: str) -> tuple:
    """Convert hex background_color string to RGBA tuple (0-1 range)."""
    h = hex_str.lstrip('#')
    if len(h) == 6:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return (r / 255.0, g / 255.0, b / 255.0, 1.0)
    elif len(h) == 8:
        r, g, b, a = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(h[6:8], 16)
        return (r / 255.0, g / 255.0, b / 255.0, a / 255.0)
    return (0.0, 0.0, 0.0, 1.0)

TRANSPARENT = (0.0, 0.0, 0.0, 0.0)
DISABLED = (0.0, 0.0, 0.0, -1.0)
BG_DARK = hex_to_rgba("0f1014")
BG_1A = hex_to_rgba("1a1d24")
BG_1F = hex_to_rgba("1f222a")
BG_25 = hex_to_rgba("252830")
BG_35 = hex_to_rgba("353942")
BG_4A = hex_to_rgba("4a5664")
SEPARATOR = hex_to_rgba("3a3d45")
RADIAL_BORDER = (74/255, 86/255, 100/255, 0.3)
UNDERLINE_COLOR = (140/255, 150/255, 165/255, 0.3)
TAG_BG = (68/255, 68/255, 68/255, 0.084)
RADIAL_COLOR = hex_to_rgba("4a5664")


def build_container_dataset(viewport_w: int = 1574, viewport_h: int = 882) -> list:
    """Build the 69-container dataset matching the static/ example.

    Positions are approximate but structurally accurate (same relative layout,
    same parent-child relationships, same visibility/passive flags).
    """
    # Center the 800x500 panel in the viewport
    cx = (viewport_w - 800) / 2
    cy = (viewport_h - 500) / 2

    containers = []

    def c(name, **kwargs):
        """Helper to create and append a container."""
        cont = Container(name=name, **kwargs)
        containers.append(cont)
        return len(containers) - 1

    # --- ROOT (index 0) ---
    i_root = c("root", position=(0, 0), size=(viewport_w, viewport_h),
               background_color=TRANSPARENT, parent=-1)

    # --- BG (index 1) ---
    i_bg = c("bg", position=(cx, cy), size=(800, 500),
             background_color=BG_DARK, border_radius=8, parent=0)

    # --- HEADER (index 2) ---
    hx, hy = cx, cy
    i_header = c("header1", position=(hx, hy), size=(800, 90),
                 background_color=BG_1A, background_color_2=BG_1F, background_gradient_rot=90.0,
                 parent=1)

    # Header > text_box (index 3)
    i_htb = c("text_box", position=(hx + 23, hy + 15), size=(560, 60),
              background_color=TRANSPARENT, parent=2)

    # Header > text_box > text (index 4)
    c("text", position=(hx + 23, hy + 15), size=(560, 23),
      background_color=TRANSPARENT, parent=3)

    # Header > text_box > separator (index 5)
    c("separator", position=(hx + 23, hy + 42), size=(560, 1),
      background_color=SEPARATOR, parent=3)

    # Header > text_box > text1 (index 6)
    c("text1", position=(hx + 23, hy + 52), size=(560, 16),
      background_color=TRANSPARENT, parent=3)

    # Header > logoh (index 7)
    c("logoh", position=(hx + 700, hy + 15), size=(100, 60),
      background_color=TRANSPARENT, parent=2)

    # --- CONTENT_CONTAINER (index 8) ---
    ccx, ccy = cx, cy + 90
    i_cc = c("content_container", position=(ccx, ccy), size=(800, 410),
             background_color=TRANSPARENT, parent=1)

    # --- LEFT SIDE (index 9) ---
    lx, ly = ccx, ccy
    i_left = c("left_side_interactions", position=(lx, ly), size=(400, 410),
               background_color=BG_1A, parent=8, overflow=0)

    # Inner content area (after 10px padding)
    lpx, lpy = lx + 10, ly + 10

    # --- BUTTON: hover_test_button ---
    def make_button(name, parent_idx, bx, by, bg, hover_bg, click_bg):
        """Create a button component (5 containers)."""
        i_btn = c(name, position=(bx, by), size=(380, 40),
                  background_color=bg, hover_background_color=hover_bg, click_background_color=click_bg,
                  border_radius=8, parent=parent_idx)
        c(f"{name}_icon", position=(bx + 8, by + 12), size=(15, 15),
          background_color=TRANSPARENT, parent=i_btn, passive=1)
        i_tbox = c(f"{name}_text_box", position=(bx + 38, by + 0), size=(280, 40),
                   background_color=TRANSPARENT, parent=i_btn, passive=1)
        c(f"{name}_text", position=(bx + 38, by + 0), size=(280, 40),
          background_color=TRANSPARENT, parent=i_tbox, passive=1)
        c(f"{name}_radial", position=(bx + 357, by + 12), size=(15, 15),
          background_color=RADIAL_COLOR, border_color=RADIAL_BORDER,
          border_radius=9999, border_width=1, parent=i_btn, passive=1)
        return i_btn

    # Button 1: hover_test (index 10-14)
    make_button("hover_test_button", 9, lpx, lpy,
                BG_25, BG_35, BG_35)

    # Button 2: click_test (index 15-19)
    make_button("click_test_button", 9, lpx, lpy + 50,
                BG_25, BG_35, BG_4A)

    # Button 3: toggle_test (index 20-24)
    make_button("toggle_test_button", 9, lpx, lpy + 100,
                BG_25, BG_35, BG_4A)

    # --- TEXT INPUT (index 25-33) ---
    tix, tiy = lpx, lpy + 150
    i_ti = c("text_input_test", position=(tix, tiy), size=(380, 210),
             background_color=TRANSPARENT, border_radius=10, parent=9)

    # label_box (index 26)
    i_tilb = c("label_box", position=(tix, tiy), size=(380, 40),
               background_color=BG_35, parent=25)
    # ti_icon (index 27)
    c("ti_icon", position=(tix + 10, tiy + 10), size=(20, 20),
      background_color=TRANSPARENT, parent=26, passive=1)
    # ti_label (index 28)
    c("ti_label", position=(tix + 40, tiy + 0), size=(330, 40),
      background_color=TRANSPARENT, parent=26)

    # input_box (index 29)
    c("input_box", position=(tix, tiy + 40), size=(380, 150),
      background_color=BG_25, border_radius=10, parent=25)

    # ti_footer (index 30)
    i_tif = c("ti_footer", position=(tix, tiy + 190), size=(380, 40),
              background_color=BG_35, parent=25)
    # ti_footer_text (index 31)
    c("ti_footer_text", position=(tix + 10, tiy + 190), size=(340, 40),
      background_color=TRANSPARENT, parent=30, passive=1)
    # ti_footer_action (index 32)
    i_tifa = c("ti_footer_action", position=(tix + 350, tiy + 200), size=(20, 20),
               background_color=TRANSPARENT, parent=30)
    # ti_footer_icon (index 33)
    c("ti_footer_icon", position=(tix + 350, tiy + 200), size=(20, 20),
      background_color=TRANSPARENT, parent=32, passive=1)

    # --- BOTTOM TEXT (index 34-35) ---
    btx, bty = lpx, lpy + 370
    i_btb = c("bottom_text_box", position=(btx, bty), size=(380, 30),
              background_color=TRANSPARENT, parent=9)
    c("bottom_text", position=(btx + 5, bty + 5), size=(370, 20),
      background_color=TRANSPARENT, parent=34)

    # --- RIGHT SIDE (index 36) ---
    rx, ry = ccx + 400, ccy
    i_right = c("right_side_interaction", position=(rx, ry), size=(400, 410),
                background_color=TRANSPARENT, parent=8)

    # --- LABEL COMPONENT ---
    def make_label(name, parent_idx, lbx, lby, bg_color, border_rad=0):
        """Create a label component (16 containers)."""
        i_label = c(name, position=(lbx, lby), size=(380, 180),
                    background_color=bg_color, border_radius=border_rad, parent=parent_idx)
        # icon_box (child 1)
        i_ib = c(f"{name}_icon_box", position=(lbx + 10, lby + 10), size=(40, 160),
                 background_color=TRANSPARENT, parent=i_label)
        c(f"{name}_icon", position=(lbx + 10, lby + 10), size=(40, 160),
          background_color=TRANSPARENT, parent=i_ib)

        # text_box (child 2)
        i_tb = c(f"{name}_text_box", position=(lbx + 60, lby + 10), size=(310, 160),
                 background_color=TRANSPARENT, parent=i_label)
        c(f"{name}_text", position=(lbx + 60, lby + 10), size=(310, 25),
          background_color=TRANSPARENT, parent=i_tb)
        c(f"{name}_underline", position=(lbx + 60, lby + 39), size=(248, 1),
          background_color=UNDERLINE_COLOR, parent=i_tb)

        # description_box
        i_db = c(f"{name}_desc_box", position=(lbx + 60, lby + 50), size=(310, 120),
                 background_color=TRANSPARENT, parent=i_tb)
        # desc icon box
        i_dib = c(f"{name}_desc_icon_box", position=(lbx + 60, lby + 50), size=(40, 120),
                  background_color=TRANSPARENT, parent=i_db)
        c(f"{name}_desc_icon", position=(lbx + 60, lby + 50), size=(40, 120),
          background_color=TRANSPARENT, parent=i_dib)
        # desp box
        i_desp = c(f"{name}_desp_box", position=(lbx + 110, lby + 50), size=(260, 120),
                   background_color=TRANSPARENT, parent=i_db)
        c(f"{name}_description", position=(lbx + 110, lby + 50), size=(260, 96),
          background_color=TRANSPARENT, parent=i_desp)
        # tags box
        i_tags = c(f"{name}_tags_box", position=(lbx + 110, lby + 146), size=(260, 24),
                   background_color=TRANSPARENT, parent=i_desp)
        i_tb1 = c(f"{name}_tags_box1", position=(lbx + 110, lby + 146), size=(70, 22),
                  background_color=TAG_BG, border_radius=300, parent=i_tags)
        c(f"{name}_tag1", position=(lbx + 119, lby + 148), size=(52, 18),
          background_color=TRANSPARENT, parent=i_tb1)
        i_tb2 = c(f"{name}_tags_box2", position=(lbx + 186, lby + 146), size=(70, 22),
                  background_color=TAG_BG, border_radius=300, parent=i_tags)
        c(f"{name}_tag2", position=(lbx + 195, lby + 148), size=(52, 18),
          background_color=TRANSPARENT, parent=i_tb2)
        return i_label

    # Label 1: default_label (index 37-52)
    rlpx, rlpy = rx + 10, ry + 10
    make_label("default_label", 36, rlpx, rlpy, (0.0, 0.0, 0.0, 1.0))

    # Label 2: simple_label (index 53-68)
    make_label("simple_label", 36, rlpx, rlpy + 190, BG_25, border_rad=8)

    assert len(containers) == 69, f"Expected 69 containers, got {len(containers)}"
    return containers


def containers_to_buffer(containers: list) -> np.ndarray:
    """Pack containers into a flat float32 buffer (identical to render.py)."""
    buf = np.zeros(len(containers) * CONTAINER_STRIDE, dtype=np.float32)
    for i, c in enumerate(containers):
        off = i * CONTAINER_STRIDE
        buf[off + 0] = float(c.display)
        buf[off + 1] = c.position[0]
        buf[off + 2] = c.position[1]
        buf[off + 3] = c.size[0]
        buf[off + 4] = c.size[1]
        buf[off + 5:off + 9] = c.background_color
        buf[off + 9:off + 13] = c.background_color_2
        buf[off + 13] = c.background_gradient_rot
        buf[off + 14:off + 18] = c.hover_background_color
        buf[off + 18:off + 22] = c.hover_background_color_2
        buf[off + 22] = c.hover_background_gradient_rot
        buf[off + 23:off + 27] = c.click_background_color
        buf[off + 27:off + 31] = c.click_background_color_2
        buf[off + 31] = c.click_background_gradient_rot
        buf[off + 32:off + 36] = c.border_color
        buf[off + 36:off + 40] = c.border_color_2
        buf[off + 40] = c.border_gradient_rot
        buf[off + 41] = c.border_radius
        buf[off + 42] = c.border_width
        buf[off + 43] = float(c.parent)
        buf[off + 44] = float(c.overflow)
        buf[off + 45:off + 48] = c.box_shadow_offset
        buf[off + 48] = c.box_shadow_blur
        buf[off + 49:off + 53] = c.box_shadow_color
        buf[off + 53] = float(c.passive)
    return buf


def containers_to_dicts(containers: list) -> list:
    """Convert to list-of-dicts format matching render.py _container_data."""
    result = []
    for i, c in enumerate(containers):
        result.append({
            'display': bool(c.display),
            'position': list(c.position),
            'size': list(c.size),
            'background_color': list(c.background_color),
            'background_color_2': list(c.background_color_2),
            'background_gradient_rot': c.background_gradient_rot,
            'hover_background_color': list(c.hover_background_color),
            'hover_background_color_2': list(c.hover_background_color_2),
            'hover_background_gradient_rot': c.hover_background_gradient_rot,
            'click_background_color': list(c.click_background_color),
            'click_background_color_2': list(c.click_background_color_2),
            'click_background_gradient_rot': c.click_background_gradient_rot,
            'border_color': list(c.border_color),
            'border_color_2': list(c.border_color_2),
            'border_gradient_rot': c.border_gradient_rot,
            'border_radius': c.border_radius,
            'border_width': c.border_width,
            'parent': c.parent,
            'overflow': int(c.overflow),
            'box_shadow_offset': list(c.box_shadow_offset),
            'box_shadow_blur': c.box_shadow_blur,
            'box_shadow_color': list(c.box_shadow_color),
            'passive': bool(c.passive),
            '_hovered': False,
            '_prev_hovered': False,
            '_clicked': False,
            '_prev_clicked': False,
        })
    return result


# =============================================================================
# Section 3: Pure Computation Functions
# =============================================================================

# -- 3A: Container loading --

def fn_load_container_full(buffer: np.ndarray, index: int) -> Container:
    """Load all 54 floats for container at `index`. Mirrors GLSL getContainer().
    COST: reads 216 bytes."""
    off = index * CONTAINER_STRIDE
    d = buffer[off:off + CONTAINER_STRIDE]
    return Container(
        display=int(d[0]),
        position=(d[1], d[2]),
        size=(d[3], d[4]),
        background_color=(d[5], d[6], d[7], d[8]),
        background_color_2=(d[9], d[10], d[11], d[12]),
        background_gradient_rot=d[13],
        hover_background_color=(d[14], d[15], d[16], d[17]),
        hover_background_color_2=(d[18], d[19], d[20], d[21]),
        hover_background_gradient_rot=d[22],
        click_background_color=(d[23], d[24], d[25], d[26]),
        click_background_color_2=(d[27], d[28], d[29], d[30]),
        click_background_gradient_rot=d[31],
        border_color=(d[32], d[33], d[34], d[35]),
        border_color_2=(d[36], d[37], d[38], d[39]),
        border_gradient_rot=d[40],
        border_radius=d[41],
        border_width=d[42],
        parent=int(d[43]),
        overflow=int(d[44]),
        box_shadow_offset=(d[45], d[46], d[47]),
        box_shadow_blur=d[48],
        box_shadow_color=(d[49], d[50], d[51], d[52]),
        passive=int(d[53]),
    )


def fn_load_container_minimal(buffer: np.ndarray, index: int) -> tuple:
    """Load only essential fields: display, position, size, parent, overflow, border_radius, passive.
    COST: reads ~40 bytes vs 216."""
    off = index * CONTAINER_STRIDE
    return (
        int(buffer[off + 0]),         # display
        (buffer[off + 1], buffer[off + 2]),  # position
        (buffer[off + 3], buffer[off + 4]),  # size
        int(buffer[off + 43]),        # parent
        int(buffer[off + 44]),        # overflow
        buffer[off + 41],             # border_radius
        int(buffer[off + 53]),        # passive
    )


# -- 3B: Geometry & SDF --

def fn_sdf_rounded_rect(pixel: tuple, position: tuple, size: tuple, border_radius: float) -> float:
    """Signed distance from pixel to rounded rectangle. Mirrors GLSL containerSDFDirect().
    Negative = inside, 0 = edge, positive = outside."""
    lx = pixel[0] - position[0]
    ly = pixel[1] - position[1]
    radius = min(border_radius, min(size[0], size[1]) * 0.5)
    dx = abs(lx - size[0] * 0.5) - size[0] * 0.5 + radius
    dy = abs(ly - size[1] * 0.5) - size[1] * 0.5 + radius
    outside = math.sqrt(max(dx, 0.0) ** 2 + max(dy, 0.0) ** 2)
    inside = min(max(dx, dy), 0.0)
    return outside + inside - radius


def fn_aabb_test(pixel: tuple, container_pos: tuple, container_size: tuple, extent: float) -> bool:
    """AABB early-out test. Returns True if pixel is within extent of container bounds."""
    lx = pixel[0] - container_pos[0]
    ly = pixel[1] - container_pos[1]
    hx = container_size[0] * 0.5
    hy = container_size[1] * 0.5
    return (abs(lx - hx) <= hx + extent and abs(ly - hy) <= hy + extent)


def fn_sdf_anti_alias(dist: float) -> float:
    """SDF to alpha. Mirrors GLSL sdfAntiAlias()."""
    return max(0.0, min(1.0, 0.5 - dist * 0.5))


# -- 3C: Visibility & Parent Chain --

def fn_is_any_parent_hidden(buffer: np.ndarray, container_index: int, container_count: int,
                            _counters: Optional[dict] = None) -> bool:
    """CURRENT: Walk parent chain, load full container per ancestor, check display.
    Returns True if any ancestor is hidden."""
    current = container_index
    for _ in range(10):
        if current < 0 or current >= container_count:
            break
        if _counters is not None:
            _counters['parent_loads'] += 1
        c = fn_load_container_full(buffer, current)
        if c.display == 0:
            return True
        if c.parent < 0:
            break
        current = c.parent
    return False


def fn_is_pixel_in_all_parent_bounds(pixel: tuple, buffer: np.ndarray,
                                     container_index: int, container_count: int,
                                     _counters: Optional[dict] = None) -> bool:
    """CURRENT: Walk parent chain, load full container, compute SDF for each
    parent with overflow=0. Returns False if pixel is clipped by any ancestor."""
    if container_index < 0 or container_index >= container_count:
        return True

    if _counters is not None:
        _counters['parent_loads'] += 1
    current = fn_load_container_full(buffer, container_index)
    parent_idx = current.parent

    while 0 <= parent_idx < container_count:
        if _counters is not None:
            _counters['parent_loads'] += 1
            _counters['sdf_evals'] += 1
        parent = fn_load_container_full(buffer, parent_idx)
        if parent.overflow == 0:
            sdf = fn_sdf_rounded_rect(pixel, parent.position, parent.size, parent.border_radius)
            if sdf > 0.0:
                return False
        parent_idx = parent.parent

    return True


def fn_precompute_visibility(containers: list) -> list:
    """PROPOSED: Compute visibility once per frame, not per pixel.
    Returns bool array: visible[i] = True if container i and all ancestors have display=1."""
    n = len(containers)
    visible = [False] * n
    for i in range(n):
        c = containers[i]
        if c.display == 0:
            visible[i] = False
            continue
        parent_idx = c.parent
        is_vis = True
        while 0 <= parent_idx < n:
            if containers[parent_idx].display == 0:
                is_vis = False
                break
            parent_idx = containers[parent_idx].parent
        visible[i] = is_vis
    return visible


def fn_precompute_clip_rects(containers: list) -> list:
    """PROPOSED: Compute accumulated clip rectangle per container, once per frame.
    Returns list of (x, y, w, h) tuples. For containers with no clipping ancestors,
    returns a very large rect."""
    n = len(containers)
    INF = 1e6
    clips = [(-INF, -INF, 2 * INF, 2 * INF)] * n

    for i in range(n):
        c = containers[i]
        # Start with own bounds (used for children's clipping)
        cx, cy = c.position
        cw, ch = c.size

        # Walk parent chain, intersect clip rects
        clip_x, clip_y = -INF, -INF
        clip_r, clip_b = INF, INF

        parent_idx = c.parent
        while 0 <= parent_idx < n:
            p = containers[parent_idx]
            if p.overflow == 0:
                px, py = p.position
                pw, ph = p.size
                # Intersect with parent bounds
                clip_x = max(clip_x, px)
                clip_y = max(clip_y, py)
                clip_r = min(clip_r, px + pw)
                clip_b = min(clip_b, py + ph)
            parent_idx = p.parent

        clips[i] = (clip_x, clip_y, clip_r - clip_x, clip_b - clip_y)

    return clips


def fn_pixel_in_clip_rect(pixel: tuple, clip_rect: tuple) -> bool:
    """PROPOSED: O(1) clip test replacing isPixelInAllParentBounds()."""
    return (clip_rect[0] <= pixel[0] <= clip_rect[0] + clip_rect[2] and
            clip_rect[1] <= pixel[1] <= clip_rect[1] + clip_rect[3])


# -- 3D: Hover/Click Detection --

def fn_determine_hover_click(mouse_pos: tuple, buffer: np.ndarray,
                             container_count: int, visibility: list,
                             _counters: Optional[dict] = None) -> tuple:
    """CURRENT shader hover/click loop. Back-to-front, find topmost hit."""
    hover_idx = -1
    click_idx = -1
    is_clicked = True  # simulated

    for i in range(container_count - 1, -1, -1):
        if _counters is not None:
            _counters['container_loads'] += 1
        c = fn_load_container_full(buffer, i)
        if c.display == 0:
            continue
        if not visibility[i]:
            continue
        if c.passive != 0:
            continue

        # AABB early-out vs mouse
        hx = c.size[0] * 0.5
        hy = c.size[1] * 0.5
        lmx = mouse_pos[0] - c.position[0]
        lmy = mouse_pos[1] - c.position[1]
        if abs(lmx - hx) > hx + c.border_radius or abs(lmy - hy) > hy + c.border_radius:
            if _counters is not None:
                _counters['aabb_tests'] += 1
            continue

        if _counters is not None:
            _counters['aabb_tests'] += 1
            _counters['aabb_passes'] += 1
            _counters['sdf_evals'] += 1

        sdf = fn_sdf_rounded_rect(mouse_pos, c.position, c.size, c.border_radius)
        if sdf <= 0.0 and fn_is_pixel_in_all_parent_bounds(mouse_pos, buffer, i, container_count, _counters):
            if hover_idx < 0:
                hover_idx = i
            if is_clicked and click_idx < 0:
                click_idx = i
            if hover_idx >= 0 and (not is_clicked or click_idx >= 0):
                break

    return hover_idx, click_idx


# -- 3E: Rendering --

def fn_gradient_color(color1: tuple, color2: tuple, rotation_deg: float,
                      pixel: tuple, origin: tuple, size: tuple) -> tuple:
    """Linear gradient interpolation. Mirrors GLSL getGradientColor()."""
    rot_rad = math.radians(rotation_deg)
    dx = math.cos(rot_rad)
    dy = math.sin(rot_rad)
    lx = pixel[0] - origin[0] - size[0] * 0.5
    ly = pixel[1] - origin[1] - size[1] * 0.5
    proj = lx * dx + ly * dy
    max_proj = abs(size[0] * 0.5 * abs(dx)) + abs(size[1] * 0.5 * abs(dy))
    t = max(0.0, min(1.0, (proj + max_proj) / (2.0 * max_proj + 1e-10)))
    return (
        color1[0] + (color2[0] - color1[0]) * t,
        color1[1] + (color2[1] - color1[1]) * t,
        color1[2] + (color2[2] - color1[2]) * t,
        color1[3] + (color2[3] - color1[3]) * t,
    )


def fn_render_shadow(pixel: tuple, container: Container,
                     _counters: Optional[dict] = None) -> tuple:
    """Compute shadow contribution. Mirrors GLSL renderShadow()."""
    if container.box_shadow_color[3] <= 0.0 or container.box_shadow_blur <= 0.0:
        return (0.0, 0.0, 0.0, 0.0)

    so = container.box_shadow_offset
    shadow_pos = (container.position[0] + so[0], container.position[1] + so[1])
    if _counters is not None:
        _counters['sdf_evals'] += 2
    shadow_dist = fn_sdf_rounded_rect(pixel, shadow_pos, container.size, container.border_radius)
    if shadow_dist > container.box_shadow_blur + 3.0:
        return (0.0, 0.0, 0.0, 0.0)
    container_dist = fn_sdf_rounded_rect(pixel, container.position, container.size, container.border_radius)
    if container_dist <= container.border_width:
        return (0.0, 0.0, 0.0, 0.0)
    softness = max(container.box_shadow_blur * 0.5, 0.5)
    alpha = 1.0 - max(0.0, min(1.0, (shadow_dist + softness) / (container.box_shadow_blur + softness + 1e-10)))
    alpha = max(0.0, min(1.0, alpha))
    sc = container.box_shadow_color
    return (sc[0], sc[1], sc[2], sc[3] * alpha)


def fn_render_container(pixel: tuple, container: Container,
                        is_hovered: bool, is_clicked: bool,
                        _counters: Optional[dict] = None) -> tuple:
    """Render container body+border at pixel. Mirrors GLSL renderContainer()."""
    if _counters is not None:
        _counters['sdf_evals'] += 1
    dist = fn_sdf_rounded_rect(pixel, container.position, container.size, container.border_radius)
    outer = container.border_width + 1.5
    if dist > outer:
        return (0.0, 0.0, 0.0, 0.0)

    if container.passive != 0:
        is_hovered = False
        is_clicked = False

    base = container.background_color
    if container.background_color_2[3] > 0.0:
        if _counters is not None:
            _counters['gradient_evals'] += 1
        base = fn_gradient_color(container.background_color, container.background_color_2,
                                 container.background_gradient_rot,
                                 pixel, container.position, container.size)

    if is_clicked and container.click_background_color[3] >= 0.0:
        base = container.click_background_color
        if container.click_background_color_2[3] > 0.0:
            if _counters is not None:
                _counters['gradient_evals'] += 1
            base = fn_gradient_color(container.click_background_color, container.click_background_color_2,
                                     container.click_background_gradient_rot,
                                     pixel, container.position, container.size)
    elif is_hovered and container.hover_background_color[3] >= 0.0:
        base = container.hover_background_color
        if container.hover_background_color_2[3] > 0.0:
            if _counters is not None:
                _counters['gradient_evals'] += 1
            base = fn_gradient_color(container.hover_background_color, container.hover_background_color_2,
                                     container.hover_background_gradient_rot,
                                     pixel, container.position, container.size)

    if dist <= 0.0:
        alpha = fn_sdf_anti_alias(dist)
        return (base[0], base[1], base[2], base[3] * alpha)

    if dist <= container.border_width and container.border_color[3] > 0.0 and container.border_width > 0.0:
        bc = container.border_color
        bd = abs(dist - container.border_width * 0.5) - container.border_width * 0.5
        ba = fn_sdf_anti_alias(bd)
        return (bc[0], bc[1], bc[2], bc[3] * ba)

    return (0.0, 0.0, 0.0, 0.0)


def fn_composite_alpha_over(dst: tuple, src: tuple) -> tuple:
    """Alpha-over compositing: dst over src."""
    sa = src[3]
    if sa <= 0.0:
        return dst
    return (
        dst[0] * (1.0 - sa) + src[0] * sa,
        dst[1] * (1.0 - sa) + src[1] * sa,
        dst[2] * (1.0 - sa) + src[2] * sa,
        dst[3] + sa * (1.0 - dst[3]),
    )


# -- 3F: CPU-side buffer packing --

def fn_build_container_struct(container_dict: dict) -> list:
    """Pack one container dict into 54-float list. Identical to render.py."""
    background_color = container_dict.get('background_color', [0, 0, 0, 1])
    background_color_2 = container_dict.get('background_color_2', [0, 0, 0, 0])
    hc = container_dict.get('hover_background_color', [0, 0, 0, -1])
    hc1 = container_dict.get('hover_background_color_2', [0, 0, 0, 0])
    cc = container_dict.get('click_background_color', [0, 0, 0, -1])
    cc1 = container_dict.get('click_background_color_2', [0, 0, 0, 0])
    bc = container_dict.get('border_color', [0, 0, 0, 0])
    bc1 = container_dict.get('border_color_2', [0, 0, 0, 0])
    pos = container_dict.get('position', [0, 0])
    sz = container_dict.get('size', [100, 100])
    so = container_dict.get('box_shadow_offset', [0, 0, 0])
    sc = container_dict.get('box_shadow_color', [0, 0, 0, 0])

    return [
        int(container_dict.get('display', False)),
        pos[0], pos[1], sz[0], sz[1],
        background_color[0], background_color[1], background_color[2], background_color[3],
        background_color_2[0], background_color_2[1], background_color_2[2], background_color_2[3],
        container_dict.get('background_gradient_rot', 0.0),
        hc[0], hc[1], hc[2], hc[3],
        hc1[0], hc1[1], hc1[2], hc1[3],
        container_dict.get('hover_background_gradient_rot', 0.0),
        cc[0], cc[1], cc[2], cc[3],
        cc1[0], cc1[1], cc1[2], cc1[3],
        container_dict.get('click_background_gradient_rot', 0.0),
        bc[0], bc[1], bc[2], bc[3],
        bc1[0], bc1[1], bc1[2], bc1[3],
        container_dict.get('border_gradient_rot', 0.0),
        container_dict.get('border_radius', 0.0),
        container_dict.get('border_width', 0.0),
        container_dict.get('parent', -1),
        int(container_dict.get('overflow', False)),
        so[0], so[1], so[2],
        container_dict.get('box_shadow_blur', 0.0),
        sc[0], sc[1], sc[2], sc[3],
        int(container_dict.get('passive', False)),
    ]


def fn_pack_all_containers(container_dicts: list) -> np.ndarray:
    """CURRENT: Full rebuild of all containers into numpy buffer."""
    arr = []
    for cd in container_dicts:
        arr.extend(fn_build_container_struct(cd))
    return np.array(arr, dtype=np.float32)


def fn_pack_single_container(container_dict: dict, index: int, buffer: np.ndarray) -> None:
    """PROPOSED: Write 54 floats at offset into pre-allocated buffer."""
    off = index * CONTAINER_STRIDE
    struct = fn_build_container_struct(container_dict)
    buffer[off:off + CONTAINER_STRIDE] = struct


def fn_detect_changed_containers(containers: list, prev_states: list) -> set:
    """Compare hover/click state between frames. Returns changed indices."""
    changed = set()
    for i in range(min(len(containers), len(prev_states))):
        if (containers[i].get('_hovered') != prev_states[i].get('_prev_hovered') or
                containers[i].get('_clicked') != prev_states[i].get('_prev_clicked')):
            changed.add(i)
    return changed


# -- 3G: Readback pipeline --

def fn_simulate_pbo_read(width: int, height: int) -> np.ndarray:
    """Simulate blocking PBO read: creates uint8 buffer of realistic size."""
    return np.random.randint(0, 256, size=width * height * 4, dtype=np.uint8)


_U8_TO_F32_SCALE = np.float32(1.0 / 255.0)

def fn_uint8_to_float32(data: np.ndarray, out: np.ndarray) -> None:
    """Convert uint8 to float32 in-place. Identical to render.py."""
    np.multiply(data, _U8_TO_F32_SCALE, out=out)


def fn_update_mouse_buffer(pre_alloc: np.ndarray, pos: tuple,
                           current_time: float, scroll: float, click: float) -> None:
    """Write mouse data into pre-allocated buffer. PROPOSED (no allocation)."""
    pre_alloc[0] = pos[0]
    pre_alloc[1] = pos[1]
    pre_alloc[2] = current_time
    pre_alloc[3] = scroll
    pre_alloc[4] = click
    pre_alloc[5] = 0.0


def fn_update_mouse_buffer_current(pos: tuple, current_time: float,
                                   scroll: float, click: float) -> np.ndarray:
    """CURRENT: Creates new numpy array each call."""
    return np.array([pos[0], pos[1], current_time, scroll, click, 0.0], dtype=np.float32)


# =============================================================================
# Section 4: Frame Simulator (Current Architecture)
# =============================================================================

def simulate_frame_baseline(containers: list, buffer: np.ndarray,
                            mouse_pos: tuple, viewport_size: tuple,
                            sample_rate: int = 8) -> FrameReport:
    """Simulate one full render frame using the CURRENT architecture.
    sample_rate: render every Nth pixel (1=all, 8=every 8th)."""
    report = FrameReport()
    counters = {
        'container_loads': 0, 'parent_loads': 0,
        'sdf_evals': 0, 'gradient_evals': 0, 'shadow_evals': 0,
        'aabb_tests': 0, 'aabb_passes': 0,
    }
    vw, vh = viewport_size
    n = len(containers)

    # STEP 0: Mouse buffer update
    t0 = time.perf_counter_ns()
    mouse_buf = fn_update_mouse_buffer_current(mouse_pos, 1.0, 0.0, 0.0)
    report.mouse_buffer_ns = time.perf_counter_ns() - t0

    # STEP 1: Change detection (simulated: mouse always changed)
    t0 = time.perf_counter_ns()
    report.containers_changed = 0  # mouse moved but no container state changed
    report.change_detect_ns = time.perf_counter_ns() - t0

    # STEP 2: Container buffer packing (CURRENT: full rebuild)
    t0 = time.perf_counter_ns()
    container_dicts = containers_to_dicts(containers)
    _packed = fn_pack_all_containers(container_dicts)
    report.container_pack_ns = time.perf_counter_ns() - t0

    # STEP 3: Visibility precomputation (not in current architecture)
    report.visibility_precompute_ns = 0

    # STEP 4a: Shader hover/click loop
    # Pre-compute visibility the old way for the simulation
    visibility = fn_precompute_visibility(containers)

    t0 = time.perf_counter_ns()
    hover_idx, click_idx = fn_determine_hover_click(
        mouse_pos, buffer, n, visibility, counters)
    report.shader_hover_ns = time.perf_counter_ns() - t0

    # STEP 4b: Shader rendering loop (sampled pixels)
    t0 = time.perf_counter_ns()
    pixels_done = 0

    for py_i in range(0, vh, sample_rate):
        for px_i in range(0, vw, sample_rate):
            pixel = (float(px_i) + 0.5, float(py_i) + 0.5)
            final = (0.0, 0.0, 0.0, 0.0)

            for i in range(n):
                counters['container_loads'] += 1
                c = fn_load_container_full(buffer, i)
                if c.display == 0:
                    continue

                # isAnyParentHidden (current: walks parent chain per pixel)
                if fn_is_any_parent_hidden(buffer, i, n, counters):
                    continue

                # AABB early-out
                extent = max(c.border_width, c.box_shadow_blur) + 5.0
                counters['aabb_tests'] += 1
                if not fn_aabb_test(pixel, c.position, c.size, extent):
                    continue
                counters['aabb_passes'] += 1

                # isPixelInAllParentBounds
                if not fn_is_pixel_in_all_parent_bounds(pixel, buffer, i, n, counters):
                    continue

                # Shadow
                shadow = fn_render_shadow(pixel, c, counters)
                if shadow[3] > 0.0:
                    counters['shadow_evals'] += 1
                    final = fn_composite_alpha_over(final, shadow)

                # Container body
                hovered = (hover_idx == i)
                clicked = (click_idx == i)
                background_color = fn_render_container(pixel, c, hovered, clicked, counters)
                if background_color[3] > 0.0:
                    final = fn_composite_alpha_over(final, background_color)

            pixels_done += 1

    report.shader_render_ns = time.perf_counter_ns() - t0
    report.pixels_sampled = pixels_done

    # Extrapolate counters to full resolution
    scale = (vw * vh) / max(pixels_done, 1)
    report.total_container_loads = int(counters['container_loads'] * scale)
    report.total_parent_chain_loads = int(counters['parent_loads'] * scale)
    report.total_sdf_evals = int(counters['sdf_evals'] * scale)
    report.total_gradient_evals = int(counters['gradient_evals'] * scale)
    report.total_shadow_evals = int(counters['shadow_evals'] * scale)
    report.aabb_tests = int(counters['aabb_tests'] * scale)
    report.aabb_passes = int(counters['aabb_passes'] * scale)
    report.buffer_reads_bytes = report.total_container_loads * 216 + report.total_parent_chain_loads * 216

    # STEP 5: Readback pipeline simulation
    t0 = time.perf_counter_ns()
    pbo_data = fn_simulate_pbo_read(vw, vh)
    report.readback_pbo_ns = time.perf_counter_ns() - t0
    report.readback_bytes = vw * vh * 4

    t0 = time.perf_counter_ns()
    float_buf = np.empty(vw * vh * 4, dtype=np.float32)
    fn_uint8_to_float32(pbo_data, float_buf)
    report.readback_numpy_ns = time.perf_counter_ns() - t0

    # Simulate texture upload (memcpy equivalent)
    t0 = time.perf_counter_ns()
    _ = float_buf.tobytes()  # simulate Buffer creation
    report.readback_upload_ns = time.perf_counter_ns() - t0

    return report


# =============================================================================
# Section 5: Architecture Variant Simulators
# =============================================================================

def simulate_frame_precomputed_visibility(containers: list, buffer: np.ndarray,
                                          mouse_pos: tuple, viewport_size: tuple,
                                          sample_rate: int = 8) -> FrameReport:
    """VARIANT: Precomputed visibility + clip rects (Architecture Changes 2+3).
    - Visibility and clip rects computed ONCE per frame on CPU
    - Hover/click NOT in shader (passed as 2 ints from CPU hit detector)
    - Shader only does rendering loop with O(1) clip test per container
    """
    report = FrameReport()
    counters = {
        'container_loads': 0, 'parent_loads': 0,
        'sdf_evals': 0, 'gradient_evals': 0, 'shadow_evals': 0,
        'aabb_tests': 0, 'aabb_passes': 0,
    }
    vw, vh = viewport_size
    n = len(containers)

    # STEP 0: Mouse buffer (proposed: pre-allocated)
    mouse_buf = np.zeros(6, dtype=np.float32)
    t0 = time.perf_counter_ns()
    fn_update_mouse_buffer(mouse_buf, mouse_pos, 1.0, 0.0, 0.0)
    report.mouse_buffer_ns = time.perf_counter_ns() - t0

    # STEP 1: Change detection
    t0 = time.perf_counter_ns()
    report.containers_changed = 0
    report.change_detect_ns = time.perf_counter_ns() - t0

    # STEP 2: Container buffer (proposed: partial update — 0 changed so skip)
    t0 = time.perf_counter_ns()
    report.container_pack_ns = time.perf_counter_ns() - t0

    # STEP 3: PROPOSED — visibility + clip precomputation on CPU
    t0 = time.perf_counter_ns()
    visibility = fn_precompute_visibility(containers)
    clip_rects = fn_precompute_clip_rects(containers)
    report.visibility_precompute_ns = time.perf_counter_ns() - t0

    # Hover/click determined on CPU (simulated — not in shader)
    hover_idx = -1
    click_idx = -1
    for i in range(n - 1, -1, -1):
        c = containers[i]
        if c.display == 0 or not visibility[i] or c.passive:
            continue
        sdf = fn_sdf_rounded_rect(mouse_pos, c.position, c.size, c.border_radius)
        if sdf <= 0.0 and fn_pixel_in_clip_rect(mouse_pos, clip_rects[i]):
            hover_idx = i
            click_idx = i
            break
    report.shader_hover_ns = 0  # hover no longer in shader

    # STEP 4: Shader rendering — single loop, no parent chain walks
    t0 = time.perf_counter_ns()
    pixels_done = 0

    for py_i in range(0, vh, sample_rate):
        for px_i in range(0, vw, sample_rate):
            pixel = (float(px_i) + 0.5, float(py_i) + 0.5)
            final = (0.0, 0.0, 0.0, 0.0)

            for i in range(n):
                if not visibility[i]:
                    continue

                counters['container_loads'] += 1
                c = fn_load_container_full(buffer, i)

                # AABB early-out
                extent = max(c.border_width, c.box_shadow_blur) + 5.0
                counters['aabb_tests'] += 1
                if not fn_aabb_test(pixel, c.position, c.size, extent):
                    continue
                counters['aabb_passes'] += 1

                # O(1) clip test instead of parent chain walk
                if not fn_pixel_in_clip_rect(pixel, clip_rects[i]):
                    continue

                # Shadow
                shadow = fn_render_shadow(pixel, c, counters)
                if shadow[3] > 0.0:
                    counters['shadow_evals'] += 1
                    final = fn_composite_alpha_over(final, shadow)

                # Container body
                hovered = (hover_idx == i)
                clicked = (click_idx == i)
                background_color = fn_render_container(pixel, c, hovered, clicked, counters)
                if background_color[3] > 0.0:
                    final = fn_composite_alpha_over(final, background_color)

            pixels_done += 1

    report.shader_render_ns = time.perf_counter_ns() - t0
    report.pixels_sampled = pixels_done

    scale = (vw * vh) / max(pixels_done, 1)
    report.total_container_loads = int(counters['container_loads'] * scale)
    report.total_parent_chain_loads = 0  # eliminated!
    report.total_sdf_evals = int(counters['sdf_evals'] * scale)
    report.total_gradient_evals = int(counters['gradient_evals'] * scale)
    report.total_shadow_evals = int(counters['shadow_evals'] * scale)
    report.aabb_tests = int(counters['aabb_tests'] * scale)
    report.aabb_passes = int(counters['aabb_passes'] * scale)
    report.buffer_reads_bytes = report.total_container_loads * 216

    # STEP 5: Readback (same as baseline — still needed unless Arch Change 1)
    t0 = time.perf_counter_ns()
    pbo_data = fn_simulate_pbo_read(vw, vh)
    report.readback_pbo_ns = time.perf_counter_ns() - t0
    report.readback_bytes = vw * vh * 4

    t0 = time.perf_counter_ns()
    float_buf = np.empty(vw * vh * 4, dtype=np.float32)
    fn_uint8_to_float32(pbo_data, float_buf)
    report.readback_numpy_ns = time.perf_counter_ns() - t0

    t0 = time.perf_counter_ns()
    _ = float_buf.tobytes()
    report.readback_upload_ns = time.perf_counter_ns() - t0

    return report


def simulate_frame_no_readback(containers: list, buffer: np.ndarray,
                               mouse_pos: tuple, viewport_size: tuple,
                               sample_rate: int = 8) -> FrameReport:
    """VARIANT: All optimizations + eliminated GPU→CPU→GPU roundtrip (Arch Change 1).
    Same as precomputed_visibility but with zero readback cost."""
    report = simulate_frame_precomputed_visibility(
        containers, buffer, mouse_pos, viewport_size, sample_rate)
    # Zero out readback costs
    report.readback_pbo_ns = 0
    report.readback_numpy_ns = 0
    report.readback_upload_ns = 0
    report.readback_bytes = 0
    return report


def simulate_frame_dirty_region(containers: list, buffer: np.ndarray,
                                mouse_pos: tuple, viewport_size: tuple,
                                sample_rate: int = 8,
                                changed_indices: set = None) -> FrameReport:
    """VARIANT: Dirty region dispatch (Architecture Change 4).
    Only re-renders pixels within the bounding box of changed containers.
    For a mouse-only change with no state changes, dispatch is ZERO pixels."""
    report = FrameReport()
    counters = {
        'container_loads': 0, 'parent_loads': 0,
        'sdf_evals': 0, 'gradient_evals': 0, 'shadow_evals': 0,
        'aabb_tests': 0, 'aabb_passes': 0,
    }
    vw, vh = viewport_size
    n = len(containers)

    # Mouse buffer (pre-allocated)
    mouse_buf = np.zeros(6, dtype=np.float32)
    t0 = time.perf_counter_ns()
    fn_update_mouse_buffer(mouse_buf, mouse_pos, 1.0, 0.0, 0.0)
    report.mouse_buffer_ns = time.perf_counter_ns() - t0

    # Change detection
    if changed_indices is None:
        changed_indices = set()
    report.containers_changed = len(changed_indices)

    # Precompute
    t0 = time.perf_counter_ns()
    visibility = fn_precompute_visibility(containers)
    clip_rects = fn_precompute_clip_rects(containers)
    report.visibility_precompute_ns = time.perf_counter_ns() - t0

    # Compute dirty region bounding box
    if len(changed_indices) == 0:
        # NO pixels need re-rendering! Just reuse previous texture.
        report.shader_render_ns = 0
        report.pixels_sampled = 0
        report.total_container_loads = 0
        report.buffer_reads_bytes = 0
        return report

    # Union bounding box of changed containers + shadow extent
    min_x, min_y = vw, vh
    max_x, max_y = 0, 0
    for idx in changed_indices:
        c = containers[idx]
        ext = max(c.border_width, c.box_shadow_blur) + 5.0
        min_x = min(min_x, c.position[0] - ext)
        min_y = min(min_y, c.position[1] - ext)
        max_x = max(max_x, c.position[0] + c.size[0] + ext)
        max_y = max(max_y, c.position[1] + c.size[1] + ext)

    min_x = max(0, int(min_x))
    min_y = max(0, int(min_y))
    max_x = min(vw, int(max_x) + 1)
    max_y = min(vh, int(max_y) + 1)

    # Hover/click on CPU
    hover_idx = -1
    for i in range(n - 1, -1, -1):
        c = containers[i]
        if c.display == 0 or not visibility[i] or c.passive:
            continue
        sdf = fn_sdf_rounded_rect(mouse_pos, c.position, c.size, c.border_radius)
        if sdf <= 0.0 and fn_pixel_in_clip_rect(mouse_pos, clip_rects[i]):
            hover_idx = i
            break

    # Render only dirty region
    t0 = time.perf_counter_ns()
    pixels_done = 0
    for py_i in range(min_y, max_y, sample_rate):
        for px_i in range(min_x, max_x, sample_rate):
            pixel = (float(px_i) + 0.5, float(py_i) + 0.5)
            final = (0.0, 0.0, 0.0, 0.0)
            for i in range(n):
                if not visibility[i]:
                    continue
                counters['container_loads'] += 1
                c = fn_load_container_full(buffer, i)
                extent = max(c.border_width, c.box_shadow_blur) + 5.0
                counters['aabb_tests'] += 1
                if not fn_aabb_test(pixel, c.position, c.size, extent):
                    continue
                counters['aabb_passes'] += 1
                if not fn_pixel_in_clip_rect(pixel, clip_rects[i]):
                    continue
                shadow = fn_render_shadow(pixel, c, counters)
                if shadow[3] > 0.0:
                    final = fn_composite_alpha_over(final, shadow)
                background_color = fn_render_container(pixel, c, hover_idx == i, False, counters)
                if background_color[3] > 0.0:
                    final = fn_composite_alpha_over(final, background_color)
            pixels_done += 1

    report.shader_render_ns = time.perf_counter_ns() - t0
    report.pixels_sampled = pixels_done

    if pixels_done > 0:
        dirty_area = (max_x - min_x) * (max_y - min_y)
        scale = dirty_area / max(pixels_done, 1)
    else:
        scale = 0
    report.total_container_loads = int(counters['container_loads'] * scale)
    report.total_sdf_evals = int(counters['sdf_evals'] * scale)
    report.aabb_tests = int(counters['aabb_tests'] * scale)
    report.aabb_passes = int(counters['aabb_passes'] * scale)
    report.buffer_reads_bytes = report.total_container_loads * 216

    return report


# =============================================================================
# Section 6: Micro-Benchmarks
# =============================================================================

def _bench(fn, iterations, *args, **kwargs):
    """Benchmark a function, return average ns per call."""
    # Warmup
    for _ in range(min(100, iterations)):
        fn(*args, **kwargs)
    t0 = time.perf_counter_ns()
    for _ in range(iterations):
        fn(*args, **kwargs)
    elapsed = time.perf_counter_ns() - t0
    return elapsed / iterations


def run_micro_benchmarks(containers: list, buffer: np.ndarray,
                         viewport_size: tuple) -> list:
    """Run isolated benchmarks per function. Returns list of (name, avg_ns, description)."""
    vw, vh = viewport_size
    n = len(containers)
    results = []

    # Pick a representative pixel (center of viewport, inside the bg container)
    pixel = (vw / 2.0, vh / 2.0)
    mouse = (vw / 2.0 + 50, vh / 2.0 + 50)

    # Container in the middle of the tree (a button)
    btn = containers[10] if n > 10 else containers[0]
    btn_pos, btn_size, btn_rad = btn.position, btn.size, btn.border_radius

    results.append(("fn_sdf_rounded_rect",
                    _bench(fn_sdf_rounded_rect, 100_000, pixel, btn_pos, btn_size, btn_rad),
                    "SDF distance to rounded rect"))

    results.append(("fn_aabb_test",
                    _bench(fn_aabb_test, 100_000, pixel, btn_pos, btn_size, 5.0),
                    "AABB early-out test"))

    results.append(("fn_sdf_anti_alias",
                    _bench(fn_sdf_anti_alias, 100_000, -0.5),
                    "SDF to alpha conversion"))

    results.append(("fn_load_container_full",
                    _bench(fn_load_container_full, 100_000, buffer, 10),
                    "Load 54 floats from buffer"))

    results.append(("fn_load_container_minimal",
                    _bench(fn_load_container_minimal, 100_000, buffer, 10),
                    "Load 10 essential floats"))

    results.append(("fn_is_any_parent_hidden",
                    _bench(fn_is_any_parent_hidden, 50_000, buffer, 14, n),
                    "Walk parent chain for visibility"))

    results.append(("fn_is_pixel_in_all_parent_bounds",
                    _bench(fn_is_pixel_in_all_parent_bounds, 50_000, pixel, buffer, 14, n),
                    "Walk parent chain for clipping"))

    results.append(("fn_gradient_color",
                    _bench(fn_gradient_color, 100_000,
                           (0.1, 0.1, 0.2, 1.0), (0.2, 0.2, 0.3, 1.0), 90.0,
                           pixel, btn_pos, btn_size),
                    "Gradient interpolation"))

    results.append(("fn_render_shadow",
                    _bench(fn_render_shadow, 50_000, pixel, btn),
                    "Shadow rendering (no shadow on this container)"))

    results.append(("fn_render_container",
                    _bench(fn_render_container, 50_000, pixel, btn, False, False),
                    "Full container render"))

    results.append(("fn_composite_alpha_over",
                    _bench(fn_composite_alpha_over, 100_000,
                           (0.1, 0.2, 0.3, 0.5), (0.5, 0.4, 0.3, 0.8)),
                    "Alpha-over compositing"))

    # CPU-side functions
    container_dicts = containers_to_dicts(containers)
    results.append(("fn_build_container_struct",
                    _bench(fn_build_container_struct, 100_000, container_dicts[10]),
                    "Pack 1 container to 54 floats"))

    results.append(("fn_pack_all_containers",
                    _bench(fn_pack_all_containers, 5_000, container_dicts),
                    f"Pack all {n} containers"))

    results.append(("fn_update_mouse_buffer_current",
                    _bench(fn_update_mouse_buffer_current, 100_000, mouse, 1.0, 0.0, 0.0),
                    "Mouse buffer (current: allocates)"))

    pre = np.zeros(6, dtype=np.float32)
    results.append(("fn_update_mouse_buffer_proposed",
                    _bench(fn_update_mouse_buffer, 100_000, pre, mouse, 1.0, 0.0, 0.0),
                    "Mouse buffer (proposed: pre-alloc)"))

    # Readback
    pbo_data = np.random.randint(0, 256, size=vw * vh * 4, dtype=np.uint8)
    float_buf = np.empty(vw * vh * 4, dtype=np.float32)
    results.append(("fn_uint8_to_float32",
                    _bench(fn_uint8_to_float32, 500, pbo_data, float_buf),
                    f"uint8→float32 ({vw * vh * 4 / 1e6:.1f}MB)"))

    # Visibility precomputation
    results.append(("fn_precompute_visibility",
                    _bench(fn_precompute_visibility, 10_000, containers),
                    f"Precompute visibility for {n} containers"))

    results.append(("fn_precompute_clip_rects",
                    _bench(fn_precompute_clip_rects, 10_000, containers),
                    f"Precompute clip rects for {n} containers"))

    return results


# =============================================================================
# Section 7: Report Generator
# =============================================================================

def print_report(baseline: FrameReport, variants: dict,
                 micro_results: list, viewport_size: tuple):
    """Print formatted comparison report."""
    vw, vh = viewport_size
    total_pixels = vw * vh

    print("\n" + "=" * 80)
    print("  PUREE RENDER PIPELINE BENCHMARK REPORT")
    print(f"  Viewport: {vw}×{vh} ({total_pixels:,} pixels)")
    print(f"  Containers: 69 | Stride: {CONTAINER_STRIDE} floats ({CONTAINER_STRIDE * 4} bytes)")
    print("=" * 80)

    # --- MICRO BENCHMARKS ---
    print("\n┌─────────────────────────────────────────────────────────────────────────────┐")
    print("│ MICRO-BENCHMARKS (per-function cost)                                        │")
    print("├──────────────────────────────────┬──────────┬────────────────────────────────┤")
    print("│ Function                         │  avg ns  │ Description                    │")
    print("├──────────────────────────────────┼──────────┼────────────────────────────────┤")
    for name, avg_ns, desc in micro_results:
        print(f"│ {name:<32} │ {avg_ns:>7.0f}  │ {desc:<30} │")
    print("└──────────────────────────────────┴──────────┴────────────────────────────────┘")

    # --- FRAME BREAKDOWN ---
    def print_frame(name: str, r: FrameReport, is_baseline: bool = False):
        print(f"\n{'─' * 80}")
        label = f"  {name}"
        if not is_baseline:
            diff = r.total_ms - baseline.total_ms
            pct = (diff / max(baseline.total_ms, 0.001)) * 100
            label += f"  ({pct:+.1f}% vs baseline)"
        print(label)
        print(f"{'─' * 80}")
        steps = [
            ("Mouse buffer update", r.mouse_buffer_ns),
            ("Change detection", r.change_detect_ns),
            ("Container buffer pack", r.container_pack_ns),
            ("Visibility precompute", r.visibility_precompute_ns),
            ("Shader: hover/click", r.shader_hover_ns),
            ("Shader: rendering", r.shader_render_ns),
            ("Readback: PBO read", r.readback_pbo_ns),
            ("Readback: numpy u8→f32", r.readback_numpy_ns),
            ("Readback: texture upload", r.readback_upload_ns),
        ]
        for step_name, ns in steps:
            ms = ns / 1_000_000
            bar_len = int(ms / max(baseline.total_ms, 0.001) * 40)
            bar = "█" * min(bar_len, 40)
            pct_of_frame = (ns / max(r.total_ns, 1)) * 100
            print(f"  {step_name:<26} {ms:>8.2f} ms  ({pct_of_frame:>5.1f}%)  {bar}")

        print(f"  {'─' * 50}")
        print(f"  {'TOTAL':<26} {r.total_ms:>8.2f} ms")
        within = "✓ WITHIN" if r.total_ms <= 16.6 else "✗ EXCEEDS"
        print(f"  16.6ms budget:             {within}")

        print(f"\n  Shader stats (extrapolated to full resolution):")
        print(f"    Container loads:  {r.total_container_loads:>15,}")
        print(f"    Parent chain loads: {r.total_parent_chain_loads:>13,}")
        print(f"    SDF evaluations:  {r.total_sdf_evals:>15,}")
        print(f"    Gradient evaluations: {r.total_gradient_evals:>11,}")
        print(f"    AABB tests:       {r.aabb_tests:>15,}")
        print(f"    AABB pass rate:   {r.aabb_hit_rate:>14.1%}")
        print(f"    Buffer bandwidth: {r.bandwidth_gb:>14.2f} GB")
        print(f"    Readback bytes:   {r.readback_bytes / 1e6:>14.1f} MB")
        print(f"    Pixels sampled:   {r.pixels_sampled:>15,}")

    print_frame("BASELINE (Current Architecture)", baseline, is_baseline=True)
    for name, report in variants.items():
        print_frame(name, report)

    # --- BOTTLENECK RANKING ---
    print(f"\n{'=' * 80}")
    print("  BOTTLENECK RANKING (baseline)")
    print(f"{'=' * 80}")
    steps = [
        ("Shader: rendering", baseline.shader_render_ns),
        ("Shader: hover/click", baseline.shader_hover_ns),
        ("Container buffer pack", baseline.container_pack_ns),
        ("Readback: PBO read", baseline.readback_pbo_ns),
        ("Readback: numpy u8→f32", baseline.readback_numpy_ns),
        ("Readback: texture upload", baseline.readback_upload_ns),
        ("Visibility precompute", baseline.visibility_precompute_ns),
        ("Mouse buffer update", baseline.mouse_buffer_ns),
        ("Change detection", baseline.change_detect_ns),
    ]
    steps.sort(key=lambda x: x[1], reverse=True)
    for rank, (name, ns) in enumerate(steps, 1):
        ms = ns / 1_000_000
        pct = (ns / max(baseline.total_ns, 1)) * 100
        print(f"  #{rank} {name:<28} {ms:>8.2f} ms  ({pct:>5.1f}%)")

    # --- RECOMMENDATIONS ---
    print(f"\n{'=' * 80}")
    print("  RECOMMENDATIONS")
    print(f"{'=' * 80}")

    readback_total = baseline.readback_pbo_ns + baseline.readback_numpy_ns + baseline.readback_upload_ns
    readback_ms = readback_total / 1_000_000
    shader_ms = (baseline.shader_render_ns + baseline.shader_hover_ns) / 1_000_000
    pack_ms = baseline.container_pack_ns / 1_000_000

    recs = []
    if readback_ms > 2.0:
        recs.append((readback_ms, "CRITICAL",
                     "Eliminate GPU→CPU→GPU roundtrip (Architecture Change 1)\n"
                     f"    Current readback cost: {readback_ms:.1f}ms/frame\n"
                     "    Share OpenGL texture between moderngl and Blender"))
    if baseline.total_parent_chain_loads > 0:
        parent_bw = baseline.total_parent_chain_loads * 216 / 1e9
        recs.append((parent_bw * 10, "HIGH",
                     f"Precompute visibility + clip rects on CPU (Architecture Change 2)\n"
                     f"    Eliminates {baseline.total_parent_chain_loads:,} parent chain loads/frame ({parent_bw:.2f} GB)"))
    if baseline.shader_hover_ns > 500_000:
        recs.append((baseline.shader_hover_ns / 1e6, "HIGH",
                     "Move hover/click out of shader (Architecture Change 3)\n"
                     "    Already computed on CPU via Rust HitDetector"))
    if pack_ms > 0.5:
        recs.append((pack_ms, "MEDIUM",
                     f"Partial container buffer updates (skip unchanged containers)\n"
                     f"    Current: rebuilds all 69 containers ({pack_ms:.1f}ms) even when 0 changed"))

    recs.sort(key=lambda x: x[0], reverse=True)
    for i, (_, severity, desc) in enumerate(recs, 1):
        print(f"\n  {i}. [{severity}] {desc}")

    print(f"\n{'=' * 80}")


# =============================================================================
# Section 8: Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Puree render pipeline benchmark")
    parser.add_argument("--sample-rate", type=int, default=16,
                        help="Sample every Nth pixel (default: 16, lower = more accurate but slower)")
    parser.add_argument("--viewport", type=str, default="1574x882",
                        help="Viewport size WxH (default: 1574x882)")
    parser.add_argument("--iterations", type=int, default=1,
                        help="Number of frame simulations to average (default: 1)")
    args = parser.parse_args()

    vw, vh = map(int, args.viewport.split('x'))
    viewport = (vw, vh)
    sr = args.sample_rate

    print(f"Building container dataset ({vw}×{vh})...")
    containers = build_container_dataset(vw, vh)
    buffer = containers_to_buffer(containers)
    print(f"  {len(containers)} containers, {len(buffer)} floats ({len(buffer) * 4} bytes)")

    # Mouse position: hovering over the first button
    mouse_pos = (containers[10].position[0] + 50, containers[10].position[1] + 20)

    print(f"\nRunning micro-benchmarks...")
    micro_results = run_micro_benchmarks(containers, buffer, viewport)

    print(f"\nSimulating frames (sample_rate={sr}, iterations={args.iterations})...")

    # Baseline
    baseline_reports = []
    for i in range(args.iterations):
        r = simulate_frame_baseline(containers, buffer, mouse_pos, viewport, sr)
        baseline_reports.append(r)
        print(f"  Baseline iter {i + 1}: {r.total_ms:.2f}ms")

    # Average baseline
    baseline = baseline_reports[0]
    if args.iterations > 1:
        for attr in ['mouse_buffer_ns', 'change_detect_ns', 'container_pack_ns',
                     'visibility_precompute_ns', 'shader_hover_ns', 'shader_render_ns',
                     'readback_pbo_ns', 'readback_numpy_ns', 'readback_upload_ns']:
            setattr(baseline, attr, int(sum(getattr(r, attr) for r in baseline_reports) / args.iterations))
        for attr in ['total_container_loads', 'total_parent_chain_loads', 'total_sdf_evals',
                     'total_gradient_evals', 'total_shadow_evals', 'aabb_tests', 'aabb_passes',
                     'buffer_reads_bytes', 'readback_bytes', 'pixels_sampled']:
            setattr(baseline, attr, int(sum(getattr(r, attr) for r in baseline_reports) / args.iterations))

    # Variants
    variants = {}

    print("  Running: Precomputed Visibility + CPU Hover...")
    r = simulate_frame_precomputed_visibility(containers, buffer, mouse_pos, viewport, sr)
    variants["Precomputed Vis + CPU Hover (Arch 2+3)"] = r
    print(f"    → {r.total_ms:.2f}ms")

    print("  Running: + No Readback (Arch 1+2+3)...")
    r = simulate_frame_no_readback(containers, buffer, mouse_pos, viewport, sr)
    variants["All Optimizations + No Readback (Arch 1+2+3)"] = r
    print(f"    → {r.total_ms:.2f}ms")

    print("  Running: Dirty Region (no state changes)...")
    r = simulate_frame_dirty_region(containers, buffer, mouse_pos, viewport, sr, changed_indices=set())
    variants["Dirty Region (0 containers changed)"] = r
    print(f"    → {r.total_ms:.2f}ms")

    print("  Running: Dirty Region (1 button hover changed)...")
    r = simulate_frame_dirty_region(containers, buffer, mouse_pos, viewport, sr, changed_indices={10})
    variants["Dirty Region (1 container changed)"] = r
    print(f"    → {r.total_ms:.2f}ms")

    print_report(baseline, variants, micro_results, viewport)


if __name__ == "__main__":
    main()
