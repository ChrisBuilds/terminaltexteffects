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

[![PyPI - Version](https://img.shields.io/pypi/v/terminaltexteffects?style=flat&color=green)](http://pypi.org/project/terminaltexteffects/ "![PyPI - Version](https://img.shields.io/pypi/v/terminaltexteffects?style=flat&color=green)")  ![PyPI - Python Version](https://img.shields.io/pypi/pyversions/terminaltexteffects) ![License](https://img.shields.io/github/license/ChrisBuilds/terminaltexteffects) 

## Table Of Contents

* [About](#tte)
* [Requirements](#requirements)
* [Installation](#installation)
* [Usage](#usage)
* [Options](#options)
* [Examples](#examples)
* [In-Development Preview](#in-development-preview)
* [Latest Release Notes](#latest-release-notes)
* [License](#license)


## TTE
![synthgrid_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/6d1bab16-0520-44fa-a508-8f92d7d3be9e)


TerminalTextEffects is a collection of visual effects that run inline in the terminal. The underlying visual effect engine supports the following:
* Xterm 256 / RGB hex color support
* Complex character movement via Paths, Waypoints, and
  motion easing.
* Complex animations via Scenes with symbol/color changes,
  layers, easing, and Path synced progression.
* Event handling for Path/Scene state changes with 
  custom callback support and many pre-defined actions.
* Variable stop/step color gradient generation. 
* Extensive effect customization via per-effect arguments.
* Runs inline, preserving terminal state and workflow.

## Requirements

TerminalTextEffects is written in Python and does not require any 3rd party modules. Terminal interactions use standard ANSI terminal sequences and should work in most modern terminals.

Note: Windows Terminal performance is slow for some effects.

## Installation


```pip install terminaltexteffects```
OR
```pipx install terminaltexteffects```

## Usage
```cat your_text | tte <effect> [options]```

OR

``` cat your_text | python -m terminaltexteffects <effect> [options]```

* Use ```<effect> -h``` to view options for a specific effect, such as color or movement direction.
  * Ex: ```tte decrypt -h```

## Options
```
options:
  -h, --help            show this help message and exit
  --tab-width (int > 0)
                        Number of spaces to use for a tab character.
  --xterm-colors        Convert any colors specified in RBG hex to the closest XTerm-256 color.
  --no-color            Disable all colors in the effect.
  --no-wrap             Disable wrapping of text.
  -a ANIMATION_RATE, --animation-rate ANIMATION_RATE
                        Minimum time, in seconds, between animation steps. This value does not normally need to be modified. Use this to increase the playback speed of all aspects of the effect. This will have
                        no impact beyond a certain lower threshold due to the processing speed of your device.

Effect:
  Name of the effect to apply. Use <effect> -h for effect specific help.

  {beams,binarypath,blackhole,bouncyballs,bubbles,burn,crumble,decrypt,dev,errorcorrect,expand,fireworks,middleout,orbittingvolley,overflow,pour,print,rain,randomsequence,rings,scattered,slide,spotlights,spray,swarm,synthgrid,test,unstable,verticalslice,vhstape,waves,wipe}
                        Available Effects
    beams               Create beams which travel over the output area illuminating the characters behind them.
    binarypath          Binary representations of each character move through the terminal towards the home coordinate of the character.
    blackhole           Characters are consumed by a black hole and explode outwards.
    bouncyballs         Characters are bouncy balls falling from the top of the output area.
    bubbles             Characters are formed into bubbles that float down and pop.
    burn                Burns vertically in the output area.
    crumble             Characters lose color and crumble into dust, vacuumed up, and reformed.
    decrypt             Display a movie style decryption effect.
    errorcorrect        Some characters start in the wrong position and are corrected in sequence.
    expand              Expands the text from a single point.
    fireworks           Characters launch and explode like fireworks and fall into place.
    middleout           Text expands in a single row or column in the middle of the output area then out.
    orbittingvolley     Four launchers orbit the output area firing volleys of characters inward to build the input text from the center out.
    overflow            Input text overflows ands scrolls the terminal in a random order until eventually appearing ordered.
    pour                Pours the characters into position from the given direction.
    print               Lines are printed one at a time following a print head. Print head performs line feed, carriage return.
    rain                Rain characters from the top of the output area.
    randomsequence      Prints the input data in a random sequence.
    rings               Characters are dispersed and form into spinning rings.
    scattered           Move the characters into place from random starting locations.
    slide               Slide characters into view from outside the terminal.
    spotlights          Spotlights search the text area, illuminating characters, before converging in the center and expanding.
    spray               Draws the characters spawning at varying rates from a single point.
    swarm               Characters are grouped into swarms and move around the terminal before settling into position.
    synthgrid           Create a grid which fills with characters dissolving into the final text.
    unstable            Spawn characters jumbled, explode them to the edge of the output area, then reassemble them in the correct layout.
    verticalslice       Slices the input in half vertically and slides it into place from opposite directions.
    vhstape             Lines of characters glitch left and right and lose detail like an old VHS tape.
    waves               Waves travel across the terminal leaving behind the characters.
    wipe                Wipes the text across the terminal to reveal characters.

Ex: ls -a | tte crumble --final-gradient-stops 5CE1FF FF8C00 --final-gradient-steps 12 --final-gradient-direction diagonal
```
## Examples
Note: All effects support extensive customization via effect specific arguments. The examples shown below only represent one possible variant of 
each effect. Check the effect help output to see arguments.

#### Beams
![beams_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/6bb98dac-688e-43c9-96aa-1a45f451d4cb)
<details>
<summary>tte beams -h</summary>
<br>
    beams | Create beams which travel over the output area illuminating the characters behind them.

    options:
      -h, --help            show this help message and exit
      --beam-row-symbols (ASCII/UTF-8 character) [(ASCII/UTF-8 character) ...]
                            Symbols to use for the beam effect when moving along a row. Strings will be used in sequence to create an animation. (default: ('▂', '▁', '_'))
      --beam-column-symbols (ASCII/UTF-8 character) [(ASCII/UTF-8 character) ...]
                            Symbols to use for the beam effect when moving along a column. Strings will be used in sequence to create an animation. (default: ('▌', '▍', '▎', '▏'))
      --beam-delay (int > 0)
                            Number of frames to wait before adding the next group of beams. Beams are added in groups of size random(1, 5). (default: 10)
      --beam-row-speed-range (hyphen separated int range e.g. '1-10')
                            Minimum speed of the beam when moving along a row. (default: (10, 40))
      --beam-column-speed-range (hyphen separated int range e.g. '1-10')
                            Minimum speed of the beam when moving along a column. (default: (6, 10))
      --beam-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the beam, a gradient will be created between the colors. (default: ('ffffff', '00D1FF', '8A008A'))
      --beam-gradient-steps (int > 0) [(int > 0) ...]
                            Space separated, unquoted, numbers for the of gradient steps to use. More steps will create a smoother and longer gradient animation. Steps are paired with the colors in final-gradient-
                            stops. (default: (2, 8))
      --beam-gradient-frames (int > 0)
                            Number of frames to display each gradient step. (default: 2)
      --final-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the wipe gradient. (default: ('8A008A', '00D1FF', 'ffffff'))
      --final-gradient-steps (int > 0) [(int > 0) ...]
                            Space separated, unquoted, numbers for the of gradient steps to use. More steps will create a smoother and longer gradient animation. Steps are paired with the colors in final-gradient-
                            stops. (default: (12,))
      --final-gradient-frames (int > 0)
                            Number of frames to display each gradient step. (default: 5)
      --final-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the final color. (default: Direction.VERTICAL)
      --final-wipe-speed (int > 0)
                            Speed of the final wipe as measured in diagonal groups activated per frame. (default: 1)

    Example: terminaltexteffects beams --beam-row-symbols ▂ ▁ _ --beam-column-symbols ▌ ▍ ▎ ▏ --beam-delay 10 --beam-row-speed-range 10-40 --beam-column-speed-range 6-10 --beam-gradient-stops ffffff 00D1FF 8A008A --beam-gradient-steps 2 8 --beam-gradient-frames 2 --final-gradient-stops 8A008A 00D1FF ffffff --final-gradient-steps 12 --final-gradient-frames 5 --final-gradient-direction vertical --final-wipe-speed 1
</details>

#### Binarypath
![binarypath_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/99ad3946-c475-4743-93e2-cdfb2a7f558f)
<details>
<summary>tte binarypath -h</summary>
<br>
    binarypath | Binary representations of each character move through the terminal towards the home coordinate of the character.

    options:
      -h, --help            show this help message and exit
      --final-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
                            (default: ('00d500', '007500'))
      --final-gradient-steps (int > 0) [(int > 0) ...]
                            Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --final-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the final color. (default: Direction.CENTER)
      --binary-colors (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the binary characters. Character color is randomly assigned from this list. (default: ('044E29', '157e38', '45bf55', '95ed87'))
      --movement-speed (float > 0)
                            Speed of the binary groups as they travel around the terminal. (default: 1.0)
      --active-binary-groups (0 <= float(n) <= 1)
                            Maximum number of binary groups that are active at any given time. Lower this to improve performance. (default: 0.05)

    Example: terminaltexteffects binarypath --final-gradient-stops 00d500 007500 --final-gradient-steps 12 --final-gradient-direction vertical --binary-colors 044E29 157e38 45bf55 95ed87 --movement-speed 1.0 --active-binary-groups 0.05
</details>

#### Blackhole
![blackhole_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/877579d3-d353-4bed-9a95-d3ea7a53200a)
<details>
<summary>tte blackhole -h</summary>
<br>
    blackhole | Characters are consumed by a black hole and explode outwards.

    options:
      -h, --help            show this help message and exit
      --blackhole-color (XTerm [0-255] OR RGB Hex [000000-ffffff])
                            Color for the stars that comprise the blackhole border. (default: ffffff)
      --star-colors (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            List of colors from which character colors will be chosen and applied after the explosion, but before the cooldown to final color. (default: ('ffcc0d', 'ff7326', 'ff194d', 'bf2669',
                            '702a8c', '049dbf'))
      --final-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
                            (default: ('8A008A', '00D1FF', 'ffffff'))
      --final-gradient-steps (int > 0) [(int > 0) ...]
                            Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --final-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the final color. (default: Direction.DIAGONAL)

    Example: terminaltexteffects blackhole --star-colors ffcc0d ff7326 ff194d bf2669 702a8c 049dbf --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --final-gradient-direction vertical
</details>

#### Bouncyballs
![bouncyballs_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/84b12fd0-6e51-4661-bd09-407dad30023d)
<details>
<summary>tte bouncyballs -h</summary>
<br>
    bouncyballs | Characters are bouncy balls falling from the top of the output area.

    options:
      -h, --help            show this help message and exit
      --ball-colors (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated list of colors from which ball colors will be randomly selected. If no colors are provided, the colors are random. (default: ('d1f4a5', '96e2a4', '5acda9'))
      --ball-symbols (ASCII/UTF-8 character) [(ASCII/UTF-8 character) ...]
                            Space separated list of symbols to use for the balls. (default: ('*', 'o', 'O', '0', '.'))
      --final-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
                            (default: ('f8ffae', '43c6ac'))
      --final-gradient-steps (int > 0) [(int > 0) ...]
                            Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --final-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the final color. (default: Direction.DIAGONAL)
      --ball-delay (int >= 0)
                            Number of animation steps between ball drops, increase to reduce ball drop rate. (default: 7)
      --movement-speed (float > 0)
                            Movement speed of the characters. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect. (default: 0.25)
      --easing EASING       Easing function to use for character movement. (default: out_bounce)

        Easing
        ------
        Note: A prefix must be added to the function name.
        
        All easing functions support the following prefixes:
            IN_  - Ease in
            OUT_ - Ease out
            IN_OUT_ - Ease in and out
            
        Easing Functions
        ----------------
        SINE   - Sine easing
        QUAD   - Quadratic easing
        CUBIC  - Cubic easing
        QUART  - Quartic easing
        QUINT  - Quintic easing
        EXPO   - Exponential easing
        CIRC   - Circular easing
        BACK   - Back easing
        ELASTIC - Elastic easing
        BOUNCE - Bounce easing
        
        Visit: https://easings.net/ for visualizations of the easing functions.

    Example: terminaltexteffects bouncyballs --ball-colors d1f4a5 96e2a4 5acda9 --ball-symbols o "*" O 0 . --final-gradient-stops f8ffae 43c6ac --final-gradient-steps 12 --final-gradient-direction diagonal --ball-delay 7 --movement-speed 0.25 --easing OUT_BOUNCE
</details>

#### Bubbles
![bubbles_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/5a616538-7936-4f55-b2ff-28e6c4179fce)
<details>
<summary>tte bubbles -h</summary>
<br>
    bubbles | Characters are formed into bubbles that float down and pop.

    options:
      -h, --help            show this help message and exit
      --rainbow             If set, the bubbles will be colored with a rotating rainbow gradient. (default: False)
      --bubble-colors (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the bubbles. Ignored if --no-rainbow is left as default False. (default: ('d33aff', '7395c4', '43c2a7', '02ff7f'))
      --pop-color (XTerm [0-255] OR RGB Hex [000000-ffffff])
                            Color for the spray emitted when a bubble pops. (default: ffffff)
      --final-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
                            (default: ('d33aff', '02ff7f'))
      --final-gradient-steps (int > 0) [(int > 0) ...]
                            Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --final-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the final color. (default: Direction.DIAGONAL)
      --bubble-speed (float > 0)
                            Speed of the floating bubbles. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect. (default: 0.1)
      --bubble-delay (int > 0)
                            Number of animation steps between bubbles. (default: 50)
      --pop-condition {row,bottom,anywhere}
                            Condition for a bubble to pop. 'row' will pop the bubble when it reaches the the lowest row for which a character in the bubble originates. 'bottom' will pop the bubble at the bottom
                            row of the terminal. 'anywhere' will pop the bubble randomly, or at the bottom of the terminal. (default: row)
      --easing (Easing Function)
                            Easing function to use for character movement after a bubble pops. (default: in_out_sine)

        Easing
        ------
        Note: A prefix must be added to the function name.
        
        All easing functions support the following prefixes:
            IN_  - Ease in
            OUT_ - Ease out
            IN_OUT_ - Ease in and out
            
        Easing Functions
        ----------------
        SINE   - Sine easing
        QUAD   - Quadratic easing
        CUBIC  - Cubic easing
        QUART  - Quartic easing
        QUINT  - Quintic easing
        EXPO   - Exponential easing
        CIRC   - Circular easing
        BACK   - Back easing
        ELASTIC - Elastic easing
        BOUNCE - Bounce easing
        
        Visit: https://easings.net/ for visualizations of the easing functions.

    Example: terminaltexteffects bubbles --bubble-colors d33aff 7395c4 43c2a7 02ff7f --pop-color ffffff --final-gradient-stops d33aff 02ff7f --final-gradient-steps 12 --final-gradient-direction diagonal --bubble-speed 0.1 --bubble-delay 50 --pop-condition row --easing IN_OUT_SINE
</details>

#### Burn
![burn_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/9770711a-ea68-48cc-947f-fb13c6613a2e)
<details>
<summary>tte burn -h</summary>
<br>
    burn | Burn the output area.

    options:
      -h, --help            show this help message and exit
      --starting-color (XTerm [0-255] OR RGB Hex [000000-ffffff])
                            Color of the characters before they start to burn. (default: 837373)
      --burn-colors (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Colors transitioned through as the characters burn. (default: ('ffffff', 'fff75d', 'fe650d', '8A003C', '510100'))
      --final-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
                            (default: ('00c3ff', 'ffff1c'))
      --final-gradient-steps (int > 0) [(int > 0) ...]
                            Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --final-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the final color. (default: Direction.VERTICAL)

    Example: terminaltexteffects burn --starting-color 837373 --burn-colors ffffff fff75d fe650d 8a003c 510100 --final-gradient-stops 00c3ff ffff1c --final-gradient-steps 12
</details>

#### Crumble
![crumble_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/f9cdea9b-b695-41b7-b129-8288232cba13)
<details>
<summary>tte crumble -h</summary>
<br>
    crumble | Characters lose color and crumble into dust, vacuumed up, and reformed.

    options:
      -h, --help            show this help message and exit
      --final-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
                            (default: ('5CE1FF', 'FF8C00'))
      --final-gradient-steps (int > 0) [(int > 0) ...]
                            Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --final-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the final color. (default: Direction.DIAGONAL)

    Example: terminaltexteffects crumble --final-gradient-stops 5CE1FF FF8C00 --final-gradient-steps 12 --final-gradient-direction diagonal
</details>

#### Decrypt
![decrypt_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/36c23e70-065d-4316-a09e-c2761882cbb3)
<details>
<summary>tte decrypt -h</summary>
<br>
    decrypt | Movie style decryption effect.

    options:
      -h, --help            show this help message and exit
      --typing-speed (int > 0)
                            Number of characters typed per keystroke. (default: 1)
      --ciphertext-colors (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the ciphertext. Color will be randomly selected for each character. (default: ('008000', '00cb00', '00ff00'))
      --final-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
                            (default: ('eda000',))
      --final-gradient-steps (int > 0) [(int > 0) ...]
                            Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --final-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the final color. (default: Direction.VERTICAL)

    Example: terminaltexteffects decrypt --typing-speed 2 --ciphertext-colors 008000 00cb00 00ff00 --final-gradient-stops eda000 --final-gradient-steps 12 --final-gradient-direction vertical
</details>

#### Errorcorrect
![errorcorrect_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/a851d333-8fe2-4c12-9c45-536ed8ebbab8)
<details>
<summary>tte errorcorrect -h</summary>
<br>
    errorcorrect | Some characters start in the wrong position and are corrected in sequence.

    options:
      -h, --help            show this help message and exit
      --error-pairs (int > 0)
                            Percent of characters that are in the wrong position. This is a float between 0 and 1.0. 0.2 means 20 percent of the characters will be in the wrong position. (default: 0.1)
      --swap-delay (int > 0)
                            Number of animation steps between swaps. (default: 10)
      --error-color (XTerm [0-255] OR RGB Hex [000000-ffffff])
                            Color for the characters that are in the wrong position. (default: e74c3c)
      --correct-color (XTerm [0-255] OR RGB Hex [000000-ffffff])
                            Color for the characters once corrected, this is a gradient from error-color and fades to final-color. (default: 45bf55)
      --final-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
                            (default: ('8A008A', '00D1FF', 'FFFFFF'))
      --final-gradient-steps (int > 0) [(int > 0) ...]
                            Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --final-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the final color. (default: Direction.VERTICAL)
      --movement-speed (float > 0)
                            Speed of the characters while moving to the correct position. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the
                            effect. (default: 0.5)

        Easing
        ------
        Note: A prefix must be added to the function name.
        
        All easing functions support the following prefixes:
            IN_  - Ease in
            OUT_ - Ease out
            IN_OUT_ - Ease in and out
            
        Easing Functions
        ----------------
        SINE   - Sine easing
        QUAD   - Quadratic easing
        CUBIC  - Cubic easing
        QUART  - Quartic easing
        QUINT  - Quintic easing
        EXPO   - Exponential easing
        CIRC   - Circular easing
        BACK   - Back easing
        ELASTIC - Elastic easing
        BOUNCE - Bounce easing
        
        Visit: https://easings.net/ for visualizations of the easing functions.

        
    Example: terminaltexteffects errorcorrect --error-pairs 0.1 --swap-delay 10 --error-color e74c3c --correct-color 45bf55 --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --movement-speed 0.5
</details>

#### Expand
![expand_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/21d1c374-9028-4546-a5d7-ee538488ee7b)
<details>
<summary>tte expand -h</summary>
<br>
    expand | Expands the text from a single point.

    options:
      -h, --help            show this help message and exit
      --final-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
                            (default: ('8A008A', '00D1FF', 'FFFFFF'))
      --final-gradient-steps (int > 0) [(int > 0) ...]
                            Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --final-gradient-frames (int > 0)
                            Number of frames to display each gradient step. (default: 5)
      --final-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the final color. (default: Direction.VERTICAL)
      --movement-speed (float > 0)
                            Movement speed of the characters. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect. (default: 0.35)
      --expand-easing EXPAND_EASING
                            Easing function to use for character movement. (default: in_out_quart)

        Easing
        ------
        Note: A prefix must be added to the function name.
        
        All easing functions support the following prefixes:
            IN_  - Ease in
            OUT_ - Ease out
            IN_OUT_ - Ease in and out
            
        Easing Functions
        ----------------
        SINE   - Sine easing
        QUAD   - Quadratic easing
        CUBIC  - Cubic easing
        QUART  - Quartic easing
        QUINT  - Quintic easing
        EXPO   - Exponential easing
        CIRC   - Circular easing
        BACK   - Back easing
        ELASTIC - Elastic easing
        BOUNCE - Bounce easing
        
        Visit: https://easings.net/ for visualizations of the easing functions.

        
    Example: terminaltexteffects expand --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --final-gradient-frames 5 --movement-speed 0.35 --expand-easing IN_OUT_QUART
</details>

#### Fireworks
![fireworks_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/da6a97b1-c4fd-4370-9852-9ddb8a494b55)
<details>
<summary>tte fireworks -h</summary>
<br>
    fireworks | Characters explode like fireworks and fall into place.

    options:
      -h, --help            show this help message and exit
      --explode-anywhere    If set, fireworks explode anywhere in the output area. Otherwise, fireworks explode above highest settled row of text. (default: False)
      --firework-colors (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated list of colors from which firework colors will be randomly selected. (default: ('88F7E2', '44D492', 'F5EB67', 'FFA15C', 'FA233E'))
      --firework-symbol (ASCII/UTF-8 character)
                            Symbol to use for the firework shell. (default: o)
      --firework-volume (0 <= float(n) <= 1)
                            Percent of total characters in each firework shell. (default: 0.02)
      --final-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
                            (default: ('8A008A', '00D1FF', 'FFFFFF'))
      --final-gradient-steps (int > 0) [(int > 0) ...]
                            Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --final-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the final color. (default: Direction.HORIZONTAL)
      --launch-delay (int >= 0)
                            Number of animation steps to wait between launching each firework shell. +/- 0-50 percent randomness is applied to this value. (default: 60)
      --explode-distance (0 <= float(n) <= 1)
                            Maximum distance from the firework shell origin to the explode waypoint as a percentage of the total output area width. (default: 0.1)

    Example: terminaltexteffects fireworks --firework-colors 88F7E2 44D492 F5EB67 FFA15C FA233E --firework-symbol o --firework-volume 0.02 --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --launch-delay 60 --explode-distance 0.1 --explode-anywhere
</details>

#### Middleout
![middleout_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/d78e37f6-ccb1-4d3b-a07c-f021b6893fce)
<details>
<summary>tte middleout -h</summary>
<br>
    middleout | Text expands in a single row or column in the middle of the output area then out.

    options:
      -h, --help            show this help message and exit
      --starting-color (XTerm [0-255] OR RGB Hex [000000-ffffff])
                            Color for the initial text in the center of the output area. (default: ffffff)
      --final-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
                            (default: ('8A008A', '00D1FF', 'FFFFFF'))
      --final-gradient-steps (int > 0) [(int > 0) ...]
                            Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --final-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the final color. (default: Direction.VERTICAL)
      --expand-direction {vertical,horizontal}
                            Direction the text will expand. (default: vertical)
      --center-movement-speed (float > 0)
                            Speed of the characters during the initial expansion of the center vertical/horiztonal line. Note: Speed effects the number of steps in the easing function. Adjust speed and animation
                            rate separately to fine tune the effect. (default: 0.35)
      --full-movement-speed (float > 0)
                            Speed of the characters during the final full expansion. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the
                            effect. (default: 0.35)
      --center-easing CENTER_EASING
                            Easing function to use for initial expansion. (default: in_out_sine)
      --full-easing FULL_EASING
                            Easing function to use for full expansion. (default: in_out_sine)

        Easing
        ------
        Note: A prefix must be added to the function name.
        
        All easing functions support the following prefixes:
            IN_  - Ease in
            OUT_ - Ease out
            IN_OUT_ - Ease in and out
            
        Easing Functions
        ----------------
        SINE   - Sine easing
        QUAD   - Quadratic easing
        CUBIC  - Cubic easing
        QUART  - Quartic easing
        QUINT  - Quintic easing
        EXPO   - Exponential easing
        CIRC   - Circular easing
        BACK   - Back easing
        ELASTIC - Elastic easing
        BOUNCE - Bounce easing
        
        Visit: https://easings.net/ for visualizations of the easing functions.

    Example: terminaltexteffects middleout --starting-color 8A008A --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --expand-direction vertical --center-movement-speed 0.35 --full-movement-speed 0.35 --center-easing IN_OUT_SINE --full-easing IN_OUT_SINE
</details>

#### Orbittingvolley
![orbittingvolley_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/084038e5-9d49-4c7d-bf15-e989f541b15c)
<details>
<summary>tte orbittingvolley -h</summary>
<br>
    orbittingvolley | Four launchers orbit the output area firing volleys of characters inward to build the input text from the center out.

    options:
      -h, --help            show this help message and exit
      --top-launcher-symbol (ASCII/UTF-8 character)
                            Symbol for the top launcher. (default: █)
      --right-launcher-symbol (ASCII/UTF-8 character)
                            Symbol for the right launcher. (default: █)
      --bottom-launcher-symbol (ASCII/UTF-8 character)
                            Symbol for the bottom launcher. (default: █)
      --left-launcher-symbol (ASCII/UTF-8 character)
                            Symbol for the left launcher. (default: █)
      --final-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
                            (default: ('FFA15C', '44D492'))
      --final-gradient-steps (int > 0) [(int > 0) ...]
                            Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --final-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the final color. (default: Direction.CENTER)
      --launcher-movement-speed (float > 0)
                            Orbitting speed of the launchers. (default: 0.5)
      --character-movement-speed (float > 0)
                            Speed of the launched characters. (default: 1)
      --volley-size (0 <= float(n) <= 1)
                            Percent of total input characters each launcher will fire per volley. Lower limit of one character. (default: 0.03)
      --launch-delay (int >= 0)
                            Number of animation ticks to wait between volleys of characters. (default: 50)
      --character-easing (Easing Function)
                            Easing function to use for launched character movement. (default: out_sine)

        Easing
        ------
        Note: A prefix must be added to the function name.
        
        All easing functions support the following prefixes:
            IN_  - Ease in
            OUT_ - Ease out
            IN_OUT_ - Ease in and out
            
        Easing Functions
        ----------------
        SINE   - Sine easing
        QUAD   - Quadratic easing
        CUBIC  - Cubic easing
        QUART  - Quartic easing
        QUINT  - Quintic easing
        EXPO   - Exponential easing
        CIRC   - Circular easing
        BACK   - Back easing
        ELASTIC - Elastic easing
        BOUNCE - Bounce easing
        
        Visit: https://easings.net/ for visualizations of the easing functions.

        
    Example: terminaltexteffects orbittingvolley --top-launcher-symbol █ --right-launcher-symbol █ --bottom-launcher-symbol █ --left-launcher-symbol █ --final-gradient-stops FFA15C 44D492 --final-gradient-steps 12 --launcher-movement-speed 0.5 --character-movement-speed 1 --volley-size 0.03 --launch-delay 50 --character-easing OUT_SINE
</details>

#### Overflow
![overflow_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/37da1088-ba15-4be9-9489-c387a6a55930)
<details>
<summary>tte overflow -h</summary>
<br>
    overflow | Input text overflows ands scrolls the terminal in a random order until eventually appearing ordered.

    options:
      -h, --help            show this help message and exit
      --final-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
                            (default: ('8A008A', '00D1FF', 'FFFFFF'))
      --final-gradient-steps (int > 0) [(int > 0) ...]
                            Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --final-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the final color. (default: Direction.VERTICAL)
      --overflow-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the overflow gradient. (default: ('f2ebc0', '8dbfb3', 'f2ebc0'))
      --overflow-cycles-range (hyphen separated int range e.g. '1-10')
                            Number of cycles to overflow the text. (default: (2, 4))
      --overflow-speed (int > 0)
                            Speed of the overflow effect. (default: 3)

    Example: terminaltexteffects overflow --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --overflow-gradient-stops f2ebc0 8dbfb3 f2ebc0 --overflow-cycles-range 2-4 --overflow-speed 3
</details>

#### Pour
![pour_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/145c2a4e-6b30-48c6-80a3-afb03edf7c22)
<details>
<summary>tte pour -h</summary>
<br>
    pour | Pours the characters into position from the given direction.

    options:
      -h, --help            show this help message and exit
      --pour-direction {up,down,left,right}
                            Direction the text will pour. (default: down)
      --pour-speed (int > 0)
                            Number of characters poured in per tick. Increase to speed up the effect. (default: 1)
      --movement-speed (float > 0)
                            Movement speed of the characters. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect. (default: 0.2)
      --gap (int >= 0)      Number of frames to wait between each character in the pour effect. Increase to slow down effect and create a more defined back and forth motion. (default: 1)
      --starting-color (XTerm [0-255] OR RGB Hex [000000-ffffff])
                            Color of the characters before the gradient starts. (default: ffffff)
      --final-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the character gradient. If only one color is provided, the characters will be displayed in that color. (default: ('8A008A', '00D1FF',
                            'FFFFFF'))
      --final-gradient-steps (int > 0)
                            Number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --final-gradient-frames (int > 0)
                            Number of frames to display each gradient step. (default: 10)
      --final-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the final color. (default: Direction.VERTICAL)
      --easing EASING       Easing function to use for character movement. (default: in_quad)

        Easing
        ------
        Note: A prefix must be added to the function name.
        
        All easing functions support the following prefixes:
            IN_  - Ease in
            OUT_ - Ease out
            IN_OUT_ - Ease in and out
            
        Easing Functions
        ----------------
        SINE   - Sine easing
        QUAD   - Quadratic easing
        CUBIC  - Cubic easing
        QUART  - Quartic easing
        QUINT  - Quintic easing
        EXPO   - Exponential easing
        CIRC   - Circular easing
        BACK   - Back easing
        ELASTIC - Elastic easing
        BOUNCE - Bounce easing
        
        Visit: https://easings.net/ for visualizations of the easing functions.

    Example: terminaltexteffects pour --pour-direction down --movement-speed 0.2 --gap 1 --starting-color FFFFFF --final-gradient-stops 8A008A 00D1FF FFFFFF --easing IN_QUAD
</details>

#### Print
![print_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/5d902350-e5d3-400c-9496-119c88d40643)
<details>
<summary>tte print -h</summary>
<br>
    print | Lines are printed one at a time following a print head. Print head performs line feed, carriage return.

    options:
      -h, --help            show this help message and exit
      --final-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
                            (default: ('02b8bd', 'c1f0e3', '00ffa0'))
      --final-gradient-steps (int > 0) [(int > 0) ...]
                            Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --final-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the final color. (default: Direction.DIAGONAL)
      --print-head-return-speed (float > 0)
                            Speed of the print head when performing a carriage return. (default: 1.25)
      --print-speed (int > 0)
                            Speed of the print head when printing characters. (default: 1)
      --print-head-easing PRINT_HEAD_EASING
                            Easing function to use for print head movement. (default: in_out_quad)

        Easing
        ------
        Note: A prefix must be added to the function name.
        
        All easing functions support the following prefixes:
            IN_  - Ease in
            OUT_ - Ease out
            IN_OUT_ - Ease in and out
            
        Easing Functions
        ----------------
        SINE   - Sine easing
        QUAD   - Quadratic easing
        CUBIC  - Cubic easing
        QUART  - Quartic easing
        QUINT  - Quintic easing
        EXPO   - Exponential easing
        CIRC   - Circular easing
        BACK   - Back easing
        ELASTIC - Elastic easing
        BOUNCE - Bounce easing
        
        Visit: https://easings.net/ for visualizations of the easing functions.

        
    Example: terminaltexteffects print --final-gradient-stops 02b8bd c1f0e3 00ffa0 --final-gradient-steps 12 --print-head-return-speed 1.25 --print-speed 1 --print-head-easing IN_OUT_QUAD
</details>

#### Rain
![rain_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/7b8cf447-67b6-41e9-b354-07b3e5161d10)
<details>
<summary>tte rain -h</summary>
<br>
    rain | Rain characters from the top of the output area.

    options:
      -h, --help            show this help message and exit
      --rain-colors (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            List of colors for the rain drops. Colors are randomly chosen from the list. (default: ('00315C', '004C8F', '0075DB', '3F91D9', '78B9F2', '9AC8F5', 'B8D8F8', 'E3EFFC'))
      --movement-speed (hyphen separated float range e.g. '0.25-0.5')
                            Falling speed range of the rain drops. (default: (0.1, 0.2))
      --rain-symbols (ASCII/UTF-8 character) [(ASCII/UTF-8 character) ...]
                            Space separated list of symbols to use for the rain drops. Symbols are randomly chosen from the list. (default: ('o', '.', ',', '*', '|'))
      --final-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
                            (default: ('488bff', 'b2e7de', '57eaf7'))
      --final-gradient-steps (int > 0) [(int > 0) ...]
                            Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --final-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the final color. (default: Direction.DIAGONAL)
      --easing (Easing Function)
                            Easing function to use for character movement. (default: in_quart)

        Easing
        ------
        Note: A prefix must be added to the function name.
        
        All easing functions support the following prefixes:
            IN_  - Ease in
            OUT_ - Ease out
            IN_OUT_ - Ease in and out
            
        Easing Functions
        ----------------
        SINE   - Sine easing
        QUAD   - Quadratic easing
        CUBIC  - Cubic easing
        QUART  - Quartic easing
        QUINT  - Quintic easing
        EXPO   - Exponential easing
        CIRC   - Circular easing
        BACK   - Back easing
        ELASTIC - Elastic easing
        BOUNCE - Bounce easing
        
        Visit: https://easings.net/ for visualizations of the easing functions.
    
    Example: terminaltexteffects rain --rain-symbols o . , "*" "|" --rain-colors 00315C 004C8F 0075DB 3F91D9 78B9F2 9AC8F5 B8D8F8 E3EFFC --final-gradient-stops 488bff b2e7de 57eaf7 --final-gradient-steps 12 --movement-speed 0.1-0.2 --easing IN_QUART
</details>

#### RandomSequence
![randomsequence_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/a2218f80-73b6-40ab-b2fb-49268cf9f890)
<details>
<summary>tte randomsequence -h</summary>
<br>
    randomsequence | Prints the input data in a random sequence.

    options:
      -h, --help            show this help message and exit
      --starting-color (XTerm [0-255] OR RGB Hex [000000-ffffff])
                            Color of the characters at spawn. (default: 000000)
      --final-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
                            (default: ('8A008A', '00D1FF', 'FFFFFF'))
      --final-gradient-steps (int > 0) [(int > 0) ...]
                            Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --final-gradient-frames (int > 0)
                            Number of frames to display each gradient step. (default: 12)
      --final-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the final color. (default: Direction.VERTICAL)
      --speed (float > 0)   Speed of the animation as a percentage of the total number of characters. (default: 0.004)

    Example: terminaltexteffects randomsequence --starting-color 000000 --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --final-gradient-frames 12 --speed 0.004
</details>

#### Rings
![rings_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/cb7f6388-0f46-42f1-a2b3-6a267e9451f0)
<details>
<summary>tte rings -h</summary>
<br>
    rings | Characters are dispersed and form into spinning rings.

    options:
      -h, --help            show this help message and exit
      --ring-colors (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the rings. (default: ('ab48ff', 'e7b2b2', 'fffebd'))
      --final-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
                            (default: ('ab48ff', 'e7b2b2', 'fffebd'))
      --final-gradient-steps (int > 0) [(int > 0) ...]
                            Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --final-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the final color. (default: Direction.VERTICAL)
      --ring-gap RING_GAP   Distance between rings as a percent of the smallest output area dimension. (default: 0.1)
      --spin-duration SPIN_DURATION
                            Number of animation steps for each cycle of the spin phase. (default: 200)
      --spin-speed (hyphen separated float range e.g. '0.25-0.5')
                            Range of speeds for the rotation of the rings. The speed is randomly selected from this range for each ring. (default: (0.25, 1.0))
      --disperse-duration DISPERSE_DURATION
                            Number of animation steps spent in the dispersed state between spinning cycles. (default: 200)
      --spin-disperse-cycles SPIN_DISPERSE_CYCLES
                            Number of times the animation will cycles between spinning rings and dispersed characters. (default: 3)

    Example: terminaltexteffects rings --ring-colors ab48ff e7b2b2 fffebd --final-gradient-stops ab48ff e7b2b2 fffebd --final-gradient-steps 12 --ring-gap 0.1 --spin-duration 200 --spin-speed 0.25-1.0 --disperse-duration 200 --spin-disperse-cycles 3
</details>

#### Scattered
![scattered_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/9948519d-0158-4ddf-ae3a-7d4eddb706d9)
<details>
<summary>tte scattered -h</summary>
<br>
    scattered | Move the characters into place from random starting locations.

    options:
      -h, --help            show this help message and exit
      --final-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the character gradient. If only one color is provided, the characters will be displayed in that color. (default: ('ff9048', 'ab9dff',
                            'bdffea'))
      --final-gradient-steps (int > 0)
                            Number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --final-gradient-frames (int > 0)
                            Number of frames to display each gradient step. (default: 12)
      --final-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the final color. (default: Direction.VERTICAL)
      --movement-speed (float > 0)
                            Movement speed of the characters. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect. (default: 0.5)
      --movement-easing MOVEMENT_EASING
                            Easing function to use for character movement. (default: in_out_back)

        Easing
        ------
        Note: A prefix must be added to the function name.
        
        All easing functions support the following prefixes:
            IN_  - Ease in
            OUT_ - Ease out
            IN_OUT_ - Ease in and out
            
        Easing Functions
        ----------------
        SINE   - Sine easing
        QUAD   - Quadratic easing
        CUBIC  - Cubic easing
        QUART  - Quartic easing
        QUINT  - Quintic easing
        EXPO   - Exponential easing
        CIRC   - Circular easing
        BACK   - Back easing
        ELASTIC - Elastic easing
        BOUNCE - Bounce easing
        
        Visit: https://easings.net/ for visualizations of the easing functions.

    Example: terminaltexteffects scattered --final-gradient-stops ff9048 ab9dff bdffea --final-gradient-steps 12 --final-gradient-frames 12 --movement-speed 0.5 --movement-easing IN_OUT_BACK
</details>

#### Slide
![slide_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/218e7218-e9ef-44de-b43b-5e824623a957)
<details>
<summary>tte slide -h</summary>
<br>
    slide | Slide characters into view from outside the terminal, grouped by row, column, or diagonal.

    options:
      -h, --help            show this help message and exit
      --movement-speed (float > 0)
                            Speed of the characters. (default: 0.5)
      --grouping {row,column,diagonal}
                            Direction to group characters. (default: row)
      --final-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the character gradient. If only one color is provided, the characters will be displayed in that color. (default: ('833ab4', 'fd1d1d',
                            'fcb045'))
      --final-gradient-steps (int > 0)
                            Number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --final-gradient-frames (int > 0)
                            Number of frames to display each gradient step. (default: 10)
      --final-gradient-direction FINAL_GRADIENT_DIRECTION
                            Direction of the gradient (vertical, horizontal, diagonal, center). (default: Direction.VERTICAL)
      --gap (int >= 0)      Number of frames to wait before adding the next group of characters. Increasing this value creates a more staggered effect. (default: 3)
      --reverse-direction   Reverse the direction of the characters. (default: False)
      --merge               Merge the character groups originating from either side of the terminal. (--reverse-direction is ignored when merging) (default: False)
      --movement-easing (Easing Function)
                            Easing function to use for character movement. (default: in_out_quad)

        Easing
        ------
        Note: A prefix must be added to the function name.
        
        All easing functions support the following prefixes:
            IN_  - Ease in
            OUT_ - Ease out
            IN_OUT_ - Ease in and out
            
        Easing Functions
        ----------------
        SINE   - Sine easing
        QUAD   - Quadratic easing
        CUBIC  - Cubic easing
        QUART  - Quartic easing
        QUINT  - Quintic easing
        EXPO   - Exponential easing
        CIRC   - Circular easing
        BACK   - Back easing
        ELASTIC - Elastic easing
        BOUNCE - Bounce easing
        
        Visit: https://easings.net/ for visualizations of the easing functions.

    Example: terminaltexteffects slide --movement-speed 0.5 --grouping row --final-gradient-stops 833ab4 fd1d1d fcb045 --final-gradient-steps 12 --final-gradient-frames 10 --final-gradient-direction vertical --gap 3 --reverse-direction --merge --movement-easing OUT_QUAD
</details>

#### Spotlights
![spotlights_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/4ab93725-0c8a-4bdf-af91-057338f4e007)
<details>
<summary>tte spotlights -h</summary>
<br>
    spotlights | Spotlights search the text area, illuminating characters, before converging in the center and expanding.

    options:
      -h, --help            show this help message and exit
      --final-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
                            (default: ('ab48ff', 'e7b2b2', 'fffebd'))
      --final-gradient-steps (int > 0) [(int > 0) ...]
                            Number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --final-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the final color. (default: Direction.VERTICAL)
      --beam-width-ratio (float > 0)
                            Width of the beam of light as min(width, height) // n of the input text. (default: 2.0)
      --beam-falloff (float >= 0)
                            Distance from the edge of the beam where the brightness begins to fall off, as a percentage of total beam width. (default: 0.3)
      --search-duration (int > 0)
                            Duration of the search phase, in animation steps, before the spotlights converge in the center. (default: 750)
      --search-speed-range (hyphen separated float range e.g. '0.25-0.5')
                            Range of speeds for the spotlights during the search phase. The speed is a random value between the two provided values. (default: (0.25, 0.5))
      --spotlight-count (int > 0)
                            Number of spotlights to use. (default: 3)

        Easing
        ------
        Note: A prefix must be added to the function name.
        
        All easing functions support the following prefixes:
            IN_  - Ease in
            OUT_ - Ease out
            IN_OUT_ - Ease in and out
            
        Easing Functions
        ----------------
        SINE   - Sine easing
        QUAD   - Quadratic easing
        CUBIC  - Cubic easing
        QUART  - Quartic easing
        QUINT  - Quintic easing
        EXPO   - Exponential easing
        CIRC   - Circular easing
        BACK   - Back easing
        ELASTIC - Elastic easing
        BOUNCE - Bounce easing
        
        Visit: https://easings.net/ for visualizations of the easing functions.

    Example: terminaltexteffects spotlights --final-gradient-stops ab48ff e7b2b2 fffebd --final-gradient-steps 12 --beam-width-ratio 2.0 --beam-falloff 0.3 --search-duration 750 --search-speed-range 0.25-0.5 --spotlight-count 3
</details>

#### Spray
![spray_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/0be02197-11c3-44d0-9e7f-cd90caefa876)
<details>
<summary>tte spray -h</summary>
<br>
    spray | Draws the characters spawning at varying rates from a single point.

    options:
      -h, --help            show this help message and exit
      --final-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
                            (default: ('8A008A', '00D1FF', 'FFFFFF'))
      --final-gradient-steps (int > 0) [(int > 0) ...]
                            Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --final-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the final color. (default: Direction.VERTICAL)
      --spray-position {n,ne,e,se,s,sw,w,nw,center}
                            Position for the spray origin. (default: e)
      --spray-volume (float > 0)
                            Number of characters to spray per tick as a percent of the total number of characters. (default: 0.005)
      --movement-speed (hyphen separated float range e.g. '0.25-0.5')
                            Movement speed of the characters. (default: (0.4, 1.0))
      --movement-easing MOVEMENT_EASING
                            Easing function to use for character movement. (default: out_expo)

        Easing
        ------
        Note: A prefix must be added to the function name.
        
        All easing functions support the following prefixes:
            IN_  - Ease in
            OUT_ - Ease out
            IN_OUT_ - Ease in and out
            
        Easing Functions
        ----------------
        SINE   - Sine easing
        QUAD   - Quadratic easing
        CUBIC  - Cubic easing
        QUART  - Quartic easing
        QUINT  - Quintic easing
        EXPO   - Exponential easing
        CIRC   - Circular easing
        BACK   - Back easing
        ELASTIC - Elastic easing
        BOUNCE - Bounce easing
        
        Visit: https://easings.net/ for visualizations of the easing functions.
        
    Example: terminaltexteffects spray --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --spray-position e --spray-volume 0.005 --movement-speed 0.4-1.0 --movement-easing OUT_EXPO
</details>

#### Swarm
![swarm_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/305e8390-a0fb-4edb-a541-7b52cef77c09)
<details>
<summary>tte swarm -h</summary>
<br>
    swarm | Characters are grouped into swarms and move around the terminal before settling into position.

    options:
      -h, --help            show this help message and exit
      --base-color (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the swarms (default: ('31a0d4',))
      --flash-color (XTerm [0-255] OR RGB Hex [000000-ffffff])
                            Color for the character flash. Characters flash when moving. (default: f2ea79)
      --final-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
                            (default: ('31b900', 'f0ff65'))
      --final-gradient-steps (int > 0) [(int > 0) ...]
                            Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --final-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the final color. (default: Direction.HORIZONTAL)
      --swarm-size (0 <= float(n) <= 1)
                            Percent of total characters in each swarm. (default: 0.1)
      --swarm-coordination (0 <= float(n) <= 1)
                            Percent of characters in a swarm that move as a group. (default: 0.8)
      --swarm-area-count (hyphen separated int range e.g. '1-10')
                            Range of the number of areas where characters will swarm. (default: (2, 4))

    Example: terminaltexteffects swarm --base-color 31a0d4 --flash-color f2ea79 --final-gradient-stops 31b900 f0ff65 --final-gradient-steps 12 --swarm-size 0.1 --swarm-coordination 0.80 --swarm-area-count 2-4
</details>

#### Synthgrid
![synthgrid_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/6d1bab16-0520-44fa-a508-8f92d7d3be9e)
<details>
<summary>tte synthgrid -h</summary>
<br>
    synthgrid | Create a grid which fills with characters dissolving into the final text.

    options:
      -h, --help            show this help message and exit
      --grid-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the grid gradient. (default: ('CC00CC', 'ffffff'))
      --grid-gradient-steps (int > 0) [(int > 0) ...]
                            Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --grid-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the grid color. (default: Direction.DIAGONAL)
      --text-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the text gradient. (default: ('8A008A', '00D1FF', 'FFFFFF'))
      --text-gradient-steps (int > 0) [(int > 0) ...]
                            Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --text-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the text color. (default: Direction.VERTICAL)
      --grid-row-symbol (ASCII/UTF-8 character)
                            Symbol to use for grid row lines. (default: ─)
      --grid-column-symbol (ASCII/UTF-8 character)
                            Symbol to use for grid column lines. (default: │)
      --text-generation-symbols (ASCII/UTF-8 character) [(ASCII/UTF-8 character) ...]
                            Space separated, unquoted, list of characters for the text generation animation. (default: ('░', '▒', '▓'))
      --max-active-blocks (float > 0)
                            Maximum percentage of blocks to have active at any given time. For example, if set to 0.1, 10 percent of the blocks will be active at any given time. (default: 0.1)

    Example: terminaltexteffects synthgrid --grid-gradient-stops CC00CC ffffff --grid-gradient-steps 12 --text-gradient-stops 8A008A 00D1FF FFFFFF --text-gradient-steps 12 --grid-row-symbol ─ --grid-column-symbol "│" --text-generation-symbols ░ ▒ ▓ --max-active-blocks 0.1
</details>

#### Unstable
![unstable_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/29adb5bf-cd35-4d67-9ed4-fa73ebcb892d)
<details>
<summary>tte unstable -h</summary>
<br>
    synthgrid | Create a grid which fills with characters dissolving into the final text.

    options:
      -h, --help            show this help message and exit
      --grid-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the grid gradient. (default: ('CC00CC', 'ffffff'))
      --grid-gradient-steps (int > 0) [(int > 0) ...]
                            Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --grid-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the grid color. (default: Direction.DIAGONAL)
      --text-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the text gradient. (default: ('8A008A', '00D1FF', 'FFFFFF'))
      --text-gradient-steps (int > 0) [(int > 0) ...]
                            Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --text-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the text color. (default: Direction.VERTICAL)
      --grid-row-symbol (ASCII/UTF-8 character)
                            Symbol to use for grid row lines. (default: ─)
      --grid-column-symbol (ASCII/UTF-8 character)
                            Symbol to use for grid column lines. (default: │)
      --text-generation-symbols (ASCII/UTF-8 character) [(ASCII/UTF-8 character) ...]
                            Space separated, unquoted, list of characters for the text generation animation. (default: ('░', '▒', '▓'))
      --max-active-blocks (float > 0)
                            Maximum percentage of blocks to have active at any given time. For example, if set to 0.1, 10 percent of the blocks will be active at any given time. (default: 0.1)

    Example: terminaltexteffects synthgrid --grid-gradient-stops CC00CC ffffff --grid-gradient-steps 12 --text-gradient-stops 8A008A 00D1FF FFFFFF --text-gradient-steps 12 --grid-row-symbol ─ --grid-column-symbol "│" --text-generation-symbols ░ ▒ ▓ --max-active-blocks 0.1
</details>

#### Verticalslice
![verticalslice_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/2341a822-7fef-4ebf-9420-8272fff64082)
<details>
<summary>tte verticalslice -h</summary>
<br>
    verticalslice | Slices the input in half vertically and slides it into place from opposite directions.

    options:
      -h, --help            show this help message and exit
      --final-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
                            (default: ('8A008A', '00D1FF', 'FFFFFF'))
      --final-gradient-steps (int > 0) [(int > 0) ...]
                            Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --final-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the final color. (default: Direction.VERTICAL)
      --movement-speed (float > 0)
                            Movement speed of the characters. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect. (default: 0.15)
      --movement-easing MOVEMENT_EASING
                            Easing function to use for character movement. (default: in_out_expo)

        Easing
        ------
        Note: A prefix must be added to the function name.
        
        All easing functions support the following prefixes:
            IN_  - Ease in
            OUT_ - Ease out
            IN_OUT_ - Ease in and out
            
        Easing Functions
        ----------------
        SINE   - Sine easing
        QUAD   - Quadratic easing
        CUBIC  - Cubic easing
        QUART  - Quartic easing
        QUINT  - Quintic easing
        EXPO   - Exponential easing
        CIRC   - Circular easing
        BACK   - Back easing
        ELASTIC - Elastic easing
        BOUNCE - Bounce easing
        
        Visit: https://easings.net/ for visualizations of the easing functions.

        
    Example: terminaltexteffects verticalslice --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --movement-speed 0.15 --movement-easing IN_OUT_EXPO
</details>

#### VHSTape
![vhstape_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/720abbf4-f97d-4ce9-96ee-15ef973488d2)
<details>
<summary>tte vhstape -h</summary>
<br>
    vhstape | Lines of characters glitch left and right and lose detail like an old VHS tape.

    options:
      -h, --help            show this help message and exit
      --final-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
                            (default: ('ab48ff', 'e7b2b2', 'fffebd'))
      --final-gradient-steps (int > 0) [(int > 0) ...]
                            Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --final-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the final color. (default: Direction.VERTICAL)
      --glitch-line-colors (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the characters when a single line is glitching. Colors are applied in order as an animation. (default: ('ffffff', 'ff0000', '00ff00',
                            '0000ff', 'ffffff'))
      --glitch-wave-colors (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the characters in lines that are part of the glitch wave. Colors are applied in order as an animation. (default: ('ffffff', 'ff0000',
                            '00ff00', '0000ff', 'ffffff'))
      --noise-colors (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the characters during the noise phase. (default: ('1e1e1f', '3c3b3d', '6d6c70', 'a2a1a6', 'cbc9cf', 'ffffff'))
      --glitch-line-chance (0 <= float(n) <= 1)
                            Chance that a line will glitch on any given frame. (default: 0.05)
      --noise-chance (0 <= float(n) <= 1)
                            Chance that all characters will experience noise on any given frame. (default: 0.004)
      --total-glitch-time (int > 0)
                            Total time, animation steps, that the glitching phase will last. (default: 1000)

    Example: terminaltexteffects vhstape --final-gradient-stops ab48ff e7b2b2 fffebd --final-gradient-steps 12 --glitch-line-colors ffffff ff0000 00ff00 0000ff ffffff --glitch-wave-colors ffffff ff0000 00ff00 0000ff ffffff --noise-colors 1e1e1f 3c3b3d 6d6c70 a2a1a6 cbc9cf ffffff --glitch-line-chance 0.05 --noise-chance 0.004 --total-glitch-time 1000
</details>

#### Waves
![waves_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/ea9b04ca-e526-4c7e-b98d-a98a42f7137f)
<details>
<summary>tte waves -h</summary>
<br>
    waves | Waves travel across the terminal leaving behind the characters.

    options:
      -h, --help            show this help message and exit
      --wave-symbols (ASCII/UTF-8 character) [(ASCII/UTF-8 character) ...]
                            Symbols to use for the wave animation. Multi-character strings will be used in sequence to create an animation. (default: ('▁', '▂', '▃', '▄', '▅', '▆', '▇', '█', '▇', '▆', '▅', '▄',
                            '▃', '▂', '▁'))
      --wave-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
                            (default: ('f0ff65', 'ffb102', '31a0d4', 'ffb102', 'f0ff65'))
      --wave-gradient-steps (int > 0) [(int > 0) ...]
                            Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (6,))
      --final-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
                            (default: ('ffb102', '31a0d4', 'f0ff65'))
      --final-gradient-steps (int > 0) [(int > 0) ...]
                            Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --final-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the final color. (default: Direction.DIAGONAL)
      --wave-count WAVE_COUNT
                            Number of waves to generate. n > 0. (default: 7)
      --wave-length (int > 0)
                            The number of frames for each step of the wave. Higher wave-lengths will create a slower wave. (default: 2)
      --wave-easing WAVE_EASING
                            Easing function to use for wave travel. (default: in_out_sine)

        Easing
        ------
        Note: A prefix must be added to the function name.
        
        All easing functions support the following prefixes:
            IN_  - Ease in
            OUT_ - Ease out
            IN_OUT_ - Ease in and out
            
        Easing Functions
        ----------------
        SINE   - Sine easing
        QUAD   - Quadratic easing
        CUBIC  - Cubic easing
        QUART  - Quartic easing
        QUINT  - Quintic easing
        EXPO   - Exponential easing
        CIRC   - Circular easing
        BACK   - Back easing
        ELASTIC - Elastic easing
        BOUNCE - Bounce easing
        
        Visit: https://easings.net/ for visualizations of the easing functions.

    Example: terminaltexteffects waves --wave-symbols ▁ ▂ ▃ ▄ ▅ ▆ ▇ █ ▇ ▆ ▅ ▄ ▃ ▂ ▁ --wave-gradient-stops f0ff65 ffb102 31a0d4 ffb102 f0ff65 --wave-gradient-steps 6 --final-gradient-stops ffb102 31a0d4 f0ff65 --final-gradient-steps 12 --wave-count 7 --wave-length 2 --wave-easing IN_OUT_SINE
</details>

#### Wipe
![wipe_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/40b8c81e-6143-4839-af56-12e361651a0a)
<details>
<summary>tte wipe -h</summary>
<br>
    wipe | Wipes the text across the terminal to reveal characters.

    options:
      -h, --help            show this help message and exit
      --wipe-direction {column_left_to_right,column_right_to_left,row_top_to_bottom,row_bottom_to_top,diagonal_top_left_to_bottom_right,diagonal_bottom_left_to_top_right,diagonal_top_right_to_bottom_left,diagonal_bottom_right_to_top_left}
                            Direction the text will wipe. (default: diagonal_bottom_left_to_top_right)
      --final-gradient-stops (XTerm [0-255] OR RGB Hex [000000-ffffff]) [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated, unquoted, list of colors for the wipe gradient. (default: ('833ab4', 'fd1d1d', 'fcb045'))
      --final-gradient-steps (int > 0) [(int > 0) ...]
                            Number of gradient steps to use. More steps will create a smoother and longer gradient animation. (default: (12,))
      --final-gradient-frames (int > 0)
                            Number of frames to display each gradient step. (default: 5)
      --final-gradient-direction (diagonal, horizontal, vertical, center)
                            Direction of the gradient for the final color. (default: Direction.VERTICAL)
      --wipe-delay (int >= 0)
                            Number of animation cycles to wait before adding the next character group. Increase, to slow down the effect. (default: 0)

    Example: terminaltexteffects wipe --wipe-direction diagonal_bottom_left_to_top_right --final-gradient-stops 833ab4 fd1d1d fcb045 --final-gradient-steps 12 --final-gradient-frames 5 --wipe-delay 0
</details>

## In-Development Preview
Any effects shown below are in development and will be available in the next release.


## Latest Release Notes

## 0.7.0

### New Features
#### Effects
 * Beams. Light beams travel across the output area and illuminate the characters behind them.
 * Overflow. The input text is scrambled by row and repeated randomly, scrolling up the terminal, before eventually displaying in the correct order.
 * OrbitingVolley. Characters fire from launcher which orbit output area.
 * Spotlights. Spotlights search the text area, illuminating characters, before converging in the center and expanding.

#### Engine
 * Gradients now support multiple step specification to control the distance between each stop pair. For example:
   graphics.Gradient(RED, BLUE, YELLOW, steps=(2,5)) results in a spectrum of RED -> (1 step) -> BLUE -> (4 steps) -> YELLOW
 * graphics.Gradient.get_color_at_fraction(fraction: float) will return a color at the given fraction of the spectrum when provided a float between 0 and 1, inclusive. This can be used to match the color to a ratio/ For example, the character height in the terminal.
 * graphics.Gradient.build_coordinate_color_mapping() will map gradient colors to coordinates in the terminal and supports a Gradient.Direction argument to enable gradients in the following directions: horizontal, vertical, diagonal, center
 * graphics.Gradient, if printed, will show a colored spectrum and the description of its stops and steps.
 * The Scene class has a new method: apply_gradient_to_symbols(). This method will iterate over a list of symbols and apply the colors from a gradient to the symbols. A frame with the symbol will be added for each color starting from the last color used in the previous symbol, up to the the index determined by the ratio of the current symbol's index in the symbols list to the total length of the list. This method allows scenes to automatically create frames from a list of symbols and gradient of arbitrary length while ensuring every symbol and color is displayed.
 * On instatiation, Terminal creates EffectCharacters for every coordinate in the output area that does not have an input character. These EffectCharacters have the symbol " " and are stored in Terminal._fill_characters as well as added to Terminal.character_by_input_coord.
 * arg_validators.IntRange will validate a range specified as "int-int" and return a tuple[int,int].
 * arg_validators.FloatRange will validate a range of floats specified as "float-float" and return a tuple[float, float].
 * character.animation.set_appearance(symbol, color) will set the character symbol and color directly. If a Scene is active, the appearance will be overwritten with the Scene frame on the next call to step_animation(). This method is intended for the occasion where a full scene isn't needed, or the appearance needs to be set based on conditions not compatible with Scenes or the EventHandler. For example, setting the color based on the terminal row. 
 * Terminal.CharacterSort enums moved to Terminal.CharacterGroup, Terminal.CharacterSort is now used for sorting and return a flat list of characters.
 * Terminal.CharacterSort has new sort methods, TOP_TO_BOTTOM_LEFT_TO_RIGHT, TOP_TO_BOTTOM_RIGHT_TO_LEFT, BOTTOM_TO_TOP_LEFT_TO_RIGHT, BOTTOM_TO_TOP_RIGHT_TO_LEFT, OUTSIDE_ROW_TO_MIDDLE, MIDDLE_ROW_TO_OUTSIDE
 * New Terminal.CharacterGroup options, CENTER_TO_OUTSIDE_DIAMONDS and OUTSIDE_TO_CENTER_DIAMONS
 * graphics.Animation.adjust_color_brightness(color: graphics.Color, brightness: float) will convert the color to HSL, adjust the brightness to the given level, and return 
   an RGB hex string.
 * CTRL-C keyboard interrupt during a running effect will exit gracefully.
 * geometry.find_coords_in_circle() has been rewritten to find all coords which fall in an ellipse. The result is a circle due to the height/width ratio of terminal cells. This function now finds all terminal coordinates within the 'circle' rather than an arbitrary subset.
 * All command line arguments are typed allowing for more easily defined and tested effect args. 

### Changes
#### Effects
 * All effects have been updated to use the latest API calls for improved performance.
 * All effects support gradients for the final appearance.
 * All effects support gradient direction.
 * All effects have had their default colors refreshed.
 * ErrorCorrect swap-delay lowered and error-pairs specification changed to percent float.
 * Rain effect supports character specification for rain drops and movement speed range for the rain drop falling speed.
 * Print effect uses the row final gradient color for the print head color.
 * RandomSequence effect accepts a starting color and a speed.
 * Rings effect prepares faster. Ring colors are set in order of appearance in the ring-colors argument. Ring spin speed is configurable. Rings with less than 25% visible characters based on radius are no longer generated. Ring gap is set as a percent of the smallest output area dimension.
 * Scattered effect gradient progresses from the first color to the row color.
 * Spray effect spray-volume is specified as a percent of the total number of characters and movement speed is a range.
 * Swarm effect swarm focus points algorithm changed to reduce long distances between points. 
 * Decrypt effect supports gradient specification for plaintext and multiple color specification for ciphertext.
 * Decrypt effect has a --typing-speed arg to increase the speed of the initial text typing effect.
 * Decrypt effect has had the decrypting speed increased.
 * Beams effect uses Animation.adjust_color_brightness() to lower the background character brightness and shows the lighter color when the beam passes by.
 * Crumble effect uses Animation.adjust_color_brightness() to set the weak and dust colors based on the final gradient.
 * Fireworks effect launch_delay argument has a +/- 0-50% randomness applied. 
 * Bubbles effect --no-rainbow changed to --rainbow and default set to False.
 * Bubbles effect --bubble-color changed to --bubble-colors. Bubble color is randomly chosen from the colors unless --rainbow is used.
 * Burn effect burns faster with some randomness in speed.
 * Burn effect final color fades in from the burned color.
 * Burn effect characters are shown prior to burning using a starting_color arg.
 * Pour effect has a --pour-speed argument.

#### Engine
 * Geometry related methods have been removed from the motion class. They are now located at terminaltexteffects.utils.geometry as separate functions.
 * The Coord() object definition has been moved from the motion module to the geometry module.
 * Terminal.add_character() takes a geometry.Coord() argument to set the character's input_coordinate.
 * EffectCharacters have a unique ID set by the Terminal on instatiation. As a result, all EffectCharacters should be created using Terminal.add_character().
 * EffectCharacters added by the effect are stored in Terminal._added_characters.
 * Retrieving EffectCharacters from the terminal should no longer be done via accessing the lists of characters [_added_characters, _fill_characters, _input_characters], but should be retrieved via Terminal.get_characters() and Terminal.get_characters_sorted(). 
 * Setting EffectCharacter visibility is now done via Terminal.set_character_visibility(). This enables the terminal to keep track of all visible characters without needing to iterate over all characters on every call to _update_terminal_state().
 * EventHandler.Action.SET_CHARACTER_VISIBILITY_STATE has been removed as visibilty state is handled by the Terminal. To enable visibility state changes through the event system, use a CALLBACK action with target EventHandler.Callback(terminal.set_character_visibility, True/False).
 * geometry.find_coords_on_circle() num_points arg renamed to points_limit and new arg unique: bool, added to remove any duplicate Coords.
 * The animation rate argument (-a, --animation-rate) has been removed from all effects and is handled as a terminal argument specified prior to the effect name.
 * argtypes.py has been renamed arg_validators.py and all functions have been refactored into classes with a METAVAR class member and a type_parser method.
 * easing.EasingFunction type alias used anywhere an easing function is accepted.
 * Exceptions raised are no longer caught in a except clause. Only a finally clause is used to restore the cursor. Tracebacks are useful.
 
 #### Other
 * More tests have been added.

### Bug Fixes
#### Effects
 * All effects with command line options that accept variable length arguments which require at least 1 argument will present an error message when the option is called with 0 arguments.

#### Engine
 * Fixed division by zero error in geometry.find_coord_at_distance() when the origin coord and the target coord are the same.
 * Fixed gradient generating an extra color in the spectrum when the initial color pair was repeated. Ex: Gradient('ffffff','000000','ffffff','000000, steps=5) would result in the third color 'ffffff' being added to the spectrum when it was already present as the end of the generation from '000000'->'ffffff'. 

## License

Distributed under the MIT License. See [LICENSE](https://github.com/ChrisBuilds/terminaltexteffects/blob/main/LICENSE.md) for more information.
