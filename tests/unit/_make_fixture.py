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
"""Deterministic A/V test fixture generator (audio-sync tests).

``ensure_tone_video()`` builds ``tests/unit/fixtures/tone_video.mp4`` on
first use when missing: ~3 s of 64x64 h264 (solid color ramping red->blue
per frame) plus a mono 440 Hz sine tone as AAC - a tiny (~35 KB) real
container WITH an audio stream, which none of the committed demo assets
have (assets/demo_clip.mp4 is video-only). The file is generated, not
committed; delete it any time to regenerate.

Requires ``av`` + ``numpy`` (both dev-installed; the callers already skip
when ``av`` is missing).
"""

import math
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
TONE_VIDEO = FIXTURES_DIR / "tone_video.mp4"

DURATION_SECONDS = 3.0
WIDTH = HEIGHT = 64
FPS = 30
SAMPLE_RATE = 44100
TONE_HZ = 440.0


def ensure_tone_video(path=TONE_VIDEO):
    """Return the fixture path, generating the file first when missing."""
    path = Path(path)
    if path.exists() and path.stat().st_size > 0:
        return path

    import av
    import numpy as np

    path.parent.mkdir(parents=True, exist_ok=True)
    with av.open(str(path), mode="w") as container:
        video = container.add_stream("h264", rate=FPS)
        video.width, video.height = WIDTH, HEIGHT
        video.pix_fmt = "yuv420p"
        video.options = {"crf": "30", "preset": "ultrafast"}
        audio = container.add_stream("aac", rate=SAMPLE_RATE, layout="mono")

        total_frames = int(DURATION_SECONDS * FPS)
        for i in range(total_frames):
            rgb = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
            ramp = int(255 * i / max(1, total_frames - 1))
            rgb[..., 0] = ramp  # red ramps up ...
            rgb[..., 1] = 64
            rgb[..., 2] = 255 - ramp  # ... blue ramps down (frame index visible)
            frame = av.VideoFrame.from_ndarray(rgb, format="rgb24").reformat(format="yuv420p")
            for packet in video.encode(frame):
                container.mux(packet)
        for packet in video.encode():  # flush
            container.mux(packet)

        samples_total = int(DURATION_SECONDS * SAMPLE_RATE)
        chunk = 1024  # matches the AAC encoder frame size
        cursor = 0
        while cursor < samples_total:
            n = min(chunk, samples_total - cursor)
            t = np.arange(cursor, cursor + n) / SAMPLE_RATE
            tone = (0.4 * np.sin(2.0 * math.pi * TONE_HZ * t) * 32767.0).astype(np.int16)
            aframe = av.AudioFrame.from_ndarray(tone.reshape(1, -1), format="s16", layout="mono")
            aframe.sample_rate = SAMPLE_RATE
            aframe.pts = cursor
            for packet in audio.encode(aframe):
                container.mux(packet)
            cursor += n
        for packet in audio.encode():  # flush
            container.mux(packet)
    return path
