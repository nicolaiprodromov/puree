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

import bpy
from bpy.props import BoolProperty, CollectionProperty, FloatVectorProperty, IntProperty, StringProperty
from bpy.types import Panel, PropertyGroup, UIList

from . import render
from .log import get_logger

logger = get_logger(__name__)


class ContainerItem(PropertyGroup):
    container_id: StringProperty()
    display_name: StringProperty()
    depth: IntProperty()
    is_visible: BoolProperty()
    is_outlined: BoolProperty()


class XWZ_UL_container_hierarchy(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)

            tree_prefix = ""
            for i in range(item.depth):
                if i == item.depth - 1:
                    tree_prefix += "↳ "
                else:
                    tree_prefix += "    "

            icon = "CHECKBOX_HLT" if item.is_outlined else "CHECKBOX_DEHLT"
            if item.depth > 0:
                op = row.operator("xwz.toggle_debug_outline", text="", icon=icon, emboss=False)
                op.container_id = item.container_id

            if item.display_name == "root":
                tree_prefix = " ⾕  "
            row.label(text=f"{tree_prefix}{item.display_name}")

        elif self.layout_type == "GRID":
            layout.alignment = "CENTER"
            icon = "CHECKBOX_HLT" if item.is_outlined else "CHECKBOX_DEHLT"
            layout.label(text="", icon=icon)


def update_container_hierarchy():
    from . import parser_op

    wm = bpy.context.window_manager
    wm.xwz_container_hierarchy.clear()

    if not parser_op._container_json_data:
        return

    containers = parser_op._container_json_data

    def build_tree(container_idx, depth=0, parent_id=None):
        if container_idx < 0 or container_idx >= len(containers):
            return

        container = containers[container_idx]
        item = wm.xwz_container_hierarchy.add()

        item.container_id = str(container_idx)

        full_id = container["id"]

        if parent_id and full_id.startswith(parent_id + "_"):
            item.display_name = full_id[len(parent_id) + 1 :]
        else:
            item.display_name = full_id

        item.depth = depth
        item.is_visible = container.get("display", True)

        is_outlined = False
        if render._render_data:
            is_outlined = item.container_id in render._render_data.debug_outlined_containers
        item.is_outlined = is_outlined

        for child_idx in container.get("children", []):
            build_tree(child_idx, depth + 1, full_id)

    build_tree(0, 0)


class XWZ_OT_toggle_debug_outline(bpy.types.Operator):
    bl_idname = "xwz.toggle_debug_outline"
    bl_label = "Toggle Debug Outline"
    bl_description = "Select this container for debug highlight"

    container_id: bpy.props.StringProperty()

    def execute(self, context):
        if render._render_data:
            if self.container_id in render._render_data.debug_outlined_containers:
                # Clicking the already-selected container deselects it
                render._render_data.debug_outlined_containers.clear()
            else:
                # Single-select: clear all, then select this one
                render._render_data.debug_outlined_containers.clear()
                render._render_data.debug_outlined_containers.add(self.container_id)

            render._render_data.needs_texture_update = True

        return {"FINISHED"}


def register():
    bpy.utils.register_class(ContainerItem)
    bpy.utils.register_class(XWZ_UL_container_hierarchy)
    bpy.utils.register_class(XWZ_OT_toggle_debug_outline)

    register_dynamic_panel()

    bpy.types.WindowManager.xwz_container_hierarchy = CollectionProperty(type=ContainerItem)
    bpy.types.WindowManager.xwz_container_hierarchy_index = IntProperty()
    bpy.types.WindowManager.xwz_debug_border_color = FloatVectorProperty(
        name="Border Color",
        subtype="COLOR",
        default=(0.1, 0.15, 0.4),
        min=0.0,
        max=1.0,
        size=3,
    )


def unregister():
    del bpy.types.WindowManager.xwz_debug_border_color
    del bpy.types.WindowManager.xwz_container_hierarchy_index
    del bpy.types.WindowManager.xwz_container_hierarchy

    unregister_dynamic_panel()

    bpy.utils.unregister_class(XWZ_OT_toggle_debug_outline)
    bpy.utils.unregister_class(XWZ_UL_container_hierarchy)
    bpy.utils.unregister_class(ContainerItem)


_current_panel_class = None


def register_dynamic_panel():
    global _current_panel_class

    # Get target space
    target_space = "VIEW_3D"  # Default
    try:
        from .space_config import get_target_space

        space = get_target_space()
        if space:
            target_space = space
    except Exception:
        logger.debug("Failed to get target space", exc_info=True)

    # Unregister existing panel if any
    unregister_dynamic_panel()

    # Create new panel class with correct space_type
    class XWZ_PT_dynamic_panel(Panel):
        bl_label = "puree"
        bl_idname = "XWZ_PT_dynamic_panel"
        bl_space_type = target_space
        bl_region_type = "UI"
        bl_category = "puree"

        @classmethod
        def poll(cls, context):
            return context.window_manager.xwz_debug_panel

        def draw(self, context):
            layout = self.layout

            # Status row: Running/Paused + Stop/Start on the same row, tall
            row = layout.row(align=True)
            row.scale_y = 1.8
            if render._render_data and render._render_data.running:
                row.operator("xwz.stop_ui", text="Stop", icon="PAUSE")
            else:
                row.operator("xwz.start_ui", text="Start", icon="PLAY")
                layout.label(text=f"Debug panel in {target_space}")

            if render._render_data and render._render_data.running:
                box = layout.box()
                col = box.row(align=True)
                col.separator()
                col.label(text=f"{render._render_data.texture_size[0]}x{render._render_data.texture_size[1]}")
                col.label(text=f"{render._render_data.compute_fps:.1f} FPS")

                box = layout.box()
                col = box.column(align=True)

                from . import parser_op

                if parser_op._container_json_data:
                    update_container_hierarchy()

                    wm = context.window_manager
                    col.template_list(
                        "XWZ_UL_container_hierarchy",
                        "",
                        wm,
                        "xwz_container_hierarchy",
                        wm,
                        "xwz_container_hierarchy_index",
                        rows=10,
                    )

                # Debug border color picker
                row = layout.box()
                row.prop(context.window_manager, "xwz_debug_border_color", text="Border Color")

    _current_panel_class = XWZ_PT_dynamic_panel
    bpy.utils.register_class(XWZ_PT_dynamic_panel)

    logger.info(f"Registered debug panel for space: {target_space}")


def unregister_dynamic_panel():
    global _current_panel_class

    if _current_panel_class:
        try:
            bpy.utils.unregister_class(_current_panel_class)
        except Exception:
            pass
        _current_panel_class = None


def update_panel_space():
    """Call this function when the space configuration changes"""
    register_dynamic_panel()
