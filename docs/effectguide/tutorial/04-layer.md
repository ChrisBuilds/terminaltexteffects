# Step 4: Layer

At the end of step 3, every character was on layer 0, so a flying character could be hidden behind one that had already
landed. In this step two events keep moving characters in front: one raises a character to layer 1 when its path
starts, and the other lowers it back to layer 0 when it lands.

**Engine chapters used:** [Characters](../engine/characters.md#visibility-activity-and-layers),
[Events](../engine/events.md).

## Update the module

Replace `myspray.py` with this version:

```python title="myspray.py" hl_lines="11 65-76"
--8<-- "docs/effectguide/examples/myspray_step4/myspray.py"
```

## What changed

`build()` registers two events on each character's path, between creating the path and activating it:

- `PATH_ACTIVATED` with `SET_LAYER` and target `1`: when the path starts, the character moves to layer 1.
- `PATH_COMPLETE` with `SET_LAYER` and target `0`: when the character reaches home, it returns to layer 0.

Characters on a higher layer are drawn on top, so a flying character on layer 1 always shows in front of the settled
characters on layer 0.

The order matters. `PATH_ACTIVATED` fires the moment `activate_path()` is called, here during `build()`, long before
the character is released. Registering the event after `activate_path()` would miss it, and the character would stay
on layer 0. Because the layer is set during `build()`, every queued character is already on layer 1 when it is released.

`Path` also has a `layer` argument that does the same as the first event. MySpray uses events to match the built-in
Spray effect, and because the second event, lowering the layer on landing, has no shortcut.

## Run it

```bash
tte --input-file tutorial_input.txt myspray
```

The animation looks like step 3, except that flying characters now always pass in front of characters that have
already landed:

![MySpray after step 4: flying characters pass in front of landed ones](../../img/effectguide/myspray_step4_demo.webp)

## Next step

Step 5 colors the characters: each one fades from a random color into its place in a gradient across the text.
