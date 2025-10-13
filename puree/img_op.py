import os
import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Matrix

_image_instances = []
_draw_handle = None

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
            self._load_images()
            self._initialized = True
    
    def _load_images(self):
        from . import get_addon_root
        addon_assets_path = os.path.join(get_addon_root(), "assets")
        if os.path.exists(addon_assets_path):
            for image_file in os.listdir(addon_assets_path):
                if image_file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tga', '.webp')):
                    image_path = os.path.join(addon_assets_path, image_file)
                    try:
                        if image_file not in bpy.data.images:
                            bpy_image = bpy.data.images.load(image_path)
                        else:
                            bpy_image = bpy.data.images[image_file]
                        
                        bpy_image.alpha_mode = 'PREMUL'
                        
                        texture = gpu.texture.from_image(bpy_image)
                        image_name = os.path.splitext(image_file)[0]
                        self.images[image_name] = image_path
                        self.textures[image_name] = texture
                    except Exception as e:
                        print(f"Failed to load image {image_file}: {e}")
        
    def get_texture(self, image_name):
        return self.textures.get(image_name, None)
    
    def get_available_images(self):
        return list(self.images.keys())
    
    def unload_images(self):
        for image_name, image_path in self.images.items():
            try:
                image_file = os.path.basename(image_path)
                if image_file in bpy.data.images:
                    bpy.data.images.remove(bpy.data.images[image_file])
            except Exception as e:
                print(f"Failed to remove image {image_name}: {e}")
        
        self.textures.clear()
        self.images.clear()
    
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

class ImageInstance:
    def __init__(self, container_id, image_name=None, pos=[50, 50], size=[100, 100], mask=None, aspect_ratio=True):
        self.id           = len(_image_instances)
        self.container_id = container_id
        self.image_name   = image_name
        self.texture      = image_manager.get_texture(self.image_name) if self.image_name else None
        self.position     = pos
        self.size         = size
        self.mask         = mask
        self.aspect_ratio = aspect_ratio
        self.shader       = gpu.shader.from_builtin('IMAGE')
        self.batch        = None
        self._create_batch()
    
    def _create_batch(self):
        if self.texture:
            vertices = [
                (0, 0), (1, 0), (1, 1), (0, 1)
            ]
            uvs = [
                (0, 0), (1, 0), (1, 1), (0, 1)
            ]
            indices = [(0, 1, 2), (0, 2, 3)]
            self.batch = batch_for_shader(
                self.shader, 'TRIS',
                {"pos": vertices, "texCoord": uvs},
                indices=indices
            )
    
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
    
    def update_all(self, image_name=None, size=None, pos=None, mask=None, aspect_ratio=None):
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
        if aspect_ratio is not None:
            self.aspect_ratio = aspect_ratio
        self._trigger_redraw()
    
    def _trigger_redraw(self):
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

def draw_all_images():
    viewport_height = 0
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for region in area.regions:
                if region.type == 'WINDOW':
                    viewport_height = region.height
                    break
            break
    
    gpu.state.blend_set('ALPHA_PREMULT')
    
    for instance in _image_instances:
        if not instance.texture or not instance.batch:
            continue
        
        if instance.mask and instance.mask[2] > 0 and instance.mask[3] > 0:
            xmin = instance.mask[0]
            ymin = viewport_height - instance.mask[1] - instance.mask[3]
            xmax = instance.mask[0] + instance.mask[2]
            ymax = viewport_height - instance.mask[1]
            gpu.state.scissor_test_set(True)
            gpu.state.scissor_set(int(xmin), int(ymin), int(xmax - xmin), int(ymax - ymin))
        
        flipped_y = viewport_height - instance.position[1] - instance.size[1]
        
        display_size = instance.get_display_size()
        
        scale_matrix = Matrix.Diagonal((display_size[0], display_size[1], 1.0, 1.0))
        translation_matrix = Matrix.Translation((instance.position[0], flipped_y, 0))
        
        matrix = gpu.matrix.get_projection_matrix()
        matrix = matrix @ translation_matrix @ scale_matrix
        
        instance.shader.bind()
        instance.shader.uniform_sampler("image", instance.texture)
        
        gpu.matrix.push_projection()
        gpu.matrix.load_projection_matrix(matrix)
        
        instance.batch.draw(instance.shader)
        
        gpu.matrix.pop_projection()
        
        if instance.mask and instance.mask[2] > 0 and instance.mask[3] > 0:
            gpu.state.scissor_test_set(False)
    
    gpu.state.blend_set('NONE')

