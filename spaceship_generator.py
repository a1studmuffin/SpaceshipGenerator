#
# spaceship_generator.py
#
# This is a Blender script that uses procedural generation to create
# textured 3D spaceship models. Tested with Blender 2.77a.
#
# michael@spaceduststudios.com
# https://github.com/a1studmuffin/SpaceshipGenerator
#

import sys
import os
import os.path
import bpy
import bmesh
import datetime
from math import sqrt, radians, pi, cos, sin
from mathutils import Vector, Matrix
from random import random, seed, uniform, randint, randrange
from enum import IntEnum
from colorsys import hls_to_rgb

DIR = os.path.dirname(os.path.abspath(__file__))

def resource_path(*path_components):
    return os.path.join(DIR, *path_components)

# Deletes all existing spaceships and unused materials from the scene
def reset_scene():
    for item in bpy.data.objects:
        item.select = item.name.startswith('Spaceship')
    bpy.ops.object.delete()
    for material in bpy.data.materials:
        if not material.users:
            bpy.data.materials.remove(material)
    for texture in bpy.data.textures:
        if not texture.users:
            bpy.data.textures.remove(texture)

# Extrudes a face along its normal by translate_forwards units.
# Returns the new face, and optionally fills out extruded_face_list
# with all the additional side faces created from the extrusion.
def extrude_face(bm, face, translate_forwards=0.0, extruded_face_list=None):
    new_faces = bmesh.ops.extrude_discrete_faces(bm, faces=[face])['faces']
    if extruded_face_list != None:
        extruded_face_list += new_faces[:]
    new_face = new_faces[0]
    bmesh.ops.translate(bm,
                        vec=new_face.normal * translate_forwards,
                        verts=new_face.verts)
    return new_face

# Similar to extrude_face, except corrigates the geometry to create "ribs".
# Returns the new face.
def ribbed_extrude_face(bm, face, translate_forwards, num_ribs=3, rib_scale=0.9):
    translate_forwards_per_rib = translate_forwards / float(num_ribs)
    new_face = face
    for i in range(num_ribs):
        new_face = extrude_face(bm, new_face, translate_forwards_per_rib * 0.25)
        new_face = extrude_face(bm, new_face, 0.0)
        scale_face(bm, new_face, rib_scale, rib_scale, rib_scale)
        new_face = extrude_face(bm, new_face, translate_forwards_per_rib * 0.5)
        new_face = extrude_face(bm, new_face, 0.0)
        scale_face(bm, new_face, 1 / rib_scale, 1 / rib_scale, 1 / rib_scale)
        new_face = extrude_face(bm, new_face, translate_forwards_per_rib * 0.25)
    return new_face

# Scales a face in local face space. Ace!
def scale_face(bm, face, scale_x, scale_y, scale_z):
    face_space = get_face_matrix(face)
    face_space.invert()
    bmesh.ops.scale(bm,
                    vec=Vector((scale_x, scale_y, scale_z)),
                    space=face_space,
                    verts=face.verts)

# Returns a rough 4x4 transform matrix for a face (doesn't handle
# distortion/shear) with optional position override.
def get_face_matrix(face, pos=None):
    x_axis = (face.verts[1].co - face.verts[0].co).normalized()
    z_axis = -face.normal
    y_axis = z_axis.cross(x_axis)
    if not pos:
        pos = face.calc_center_bounds()

    # Construct a 4x4 matrix from axes + position:
    # http://i.stack.imgur.com/3TnQP.png
    mat = Matrix()
    mat[0][0] = x_axis.x
    mat[1][0] = x_axis.y
    mat[2][0] = x_axis.z
    mat[3][0] = 0
    mat[0][1] = y_axis.x
    mat[1][1] = y_axis.y
    mat[2][1] = y_axis.z
    mat[3][1] = 0
    mat[0][2] = z_axis.x
    mat[1][2] = z_axis.y
    mat[2][2] = z_axis.z
    mat[3][2] = 0
    mat[0][3] = pos.x
    mat[1][3] = pos.y
    mat[2][3] = pos.z
    mat[3][3] = 1
    return mat

