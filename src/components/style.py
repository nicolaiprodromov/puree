from __future__ import annotations
from typing import Optional, List, Union

class Style(): 
    def __init__(self): 
        self.id: str = ""

        self.width  : float = 0.0
        self.height : float = 0.0

        self.color              : List[float] = [0.0, 0.0, 0.0, 1.0]
        self.color_1            : List[float] = [0.0, 0.0, 0.0, 0.0]
        self.color_gradient_rot : float       = 0.0
        
        self.hover_color             : List[float] = [0.0, 0.0, 0.0, -1.0]
        self.hover_color_1           : List[float] = [0.0, 0.0, 0.0, 0.0]
        self.hover_color_gradient_rot: float       = 0.0

        self.click_color             : List[float] = [0.0, 0.0, 0.0, -1.0]
        self.click_color_1           : List[float] = [0.0, 0.0, 0.0, 0.0]
        self.click_color_gradient_rot: float       = 0.0
        
        self.text_x                 : float       = 0.0
        self.text_y                 : float       = 0.0
        self.text_scale             : float       = 12.0
        self.text_color             : List[float] = [1.0, 1.0, 1.0, 1.0]
        self.text_color_1           : List[float] = [0.0, 0.0, 0.0, 0.0]
        self.text_color_gradient_rot: float       = 0.0

        self.border_radius            : float       = 0.0
        self.border_width             : float       = 0.0
        self.border_color             : List[float] = [0.0, 0.0, 0.0, 0.0]
        self.border_color_1           : List[float] = [0.0, 0.0, 0.0, 0.0]
        self.border_color_gradient_rot: float       = 0.0
        
        self.box_shadow_color : List[float] = [0.0, 0.0, 0.0, 0.0]
        self.box_shadow_offset: List[float] = [0.0, 0.0, 0.0]
        self.box_shadow_blur  : float       = 0.0

        # STRECHABLE PROPERTIES -------------------------------------------------------------------------------------------
        self.background_image   : Optional[str] = None
        self.background_size    : str           = 'AUTO'       # AUTO, COVER, CONTAIN
        self.background_position: List[float]   = [0.0, 0.0]
        self.background_repeat  : str           = 'NO_REPEAT'  # REPEAT, NO_REPEAT, REPEAT_X, REPEAT_Y

        self.display         : str  = 'FLEX'      # Display: NONE, FLEX, GRID, BLOCK
        self.overflow        : str  = 'HIDDEN'
        self.scrollbar_width: float = 0.0         # float
        self.position        : str  = 'RELATIVE'  # Position: RELATIVE, ABSOLUTE
        
        self.align_items    : str = 'START'  # AlignItems: START, END, FLEX_START, FLEX_END, CENTER, BASELINE, STRETCH
        self.justify_items  : str = 'START'  # JustifyItems: START, END, FLEX_START, FLEX_END, CENTER, BASELINE, STRETCH
        self.align_self     : str = 'START'  # AlignSelf: START, END, FLEX_START, FLEX_END, CENTER, BASELINE, STRETCH
        self.justify_self   : str = 'START'  # JustifySelf: START, END, FLEX_START, FLEX_END, CENTER, BASELINE, STRETCH
        self.align_content  : str = 'START'  # AlignContent: START, END, FLEX_START, FLEX_END, CENTER, STRETCH, SPACE_BETWEEN, SPACE_EVENLY, SPACE_AROUND
        self.justify_content: str = 'START'  # JustifyContent: START, END, FLEX_START, FLEX_END, CENTER, STRETCH, SPACE_BETWEEN, SPACE_EVENLY, SPACE_AROUND
        
        # self.gap    : List[float] = [0.0, 0.0]            # SizePointsPercent (width, height)
        # self.padding: List[float] = [0.0, 0.0, 0.0, 0.0]  # RectPointsPercent (top, right, bottom, left)
        # self.border : List[float] = [0.0, 0.0, 0.0, 0.0]  # RectPointsPercent (top, right, bottom, left)
        # self.margin : List[float] = [0.0, 0.0, 0.0, 0.0]  # RectPointsPercentAuto (top, right, bottom, left)
        
        self.size        : List[float]     = [0.0, 0.0]  # SizePointsPercentAuto (width, height)
        self.min_size    : List[float]     = [0.0, 0.0]  # SizePointsPercentAuto (width, height)
        self.max_size    : List[float]     = [0.0, 0.0]  # SizePointsPercentAuto (width, height)
        self.aspect_ratio = True
        
        self.flex_wrap     : str   = 'NO_WRAP'  # FlexWrap: NO_WRAP, WRAP, WRAP_REVERSE
        self.flex_direction: str   = 'ROW'      # FlexDirection: ROW, COLUMN, ROW_REVERSE, COLUMN_REVERSE
        self.flex_grow     : float = 0.0        # float
        self.flex_shrink   : float = 1.0        # float
        self.flex_basis    : float = 0.0        # LengthPointsPercentAuto
        
        self.grid_auto_flow       : str            = 'ROW'   # GridAutoFlow: ROW, COLUMN, ROW_DENSE, COLUMN_DENSE
        self.grid_template_rows   : Optional[List] = None    # list[GridTrackSizing] or None
        self.grid_template_columns: Optional[List] = None    # list[GridTrackSizing] or None
        self.grid_auto_rows       : Optional[List] = None    # list[GridTrackSize] or None
        self.grid_auto_columns    : Optional[List] = None    # list[GridTrackSize] or None
        self.grid_row             : str            = 'AUTO'  # GridPlacement
        self.grid_column          : str            = 'AUTO'  # GridPlacement

