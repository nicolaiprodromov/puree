"""
Puree JSON persistence module.

Provides a simple key-value store backed by a JSON file on disk.
Supports dot-notation for nested access, atomic writes, and optional
debounced auto-save via bpy.app.timers.

Usage:
    from puree.storage import Storage

    store = Storage("my_addon")
    store.set("theme", "dark")
    store.set("window.width", 800)
    theme = store.get("theme", default="light")

    store.auto_save = True          # debounced 500 ms auto-save
    store.save()                    # explicit flush
    store.load()                    # reload from disk

    # Project-scoped (saved next to .blend file)
    project = Storage("my_addon", scope="project")
"""

import json
import os
import pathlib

from .log import get_logger

logger = get_logger(__name__)


def _get_global_config_dir() -> pathlib.Path:
    """Return the platform-appropriate config directory for Puree."""
    if os.name == "nt":
        appdata = os.getenv("APPDATA")
        base = pathlib.Path(appdata) if appdata else pathlib.Path.home() / ".config"
    else:
        base = pathlib.Path.home() / ".config"
    return base / "puree"


class Storage:
    """JSON-backed key-value store with dot-notation, atomic writes, and
    optional debounced auto-save.

    Parameters
    ----------
    namespace:
        Logical name for this store (used as directory/file name component).
    scope:
        ``"global"`` (default) — stored in the OS config directory.
        ``"project"`` — stored next to the currently open ``.blend`` file;
        falls back to global scope if the file is unsaved.
    """

    def __init__(self, namespace: str, scope: str = "global") -> None:
        self._namespace = namespace
        self._scope = scope
        self._data: dict = {}
        self._auto_save: bool = False
        self._save_scheduled: bool = False
        self.load()

    def _get_data_path(self) -> pathlib.Path:
        """Resolve the JSON file path based on scope."""
        if self._scope == "project":
            try:
                import bpy

                blend_path = bpy.data.filepath
                if blend_path:
                    blend_dir = pathlib.Path(blend_path).parent
                    return blend_dir / f"puree_{self._namespace}.json"
                else:
                    logger.warning(
                        "Storage(scope='project'): .blend file is unsaved — "
                        "falling back to global scope for namespace '%s'.",
                        self._namespace,
                    )
            except Exception as exc:
                logger.warning(
                    "Storage(scope='project'): could not determine blend path "
                    "(%s) — falling back to global scope.",
                    exc,
                )

        return _get_global_config_dir() / self._namespace / "data.json"

    @property
    def auto_save(self) -> bool:
        return self._auto_save

    @auto_save.setter
    def auto_save(self, value: bool) -> None:
        self._auto_save = bool(value)

    def _schedule_save(self) -> None:
        """Schedule a debounced save via bpy.app.timers (0.5 s)."""
        if self._save_scheduled:
            return
        try:
            import bpy

            def _timer_callback():
                self._save_scheduled = False
                self.save()
                return None

            bpy.app.timers.register(_timer_callback, first_interval=0.5)
            self._save_scheduled = True
        except Exception as exc:
            logger.warning(
                "Storage._schedule_save: could not register timer (%s).", exc
            )

    def _navigate(self, keys: list[str], create: bool = False):
        """Walk nested dicts following *keys*.

        Returns ``(parent_dict, final_key)`` so the caller can read/write.
        Raises ``KeyError`` if a segment is missing and *create* is False.
        """
        node = self._data
        for key in keys[:-1]:
            if create:
                if key not in node or not isinstance(node[key], dict):
                    node[key] = {}
            node = node[key]
        return node, keys[-1]

    def get(self, key: str, default=None):
        """Return the value at *key* (dot-separated path), or *default*."""
        keys = key.split(".")
        try:
            node, final = self._navigate(keys)
            return node[final]
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value) -> None:
        """Set *value* at *key* (dot-separated path), creating intermediates."""
        keys = key.split(".")
        node, final = self._navigate(keys, create=True)
        node[final] = value
        if self._auto_save:
            self._schedule_save()

    def delete(self, key: str) -> bool:
        """Delete the entry at *key*.  Returns ``True`` if it existed."""
        keys = key.split(".")
        try:
            node, final = self._navigate(keys)
            if final in node:
                del node[final]
                if self._auto_save:
                    self._schedule_save()
                return True
            return False
        except (KeyError, TypeError):
            return False

    def clear(self) -> None:
        """Remove all data from this store (in-memory only; call save() to persist)."""
        self._data = {}
        if self._auto_save:
            self._schedule_save()

    def load(self) -> None:
        """Load data from disk.  Missing file → empty store.  Corrupt JSON → warning + empty."""
        path = self._get_data_path()
        if not path.exists():
            self._data = {}
            return
        try:
            with path.open("r", encoding="utf-8") as fh:
                self._data = json.load(fh)
            logger.debug(
                "Storage('%s'): loaded %d top-level keys from %s.",
                self._namespace,
                len(self._data),
                path,
            )
        except json.JSONDecodeError as exc:
            logger.warning(
                "Storage('%s'): JSON decode error in %s (%s) — starting fresh.",
                self._namespace,
                path,
                exc,
            )
            self._data = {}
        except OSError as exc:
            logger.warning(
                "Storage('%s'): could not read %s (%s) — starting fresh.",
                self._namespace,
                path,
                exc,
            )
            self._data = {}

    def save(self) -> bool:
        """Atomically write current data to disk.

        Returns ``True`` on success, ``False`` on failure.
        """
        path = self._get_data_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = path.with_suffix(".json.tmp")
            with tmp_path.open("w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=2, ensure_ascii=False)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_path, path)
            logger.debug("Storage('%s'): saved to %s.", self._namespace, path)
            return True
        except OSError as exc:
            logger.error(
                "Storage('%s'): failed to save to %s: %s",
                self._namespace,
                path,
                exc,
            )
            return False
