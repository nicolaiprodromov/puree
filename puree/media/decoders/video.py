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
"""Video media source (``video: clips/intro.mp4``) - PyAV decode.

PyAV (``av``) SHIPS BUNDLED with Puree core (MEDIA_PLAN section 12
decision 1, superseded 2026-07-20). It is still imported lazily inside
methods and never at module import time - a safety net for exotic
platforms / broken installs: when the package is absent the source
degrades to ``ready_state == 'unsupported'``, shows its ``poster:`` (or
nothing) and logs ONE warning per session.

Threading model (one daemon decoder thread per PLAYING video)
--------------------------------------------------------------
The thread owns its av container end to end: open -> find video stream ->
decode loop -> close (in its ``finally``). Decoded frames are converted
to bottom-up RGBA bytes and pushed into a bounded ``queue.Queue`` as
``(generation, pts_seconds, width, height, rgba_bytes)``. Backpressure:
the thread paces itself against the shared MediaClock (never decodes more
than ~250 ms ahead), waits briefly for queue space and then DROPS THE
OLDEST frame so latency stays bounded on slow machines. Seeks are
requested by the main thread (target + generation bump under a lock, an
Event as the doorbell); the thread seeks the container to the nearest
keyframe at-or-before the target and decodes forward to it. Stale queue
items (pre-seek generation) are discarded on the main thread.

Lifecycle: pausing freezes the clock, which parks the pacing loop; after
``PAUSE_GRACE_SECONDS`` the thread exits (container closed). EOF on a
non-looping video parks the thread for the same grace period (an
immediate replay reuses the warm container via a seek request), looping
videos seek back to 0 and keep decoding. ``play()``/``seek()``/``tick()``
restart a dead thread on demand. ``release()`` (called by
``MediaManager.shutdown()`` and attach-reconciliation) signals the stop
event and joins the thread (<= 1 s; it is a daemon, so a wedged join can
never hang Blender).

Main-thread tick pulls the queued frame that best matches the clock time
(dropping older ones), uploads it through the shared SRGB8_A8/RGBA8
texture helper from ``puree.media.upload`` and swaps ``instance.texture``.
A 3-texture ring keeps the last uploads alive so an in-flight draw never
loses its texture (plan section 10). Only the main thread touches gpu.

Orientation: the image overlay quad samples uv v=0 at its *bottom*, so
frames must be flipped bottom-up - same convention the Rust GIF decoder
applies at decode time. Decision: frames are converted with av's own
``frame.reformat(format='rgba')`` (no hard numpy dependency) and flipped
by :func:`flip_rgba`, which uses numpy when importable (Blender ships it;
one negative-stride copy) and falls back to pure-bytes per-row slicing
that strips the plane stride in the same O(h) pass.

Color: RGBA out of a video reformat is effectively opaque (alpha 255), so
premultiplied == straight and no premultiply pass is needed; videos that
do carry alpha (rare VP9/ProRes 4444) would show slightly wrong fringes -
accepted v1 limitation.

Audio + sync (MEDIA_PLAN section 5.3): the file's audio stream plays
through :class:`puree.media.audio.AudioTrack` (Blender's built-in ``aud``;
inert no-op outside Blender). ``has_audio`` is av-probed with the
metadata. While PLAYING and unmuted, with an audio stream, a live aud
handle and ``playback_rate == 1.0``, AUDIO IS THE MASTER CLOCK: each tick
reads ``handle.position`` and, when the MediaClock has drifted apart by
more than RESYNC_THRESHOLD_SECONDS, resyncs the clock directly to the
audio position (v1 policy) - frame selection then follows the corrected
clock. In every other state (muted / no audio / rate != 1 / aud missing
or errored) the monotonic MediaClock drives and audio is silent.
``playback_rate != 1.0`` force-mutes audio for the duration (MEDIA_PLAN
decision 4, v1): the track is stopped while the rate stays != 1.0 and
restored at the current time when it returns to 1.0 (logged once per
source). Transitions keep time continuous: play starts audio at
``clock.current_time``; pause parks the live handle (``handle.pause()``);
seek repositions it; mute stops audio while the clock continues
monotonically from the same time (no jump); unmute restarts audio at the
current time (master again); a loop wrap reseeks audio to ~0 with the
clock; ended/stop() stop the track; volume changes hit the live handle.
``release()`` (attach-reconcile and MediaManager.shutdown()) stops and
releases the track, so no audio outlives UI stop or hot reload.
"""

