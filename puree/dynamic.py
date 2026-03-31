# Created by XWZ
# ◕‿◕ Distributed for free at:
# https://github.com/nicolaiprodromov/puree
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from .log import get_logger

logger = get_logger(__name__)

_id_counter = 0

if TYPE_CHECKING:
    from .components.container import Container
    from .parser import UI


class DynamicContainerManager:
    """
    Manages dynamic container creation and destruction at runtime.
    Holds a reference to the active UI instance and delegates to its methods.
    """

    def __init__(self):
        self._ui: Optional["UI"] = None

    def set_ui(self, ui: "UI") -> None:
        self._ui = ui

    def _require_ui(self) -> "UI":
        if self._ui is None:
            raise RuntimeError(
                "DynamicContainerManager has no UI. Call set_ui() after parsing, or ensure the UI is loaded."
            )
        return self._ui

    def add_child(
        self, parent: "Container", template: str, child_id: Optional[str] = None, params: Optional[dict] = None
    ) -> "Container":
        """
        Add a new child container from a component template and append it to parent.

        Args:
            parent:    The container to add the child to.
            template:  Component template name, e.g. "[msg_slot]" or "msg_slot".
            child_id:  Optional explicit ID for the new container.
            params:    Template parameter overrides.

        Returns:
            The newly created Container.
        """
        ui = self._require_ui()
        template_name = template.strip("[]")

        if child_id is None:
            global _id_counter
            child_id = f"{parent.id}_{template_name}_{_id_counter}"
            _id_counter += 1

        from .components.container import Container

        child = Container()
        child.id = child_id
        child.parent = parent

        if params is None:
            params = {}

        if template_name in ui._component_registry:
            ui._instantiate_component_into(template_name, child, params)
        else:
            logger.warning(f"add_child: component '{template_name}' not in registry — creating empty container")

        parent.children.append(child)
        parent.mark_dirty()

        try:
            ui._rebuild_after_structural_change()
        except Exception as e:
            logger.error(f"Rebuild failed after add_child: {e}", exc_info=True)

        logger.debug(f"add_child: created '{child_id}' under '{parent.id}'")
        return child

    def insert_child(
        self,
        parent: "Container",
        index: int,
        template: str,
        child_id: Optional[str] = None,
        params: Optional[dict] = None,
    ) -> "Container":
        """
        Insert a new child container from a component template at a specific index.

        Args:
            parent:    The container to insert into.
            index:     Position to insert at (0 = prepend; clamped to valid range).
            template:  Component template name, e.g. "[msg_slot]" or "msg_slot".
            child_id:  Optional explicit ID for the new container.
            params:    Template parameter overrides.

        Returns:
            The newly created Container.
        """
        ui = self._require_ui()
        template_name = template.strip("[]")

        if child_id is None:
            global _id_counter
            child_id = f"{parent.id}_{template_name}_{_id_counter}"
            _id_counter += 1

        from .components.container import Container

        child = Container()
        child.id = child_id
        child.parent = parent

        if params is None:
            params = {}

        if template_name in ui._component_registry:
            ui._instantiate_component_into(template_name, child, params)
        else:
            logger.warning(f"insert_child: component '{template_name}' not in registry — creating empty container")

        idx = max(0, min(index, len(parent.children)))
        parent.children.insert(idx, child)
        parent.mark_dirty()

        try:
            ui._rebuild_after_structural_change()
        except Exception as e:
            logger.error(f"Rebuild failed after insert_child: {e}", exc_info=True)

        logger.debug(f"insert_child: created '{child_id}' at index {idx} under '{parent.id}'")
        return child

    def remove_child(self, parent: "Container", id_or_container) -> bool:
        """
        Remove a child container by ID string or Container reference.

        Returns:
            True if the child was found and removed, False otherwise.
        """
        ui = self._require_ui()

        if isinstance(id_or_container, str):
            target = next((c for c in parent.children if c.id == id_or_container), None)
        else:
            target = id_or_container if id_or_container in parent.children else None

        if target is None:
            logger.warning(f"remove_child: '{id_or_container}' not found in '{parent.id}'")
            return False

        parent.children.remove(target)
        target.parent = None
        parent.mark_dirty()

        try:
            ui._rebuild_after_structural_change()
        except Exception as e:
            logger.error(f"Rebuild failed after remove_child: {e}", exc_info=True)

        logger.debug(f"remove_child: removed '{getattr(target, 'id', id_or_container)}' from '{parent.id}'")
        return True

    def clear_children(self, parent: "Container") -> None:
        """Remove all children from a container."""
        ui = self._require_ui()

        for child in parent.children:
            child.parent = None
        parent.children.clear()
        parent.mark_dirty()

        try:
            ui._rebuild_after_structural_change()
        except Exception as e:
            logger.error(f"Rebuild failed after clear_children: {e}", exc_info=True)

        logger.debug(f"clear_children: cleared all children from '{parent.id}'")


# Module-level singleton used by Container methods and parser_op.
dynamic_manager = DynamicContainerManager()
