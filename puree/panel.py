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

import time
from collections import deque

import bpy
from bpy.props import BoolProperty, CollectionProperty, FloatProperty, FloatVectorProperty, IntProperty, StringProperty
from bpy.types import Panel, PropertyGroup, UIList

from . import render
from .console import _messages as _console_messages
from .log import get_logger

logger = get_logger(__name__)

_MAX_EVENT_LOG = 200
_event_log = deque(maxlen=_MAX_EVENT_LOG)


def log_event(action, container_id):
    """Record a UI event. Called from hit_op, transition_manager, etc."""
    _event_log.appendleft((time.monotonic(), action, container_id))


def _update_event_log_collection():
    wm = bpy.context.window_manager
    wm.xwz_event_log.clear()
    for _ts, action, cid in _event_log:
        item = wm.xwz_event_log.add()
        item.action = action
        item.container_id = cid


class EventLogItem(PropertyGroup):
    action: StringProperty()
    container_id: StringProperty()


_ACTION_ICONS = {
    "hover": "MOUSE_MOVE",
    "hoverout": "MOUSE_MOVE",
    "click": "MOUSE_LMB",
    "toggle": "CHECKMARK",
    "focus": "LIGHT_SUN",
    "input:focus": "CURSOR",
    "input:blur": "CURSOR",
    "scroll": "MOUSE_MMB",
}


def _icon_for_action(action):
    if action in _ACTION_ICONS:
        return _ACTION_ICONS[action]
    if action.startswith("transition:"):
        return "ANIM"
    return "EVENT_RETURN"


class XWZ_UL_event_log(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)
            row.label(text="", icon=_icon_for_action(item.action))
            sub = row.row(align=True)
            sub.scale_x = 0.6
            sub.label(text=item.container_id)
            row.label(text=f"→  {item.action}")
        elif self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text=item.action, icon=_icon_for_action(item.action))


class XWZ_OT_show_hierarchy(bpy.types.Operator):
    bl_idname = "xwz.show_hierarchy"
    bl_label = "Hierarchy"
    bl_description = "Show the container hierarchy"

    def execute(self, context):
        context.window_manager.xwz_debug_tab = "HIERARCHY"
        return {"FINISHED"}


class XWZ_OT_show_event_log(bpy.types.Operator):
    bl_idname = "xwz.show_event_log"
    bl_label = "Events"
    bl_description = "Show the live event log"

    def execute(self, context):
        context.window_manager.xwz_debug_tab = "EVENTS"
        return {"FINISHED"}


class XWZ_OT_show_console(bpy.types.Operator):
    bl_idname = "xwz.show_console"
    bl_label = "Console"
    bl_description = "Show the developer console output"

    def execute(self, context):
        context.window_manager.xwz_debug_tab = "CONSOLE"
        return {"FINISHED"}


class XWZ_OT_show_settings(bpy.types.Operator):
    bl_idname = "xwz.show_settings"
    bl_label = "Settings"
    bl_description = "Show debug panel settings"

    def execute(self, context):
        context.window_manager.xwz_debug_tab = "SETTINGS"
        return {"FINISHED"}


class XWZ_OT_restart_ui(bpy.types.Operator):
    bl_idname = "xwz.restart_ui"
    bl_label = "Restart UI"
    bl_description = "Stop and start the UI (full refresh)"

    def execute(self, context):
        bpy.ops.xwz.stop_ui()
        _event_log.clear()
        context.window_manager.xwz_event_log.clear()
        bpy.ops.xwz.start_ui()
        return {"FINISHED"}


class XWZ_OT_clear_event_log(bpy.types.Operator):
    bl_idname = "xwz.clear_event_log"
    bl_label = "Clear Event Log"
    bl_description = "Clear all logged events"

    def execute(self, context):
        _event_log.clear()
        context.window_manager.xwz_event_log.clear()
        return {"FINISHED"}


class ConsoleMessageItem(PropertyGroup):
    level: StringProperty()
    message: StringProperty()


_LEVEL_ICONS = {
    "LOG": "INFO",
    "INFO": "INFO",
    "WARN": "ERROR",
    "ERROR": "CANCEL",
}


