# 3D Effects

Every TTE effect already runs in 3D. Each character is a point in a 3D world, and the 2D canvas is one flat body in
that world, the **text plane**, which the camera looks straight at. A 2D effect never notices, because a character
that stays on the text plane lands exactly in the cell it would in 2D. A 3D effect tips the text plane, lifts characters
off it, adds bodies of its own and moves the camera.

This part of the guide explains the ideas behind that, in plain Python: where things sit, how they turn, how the world
becomes cells on a terminal, and what reads well at that resolution. By the end you should be able to predict what a
move will look like before you run it, and know where to look when the high-level calls don't do what you need.

!!! info "New in 0.16.0"

    The world and the `geometry3d` primitives are available on development `main` and are not in the published 0.15.0
    package.

## Two layers

| Layer | Module | What it gives you |
| --- | --- | --- |
| [The world](../../engine/world.md) | `terminaltexteffects.engine.world` and its neighbors | `terminal.world`: the text plane, the camera, the light and **bodies**, shapes you move, turn, draw and attach characters to. |
| [`geometry3d`](../../engine/utils/geometry3d.md) | `terminaltexteffects.utils.geometry3d` | The primitives underneath: vectors, rotations, the camera's projection, meshes, rasterizing into a depth buffer, wireframes and shading. |

Most effects only need the world. Each chapter shows the world's calls first, then the primitives they use, for the
times you want more control.

### Imports

The names an effect uses are on the top-level package, beside `Coord` and `Color`:

| Import | Gives you |
| --- | --- |
| `tte.shapes` | `Box`, `Cube`, `Cylinder`, `Plane`, `Prism`, `Pyramid`, `Sphere`, `Torus`, `Tetrahedron`, `Octahedron`, `Icosahedron`, and `Shape` for your own |
| `tte.looks` | `Shaded`, `Solid`, `Textured` and `Wireframe`, the looks `body.draw()` takes, and `Look`, any of them |
| `tte.Vec3`, `tte.Rotation` | Positions, directions and rotations |
| `tte.rotation_about` | A rotation from an axis name and degrees: `rotation_about("y", 45)` |
| `tte.Body` | The type of `world.body()`, for annotations |

```python
import terminaltexteffects as tte

ball = self.terminal.world.body(tte.shapes.Sphere(10)).draw(tte.looks.Shaded())
```

`from terminaltexteffects.shapes import Sphere` and `from terminaltexteffects.looks import Shaded` work too. The world
itself comes from the terminal, `self.terminal.world`, and the primitives under it from
`terminaltexteffects.utils.geometry3d`.

## Two ways to show things

A body reaches the screen in one of two ways, and most effects use one or both:

| | Attached characters | Drawn bodies |
| --- | --- | --- |
| What you call | `character.attach(body)`, or `body.surface.face("front").layout_text(characters)` | `body.draw(Shaded())`, `Solid()`, `Textured()` or `Wireframe()` |
| What moves | Your own characters, each a child of the body. A character's position is on the body's surface, or in its axes | Nothing of yours. The world fills cells with characters it owns |
| Each frame | The body's pose places each character in the world, and the camera **projects** it to one cell | The body's mesh is transformed and projected, each face is **rasterized** into the cells it covers, and **shading** or a texture picks each cell's symbol and color |
| Hiding | Nearer characters paint over farther ones in the same layer, and a character can't be seen from behind the camera | The same depth order, shared by every drawn cell and every character |
| Afterward | Characters stay yours: attach them back to the text plane and give them ordinary paths | The cells go when the body is erased or removed |

Attached characters keep everything a character has. Their paths, scenes, events and layers all work, and a path on a
body's surface travels over the shape. Drawn bodies are for solid shapes and decoration. [Texture
mapping](textures.md) compares the two with the same words.

## The frame loop

A 3D effect is an ordinary effect (see the Engine chapter on the [frame loop](../engine/frame-loop.md)). `update()`
already steps the world: it plays the camera's and bodies' tweens, moves bodies along their paths, works out where
every character lands, ticks the active characters and paints the drawn bodies. There is no extra call to make.

### A drawn body

A drawn body needs no characters of yours, so the world alone decides when the effect is done:

