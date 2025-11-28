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

[![PyPI - Version](https://img.shields.io/pypi/v/terminaltexteffects?style=flat&color=green)](http://pypi.org/project/terminaltexteffects/ "![PyPI - Version](https://img.shields.io/pypi/v/terminaltexteffects?style=flat&color=green)")  ![PyPI - Python Version](https://img.shields.io/pypi/pyversions/terminaltexteffects) [![Python Bytes](https://img.shields.io/badge/Python_Bytes-377-D7F9FF?logo=applepodcasts&labelColor=blue)](https://youtu.be/eWnYlxOREu4?t=1549) ![License](https://img.shields.io/github/license/ChrisBuilds/terminaltexteffects)

## Table Of Contents

* [About](#tte)
* [Requirements](#requirements)
* [Installation](#installation)
* [Usage (Application)](#application-quickstart)
* [Usage (Library)](#library-quickstart)
* [Effect Showcase](#effect-showcase)
* [In-Development Preview](#in-development-preview)
* [Latest Release Notes](#latest-release-notes)
* [License](#license)

## TTE

![thunderstorm_demo](https://github.com/user-attachments/assets/7678e1d2-df49-497e-bccd-87b933ece981)

TerminalTextEffects (TTE) is a terminal visual effects engine. TTE can be installed as a system application to produce effects in your terminal, or as a Python library to enable effects within your Python scripts/applications. TTE includes a growing library of built-in effects which showcase the engine's features. These features include:

* Xterm 256 / RGB hex color support
* Complex character movement via Paths, Waypoints, and
  motion easing, with support for bezier curves.
* Complex animations via Scenes with symbol/color changes,
  layers, easing, and Path synced progression.
* Variable stop/step color gradient generation.
* Event handling for Path/Scene state changes with
  custom callback support and many pre-defined actions.
* Effect customization exposed through a typed effect configuration
  dataclass that is automatically handled as CLI arguments.
* Runs inline, preserving terminal state and workflow.

## Requirements

TerminalTextEffects is written in Python and does not require any 3rd party modules. Terminal interactions use standard ANSI terminal sequences and should work in most modern terminals.

## Installation

<details>

<summary>UV Install</summary>

Tool Run

```uv tool run terminaltexteffects -h```

Application Install

```uv tool install terminaltexteffects```

Library Install

```uv install terminaltexteffects```

</details>

<details>

<summary>Pip Install</summary>

Application Install

```pipx install terminaltexteffects```

Library Install

```pip install terminaltexteffects```

</details>

<details>

<summary>Nix (flakes)</summary>

Add it as an input to a flake:

```nix
inputs = {
  terminaltexteffects.url = "github:ChrisBuilds/terminaltexteffects/<optional-ref>"
}
````

Create a shell with it:

```nix
nix shell github:ChrisBuilds/terminaltexteffects/<optional-ref>
```

Or run it directly:

```nix
echo 'terminaltexteffects is awesome' | nix run github:ChrisBuilds/terminaltexteffects/<optional-ref> -- beams
```

</details>

<details>

<summary>Nix (classic)</summary>

Fetch the source and add it to, e.g. your shell:

```nix
let
  pkgs = import <nixpkgs> {};

  tte = pkgs.callPackage (pkgs.fetchFromGitHub {
    owner = "ChrisBuilds";
    repo = "terminaltexteffects";
    rev = "<revision, e.g. main/v0.13.0/etc.>";
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

#### Options

<details>

<summary>TTE Command Line Options</summary>

```markdown
  options:
  -h, --help            show this help message and exit
  --input-file, -i INPUT_FILE
                        File to read input from
  --version, -v         show program's version number and exit
  --random-effect, -R   Randomly select an effect to apply
  --include-effects INCLUDE_EFFECTS [INCLUDE_EFFECTS ...]
                        Space-separated list of Effects to include when randomly selecting an effect
  --exclude-effects EXCLUDE_EFFECTS [EXCLUDE_EFFECTS ...]
                        Space-separated list of Effects to exclude when randomly selecting an effect
  --tab-width (int > 0)
                        Number of spaces to use for a tab character.
  --xterm-colors        Convert any colors specified in 24-bit RBG hex to the closest 8-bit XTerm-256 color.
  --no-color            Disable all colors in the effect.
  --terminal-background-color (XTerm [0-255] OR RGB Hex [000000-ffffff])
                        The background color of you terminal. Used to determine the appropriate color for fade-in/out within effects.
  --existing-color-handling {always,dynamic,ignore}
                        Specify handling of existing 8-bit and 24-bit ANSI color sequences in the input data. 3-bit and 4-bit sequences are not supported. 'always' will always use the
                        input colors, ignoring any effect specific colors. 'dynamic' will leave it to the effect implementation to apply input colors. 'ignore' will ignore the colors in
                        the input data. Default is 'ignore'.
  --wrap-text           Wrap text wider than the canvas width.
  --frame-rate FRAME_RATE
                        Target frame rate for the animation in frames per second. Set to 0 to disable frame rate limiting. Defaults to 60.
  --canvas-width int >= -1
                        Canvas width, set to an integer > 0 to use a specific dimension, use 0 to match the terminal width, or use -1 to match the input text width. Defaults to -1.
  --canvas-height int >= -1
                        Canvas height, set to an integer > 0 to use a specific dimension, use 0 to match the terminal height, or use -1 to match the input text height. Defaults to -1.
  --anchor-canvas {sw,s,se,e,ne,n,nw,w,c}
                        Anchor point for the canvas. The canvas will be anchored in the terminal to the location corresponding to the cardinal/diagonal direction. Defaults to 'sw'.
  --anchor-text {n,ne,e,se,s,sw,w,nw,c}
                        Anchor point for the text within the Canvas. Input text will anchored in the Canvas to the location corresponding to the cardinal/diagonal direction. Defaults to
                        'sw'.
  --ignore-terminal-dimensions
                        Ignore the terminal dimensions and utilize the full Canvas beyond the extents of the terminal. Useful for sending frames to another output handler.
  --reuse-canvas        Do not create new rows at the start of the effect. The cursor will be moved up the number of rows present in the input text in an attempt to re-use the canvas.
                        This option works best when used in a shell script. If used interactively with prompts between runs, the result is unpredictable.
  --no-eol              Suppress the trailing newline emitted when an effect animation completes.
  --no-restore-cursor   Do not restore cursor visibility after the effect.

  Effect:
  Name of the effect to apply. Use <effect> -h for effect specific help.

  {beams,binarypath,blackhole,bouncyballs,bubbles,burn,colorshift,crumble,decrypt,errorcorrect,expand,fireworks,highlight,laseretch,matrix,middleout,orbittingvolley,overflow,pour,print,rain,randomsequence,rings,scattered,slice,slide,smoke,spotlights,spray,swarm,sweep,synthgrid,thunderstorm,unstable,vhstape,waves,wipe}
                        Available Effects
    beams               Create beams which travel over the canvas illuminating the characters behind them.
    binarypath          Binary representations of each character move towards the home coordinate of the character.
    blackhole           Characters are consumed by a black hole and explode outwards.
    bouncyballs         Characters are bouncy balls falling from the top of the canvas.
    bubbles             Characters are formed into bubbles that float down and pop.
    burn                Burns vertically in the canvas.
    colorshift          Display a gradient that shifts colors across the terminal.
    crumble             Characters lose color and crumble into dust, vacuumed up, and reformed.
    decrypt             Display a movie style decryption effect.
    errorcorrect        Some characters start in the wrong position and are corrected in sequence.
    expand              Expands the text from a single point.
    fireworks           Characters launch and explode like fireworks and fall into place.
    highlight           Run a specular highlight across the text.
    laseretch           A laser etches characters onto the terminal.
    matrix              Matrix digital rain effect.
    middleout           Text expands in a single row or column in the middle of the canvas then out.
    orbittingvolley     Four launchers orbit the canvas firing volleys of characters inward to build the input text from the center out.
    overflow            Input text overflows and scrolls the terminal in a random order until eventually appearing ordered.
    pour                Pours the characters into position from the given direction.
    print               Lines are printed one at a time following a print head. Print head performs line feed, carriage return.
    rain                Rain characters from the top of the canvas.
    randomsequence      Prints the input data in a random sequence.
    rings               Characters are dispersed and form into spinning rings.
    scattered           Text is scattered across the canvas and moves into position.
    slice               Slices the input in half and slides it into place from opposite directions.
    slide               Slide characters into view from outside the terminal.
    smoke               Smoke floods the canvas colorizing any characters it crosses.
    spotlights          Spotlights search the text area, illuminating characters, before converging in the center and expanding.
    spray               Draws the characters spawning at varying rates from a single point.
    swarm               Characters are grouped into swarms and move around the terminal before settling into position.
    sweep               Sweep across the canvas to reveal uncolored text, reverse sweep to color the text.
    synthgrid           Create a grid which fills with characters dissolving into the final text.
    thunderstorm        Create a thunderstorm in the terminal.
    unstable            Spawn characters jumbled, explode them to the edge of the canvas, then reassemble them in the correct layout.
    vhstape             Lines of characters glitch left and right and lose detail like an old VHS tape.
    waves               Waves travel across the terminal leaving behind the characters.
    wipe                Wipes the text across the terminal to reveal characters.

  Ex: ls -a | tte decrypt --typing-speed 2 --ciphertext-colors 008000 00cb00 00ff00 --final-gradient-stops eda000 --final-gradient-steps 12 --final-gradient-direction vertical
```

</details>

```cat your_text | tte <effect> [options]```

OR

```cat your_text | python -m terminaltexteffects <effect> [options]```

* Use ```<effect> -h``` to view options for a specific effect, such as color or movement direction.
  * Ex: ```tte decrypt -h```

For more information, view the [Application Usage Guide](https://chrisbuilds.github.io/terminaltexteffects/appguide/).

### Library Quickstart

All effects are iterators which return a string representing the current frame. Basic usage is as simple as importing the effect, instantiating it with the input text, and iterating over the effect.

```python
from terminaltexteffects.effects import Rain

effect = Rain("your text here")

for frame in effect:
    # do something with the string
    ...
```

In the event you want to allow TTE to handle the terminal setup/teardown, cursor positioning, and animation frame rate, a terminal_output() context manager is available.

```python
from terminaltexteffects.effects import Rain

effect = Rain("your text here")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

For more information, view the [Library Usage Guide](https://chrisbuilds.github.io/terminaltexteffects/libguide/).

### Effect Showcase

Note: Below you'll find a subset of the built-in effects.

View all of the effects and related information in the [Effects Showroom](https://chrisbuilds.github.io/terminaltexteffects/showroom/).

<details>

<summary>Effects Demos</summary>

#### Beams

![beams_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/6bb98dac-688e-43c9-96aa-1a45f451d4cb)


#### Burn

![burn_demo](https://github.com/user-attachments/assets/b2e6ad48-15f7-4363-b281-d165b91403c4)

#### Decrypt

![decrypt_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/36c23e70-065d-4316-a09e-c2761882cbb3)

#### LaserEtch

![laseretch_demo](https://github.com/user-attachments/assets/b65b57b6-3a02-411e-b9f2-23ec4572c328)

#### Matrix

![matrix_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/0f6ddfd9-5e78-4de2-a187-7950b1e5b9d0)

#### Spotlights

![spotlights_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/4ab93725-0c8a-4bdf-af91-057338f4e007)

#### VHSTape

![vhstape_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/720abbf4-f97d-4ce9-96ee-15ef973488d2)

</details>

## Latest Release Notes

Visit the [ChangeBlog](https://chrisbuilds.github.io/terminaltexteffects/changeblog/changeblog/) for release write-ups.

## 0.14.0

---

### New Features (0.14.0)

---

#### New Application Features (0.14.0)

* `random_effect` is now specified as `--random-effect` and supports `--include-effects` or `--exclude-effects` for limiting which effects are available.

---

### Changes (0.14.0)

---

#### Engine Changes (0.14.0)

* Added `EasingTracker`, a reusable helper that tracks eased progress, deltas, and completion state for any easing function.
* Replaced `eased_step_function` closure with the new `SequenceEaser`, enabling eased iteration over arbitrary sequences while reporting added, removed, and total elements for each step.
* Renamed `CharacterGroup` center related groupings to `CENTER_TO_OUTSIDE` / `OUTSIDE_TO_CENTER`.
* `CharacterGroup`, `CharacterSort`, and `ColorSort` themselves were relocated from the `Terminal` module into `terminaltexteffects.utils.argutils`, and the terminal now imports them from there so both the CLI and the engine share a single definition of the enums.
* `terminaltexteffects.utils.argutils` introduces dedicated argument-type helpers for `CharacterGroup`, `CharacterSort`, and `ColorSort`.
* `Canvas` now exposes a `text_center` `Coord` computed from `text_center_row`/`text_center_column`, eliminating redundant per-call calculations when effects or sort helpers need the true center of the anchored text.
* Center-to-outside/Outside-to-center `CharacterGroup` calculations within `Terminal` now measure distance from the text center instead of the canvas center, so middle-out and outside-in sorts stay aligned with the rendered text even when it is offset on the canvas.

#### Effects Changes (0.14.0)

* Highlight - Simplified effect logic by offloading to `SequenceEaser`.
* Sweep - Simplified effect logic by offloading to `SequenceEaser`.
* Wipe - Simplified effect logic by offloading to `SequenceEaser`. 
* Wipe - Changed default `--wipe-ease` to `IN_OUT_CIRC`.
* Wipe - Removed `--wipe-ease-stepsize` CLI arg.
* Colorshift - `--travel` renamed `--no-travel`. The default behavior is to travel radially.
* Colorshift - Default `--travel-direction` changed from horizontal to radial.

---

### Bug Fixes (0.14.0)

---

#### Effect Fixes (0.14.0)

* Sweep - Fixed bug when second sweep direction is a grouping of a different length from the first direction. 
* Removed mistakenly added effect dev_worm.

#### Application Fixes (0.14.0)

* CLI now exits with a non-zero status when input files are missing, no input is provided, or no effect is specified.
* CLI detects duplicate effect command registrations.

---

## License

Distributed under the MIT License. See [LICENSE](https://github.com/ChrisBuilds/terminaltexteffects/blob/main/LICENSE.md) for more information.
