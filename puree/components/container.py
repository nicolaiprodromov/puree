from __future__ import annotations
from typing import Optional, List

class Container(): 
    def __init__(self): 
        self.id       : str                       = ""
        self.parent   : Optional[Container]       = []
        self.children : Optional[List[Container]] = []

        self.style : Optional[str] = ""
        self.data  : Optional[str] = ""
        self.img   : Optional[str] = ""
        self.text  : Optional[str] = ""
        self.font  : Optional[str] = ""

        self.layer   : int   = 0
        self.passive : bool  = False

        self.click         : List  = []
        self.toggle        : List  = []
        self.scroll        : List  = []
        self.hover         : List  = []
        self.hoverout      : List  = []
        
        self._toggle_value : bool  = False
        self._toggled      : bool  = False
        self._clicked      : bool  = False
        self._hovered      : bool  = False
        self._prev_toggled : bool  = False
        self._prev_clicked : bool  = False
        self._prev_hovered : bool  = False
        self._scroll_value : float = 0.0

class ContainerDefault():
    def __init__(self): 
        self.id    = None
        self.style = None

        self.parent   = None
        self.children = []

        self.click         = []
        self.toggle        = []
        self.scroll        = []
        self.hover         = []
        self.hoverout      = []
        self._toggle_value = False
        self._toggled      = False
        self._clicked      = False
        self._hovered      = False
        self._prev_toggled = False
        self._prev_clicked = False
        self._prev_hovered = False
        self._scroll_value = 0.0

        self.display      = True
        self.overflow     = False
        self.data         = ""
        self.img          = ""
        self.aspect_ratio = False
        self.text         = ""
        self.font         = 'NeueMontreal-Regular'

        self.layer   = 0
        self.passive = False

        self.x = 0.0
        self.y = 0.0

        self.width  = 100.0
        self.height = 100.0

        self.color              = [0.0, 0.0, 0.0, 1.0]
        self.color_1            = [0.0, 0.0, 0.0, 0.0]
        self.color_gradient_rot = 0.0
        
        self.hover_color              = [0.0, 0.0, 0.0, -1.0]
        self.hover_color_1            = [0.0, 0.0, 0.0, 0.0]
        self.hover_color_gradient_rot = 0.0

        self.click_color              = [0.0, 0.0, 0.0, -1.0]
        self.click_color_1            = [0.0, 0.0, 0.0, 0.0]
        self.click_color_gradient_rot = 0.0

        self.toggle_color              = [0.0, 0.0, 0.0, -1.0]
        self.toggle_color_1            = [0.0, 0.0, 0.0, 0.0]
        self.toggle_color_gradient_rot = 0.0

        self.border_color              = [0.0, 0.0, 0.0, 0.0]
        self.border_color_1            = [0.0, 0.0, 0.0, 0.0]
        self.border_color_gradient_rot = 0.0
        self.border_radius             = 0.0
        self.border_width              = 0.0
        
        self.text_color              = [1.0, 1.0, 1.0, 1.0]
        self.text_color_1            = [0.0, 0.0, 0.0, 0.0]
        self.text_color_gradient_rot = 0.0
        self.text_scale              = 12.0
        self.text_x                  = 0.0
        self.text_y                  = 0.0
        
        self.box_shadow_color  = [0.0, 0.0, 0.0, 0.0]
        self.box_shadow_offset = [0.0, 0.0, 0.0]
        self.box_shadow_blur   = 0.0
        
container_default = ContainerDefault()