# Returns the rough length and width of a quad face.
# Assumes a perfect rectangle, but close enough.
def get_face_width_and_height(face):
    if not face.is_valid or len(face.verts[:]) < 4:
        return -1, -1
    width = (face.verts[0].co - face.verts[1].co).length
    height = (face.verts[2].co - face.verts[1].co).length
    return width, height

# Returns the rough aspect ratio of a face. Always >= 1.
def get_aspect_ratio(face):
    if not face.is_valid:
        return 1.0
    face_aspect_ratio = max(0.01, face.edges[0].calc_length() / face.edges[1].calc_length())
    if face_aspect_ratio < 1.0:
        face_aspect_ratio = 1.0 / face_aspect_ratio
    return face_aspect_ratio

# Returns true if this face is pointing behind the ship
def is_rear_face(face):
    return face.normal.x < -0.95

# Given a face, splits it into a uniform grid and extrudes each grid face
# out and back in again, making an exhaust shape.
def add_exhaust_to_face(bm, face):
    if not face.is_valid:
        return

    # The more square the face is, the more grid divisions it might have
    num_cuts = randint(1, int(4 - get_aspect_ratio(face)))
    result = bmesh.ops.subdivide_edges(bm,
                                    edges=face.edges[:],
                                    cuts=num_cuts,
                                    fractal=0.02,
                                    use_grid_fill=True)

    exhaust_length = uniform(0.1, 0.2)
    scale_outer = 1 / uniform(1.3, 1.6)
    scale_inner = 1 / uniform(1.05, 1.1)
    for face in result['geom']:
        if isinstance(face, bmesh.types.BMFace):
            if is_rear_face(face):
                face.material_index = Material.hull_dark
                face = extrude_face(bm, face, exhaust_length)
                scale_face(bm, face, scale_outer, scale_outer, scale_outer)
                extruded_face_list = []
                face = extrude_face(bm, face, -exhaust_length * 0.9, extruded_face_list)
                for extruded_face in extruded_face_list:
                    extruded_face.material_index = Material.exhaust_burn
                scale_face(bm, face, scale_inner, scale_inner, scale_inner)

# Given a face, splits it up into a smaller uniform grid and extrudes each grid cell.
def add_grid_to_face(bm, face):
    if not face.is_valid:
        return
    result = bmesh.ops.subdivide_edges(bm,
                                    edges=face.edges[:],
                                    cuts=randint(2, 4),
                                    fractal=0.02,
                                    use_grid_fill=True,
                                    use_single_edge=False)
    grid_length = uniform(0.025, 0.15)
    scale = 0.8
    for face in result['geom']:
        if isinstance(face, bmesh.types.BMFace):
            material_index = Material.hull_lights if random() > 0.5 else Material.hull
            extruded_face_list = []
            face = extrude_face(bm, face, grid_length, extruded_face_list)
            for extruded_face in extruded_face_list:
                if abs(face.normal.z) < 0.707: # side face
                    extruded_face.material_index = material_index
            scale_face(bm, face, scale, scale, scale)

# Given a face, adds some cylinders along it in a grid pattern.
def add_cylinders_to_face(bm, face):
    if not face.is_valid or len(face.verts[:]) < 4:
        return
    horizontal_step = randint(1, 3)
    vertical_step = randint(1, 3)
    num_segments = randint(6, 12)
    face_width, face_height = get_face_width_and_height(face)
    cylinder_depth = 1.3 * min(face_width / (horizontal_step + 2),
                               face_height / (vertical_step + 2))
    cylinder_size = cylinder_depth * 0.5
    for h in range(horizontal_step):
        top = face.verts[0].co.lerp(
            face.verts[1].co, (h + 1) / float(horizontal_step + 1))
        bottom = face.verts[3].co.lerp(
            face.verts[2].co, (h + 1) / float(horizontal_step + 1))
        for v in range(vertical_step):
            pos = top.lerp(bottom, (v + 1) / float(vertical_step + 1))
            cylinder_matrix = get_face_matrix(face, pos) @ \
                Matrix.Rotation(radians(90), 3, 'X').to_4x4()
            bmesh.ops.create_cone(bm,
                                  cap_ends=True,
                                  cap_tris=False,
                                  segments=num_segments,
                                  diameter1=cylinder_size,
                                  diameter2=cylinder_size,
                                  depth=cylinder_depth,
                                  matrix=cylinder_matrix)

