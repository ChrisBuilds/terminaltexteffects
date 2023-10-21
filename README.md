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

[![PyPI - Version](https://img.shields.io/pypi/v/terminaltexteffects?style=flat&color=green)](http://https://pypi.org/project/terminaltexteffects/ "![PyPI - Version](https://img.shields.io/pypi/v/terminaltexteffects?style=flat&color=green)")  ![PyPI - Python Version](https://img.shields.io/pypi/pyversions/terminaltexteffects) ![License](https://img.shields.io/github/license/ChrisBuilds/terminaltexteffects) 

## Table Of Contents

* [About](#tte)
* [Requirements](#requirements)
* [Installation](#installation)
* [Usage](#usage)
* [Options](#options)
* [Examples](#examples)
* [In-Development Preview](#in-development-preview)
* [Recent Changes](#recent-changes)
* [License](#license)


## TTE
![spray_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/b756b01d-f03e-4f29-b3b3-6856ec1fbf6a)


TerminalTextEffects is a collection of visual effects that run inline in the terminal. The underlying visual effect framework supports the following:
* Xterm 256 color and RBG hex color support                 
* Color gradients                                           
* Runs inline, preserving terminal state and workflow       
* Dynamic character movement with motion easing             
* Dynamic animations with symbol and color changes          
* Effect customization through command line arguments 

## Requirements

TerminalTextEffects is written in Python and does not require any 3rd party modules. Terminal interactions use standard ANSI terminal sequences and should work in most modern terminals.

Note: Windows Terminal performance is slow for some effects.

## Installation


```pip install terminaltexteffects```

## Usage
```cat your_text | tte <effect> [options]```

OR

``` cat your_text | python -m terminaltexteffects <effect> [options]```

* All effects support adjustable animation speed using the ```-a``` option.
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

  {bouncyballs,bubbles,burn,columnslide,decrypt,errorcorrect,expand,fireworks,middleout,pour,rain,randomsequence,rowmerge,rowslide,scattered,spray,unstable,verticalslice}
                        Available Effects
    bouncyballs         Characters are bouncy balls falling from the top of the output area.
    bubbles             Characters are formed into bubbles that float down and pop.
    burn                Burns vertically in the output area.
    columnslide         Slides each column into place from the outside to the middle.
    decrypt             Display a movie style decryption effect.
    errorcorrect        Some characters start in the wrong position and are corrected in sequence.
    expand              Expands the text from a single point.
    fireworks           Characters launch and explode like fireworks and fall into place.
    middleout           Text expands in a single row or column in the middle of the output area then
                        out.
    pour                Pours the characters into position from the given direction.
    rain                Rain characters from the top of the output area.
    randomsequence      Prints the input data in a random sequence.
    rowmerge            Merges rows of characters.
    rowslide            Slides each row into place.
    scattered           Move the characters into place from random starting locations.
    spray               Draws the characters spawning at varying rates from a single point.
    unstable            Spawn characters jumbled, explode them to the edge of the output area, then
                        reassemble them in the correct layout.
    verticalslice       Slices the input in half vertically and slides it into place from opposite
                        directions.

Ex: ls -a | python -m terminaltexteffects --xterm-colors decrypt -a 0.002 --ciphertext-color 00ff00
--plaintext-color ff0000 --final-color 0000ff
```


## Examples
#### Fireworks
![fireworks_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/af5929b0-43e4-4ebd-80ec-32fd0deec7f8)

#### RAIN
![rain_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/ed94a21f-503d-46f3-8510-7a1e83b28314)

#### DECRYPT
![decrypt_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/586224f3-6a03-40ae-bdcf-067a6c96cbb5)

#### SPRAY
![spray_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/d39b4caa-7393-4357-8e27-b0ef9dce756b)

#### SCATTERED
![scattered_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/ddcf3c65-a91b-4e42-84fc-0c2508a85be5)

#### EXPAND
![expand_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/9b319e77-d2b7-489e-b59c-c87277ea1285)

#### BURN
![burn_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/ddc8ca36-4157-448b-b10d-573f108361c7)

#### POUR
![pour_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/d5b827a5-3267-47ad-88c7-6fb0b2dbb478)

#### ROWSLIDE
![rowslide_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/fc62bbe3-d75f-4757-b1ef-c14abff2666b)

#### ROWMERGE
![rowmerge_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/5cd4d5a1-e82d-42ed-b91c-6ac8061cab44)

#### COLUMNSLIDE
![columnslide_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/f2ecdc42-415d-47d3-889d-8e8993657b8f)

#### RANDOMSEQUENCE
![randomsequence_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/8ee83d75-6c22-4c0b-8f96-a12301d7a4eb)

#### VERTICALSLICE
![verticalslice_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/237e36c5-cb4e-4866-9a33-b7f27a2907dc)

#### Unstable
![unstable_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/2e4b6e51-2b65-4765-a41c-92542981c77c)

#### Bubbles
![bubbles_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/e12a6f2a-a8f8-47d8-8d42-8cff621db24e)

#### Bouncyballs
![bouncyballs_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/bb62112c-a6b7-466f-a7c8-ee66f528616b)

#### Middleout
![middleout_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/a69d4164-851e-4668-b2d0-8ee08e2dc5e3)

#### Errorcorrect
![errorcorrect_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/7e63d3f0-6e7f-4145-9886-fd54633896be)

## In-Development Preview
Any effects shown below are in development and will be available in the next release.

#### Cycle
![cycle_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/cc067825-b024-44f1-b448-cc87753cab4b)


## Recent Changes

## 0.3.1

### New Features
* Bouncyballs effect. Balls drop from the top of the output area and bounce before
  settling into position. A gradient is used to transition to the final color after the
  ball has landed. Random colors are used for balls unless specified.

* Unstable effect. Spawn characters jumbled, explode to the edge of the output area, 
  then reassemble them in the correct layout.

* Bubble effect. Characters are formed into bubbles and fall down the screen before popping.

* Middleout effect. Characters start as a single character in the center of the output area. A row or column
  is expanded in the center of the screen, then the entire output is expanded from this row/column. Expansion
  from row/column is determined by the --expand-direction argument.

* Errorcorrect effect. Some characters spawn with their location swapped with another character. The characters
  then move, in pairs, to their correct location following an animation.

* --no-wrap argument prevents line wrapping.

* --tab-width argument can be used to specify the number of spaces used in place of tab characters. Defaults to 4.

* New Events for WaypointActivated and SceneActivated.

* New Event Actions for DeactivateWaypoint and DeactivateScene.

* Scenes can be synced to Waypoint progress. The scene will progress in-line with the character's steps towards
  the waypoint.

* Waypoints now have a layer attribute. Characters are drawin in ascending layer order. While a character has 
  a waypoint active, that waypoint's layer is used. Otherwise, the character is drawn in layer 0.

### Changes
* Added Easing Functions help output for fireworks effect.
* Updated spray effect help output.
* Removed shootingstar effect. It was not particularly interesting.
* Coord type is now hashable and frozen.
* Waypoints are hashable. Can be compared for equality based on row, col pair.
* Scenes can be compared for equality based on id.
* Terminal maintains an input_coord tuple[row, col] -> EffectCharacter map called character_by_input_coord.
* The terminal cursor is now hidden during the effect.
* The find_points_on_circle method in the motion module is now a static method.
* Terminal.OutputArea has center_row and center_column attributes.
* Added layers to effects.

### Bug Fixes
* Fixed animating_chars filter in effect_template to properly remove completed characters.
* Initial symbol assignment when activating a scene no longer increases played_frames count.
* Waypoints and Animations completed are deactivated to prevent repeated event triggering.
* Fixed step_animation in graphics module handling of looping animations. It will no longer deactivate the animation.

## License

Distributed under the MIT License. See [LICENSE](https://github.com/ChrisBuilds/terminaltexteffects/blob/main/LICENSE.md) for more information.
