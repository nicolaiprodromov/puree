# Created by XWZ
# ◕‿◕ Distributed for free at:
# https://github.com/nicolaiprodromov/puree
from typing import Optional, Callable, List


class KeyBinding:
    """A single registered keyboard shortcut."""
    def __init__(self, handle_id: str, key_combo: str, callback: Callable,
                 when: Optional[str] = None, container_id: Optional[str] = None):
        self.handle_id = handle_id
        self.key_combo = key_combo       # normalized, e.g. "CTRL+N"
        self.callback = callback
        self.when = when                 # None | "input_focused" | container_id string
        self.container_id = container_id # scope to container (None = global)
        self.cancelled = False


class ContainerKeyProxy:
    """Proxy returned by container.keys to scope bindings to that container."""
    def __init__(self, container_id: str):
        self._container_id = container_id

    def bind(self, key_combo: str, callback: Callable, when: Optional[str] = None) -> 'KeyBinding':
        return keys.bind(key_combo, callback, when=when, container_id=self._container_id)


class KeyManager:
    def __init__(self):
        self._bindings: List[KeyBinding] = []
        self._id_counter = 0

    def bind(self, key_combo: str, callback: Callable,
             when: Optional[str] = None, container_id: Optional[str] = None) -> KeyBinding:
        """Register a keyboard shortcut. Returns binding handle."""
        normalized = self._normalize_combo(key_combo)
        handle_id = f"kb_{self._id_counter}"
        self._id_counter += 1
        binding = KeyBinding(handle_id, normalized, callback, when=when, container_id=container_id)
        self._bindings.append(binding)
        return binding

    def unbind(self, binding: KeyBinding) -> None:
        """Remove a binding."""
        binding.cancelled = True
        self._bindings = [b for b in self._bindings if not b.cancelled]

    def clear(self) -> None:
        """Remove all bindings (called on hot reload)."""
        self._bindings.clear()

    def dispatch(self, event, focused_container_id: Optional[str] = None,
                 any_input_focused: bool = False) -> bool:
        """
        Called from KeyboardHandler.modal().
        Returns True if event was consumed by a binding.
        """
        if event.value != 'PRESS':
            return False

        event_combo = self._event_to_combo(event)
        if not event_combo:
            return False

        consumed = False
        for binding in list(self._bindings):
            if binding.cancelled:
                continue
            if binding.key_combo != event_combo:
                continue
            # Check when condition
            if not self._check_when(binding, focused_container_id, any_input_focused):
                continue
            # Check container scope
            if binding.container_id is not None:
                if binding.container_id != focused_container_id:
                    continue
            # Fire
            try:
                binding.callback()
            except Exception as e:
                from .log import get_logger
                get_logger(__name__).error(f"Keyboard binding error: {e}", exc_info=True)
            consumed = True

        return consumed

    def _check_when(self, binding: KeyBinding, focused_id: Optional[str],
                    any_input_focused: bool) -> bool:
        if binding.when is None:
            return True
        if binding.when == "input_focused":
            return any_input_focused
        # Otherwise treat as container ID scope
        return focused_id == binding.when

    def _normalize_combo(self, combo: str) -> str:
        """Normalize key combo string: 'ctrl+n' -> 'CTRL+N', 'Enter' -> 'ENTER'."""
        parts = combo.upper().replace(' ', '').split('+')
        modifiers = sorted(p for p in parts if p in ('CTRL', 'SHIFT', 'ALT'))
        key_parts = [p for p in parts if p not in ('CTRL', 'SHIFT', 'ALT')]
        if not key_parts:
            return '+'.join(modifiers)
        # Normalize key aliases
        key = key_parts[0]
        aliases = {
            'ENTER': 'ENTER', 'RETURN': 'ENTER',
            'ESC': 'ESCAPE', 'ESCAPE': 'ESCAPE',
            'DEL': 'DELETE', 'DELETE': 'DELETE',
            'BACKSPACE': 'BACKSPACE',
            'TAB': 'TAB',
            'SPACE': 'SPACE',
            'UP': 'UP', 'DOWN': 'DOWN', 'LEFT': 'LEFT', 'RIGHT': 'RIGHT',
            'HOME': 'HOME', 'END': 'END',
            'PAGEUP': 'PAGE_UP', 'PAGE_UP': 'PAGE_UP',
            'PAGEDOWN': 'PAGE_DOWN', 'PAGE_DOWN': 'PAGE_DOWN',
        }
        key = aliases.get(key, key)
        all_parts = modifiers + [key]
        return '+'.join(all_parts)

    def _event_to_combo(self, event) -> Optional[str]:
        """Convert a Blender event to a normalized combo string."""
        type_map = {
            'RET': 'ENTER', 'NUMPAD_ENTER': 'ENTER',
            'ESC': 'ESCAPE',
            'DEL': 'DELETE',
            'BACK_SPACE': 'BACKSPACE',
            'TAB': 'TAB',
            'SPACE': 'SPACE',
            'UP_ARROW': 'UP',
            'DOWN_ARROW': 'DOWN',
            'LEFT_ARROW': 'LEFT',
            'RIGHT_ARROW': 'RIGHT',
            'HOME': 'HOME',
            'END': 'END',
            'PAGE_UP': 'PAGE_UP',
            'PAGE_DOWN': 'PAGE_DOWN',
        }

        evt_type = event.type
        if len(evt_type) == 1 and evt_type.isalpha():
            key = evt_type.upper()
        elif evt_type in type_map:
            key = type_map[evt_type]
        else:
            return None  # unknown key, ignore

        parts = []
        if event.ctrl:
            parts.append('CTRL')
        if event.shift:
            parts.append('SHIFT')
        if event.alt:
            parts.append('ALT')
        parts.append(key)
        return '+'.join(parts)


# Module-level singleton
keys = KeyManager()
