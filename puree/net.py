"""
puree.net — Built-in HTTP client with SSE streaming.

Usage::

    from puree.net import http, sse

    # Simple GET
    http.get("https://api.example.com/models",
        headers={"Authorization": f"Bearer {key}"},
        on_success=lambda resp: update_model_list(resp.json()),
        on_error=lambda err: show_error(str(err)))

    # POST with JSON body
    http.post("https://api.example.com/chat",
        json={"messages": msgs},
        on_success=handle_response,
        on_error=handle_error)

    # SSE streaming
    stream = sse.connect("https://api.example.com/stream",
        method="POST",
        json={"messages": msgs, "stream": True},
        headers={"Authorization": f"Bearer {key}"},
        on_chunk=lambda event: append_text(event.data),
        on_done=lambda: finalize_message(),
        on_error=lambda err: show_error(str(err)))

    # Cancel an in-flight stream
    stream.cancel()

Callbacks are always delivered on the main Blender thread via a queue
drained every 50 ms by a bpy.app.timers interval.
"""

import json as _json
import threading
import collections
import concurrent.futures
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Callable, Optional

from .log import get_logger

logger = get_logger(__name__)

_callback_queue: collections.deque = collections.deque()


@dataclass
class HttpResponse:
    """Wraps a completed HTTP response."""

    status_code: int
    headers: dict
    _body: bytes

    def json(self):
        """Deserialise the response body as JSON."""
        return _json.loads(self._body)

    @property
    def text(self) -> str:
        """Decode the response body as UTF-8 text."""
        return self._body.decode("utf-8", errors="replace")

    @property
    def ok(self) -> bool:
        """True when the status code is 2xx."""
        return 200 <= self.status_code < 300

    def __repr__(self) -> str:
        return f"<HttpResponse status={self.status_code} ok={self.ok} len={len(self._body)}>"


@dataclass
class SSEEvent:
    """A single server-sent event dispatched from the stream."""

    event: str = "message"
    data: str = ""
    id: str = ""

    def __repr__(self) -> str:
        return f"<SSEEvent event={self.event!r} id={self.id!r} data={self.data!r}>"


class SSEStream:
    """
    Handle for an active SSE connection.

    Call :meth:`cancel` to abort the stream early.
    """

    def __init__(self) -> None:
        self._stop_event = threading.Event()

    def cancel(self) -> None:
        """Signal the streaming thread to stop after the current read."""
        self._stop_event.set()
        logger.debug("SSEStream.cancel() called")

    @property
    def cancelled(self) -> bool:
        """True once :meth:`cancel` has been called."""
        return self._stop_event.is_set()


class HttpError(Exception):
    """Raised when the server returns a non-2xx response."""

    def __init__(self, status_code: int, reason: str, body: bytes = b"") -> None:
        super().__init__(f"HTTP {status_code}: {reason}")
        self.status_code = status_code
        self.reason = reason
        self.body = body

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


class HttpClient:
    """
    Thin async HTTP client backed by a thread pool.

    Responses are delivered via *on_success* / *on_error* callbacks that are
    always invoked on the main Blender thread (through *_callback_queue*).
    """

    def __init__(self, max_workers: int = 4) -> None:
        self._pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="puree-http",
        )

    def get(
        self,
        url: str,
        *,
        headers: Optional[dict] = None,
        on_success: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
        timeout: float = 30,
    ) -> concurrent.futures.Future:
        """Issue a GET request in the background."""
        return self._submit(
            "GET",
            url,
            headers=headers,
            on_success=on_success,
            on_error=on_error,
            timeout=timeout,
        )

    def post(
        self,
        url: str,
        *,
        json: Optional[dict] = None,
        data=None,
        headers: Optional[dict] = None,
        on_success: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
        timeout: float = 30,
    ) -> concurrent.futures.Future:
        """Issue a POST request in the background."""
        return self._submit(
            "POST",
            url,
            json_data=json,
            data=data,
            headers=headers,
            on_success=on_success,
            on_error=on_error,
            timeout=timeout,
        )

    def shutdown(self) -> None:
        """Shut down the thread pool.  Called automatically on addon unregister."""
        logger.debug("HttpClient.shutdown() called")
        self._pool.shutdown(wait=False)

    def _submit(
        self,
        method,
        url,
        *,
        json_data=None,
        data=None,
        headers=None,
        on_success=None,
        on_error=None,
        timeout=30,
    ):
        future = self._pool.submit(
            self._worker,
            method,
            url,
            json_data,
            data,
            headers,
            on_success,
            on_error,
            timeout,
        )
        return future

    def _worker(
        self, method, url, json_data, data, headers, on_success, on_error, timeout
    ):
        try:
            response = _do_request(
                method,
                url,
                json_data=json_data,
                data=data,
                headers=headers,
                timeout=timeout,
            )
            if on_success is not None:
                _callback_queue.append((on_success, response))
        except Exception as exc:
            logger.warning("http.%s %s failed: %s", method.lower(), url, exc)
            if on_error is not None:
                _callback_queue.append((on_error, exc))


