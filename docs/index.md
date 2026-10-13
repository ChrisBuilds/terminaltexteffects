# Intro to TTE

![title_blackhole](./img/application_demos/shadow_title_blackhole.gif)

## What is TTE?

TerminalTextEffects (TTE) is a terminal visual effects engine. TTE can be installed as a system application to produce
effects in your terminal, or as a Python library to enable effects within your Python scripts/applications. TTE
includes a growing library of built-in effects which showcase the engine's features. These features include:

* XTerm 256 and RGB hex color support, including colors parsed from the input text.
* Complex character movement via Paths, Waypoints, and motion easing, with support for quadratic/cubic Bezier curves.
* Complex animations via Scenes with symbol/color changes, layers, easing, and Path-synced progression.
* Variable stop/step color gradient generation.
* Event handling for Path/Scene state changes with custom callback support and many predefined actions.
* Effect customization exposed through a typed effect configuration dataclass that is automatically handled as CLI
  arguments.
* Flexible character ordering by rows, columns, diagonals, rings, and spirals.
* Inline output that preserves terminal state and workflow, with an optional alternate-screen mode.
* Random and repeated playback, plus recording effects to files for low-CPU replay.
* Community effects loaded from your configuration directory.

Character ordering, alternate-screen output, repeated playback, and recording are new in 0.16.0 and are not in the
published 0.15.0 package.

## Getting Started

TTE can be used as a system application or as a Python library. To get started, visit the installation and usage guides below.

[Installation Guide](./installation.md){ .md-button } [Application Usage](./appguide.md){ .md-button } [Library Usage](./libguide.md){ .md-button }

## Effects Library

TTE includes a growing library of built-in effects. Visit the showroom to see examples of each effect.

[Effects Showroom](./showroom.md){ .md-button }

## Library Cookbook

Check out the cookbook to see interesting examples using the TTE library.

[Library Cookbook](./cookbook.md){ .md-button }

## Release Write-Ups

Friendly release write-ups can be found in the [ChangeBlog](./changeblog/changeblog.md).

[ChangeBlog](./changeblog/changeblog.md){ .md-button }
