# 3D Effects

TTE can move characters through 3D space and draw solid shapes, all in plain Python. This part of the guide explains
the ideas behind it: where things sit, how they turn, how a 3D scene becomes cells on a terminal, and what reads well
at that resolution. By the end you should be able to predict what a transform will look like before you run it, and
know where to look when the high-level calls don't do what you need.

!!! info "New in 0.16.0"

    `Space3D` and the `geometry3d` primitives are available on development `main` and are not in the published 0.15.0
    package.

## Two layers

| Layer | Module | What it gives you |
| --- | --- | --- |
| [`Space3D`](../../engine/space3d.md) | `terminaltexteffects.engine.space3d` | A camera, a light and **bodies**: shapes you move, turn and animate. You mount your characters on bodies, or draw the bodies as filled surfaces. |
| [`geometry3d`](../../engine/utils/geometry3d.md) | `terminaltexteffects.utils.geometry3d` | The primitives underneath: vectors, rotations, the camera's projection, meshes, rasterizing into a depth buffer, wireframes and shading. |

Most effects only need `Space3D`. Each chapter shows the `Space3D` calls first, then the primitives they use, for
the times you want more control.

## The frame loop

A 3D effect is an ordinary effect with one extra call per frame. `space.step()` plays the bodies' queued animations,
redraws any drawn surfaces and works out where every mounted character lands. `update()` then moves the characters
there, as usual:

```python
from terminaltexteffects.engine.space3d import Cube, Shaded, Space3D

# In the iterator's __init__:
self.space = Space3D(self.terminal)
self.cube = self.space.body(Cube(16)).draw(Shaded())
self.cube.spin("y", turns=1, frames=240)


# In __next__:
def __next__(self) -> str:
    if not self.space.animating:
        raise StopIteration
    self.space.step()
    self.update()
    return self.frame
```

Bodies own no characters. A drawn body shows itself with characters the space creates, and characters you mount
stay yours: their scenes, events and layers keep working, and you can release them back to ordinary paths at any time.

## Running the examples

Every chapter has a small example effect with options. Each one lives in its own directory under
[`docs/effectguide/examples/3d/`](https://github.com/ChrisBuilds/terminaltexteffects/tree/main/docs/effectguide/examples/3d).
Save it in your community effects directory, as in the Engine chapters. The examples run on the same
[`concept_input.txt`](../engine/characters.md#seeing-the-orders) as the Engine chapters, on an 80 by 24 canvas so the
shapes have room:

```bash
tte --input-file concept_input.txt --canvas-width 80 --canvas-height 24 --anchor-text c cubes
```

The concept examples end by swapping their shapes for the input text, so you can see each idea on its own. The
[Recipes](recipes.md) combine several ideas into complete effects.

## Chapters

1. [3D in a terminal](terminal.md): what cells can and can't show.
2. [Space and coordinates](coordinates.md): where things sit.
3. [Tall cells](tall-cells.md): why rows and columns aren't the same size, and how the camera corrects for it.
4. [Transforms](transforms.md): moving, turning and scaling, and why order matters.
5. [Rotation](rotation.md): axes, tumbles and getting back to rest.
6. [Camera and projection](camera.md): perspective and the flat view.
7. [Depth and hidden surfaces](depth.md): what hides what.
8. [Meshes](meshes.md): the built-in shapes and making your own.
9. [Light and shading](light.md): how faces get their symbols and colors.
10. [Texture mapping](textures.md): wrapping text over surfaces.
11. [Animating in 3D](animating.md): tweens, timing and handing the text back to 2D.
12. [Performance](performance.md): what a frame costs.
13. [Recipes](recipes.md): a spinning logo, a die, a globe, a ticker and wireframe solids.
