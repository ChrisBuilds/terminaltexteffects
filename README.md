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
![synthgrid_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/ebd8d3f1-c8b0-4de9-81ad-b70dde5a07b4)


TerminalTextEffects is a collection of visual effects that run inline in the terminal. The underlying visual effect framework supports the following:
* Xterm 256 color and RBG hex color support                 
* Color gradients                                           
* Runs inline, preserving terminal state and workflow       
* Dynamic character movement with motion easing             
* Dynamic animations with symbol and color changes and animation easing          
* Effect customization through command line arguments 

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
  --xterm-colors        Convert any colors specified in RBG hex to the closest XTerm-256 color.
  --no-color            Disable all colors in the effect.
  --tab-width TAB_WIDTH
                        Number of spaces to use for a tab character.
  --no-wrap             Disable wrapping of text.

Effect:
  Name of the effect to apply. Use <effect> -h for effect specific help.

  {binarypath,blackhole,bouncyballs,bubbles,burn,crumble,decrypt,errorcorrect,expand,fireworks,middleout,pour,print,rain,randomsequence,rings,scattered,slide,spray,swarm,synthgrid,test,unstable,verticalslice,vhstape,waves,wipe}
                        Available Effects
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
    pour                Pours the characters into position from the given direction.
    print               Lines are printed one at a time following a print head. Print head performs line feed, carriage return.
    rain                Rain characters from the top of the output area.
    randomsequence      Prints the input data in a random sequence.
    rings               Characters are dispersed and form into spinning rings.
    scattered           Move the characters into place from random starting locations.
    slide               Slide characters into view from outside the terminal.
    spray               Draws the characters spawning at varying rates from a single point.
    swarm               Characters are grouped into swarms and move around the terminal before settling into position.
    synthgrid           Create a grid which fills with characters dissolving into the final text.
    unstable            Spawn characters jumbled, explode them to the edge of the output area, then reassemble them in the correct layout.
    verticalslice       Slices the input in half vertically and slides it into place from opposite directions.
    vhstape             Lines of characters glitch left and right and lose detail like an old VHS tape.
    waves               Waves travel across the terminal leaving behind the characters.
    wipe                Wipes the text across the terminal to reveal characters.