# Given a face, adds some weapon turrets to it in a grid pattern.
# Each turret will have a random orientation.
def add_weapons_to_face(bm, face):
    if not face.is_valid or len(face.verts[:]) < 4:
        return
    horizontal_step = randint(1, 2)
    vertical_step = randint(1, 2)
    num_segments = 16
    face_width, face_height = get_face_width_and_height(face)
    weapon_size = 0.5 * min(face_width / (horizontal_step + 2),
                            face_height / (vertical_step + 2))
    weapon_depth = weapon_size * 0.2
    for h in range(horizontal_step):
        top = face.verts[0].co.lerp(
            face.verts[1].co, (h + 1) / float(horizontal_step + 1))
        bottom = face.verts[3].co.lerp(
            face.verts[2].co, (h + 1) / float(horizontal_step + 1))
        for v in range(vertical_step):
            pos = top.lerp(bottom, (v + 1) / float(vertical_step + 1))
            face_matrix = get_face_matrix(face, pos + face.normal * weapon_depth * 0.5) @ \
                Matrix.Rotation(radians(uniform(0, 90)), 3, 'Z').to_4x4()

            # Turret foundation
            bmesh.ops.create_cone(bm,
                                  cap_ends=True,
                                  cap_tris=False,
                                  segments=num_segments,
                                  diameter1=weapon_size * 0.9,
                                  diameter2=weapon_size,
                                  depth=weapon_depth,
                                  matrix=face_matrix)

            # Turret left guard
            left_guard_mat = face_matrix @ \
                Matrix.Rotation(radians(90), 3, 'Y').to_4x4() @ \
                Matrix.Translation(Vector((0, 0, weapon_size * 0.6))).to_4x4()
            bmesh.ops.create_cone(bm,
                                  cap_ends=True,
                                  cap_tris=False,
                                  segments=num_segments,
                                  diameter1=weapon_size * 0.6,
                                  diameter2=weapon_size * 0.5,
                                  depth=weapon_depth * 2,
                                  matrix=left_guard_mat)

            # Turret right guard
            right_guard_mat = face_matrix @ \
                Matrix.Rotation(radians(90), 3, 'Y').to_4x4() @ \
                Matrix.Translation(Vector((0, 0, weapon_size * -0.6))).to_4x4()
            bmesh.ops.create_cone(bm,
                                  cap_ends=True,
                                  cap_tris=False,
                                  segments=num_segments,
                                  diameter1=weapon_size * 0.5,
                                  diameter2=weapon_size * 0.6,
                                  depth=weapon_depth * 2,
                                  matrix=right_guard_mat)

            # Turret housing
            upward_angle = uniform(0, 45)
            turret_house_mat = face_matrix @ \
                Matrix.Rotation(radians(upward_angle), 3, 'X').to_4x4() @ \
                Matrix.Translation(Vector((0, weapon_size * -0.4, 0))).to_4x4()
            bmesh.ops.create_cone(bm,
                                  cap_ends=True,
                                  cap_tris=False,
                                  segments=8,
                                  diameter1=weapon_size * 0.4,
                                  diameter2=weapon_size * 0.4,
                                  depth=weapon_depth * 5,
                                  matrix=turret_house_mat)

            # Turret barrels L + R
            bmesh.ops.create_cone(bm,
                                  cap_ends=True,
                                  cap_tris=False,
                                  segments=8,
                                  diameter1=weapon_size * 0.1,
                                  diameter2=weapon_size * 0.1,
                                  depth=weapon_depth * 6,
                                  matrix=turret_house_mat @ \
                                         Matrix.Translation(Vector((weapon_size * 0.2, 0, -weapon_size))).to_4x4())
            bmesh.ops.create_cone(bm,
                                  cap_ends=True,
                                  cap_tris=False,
                                  segments=8,
                                  diameter1=weapon_size * 0.1,
                                  diameter2=weapon_size * 0.1,
                                  depth=weapon_depth * 6,
                                  matrix=turret_house_mat @ \
                                         Matrix.Translation(Vector((weapon_size * -0.2, 0, -weapon_size))).to_4x4())

