# Performance

TTE aims for 60 frames per second. Each frame has about 16 milliseconds for your `__next__`, the character updates,
and drawing the frame. If a frame takes longer, the animation slows down: TTE never skips frames to catch up. This
chapter explains where a frame's time goes and how to keep it short on large input.

## Where the time goes

Every frame does three kinds of work:

| Work | Grows with | Cost |
| --- | --- | --- |
| Your code in `__next__` | Whatever it loops over | Anything that scans every character costs that much on every frame. |
| `update()` | The number of **active** characters | Each active character moves along its path and steps its scene. |
| Drawing the frame | The number of **visible** characters | Each visible character is placed into its row of the output. |

Visible and active are separate (see [The frame loop](frame-loop.md)). A character that has finished moving and
animating, but is still shown, costs only drawing. That is why effects remove finished characters from
`active_characters`, which `update()` does automatically, and only add a character when it has something to do.

Setup, in the iterator's `__init__()`, runs once. Moving work there from `__next__` almost always pays off.

## Keeping frames fast

- **Compute once.** Build gradients, coordinate color mappings, character groups, and spanning trees during setup,
  not per frame. Glow, Paint, and MySpray build every scene before the first frame.
- **Don't scan every character per frame.** Keep lists of the characters each phase needs, such as MySpray's
  `pending_chars`, and take from them, instead of filtering `terminal.get_characters()` every tick.
- **Keep the active set small.** Release characters as they are needed, and let finished ones become inactive.
- **Cap particles.** Give a `ParticlePool` a `max_size` so large input can't create unlimited particles (see
  [Particles](../writing/patterns/particles.md#when-the-pool-is-full)).
- **Avoid needless fill characters.** Fill characters are created only when first requested. Ask for
  `inner_fill_chars` or `outer_fill_chars` only when the effect animates empty cells, since outer fill on a large
  canvas adds many characters.

## Engine options for large effects

These options trade memory or setup for speed. Each helps only some effects, so measure before and after.

| Option | Helps when |
| --- | --- |
| `new_scene(cache_easing=True)` | Many characters play eased scenes with the same built-in easing function and length. The frame schedule is computed once and shared. |
| `new_scene(cache_appearance=True)` | Many characters build frames with the same symbols and colors. The encoded appearance strings are shared while the scenes are built. |
| `terminal.enable_row_cache()` | Most rows of the output stay the same from one frame to the next, for example when a few characters move over settled text. Unchanged rows are reused instead of drawn again. |

Call `enable_row_cache()` once during setup. Changes to a character's position, visibility, layer, or appearance mark
its row as changed, so the output stays correct. When most rows change every frame, the tracking costs time and saves
none, which is why the cache is off by default.

## Measuring

To see how fast your effect runs without the frame-rate limit, time it with `--frame-rate 0` and discard the output:

```bash
time tte --input-file large_input.txt --frame-rate 0 myspray > /dev/null
```

Compare runs before and after a change, on the same input. Use input at least as large as your users are likely to
send, and try `--canvas-width 0 --canvas-height 0` to fill the terminal.

In a TTE repository checkout, the benchmark harness in `tools/perf/` finds effects the same way `tte` does, so it can
measure your effect too, including one in a directory named by `TTE_DEV_EFFECTS_DIR`. It reports build and render times separately and can profile a run.
[Performance Testing](../../performance.md) explains how to use it.

## Where to go next

- [The frame loop](frame-loop.md) covers `update()`, `active_characters`, and the frame rate.
- [Conventions and quality](../writing/conventions.md#edge-case-checklist) lists the inputs to test, including large
  ones.
