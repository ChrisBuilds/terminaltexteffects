# Performance

A frame has about 16 milliseconds at 60 frames per second (see the Engine chapter on
[Performance](../engine/performance.md)). 3D adds one call to the frame, `space.step()`, and that call is usually
the most expensive thing in it. This chapter shows what it costs and how to keep it inside the budget.

## The idea

`step()` does two kinds of work, and they grow with different things:

| Work | Grows with |
| --- | --- |
| Drawing surfaces | The number of **triangles** in drawn bodies, and the number of **cells** they cover. Each triangle is projected and filled cell by cell into the depth buffer. |
| Placing mounted characters | The number of **mounted characters**. Each one is turned, moved and projected to a cell. |

Bodies that are neither drawn nor carrying characters cost almost nothing. A body that has finished its tweens and
hasn't moved is still drawn every frame, because the space doesn't know whether anything else in the scene changed.

## Measured costs

These are the guide's own examples on an 80 by 24 canvas, timed with the frame-rate limit off. The numbers come from
one machine. Yours will differ, but the ratios hold.

| Example | What it draws | Time per frame |
| --- | --- | --- |
| [Wireframe solids](recipes.md#wireframe-solids) | Four solids as edges | 1.9 ms |
| [Card](depth.md) | Mounted text on a plane | 2.9 ms |
| [Cubes](terminal.md) | Three shaded cubes | 3.1 ms |
| [Spinning logo](recipes.md#spinning-logo) | Mounted text with lighting scenes | 3.3 ms |
| [Depth](depth.md) | A cube and a sphere, see-through | 4.0 ms |
| [Light](light.md) | A shaded sphere | 6.2 ms |
| [Light](light.md) `--shape torus` | A shaded torus | 7.7 ms |
| [Gallery](meshes.md) | Ten shapes | 7.8 ms |
| [Texture](textures.md) `--text` | A textured cube | 8.8 ms |
| [Globe](recipes.md#globe) | A textured sphere, 48 by 24, back faces shown | 23.5 ms |

The globe is the only one over budget, so it plays at about 43 frames per second instead of 60. Here's the same
sphere drawn different ways, measuring `step()` alone:

| Sphere, radius 20 | Time per step |
| --- | --- |
| 24 by 12, `Shaded()` | 6.2 ms |
| 48 by 24, `Shaded()` | 12.1 ms |
| 24 by 12, `Textured(back="dim")` | 11.5 ms |
| 48 by 24, `Textured()` | 12.8 ms |
| 48 by 24, `Textured(back="dim")` | 23.4 ms |

Two things stand out:

- **Doubling the segments and rings doubles the cost**, even though the sphere covers the same cells. Four times the
  triangles, but each one covers fewer cells.
- **Showing back faces doubles it again.** `back="dim"` fills the far side too, so the space rasterizes the shape
  twice.

Mounted characters cost about 9 microseconds each per step. The concept input's 304 characters take under 3 ms. A
full 200 by 50 screen of text, 5,760 characters, takes about 52 ms, before `update()` moves any of them.

## In TTE

- **Use as few triangles as read well.** At terminal resolution, a sphere with 24 segments and 12 rings looks as
  round as one with 48 and 24 unless it's very large. Raise the counts only when you see facets.
- **Show back faces only when they add something.** `Textured(back=...)` and `Wireframe(hidden_color=...)` draw the
  far side. Leave them off when the front hides it anyway.
- **Erase what's off screen or finished.** `body.erase()` stops drawing a body, and `space.step()` hides its surface
  characters. A body you've moved out of view is still drawn until you erase it.
- **Mount only the characters you need.** Mount the visible text, not the spaces between it, as `text_plane` examples
  do by skipping blank input cells.
- **Release finished characters.** `release_all()` hands characters back to 2D paths, which cost only their own
  `update()`.
- **Watch the count of drawn bodies.** Ten shapes in the gallery cost about twice one sphere. Many small shapes cost
  more than a few large ones and read worse (see [3D in a terminal](terminal.md)).

## Measuring

Time your effect with the frame-rate limit off, as in the Engine chapter:

```bash
time tte --input-file concept_input.txt --canvas-width 80 --canvas-height 24 --anchor-text c --frame-rate 0 globe > /dev/null
```

Divide the time by the number of frames to get the cost per frame. To find where the time goes, run the effect under
Python's profiler, sorted by the time spent inside each function. The table prints after the last frame, at the end
of the file:

```bash
python -m cProfile -s tottime -m terminaltexteffects --input-file concept_input.txt --frame-rate 0 globe > profile.txt
```

In a 3D effect, `rasterize` near the top means surfaces dominate, so cut triangles or back
faces. `project` and `apply` near the top, without `rasterize`, mean mounted characters dominate, so mount fewer. In a TTE checkout,
the harness in `tools/perf/` measures and profiles effects too (see [Performance Testing](../../performance.md)).

## At cell resolution

- The terminal shows at most a few thousand cells, so detail past that is wasted work. If two meshes look the same
  on screen, use the smaller one.
- A large shape fills more cells, so it costs more to draw than a small one with the same triangles. That's still
  usually the right trade, since large shapes read better.
- Test on a full-size terminal with `--canvas-width 0 --canvas-height 0`, since mounted text and surfaces both grow
  with the canvas.
