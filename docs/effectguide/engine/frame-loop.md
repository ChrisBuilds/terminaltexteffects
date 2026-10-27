# Frame loop

An effect is an iterator: each call to `next()` advances the animation by one **tick** and returns one **frame**, the
whole canvas rendered as a string. This chapter explains what happens during that call and how an effect decides when
it is finished.

## One frame, step by step

``` mermaid
sequenceDiagram
    participant Caller as tte or your code
    participant It as Your iterator
    participant W as World
    participant Ch as Active characters
    participant T as Terminal
    Caller->>It: next()
    It->>It: effect logic (release characters, change phase)
    It->>W: update(): step the world
    It->>Ch: tick each active character
    Ch->>Ch: motion.move(), then animation.step_animation()
    It->>It: drop characters that are no longer active
    It->>W: paint drawn bodies
    It->>T: frame: wait for the frame rate, then render
    T-->>It: frame string
    It-->>Caller: frame string
```

Most `__next__` methods follow the same shape. This one is from the built-in Spray effect:

```python
def __next__(self) -> str:
    if self.pending_chars or self.active_characters:
        # Effect logic: release a few more characters this frame.
        ...
        self.update()
        return self.frame
    raise StopIteration
```

1. **Effect logic.** Your code decides what changes this frame: which characters appear, which phase the effect is
   in, what new paths or scenes to start. Keep it cheap, since it runs every frame; do expensive setup once, when the
   iterator is created.
2. **`self.update()`** steps the world, ticks every character in `self.active_characters`, removes the ones that have
   finished, and paints any drawn bodies.
3. **`self.frame`** waits until the next frame is due, then asks the terminal to render the canvas.
4. **`StopIteration`** ends the effect once nothing is left to do.

## The world's part

Every terminal has a 3D [world](../3d/world.md), `self.terminal.world`, and every character sits in it, on the flat
**text plane** the camera looks straight at. `update()` steps the world before the characters tick: it plays camera
and body tweens, moves bodies along their paths, and when the view changed, projects every character to its cell
again. After the ticks it paints any bodies the effect drew.

A 2D effect never moves the camera or the text plane, so stepping the world does nothing visible and costs almost
nothing: a character on the text plane at rest is drawn in exactly the cell its position names. The
[3D Effects](../3d/index.md) part of the guide covers what the world can do.

## Ticking a character

[`EffectCharacter.tick()`](../../engine/basecharacter.md) does two things, in this order:

1. `motion.move()` moves the character one step along its active path, if it has one, and fires path events such
   as `PATH_COMPLETE`.
2. `animation.step_animation()` advances its active scene, if it has one, and fires scene events such as
   `SCENE_COMPLETE`.

Motion runs first so that a scene synced to movement sees this tick's position.

A character is **active** while it has an unfinished path or an unfinished scene. `update()` checks this after every
tick and removes characters that are no longer active from `active_characters`. A character with a looping path or
looping scene never finishes on its own, so it stays active until your code deactivates it.

## Active and visible are separate

Two independent flags decide what a character does:

| | Visible | Hidden |
| --- | --- | --- |
| **Active** | Moves and changes, and is drawn. The usual state while animating. | Moves and changes, but isn't drawn. Useful for staging a character before it appears. |
| **Inactive** | Drawn as it last looked, without changing. The usual state once a character has settled. | Neither drawn nor updated. Every character starts this way. |

- Make a character visible with `self.terminal.set_character_visibility(character, is_visible=True)`.
- Make it active by adding it to `self.active_characters`. `update()` removes it again when it finishes.

Forgetting either step is the most common reason a new effect shows nothing, or shows characters that never move.

## Frame rate and time

`self.frame` paces output to `TerminalConfig.frame_rate`, 60 frames per second by default. It sleeps if the
previous frame was returned less than one frame period ago, then renders. A frame rate of `0` turns pacing off.

Because pacing happens inside `self.frame`, read it once per `next()` call. Your effect logic should count in ticks
rather than seconds: "release 5 characters per frame" or "hold for 30 frames". When a phase must last a fixed time,
measure it with `self.terminal.clock()` instead of the system clock. During recording, `tte --export` runs the clock
one frame period per frame, so the phase lasts the same number of frames however fast the machine renders.

## Ending the effect

Raise `StopIteration` when there is nothing left to show. Typical conditions are:

- No characters are waiting to be released and none are active, as in Spray.
- The effect's last phase has finished.

Effects that loop forever never raise `StopIteration`. They are valid, and the library guide shows how to
[stop them](../../libguide.md#infinitely-looping-effects); give them an option that limits the number of loops.

## Who prints the frames

Your iterator only returns strings. Printing them is the caller's job:

```python
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

[`terminal_output()`](../../engine/baseeffect.md#terminaltexteffects.engine.base_effect.BaseEffect.terminal_output)
makes room for the canvas and hides the cursor, and restores the cursor when the loop ends, even after an error.
The `tte` command runs this same loop, so you don't need to handle terminal setup in your effect.

## Where to go next

- [Tutorial step 1: Scaffold](../tutorial/01-scaffold.md) writes a `__next__` method that returns a single frame.
- [Architecture](architecture.md) shows how the iterator fits with the other parts of an effect.