# Given a face, adds a sphere on the surface, partially inset.
def add_sphere_to_face(bm, face):
    if not face.is_valid:
        return
    face_width, face_height = get_face_width_and_height(face)
    sphere_size = uniform(0.4, 1.0) * min(face_width, face_height)
    sphere_matrix = get_face_matrix(face,
                                    face.calc_center_bounds() - face.normal * \
                                    uniform(0, sphere_size * 0.5))
    result = bmesh.ops.create_icosphere(bm,
                                        subdivisions=3,
                                        diameter=sphere_size,
                                        matrix=sphere_matrix)
    for vert in result['verts']:
        for face in vert.link_faces:
            face.material_index = Material.hull

# Given a face, adds some pointy intimidating antennas.
def add_surface_antenna_to_face(bm, face):
    if not face.is_valid or len(face.verts[:]) < 4:
        return
    horizontal_step = randint(4, 10)
    vertical_step = randint(4, 10)
    for h in range(horizontal_step):
        top = face.verts[0].co.lerp(
            face.verts[1].co, (h + 1) / float(horizontal_step + 1))
        bottom = face.verts[3].co.lerp(
            face.verts[2].co, (h + 1) / float(horizontal_step + 1))
        for v in range(vertical_step):
            if random() > 0.9:
                pos = top.lerp(bottom, (v + 1) / float(vertical_step + 1))
                face_size = sqrt(face.calc_area())
                depth = uniform(0.1, 1.5) * face_size
                depth_short = depth * uniform(0.02, 0.15)
                base_diameter = uniform(0.005, 0.05)

                material_index = Material.hull if random() > 0.5 else Material.hull_dark

                # Spire
                num_segments = uniform(3, 6)
                result = bmesh.ops.create_cone(bm,
                                               cap_ends=False,
                                               cap_tris=False,
                                               segments=num_segments,
                                               diameter1=0,
                                               diameter2=base_diameter,
                                               depth=depth,
                                               matrix=get_face_matrix(face, pos + face.normal * depth * 0.5))
                for vert in result['verts']:
                    for vert_face in vert.link_faces:
                        vert_face.material_index = material_index

                # Base
                result = bmesh.ops.create_cone(bm,
                                               cap_ends=True,
                                               cap_tris=False,
                                               segments=num_segments,
                                               diameter1=base_diameter * uniform(1, 1.5),
                                               diameter2=base_diameter * uniform(1.5, 2),
                                               depth=depth_short,
                                               matrix=get_face_matrix(face, pos + face.normal * depth_short * 0.45))
                for vert in result['verts']:
                    for vert_face in vert.link_faces:
                        vert_face.material_index = material_index

# Given a face, adds a glowing "landing pad" style disc.
def add_disc_to_face(bm, face):
    if not face.is_valid:
        return
    face_width, face_height = get_face_width_and_height(face)
    depth = 0.125 * min(face_width, face_height)
    bmesh.ops.create_cone(bm,
                          cap_ends=True,
                          cap_tris=False,
                          segments=32,
                          diameter1=depth * 3,
                          diameter2=depth * 4,
                          depth=depth,
                          matrix=get_face_matrix(face, face.calc_center_bounds() + face.normal * depth * 0.5))
    result = bmesh.ops.create_cone(bm,
                                   cap_ends=False,
                                   cap_tris=False,
                                   segments=32,
                                   diameter1=depth * 1.25,
                                   diameter2=depth * 2.25,
                                   depth=0.0,
                                   matrix=get_face_matrix(face, face.calc_center_bounds() + face.normal * depth * 1.05))
    for vert in result['verts']:
        for face in vert.link_faces:
            face.material_index = Material.glow_disc

class Material(IntEnum):
    hull = 0            # Plain spaceship hull
    hull_lights = 1     # Spaceship hull with emissive windows
    hull_dark = 2       # Plain Spaceship hull, darkened
    exhaust_burn = 3    # Emissive engine burn material
    glow_disc = 4       # Emissive landing pad disc material


