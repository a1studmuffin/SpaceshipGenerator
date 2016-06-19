#!/usr/bin/env python

from os.path import abspath, dirname, join as pjoin
import zipfile

SRC_DIR = dirname(abspath(__file__))

with zipfile.ZipFile('add_mesh_SpaceshipGenerator.zip', 'w', zipfile.ZIP_DEFLATED) as arch:
    for filename in [
            '__init__.py',
            'spaceship_generator.py',
            'textures/hull_normal.png',
            'textures/hull_lights_emit.png',
            'textures/hull_lights_diffuse.png']:
        arch.write(pjoin(SRC_DIR, filename), 'add_mesh_SpaceshipGenerator/'+filename)

print('created file: add_mesh_SpaceshipGenerator.zip')
