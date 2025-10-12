# Font/Image Enum Error on Addon Reinstall Without Blender Restart

## Problem Description

When the addon was uninstalled and then reinstalled without restarting Blender, the following error would occur:

```
TypeError: Converting py args to operator properties: enum "NeueMontreal-BoldItalic" not found in ('default')
```

This error manifested during the UI startup process when calling `bpy.ops.xwz.draw_text()`.

## Root Cause

The issue was caused by **singleton pattern management** in both `FontManager` (text_op.py) and `ImageManager` (img_op.py).

### What Was Happening:

1. **First Install**: 
   - Singleton created with `_initialized = False`
   - `__init__` runs, loads fonts/images, sets `_initialized = True`
   - EnumProperty callbacks can successfully enumerate available fonts/images

2. **Uninstall**:
   - `unregister()` calls `font_manager.unload_fonts()` or `image_manager.unload_images()`
   - Resources are released BUT singleton instance persists with `_initialized = True`
   - The `fonts` and `images` dictionaries are cleared

3. **Reinstall (without Blender restart)**:
   - Same singleton instance is reused (because it's module-level)
   - `__init__` checks `if not self._initialized` → **FALSE**, so it returns early
   - Fonts/images are **NOT reloaded**
   - EnumProperty items callbacks try to enumerate from empty dictionaries
   - When the parser tries to use a font like "NeueMontreal-BoldItalic", the enum validation fails because the items list is empty except for the default fallback

## Solution

The fix involves properly managing the singleton lifecycle during addon registration/unregistration:

### Changes Made:

1. **Added `reload_fonts()` / `reload_images()` methods**:
   - Explicitly unload and reload resources
   - Used when addon is re-enabled after being disabled

2. **Added `reset_instance()` class method**:
   - Properly cleans up and nullifies the singleton
   - Called during `unregister()`

3. **Modified `register()` functions**:
   - Check if singleton is None (after unregister)
   - Recreate singleton if needed
   - Reload resources if singleton exists but was previously unloaded

4. **Modified `unregister()` functions**:
   - Call `reset_instance()` to properly clean up
   - Set global manager variable to None

### Code Changes:

**text_op.py:**
```python
def reload_fonts(self):
    """Reload all fonts - used when addon is re-enabled without Blender restart"""
    self.unload_fonts()
    self._load_fonts()

@classmethod
def reset_instance(cls):
    """Reset the singleton instance - used during addon unregister"""
    if cls._instance is not None:
        if cls._instance._initialized:
            cls._instance.unload_fonts()
        cls._instance = None

# In register():
if font_manager is None:
    font_manager = FontManager()
elif font_manager._initialized:
    font_manager.reload_fonts()

# In unregister():
FontManager.reset_instance()
font_manager = None
```

**img_op.py:**
- Similar changes applied to `ImageManager`

## Testing

To verify the fix works:

1. Install the addon
2. Enable it
3. Verify UI starts correctly with fonts
4. Disable the addon (uninstall)
5. Re-enable the addon (reinstall) **without restarting Blender**
6. UI should start correctly without font enum errors

## Technical Notes

- The singleton pattern is maintained for performance (avoid reloading resources on every import)
- The fix ensures resources are properly reloaded when needed
- This pattern should be applied to any future singleton managers in the codebase
- The `_initialized` flag alone was insufficient; explicit reload logic was needed