# Returns shader node
def getShaderNode(mat):
    ntree = mat.node_tree
    node_out = ntree.get_output_node('EEVEE')
    shader_node = node_out.inputs['Surface'].links[0].from_node
    return shader_node

def getShaderInput(mat, name):
    shaderNode = getShaderNode(mat)
    return shaderNode.inputs[name]

# Adds a hull normal map texture slot to a material.
def add_hull_normal_map(mat, hull_normal_map):
    ntree = mat.node_tree
    shader = getShaderNode(mat)
    links = ntree.links

    teximage_node = ntree.nodes.new('ShaderNodeTexImage')
    teximage_node.image = hull_normal_map
    teximage_node.image.colorspace_settings.name = 'Raw'
    teximage_node.projection ='BOX'
    tex_coords_node = ntree.nodes.new('ShaderNodeTexCoord')
    links.new(tex_coords_node.outputs['Object'], teximage_node.inputs['Vector'])
    normalMap_node = ntree.nodes.new('ShaderNodeNormalMap')
    links.new(teximage_node.outputs[0], normalMap_node.inputs['Color'])
    links.new(normalMap_node.outputs['Normal'], shader.inputs['Normal'])
    return tex_coords_node



# Sets some basic properties for a hull material.
def set_hull_mat_basics(mat, color, hull_normal_map):
    shader_node = getShaderNode(mat)
    shader_node.inputs["Specular"].default_value = 0.1
    shader_node.inputs["Base Color"].default_value = color

    return add_hull_normal_map(mat, hull_normal_map)

# Creates all our materials and returns them as a list.
def create_materials():
    ret = []

    for material in Material:
        mat = bpy.data.materials.new(name=material.name)
        mat.use_nodes = True
        ret.append(mat)

    # Choose a base color for the spaceship hull
    hull_base_color = hls_to_rgb(
        random(), uniform(0.05, 0.5), uniform(0, 0.25))
    hull_base_color = (hull_base_color[0], hull_base_color[1], hull_base_color[2], 1.0)

    # Load up the hull normal map
    hull_normal_map = bpy.data.images.load(resource_path('textures', 'hull_normal.png'), check_existing=True)


    # Build the hull texture
    mat = ret[Material.hull]
    set_hull_mat_basics(mat, hull_base_color, hull_normal_map)

    # Build the hull_lights texture
    mat = ret[Material.hull_lights]
    tex_coords_node = set_hull_mat_basics(mat, hull_base_color, hull_normal_map)
    ntree = mat.node_tree
    shader_node = getShaderNode(mat)
    links = ntree.links

    # Add a diffuse layer that sets the window color
    hull_lights_diffuse_map = bpy.data.images.load(resource_path('textures', 'hull_lights_diffuse.png'), check_existing=True)
    teximage_diff_node = ntree.nodes.new('ShaderNodeTexImage')
    teximage_diff_node.image = hull_lights_diffuse_map
    teximage_diff_node.projection ='BOX'
    links.new(tex_coords_node.outputs['Object'], teximage_diff_node.inputs['Vector'])
    RGB_node = ntree.nodes.new('ShaderNodeRGB')
    RGB_node.outputs[0].default_value = hull_base_color
    mix_node = ntree.nodes.new('ShaderNodeMixRGB')
    links.new(RGB_node.outputs[0], mix_node.inputs[1])
    links.new(teximage_diff_node.outputs[0], mix_node.inputs[2])
    links.new(teximage_diff_node.outputs[1], mix_node.inputs[0])
    links.new(mix_node.outputs[0], shader_node.inputs["Base Color"])



    # Add an emissive layer that lights up the windows
    hull_lights_emessive_map = bpy.data.images.load(resource_path('textures', 'hull_lights_emit.png'), check_existing=True)
    teximage_emit_node = ntree.nodes.new('ShaderNodeTexImage')
    teximage_emit_node.image = hull_lights_emessive_map
    teximage_emit_node.projection ='BOX'
    links.new(tex_coords_node.outputs['Object'], teximage_emit_node.inputs['Vector'])
    links.new(teximage_emit_node.outputs[0], shader_node.inputs["Emission"])



    # Build the hull_dark texture
    mat = ret[Material.hull_dark]
    set_hull_mat_basics(mat, [0.3 * x for x in hull_base_color], hull_normal_map)

    # Choose a glow color for the exhaust + glow discs
    glow_color = hls_to_rgb(random(), uniform(0.5, 1), 1)
    glow_color = (glow_color[0], glow_color[1], glow_color[2], 1.0)

    # # Build the exhaust_burn texture
    mat = ret[Material.exhaust_burn]
    shader_node = getShaderNode(mat)
    shader_node.inputs["Emission"].default_value = glow_color

    # # Build the glow_disc texture
    mat = ret[Material.glow_disc]
    shader_node = getShaderNode(mat)
    shader_node.inputs["Emission"].default_value = glow_color

    return ret

