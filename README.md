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

![synthgrid_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/6d1bab16-0520-44fa-a508-8f92d7d3be9e)

TerminalTextEffects (TTE) is a terminal visual effects engine. TTE can be installed as a system application to produce effects in your terminal, or as a Python library to enable effects within your Python scripts/applications. TTE includes a growing library of built-in effects which showcase the engine's features. These features include:

* Xterm 256 / RGB hex color support
* Complex character movement via Paths, Waypoints, and
  motion easing, with support for quadratic/cubic bezier curves.
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

Note: Windows Terminal performance is slow for some effects.

## Installation

```pip install terminaltexteffects```
OR
```pipx install terminaltexteffects```

## Usage

View the [Documentation](https://chrisbuilds.github.io/terminaltexteffects/) for a full installation and usage guide.

### Application Quickstart

#### Options

<details>

<summary>TTE Command Line Options</summary>

```markdown
  options:
  -h, --help            show this help message and exit
  --input-file INPUT_FILE, -i INPUT_FILE
                        File to read input from (default: None)
  --tab-width (int > 0)
                        Number of spaces to use for a tab character. (default: 4)
  --xterm-colors        Convert any colors specified in RBG hex to the closest XTerm-256 color.
                        (default: False)
  --no-color            Disable all colors in the effect. (default: False)
  --wrap-text           Wrap text wider than the canvas width. (default: False)
  --frame-rate FRAME_RATE
                        Target frame rate for the animation. (default: 100)
  --canvas-width CANVAS_WIDTH
                        Canvas width, if set to 0 the canvas width is detected automatically based on
                        the terminal device. (default: 0)
  --canvas-height CANVAS_HEIGHT
                        Canvas height, if set to 0 the canvas height is detected automatically based on
                        the terminal device. (default: 0)
  --ignore-terminal-dimensions
                        Ignore the terminal dimensions and use the input data dimensions for the
                        canvas. (default: False)

  Effect:
  Name of the effect to apply. Use <effect> -h for effect specific help.

  {beams,binarypath,blackhole,bouncyballs,bubbles,burn,colorshift,crumble,decrypt,errorcorrect,expand,fireworks,middleout,orbittingvolley,overflow,pour,print,rain,randomsequence,rings,scattered,slice,slide,spotlights,spray,swarm,synthgrid,unstable,vhstape,waves,wipe}
                        Available Effects
    beams               Create beams which travel over the canvas illuminating the characters behind
                        them.
    binarypath          Binary representations of each character move through the terminal towards the
                        home coordinate of the character.
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
    middleout           Text expands in a single row or column in the middle of the canvas then out.
    orbittingvolley     Four launchers orbit the canvas firing volleys of characters inward to build
                        the input text from the center out.
    overflow            Input text overflows and scrolls the terminal in a random order until
                        eventually appearing ordered.
    pour                Pours the characters into position from the given direction.
    print               Lines are printed one at a time following a print head. Print head performs
                        line feed, carriage return.
    rain                Rain characters from the top of the canvas.
    randomsequence      Prints the input data in a random sequence.
    rings               Characters are dispersed and form into spinning rings.
    scattered           Text is scattered across the canvas and moves into position.
    slice               Slices the input in half and slides it into place from opposite directions.
    slide               Slide characters into view from outside the terminal.
    spotlights          Spotlights search the text area, illuminating characters, before converging in
                        the center and expanding.
    spray               Draws the characters spawning at varying rates from a single point.
    swarm               Characters are grouped into swarms and move around the terminal before settling
                        into position.
    synthgrid           Create a grid which fills with characters dissolving into the final text.
    unstable            Spawn characters jumbled, explode them to the edge of the canvas, then
                        reassemble them in the correct layout.
    vhstape             Lines of characters glitch left and right and lose detail like an old VHS tape.
    waves               Waves travel across the terminal leaving behind the characters.
    wipe                Wipes the text across the terminal to reveal characters.

  Ex: ls -a | python -m terminaltexteffects decrypt --typing-speed 2 --ciphertext-colors 008000 00cb00 00ff00 --final-gradient-stops eda000 --final-gradient-steps 12 --final-gradient-direction vertical
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
from terminaltexteffects.effects import effect_rain

effect = effect_rain.Rain("your text here")

for frame in effect:
    # do something with the string
    ...
```

In the event you want to allow TTE to handle the terminal setup/teardown, cursor positioning, and animation frame rate, a terminal_output() context manager is available.

```python
from terminaltexteffects.effects import effect_rain

effect = effect_rain.Rain("your text here")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

For more information, view the [Library Usage Guide](https://chrisbuilds.github.io/terminaltexteffects/libguide/).

### Effect Showcase

Note: Below you'll find a subset of the built-in effects.

View all of the effects and related information in the [Effects Showroom](https://chrisbuilds.github.io/terminaltexteffects/showroom/).

#### Beams

![beams_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/6bb98dac-688e-43c9-96aa-1a45f451d4cb)

#### Binarypath

![binarypath_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/99ad3946-c475-4743-93e2-cdfb2a7f558f)

#### Blackhole

![blackhole_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/877579d3-d353-4bed-9a95-d3ea7a53200a)

#### Bubbles

![bubbles_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/5a616538-7936-4f55-b2ff-28e6c4179fce)

#### Burn

![burn_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/9770711a-ea68-48cc-947f-fb13c6613a2e)

#### Decrypt

![decrypt_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/36c23e70-065d-4316-a09e-c2761882cbb3)

#### Fireworks

![fireworks_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/da6a97b1-c4fd-4370-9852-9ddb8a494b55)

#### Orbittingvolley

![orbittingvolley_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/084038e5-9d49-4c7d-bf15-e989f541b15c)

#### Pour

![pour_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/145c2a4e-6b30-48c6-80a3-afb03edf7c22)

#### Print

![print_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/5d902350-e5d3-400c-9496-119c88d40643)

#### Rain

![rain_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/7b8cf447-67b6-41e9-b354-07b3e5161d10)

#### Rings

![rings_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/cb7f6388-0f46-42f1-a2b3-6a267e9451f0)

#### Slide

![slide_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/218e7218-e9ef-44de-b43b-5e824623a957)

#### Spotlights

![spotlights_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/4ab93725-0c8a-4bdf-af91-057338f4e007)

#### Swarm

![swarm_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/305e8390-a0fb-4edb-a541-7b52cef77c09)

#### VHSTape

![vhstape_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/720abbf4-f97d-4ce9-96ee-15ef973488d2)

#### Waves

![waves_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/ea9b04ca-e526-4c7e-b98d-a98a42f7137f)

## In-Development Preview

Any effects shown below are in development and will be available in the next release.

![matrix_demo](./docs/img/effects_demos/matrix_demo.gif)

## Latest Release Notes

Visit the [ChangeBlog](https://chrisbuilds.github.io/terminaltexteffects/changeblog/) for release write-ups.

### Changes (0.10.1)

---

#### Engine Changes (0.10.1)

* Performance improvements to geometry functions related to circles.

### Bug Fixes (0.10.1)

* Fixed swarm effect not handling the first swarm (bottom right characters) resulting in missing characters in the output.

---

## 0.10.0

---

### New Features (0.10.0)

---

#### New Effects (0.10.0)

* ColorShift: Display a gradient that shifts colors across the terminal. Supports standing and traveling gradients in
  the following directions: vertical, horizontal, diagonal, radial. The final gradient appearance is optional using the
  --skips-final-gradient argument. This effect supports infinite looping when imported by setting
  ColorShiftConfig.cycles
  to 0. This functionality is not available when run from the TTE application.

#### New Engine Features (0.10.0)

* File input: Use the `--input-file` or `-i` option to pass a file as input.

### Changes (0.10.0)

---

#### Effects Changes (0.10.0)

* Added `--wave-direction` config to Waves effect.
* Added additional directions to `--wipe-direction` config in Wipe effect.
* VerticalSlice is now Slice and supports vertical, horizontal, and diagonal slice directions.

#### Engine Changes (0.10.0)

* Increased compatibility with Python versions from >=3.10 to >=3.8
* Updated type information for gradient step variables to accept a single int as well as tuple[int, ...].
* Color TypeAlias replaced with Color class. Color objects are used throughout the engine.
* Renamed OutputArea to Canvas.
* Changed center gradient direction to radial.

### Bug Fixes (0.10.0)

---

#### Engine Fixes (0.10.0)

* Characters created as `fill_characters` now adhere to `--no-color` and `--xterm-colors`.

#### Other (0.10.0)

* Added cookbook to the documentation and animated prompt example.
* Added printing `Color` and `Gradient` objects examples to docs.

---

## License

Distributed under the MIT License. See [LICENSE](https://github.com/ChrisBuilds/terminaltexteffects/blob/main/LICENSE.md) for more information.
