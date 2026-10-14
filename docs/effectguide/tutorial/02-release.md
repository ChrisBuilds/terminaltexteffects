# Step 2: Release

In step 1 the whole text appeared in a single frame. Spray builds the text up instead, releasing characters in a
random order, a few per frame. In this step you add that timing, before any character moves.

**Engine chapters used:** [Frame loop](../engine/frame-loop.md), [Characters](../engine/characters.md).

## Update the module

Replace `myspray.py` with this version:

```python title="myspray.py" hl_lines="8 11 40-48 50-60"
--8<-- "docs/effectguide/examples/myspray_step2/myspray.py"
```

## What changed

### A queue of characters

`build()` puts every character in `self.pending_chars` and shuffles it, so the release order is random. Spray keeps
setup in a `build()` method called from `__init__`; the setup grows over the next steps.

`self._volume` is the most characters to release in one frame: 0.5% of the text, and at least one. The tutorial input
has 121 characters, so its volume is 1; text with 2,000 characters would release up to 10 per frame.

### Releasing characters each frame

Each call to `__next__` now does three things:

1. It pops between 1 and `self._volume` characters off the queue, makes each one visible, and adds it to
   `self.active_characters`.
2. It calls `self.update()`, which ticks the active characters.
3. It returns the frame.

The effect ends when the queue is empty and no character is active.

Released characters have no path or scene yet, so they finish on their first tick and `update()` removes them from
`active_characters` straight away. They stay visible, so they stay on screen. Adding them to `active_characters` now
means they start moving once step 3 gives them somewhere to go.

## Run it

```bash
tte --input-file tutorial_input.txt myspray
```

The characters appear one at a time in a random order until the text is complete:

![MySpray after step 2: characters appear one at a time in random order](../../img/effectguide/myspray_step2_demo.webp)

The order is random, so each run fills in differently.

## Next step

Step 3 starts every character at the edge of the canvas and sends it to its place in the text.
