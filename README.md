# Spaceship Generator

A Blender script to procedurally generate 3D spaceships from a random seed.

![alt tag](https://raw.githubusercontent.com/a1studmuffin/SpaceshipGenerator/master/screenshots/spaceships_grid.jpg)

Usage
-----
* Install Blender: http://blender.org/download/
* Open a *Text Editor* view
* Press *Alt + O*, or go to *Text > Open Text Block* and open `spaceship_generator.py`
* Press *Alt + P* or click *Run script*

How it works
------------
* Start with a box.
* Build the hull: Extrude the front/rear faces several times, adding random translation/scaling/rotation along the way.
* Add asymmetry to the hull: Pick random faces and extrude them out in a similar manner, reducing in scale each time.
* Add detail to the hull: Categorize each face by its orientation and generate details on it such as engines, antenna, weapon turrets, lights etc.
* Sometimes apply horizontal symmetry.
* Add a Bevel modifier to angularize the shape a bit.
* Apply materials to the final result.
* Take over the universe with your new infinite fleet of spaceships.

Extreme examples
----------------
The following screenshots were created using extreme values for the number of hull segments and asymmetry segments to show how the algorithm works.

![alt tag](https://raw.githubusercontent.com/a1studmuffin/SpaceshipGenerator/master/screenshots/extreme_examples.jpg)

Credits
-------
Written for fun as part of the [/r/proceduralgeneration](https://www.reddit.com/r/proceduralgeneration/) June 2016 [monthly challenge](https://www.reddit.com/r/proceduralgeneration/comments/4mn9gj/monthly_challenge_7_june_2016_procedural/).

Released under the [MIT License].

Authored and maintained by Michael Davies.

> GitHub [@a1studmuffin](https://github.com/a1studmuffin)
> Twitter [@butterparty](https://twitter.com/butterparty)

[MIT License]: http://mit-license.org/
