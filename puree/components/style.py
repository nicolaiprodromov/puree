# Created by XWZ
# ◕‿◕ Distributed for free at:
# https://github.com/nicolaiprodromov/puree
# ╔═════════════════════════════════╗
# ║  ██   ██  ██      ██  ████████  ║
# ║   ██ ██   ██  ██  ██       ██   ║
# ║    ███    ██  ██  ██     ██     ║
# ║   ██ ██   ██  ██  ██   ██       ║
# ║  ██   ██   ████████   ████████  ║
# ╚═════════════════════════════════╝
from __future__ import annotations
from typing import Optional, List

class Style(): 
    def __init__(self): 
        self.id: str = ""

        self.width  : float = 0.0
        self.height : float = 0.0
        self.min_width  : str = 'auto'
        self.min_height : str = 'auto'
        self.max_width  : str = 'auto'
        self.max_height : str = 'auto'
        
        self.top    : str = 'auto'
        self.right  : str = 'auto'
        self.bottom : str = 'auto'
        self.left   : str = 'auto'

        self.background_color              : List[float] = [0.0, 0.0, 0.0, 0.0]
        self.background_color_2            : List[float] = [0.0, 0.0, 0.0, 0.0]
        self.background_gradient_rot       : float       = 0.0
        
        self.hover_background_color              : List[float] = [0.0, 0.0, 0.0, -1.0]
        self.hover_background_color_2            : List[float] = [0.0, 0.0, 0.0, 0.0]
        self.hover_background_gradient_rot       : float       = 0.0

        self.click_background_color              : List[float] = [0.0, 0.0, 0.0, -1.0]
        self.click_background_color_2            : List[float] = [0.0, 0.0, 0.0, 0.0]
        self.click_background_gradient_rot       : float       = 0.0
        
        self.text_x                  : float       = 0.0
        self.text_y                  : float       = 0.0
        self.font_size               : float       = 12.0
        self.font_family             : str         = ''
        self.font_weight             : str         = 'NORMAL'
        self.font_style              : str         = 'NORMAL'
        self.color                   : List[float] = [1.0, 1.0, 1.0, 1.0]
        self.text_align              : str         = 'LEFT'
        self.text_align_v            : str         = 'CENTER'
        self.text_transform          : str         = 'NONE'
        self.text_decoration         : str         = 'NONE'
        self.line_height             : float       = 1.2
        self.letter_spacing          : float       = 0.0
        self.text_overflow           : str         = 'CLIP'
        self.white_space             : str         = 'NORMAL'
        self.overflow_wrap           : str         = 'NORMAL'
        self.word_break              : str         = 'NORMAL'

        self.img_align_h            : str         = 'LEFT'
        self.img_align_v            : str         = 'TOP'
        self.opacity                : float       = 1.0

        self.border_radius            : float       = 0.0
        self.border_radius_tl         : float       = 0.0
        self.border_radius_tr         : float       = 0.0
        self.border_radius_br         : float       = 0.0
        self.border_radius_bl         : float       = 0.0
        self.border_width             : float       = 0.0
        self.border_width_top         : float       = 0.0
        self.border_width_right       : float       = 0.0
        self.border_width_bottom      : float       = 0.0
        self.border_width_left        : float       = 0.0
        self.border_color             : List[float] = [0.0, 0.0, 0.0, 0.0]
        self.border_color_2           : List[float] = [0.0, 0.0, 0.0, 0.0]
        self.border_gradient_rot      : float       = 0.0
        self.hover_border_color       : List[float] = [0.0, 0.0, 0.0, -1.0]
        self.click_border_color       : List[float] = [0.0, 0.0, 0.0, -1.0]
        self.hover_opacity            : float       = -1.0
        self.click_opacity            : float       = -1.0
        self.hover_color              : List[float] = [0.0, 0.0, 0.0, -1.0]
        self.click_color              : List[float] = [0.0, 0.0, 0.0, -1.0]
        
        self.box_shadow_color : List[float] = [0.0, 0.0, 0.0, 0.0]
        self.box_shadow_offset: List[float] = [0.0, 0.0, 0.0]
        self.box_shadow_blur  : float       = 0.0

        self.text_shadow_color   : List[float] = [0.0, 0.0, 0.0, 0.0]
        self.text_shadow_offset_x: float       = 0.0
        self.text_shadow_offset_y: float       = 0.0
        self.text_shadow_blur    : float       = 0.0

        self.gradient_stops              : str = ''
        self.hover_gradient_stops        : str = ''
        self.click_gradient_stops        : str = ''

        self.display         : str  = 'FLEX'
        self.box_sizing      : str  = 'BORDER_BOX'
        self.overflow        : str  = 'VISIBLE'
        self.overflow_x      : str  = ''
        self.overflow_y      : str  = ''
        self.scrollbar_width : float = 0.0
        self.position        : str  = 'RELATIVE'
        self.pointer_events  : str  = 'AUTO'
        self.visibility      : str  = 'VISIBLE'
        self.z_index         : int  = 0
        
        self.align_items    : str = 'STRETCH'
        self.justify_items  : str = 'START'
        self.align_self     : str = ''
        self.justify_self   : str = ''
        self.align_content  : str = 'START'
        self.justify_content: str = 'START'
        
        self.size         : List[float]     = [0.0, 0.0]
        self.min_size     : List[float]     = [0.0, 0.0]
        self.max_size     : List[float]     = [0.0, 0.0]
        self.aspect_ratio : bool = True
        
        self.flex_wrap     : str   = 'NO_WRAP'
        self.flex_direction: str   = 'ROW'
        self.flex_grow     : float = 0.0
        self.flex_shrink   : float = 1.0
        self.flex_basis    : str   = 'auto'
        
        self.gap            : str  = '0px'
        self.row_gap        : str  = ''
        self.column_gap     : str  = ''
        
        self.grid_auto_flow       : str            = 'ROW'
        self.grid_template_rows   : Optional[List] = None
        self.grid_template_columns: Optional[List] = None
        self.grid_auto_rows       : Optional[List] = None
        self.grid_auto_columns    : Optional[List] = None
        self.grid_row             : str            = 'AUTO'
        self.grid_column          : str            = 'AUTO'

        # CSS transitions (single-transition compat fields, and multi-transition list)
        self.transition_property         : str   = 'none'
        self.transition_duration         : float = 0.0
        self.transition_timing_function  : str   = 'ease'
        self.transition_delay            : float = 0.0
        self.transitions                 : list  = []

