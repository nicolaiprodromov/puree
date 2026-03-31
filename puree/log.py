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

All Puree output (engine, user scripts, reload events) is routed through
Python's logging module and written to a single rotating log file.

Usage in any puree module:
    from .log import get_logger
    logger = get_logger(__name__)

    logger.debug("Detailed trace info")
    logger.info("General operational info")
    logger.warning("Something unexpected")
    logger.error("Something failed")

Log destination:
    <addon_root>/logs/puree.log  (rotating, 5 MB, 3 backups)

    The addon root is wherever Blender loaded the addon from.
    With `just link` (symlinked source), that resolves to the
    source repo, so logs land in <repo>/logs/.
    In production (installed extension), logs go alongside the addon
    in the Blender extensions directory.

Console behaviour:
    Silent by default — everything goes to the log file only.
    Set PUREE_DEBUG=1 or call set_debug(True) for DEBUG+ on stderr.
    If the log file cannot be created, console falls back to ERROR+.

User script output capture:
    Wrap user script execution with capture_output() to route any
    print() / stderr writes from user code into the log file under
    the 'puree.user' logger.

TCP access:
    Send 'log_path' to the reload server (127.0.0.1:19746) to get
    the active log file path.  Use `just tail` to live-follow it.
"""

import logging
import os
import sys
from contextlib import contextmanager
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

_SILENT_LEVEL = logging.CRITICAL + 1  # effectively mutes console

_initialized = False
_debug_mode = None
_file_handler_ok = False
_log_path = None


# ── Public API ───────────────────────────────────────────────────────


def get_logger(name: str) -> logging.Logger:
    """Get a named logger under the 'puree' hierarchy.

    Typical usage::

        logger = get_logger(__name__)
    """
    _ensure_initialized()
    if not name.startswith(_ROOT_LOGGER_NAME):
        name = f"{_ROOT_LOGGER_NAME}.{name}"
    return logging.getLogger(name)


def get_log_path() -> str | None:
    """Return the absolute path to the active log file, or None if file logging failed."""
    _ensure_initialized()
    return _log_path


def set_debug(enabled: bool):
    """Enable or disable debug console output at runtime."""
    global _debug_mode
    _debug_mode = enabled
    root = logging.getLogger(_ROOT_LOGGER_NAME)
    for handler in root.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, RotatingFileHandler):
            handler.setLevel(logging.DEBUG if enabled else (_SILENT_LEVEL if _file_handler_ok else logging.ERROR))


def reinitialize():
    """Force re-initialization (e.g. after addon reload changes the addon root).

    Clears all handlers, re-resolves the log path, and writes a session
    separator so reloads are visible in the log file.
    """
    global _initialized
    _initialized = False
    _ensure_initialized()
    # Session banner — makes reload boundaries easy to find in the log
    root = logging.getLogger(_ROOT_LOGGER_NAME)
    root.info("=" * 72)
    root.info("  Puree session started  |  log: %s", _log_path or "(file logging unavailable)")
    root.info("=" * 72)


@contextmanager
def capture_output(source: str = "user"):
    """Context manager that tees stdout/stderr into the Puree log.

    Intended for wrapping user script execution so that print() and
    traceback output from script.py files are captured::

        with capture_output("user"):
            spec.loader.exec_module(module)
            module.main(self, app)

    The original streams are always restored, even on exception.
    Output is written to *both* the original stream and the log file
    so Blender's console still shows it.
    """
    _ensure_initialized()
    if not _file_handler_ok:
        yield  # nothing to capture into
        return

    user_logger = logging.getLogger(f"{_ROOT_LOGGER_NAME}.{source}")
    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout = _TeeStream(old_stdout, user_logger, logging.INFO)
    sys.stderr = _TeeStream(old_stderr, user_logger, logging.WARNING)
    try:
        yield
    finally:
        # Flush any partial line before restoring
        sys.stdout.flush()
        sys.stderr.flush()
        sys.stdout = old_stdout
        sys.stderr = old_stderr


def setup_cli_logging(name: str) -> logging.Logger:
    """Configure logging for standalone CLI scripts (dist/).

    Returns a logger with clean console output (INFO+) and file logging.
    """
    _ensure_initialized()
    logger = logging.getLogger(f"{_ROOT_LOGGER_NAME}.cli.{name}")
    for handler in logging.getLogger(_ROOT_LOGGER_NAME).handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, RotatingFileHandler):
            handler.setLevel(logging.INFO)
            handler.setFormatter(logging.Formatter(_CLI_FORMAT))
    return logger


# ── Internals ────────────────────────────────────────────────────────


def _is_debug() -> bool:
    global _debug_mode
    if _debug_mode is not None:
        return _debug_mode
    return os.environ.get("PUREE_DEBUG", "0") == "1"


def _get_log_dir() -> str:
    """Resolve log directory: <addon_root>/logs/."""
    try:
        from . import get_addon_root

        addon_root = get_addon_root()
    except (ImportError, RuntimeError):
        addon_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(addon_root, _LOG_DIR_NAME)


def _ensure_initialized():
    global _initialized, _file_handler_ok, _log_path
    if _initialized:
        return

    root = logging.getLogger(_ROOT_LOGGER_NAME)
    root.setLevel(logging.DEBUG)
    root.propagate = False  # never bubble up to root (prevents Blender duplicates)

    # Clear stale handlers from previous loads/reloads
    for h in root.handlers[:]:
        try:
            h.close()
        except Exception:
            pass
        root.removeHandler(h)

    # ── File handler (always logs everything) ────────────────────────
    _file_handler_ok = False
    _log_path = None
    try:
        log_dir = _get_log_dir()
        os.makedirs(log_dir, exist_ok=True)
        _log_path = os.path.join(log_dir, _LOG_FILE_NAME)

        file_handler = RotatingFileHandler(
            _log_path,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(_FILE_FORMAT, datefmt=_DATE_FORMAT))
        root.addHandler(file_handler)
        _file_handler_ok = True
    except Exception:
        pass  # console handler will compensate

    # ── Console handler ──────────────────────────────────────────────
    if _is_debug():
        console_level = logging.DEBUG
    elif _file_handler_ok:
        console_level = _SILENT_LEVEL
    else:
        console_level = logging.ERROR  # no file — surface errors as fallback

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(logging.Formatter(_CONSOLE_FORMAT))
    root.addHandler(console_handler)

    _initialized = True


# ── Stream capture helpers ───────────────────────────────────────────


class _TeeStream:
    """Wraps a stream so writes go to both the original stream and a logger.

    Designed as a temporary sys.stdout/stderr replacement inside
    capture_output().  All attribute access (encoding, fileno, etc.)
    is forwarded to the original stream so Blender internals aren't
    disrupted.
    """

    def __init__(self, original, logger: logging.Logger, level: int):
        self._original = original
        self._logger = logger
        self._level = level
        self._line_buf = ""

    def write(self, msg: str) -> int:
        if msg:
            self._buffer_and_log(msg)
        return len(msg) if msg else 0

    def flush(self):
        if self._line_buf.strip():
            self._logger.log(self._level, self._line_buf.rstrip())
            self._line_buf = ""

    def _buffer_and_log(self, msg: str):
        """Buffer until newlines, then emit complete lines to the logger."""
        self._line_buf += msg
        while "\n" in self._line_buf:
            line, self._line_buf = self._line_buf.split("\n", 1)
            if line.strip():
                self._logger.log(self._level, line.rstrip())

    def __getattr__(self, name):
        return getattr(self._original, name)
