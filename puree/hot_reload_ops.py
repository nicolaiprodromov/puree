"""
Hot Reload Operators for Puree UI
"""
import bpy
from bpy.types import Operator


class XWZ_OT_enable_hot_reload(Operator):
    bl_idname = "xwz.enable_hot_reload"
    bl_label = "Enable Hot Reload"
    bl_description = "Enable live file watching and UI hot reload"
    
    def execute(self, context):
        try:
            from .hot_reload import (
                setup_hot_reload, 
                register_default_callbacks, 
                get_hot_reload_manager
            )
            from . import get_addon_root
            from . import render
            
            addon_dir = get_addon_root()
            wm = context.window_manager
            
            # Setup hot reload system
            if setup_hot_reload(addon_dir):
                # Register callbacks
                register_default_callbacks()
                
                # Enable
                manager = get_hot_reload_manager()
                manager.enable()
                
                # Set global flag
                render._hot_reload_enabled = True
                
                self.report({'INFO'}, "🔥 Hot reload enabled")
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "Failed to enable hot reload")
                return {'CANCELLED'}
                
        except Exception as e:
            self.report({'ERROR'}, f"Hot reload error: {e}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


class XWZ_OT_disable_hot_reload(Operator):
    bl_idname = "xwz.disable_hot_reload"
    bl_label = "Disable Hot Reload"
    bl_description = "Disable live file watching and UI hot reload"
    
    def execute(self, context):
        try:
            from .hot_reload import get_hot_reload_manager
            from . import render
            
            manager = get_hot_reload_manager()
            manager.disable()
            
            # Clear global flag
            render._hot_reload_enabled = False
            
            self.report({'INFO'}, "❄️  Hot reload disabled")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Error disabling hot reload: {e}")
            return {'CANCELLED'}


class XWZ_OT_trigger_ui_reload(Operator):
    bl_idname = "xwz.trigger_ui_reload"
    bl_label = "Reload UI"
    bl_description = "Manually trigger a full UI reload"
    
    def execute(self, context):
        try:
            from .hot_reload import trigger_ui_reload
            
            if trigger_ui_reload():
                self.report({'INFO'}, "✓ UI reloaded")
                return {'FINISHED'}
            else:
                self.report({'WARNING'}, "UI reload completed with warnings")
                return {'FINISHED'}
                
        except Exception as e:
            self.report({'ERROR'}, f"Reload failed: {e}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


def register():
    bpy.utils.register_class(XWZ_OT_enable_hot_reload)
    bpy.utils.register_class(XWZ_OT_disable_hot_reload)
    bpy.utils.register_class(XWZ_OT_trigger_ui_reload)


def unregister():
    bpy.utils.unregister_class(XWZ_OT_trigger_ui_reload)
    bpy.utils.unregister_class(XWZ_OT_disable_hot_reload)
    bpy.utils.unregister_class(XWZ_OT_enable_hot_reload)
