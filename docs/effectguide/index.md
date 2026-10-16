# Effect Guide

This guide teaches you to write your own TerminalTextEffects (TTE) effects. It explains how the engine works,
then walks you through building a complete effect and sharing it with other TTE users.

!!! note "TTE version"

    This guide describes TTE 0.16.0. Engine APIs can change between releases; check the
    [changelog](../changelog.md) for breaking changes before updating an effect to a newer TTE.

## Who this guide is for

You know Python and want to make an effect: a new way for text to arrive on, move around, or leave the terminal.
You don't need to know anything about TTE's internals. Maintainers adding built-in effects follow the same guide, and
then the [promotion checklist](https://github.com/ChrisBuilds/terminaltexteffects/blob/main/dev_effects/README.md#promotion-checklist).

## How the guide is organized

``` mermaid
flowchart LR
    start[Start here] --> engine[The Engine]
    start --> writing[Writing Effects]
    engine --> threed[3D Effects]
    writing -- each step links --> engine
    engine --> reference[API Reference]
    writing --> reference
```

- **The Engine** explains each part of TTE: what it does, how it is designed, and what it can't do. Read it in order
  or come back to a chapter when you need it.
- **3D Effects** teaches the ideas behind 3D graphics (coordinates, transforms, the camera, depth and light) at the
  level you need to use TTE's 3D tools, with diagrams and an example effect for each idea. Read it after the Engine.
- **Writing Effects** is hands-on. Its tutorial rebuilds the built-in [Spray](../effects/spray.md) effect from an
  empty file, one step per page, and each step links the engine chapter it relies on.
- The **Reference** section, generated from the source, lists every class and function. This guide links to it
  instead of repeating signatures.

The guide only uses public APIs: names exported by the `terminaltexteffects` package and the public modules under
`terminaltexteffects.engine` and `terminaltexteffects.utils`. Anything whose name starts with an underscore is
internal and can change without notice.

## What you need

- Python 3.9.2 or later and TTE installed in the same environment (see [Install](../installation.md)).
- A terminal with color support. Any terminal that can run `tte` works.
- A directory for your effect. TTE loads community effects from
  `${XDG_CONFIG_HOME:-$HOME/.config}/terminaltexteffects/effects`; the
  [application guide](../appguide.md#community-effects) explains the rules.

## Where to start

New to TTE effects? Start with [Architecture](engine/architecture.md), then follow the tutorial from
[Step 1: Scaffold](tutorial/01-scaffold.md). The tutorial and engine chapters are written to be read side by side.
