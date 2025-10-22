import bpy_extras.view3d_utils
from mathutils import Vector

def recursive_search(container, target_id):
    if container.id == target_id:
        return container
    for child in container.children:
        result = recursive_search(child, target_id)
        if result:
            return result
    return None

def osb(obj, context):
    region = context.region
    rv3d = context.region_data
    
    if not obj or not obj.type == 'MESH':
        return None
    
    bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    
    screen_coords = []
    for co in bbox_corners:
        screen_co = bpy_extras.view3d_utils.location_3d_to_region_2d(region, rv3d, co)
        if screen_co:
            screen_coords.append(screen_co)
    
    if not screen_coords:
        return None
    
    min_x = min(co.x for co in screen_coords)
    max_x = max(co.x for co in screen_coords)
    min_y = min(co.y for co in screen_coords)
    max_y = max(co.y for co in screen_coords)
    
    width = max_x - min_x
    height = max_y - min_y
    
    return {
        'x': min_x,
        'y': region.height - max_y,
        'width': width,
        'height': height
    }