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
| [`Space3D`](../../engine/space3d.md) | `terminaltexteffects.engine.space3d` | A camera, a light and **bodies**: shapes you move, turn and animate, viewed through a camera you can also move and aim. You mount your characters on bodies, or draw the bodies as filled surfaces. |
| [`geometry3d`](../../engine/utils/geometry3d.md) | `terminaltexteffects.utils.geometry3d` | The primitives underneath: vectors, rotations, the camera's projection, meshes, rasterizing into a depth buffer, wireframes and shading. |

Most effects only need `Space3D`. Each chapter shows the `Space3D` calls first, then the primitives they use, for
the times you want more control.

## Two ways to show things

A body reaches the screen in one of two ways, and most effects use one or both:

| | Mounted characters | Drawn surfaces |
| --- | --- | --- |
| What you call | `body.add_chars(characters, anchors)` or `space.mount(character, anchor)` | `body.draw(Shaded())`, `Solid()`, `Textured()` or `Wireframe()` |
| What moves | Your own characters, each riding one **anchor**: a point on the body | Nothing of yours. The space fills cells with characters it owns |
| Each frame | The body's transform places each anchor in the world, the camera **projects** it to one cell, and the character moves there whole | The body's mesh is transformed and projected, each face is **rasterized** into the cells whose centers it covers, a **depth buffer** keeps the nearest face per cell, and **shading** or a texture picks each cell's symbol and color |
| Hiding | Characters are ordered by layer, which `layer_by_depth` raises for nearer ones | The depth buffer, shared by every drawn body |
| Afterward | Release the characters back to ordinary 2D paths and scenes | The cells disappear when the body is erased or removed |

The chapters follow that order: [coordinates](coordinates.md), [transforms](transforms.md) and
[rotation](rotation.md) place points; the [camera](camera.md) projects them; [depth](depth.md),
[meshes](meshes.md), [light](light.md) and [textures](textures.md) turn faces into cells. Mount text that has to land
somewhere or carry its own colors and scenes; draw a surface for solid shapes and decoration. [Texture
mapping](textures.md#mounted-text-or-textured-surface) compares the two with the same words.

## The frame loop

A 3D effect is an ordinary effect (see the Engine chapter on the [frame loop](../engine/frame-loop.md)) with one
extra call per frame, before `update()`. `space.step()` plays the camera's and bodies' queued animations, redraws any drawn
surfaces and works out where every mounted anchor lands. `update()` then ticks the active characters, and a mounted
character's tick moves it to its anchor's cell.

### A drawn surface

A drawn body needs no characters of yours, so the space alone decides when the effect is done:

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

The same loop works when only the camera animates. Leave the body still and queue a viewpoint move instead:

```python
self.space = Space3D(self.terminal)
self.cube = self.space.body(Cube(16)).draw(Shaded())
self.space.camera.truck(12, frames=120)
```

`space.animating` stays true for that camera queue. [Moving the camera](camera-movement.md) explains the controls.

### Mounted text

Mounted characters are your own characters, so the usual lifecycle still applies, with three additions:

```python
from terminaltexteffects.engine.space3d import Space3D

# In the iterator's __init__:
self.space = Space3D(self.terminal)
characters = [character for character in self.terminal.get_characters() if character.input_symbol != " "]
for character in characters:
    self.terminal.set_character_visibility(character, is_visible=True)  # Shown...
    self.active_characters.add(character)  # ...and ticked by update().
self.sheet = self.space.body()
self.sheet.add_chars(characters, self.sheet.text_plane(characters))
self.sheet.spin("y", turns=1, frames=240)
self.sheet.on_complete(lambda sheet: sheet.release_all())  # Hand the text back when the spin ends.


# In __next__:
def __next__(self) -> str:
    if not self.space.animating and not self.active_characters:
        raise StopIteration
    self.space.step()
    self.update()
    return self.frame
```

- **Mounting doesn't show or tick a character.** Visibility and membership in `active_characters` are separate, as
  in any effect. A hidden mounted character still moves; one that isn't in `active_characters` never ticks, so it
  stays where it was.
- **An active mount keeps its character active.** Mounted characters never finish on their own, even after the
  body's tweens end and any blend toward the anchor is over, so `update()` never drops them. Release them, as
  `on_complete` does here, or the effect never ends.
- **`space.animating` tracks camera and body tweens.** It turns false when all their queues are empty, while mounted characters,
  blends and any 2D paths you start after release may still be moving. End on `active_characters` too, as above.

Bodies own no characters. A drawn body shows itself with characters the space creates, and characters you mount
stay yours: their scenes, events and layers keep working, and you can release them back to ordinary paths at any time.
[Animating in 3D](animating.md#mount-readings) covers what a mount reports each frame and how to hand text off to 2D.

## Running the examples

Every chapter has a small example effect with options. Each one lives in its own directory under
[`docs/effectguide/examples/3d/`](https://github.com/ChrisBuilds/terminaltexteffects/tree/main/docs/effectguide/examples/3d).
Save it in your community effects directory, as in the Engine chapters. The examples run on the same
[`concept_input.txt`](../engine/characters.md#seeing-the-orders) as the Engine chapters, on the canvas size printed beside each example so the
shapes have room. Most use 80 by 24; the camera lessons use 80 by 32 for captions and framing:

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
6. [Camera and projection](camera.md): perspective, focal length, framing, view coordinates and the flat view.
7. [Moving the camera](camera-movement.md): travel, turning, aiming and orbiting a stationary scene.
8. [Depth and hidden surfaces](depth.md): what hides what.
9. [Meshes](meshes.md): the built-in shapes and making your own.
10. [Light and shading](light.md): how faces get their symbols and colors.
11. [Texture mapping](textures.md): wrapping text over surfaces.
12. [Animating in 3D](animating.md): tweens, timing and handing the text back to 2D.
13. [Performance](performance.md): what a frame costs.
14. [Recipes](recipes.md): a spinning logo, a die, a globe, a ticker and wireframe solids.

For a first camera experiment, try the [camera lab](camera-movement.md#run-the-camera-lab).

Then the [Spin tutorial](spin/01-sheet.md) builds a complete 3D effect in six steps.
