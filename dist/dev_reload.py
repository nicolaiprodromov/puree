#!/usr/bin/env python3
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
Trigger a full addon reload in a running Blender instance.

Primary: connects to Puree's built-in reload server (TCP 127.0.0.1:19746).
Fallback: writes a sentinel file that the Puree timer picks up.
"""
import socket
import sys
import time
from pathlib import Path

RELOAD_PORT = 19746
SENTINEL = Path(__file__).resolve().parent.parent / ".puree_reload"


def reload_via_tcp():
    """Send reload command over TCP. Returns True on success."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3.0)
        s.connect(("127.0.0.1", RELOAD_PORT))
        s.sendall(b"reload")
        resp = s.recv(64).decode("utf-8", errors="ignore").strip()
        s.close()
        return resp == "ok"
    except (ConnectionRefusedError, OSError, socket.timeout):
        return False


def reload_via_sentinel():
    """Write sentinel file for timer-based fallback."""
    SENTINEL.write_text(str(time.time()))
    return True


def main():
    if reload_via_tcp():
        print("[Puree] ✓ Reload triggered (via reload server)")
        return True

    print("[Puree] Reload server not reachable, using sentinel fallback...")
    reload_via_sentinel()
    print("[Puree] ✓ Sentinel written — Blender will pick this up within ~2s")
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
