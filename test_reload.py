"""
Test script to verify font/image reload fix

This script tests that the addon can be disabled and re-enabled
without restarting Blender, and that fonts/images are properly reloaded.

Usage in Blender:
1. Enable the addon
2. Run this script
3. The script will test the reload functionality
"""

import bpy

def test_font_reload():
    """Test that fonts are available after reload"""
    print("\n=== Testing Font Reload ===")
    
    # Check if addon is loaded
    if not hasattr(bpy.ops, 'xwz'):
        print("ERROR: Addon not loaded")
        return False
    
    # Get font manager
    from puree.text_op import font_manager
    
    if font_manager is None:
        print("ERROR: font_manager is None")
        return False
    
    available_fonts = font_manager.get_available_fonts()
    print(f"Available fonts: {available_fonts}")
    
    if len(available_fonts) == 0:
        print("ERROR: No fonts loaded")
        return False
    
    print(f"SUCCESS: {len(available_fonts)} fonts loaded")
    return True

def test_image_reload():
    """Test that images are available after reload"""
    print("\n=== Testing Image Reload ===")
    
    # Get image manager
    from puree.img_op import image_manager
    
    if image_manager is None:
        print("ERROR: image_manager is None")
        return False
    
    available_images = image_manager.get_available_images()
    print(f"Available images: {available_images}")
    
    if len(available_images) == 0:
        print("WARNING: No images loaded (this is OK if assets folder is empty)")
        return True
    
    print(f"SUCCESS: {len(available_images)} images loaded")
    return True

def test_full_cycle():
    """Test unregister and re-register cycle"""
    print("\n=== Testing Full Unregister/Register Cycle ===")
    
    try:
        # Unregister
        print("Unregistering addon...")
        import puree
        puree.unregister()
        print("Unregister complete")
        
        # Re-register
        print("Re-registering addon...")
        puree.register()
        print("Re-register complete")
        
        # Test that resources are available
        font_ok = test_font_reload()
        image_ok = test_image_reload()
        
        if font_ok and image_ok:
            print("\n✓ Full cycle test PASSED")
            return True
        else:
            print("\n✗ Full cycle test FAILED")
            return False
            
    except Exception as e:
        print(f"ERROR during full cycle test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Font/Image Reload Test")
    print("=" * 60)
    
    # Test initial state
    font_ok = test_font_reload()
    image_ok = test_image_reload()
    
    # Test full cycle
    if font_ok:
        cycle_ok = test_full_cycle()
    else:
        print("\nSkipping full cycle test due to initial state errors")
        cycle_ok = False
    
    print("\n" + "=" * 60)
    if font_ok and cycle_ok:
        print("ALL TESTS PASSED ✓")
    else:
        print("SOME TESTS FAILED ✗")
    print("=" * 60)