class SSEClient:
    """
    SSE (Server-Sent Events) client.

    Each :meth:`connect` call spawns a dedicated daemon thread that reads the
    response line-by-line and pushes parsed :class:`SSEEvent` objects onto the
    shared callback queue for delivery on the main thread.
    """

    def connect(
        self,
        url: str,
        *,
        method: str = "GET",
        json: Optional[dict] = None,
        headers: Optional[dict] = None,
        on_chunk: Optional[Callable] = None,
        on_done: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
        timeout: float = 0,
    ) -> SSEStream:
        """Open an SSE connection and return an :class:`SSEStream` handle."""
        stream = SSEStream()
        t = threading.Thread(
            target=self._stream_worker,
            args=(
                stream,
                url,
                method,
                json,
                headers,
                on_chunk,
                on_done,
                on_error,
                timeout,
            ),
            daemon=True,
            name=f"puree-sse-{url[:40]}",
        )
        t.start()
        logger.debug("SSE stream started: %s %s", method, url)
        return stream

    def _stream_worker(
        self,
        stream,
        url,
        method,
        json_data,
        headers,
        on_chunk,
        on_done,
        on_error,
        timeout,
    ):
        try:
            merged_headers = {
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache",
            }
            if headers:
                merged_headers.update(headers)

            req = urllib.request.Request(url, headers=merged_headers, method=method)

            if json_data is not None:
                body = _json.dumps(json_data).encode("utf-8")
                req.add_header("Content-Type", "application/json")
                req.data = body

            open_kwargs = {}
            if timeout:
                open_kwargs["timeout"] = timeout

            with urllib.request.urlopen(req, **open_kwargs) as response:
                self._read_sse(stream, response, on_chunk)

            if not stream.cancelled:
                if on_done is not None:
                    _callback_queue.append((on_done, None))
                logger.debug("SSE stream finished cleanly: %s", url)

        except urllib.error.HTTPError as exc:
            body = b""
            try:
                body = exc.read()
            except Exception:
                pass
            err = HttpError(exc.code, exc.reason, body)
            logger.warning("SSE HTTPError %s %s: %s", method, url, err)
            if on_error is not None:
                _callback_queue.append((on_error, err))

        except urllib.error.URLError as exc:
            logger.warning("SSE URLError %s %s: %s", method, url, exc.reason)
            if on_error is not None:
                _callback_queue.append((on_error, exc))

        except Exception as exc:
            logger.warning("SSE unexpected error %s %s: %s", method, url, exc)
            if on_error is not None:
                _callback_queue.append((on_error, exc))

    @staticmethod
    def _read_sse(stream: SSEStream, response, on_chunk: Optional[Callable]) -> None:
        """Parse SSE lines from *response* and push events onto the callback queue."""
        event_type = "message"
        data_lines: list = []
        event_id = ""

        for raw_line in response:
            if stream._stop_event.is_set():
                logger.debug("SSE stream cancelled mid-read")
                break

            line = raw_line.decode("utf-8", errors="replace").rstrip("\n\r")

            if line.startswith(":"):
                continue

            if line == "":
                if data_lines:
                    event = SSEEvent(
                        event=event_type,
                        data="\n".join(data_lines),
                        id=event_id,
                    )
                    if on_chunk is not None:
                        _callback_queue.append((on_chunk, event))
                event_type = "message"
                data_lines = []
                event_id = ""
                continue

            if line.startswith("event:"):
                event_type = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data_lines.append(line[len("data:") :].strip())
            elif line.startswith("id:"):
                event_id = line[len("id:") :].strip()


def _do_request(
    method: str,
    url: str,
    *,
    json_data=None,
    data=None,
    headers: Optional[dict] = None,
    timeout: float = 30,
) -> HttpResponse:
    """Synchronous HTTP request.  Runs inside a worker thread."""
    req = urllib.request.Request(url, headers=headers or {}, method=method)

    if json_data is not None:
        body = _json.dumps(json_data).encode("utf-8")
        req.add_header("Content-Type", "application/json")
        req.data = body
    elif data is not None:
        req.data = data if isinstance(data, bytes) else data.encode("utf-8")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            return HttpResponse(
                status_code=resp.status,
                headers=dict(resp.headers),
                _body=body,
            )
    except urllib.error.HTTPError as exc:
        body = b""
        try:
            body = exc.read()
        except Exception:
            pass
        raise HttpError(exc.code, exc.reason, body) from exc
    except urllib.error.URLError as exc:
        raise HttpError(0, str(exc.reason), b"") from exc


def _drain_callbacks() -> None:
    """
    Drain the shared callback queue.

    Called from the main Blender thread via a bpy.app.timers interval so that
    all *on_success* / *on_error* / *on_chunk* / *on_done* callbacks are
    safely executed on the main thread.
    """
    while _callback_queue:
        try:
            callback, arg = _callback_queue.popleft()
            if callback is not None:
                if arg is None:
                    callback()
                else:
                    callback(arg)
        except Exception as exc:
            logger.error("Callback error: %s", exc, exc_info=True)


_drain_handle = None


def register() -> None:
    """Start the callback drain timer.  Called from ``puree.__init__.register()``."""
    from .timers import set_interval

    global _drain_handle
    _drain_handle = set_interval(_drain_callbacks, 50)
    logger.debug("net.register(): drain timer started (handle=%s)", _drain_handle.id)


def unregister() -> None:
    """Stop the callback drain timer.  Called from ``puree.__init__.unregister()``."""
    global _drain_handle
    if _drain_handle is not None:
        from .timers import clear

        clear(_drain_handle)
        logger.debug("net.unregister(): drain timer stopped")
        _drain_handle = None
    http.shutdown()


http = HttpClient()
sse = SSEClient()