def _update_console_collection():
    wm = bpy.context.window_manager
    wm.xwz_console_messages.clear()
    for _ts, level, msg in _console_messages:
        item = wm.xwz_console_messages.add()
        item.level = level
        item.message = msg


class XWZ_UL_console_messages(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)
            row.label(text="", icon=_LEVEL_ICONS.get(item.level, "INFO"))
            row.label(text=item.message)
        elif self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text=item.message, icon=_LEVEL_ICONS.get(item.level, "INFO"))


class XWZ_OT_clear_console(bpy.types.Operator):
    bl_idname = "xwz.clear_console"
    bl_label = "Clear Console"
    bl_description = "Clear all console messages"

    def execute(self, context):
        _console_messages.clear()
        context.window_manager.xwz_console_messages.clear()
        return {"FINISHED"}


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
                render._render_data.debug_outlined_containers.clear()
            else:
                render._render_data.debug_outlined_containers.clear()
                render._render_data.debug_outlined_containers.add(self.container_id)

            render._render_data.needs_texture_update = True

        return {"FINISHED"}


class XWZ_OT_toggle_inspect_mode(bpy.types.Operator):
    bl_idname = "xwz.toggle_inspect_mode"
    bl_label = "Toggle Inspect Mode"
    bl_description = "Hover over elements to highlight them (like browser inspector)"

    def execute(self, context):
        wm = context.window_manager
        wm.xwz_inspect_mode = not wm.xwz_inspect_mode
        if not wm.xwz_inspect_mode and render._render_data:
            render._render_data.debug_outlined_containers.clear()
            render._render_data.needs_texture_update = True
        return {"FINISHED"}


def register():
    bpy.utils.register_class(ContainerItem)
    bpy.utils.register_class(EventLogItem)
    bpy.utils.register_class(XWZ_UL_container_hierarchy)
    bpy.utils.register_class(XWZ_UL_event_log)
    bpy.utils.register_class(XWZ_OT_toggle_debug_outline)
    bpy.utils.register_class(XWZ_OT_toggle_inspect_mode)
    bpy.utils.register_class(XWZ_OT_show_hierarchy)
    bpy.utils.register_class(XWZ_OT_show_event_log)
    bpy.utils.register_class(XWZ_OT_show_console)
    bpy.utils.register_class(XWZ_OT_show_settings)
    bpy.utils.register_class(XWZ_OT_restart_ui)
    bpy.utils.register_class(XWZ_OT_clear_event_log)
    bpy.utils.register_class(ConsoleMessageItem)
    bpy.utils.register_class(XWZ_UL_console_messages)
    bpy.utils.register_class(XWZ_OT_clear_console)

    register_dynamic_panel()

    bpy.types.WindowManager.xwz_container_hierarchy = CollectionProperty(type=ContainerItem)
    bpy.types.WindowManager.xwz_container_hierarchy_index = IntProperty()
    bpy.types.WindowManager.xwz_event_log = CollectionProperty(type=EventLogItem)
    bpy.types.WindowManager.xwz_event_log_index = IntProperty()
    bpy.types.WindowManager.xwz_console_messages = CollectionProperty(type=ConsoleMessageItem)
    bpy.types.WindowManager.xwz_console_messages_index = IntProperty()
    bpy.types.WindowManager.xwz_debug_tab = StringProperty(
        name="Debug Tab",
        default="HIERARCHY",
    )
    bpy.types.WindowManager.xwz_inspect_mode = BoolProperty(
        name="Inspect Mode",
        default=False,
    )
    bpy.types.WindowManager.xwz_debug_passepartout = FloatProperty(
        name="Passepartout",
        default=0.7,
        min=0.0,
        max=1.0,
        subtype="FACTOR",
    )
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
    del bpy.types.WindowManager.xwz_debug_passepartout
    del bpy.types.WindowManager.xwz_inspect_mode
    del bpy.types.WindowManager.xwz_debug_tab
    del bpy.types.WindowManager.xwz_console_messages_index
    del bpy.types.WindowManager.xwz_console_messages
    del bpy.types.WindowManager.xwz_event_log_index
    del bpy.types.WindowManager.xwz_event_log
    del bpy.types.WindowManager.xwz_container_hierarchy_index
    del bpy.types.WindowManager.xwz_container_hierarchy

    _event_log.clear()
    _console_messages.clear()

    unregister_dynamic_panel()

    bpy.utils.unregister_class(XWZ_OT_clear_console)
    bpy.utils.unregister_class(XWZ_UL_console_messages)
    bpy.utils.unregister_class(ConsoleMessageItem)
    bpy.utils.unregister_class(XWZ_OT_clear_event_log)
    bpy.utils.unregister_class(XWZ_OT_restart_ui)
    bpy.utils.unregister_class(XWZ_OT_show_settings)
    bpy.utils.unregister_class(XWZ_OT_show_console)
    bpy.utils.unregister_class(XWZ_OT_show_event_log)
    bpy.utils.unregister_class(XWZ_OT_show_hierarchy)
    bpy.utils.unregister_class(XWZ_OT_toggle_inspect_mode)
    bpy.utils.unregister_class(XWZ_OT_toggle_debug_outline)
    bpy.utils.unregister_class(XWZ_UL_event_log)
    bpy.utils.unregister_class(XWZ_UL_container_hierarchy)
    bpy.utils.unregister_class(EventLogItem)
    bpy.utils.unregister_class(ContainerItem)


