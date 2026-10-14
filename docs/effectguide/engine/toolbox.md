# Toolbox

The engine chapters cover the parts every effect uses. This page surveys the helpers effects reach for in particular
cases, with a link to the Reference page for each. All of them are public and can be imported as shown.

## Geometry

`terminaltexteffects.utils.geometry` finds coordinates for shapes and measures distances. Functions that work with
circles and distances account for terminal cells being about twice as tall as they are wide (see
[Distances are measured on screen](canvas.md#distances-are-measured-on-screen)).

| Function | Returns |
| --- | --- |
| `find_coords_on_circle(origin, radius, coords_limit=0)` | Coordinates on the outline of a circle that looks round on screen. With `coords_limit`, up to that many evenly spaced points. |
| `find_coords_in_circle(center, radius)` | Every coordinate inside such a circle. |
| `find_coords_on_rect(origin, half_width, half_height)` | Coordinates on the outline of a rectangle. |
| `find_coords_in_rect(origin, distance)` | Every coordinate in a square `distance` cells from `origin` in each direction. |
| `rasterize_line(start, end)` | One cell per step along a line, as for drawing it. |
| `rasterize_supercover_line(start, end)` | Every cell the line touches. |
| `find_coord_on_bezier_curve(start, control, end, t)` | The point a fraction `t` along a bezier curve. |
| `interpolate_coord(start, end, t)` | The point a fraction `t` along a straight line. |
| `extrapolate_along_ray(origin, target, offset_from_target)` | A point beyond `target`, continuing the line from `origin`. |
| `find_length_of_line(coord1, coord2)` | The on-screen distance between two coordinates. |
| `find_normalized_distance_from_center(bottom, top, left, right, coord)` | How far a coordinate is from the center of a rectangle, from 0 to 1. |

Circles are useful for rings, explosions, and orbits; lines for beams and trails. Results can include coordinates off
the canvas, which is fine for paths but not for looking up characters.

See the [geometry Reference](../../engine/utils/geometry.md).

## Easing beyond paths and scenes

Paths and scenes take an easing function directly. The `terminaltexteffects.utils.easing` module also has helpers for
easing anything else:

| Helper | Use |
| --- | --- |
| `make_easing(x1, y1, x2, y2)` | Builds a custom easing curve from two control points, like CSS `cubic-bezier()`. |
| `EasingTracker(easing_function, total_steps)` | Steps through an easing function: each `step()` returns the next eased value, for driving anything you update per tick, such as a radius or a count. |
| `SequenceEaser(sequence, easing_function, total_steps)` | Eases through a list: each `step()` returns the items newly reached, so you can release characters at an eased rate instead of a constant one. |

See the [easing Reference](../../engine/utils/easing.md).

## Particles

`ParticlePool`, exported by `terminaltexteffects`, creates and reuses helper characters for sparks, smoke, and debris.
See [Particles](../writing/patterns/particles.md) and the [`ParticlePool` Reference](../../engine/particles.md).

## Spanning trees

The generators in `terminaltexteffects.utils.spanningtree.algo` connect the characters into a tree, for effects that
grow, burn, or spread through the text, and `BreadthFirst` walks a finished tree. See
[Spanning trees](../writing/patterns/spanning-trees.md) and the
[spanning tree Reference](../../engine/utils/spanningtree/base_generator.md).

## Colors

`Animation.adjust_color_brightness(color, brightness)` returns a lighter or darker version of a color, for glows and
shadows without building a gradient. See [Color](color.md) for gradients, and the
[`Animation` Reference](../../engine/animation/animation.md).

## Where to go next

- [Patterns](../writing/patterns/phases.md) shows several of these helpers in complete effects.