Ex: ls -a | python -m terminaltexteffects --xterm-colors decrypt -a 0.002 --ciphertext-color 00ff00 --plaintext-color ff0000 --final-color 0000ff
```


## Examples
Note: All effects support extensive customization via effect specific arguments. The examples shown below only represent the default settings for a given effect. 

#### Fireworks
![fireworks_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/e3788e25-758b-43e1-827f-42066fb29f91)
<details>
<summary>tte fireworks -h</summary>
<br>
    fireworks | Characters explode like fireworks and fall into place.

    options:
      -h, --help            show this help message and exit
      -a ANIMATION_RATE, --animation-rate ANIMATION_RATE
                            Minimum time, in seconds, between animation steps. This value does not normally need to be modified. Use this to increase the playback speed of all aspects of the effect. This will have
                            no impact beyond a certain lower threshold due to the processing speed of your device. (default: 0.01)
      --explode-anywhere    If set, fireworks explode anywhere in the output area. Otherwise, fireworks explode above highest settled row of text. (default: False)
      --firework-colors [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            Space separated list of colors from which firework colors will be randomly selected. (default: ['88F7E2', '44D492', 'F5EB67', 'FFA15C', 'FA233E'])
      --firework-symbol (single character)
                            Symbol to use for the firework shell. (default: o)
      --firework-volume (float 0 < n <= 1)
                            Percent of total characters in each firework shell. (default: 0.02)
      --final-color (XTerm [0-255] OR RGB Hex [000000-ffffff])
                            Color for the final character. (default: ffffff)
      --launch-delay (int >= 0)
                            Number of animation steps to wait between launching each firework shell. (default: 60)
      --explode-distance (float 0 < n <= 1)
                            Maximum distance from the firework shell origin to the explode waypoint as a percentage of the total output area width. (default: 0.1)

            
    Example: terminaltexteffects fireworks -a 0.01 --firework-colors 88F7E2 44D492 F5EB67 FFA15C FA233E --firework-symbol o --firework-volume 2 --final-color ffffff --launch-delay 60 --explode-distance 10
</details>

#### Rain
![rain_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/ed94a21f-503d-46f3-8510-7a1e83b28314)
<details>
<summary>tte rain -h</summary>
<br>
    rain | Rain characters from the top of the output area.

    options:
      -h, --help            show this help message and exit
      -a ANIMATION_RATE, --animation-rate ANIMATION_RATE
                            Minimum time, in seconds, between animation steps. This value does not normally need to be modified. Use this to increase the playback speed of all aspects of the effect. This will have
                            no impact beyond a certain lower threshold due to the processing speed of your device. (default: 0.01)
      --rain-colors [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            List of colors for the rain drops. Colors are randomly chosen from the list. (default: 0)
      --final-color (XTerm [0-255] OR RGB Hex [000000-ffffff])
                            Color for the final character. (default: ffffff)
      --movement-speed (float > 0)
                            Falling speed of the rain drops. (default: 0.15)
      --easing EASING       Easing function to use for character movement. (default: IN_QUART)

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

            
    Example: terminaltexteffects rain -a 0.01 --rain-colors 39 45 51 21
</details>

#### Decrypt
![decrypt_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/586224f3-6a03-40ae-bdcf-067a6c96cbb5)
<details>
<summary>tte decrypt -h</summary>
<br>
    decrypt | Movie style decryption effect.

    options:
      -h, --help            show this help message and exit
      -a ANIMATION_RATE, --animation-rate ANIMATION_RATE
                            Time to sleep between animation steps. Defaults to 0.003 seconds.
      --ciphertext-color (XTerm [0-255] OR RGB Hex [000000-ffffff])
                            Color for the ciphertext. Defaults to 40
      --plaintext-color (XTerm [0-255] OR RGB Hex [000000-ffffff])
                            Color for the plaintext. Defaults to 208.

    Example: terminaltexteffects decrypt -a 0.003 --cipher-text-color 40 --plain-text-color 208
</details>

#### Spray
![spray_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/d39b4caa-7393-4357-8e27-b0ef9dce756b)
<details>
<summary>tte spray -h</summary>
<br>
    spray | Draws the characters spawning at varying rates from a single point.

    options:
      -h, --help            show this help message and exit
      -a ANIMATION_RATE, --animation-rate ANIMATION_RATE
                            Minimum time, in seconds, between animation steps. This value does not normally need to be modified. Use this to increase the playback speed of all aspects of the effect. This will have
                            no impact beyond a certain lower threshold due to the processing speed of your device. (default: 0.01)
      --spray-colors [(XTerm [0-255] OR RGB Hex [000000-ffffff]) ...]
                            List of colors for the character spray. Colors are randomly chosen from the list. (default: 0)
      --final-color (XTerm [0-255] OR RGB Hex [000000-ffffff])
                            Color for the final character. (default: ffffff)
      --spray-position {n,ne,e,se,s,sw,w,nw,center}
                            Position for the spray origin. (default: e)
      --spray-volume (int > 0)
                            Maximum number of characters to spray at a time. (default: 5)
      --movement-speed (float > 0)
                            Movement speed of the characters. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect. (default: 0.7)
      --easing EASING       Easing function to use for character movement. (default: OUT_EXPO)

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

            
    Example: terminaltexteffects spray -a 0.01 --spray-position center --spray-volume 5 --movement-speed 0.7 --easing OUT_EXPO --spray-colors 10 11 12 --final-color 0
</details>

#### Scattered
![scattered_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/ddcf3c65-a91b-4e42-84fc-0c2508a85be5)
<details>
<summary>tte scattered -h</summary>
<br>
    scattered | Move the characters into place from random starting locations.

    options:
      -h, --help            show this help message and exit
      -a ANIMATION_RATE, --animation-rate ANIMATION_RATE
                            Time between animation steps. (default: 0.01)
      --movement-speed (float > 0)
                            Movement speed of the characters. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect. (default: 0.5)
      --easing EASING       Easing function to use for character movement. (default: IN_OUT_BACK)

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

            
    Example: terminaltexteffects scattered --movement-speed 0.5 --easing IN_OUT_BACK
</details>

#### Expand
![expand_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/9b319e77-d2b7-489e-b59c-c87277ea1285)
<details>
<summary>tte expand -h</summary>
<br>
    expand | Expands the text from a single point.

    options:
      -h, --help            show this help message and exit
      -a ANIMATION_RATE, --animation-rate ANIMATION_RATE
                            Minimum time, in seconds, between animation steps. This value does not normally need to be modified. Use this to increase the playback speed of all aspects of the effect. This will have
                            no impact beyond a certain lower threshold due to the processing speed of your device. (default: 0.01)
      --movement-speed (float > 0)
                            Movement speed of the characters. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect. (default: 0.5)
      --easing EASING       Easing function to use for character movement. (default: IN_OUT_QUART)

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

            
    Example: terminaltexteffects expand -a 0.01 --movement-speed 0.5 --easing IN_OUT_QUART
</details>

#### Burn
![burn_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/ddc8ca36-4157-448b-b10d-573f108361c7)
<details>
<summary>tte burn -h</summary>
<br>
    burn | Burn the output area.

    options:
      -h, --help            show this help message and exit
      -a ANIMATION_RATE, --animation-rate ANIMATION_RATE
                            Time between animation steps. Defaults to 0.03 seconds.
      --burned-color (XTerm [0-255] OR RGB Hex [000000-ffffff])
                            Color faded toward as blocks burn. Defaults to 252525
      --flame-color (XTerm [0-255] OR RGB Hex [000000-ffffff])
                            Color for the flame. Defaults to 0
      --final-color (XTerm [0-255] OR RGB Hex [000000-ffffff])
                            Color for the final character. Will leave as system default if not provided.

    Example: terminaltexteffects burn -a 0.003 --flame-color ff9600 --burned-color 252525
</details>

#### Pour
![pour_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/b67a0f36-a96c-4869-85f2-6850d15f6b71)
<details>
<summary>tte pour -h</summary>
<br>
    pour | Pours the characters into position from the given direction.

    options:
      -h, --help            show this help message and exit
      -a ANIMATION_RATE, --animation-rate ANIMATION_RATE
                            Minimum time, in seconds, between animation steps. This value does not normally need to be modified. Use this to increase the playback speed of all aspects of the effect. This will have
                            no impact beyond a certain lower threshold due to the processing speed of your device. (default: 0.004)
      --pour-direction {up,down,left,right}
                            Direction the text will pour. (default: down)
      --movement-speed (float > 0)
                            Movement speed of the characters. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect. (default: 0.2)
      --easing EASING       Easing function to use for character movement. (default: IN_QUAD)

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

            
    Example: terminaltexteffects pour -a 0.004 --pour-direction down
</details>

#### Randomsequence
![randomsequence_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/db4d04a2-bb9c-42de-8895-0ef1747ae6e8)

#### Verticalslice
![verticalslice_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/237e36c5-cb4e-4866-9a33-b7f27a2907dc)

#### Unstable
![unstable_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/2e4b6e51-2b65-4765-a41c-92542981c77c)

#### Bubbles
![bubbles_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/1ae892fb-0525-4308-8e0b-382e7c079cb2)

#### Bouncyballs
![bouncyballs_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/bb62112c-a6b7-466f-a7c8-ee66f528616b)

#### Middleout
![middleout_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/a69d4164-851e-4668-b2d0-8ee08e2dc5e3)

#### Errorcorrect
![errorcorrect_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/7e63d3f0-6e7f-4145-9886-fd54633896be)

#### Waves
![waves_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/ed057ac5-4cbb-4f8b-a47b-255574614965)

#### Blackhole
![blackhole_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/e8c9a3d5-6160-4cdb-9f3b-dc2d8a6a1a7f)

#### Swarm
![swarm_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/133a3e7d-b493-48c3-ace3-3848c89e6e39)

#### Crumble
![crumble_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/b052ff86-2920-4067-8a47-2713c43257cc)

#### Rings
![rings_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/2d97ba47-bf85-4727-9257-45a5b2a9dddd)

#### VHStape
![vhstape_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/ff11e292-4bfd-4989-ab81-1a624b2c0822)

#### Print
![print_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/ff4fcb44-ebb9-4166-933b-8b0ad3d1810a)

#### BinaryPath
![binarypath_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/f3570ebe-108d-4b34-8766-a448c9ff8f53)

#### Slide
![slide_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/4b862b03-0f97-4e7d-a553-587372e0af27)

#### Wipe
![wipe_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/8d7821c5-0e11-4a5e-a61a-9684fb0ddcd8)

#### SynthGrid
![synthgrid_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/ebd8d3f1-c8b0-4de9-81ad-b70dde5a07b4)


## In-Development Preview
Any effects shown below are in development and will be available in the next release.

#### Beams
![beams_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/2768489f-755e-4460-92f7-bccc8b83a026)

#### Overflow
![overflow_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/83bc225f-926b-4ddd-bbf0-777c601ba244)

## Latest Release Notes

## 0.6.0

### New Features
#### Effects
 * Print. Lines are printed one at a time following a print head. Print head performs line feed, carriage return.
 * BinaryPath. Characters are converted into their binary representation. These binary groups travel to their input coordinate and collapse into the original character symbol.
 * Wipe. Performs directional wipes with an optional trailing gradient.
 * Slide. Slides characters into position from outside the terminal view. Characters can be grouped by column, row, or diagonal. Groups can be merged from opposite directions or slide from the same direction.
 * SynthGrid. Creates a gradient colored grid in which blocks of characters dissolve into the input text.

#### Engine
 * Terminal.get_character() method accepts a Terminal.CharacterSort argument to easily retrieve the input characters in groups sorted by various directions, ex: Terminal.CharacterSort.COLUMN_LEFT_TO_RIGHT
 * Terminal.add_character() method allows adding characters to the effect that are not part of the input text. These characters are added to a separate list (Terminal.non_input_characters) in terminal to allow for iteration over Terminal.characters and adding new characters based on the input characters without modifying the Terminal.characters list during iteration. The added characters are handled the same as input characters by the Terminal.
 * New EventHandler Action, Callback. The Action target can be any callable and will pass the character as the first argument, followed by any additional arguments provided. Uses new EventHandler.Callback type with signature EventHandler.Callback(typing.Callable, *args)
 * graphics.Gradient() objects specified with a single color will create a list of the single color with length *steps*. This enables gradients to be specified via command line arguments while supporting an arbitrary number of colors > 0, without needing to perform any checking in the effect logic. 

### Changes
### Effects
  * Rowslide, Columnslide, and Rowmerge have been replaced with a single effect, Slide.
  * Many classic effects now support gradient specification which includes stops, steps, and frames to enable greater customization.
  * Randomsequence effect supports gradient specification.
  * Scattered effect supports gradient specification.
  * Expand effect supports gradient specification.
  * Pour effect now has a back and forth pouring animation and supports gradient specification.

#### Engine
  * Terminal._update_terminal_state() refactored for improved performance.
  * EffectCharacter.tick() will progress motion and animation by one step. This solves the problem of running Animation.step_animation() before Motion.move() and desyncing Path synced animations.
  * EffectCharacter.is_active has been renamed to EffectCharacter.is_visible. 
  * EffectCharacter.is_active() can be used to check if motion/animation is in progress.
  * graphics.Animation.new_scene(), motion.Motion.new_path(), and Path.new_waypoint() all support automatic IDs. If no ID is provided a unique ID is automatically generated.

### Bug Fixes
 * Fixed rare division by zero error in Path.step() when the final segment has a distance of zero and the distance to travel exceeds
   the total distance of the Path.
 * Fixed effects not respecting --no-color argument.

## License

Distributed under the MIT License. See [LICENSE](https://github.com/ChrisBuilds/terminaltexteffects/blob/main/LICENSE.md) for more information.