# Generates a textured spaceship mesh and returns the object.
# Just uses global cube texture coordinates rather than generating UVs.
# Takes an optional random seed value to generate a specific spaceship.
# Allows overriding of some parameters that affect generation.
def generate_spaceship(random_seed='',
                       num_hull_segments_min=3,
                       num_hull_segments_max=6,
                       create_asymmetry_segments=True,
                       num_asymmetry_segments_min=1,
                       num_asymmetry_segments_max=5,
                       create_face_detail=True,
                       allow_horizontal_symmetry=True,
                       allow_vertical_symmetry=False,
                       apply_bevel_modifier=True,
                       assign_materials=True):
    if random_seed:
        seed(random_seed)

    # Let's start with a unit BMesh cube scaled randomly
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    scale_vector = Vector(
        (uniform(0.75, 2.0), uniform(0.75, 2.0), uniform(0.75, 2.0)))
    bmesh.ops.scale(bm, vec=scale_vector, verts=bm.verts)

    # Extrude out the hull along the X axis, adding some semi-random perturbations
    for face in bm.faces[:]:
        if abs(face.normal.x) > 0.5:
            hull_segment_length = uniform(0.3, 1)
            num_hull_segments = randrange(num_hull_segments_min, num_hull_segments_max)
            hull_segment_range = range(num_hull_segments)
            for i in hull_segment_range:
                is_last_hull_segment = i == hull_segment_range[-1]
                val = random()
                if val > 0.1:
                    # Most of the time, extrude out the face with some random deviations
                    face = extrude_face(bm, face, hull_segment_length)
                    if random() > 0.75:
                        face = extrude_face(
                            bm, face, hull_segment_length * 0.25)

                    # Maybe apply some scaling
                    if random() > 0.5:
                        sy = uniform(1.2, 1.5)
                        sz = uniform(1.2, 1.5)
                        if is_last_hull_segment or random() > 0.5:
                            sy = 1 / sy
                            sz = 1 / sz
                        scale_face(bm, face, 1, sy, sz)

                    # Maybe apply some sideways translation
                    if random() > 0.5:
                        sideways_translation = Vector(
                            (0, 0, uniform(0.1, 0.4) * scale_vector.z * hull_segment_length))
                        if random() > 0.5:
                            sideways_translation = -sideways_translation
                        bmesh.ops.translate(bm,
                                            vec=sideways_translation,
                                            verts=face.verts)

                    # Maybe add some rotation around Y axis
                    if random() > 0.5:
                        angle = 5
                        if random() > 0.5:
                            angle = -angle
                        bmesh.ops.rotate(bm,
                                         verts=face.verts,
                                         cent=(0, 0, 0),
                                         matrix=Matrix.Rotation(radians(angle), 3, 'Y'))
                else:
                    # Rarely, create a ribbed section of the hull
                    rib_scale = uniform(0.75, 0.95)
                    face = ribbed_extrude_face(
                        bm, face, hull_segment_length, randint(2, 4), rib_scale)

    # Add some large asynmmetrical sections of the hull that stick out
    if create_asymmetry_segments:
        for face in bm.faces[:]:
            # Skip any long thin faces as it'll probably look stupid
            if get_aspect_ratio(face) > 4:
                continue
            if random() > 0.85:
                hull_piece_length = uniform(0.1, 0.4)
                for i in range(randrange(num_asymmetry_segments_min, num_asymmetry_segments_max)):
                    face = extrude_face(bm, face, hull_piece_length)

                    # Maybe apply some scaling
                    if random() > 0.25:
                        s = 1 / uniform(1.1, 1.5)
                        scale_face(bm, face, s, s, s)

    # Now the basic hull shape is built, let's categorize + add detail to all the faces
    if create_face_detail:
        engine_faces = []
        grid_faces = []
        antenna_faces = []
        weapon_faces = []
        sphere_faces = []
        disc_faces = []
        cylinder_faces = []
        for face in bm.faces[:]:
            # Skip any long thin faces as it'll probably look stupid
            if get_aspect_ratio(face) > 3:
                continue

            # Spin the wheel! Let's categorize + assign some materials
            val = random()
            if is_rear_face(face):  # rear face
                if not engine_faces or val > 0.75:
                    engine_faces.append(face)
                elif val > 0.5:
                    cylinder_faces.append(face)
                elif val > 0.25:
                    grid_faces.append(face)
                else:
                    face.material_index = Material.hull_lights
            elif face.normal.x > 0.9:  # front face
                if face.normal.dot(face.calc_center_bounds()) > 0 and val > 0.7:
                    antenna_faces.append(face)  # front facing antenna
                    face.material_index = Material.hull_lights
                elif val > 0.4:
                    grid_faces.append(face)
                else:
                    face.material_index = Material.hull_lights
            elif face.normal.z > 0.9:  # top face
                if face.normal.dot(face.calc_center_bounds()) > 0 and val > 0.7:
                    antenna_faces.append(face)  # top facing antenna
                elif val > 0.6:
                    grid_faces.append(face)
                elif val > 0.3:
                    cylinder_faces.append(face)
            elif face.normal.z < -0.9:  # bottom face
                if val > 0.75:
                    disc_faces.append(face)
                elif val > 0.5:
                    grid_faces.append(face)
                elif val > 0.25:
                    weapon_faces.append(face)
            elif abs(face.normal.y) > 0.9:  # side face
                if not weapon_faces or val > 0.75:
                    weapon_faces.append(face)
                elif val > 0.6:
                    grid_faces.append(face)
                elif val > 0.4:
                    sphere_faces.append(face)
                else:
                    face.material_index = Material.hull_lights

        # Now we've categorized, let's actually add the detail
        for face in engine_faces:
            add_exhaust_to_face(bm, face)

        for face in grid_faces:
            add_grid_to_face(bm, face)

        for face in antenna_faces:
            add_surface_antenna_to_face(bm, face)

        for face in weapon_faces:
            add_weapons_to_face(bm, face)

        for face in sphere_faces:
            add_sphere_to_face(bm, face)

        for face in disc_faces:
            add_disc_to_face(bm, face)

        for face in cylinder_faces:
            add_cylinders_to_face(bm, face)

    # Apply horizontal symmetry sometimes
    if allow_horizontal_symmetry and random() > 0.5:
        bmesh.ops.symmetrize(bm, input=bm.verts[:] + bm.edges[:] + bm.faces[:], direction="Y")

    # Apply vertical symmetry sometimes - this can cause spaceship "islands", so disabled by default
    if allow_vertical_symmetry and random() > 0.5:
        bmesh.ops.symmetrize(bm, input=bm.verts[:] + bm.edges[:] + bm.faces[:], direction="Z")

    # Finish up, write the bmesh into a new mesh
    me = bpy.data.meshes.new('Mesh')
    bm.to_mesh(me)
    bm.free()

    # Add the mesh to the scene
    scene = bpy.context.scene
    obj = bpy.data.objects.new('Spaceship', me)
    # scene.objects.link(obj)
    scene.collection.objects.link(obj)

    # Select and make active
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    # scene.objects.active = obj
    # obj.select = True

    # Recenter the object to its center of mass
    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS')
    ob = bpy.context.object
    ob.location = (0, 0, 0)

    # Add a fairly broad bevel modifier to angularize shape
    if apply_bevel_modifier:
        bevel_modifier = ob.modifiers.new('Bevel', 'BEVEL')
        bevel_modifier.width = uniform(5, 20)
        bevel_modifier.offset_type = 'PERCENT'
        bevel_modifier.segments = 2
        bevel_modifier.profile = 0.25
        bevel_modifier.limit_method = 'NONE'

    # Add materials to the spaceship
    me = ob.data
    materials = create_materials()
    # materials = []
    for mat in materials:
        if assign_materials:
            me.materials.append(mat)
        else:
            me.materials.append(bpy.data.materials.new(name="Material"))

    return obj

