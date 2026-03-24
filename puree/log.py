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

Usage in any module:
    from .log import get_logger
    logger = get_logger(__name__)

    logger.debug("Detailed trace info")
    logger.info("General operational info")
    logger.warning("Something unexpected")
    logger.error("Something failed")

For dist/ scripts (standalone CLI):
    from puree.log import setup_cli_logging
    logger = setup_cli_logging("install")

Configuration:
    - File logs always go to <addon_root>/logs/puree.log (rotating, 5 MB max, 3 backups)
    - Console output is controlled by PUREE_DEBUG env var:
        PUREE_DEBUG=1  → console shows DEBUG and above
        PUREE_DEBUG=0  → console shows WARNING and above (default)
    - Or set programmatically: set_debug(True)
"""
import os
import logging
from logging.handlers import RotatingFileHandler

_LOG_DIR_NAME = "logs"
_LOG_FILE_NAME = "puree.log"
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
_BACKUP_COUNT = 3
_ROOT_LOGGER_NAME = "puree"

_FILE_FORMAT = "[%(asctime)s] %(levelname)-8s %(name)s: %(message)s"
_CONSOLE_FORMAT = "%(levelname)-8s %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_initialized = False
_debug_mode = None


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
            handler.setLevel(logging.DEBUG if enabled else logging.WARNING)


def _get_log_dir() -> str:
    try:
        from . import get_addon_root
        addon_root = get_addon_root()
    except (ImportError, RuntimeError):
        addon_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(addon_root, _LOG_DIR_NAME)


def _ensure_initialized():
    global _initialized
    if _initialized:
        return

    root = logging.getLogger(_ROOT_LOGGER_NAME)
    root.setLevel(logging.DEBUG)

    if root.handlers:
        _initialized = True
        return

    # File handler — always logs everything
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
    except (OSError, PermissionError):
        pass  # Can't write logs — continue with console only

    # Console handler — gated by debug flag
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if _is_debug() else logging.WARNING)
    console_handler.setFormatter(logging.Formatter(_CONSOLE_FORMAT))
    root.addHandler(console_handler)

    _initialized = True


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
    """
    Configure logging for standalone CLI scripts (dist/).

    Returns a logger with console output at INFO level and file logging.
    """
    _ensure_initialized()

    logger = logging.getLogger(f"{_ROOT_LOGGER_NAME}.cli.{name}")

    # CLI scripts always show INFO+ on console
    for handler in logging.getLogger(_ROOT_LOGGER_NAME).handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, RotatingFileHandler):
            handler.setLevel(logging.INFO)

    return logger
