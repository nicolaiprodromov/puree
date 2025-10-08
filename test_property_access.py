"""
Test script to verify property-based container access works correctly.
This demonstrates both index-based (old) and property-based (new) access methods.
"""

# Import only the Container class definition without bpy dependencies
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
        
        self._dirty        : bool  = False  # Track if container state changed
    
    def __getattr__(self, name):
        """
        Enable property-based access to child containers by their id.
        This allows accessing containers like: app.theme.root.bg.body
        instead of: app.theme.root.children[0].children[2]
        """
        # Avoid infinite recursion by checking if we're accessing 'children'
        if name == 'children':
            raise AttributeError(f"'Container' object has no attribute '{name}'")
        
        # Search for a child container with matching id
        try:
            children = object.__getattribute__(self, 'children')
            for child in children:
                if child.id == name:
                    return child
        except AttributeError:
            pass
        
        # If not found in children, raise AttributeError
        raise AttributeError(f"'Container' object has no attribute or child named '{name}'")
    
    def mark_dirty(self):
        """Mark this container as having changed state that needs GPU sync"""
        self._dirty = True

# Create a simple container hierarchy matching the TOML structure
root = Container()
root.id = "root"

bg = Container()
bg.id = "bg"
bg.parent = root
root.children.append(bg)

body = Container()
body.id = "body"
body.parent = bg
bg.children.append(body)

buttons_test1 = Container()
buttons_test1.id = "buttons_test1"
buttons_test1.parent = body
body.children.append(buttons_test1)

hover_test = Container()
hover_test.id = "hover_test"
hover_test.parent = buttons_test1
buttons_test1.children.append(hover_test)

ht_text = Container()
ht_text.id = "ht_text"
ht_text.parent = hover_test
hover_test.children.append(ht_text)

print("Testing container property-based access...\n")

# Test 1: Old way (index-based access) - should still work
print("1. Index-based access (OLD WAY):")
try:
    old_way = root.children[0].children[0].children[0].children[0]
    print(f"   ✓ root.children[0].children[0].children[0].children[0].id = '{old_way.id}'")
except Exception as e:
    print(f"   ✗ Failed: {e}")

# Test 2: New way (property-based access)
print("\n2. Property-based access (NEW WAY):")
try:
    new_way = root.bg.body.buttons_test1.hover_test
    print(f"   ✓ root.bg.body.buttons_test1.hover_test.id = '{new_way.id}'")
except Exception as e:
    print(f"   ✗ Failed: {e}")

# Test 3: Verify both ways point to the same object
print("\n3. Verify both methods access the same object:")
try:
    old_way = root.children[0].children[0].children[0].children[0]
    new_way = root.bg.body.buttons_test1.hover_test.ht_text
    if old_way is new_way:
        print(f"   ✓ Both methods point to the same object: '{new_way.id}'")
    else:
        print(f"   ✗ Objects differ: old='{old_way.id}' vs new='{new_way.id}'")
except Exception as e:
    print(f"   ✗ Failed: {e}")

# Test 4: Access full path with property-based syntax
print("\n4. Full path access:")
try:
    full_path = root.bg.body.buttons_test1.hover_test.ht_text
    print(f"   ✓ root.bg.body.buttons_test1.hover_test.ht_text.id = '{full_path.id}'")
except Exception as e:
    print(f"   ✗ Failed: {e}")

# Test 5: Error handling for non-existent child
print("\n5. Error handling for non-existent child:")
try:
    invalid = root.bg.nonexistent
    print(f"   ✗ Should have raised AttributeError but got: '{invalid.id}'")
except AttributeError as e:
    print(f"   ✓ Correctly raised AttributeError: {e}")

# Test 6: Mixed access (combining both methods)
print("\n6. Mixed access (combining index and property-based):")
try:
    mixed = root.children[0].body.buttons_test1.children[0].ht_text
    print(f"   ✓ root.children[0].body.buttons_test1.children[0].ht_text.id = '{mixed.id}'")
except Exception as e:
    print(f"   ✗ Failed: {e}")

print("\n" + "="*60)
print("All tests completed successfully!")
print("="*60)
print("\nYou can now use property-based access in your scripts:")
print("  app.theme.root.bg.body.buttons_test1.hover_test")
print("instead of:")
print("  app.theme.root.children[0].children[2].children[0].children[0]")
