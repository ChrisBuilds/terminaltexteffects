# World

*Modules*: `terminaltexteffects.engine.world`, `camera`, `tweens`, `shapes`, `surfaces`, `drawing`, `view`

!!! info "New in 0.16.0"

    The world is available on development `main` and is not in the published 0.15.0 package.

Every terminal has a world, `terminal.world`: a tree of **nodes** in 3D, a camera and a light. Characters and bodies
are nodes. A **body** has a position, rotation and scale, and the nodes attached to it move, turn and scale with it.
A body with a shape has a **surface**, a grid of cells over the shape that characters sit on and travel over.

- `world.root` never moves; free nodes are its children.
- `world.text_plane` is the flat body the input characters start on, at their input cells. Turn or move it and the
  text goes with it.
- `world.screen` is fixed to the canvas: characters attached to it stay on their cells whatever the camera does, for
  labels and overlays.
- `world.body(shape, at=...)` makes a body. `body.draw(look)` draws it with characters the world adds, and
  `world.remove(body)` takes it out.
- `world.camera` projects the world onto the canvas, and moves now or over frames. `world.set_light()` points the
  light.

Units are columns; a row is two units tall. The origin is the middle of the canvas, +x is right, +y is up and +z points
toward the default camera. Angles are degrees.

## A frame

`update()` plays one frame: the world steps (camera and body tweens, then body paths, then tween callbacks), every
character is projected again if the view changed, active characters tick, and the world paints drawn bodies. Characters
and drawn cells are painted farther first, so the nearest wins each cell. A character facing the camera on a drawn
body's surface draws over the body's own cell beneath it.

## Turning and scaling bodies

`rotate`, `reset` and the `position`, `rotation` and `scale` setters change a body now. `spin`, `settle`, `turn_to`,
`turn_to_rest`, `random_pose`, `scale_to` and `hold` queue tweens that the world plays one frame at a time, one after
another or alongside the last with `together=True`. Tweens apply their change as a delta, so they compose with each
other and with changes made now. `on_complete` and `on_group_complete` run callbacks once every body and the camera
have moved. Bodies move over frames along `body.motion` paths, like characters.

## Reading the view

`character.view` reports how a character is seen this frame: its `cell`, `depth`, `nearness`, whether it is `facing`
the camera and by how much, the `light` on it and the `face` of its parent's surface it is on. Scenes synced to
`LIGHT` or `DEPTH` read it. A character behind the camera is hidden, and so is one facing away on a body with
`hide_facing_away` set; it shows again once the view sees it.

::: terminaltexteffects.engine.world

::: terminaltexteffects.engine.camera

::: terminaltexteffects.engine.tweens

::: terminaltexteffects.engine.view

::: terminaltexteffects.engine.shapes

::: terminaltexteffects.engine.surfaces

::: terminaltexteffects.engine.drawing
