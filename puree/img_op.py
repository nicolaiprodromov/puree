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
import difflib
import os

import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Matrix

from .log import get_logger
from .media import MEDIA_EXTENSIONS

logger = get_logger(__name__)

_image_instances = []
_draw_handle = None
_cached_viewport_height = None

# Raster formats, loaded eagerly through bpy.data.images + gpu.texture.from_image.
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tga", ".webp")
# Full asset-scan whitelist: rasters + every registered media format
# (puree.media MEDIA_EXTENSIONS, derived from the decoder registry:
# .gif/.svg on img:, .mp4/.webm/.mkv/.mov on video:). Media formats never
# load through bpy.data.images - the scan registers them as stubs and
# MediaManager supplies their textures per frame.
SCAN_EXTENSIONS = tuple(dict.fromkeys(IMAGE_EXTENSIONS + MEDIA_EXTENSIONS))


def _same_filepath(filepath_a, filepath_b):
    """True when two image filepaths point at the same file on disk."""
    try:
        a = os.path.normcase(os.path.normpath(bpy.path.abspath(filepath_a)))
        b = os.path.normcase(os.path.normpath(bpy.path.abspath(filepath_b)))
        return a == b
    except Exception:
        return False


class ImageManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.images = {}
            self.textures = {}
            self._bpy_images = {}  # image key -> bpy.types.Image datablock
            self._media_keys = set()  # keys registered as media stubs (.gif/.svg/video, ...)
            self._warned_missing = set()  # names already reported by resolve()
            self._try_load_images()
            self._initialized = True

    def _try_load_images(self):
        """Load images only when bpy.data is available (not during restricted context)."""
        try:
            _ = bpy.data.images
            self._load_images()
        except AttributeError:
            logger.debug("bpy.data not yet available — deferring image load")
            bpy.app.timers.register(self._deferred_load, first_interval=0.1)

    def _deferred_load(self):
        try:
            _ = bpy.data.images
            self._load_images()
        except AttributeError:
            return 0.2  # retry
        return None  # done

    def _load_images(self):
        from . import get_addon_root

        addon_assets_path = os.path.join(get_addon_root(), "assets")
        if not os.path.isdir(addon_assets_path):
            return
        for dirpath, _dirs, filenames in os.walk(addon_assets_path):
            for image_file in sorted(filenames):
                if not image_file.lower().endswith(SCAN_EXTENSIONS):
                    continue
                image_path = os.path.join(dirpath, image_file)
                # Key by path relative to assets/, posix-style, WITH extension:
                # "loggoui2.png", "icons/play.png"
                image_key = os.path.relpath(image_path, addon_assets_path).replace(os.sep, "/")

                # Media formats (gif/svg/video, ...) can't go through
                # bpy.data.images - register a stub so resolve()/
                # get_available_images()/operator enums know the asset;
                # MediaManager supplies the texture.
                if os.path.splitext(image_file)[1].lower() in MEDIA_EXTENSIONS:
                    self.images[image_key] = image_path
                    self.textures[image_key] = None
                    self._media_keys.add(image_key)
                    continue

                try:
                    # Reuse the datablock we already loaded for this key, if alive
                    bpy_image = self._bpy_images.get(image_key)
                    if bpy_image is not None:
                        try:
                            _ = bpy_image.name
                        except ReferenceError:
                            bpy_image = None
                    if bpy_image is None:
                        existing = bpy.data.images.get(image_file)
                        if existing is not None and _same_filepath(existing.filepath, image_path):
                            bpy_image = existing
                        else:
                            # New file — or a subdir file whose basename collides
                            # with an already-loaded image; load() auto-uniquifies
                            # the datablock name, so keep the returned reference.
                            bpy_image = bpy.data.images.load(image_path)

                    bpy_image.alpha_mode = "PREMUL"

                    texture = gpu.texture.from_image(bpy_image)
                    self.images[image_key] = image_path
                    self.textures[image_key] = texture
                    self._bpy_images[image_key] = bpy_image
                except Exception as e:
                    logger.error(f"Failed to load image {image_key}: {e}")

    def get_texture(self, image_name):
        return self.textures.get(image_name, None)

    def resolve(self, image_name):
        """Resolve an ``img:`` value (full filename incl. extension) to a texture.

        Returns the GPUTexture, or None on a miss. Each unique missing name is
        reported once with an actionable error (extension hint or close-match
        suggestions) — never per frame. Registered media assets (.gif/.svg/
        video, ...) return None silently: they are stubs whose texture
        arrives per-frame through MediaManager, not missing assets.
        """
        if not image_name:
            return None
        image_key = str(image_name).replace("\\", "/")
        if image_key in self.textures:
            return self.textures[image_key]
        if image_key not in self._warned_missing:
            self._warned_missing.add(image_key)
            logger.error(self._miss_message(image_key))
        return None

    def is_media(self, image_name):
        """True when the name is a registered media asset (texture via MediaManager)."""
        if not image_name:
            return False
        return str(image_name).replace("\\", "/") in self._media_keys

    def _miss_message(self, image_key):
        known = sorted(self.textures.keys())

        def _or_join(names):
            return " or ".join(names)

        if not os.path.splitext(image_key)[1]:
            stem_matches = [
                k
                for k in known
                if os.path.splitext(k)[0] == image_key or os.path.splitext(os.path.basename(k))[0] == image_key
            ]
            if stem_matches:
                return (
                    f"img: '{image_key}' has no extension - did you mean {_or_join(stem_matches)}? "
                    f"(img: values require the full filename, e.g. img: logo.png)"
                )
        close = difflib.get_close_matches(image_key, known, n=3, cutoff=0.5)
        if close:
            return f"img: '{image_key}' not found in assets/ - did you mean {_or_join(close)}?"
        return f"img: '{image_key}' not found in assets/ - available: {', '.join(known) if known else 'none'}"

    def get_available_images(self):
        return list(self.images.keys())

    def unload_images(self):
        for image_name in list(self.images.keys()):
            try:
                # Remove by datablock reference — names may have been
                # auto-uniquified on basename collisions (e.g. "play.png.001")
                bpy_image = self._bpy_images.get(image_name)
                if bpy_image is not None:
                    bpy.data.images.remove(bpy_image)
            except Exception as e:
                logger.error(f"Failed to remove image {image_name}: {e}")

        self.textures.clear()
        self.images.clear()
        self._bpy_images.clear()
        self._media_keys.clear()
        self._warned_missing.clear()

    def reload_images(self):
        """Reload all images - used when addon is re-enabled without Blender restart"""
        self.unload_images()
        self._load_images()

    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance - used during addon unregister"""
        if cls._instance is not None:
            if cls._instance._initialized:
                cls._instance.unload_images()
            cls._instance = None


image_manager = ImageManager()

# Shared shader cache - compiled once and reused by all instances
_image_shader_with_opacity = None


def get_image_shader_with_opacity():
    """Get or create the shared image shader that supports opacity"""
    global _image_shader_with_opacity

    if _image_shader_with_opacity is None:
        vert_src = """
