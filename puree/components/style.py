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
        self.color                   : List[float] = [1.0, 1.0, 1.0, 1.0]
        self.color_2                 : List[float] = [0.0, 0.0, 0.0, 0.0]
        self.color_gradient_rot      : float       = 0.0
        self.text_align              : str         = 'LEFT'
        self.text_align_v            : str         = 'CENTER'

        self.img_align_h            : str         = 'LEFT'
        self.img_align_v            : str         = 'TOP'
        self.opacity                : float       = 1.0

        self.border_radius            : float       = 0.0
        self.border_width             : float       = 0.0
        self.border_color             : List[float] = [0.0, 0.0, 0.0, 0.0]
        self.border_color_2           : List[float] = [0.0, 0.0, 0.0, 0.0]
        self.border_gradient_rot      : float       = 0.0
        
        self.box_shadow_color : List[float] = [0.0, 0.0, 0.0, 0.0]
        self.box_shadow_offset: List[float] = [0.0, 0.0, 0.0]
        self.box_shadow_blur  : float       = 0.0

        self.display         : str  = 'FLEX'
        self.overflow        : str  = 'HIDDEN'
        self.scrollbar_width : float = 0.0
        self.position        : str  = 'RELATIVE'
        
        self.align_items    : str = 'START'
        self.justify_items  : str = 'START'
        self.align_self     : str = 'START'
        self.justify_self   : str = 'START'
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
        self.flex_basis    : float = 0.0
        
        self.grid_auto_flow       : str            = 'ROW'
        self.grid_template_rows   : Optional[List] = None
        self.grid_template_columns: Optional[List] = None
        self.grid_auto_rows       : Optional[List] = None
        self.grid_auto_columns    : Optional[List] = None
        self.grid_row             : str            = 'AUTO'
        self.grid_column          : str            = 'AUTO'