if __name__ == "__main__":

    # When true, this script will generate a single spaceship in the scene.
    # When false, this script will render multiple movie frames showcasing lots of ships.
    generate_single_spaceship = True

    if generate_single_spaceship:
        # Reset the scene, generate a single spaceship and focus on it
        reset_scene()
        customseed = '' # add anything here to generate the same spaceship
        obj = generate_spaceship(customseed)

        # View the selected object in all views
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                ctx = bpy.context.copy()
                ctx['area'] = area
                ctx['region'] = area.regions[-1]
                bpy.ops.view3d.view_selected(ctx)
    else:
        # Export a movie showcasing many different kinds of ships

        # Settings
        output_path = '' # leave empty to use script folder
        total_movie_duration = 16
        total_spaceship_duration = 1
        yaw_rate = 45 # degrees/sec
        yaw_offset = 220 # degrees/sec
        camera_pole_rate = 1
        camera_pole_pitch_min = 15 # degrees
        camera_pole_pitch_max = 30 # degrees
        camera_pole_pitch_offset = 0 # degrees
        camera_pole_length = 10
        camera_refocus_object_every_frame = False
        fov = 60 # degrees
        fps = 30
        res_x = 1920
        res_y = 1080

        # Batch render the movie frames
        inv_fps = 1/float(fps)
        movie_duration = 0
        spaceship_duration = total_spaceship_duration
        scene = bpy.data.scenes["Scene"]
        scene.render.resolution_x = res_x
        scene.render.resolution_y = res_y
        scene.camera.rotation_mode = 'XYZ'
        scene.camera.data.angle = radians(fov)
        frame = 0
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        while movie_duration < total_movie_duration:
            movie_duration += inv_fps
            spaceship_duration += inv_fps
            if spaceship_duration >= total_spaceship_duration:
                spaceship_duration -= total_spaceship_duration

                # Generate a new spaceship
                reset_scene()
                obj = generate_spaceship()

                # look for a mirror plane in the scene, and position it just underneath the ship if found
                lowest_z = centre = min((Vector(b).z for b in obj.bound_box))
                plane_obj = bpy.data.objects['Plane'] if 'Plane' in bpy.data.objects else None
                if plane_obj:
                    plane_obj.location.z = lowest_z - 0.3

            # Position and orient the camera
            rad = radians(yaw_offset + (yaw_rate * movie_duration))
            camera_pole_pitch_lerp = 0.5 * (1 + cos(camera_pole_rate * movie_duration)) # 0-1
            camera_pole_pitch = camera_pole_pitch_max * camera_pole_pitch_lerp + \
                                camera_pole_pitch_min * (1 - camera_pole_pitch_lerp)
            scene.camera.rotation_euler = (radians(90 - camera_pole_pitch + camera_pole_pitch_offset), 0, rad)
            scene.camera.location = (sin(rad) * camera_pole_length,
                                     cos(rad) * -camera_pole_length,
                                     sin(radians(camera_pole_pitch))*camera_pole_length)
            if camera_refocus_object_every_frame:
                bpy.ops.view3d.camera_to_view_selected()

            # Render the scene to disk
            script_path = bpy.context.space_data.text.filepath if bpy.context.space_data else __file__
            folder = output_path if output_path else os.path.split(os.path.realpath(script_path))[0]
            filename = os.path.join('renders', timestamp, timestamp + '_' + str(frame).zfill(5) + '.png')
            bpy.data.scenes['Scene'].render.filepath = os.path.join(folder, filename)
            print('Rendering frame ' + str(frame) + '...')
            bpy.ops.render.render(write_still=True)
            frame += 1
