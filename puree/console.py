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
Puree developer console.

Provides a browser-style console object for logging messages from
user scripts.  Messages are displayed in the debug panel's Console tab.

Usage:
    from puree.console import console

    console.log("hello", 42, {"key": "value"})
    console.warn("something looks off")
    console.error("failed to load asset")
    console.clear()
"""

import time
from collections import deque

_MAX_MESSAGES = 500
_messages = deque(maxlen=_MAX_MESSAGES)


def _format_args(*args):
    """Join all arguments into a single display string."""
    parts = []
    for a in args:
        parts.append(str(a))
    return " ".join(parts)


class _Console:
    """Singleton console exposed to user scripts."""

    @staticmethod
    def log(*args):
        _messages.appendleft((time.monotonic(), "LOG", _format_args(*args)))

    @staticmethod
    def warn(*args):
        _messages.appendleft((time.monotonic(), "WARN", _format_args(*args)))

    @staticmethod
    def error(*args):
        _messages.appendleft((time.monotonic(), "ERROR", _format_args(*args)))

    @staticmethod
    def info(*args):
        _messages.appendleft((time.monotonic(), "INFO", _format_args(*args)))

    @staticmethod
    def clear():
        _messages.clear()


console = _Console()