```python
from terminaltexteffects.looks import Shaded
from terminaltexteffects.shapes import Cube

# In the iterator's __init__:
self.world = self.terminal.world
self.cube = self.world.body(Cube(16)).draw(Shaded())
self.cube.spin("y", turns=1, frames=240)


# In __next__:
def __next__(self) -> str:
    if not self.world.animating:
        raise StopIteration
    self.update()
    return self.frame
```

The same loop works when only the camera moves. Leave the body still and queue a camera move instead:

```python
self.cube = self.world.body(Cube(16)).draw(Shaded())
self.world.camera.truck(12, frames=120)
```

`world.animating` stays true while the camera or any body has a tween queued or a body is moving along a path. [Moving the camera](camera-movement.md)
explains the controls.

### The text in 3D

The input characters start on the text plane, so the simplest 3D text effect turns the text plane itself:

```python
# In the iterator's __init__:
self.world = self.terminal.world
for character in self.terminal.get_characters():
    if character.input_symbol != " ":
        self.terminal.set_character_visibility(character, is_visible=True)
self.world.text_plane.spin("y", turns=1, frames=240)


# In __next__:
def __next__(self) -> str:
    if not self.world.animating and not self.active_characters:
        raise StopIteration
    self.update()
    return self.frame
```

- **Characters move with their body without ticking.** The world places every character on a moving body each frame,
  active or not. Add a character to `active_characters` only when it has its own path or scene to play.
- **`world.animating` tracks tweens, not characters.** It turns false when the camera and the bodies are done, while
  characters may still be on their paths. End on `active_characters` too, as above.
- **At rest, the text is home.** When the text plane is back at rest and the camera is at its starting view, every
  character on it is drawn in its input cell again.

## Running the examples

Every chapter has a small example effect with options. Each one lives in its own directory under
[`docs/effectguide/examples/3d/`](https://github.com/ChrisBuilds/terminaltexteffects/tree/main/docs/effectguide/examples/3d).
Save it in your community effects directory, as in the Engine chapters. The examples run on the same
[`concept_input.txt`](../engine/characters.md#seeing-the-orders) as the Engine chapters, on the canvas size printed
beside each example so the shapes have room. Most use 80 by 24; the camera lessons use 80 by 32 for captions and
framing:

```bash
tte --input-file concept_input.txt --canvas-width 80 --canvas-height 24 --anchor-text c cubes
```

The concept examples end by swapping their shapes for the input text, so you can see each idea on its own. The
[Recipes](recipes.md) combine several ideas into complete effects.

## Chapters

1. [3D in a terminal](terminal.md): what cells can and can't show.
2. [The world](world.md): nodes, bodies, the text plane, the screen and the root.
3. [Frames and coordinates](coordinates.md): where a position is measured, and what its numbers mean.
4. [Tall cells](tall-cells.md): why rows and columns aren't the same size, and how the camera corrects for it.
5. [Transforms](transforms.md): moving, turning and scaling, and why order matters.
6. [Rotation](rotation.md): axes, tumbles and getting back to rest.
7. [Camera and projection](camera.md): perspective, focal length, framing, view coordinates and the flat view.
8. [Moving the camera](camera-movement.md): travel, turning, aiming and orbiting a stationary scene.
9. [Attaching and detaching](attaching.md): moving characters between bodies, flights to moving targets, and coming
   home.
10. [Surfaces](surfaces.md): the grid over a shape, its faces, laying out text, and travelling over edges.
11. [Depth and hidden surfaces](depth.md): what hides what.
12. [Meshes](meshes.md): the built-in shapes and making your own.
13. [Light and shading](light.md): how faces get their symbols and colors.
14. [Texture mapping](textures.md): wrapping text over surfaces.
15. [Animating in 3D](animating.md): tweens, timing, what a character sees, and handing the text back to 2D.
16. [Performance](performance.md): what a frame costs.
17. [Recipes](recipes.md): a spinning logo, a die, a globe, a ticker and wireframe solids.

For a first camera experiment, try the [camera lab](camera-movement.md#run-the-camera-lab).

Then the [Spin tutorial](spin/01-sheet.md) builds a complete 3D effect in six steps.