import os
import queue
import threading
import time
from collections import deque

try:
    from ...log import get_logger

    logger = get_logger(__name__)
except Exception:  # pragma: no cover - outside the package/Blender
    import logging

    logger = logging.getLogger(__name__)

# Audio playback (Blender's aud) - import-safe outside Blender, degrades
# to an inert no-op track when aud/the audio device is unavailable.
from ..audio import AudioTrack
from ..clock import MediaClock

# Texture upload (with the SRGB8_A8/RGBA8 probe) is shared by all media
# decoders - see puree.media.upload (get_texture_format lives there too).
from ..upload import upload_texture

# Extensions this source registers for (decoders/__init__.SOURCE_FACTORIES
# imports this and derives its VideoSource entries from it).
VIDEO_EXTENSIONS = (".mp4", ".webm", ".mkv", ".mov")

QUEUE_SIZE = 6  # decoded frames buffered ahead (bounded latency)
AHEAD_MAX_SECONDS = 0.25  # decode pacing: stay at most this far ahead of the clock
FULL_QUEUE_WAIT = 0.25  # wait this long for queue space before dropping the oldest
PAUSE_GRACE_SECONDS = 2.0  # paused/EOF-parked this long -> decoder thread exits
JOIN_TIMEOUT = 1.0  # release() join timeout (thread is a daemon regardless)
SEEK_EPSILON = 1.0 / 120.0  # display/seek slack: half a 60 fps frame
RESYNC_THRESHOLD_SECONDS = 0.08  # audio-master drift beyond this resyncs the clock
RATE_EPSILON = 1e-6  # playback_rate == 1.0 comparison slack (decision 4)

_warned_no_av = False  # one missing-dependency warning per session
_failed_paths = set()  # abs paths that already logged a probe/decode error


def _import_av():
    """Lazily import PyAV; None (plus one session-wide warning) when absent."""
    global _warned_no_av
    try:
        import av

        return av
    except ImportError:
        if not _warned_no_av:
            _warned_no_av = True
            logger.warning(
                "PyAV ('av') is unavailable - it ships bundled with Puree; refresh/reinstall "
                "the Puree extension in Blender (Preferences > Extensions) or restart Blender "
                "(video: elements show their poster: until then)"
            )
        return None


def flip_rgba(data, width, height, stride=None):
    """Flip packed RGBA scanlines bottom-up, stripping any stride padding.

    numpy path (ships with Blender's Python): one negative-stride copy.
    Pure-bytes fallback: O(h) row slices, stride-aware, no dependencies.
    """
    row = width * 4
    stride = row if stride is None else int(stride)
    if stride < row:
        raise ValueError(f"plane stride {stride} smaller than row size {row}")
    if len(data) < stride * height:
        raise ValueError(f"frame buffer too small: {len(data)} < {stride * height}")
    try:
        import numpy as np

        arr = np.frombuffer(data, dtype=np.uint8)[: stride * height]
        return arr.reshape(height, stride)[::-1, :row].tobytes()
    except ImportError:
        pass
    return b"".join(data[y * stride : y * stride + row] for y in range(height - 1, -1, -1))


def _frame_to_rgba_bottom_up(frame):
    """av.VideoFrame -> (width, height, bottom-up packed RGBA bytes)."""
    rgba = frame.reformat(format="rgba")
    plane = rgba.planes[0]
    return rgba.width, rgba.height, flip_rgba(bytes(plane), rgba.width, rgba.height, stride=plane.line_size)


def _block_attrs(block):
    """Normalized playback-attribute snapshot of an image block (reconcile key)."""
    block = block or {}
    return (
        str(block.get("poster", "") or ""),
        bool(block.get("autoplay", False)),
        bool(block.get("loop", False)),
        bool(block.get("muted", False)),
        float(block.get("volume", 1.0)),
        float(block.get("playback_rate", 1.0)),
        str(block.get("preload", "metadata") or "metadata").strip().lower(),
        bool(block.get("controls", False)),
    )


