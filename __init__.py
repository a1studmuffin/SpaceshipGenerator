bl_info = {
    "name": "Spaceship Generator",
    "author": "Michael Davies",
    "version": (1, 1, 2),
    "blender": (2, 76, 0),
    "location": "View3D > Add > Mesh",
    "description": "Procedurally generate 3D spaceships from a random seed.",
    "wiki_url": "https://github.com/a1studmuffin/SpaceshipGenerator/blob/master/README.md",
    "tracker_url": "https://github.com/a1studmuffin/SpaceshipGenerator/issues",
    "category": "Add Mesh"
}

if "bpy" in locals():
    # reload logic (magic)
    import importlib
    importlib.reload(spaceship_generator)
else:
    from . import spaceship_generator

import bpy
from bpy.props import StringProperty, BoolProperty, IntProperty
from bpy.types import Operator

class GenerateSpaceship(Operator):
    """Procedurally generate 3D spaceships from a random seed."""
    bl_idname = "mesh.generate_spaceship"
    bl_label = "Spaceship"
    bl_options = {'REGISTER', 'UNDO'}

    random_seed = StringProperty(default='', name='Seed')
    num_hull_segments_min      = IntProperty (default=3, min=0, soft_max=16, name='Min. Hull Segments')
    num_hull_segments_max      = IntProperty (default=6, min=0, soft_max=16, name='Max. Hull Segments')
    create_asymmetry_segments  = BoolProperty(default=True, name='Create Asymmetry Segments')
    num_asymmetry_segments_min = IntProperty (default=1, min=1, soft_max=16, name='Min. Asymmetry Segments')
    num_asymmetry_segments_max = IntProperty (default=5, min=1, soft_max=16, name='Max. Asymmetry Segments')
    create_face_detail         = BoolProperty(default=True,  name='Create Face Detail')
    allow_horizontal_symmetry  = BoolProperty(default=True,  name='Allow Horizontal Symmetry')
    allow_vertical_symmetry    = BoolProperty(default=False, name='Allow Vertical Symmetry')
    apply_bevel_modifier       = BoolProperty(default=True,  name='Apply Bevel Modifier')
    assign_materials           = BoolProperty(default=True,  name='Assign Materials')

    def execute(self, context):
        spaceship_generator.generate_spaceship(
            self.random_seed,
            self.num_hull_segments_min,
            self.num_hull_segments_max,
            self.create_asymmetry_segments,
            self.num_asymmetry_segments_min,
            self.num_asymmetry_segments_max,
            self.create_face_detail,
            self.allow_horizontal_symmetry,
            self.allow_vertical_symmetry,
            self.apply_bevel_modifier,
            self.assign_materials)
        return {'FINISHED'}

def menu_func(self, context):
    self.layout.operator(GenerateSpaceship.bl_idname, text="Spaceship")

def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_mesh_add.append(menu_func)

def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_mesh_add.remove(menu_func)

if __name__ == "__main__":
    register()
