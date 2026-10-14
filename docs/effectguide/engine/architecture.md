# Architecture

Every TTE effect is built from the same four parts: an **effect**, its **configuration**, an **iterator** that
produces frames, and a **terminal** that owns the characters. This chapter explains what each part does and how
input text becomes animation frames.

## The four parts

``` mermaid
flowchart TB
    module["effect module<br/>get_effect_resources()"] --> effect
    module --> config
    config["Config<br/>(BaseConfig subclass)"] --> effect["Effect<br/>(BaseEffect subclass)"]
    effect -- "iter(effect)" --> iterator["Iterator<br/>(BaseEffectIterator subclass)"]
    iterator -- builds --> terminal[Terminal]
    terminal -- creates --> characters["EffectCharacter<br/>one per non-space symbol"]
    iterator -- "next() returns" --> frame["frame string"]
```

| Part | Base class | Responsibility |
| --- | --- | --- |
| Effect | [`BaseEffect`](../../engine/baseeffect.md) | Holds the input text, the effect configuration, and the terminal configuration. Creates a fresh iterator each time it is iterated. |
| Configuration | [`BaseConfig`](../../engine/baseconfig.md) | A dataclass of the effect's options. The same fields drive the command-line parser and library defaults. |
| Iterator | [`BaseEffectIterator`](../../engine/baseeffect.md) | Sets up the animation, then returns one frame string per `next()` call until the effect ends. |
| Terminal | [`Terminal`](../../engine/terminal/terminal.md) | Parses the input into characters, lays them out on a canvas, tracks which are visible, and renders frames. |

An effect module ties the parts together with one function, `get_effect_resources()`, which returns the command name
and the effect and configuration classes. TTE calls it when it discovers the module, as described in
[How TTE finds your effect](#how-tte-finds-your-effect) below.

## From input text to frames

When you run `printf 'Hello' | tte spray`, or iterate over an effect in Python, this happens:

1. **The effect is created.** `BaseEffect.__init__` stores the input text and builds default configurations unless
   you pass your own. Nothing is drawn yet.
2. **An iterator is created.** `iter(effect)` builds a new iterator. `BaseEffectIterator.__init__` deep-copies the
   effect configuration and builds a `Terminal` for the input. If the input contains no visible characters, it raises
   `EmptyInputError`.
3. **The terminal makes characters.** The `Terminal` parses the input (including any ANSI colors), measures the
   available space, creates a [`Canvas`](../../engine/terminal/canvas.md), and creates one
   [`EffectCharacter`](../../engine/basecharacter.md) for each non-space input symbol. Each character remembers its symbol and
   its home position, `input_coord`. All characters start hidden.
4. **Your iterator builds the animation.** In its `__init__`, your iterator gives characters their starting
   positions, paths to follow, and scenes to play, and decides when each one appears.
5. **Frames are produced.** Each `next()` call advances the animation by one step and returns the terminal's
   rendering as a string. When the effect is finished, `next()` raises `StopIteration`.
6. **Something prints the frames.** The `tte` command, or your own code, prints each frame. The effect itself never
   writes to the terminal.

Because the iterator holds all animation state, iterating the same effect twice plays the animation twice from the
start, and an effect can be reused with different configurations.

## Characters own their behavior

TTE treats every character on screen as an independent object. An `EffectCharacter` carries three helpers:

- **`motion`** ([`Motion`](../../engine/motion/motion.md)) moves the character along paths made of waypoints.
- **`animation`** ([`Animation`](../../engine/animation/animation.md)) changes the character's symbol and colors by
  playing scenes made of frames.
- **`event_handler`** ([`EventHandler`](../../engine/eventhandler.md)) reacts when a path or scene starts or
  finishes, for example by starting the next scene.

Your iterator configures these helpers up front, then mostly steps back. Each frame, the engine advances every active
character by one tick, and the terminal draws each visible character at its current position with its current
appearance. The [Frame loop](frame-loop.md) chapter covers that cycle in detail.

This design keeps effects short. The built-in Spray effect, for example, gives every character a path to its home
position and a scene that fades its color, then only decides how many characters to release each frame.

## Two configurations

An effect has two configuration objects:

- **The effect configuration** is your `BaseConfig` subclass. It holds options specific to your effect, such as
  movement speed or gradient colors.
- **The terminal configuration**, [`TerminalConfig`](../../engine/terminal/terminalconfig.md), holds options every
  effect shares: frame rate, canvas size and anchoring, color handling, tab width, and so on. Your effect reads it as
  `self.terminal.config` but doesn't define it.

The Configuration and the CLI chapter explains how a configuration dataclass becomes command-line options.

## How TTE finds your effect

TTE builds its command-line parser from every effect module it can find:

- Built-in effects in the `terminaltexteffects.effects` package.
- Community effects: every `.py` file in `${XDG_CONFIG_HOME:-$HOME/.config}/terminaltexteffects/effects` that
  defines `get_effect_resources()`.

Each module must return a unique command name. If two modules return the same name, TTE reports a duplicate effect
command and stops, so a community effect can't replace a built-in one.

## Where to go next

- [Frame loop](frame-loop.md) explains what happens on every frame.
- [Tutorial step 1: Scaffold](../tutorial/01-scaffold.md) builds the smallest effect that runs, using the parts
  described here.