class VideoSource:
    """Per-element playback of one video file onto one ImageInstance."""

    kind = "video"

    def __init__(self, container_id, image_name, path, instance, block=None):
        self.container_id = container_id
        self.image_name = image_name  # asset key, e.g. "demo_clip.mp4" / "clips/intro.mp4"
        self.path = os.path.abspath(path)
        self.instance = instance
        self.released = False

        self._attrs_snapshot = _block_attrs(block)
        (
            self.poster,
            self.autoplay,
            self._loop,
            self.muted,  # live - set_muted() starts/stops the aud track
            self.volume,  # live 0..1 - set_volume() updates the aud handle
            self._rate,
            self.preload,
            self.controls,  # consumed by default controls in Phase 5
        ) = self._attrs_snapshot
        if self.preload not in ("none", "metadata", "auto"):
            logger.warning(f"video '{image_name}': unknown preload '{self.preload}' - using 'metadata'")
            self.preload = "metadata"

        # none|metadata|ready|unsupported|error
        self.ready_state = "none"
        self._duration = None  # float seconds once probed
        self._width = 0
        self._height = 0
        self.clock = MediaClock(duration=0.0, loop=self._loop, playback_rate=self._rate)

        # ── decoder-thread plumbing ───────────────────────────────────
        self._queue = queue.Queue(maxsize=QUEUE_SIZE)
        self._thread = None
        self._stop_event = threading.Event()  # replaced per thread start
        self._wake_event = threading.Event()  # kicks the thread out of naps
        self._seek_lock = threading.Lock()  # guards _seek_target/_generation
        self._seek_target = None  # pending seek (seconds), None when idle
        self._generation = 0  # bumped per seek; queue items carry theirs
        self._seek_display = False  # show the first post-seek frame at once
        self._pending = None  # future frame held for a later tick
        self._pause_started = None  # monotonic ts when pause began (grace)

        # ── GPU state (main thread only) ──────────────────────────────
        self._texture = None
        self._ring = deque(maxlen=3)  # keep the last 3 uploads alive (plan section 10)
        self._poster_texture = None

        # ── audio (aud) state - see the module docstring ──────────────
        self.has_audio = False  # av-probed: the container has an audio stream
        self._audio = None  # AudioTrack, created lazily on first need
        self._rate_mute_logged = False  # decision-4 suppression logged once per source
        self._last_media_time = None  # previous tick's clock time (loop-wrap detect)

        if _import_av() is None:
            self.ready_state = "unsupported"
        else:
            if self.preload in ("metadata", "auto"):
                self._probe()
            if self.preload == "auto" and self.ready_state == "metadata":
                self._decode_first_frame()

        # poster: shown until the first decoded frame replaces it (also the
        # unsupported/preload-none face of the element)
        self._show_poster_if_needed()

        if self.autoplay and self.ready_state not in ("unsupported", "error"):
            self.play()

    # ── attach() reconcile hook ──────────────────────────────────────

    def matches_block(self, block):
        """False when the YAML playback attrs changed (source gets rebuilt)."""
        return self._attrs_snapshot == _block_attrs(block)

    # ── metadata / first frame (main thread) ─────────────────────────

    @property
    def duration(self):
        """Duration in seconds, or None until metadata is known."""
        return self._duration if self._duration else None

    @property
    def seeking(self):
        """True from seek() until the post-seek frame has been displayed."""
        if self._seek_display:
            return True
        with self._seek_lock:
            return self._seek_target is not None

    @staticmethod
    def _video_stream(container):
        streams = container.streams.video
        if not streams:
            raise ValueError("no video stream")
        return streams[0]

    def _ensure_metadata(self):
        if self._duration is not None:
            return True
        return self._probe()

    def _probe(self):
        """Open the container, read duration/size, close (preload: metadata)."""
        av = _import_av()
        if av is None:
            self.ready_state = "unsupported"
            return False
        try:
            with av.open(self.path) as container:
                stream = self._video_stream(container)
                duration = None
                if stream.duration is not None and stream.time_base is not None:
                    duration = float(stream.duration * stream.time_base)
                elif container.duration is not None:
                    # container.duration is in av.time_base units (int
                    # units-per-second in older PyAV, Fraction seconds-per-unit
                    # in newer) - support both.
                    tb = getattr(av, "time_base", 1_000_000)
                    duration = container.duration / tb if isinstance(tb, int) else float(container.duration * tb)
                self._duration = max(0.0, float(duration or 0.0))
                codec = stream.codec_context
                self._width = int(getattr(codec, "width", 0) or 0)
                self._height = int(getattr(codec, "height", 0) or 0)
                # Audio presence rides the same probe (MEDIA_PLAN section 5.3)
                self.has_audio = len(container.streams.audio) > 0
            # Duration is known now - rebuild the clock in place (paused at 0;
            # playback never starts before metadata, so nothing is lost).
            rate = self.clock.playback_rate
            self.clock = MediaClock(duration=self._duration, loop=self._loop, playback_rate=rate)
            if self.ready_state == "none":
                self.ready_state = "metadata"
            logger.debug(
                f"Probed video {os.path.basename(self.path)}: {self._width}x{self._height}, {self._duration:.2f}s"
            )
            return True
        except Exception as e:
            self._set_error(f"failed to probe video '{self.image_name}': {e}")
            return False

    def _decode_first_frame(self):
        """Synchronously decode + show frame 0 (preload: auto), then close."""
        av = _import_av()
        if av is None:
            return
        try:
            with av.open(self.path) as container:
                stream = self._video_stream(container)
                for frame in container.decode(stream):
                    width, height, data = _frame_to_rgba_bottom_up(frame)
                    self._width, self._height = width, height
                    self._texture = self._upload(width, height, data)
                    self._apply_texture()
                    self.ready_state = "ready"
                    break
        except Exception as e:
            self._set_error(f"failed to decode first frame of '{self.image_name}': {e}")

    def _set_error(self, message):
        self.ready_state = "error"
        # Freeze playback immediately - a decode error can land MID-PLAY
        # (decoder thread): a still-running clock would keep the controller
        # emitting timeupdate at ~4 Hz forever (label updates -> dirty-sync
        # churn). MediaClock writes are benign cross-thread; tick()'s inert
        # branch finishes the quiesce (audio pause) on the main thread.
        try:
            self.clock.pause()
        except Exception:  # pragma: no cover - MediaClock never raises
            pass
        if self.path not in _failed_paths:
            _failed_paths.add(self.path)
            logger.error(message)

    # ── poster / texture (main thread, gpu only here) ────────────────

    def _resolve_poster(self):
        """Poster is a regular raster asset - resolved through ImageManager."""
        if not self.poster:
            return None
        try:
            from ...img_op import image_manager
        except Exception:  # bpy unavailable (headless tests)
            return None
        try:
            return image_manager.resolve(self.poster)
        except Exception:
            logger.debug(f"poster '{self.poster}' resolution failed", exc_info=True)
            return None

    def _show_poster_if_needed(self):
        if self._texture is not None:
            return
        if self._poster_texture is None:
            self._poster_texture = self._resolve_poster()
        if self._poster_texture is not None:
            self._texture = self._poster_texture
            self._apply_texture()

    def _upload(self, width, height, data):
        """Upload one RGBA frame; the shared SRGB8_A8/RGBA8 probe lives in
        puree.media.upload."""
        texture = upload_texture(width, height, data)
        self._ring.append(texture)
        return texture

    def _apply_texture(self):
        """Push the current texture onto the instance (and build its batch)."""
        instance = self.instance
        if instance is None or self._texture is None:
            return
        instance.texture = self._texture
        if instance.batch is None:
            instance._create_batch()

    # ── playback controls (main thread) ──────────────────────────────

    def play(self):
        """Start/resume playback; restarts the decoder thread when needed."""
        if self.released or self.ready_state in ("unsupported", "error"):
            if not self.released:
                # Inert guarantee: an unsupported/errored source never starts
                # its clock (no timeupdate/play events can ever fire).
                logger.debug(f"video '{self.image_name}': play() ignored - source is {self.ready_state}")
            return
        if not self._ensure_metadata():
            return
        self._pause_started = None
        was_playing = self.clock.playing
        replay = False
        if self.clock.ended:
            # HTMLMediaElement parity: play() after ended replays from 0.
            self.clock.seek(0.0)
            self._request_seek(0.0, display=False)
            self._last_media_time = None
            replay = True
        self.clock.play()
        # Audio starts at the clock position. A replay forces a fresh handle
        # (the old one may still be live when the audio stream outlasts the
        # video); a double play() on an already-running source leaves the
        # in-sync handle alone.
        if self._audio_should_play() and (replay or not was_playing):
            self._audio_align(self.clock.current_time, restart=replay)
        self._ensure_thread()
        self._wake_event.set()

    def pause(self):
        """Freeze the clock; the decoder thread parks and exits after grace.
        The audio handle pauses in place (handle.pause() - kept alive);
        play() realigns it to the clock on resume."""
        if self.released:
            return
        self._pause_started = time.monotonic()
        self.clock.pause()
        if self._audio is not None:
            self._audio.pause()

    def seek(self, seconds):
        """Jump the clock now; the thread seeks the container and decodes
        forward to the target. Works while paused too (the target frame is
        decoded, displayed, and the thread re-parks). A live audio handle
        seeks with the clock and keeps the master role afterwards."""
        if self.released or self.ready_state in ("unsupported", "error"):
            return
        if not self._ensure_metadata():
            return
        self.clock.seek(seconds)
        if self.clock.paused and self._pause_started is None:
            self._pause_started = time.monotonic()
        self._request_seek(self.clock.current_time, display=True)
        if self.clock.playing and self._audio_should_play():
            self._audio_align(self.clock.current_time)
        self._last_media_time = None  # a seek jump is not a loop wrap
        self._ensure_thread()

    def stop(self):
        """Pause, rewind to 0 and stop the decoder thread immediately."""
        if self.released:
            return
        self._pause_started = time.monotonic()
        self.clock.pause()
        self.clock.seek(0.0)
        if self._audio is not None:
            self._audio.stop()
        self._last_media_time = None
        self._stop_thread(JOIN_TIMEOUT)
        self._drain_queue()
        self._pending = None

    def set_muted(self, muted):
        """Mute/unmute live. Muting stops the track while the clock continues
        monotonically from the same time (no jump); unmuting mid-play starts
        audio at the current time, which makes it the master clock again."""
        muted = bool(muted)
        if muted == self.muted:
            return
        self.muted = muted
        if muted:
            if self._audio is not None:
                self._audio.stop()
        elif self.clock.playing and self._audio_should_play():
            self._audio_align(self.clock.current_time)

    def set_volume(self, volume):
        """Clamped 0..1; pushed onto the live audio handle immediately."""
        try:
            self.volume = min(1.0, max(0.0, float(volume)))
        except (TypeError, ValueError):
            return
        if self._audio is not None:
            self._audio.volume = self.volume

    def set_playback_rate(self, rate):
        """Feeds MediaClock.playback_rate. MEDIA_PLAN decision 4 (v1): a rate
        != 1.0 force-mutes audio - the track is stopped while the rate stays
        != 1.0 and restored at the current time once it returns to 1.0."""
        try:
            self._rate = max(0.0, float(rate))
        except (TypeError, ValueError):
            return
        self.clock.playback_rate = self._rate
        if self._rate_blocks_audio():
            if self._audio is not None:
                self._audio.stop()
        elif self.clock.playing and self._audio_should_play():
            self._audio_align(self.clock.current_time)

    def set_loop(self, loop):
        self._loop = bool(loop)
        self.clock.loop = self._loop

    def _request_seek(self, target, display):
        with self._seek_lock:
            self._generation += 1
            self._seek_target = max(0.0, float(target))
        self._pending = None
        self._seek_display = bool(display)
        self._wake_event.set()

    # ── audio (main thread) - MEDIA_PLAN section 5.3 ─────────────────

    def _rate_blocks_audio(self):
        """True while playback_rate != 1.0 (audio force-muted, decision 4).
        Logged once per source, when the suppression actually mutes audio."""
        if abs(self._rate - 1.0) <= RATE_EPSILON:
            return False
        if self.has_audio and not self.muted and not self._rate_mute_logged:
            self._rate_mute_logged = True
            logger.info(
                f"video '{self.image_name}': playback_rate != 1.0 forces mute "
                f"(v1 limitation, MEDIA_PLAN decision 4) - audio resumes at rate 1.0"
            )
        return True

    def _audio_should_play(self):
        """True when audio should be audible: the file has an audio stream,
        the source is not muted and the rate is 1.0 (decision 4). Callers
        add the clock state; aud availability is checked at the track."""
        if not self.has_audio or self.ready_state in ("unsupported", "error"):
            return False
        return not self.muted and not self._rate_blocks_audio()

    def _ensure_audio(self):
        """The AudioTrack for this source (created + opened exactly once),
        or None when audio cannot play (aud missing / open failed)."""
        if self._audio is None:
            self._audio = AudioTrack(label=self.image_name)
            self._audio.open(self.path)
        return self._audio if self._audio.available else None

    def _audio_align(self, seconds, restart=False):
        """Make audio audible at *seconds*: seek the live handle, or start a
        fresh one (AudioTrack.play stops any previous handle first)."""
        track = self._ensure_audio()
        if track is None:
            return
        if track.volume != self.volume:
            track.volume = self.volume
        if not restart and track.playing:
            track.seek(seconds)
        else:
            track.play(seconds)

    def _sync_audio(self, now):
        """Per-tick audio upkeep + master-clock sync.

        While PLAYING, unmuted, at rate 1.0, on a file with audio and with
        a live aud handle: AUDIO IS THE MASTER CLOCK - drift beyond
        RESYNC_THRESHOLD_SECONDS resyncs the MediaClock directly to
        ``handle.position`` (v1: direct resync, no slewing); the caller
        pulls frames against the corrected clock. Every other state leaves
        the monotonic clock in charge. A loop wrap (clock jumped backwards
        by more than half the duration since the last tick) restarts audio
        at the wrapped position; a non-loop end stops the track.
        """
        clock = self.clock
        if clock.ended:
            if self._audio is not None:
                self._audio.stop()
            self._last_media_time = None
            return
        if not clock.playing:
            self._last_media_time = None
            return
        if not self._audio_should_play():
            # Muted / rate != 1 / no audio stream: monotonic clock drives;
            # the transition setters already stopped any live handle.
            self._last_media_time = None
            return
        track = self._ensure_audio()
        if track is None:
            self._last_media_time = None
            return

        t = clock.current_time
        duration = self._duration or 0.0
        last = self._last_media_time
        self._last_media_time = t
        if last is not None and duration > 0.0 and t < last - duration * 0.5:
            # Loop wrap: reseek audio to ~0 with the clock (the old handle
            # normally already stopped at the audio stream's natural end).
            self._audio_align(t, restart=True)
            return
        if not track.playing:
            # No live handle: the audio stream ended before the video did (or
            # a start failed). The monotonic clock drives until the next
            # wrap/end/transition - auto-restarting here would seek past the
            # stream's end and stop again every tick.
            return
        apos = track.position
        if apos is None:
            return
        if duration > 0.0 and apos > duration - RESYNC_THRESHOLD_SECONDS:
            return  # audio at its very end - the ended/wrap logic takes over
        delta = t - apos
        if duration > 0.0 and abs(delta) > duration * 0.5:
            return  # cross-iteration mismatch - the wrap branch handles it
        if abs(delta) > RESYNC_THRESHOLD_SECONDS:
            clock.seek(apos)  # AUDIO IS MASTER - direct resync (v1)
            self._last_media_time = clock.current_time

    # ── MediaSource interface (main thread) ──────────────────────────

    def tick(self, now):
        """Advance playback; True when the visible texture changed."""
        instance = self.instance
        if self.released or instance is None:
            return False
        if instance.image_name != self.image_name:
            # Retargeted to another asset (hot reload / script update_image).
            self.release()
            return False

        changed = False
        if self.ready_state in ("unsupported", "error"):
            # Inert guarantee: unsupported/errored sources never advance or
            # emit. An error that landed mid-play (decoder thread) already
            # froze the clock in _set_error; this closes the race on the
            # main thread and parks the audio handle with it.
            if not self.clock.paused:
                self.pause()
        else:
            # Audio first: frame selection must follow the (possibly
            # audio-resynced) clock - MEDIA_PLAN section 5.3.
            self._sync_audio(now)
            frame = self._pull_frame()
            if frame is not None:
                _gen, _pts, width, height, data = frame
                self._width, self._height = width, height
                self._texture = self._upload(width, height, data)
                self._apply_texture()
                if self.ready_state != "ready":
                    self.ready_state = "ready"
                changed = True
            # Self-heal the thread: grace/EOF exits followed by a running
            # clock (e.g. play() raced the park timeout) restart it here.
            if self.clock.is_active(now) and (self._thread is None or not self._thread.is_alive()):
                self._ensure_thread()

        # Self-heal the texture: scroll/dirty-sync/hot-reload paths call
        # instance.update_all(image_name=...), which resets media textures
        # to the ImageManager stub (None) - identity check is cheap.
        if self._texture is not None and instance.texture is not self._texture:
            self._apply_texture()
            changed = True
        return changed

    def is_active(self, now=None):
        """True while playback can change the visible frame (gates redraws)."""
        if self.released or self.instance is None:
            return False
        if self.ready_state in ("unsupported", "error"):
            return False
        return self.clock.is_active(now)

    def release(self):
        """Detach and stop decoding (idempotent). Called by
        MediaManager.shutdown() and attach-reconciliation: stops the thread
        (join <= JOIN_TIMEOUT), stops + releases the audio track (no orphaned
        sound after UI stop / hot reload), drops queue/ring/textures,
        detaches the instance. The av container is closed by the thread's
        own finally."""
        self.released = True
        try:
            self.clock.pause()
        except Exception:
            pass
        if self._audio is not None:
            try:
                self._audio.release()
            except Exception:  # pragma: no cover - AudioTrack never raises
                pass
            self._audio = None
        self._stop_thread(JOIN_TIMEOUT)
        self._drain_queue()
        self._pending = None
        self._ring.clear()
        self._texture = None
        self._poster_texture = None
        self.instance = None

    # ── frame selection (main thread) ────────────────────────────────

    def _pull_frame(self):
        """The queued frame that best matches the clock time, or None.

        Newer displayable frames supersede older ones (catch-up drops), a
        future frame is held as ``_pending`` for a later tick, and stale
        generations (pre-seek) are discarded. Loop-wrap awareness: with a
        looping clock, a frame more than half the duration AHEAD belongs
        to the previous iteration (discard); more than half the duration
        BEHIND belongs to the next iteration, queued just before the clock
        wraps (hold until it does).
        """
        with self._seek_lock:
            generation = self._generation
        t = self.clock.current_time

        best = None
        pending = self._pending
        self._pending = None
        if pending is not None and pending[0] == generation:
            verdict = self._classify(pending[1], t)
            if verdict == "display":
                best = pending
            elif verdict == "hold":
                self._pending = pending

        while self._pending is None:
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                break
            if item[0] != generation:
                continue  # decoded before the last seek
            verdict = self._classify(item[1], t)
            if verdict == "display":
                best = item
            elif verdict == "hold":
                self._pending = item
            # "stale" - drop and keep draining

        if best is not None and self._seek_display:
            self._seek_display = False
        return best

    def _classify(self, pts, t):
        """'display' | 'hold' | 'stale' for a frame pts against clock time."""
        if self._seek_display:
            return "display"  # first post-seek frame shows immediately
        duration = self._duration or 0.0
        if self._loop and duration > 0.0:
            delta = pts - t
            if delta > duration * 0.5:
                return "stale"  # previous-iteration leftovers after the wrap
            if -delta > duration * 0.5:
                return "hold"  # next-iteration frame, clock not wrapped yet
        return "display" if pts <= t + SEEK_EPSILON else "hold"

    # ── decoder thread management ────────────────────────────────────

    def _ensure_thread(self):
        """Start the decoder thread if it is not running (main thread)."""
        if self.released:
            return
        if self._thread is not None and self._thread.is_alive():
            return
        stop_event = threading.Event()  # fresh per thread - a stopping old
        self._stop_event = stop_event  # thread can never be revived
        self._wake_event.set()
        with self._seek_lock:
            if self._seek_target is None:
                t = self.clock.current_time
                if t > SEEK_EPSILON:
                    self._seek_target = t  # resume decode at the clock position
        self._thread = threading.Thread(
            target=self._decode_loop,
            args=(stop_event,),
            name=f"puree-video-{os.path.basename(self.path)}",
            daemon=True,
        )
        self._thread.start()

    def _stop_thread(self, join_timeout):
        thread = self._thread
        stop_event = self._stop_event
        self._thread = None
        if thread is None or not thread.is_alive():
            return
        stop_event.set()
        self._wake_event.set()
        thread.join(join_timeout)
        if thread.is_alive():  # pragma: no cover - defensive
            logger.warning(
                f"video decoder thread for '{self.image_name}' did not stop within "
                f"{join_timeout}s (daemon - it cannot outlive Blender)"
            )

    def _drain_queue(self):
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                return

    def _seek_requested(self):
        with self._seek_lock:
            return self._seek_target is not None

    def _take_seek_target(self):
        with self._seek_lock:
            target = self._seek_target
            self._seek_target = None
            return target

    def _pause_expired(self):
        """Thread side: True once the clock has been paused past the grace."""
        if not self.clock.paused:
            return False
        started = self._pause_started
        if started is None:
            self._pause_started = time.monotonic()  # raced pause() - stamp now
            return False
        return (time.monotonic() - started) > PAUSE_GRACE_SECONDS

    # ── decoder thread body (NO gpu/bpy in here) ─────────────────────

    def _decode_loop(self, stop_event):
        """Daemon decoder thread: open -> find stream -> decode -> close."""
        av = _import_av()
        if av is None:  # pragma: no cover - play() checks before starting
            return
        container = None
        try:
            container = av.open(self.path)
            stream = self._video_stream(container)
            try:
                stream.thread_type = "AUTO"  # FFmpeg frame/slice threading
            except Exception:
                pass
            time_base = stream.time_base

            while not stop_event.is_set():
                target = self._take_seek_target()
                skip_until = None
                if target is not None:
                    self._av_seek(container, stream, target)
                    skip_until = max(0.0, target - SEEK_EPSILON)

                interrupted = False
                for frame in container.decode(stream):
                    if stop_event.is_set() or self._seek_requested():
                        interrupted = True
                        break
                    pts = frame.time
                    if pts is None:
                        pts = float(frame.pts * time_base) if (frame.pts is not None and time_base) else 0.0
                    if skip_until is not None and pts < skip_until:
                        continue  # decode-forward from the keyframe to the target
                    skip_until = None
                    width, height, data = _frame_to_rgba_bottom_up(frame)
                    if not self._deliver(stop_event, pts, width, height, data):
                        interrupted = True
                        break

                if stop_event.is_set():
                    break
                if interrupted:
                    if self._pause_expired() and not self._seek_requested():
                        break  # paused past grace - exit (play() restarts)
                    continue  # seek requested - outer loop re-seeks

                # ── EOF ──
                if self._loop:
                    self._av_seek(container, stream, 0.0)
                    continue
                if not self._park_at_eof(stop_event):
                    break  # grace passed - exit; play() starts a fresh thread
        except Exception as e:
            self._set_error(f"video decode failed for '{self.image_name}': {e}")
        finally:
            if container is not None:
                try:
                    container.close()
                except Exception:
                    pass

    @staticmethod
    def _av_seek(container, stream, target):
        """Seek to the nearest keyframe at-or-before *target* (thread side)."""
        target = max(0.0, float(target))
        try:
            if stream.time_base:
                container.seek(int(target / stream.time_base), stream=stream, backward=True, any_frame=False)
            else:  # pragma: no cover - no time base reported
                container.seek(int(target * 1_000_000), backward=True, any_frame=False)
            try:
                stream.codec_context.flush_buffers()
            except Exception:
                pass
        except Exception:
            logger.debug("av seek failed - continuing from current position", exc_info=True)

    def _deliver(self, stop_event, pts, width, height, data):
        """Queue one decoded frame (thread side); False = abandon this run.

        Pacing: naps while the frame is further ahead of the clock than
        AHEAD_MAX_SECONDS - a paused clock therefore parks the thread here
        until the grace period expires. Delivery: waits up to
        FULL_QUEUE_WAIT for queue space, then drops the OLDEST queued frame
        and retries, keeping latency bounded on slow machines.
        """
        with self._seek_lock:
            generation = self._generation

        duration = self._duration or 0.0
        while not stop_event.is_set() and not self._seek_requested():
            if self._pause_expired():
                return False
            ahead = pts - self.clock.current_time
            if self._loop and duration > 0.0 and ahead < -duration * 0.5:
                # Next-iteration frame (decoded past EOF before the clock
                # wraps): its real distance is "time left until the wrap".
                ahead += duration
            if ahead <= AHEAD_MAX_SECONDS or self._seek_display:
                break
            self._wake_event.clear()
            self._wake_event.wait(min(0.1, max(0.01, ahead - AHEAD_MAX_SECONDS)))
        if stop_event.is_set() or self._seek_requested():
            return False

        item = (generation, pts, width, height, data)
        deadline = time.monotonic() + FULL_QUEUE_WAIT
        while not stop_event.is_set():
            try:
                self._queue.put_nowait(item)
                return True
            except queue.Full:
                if self._seek_requested() or self._pause_expired():
                    return False
                if time.monotonic() >= deadline:
                    try:
                        self._queue.get_nowait()  # DROP OLDEST, then retry
                    except queue.Empty:
                        pass
                    continue
                time.sleep(0.01)
        return False

    def _park_at_eof(self, stop_event):
        """Non-loop EOF: idle until a seek arrives (True - keep the warm
        container) or the grace period passes (False - exit the thread)."""
        parked_at = time.monotonic()
        while not stop_event.is_set():
            if self._seek_requested():
                return True
            if time.monotonic() - parked_at > PAUSE_GRACE_SECONDS:
                return False
            self._wake_event.clear()
            self._wake_event.wait(0.1)
        return False