class DrawImageOP(bpy.types.Operator):
    bl_idname = "xwz.draw_image"
    bl_label = "Add Image Instance"
    
    def get_image_items(self, context):
        image_manager._load_images()
        items = [(name, name, "") for name in image_manager.get_available_images()]
        return items if items else [("none", "None", "")]
    
    container_id: bpy.props.StringProperty(name="Container ID", default="root")
    image_name  : bpy.props.EnumProperty(
        name  = "Image",
        items = get_image_items
    )
    width       : bpy.props.IntProperty(name="Width", default=100, min=1, max=2000)
    height      : bpy.props.IntProperty(name="Height", default=100, min=1, max=2000)
    x_pos       : bpy.props.IntProperty(name="X Position", default=50)
    y_pos       : bpy.props.IntProperty(name="Y Position", default=50)
    mask_x      : bpy.props.IntProperty(name="Mask X", default=0)
    mask_y      : bpy.props.IntProperty(name="Mask Y", default=0)
    mask_width  : bpy.props.IntProperty(name="Mask Width", default=0)
    mask_height : bpy.props.IntProperty(name="Mask Height", default=0)
    aspect_ratio: bpy.props.BoolProperty(name="Keep Aspect Ratio", default=True)
    
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
            aspect_ratio=self.aspect_ratio
        )
        _image_instances.append(new_instance)
        
        if _draw_handle is None:
            _draw_handle = bpy.types.SpaceView3D.draw_handler_add(
                draw_all_images, (), 'WINDOW', 'POST_PIXEL')
        
        context.area.tag_redraw()
        self.report({'INFO'}, f"Added image instance #{new_instance.id} with image {self.image_name}")
        return {'FINISHED'}

class RemoveImageOP(bpy.types.Operator):
    bl_idname = "xwz.remove_image"
    bl_label = "Remove Image Instance"
    
    instance_id: bpy.props.IntProperty(name="Instance ID", default=0, min=0)
    
    def execute(self, context):
        global _draw_handle, _image_instances
        
        for i, instance in enumerate(_image_instances):
            if instance.id == self.instance_id:
                _image_instances.pop(i)
                self.report({'INFO'}, f"Removed image instance #{self.instance_id}")
                break
        else:
            self.report({'ERROR'}, f"Image instance #{self.instance_id} not found")
            return {'CANCELLED'}
        
        if not _image_instances and _draw_handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, 'WINDOW')
            _draw_handle = None
        
        context.area.tag_redraw()
        return {'FINISHED'}

