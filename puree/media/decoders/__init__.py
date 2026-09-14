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
"""Media decoder registry - maps file extensions to MediaSource factories.

Phase 2+ decoders (svg, video, lottie) register here; everything else in
the engine dispatches through this table so adding a format is one entry.
"""

from .gif import GifSource
from .lottie import LOTTIE_EXTENSIONS, LottieSource
from .svg import SvgSource
from .video import VIDEO_EXTENSIONS, VideoSource

# extension (lower, with dot) -> source factory
# factory signature: (container_id, image_name, abs_path, image_instance)
# factories may declare an extra `block` keyword parameter to receive the
# element's image block (playback attrs) - MediaManager passes it when the
# signature asks for it (VideoSource and LottieSource do).
SOURCE_FACTORIES = {
    ".gif": GifSource,
    ".svg": SvgSource,
    # video element (MEDIA_PLAN section 5.3) - PyAV decode, bundled with
    # Puree (lazy-imported safety net); one entry per container extension
    # (.mp4/.webm/.mkv/.mov)
    **dict.fromkeys(VIDEO_EXTENSIONS, VideoSource),
    # lottie element (MEDIA_PLAN section 5.4) - rlottie-python render,
    # bundled with Puree (lazy-imported safety net). ".json" is
    # deliberately broad: LottieSource validates the document on open and
    # a non-Bodymovin .json degrades to an inert 'unsupported' source (one
    # warning, never a crash). ".lottie" zip containers are a plan
    # non-goal (v1) and not registered.
    **dict.fromkeys(LOTTIE_EXTENSIONS, LottieSource),
}

# Extensions the asset scanner must treat as media (registered as stubs,
# never loaded through bpy.data.images).
MEDIA_EXTENSIONS = tuple(sorted(SOURCE_FACTORIES.keys()))


def get_factory(extension):
    """The MediaSource factory for an extension, or None."""
    return SOURCE_FACTORIES.get(extension.lower())
