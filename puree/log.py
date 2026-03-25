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
"""
Puree logging system.

Usage in any puree module:
    from .log import get_logger
    logger = get_logger(__name__)

    logger.debug("Detailed trace info")
    logger.info("General operational info")
    logger.warning("Something unexpected")
    logger.error("Something failed")

Log destination:
    <addon_root>/logs/puree.log  (rotating, 5 MB, 3 backups)

    In dev mode (just dev-link), addon_root is the source repo (via symlink),
    so logs land in <repo>/logs/.  In production (installed extension),
    logs go alongside the addon.

Console behavior:
    Silent by default — everything goes to the log file only.
    Set PUREE_DEBUG=1 or call set_debug(True) for DEBUG+ on stderr.
    If the log file cannot be created, console falls back to ERROR+.
"""
import os
import sys
import logging
from logging.handlers import RotatingFileHandler

_LOG_DIR_NAME = "logs"
_LOG_FILE_NAME = "puree.log"
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
_BACKUP_COUNT = 3
_ROOT_LOGGER_NAME = "puree"

_FILE_FORMAT = "[%(asctime)s] %(levelname)-8s %(name)s: %(message)s"
_CLI_FORMAT = "%(message)s"
_CONSOLE_FORMAT = "%(levelname)-8s %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_SILENT_LEVEL = logging.CRITICAL + 1  # Above all levels — effectively mutes console

_initialized = False
_debug_mode = None
_file_handler_ok = False


def _is_debug() -> bool:
    global _debug_mode
    if _debug_mode is not None:
        return _debug_mode
    return os.environ.get("PUREE_DEBUG", "0") == "1"


def set_debug(enabled: bool):
    """Enable or disable debug console output at runtime."""
    global _debug_mode
    _debug_mode = enabled
    root = logging.getLogger(_ROOT_LOGGER_NAME)
    for handler in root.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, RotatingFileHandler):
            handler.setLevel(logging.DEBUG if enabled else (_SILENT_LEVEL if _file_handler_ok else logging.ERROR))


def _get_log_dir() -> str:
    """Resolve log directory: <addon_root>/logs/.

    With dev-link (symlinked source), addon_root follows the symlink back
    to the repo, so logs naturally land in <repo>/logs/.
    """
    try:
        from . import get_addon_root
        addon_root = get_addon_root()
    except (ImportError, RuntimeError):
        # Fallback: assume log.py lives at <root>/puree/log.py
        addon_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(addon_root, _LOG_DIR_NAME)


def _ensure_initialized():
    global _initialized, _file_handler_ok
    if _initialized:
        return

    root = logging.getLogger(_ROOT_LOGGER_NAME)
    root.setLevel(logging.DEBUG)
    root.propagate = False  # Never bubble up to root logger (prevents Blender duplicates)

    # Always clear stale handlers from previous loads/reloads — prevents duplicates
    for h in root.handlers[:]:
        try:
            h.close()
        except Exception:
            pass
        root.removeHandler(h)

    # File handler — always logs everything
    _file_handler_ok = False
    try:
        log_dir = _get_log_dir()
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, _LOG_FILE_NAME)

        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(_FILE_FORMAT, datefmt=_DATE_FORMAT))
        root.addHandler(file_handler)
        _file_handler_ok = True
    except Exception:
        pass  # Fall through — console handler will compensate

    # Console handler — silent when file is working, ERROR fallback if file failed
    # PUREE_DEBUG=1 always enables full console output
    if _is_debug():
        console_level = logging.DEBUG
    elif _file_handler_ok:
        console_level = _SILENT_LEVEL  # File handles everything, console stays quiet
    else:
        console_level = logging.ERROR  # No file — surface errors to console as fallback

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(logging.Formatter(_CONSOLE_FORMAT))
    root.addHandler(console_handler)

    _initialized = True


def reinitialize():
    """Force re-initialization (e.g. after addon reload or log path change)."""
    global _initialized
    _initialized = False
    _ensure_initialized()


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger under the 'puree' hierarchy.

    Typical usage:
        logger = get_logger(__name__)
    """
    _ensure_initialized()
    if not name.startswith(_ROOT_LOGGER_NAME):
        name = f"{_ROOT_LOGGER_NAME}.{name}"
    return logging.getLogger(name)


def setup_cli_logging(name: str) -> logging.Logger:
    """Configure logging for standalone CLI scripts (dist/).

    Returns a logger with clean console output (INFO+) and file logging.
    """
    _ensure_initialized()

    logger = logging.getLogger(f"{_ROOT_LOGGER_NAME}.cli.{name}")

    # CLI scripts: show INFO+ on console with clean message-only format
    for handler in logging.getLogger(_ROOT_LOGGER_NAME).handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, RotatingFileHandler):
            handler.setLevel(logging.INFO)
            handler.setFormatter(logging.Formatter(_CLI_FORMAT))

    return logger