_current_panel_class = None


def register_dynamic_panel():
    global _current_panel_class

    target_space = "VIEW_3D"
    try:
        from .space_config import get_target_space

        space = get_target_space()
        if space:
            target_space = space
    except Exception:
        logger.debug("Failed to get target space", exc_info=True)

    unregister_dynamic_panel()

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

            row = layout.row(align=True)
            row.scale_y = 1.8
            if render._render_data and render._render_data.running:
                row.operator("xwz.stop_ui", text="Stop", icon="PAUSE")
                row.scale_x = 1.5
                row.operator("xwz.restart_ui", text="", icon="FILE_REFRESH")
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

                    tab = wm.xwz_debug_tab

                    toolbar_row = col.row(align=False)
                    left = toolbar_row.row(align=True)
                    inspect_icon = "VIEWZOOM" if not wm.xwz_inspect_mode else "HIDE_OFF"
                    left.operator("xwz.toggle_inspect_mode", text="", icon=inspect_icon, depress=wm.xwz_inspect_mode)
                    right = toolbar_row.row(align=True)
                    right.alignment = "RIGHT"
                    right.operator("xwz.show_hierarchy", text="Hierarchy", icon="OUTLINER", depress=tab == "HIERARCHY")
                    right.operator("xwz.show_event_log", text="Events", icon="TEXT", depress=tab == "EVENTS")
                    right.operator("xwz.show_console", text="Console", icon="CONSOLE", depress=tab == "CONSOLE")
                    right.operator("xwz.show_settings", text="", icon="PREFERENCES", depress=tab == "SETTINGS")

                    if tab == "EVENTS":
                        _update_event_log_collection()
                        col.template_list(
                            "XWZ_UL_event_log",
                            "",
                            wm,
                            "xwz_event_log",
                            wm,
                            "xwz_event_log_index",
                            rows=10,
                        )
                        col.operator("xwz.clear_event_log", text="Clear", icon="TRASH")
                    elif tab == "CONSOLE":
                        _update_console_collection()
                        col.template_list(
                            "XWZ_UL_console_messages",
                            "",
                            wm,
                            "xwz_console_messages",
                            wm,
                            "xwz_console_messages_index",
                            rows=10,
                        )
                        col.operator("xwz.clear_console", text="Clear", icon="TRASH")
                    elif tab == "SETTINGS":
                        col.separator(factor=0.5)

                        col.label(text="Overlay", icon="OVERLAY")
                        overlay = col.column(align=True)
                        overlay.prop(wm, "xwz_debug_passepartout", text="Passepartout", slider=True)

                        col.separator(factor=1.0)

                        col.label(text="Appearance", icon="COLOR")
                        appearance = col.column(align=True)
                        appearance.prop(wm, "xwz_debug_border_color", text="Border Color")
                    else:
                        col.template_list(
                            "XWZ_UL_container_hierarchy",
                            "",
                            wm,
                            "xwz_container_hierarchy",
                            wm,
                            "xwz_container_hierarchy_index",
                            rows=10,
                        )

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
