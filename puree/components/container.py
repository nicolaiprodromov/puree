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
        
        self._dirty        : bool  = False
    
    def __getattr__(self, name):
        """
        Enable property-based access to:
        1. Child containers by their id (e.g., app.theme.root.bg.body)
        2. Style properties (e.g., container.text_scale delegates to container.style.text_scale)
        """
        # Avoid infinite recursion by checking if we're accessing core attributes
        if name in ('children', 'style', '__dict__'):
            raise AttributeError(f"'Container' object has no attribute '{name}'")
        
        # First, search for a child container with matching id
        try:
            children = object.__getattribute__(self, 'children')
            for child in children:
                if child.id == name or child.id.endswith(f"_{name}"):
                    return child
        except AttributeError:
            pass
        
        # If not found in children, try to get from style object
        try:
            style = object.__getattribute__(self, 'style')
            if style and hasattr(style, name):
                return getattr(style, name)
        except AttributeError:
            pass
        
        # If not found anywhere, raise AttributeError
        raise AttributeError(f"'Container' object has no attribute or child named '{name}'")
    
    def __setattr__(self, name, value):
        """
        Enable property-based setting of style properties.
        If the attribute doesn't exist on Container but exists on style,
        delegate to the style object.
        """
        # List of Container's own attributes that should be set directly
        container_attrs = {
            'id', 'parent', 'children', 'style', 'data', 'img', 'text', 'font',
            'layer', 'passive', 'click', 'toggle', 'scroll', 'hover', 'hoverout',
            '_toggle_value', '_toggled', '_clicked', '_hovered',
            '_prev_toggled', '_prev_clicked', '_prev_hovered', '_scroll_value', '_dirty'
        }
        
        # If it's a Container attribute, set it directly
        if name in container_attrs:
            object.__setattr__(self, name, value)
        # Otherwise, try to set it on the style object if it exists there
        else:
            try:
                style = object.__getattribute__(self, 'style')
                if style and hasattr(style, name):
                    setattr(style, name, value)
                else:
                    # If style doesn't have it either, set it on container
                    object.__setattr__(self, name, value)
            except AttributeError:
                # If style doesn't exist yet, set it on container
                object.__setattr__(self, name, value)
    
    def mark_dirty(self):
        """Mark this container as having changed state that needs GPU sync"""
        self._dirty = True

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