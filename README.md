<br/>
<p align="center">
  <a href="https://github.com/ChrisBuilds/terminaltexteffects">
    <img src="https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/66388e57-e95e-4619-b804-1d8d7ebd124f" alt="TTE" width="80" height="80">
  </a>

  <h3 align="center">Terminal Text Effects</h3>

  <p align="center">
    Inline Visual Effects in the Terminal
    <br/>
    <br/>
  </p>
</p>

[![PyPI - Version](https://img.shields.io/pypi/v/terminaltexteffects?style=flat&color=green)](https://pypi.org/project/terminaltexteffects/)  ![Python Version](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2FChrisBuilds%2Fterminaltexteffects%2Fmain%2Fpyproject.toml) [![Python Bytes](https://img.shields.io/badge/Python_Bytes-377-D7F9FF?logo=applepodcasts&labelColor=blue)](https://youtu.be/eWnYlxOREu4?t=1549) ![License](https://img.shields.io/github/license/ChrisBuilds/terminaltexteffects)

> [!NOTE]
> This README and the [documentation](https://chrisbuilds.github.io/terminaltexteffects/) follow
> development `main`, toward 0.16.0. The latest published release is 0.15.0, so some features
> described here are not yet in the package on PyPI. See [SUPPORT.md](SUPPORT.md) for the
> differences between releases.

## Table Of Contents

* [About](#tte)
* [Quick Start](#quick-start)
* [Requirements](#requirements)
* [Support and Security](#support-and-security)
* [Installation](#installation)
* [Usage](#usage)
  * [Application Quickstart](#application-quickstart)
  * [Library Quickstart](#library-quickstart)
* [Effect Showcase](#effect-showcase)
* [Changelog](#changelog)
* [License](#license)

## TTE

![thunderstorm_demo](https://raw.githubusercontent.com/ChrisBuilds/terminaltexteffects/main/docs/img/effects_demos/thunderstorm_demo.webp)

TerminalTextEffects (TTE) is a terminal visual effects engine. TTE can be installed as a system application to produce effects in your terminal, or as a Python library to enable effects within your Python scripts/applications. TTE includes a growing library of built-in effects which showcase the engine's features. These features include:

* Xterm 256 / RGB hex color support.
* Complex character movement via Paths, Waypoints, and
  motion easing, with support for Bézier curves.
* Complex animations via Scenes with symbol/color changes,
  layers, easing, and Path-synced progression.
* Variable stop/step color gradient generation.
* Event handling for Path/Scene state changes with
  custom callback support and many pre-defined actions.
* Typed effect configuration that is automatically exposed as CLI arguments.
* Input color preservation and parsing of common ANSI sequences from fetch-style tools.
* Recording rendered effects to files and replaying them without re-rendering.
* Custom effect plugins that run alongside the built-in effects.
* Runs inline, preserving terminal state and workflow.

## Quick Start

```sh
pipx install terminaltexteffects
```

```sh
echo "Hello, terminal!" | tte beams
```

## Requirements

Development `main` requires Python 3.9.2 or newer. The core package does not require any third-party modules. Terminal interactions use standard ANSI terminal sequences and should work in most modern terminals.

## Support and Security

See [SUPPORT.md](SUPPORT.md) for Python/platform coverage, terminal requirements, shell completion,
and reporting ordinary problems. Report vulnerabilities privately through the
route in [SECURITY.md](SECURITY.md); security fixes target the latest stable release.

## Installation

<details>

<summary>pip / pipx</summary>

Application install:

```sh
pipx install terminaltexteffects
```

Library install:

```sh
pip install terminaltexteffects
```

</details>

<details>

<summary>uv</summary>

Run without installing:

```sh
uv tool run terminaltexteffects -h
```

Application install:

```sh
uv tool install terminaltexteffects
```

Library install:

```sh
uv add terminaltexteffects
```

</details>

<details>

<summary>Nix (flakes)</summary>

Enable `nix-command` and `flakes` in your Nix configuration, for example with
`experimental-features = nix-command flakes` in `~/.config/nix/nix.conf`.

Create a shell with it:

```sh
nix shell github:ChrisBuilds/terminaltexteffects
```

Or run it directly:

```sh
echo 'terminaltexteffects is awesome' | nix run github:ChrisBuilds/terminaltexteffects -- beams
```

Or add it as an input to a flake:

```nix
inputs = {
  terminaltexteffects.url = "github:ChrisBuilds/terminaltexteffects";
};
```

These commands use development `main`. Append `/COMMIT_SHA` to select an exact
revision, or `/release-VERSION` for a published release tag that includes Nix support
(replace the uppercase placeholders). Flake inputs are pinned by the consumer's
`flake.lock`; use `terminaltexteffects.packages.${pkgs.system}.default` in its outputs.

</details>

<details>

<summary>Nix (classic)</summary>

Save this template as `shell.nix`. Replace `COMMIT_SHA` with a full commit or an
existing `release-VERSION` tag. Run `nix-shell` once with the empty hash, then copy
the reported `got: sha256-...` value into `hash` and run `nix-shell` again. Repeat
the hash update when changing `rev`. The selected `<nixpkgs>` must provide the
modern Python build tooling used by `default.nix`; CI tests the repository's locked
nixpkgs input, rather than an arbitrary local channel.

```nix
let
  pkgs = import <nixpkgs> {};

  tte = pkgs.callPackage (pkgs.fetchFromGitHub {
    owner = "ChrisBuilds";
    repo = "terminaltexteffects";
    rev = "COMMIT_SHA";
    hash = ""; # Build first, put proper hash in place
  }) {};
in
  pkgs.mkShell {
    packages = [tte];
  }
```

</details>

## Usage

View the [Documentation](https://chrisbuilds.github.io/terminaltexteffects/) for a full installation and usage guide.

### Application Quickstart

```sh
tte [global_options] <effect> [effect_options] < your_file
```

Input can be piped or redirected through stdin, or passed with `--input-file`/`-i`.
`python -m terminaltexteffects` works in place of `tte`.

* Use `tte -h` to list global options and effects, and `tte <effect> -h` to view options for a
  specific effect, such as color or movement direction.
* Randomly select an effect with `--random-effect`/`-R`. Use `--seed` to make the choice repeatable,
  and `--include-effects` or `--exclude-effects` to limit the pool.
* Enable shell completion for built-in effects in the current shell. Add the line to `~/.bashrc` or
  `~/.zshrc` to keep it. See [Shell Completion](https://chrisbuilds.github.io/terminaltexteffects/appguide/#shell-completion)
  for PowerShell and other details.
  * Bash: `eval "$(tte --print-completion bash)"`
  * Zsh: `eval "$(tte --print-completion zsh)"`
* Add custom effect modules to `${XDG_CONFIG_HOME}/terminaltexteffects/effects`, or
  `~/.config/terminaltexteffects/effects` when `XDG_CONFIG_HOME` is unset, empty, or a relative path.
  See [Community effects](https://chrisbuilds.github.io/terminaltexteffects/appguide/#community-effects)
  for installation steps, and browse or share projects in
  [TTE Effect Show and Tell](https://github.com/ChrisBuilds/terminaltexteffects/discussions/categories/tte-effect-show-and-tell).
* Record effects and replay them later with `--record` and `--play`. See
  [Recording and playback](https://chrisbuilds.github.io/terminaltexteffects/appguide/#recording-and-playback).
* TTE is not a full terminal emulator, but it parses common fetch-style input including SGR colors,
  cursor movement, and carriage returns. Unsupported control sequences fail with an error rather
  than leaking into the animation.

For all options and more examples, view the [Application Usage Guide](https://chrisbuilds.github.io/terminaltexteffects/appguide/).

### Library Quickstart

All effects are iterators which return a string representing the current frame. Basic usage is as simple as importing the effect, instantiating it with the input text, and iterating over the effect.

```python
from terminaltexteffects.effects import Rain

effect = Rain("your text here")

for frame in effect:
    # do something with the string
    ...
```

To let TTE handle terminal setup/teardown, cursor positioning, and animation frame rate, use the `terminal_output()` context manager.

```python
from terminaltexteffects.effects import Rain

effect = Rain("your text here")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

For more information, view the [Library Usage Guide](https://chrisbuilds.github.io/terminaltexteffects/libguide/).

## Effect Showcase

Below you'll find a subset of the built-in effects. View all of the effects and related information in the [Effects Showroom](https://chrisbuilds.github.io/terminaltexteffects/showroom/).

<details>

<summary>Effects Demos</summary>

#### Beams

![beams_demo](https://raw.githubusercontent.com/ChrisBuilds/terminaltexteffects/main/docs/img/effects_demos/beams_demo.webp)

#### Burn

![burn_demo](https://raw.githubusercontent.com/ChrisBuilds/terminaltexteffects/main/docs/img/effects_demos/burn_demo.webp)

#### Decrypt

![decrypt_demo](https://raw.githubusercontent.com/ChrisBuilds/terminaltexteffects/main/docs/img/effects_demos/decrypt_demo.webp)

#### LaserEtch

![laseretch_demo](https://raw.githubusercontent.com/ChrisBuilds/terminaltexteffects/main/docs/img/effects_demos/laseretch_demo.webp)

#### Matrix

![matrix_demo](https://raw.githubusercontent.com/ChrisBuilds/terminaltexteffects/main/docs/img/effects_demos/matrix_demo.webp)

#### Spotlights

![spotlights_demo](https://raw.githubusercontent.com/ChrisBuilds/terminaltexteffects/main/docs/img/effects_demos/spotlights_demo.webp)

#### VHSTape

![vhstape_demo](https://raw.githubusercontent.com/ChrisBuilds/terminaltexteffects/main/docs/img/effects_demos/vhstape_demo.webp)

</details>

## Changelog

See the [CHANGELOG](./CHANGELOG.md) for release history. Unreleased changes on development `main` appear
in the [documentation changelog](https://chrisbuilds.github.io/terminaltexteffects/changelog/).
The [ChangeBlog](https://chrisbuilds.github.io/terminaltexteffects/changeblog/changeblog/) provides optional release
write-ups and demos.

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.