void main()
{
    uvInterp = texCoord;
    gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
}
"""
        frag_src = """
void main()
{
    vec4 texColor = texture(image, uvInterp);
    fragColor = vec4(texColor.rgb * opacity, texColor.a * opacity);
}
"""
        shader_info = gpu.types.GPUShaderCreateInfo()
        shader_info.vertex_in(0, "VEC2", "pos")
        shader_info.vertex_in(1, "VEC2", "texCoord")
        shader_info.push_constant("MAT4", "ModelViewProjectionMatrix")
        shader_info.sampler(0, "FLOAT_2D", "image")
        shader_info.push_constant("FLOAT", "opacity")

        iface = gpu.types.GPUStageInterfaceInfo("img_opacity_iface")
        iface.smooth("VEC2", "uvInterp")
        shader_info.vertex_out(iface)
        shader_info.fragment_out(0, "VEC4", "fragColor")

        shader_info.vertex_source(vert_src)
        shader_info.fragment_source(frag_src)

        _image_shader_with_opacity = gpu.shader.create_from_info(shader_info)
        del shader_info
        del iface

    return _image_shader_with_opacity


class ImageInstance:
    def __init__(
        self,
        container_id,
        image_name=None,
        pos=[50, 50],
        size=[100, 100],
        mask=None,
        aspect_ratio=True,
        align_h="LEFT",
        align_v="TOP",
        opacity=1.0,
    ):
        self.id = len(_image_instances)
        self.container_id = container_id
        self.image_name = image_name
        self.texture = image_manager.resolve(self.image_name) if self.image_name else None
        self.position = pos
        self.size = size
        self.mask = mask
        self.clip = None  # Separate scissor rect [x, y, w, h] for scroll clipping
        self.aspect_ratio = aspect_ratio
        self.align_h = align_h
        self.align_v = align_v
        self.opacity = max(0.0, min(1.0, opacity))  # Clamp between 0 and 1
        self.shader = get_image_shader_with_opacity()  # Use shared shader
        self.batch = None
        self._create_batch()

    def _create_batch(self):
        if self.texture:
            vertices = [(0, 0), (1, 0), (1, 1), (0, 1)]
            uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]
            indices = [(0, 1, 2), (0, 2, 3)]
            self.batch = batch_for_shader(self.shader, "TRIS", {"pos": vertices, "texCoord": uvs}, indices=indices)

    def get_display_size(self):
        if not self.aspect_ratio or not self.texture:
            return self.size

        tex_width = self.texture.width
        tex_height = self.texture.height

        if tex_width == 0 or tex_height == 0:
            return self.size

        tex_aspect = tex_width / tex_height
        target_width, target_height = self.size
        target_aspect = target_width / target_height

        if tex_aspect > target_aspect:
            actual_width = target_width
            actual_height = target_width / tex_aspect
        else:
            actual_width = target_height * tex_aspect
            actual_height = target_height

        return [actual_width, actual_height]

    def update_image(self, new_image_name):
        if new_image_name in image_manager.get_available_images():
            self.image_name = new_image_name
            self.texture = image_manager.get_texture(new_image_name)
            self._create_batch()
            self._trigger_redraw()

    def update_size(self, new_size):
        self.size = [max(1, min(2000, new_size[0])), max(1, min(2000, new_size[1]))]
        self._trigger_redraw()

    def update_position(self, new_pos):
        self.position = list(new_pos)
        self._trigger_redraw()

    def update_mask(self, new_mask):
        self.mask = new_mask
        self._trigger_redraw()

    def update_aspect_ratio(self, new_aspect_ratio):
        self.aspect_ratio = new_aspect_ratio
        self._trigger_redraw()

    def update_opacity(self, new_opacity):
        self.opacity = max(0.0, min(1.0, new_opacity))
        self._trigger_redraw()

    def update_all(
        self,
        image_name=None,
        size=None,
        pos=None,
        mask=None,
        clip=None,
        aspect_ratio=None,
        align_h=None,
        align_v=None,
        opacity=None,
    ):
        if image_name is not None and image_name in image_manager.get_available_images():
            self.image_name = image_name
            self.texture = image_manager.get_texture(image_name)
            self._create_batch()
        if size is not None:
            self.size = [max(1, min(2000, size[0])), max(1, min(2000, size[1]))]
        if pos is not None:
            self.position = list(pos)
        if mask is not None:
            self.mask = mask
        if clip is not None:
            self.clip = clip
        if aspect_ratio is not None:
            self.aspect_ratio = aspect_ratio
        if align_h is not None:
            self.align_h = align_h
        if align_v is not None:
            self.align_v = align_v
        if opacity is not None:
            self.opacity = max(0.0, min(1.0, opacity))
        self._trigger_redraw()

    def _trigger_redraw(self):
        from .space_config import get_target_space

        target_space = get_target_space()
        for area in bpy.context.screen.areas:
            if area.type == target_space:
                area.tag_redraw()


def draw_all_images():
    global _cached_viewport_height

    if _cached_viewport_height is None:
        from .space_config import get_target_space

        target_space = get_target_space()
        for area in bpy.context.screen.areas:
            if area.type == target_space:
                for region in area.regions:
                    if region.type == "WINDOW":
                        _cached_viewport_height = region.height
                        break
                break

    viewport_height = _cached_viewport_height or 0

    # Fullscreen presentation mode (FULLSCREEN_PLAN Phase A): only the
    # active subtree's instances draw (the manager retargeted them to the
    # private layout); everything else stays hidden behind the backdrop.
    # None = inactive = the zero-cost pre-fullscreen path.
    from .fullscreen import fullscreen_manager

    fs_visible = fullscreen_manager.visible_instance_ids()

    saved_blend = gpu.state.blend_get()
    gpu.state.blend_set("ALPHA_PREMULT")

    for instance in _image_instances:
        if not instance.texture or not instance.batch:
            continue
        if fs_visible is not None and instance.container_id not in fs_visible:
            continue

        scissor_rect = None
        if instance.mask and instance.mask[2] > 0 and instance.mask[3] > 0:
            scissor_rect = [float(v) for v in instance.mask]
        # Intersect with the scroll-area clip (scissor duty) — the mask keeps
        # its alignment duty at the scrolled content position.
        if instance.clip is not None and instance.clip[2] > 0 and instance.clip[3] > 0:
            if scissor_rect is None:
                scissor_rect = [float(v) for v in instance.clip]
            else:
                ix = max(scissor_rect[0], float(instance.clip[0]))
                iy = max(scissor_rect[1], float(instance.clip[1]))
                ir = min(scissor_rect[0] + scissor_rect[2], float(instance.clip[0]) + float(instance.clip[2]))
                ib = min(scissor_rect[1] + scissor_rect[3], float(instance.clip[1]) + float(instance.clip[3]))
                scissor_rect = [ix, iy, max(0.0, ir - ix), max(0.0, ib - iy)]

        if scissor_rect is not None:
            xmin = scissor_rect[0]
            ymin = viewport_height - scissor_rect[1] - scissor_rect[3]
            gpu.state.scissor_test_set(True)
            gpu.state.scissor_set(int(xmin), int(ymin), int(scissor_rect[2]), int(scissor_rect[3]))

        display_size = instance.get_display_size()

        x_pos = instance.position[0]
        y_pos = instance.position[1]

        if instance.mask and instance.mask[2] > 0 and instance.mask[3] > 0:
            container_width = instance.mask[2]
            container_height = instance.mask[3]

            if instance.align_h == "LEFT":
                x_pos = instance.mask[0]
            elif instance.align_h == "CENTER":
                x_pos = instance.mask[0] + (container_width - display_size[0]) / 2
            elif instance.align_h == "RIGHT":
                x_pos = instance.mask[0] + container_width - display_size[0]

            if instance.align_v == "TOP":
                y_pos = instance.mask[1]
            elif instance.align_v == "CENTER":
                y_pos = instance.mask[1] + (container_height - display_size[1]) / 2
            elif instance.align_v == "BOTTOM":
                y_pos = instance.mask[1] + container_height - display_size[1]

        flipped_y = viewport_height - y_pos - display_size[1]

        scale_matrix = Matrix.Diagonal((display_size[0], display_size[1], 1.0, 1.0))
        translation_matrix = Matrix.Translation((x_pos, flipped_y, 0))

        matrix = gpu.matrix.get_projection_matrix()
        matrix = matrix @ translation_matrix @ scale_matrix

        instance.shader.bind()
        instance.shader.uniform_sampler("image", instance.texture)
        instance.shader.uniform_float("opacity", instance.opacity)

        gpu.matrix.push_projection()
        gpu.matrix.load_projection_matrix(matrix)

        instance.batch.draw(instance.shader)

        gpu.matrix.pop_projection()

        if scissor_rect is not None:
            gpu.state.scissor_test_set(False)

    gpu.state.blend_set(saved_blend)


class DrawImageOP(bpy.types.Operator):
    bl_idname = "xwz.draw_image"
    bl_label = "Add Image Instance"

    def get_image_items(self, context):
        image_manager._load_images()
        items = [(name, name, "") for name in image_manager.get_available_images()]
        return items if items else [("none", "None", "")]

    container_id: bpy.props.StringProperty(name="Container ID", default="root")
    image_name: bpy.props.EnumProperty(name="Image", items=get_image_items)
    width: bpy.props.IntProperty(name="Width", default=100, min=1, max=2000)
    height: bpy.props.IntProperty(name="Height", default=100, min=1, max=2000)
    x_pos: bpy.props.IntProperty(name="X Position", default=50)
    y_pos: bpy.props.IntProperty(name="Y Position", default=50)
    mask_x: bpy.props.IntProperty(name="Mask X", default=0)
    mask_y: bpy.props.IntProperty(name="Mask Y", default=0)
    mask_width: bpy.props.IntProperty(name="Mask Width", default=0)
    mask_height: bpy.props.IntProperty(name="Mask Height", default=0)
    aspect_ratio: bpy.props.BoolProperty(name="Keep Aspect Ratio", default=True)
    align_h: bpy.props.EnumProperty(
        name="Horizontal Align",
        items=[("LEFT", "Left", ""), ("CENTER", "Center", ""), ("RIGHT", "Right", "")],
        default="LEFT",
    )
    align_v: bpy.props.EnumProperty(
        name="Vertical Align",
        items=[("TOP", "Top", ""), ("CENTER", "Center", ""), ("BOTTOM", "Bottom", "")],
        default="TOP",
    )
    opacity: bpy.props.FloatProperty(name="Opacity", default=1.0, min=0.0, max=1.0)

    def execute(self, context):
        global _draw_handle, _image_instances

        mask = None
        if self.mask_width > 0 and self.mask_height > 0:
            mask = [self.mask_x, self.mask_y, self.mask_width, self.mask_height]

        new_instance = ImageInstance(
            container_id=self.container_id,
            image_name=self.image_name,
            pos=[self.x_pos, self.y_pos],
            size=[self.width, self.height],
            mask=mask,
            aspect_ratio=self.aspect_ratio,
            align_h=self.align_h,
            align_v=self.align_v,
            opacity=self.opacity,
        )
        _image_instances.append(new_instance)

        if _draw_handle is None:
            from .space_config import get_space_class

            space_class = get_space_class() or bpy.types.SpaceView3D
            _draw_handle = space_class.draw_handler_add(draw_all_images, (), "WINDOW", "POST_PIXEL")

        context.area.tag_redraw()
        logger.info(f"Added image instance #{new_instance.id} with image {self.image_name}")
        return {"FINISHED"}


class RemoveImageOP(bpy.types.Operator):
    bl_idname = "xwz.remove_image"
    bl_label = "Remove Image Instance"

    instance_id: bpy.props.IntProperty(name="Instance ID", default=0, min=0)

    def execute(self, context):
        global _draw_handle, _image_instances

        for i, instance in enumerate(_image_instances):
            if instance.id == self.instance_id:
                _image_instances.pop(i)
                logger.info(f"Removed image instance #{self.instance_id}")
                break
        else:
            logger.error(f"Image instance #{self.instance_id} not found")
            return {"CANCELLED"}

        if not _image_instances and _draw_handle is not None:
            from .space_config import get_space_class

            space_class = get_space_class() or bpy.types.SpaceView3D
            space_class.draw_handler_remove(_draw_handle, "WINDOW")
            _draw_handle = None

        context.area.tag_redraw()
        return {"FINISHED"}


class ClearImageOP(bpy.types.Operator):
    bl_idname = "xwz.clear_images"
    bl_label = "Clear All Images"

    def execute(self, context):
        global _draw_handle, _image_instances

        _image_instances.clear()

        if _draw_handle is not None:
            from .space_config import get_space_class

            space_class = get_space_class() or bpy.types.SpaceView3D
            space_class.draw_handler_remove(_draw_handle, "WINDOW")
            _draw_handle = None

        context.area.tag_redraw()
        return {"FINISHED"}


class UpdateImageOP(bpy.types.Operator):
    bl_idname = "xwz.update_image"
    bl_label = "Update Image Instance"

    def get_image_items(self, context):
        image_manager._load_images()
        # Add a "no change" option at the beginning
        items = [("__NOCHANGE__", "No Change", "Don't change the image")]
        items.extend([(name, name, "") for name in image_manager.get_available_images()])
        return items

    instance_id: bpy.props.IntProperty(name="Instance ID", default=0, min=0)
    image_name: bpy.props.EnumProperty(
        name="Image",
        items=get_image_items,
        default=0,  # Will default to "No Change"
    )
    width: bpy.props.IntProperty(name="Width", default=-1, min=-1, max=2000)  # -1 = no change
    height: bpy.props.IntProperty(name="Height", default=-1, min=-1, max=2000)  # -1 = no change
    x_pos: bpy.props.IntProperty(name="X Position", default=-999999)  # sentinel = no change
    y_pos: bpy.props.IntProperty(name="Y Position", default=-999999)  # sentinel = no change
    mask_x: bpy.props.IntProperty(name="Mask X", default=-999999)  # sentinel = no change
    mask_y: bpy.props.IntProperty(name="Mask Y", default=-999999)  # sentinel = no change
    mask_width: bpy.props.IntProperty(name="Mask Width", default=-1, min=-1)  # -1 = no change
    mask_height: bpy.props.IntProperty(name="Mask Height", default=-1, min=-1)  # -1 = no change
    aspect_ratio: bpy.props.EnumProperty(
        name="Keep Aspect Ratio",
        items=[
            ("__NOCHANGE__", "No Change", "Don't change aspect ratio setting"),
            ("TRUE", "True", "Keep aspect ratio"),
            ("FALSE", "False", "Don't keep aspect ratio"),
        ],
        default=0,  # Will default to "No Change"
    )
    align_h: bpy.props.EnumProperty(
        name="Horizontal Align",
        items=[
            ("__NOCHANGE__", "No Change", ""),
            ("LEFT", "Left", ""),
            ("CENTER", "Center", ""),
            ("RIGHT", "Right", ""),
        ],
        default="__NOCHANGE__",
    )
    align_v: bpy.props.EnumProperty(
        name="Vertical Align",
        items=[
            ("__NOCHANGE__", "No Change", ""),
            ("TOP", "Top", ""),
            ("CENTER", "Center", ""),
            ("BOTTOM", "Bottom", ""),
        ],
        default="__NOCHANGE__",
    )
    opacity: bpy.props.FloatProperty(name="Opacity", default=-1.0, min=-1.0, max=1.0)  # -1 = no change

    def execute(self, context):
        for instance in _image_instances:
            if instance.id == self.instance_id:
                kwargs = {}

                # Check image name
                if self.image_name != "__NOCHANGE__" and self.image_name in image_manager.get_available_images():
                    kwargs["image_name"] = self.image_name

                # Check size
                if self.width != -1 or self.height != -1:
                    # If only one dimension is specified, keep the other unchanged
                    new_width = max(1, min(2000, self.width)) if self.width != -1 else instance.size[0]
                    new_height = max(1, min(2000, self.height)) if self.height != -1 else instance.size[1]
                    kwargs["size"] = [new_width, new_height]

                # Check position
                if self.x_pos != -999999 or self.y_pos != -999999:
                    # If only one coordinate is specified, keep the other unchanged
                    new_x = self.x_pos if self.x_pos != -999999 else instance.position[0]
                    new_y = self.y_pos if self.y_pos != -999999 else instance.position[1]
                    kwargs["pos"] = [new_x, new_y]

                # Check mask - only update if any mask property is specified
                if self.mask_x != -999999 or self.mask_y != -999999 or self.mask_width != -1 or self.mask_height != -1:
                    current_mask = instance.mask or [0, 0, 0, 0]
                    new_mask_x = self.mask_x if self.mask_x != -999999 else current_mask[0]
                    new_mask_y = self.mask_y if self.mask_y != -999999 else current_mask[1]
                    new_mask_w = self.mask_width if self.mask_width != -1 else current_mask[2]
                    new_mask_h = self.mask_height if self.mask_height != -1 else current_mask[3]

                    if new_mask_w > 0 and new_mask_h > 0:
                        kwargs["mask"] = [new_mask_x, new_mask_y, new_mask_w, new_mask_h]
                    else:
                        kwargs["mask"] = None

                # Check aspect ratio
                if self.aspect_ratio != "__NOCHANGE__":
                    kwargs["aspect_ratio"] = self.aspect_ratio == "TRUE"

                if self.align_h != "__NOCHANGE__":
                    kwargs["align_h"] = self.align_h

                if self.align_v != "__NOCHANGE__":
                    kwargs["align_v"] = self.align_v

                # Check opacity
                if self.opacity != -1.0:
                    kwargs["opacity"] = max(0.0, min(1.0, self.opacity))

                if kwargs:
                    instance.update_all(**kwargs)

                else:
                    logger.info(f"No properties specified to update for image instance #{self.instance_id}")

                return {"FINISHED"}

        logger.error(f"Image instance #{self.instance_id} not found")
        return {"CANCELLED"}


def register():
    global image_manager

    # Ensure images are loaded/reloaded when addon is (re)enabled
    if image_manager is None:
        # After unregister was called - recreate the singleton
        image_manager = ImageManager()
    elif image_manager._initialized:
        # Addon was previously loaded - reload images
        image_manager.reload_images()

    bpy.utils.register_class(DrawImageOP)
    bpy.utils.register_class(RemoveImageOP)
    bpy.utils.register_class(ClearImageOP)
    bpy.utils.register_class(UpdateImageOP)


def unregister():
    global _draw_handle, _image_instances, image_manager, _image_shader_with_opacity

    # Force clear all image instances
    _image_instances.clear()

    if _draw_handle is not None:
        from .space_config import get_space_class

        space_class = get_space_class() or bpy.types.SpaceView3D
        space_class.draw_handler_remove(_draw_handle, "WINDOW")
        _draw_handle = None

    # Clear the cached shader
    _image_shader_with_opacity = None

    # Unload images and reset the singleton
    ImageManager.reset_instance()
    image_manager = None

    bpy.utils.unregister_class(DrawImageOP)
    bpy.utils.unregister_class(RemoveImageOP)
    bpy.utils.unregister_class(ClearImageOP)
    bpy.utils.unregister_class(UpdateImageOP)