class ClearImageOP(bpy.types.Operator):
    bl_idname = "xwz.clear_images"
    bl_label = "Clear All Images"
    
    def execute(self, context):
        global _draw_handle, _image_instances
        
        _image_instances.clear()
        
        if _draw_handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, 'WINDOW')
            _draw_handle = None
        
        context.area.tag_redraw()
        return {'FINISHED'}

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
    image_name : bpy.props.EnumProperty(
        name="Image",
        items=get_image_items,
        default=0  # Will default to "No Change"
    )
    width      : bpy.props.IntProperty(name="Width", default=-1, min=-1, max=2000)  # -1 = no change
    height     : bpy.props.IntProperty(name="Height", default=-1, min=-1, max=2000)  # -1 = no change
    x_pos      : bpy.props.IntProperty(name="X Position", default=-999999)  # sentinel = no change
    y_pos      : bpy.props.IntProperty(name="Y Position", default=-999999)  # sentinel = no change
    mask_x     : bpy.props.IntProperty(name="Mask X", default=-999999)  # sentinel = no change
    mask_y     : bpy.props.IntProperty(name="Mask Y", default=-999999)  # sentinel = no change
    mask_width : bpy.props.IntProperty(name="Mask Width", default=-1, min=-1)  # -1 = no change
    mask_height: bpy.props.IntProperty(name="Mask Height", default=-1, min=-1)  # -1 = no change
    aspect_ratio: bpy.props.EnumProperty(
        name="Keep Aspect Ratio",
        items=[
            ("__NOCHANGE__", "No Change", "Don't change aspect ratio setting"),
            ("TRUE", "True", "Keep aspect ratio"),
            ("FALSE", "False", "Don't keep aspect ratio")
        ],
        default=0  # Will default to "No Change"
    )
    
    def execute(self, context):
        for instance in _image_instances:
            if instance.id == self.instance_id:
                kwargs = {}
                
                # Check image name
                if self.image_name != "__NOCHANGE__" and self.image_name in image_manager.get_available_images():
                    kwargs['image_name'] = self.image_name
                
                # Check size
                if self.width != -1 or self.height != -1:
                    # If only one dimension is specified, keep the other unchanged
                    new_width = max(1, min(2000, self.width)) if self.width != -1 else instance.size[0]
                    new_height = max(1, min(2000, self.height)) if self.height != -1 else instance.size[1]
                    kwargs['size'] = [new_width, new_height]
                
                # Check position
                if self.x_pos != -999999 or self.y_pos != -999999:
                    # If only one coordinate is specified, keep the other unchanged
                    new_x = self.x_pos if self.x_pos != -999999 else instance.position[0]
                    new_y = self.y_pos if self.y_pos != -999999 else instance.position[1]
                    kwargs['pos'] = [new_x, new_y]
                
                # Check mask - only update if any mask property is specified
                if (self.mask_x != -999999 or self.mask_y != -999999 or 
                    self.mask_width != -1 or self.mask_height != -1):
                    
                    current_mask = instance.mask or [0, 0, 0, 0]
                    new_mask_x = self.mask_x if self.mask_x != -999999 else current_mask[0]
                    new_mask_y = self.mask_y if self.mask_y != -999999 else current_mask[1]
                    new_mask_w = self.mask_width if self.mask_width != -1 else current_mask[2]
                    new_mask_h = self.mask_height if self.mask_height != -1 else current_mask[3]
                    
                    if new_mask_w > 0 and new_mask_h > 0:
                        kwargs['mask'] = [new_mask_x, new_mask_y, new_mask_w, new_mask_h]
                    else:
                        kwargs['mask'] = None
                
                # Check aspect ratio
                if self.aspect_ratio != "__NOCHANGE__":
                    kwargs['aspect_ratio'] = self.aspect_ratio == "TRUE"
                
                if kwargs:
                    instance.update_all(**kwargs)
                    updated_props = list(kwargs.keys())

                else:
                    self.report({'INFO'}, f"No properties specified to update for image instance #{self.instance_id}")
                
                return {'FINISHED'}
        
        self.report({'ERROR'}, f"Image instance #{self.instance_id} not found")
        return {'CANCELLED'}

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
    global _draw_handle, _image_instances, image_manager
    
    # Force clear all image instances
    _image_instances.clear()
    
    if _draw_handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, 'WINDOW')
        _draw_handle = None
    
    # Unload images and reset the singleton
    ImageManager.reset_instance()
    image_manager = None
    
    bpy.utils.unregister_class(DrawImageOP)
    bpy.utils.unregister_class(RemoveImageOP)
    bpy.utils.unregister_class(ClearImageOP)
    bpy.utils.unregister_class(UpdateImageOP)