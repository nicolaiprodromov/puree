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
import socket
import threading

from .log import get_log_path, get_logger

logger = get_logger(__name__)

PUREE_RELOAD_PORT = 19746


class ReloadServer:
    def __init__(self, port=PUREE_RELOAD_PORT, reload_fn=None):
        self.port = port
        self._reload_fn = reload_fn
        self._running = False
        self._thread = None
        self._sock = None

    def start(self):
        if self._running:
            return True
        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True, name="PureeReloadServer")
        self._thread.start()
        return True

    def stop(self):
        if not self._running:
            return
        self._running = False
        # Poke the socket to unblock accept()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect(("127.0.0.1", self.port))
            s.close()
        except OSError:
            pass
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def _serve(self):
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._sock.settimeout(1.0)
            self._sock.bind(("127.0.0.1", self.port))
            self._sock.listen(1)
            logger.info("Reload server listening on 127.0.0.1:%d", self.port)
        except OSError as e:
            logger.error("Reload server failed to start: %s", e)
            self._running = False
            return

        while self._running:
            try:
                conn, _addr = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            if not self._running:
                conn.close()
                break

            try:
                data = conn.recv(256).decode("utf-8", errors="ignore").strip()
                self._handle_command(conn, data)
            except OSError:
                pass

        try:
            self._sock.close()
        except OSError:
            pass

    def _handle_command(self, conn, data: str):
        """Dispatch a single client command."""
        try:
            if data == "reload":
                conn.sendall(b"ok\n")
                conn.close()
                logger.info("Reload requested via TCP")
                self._schedule_reload()
            elif data == "ping":
                conn.sendall(b"pong\n")
                conn.close()
            elif data == "log_path":
                path = get_log_path() or ""
                conn.sendall(f"{path}\n".encode("utf-8"))
                conn.close()
            elif data == "logs" or data.startswith("logs "):
                self._send_log_tail(conn, data)
            else:
                conn.sendall(b"unknown\n")
                conn.close()
        except OSError:
            pass

    def _send_log_tail(self, conn, data: str):
        """Send the last N lines of the log file."""
        parts = data.split(None, 1)
        count = 50
        if len(parts) == 2:
            try:
                count = max(1, min(int(parts[1]), 5000))
            except ValueError:
                pass
        path = get_log_path()
        if not path:
            conn.sendall(b"(no log file)\n")
            conn.close()
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            tail = lines[-count:]
            conn.sendall("".join(tail).encode("utf-8"))
        except Exception as e:
            conn.sendall(f"(error reading log: {e})\n".encode("utf-8"))
        finally:
            conn.close()

    def _schedule_reload(self):
        """Schedule reload on Blender's main thread (thread-safe)."""
        import bpy

        if self._reload_fn:
            bpy.app.timers.register(self._reload_fn, first_interval=0.0)
