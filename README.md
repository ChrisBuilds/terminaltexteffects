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
![unstable_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/2e4b6e51-2b65-4765-a41c-92542981c77c)


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

  {blackhole,bouncyballs,bubbles,burn,columnslide,decrypt,errorcorrect,expand,fireworks,middleout,pour,rain,randomsequence,rowmerge,rowslide,scattered,spray,swarm,test,unstable,verticalslice,waves}
                        Available Effects
    blackhole           Characters are consumed by a black hole and explode outwards.
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
    swarm               Characters are grouped into swarms and move around the terminal before settling
                        into position.
    test                effect_description
    unstable            Spawn characters jumbled, explode them to the edge of the output area, then
                        reassemble them in the correct layout.
    verticalslice       Slices the input in half vertically and slides it into place from opposite
                        directions.
    waves               Waves travel across the terminal leaving behind the characters.

Ex: ls -a | python -m terminaltexteffects --xterm-colors decrypt -a 0.002 --ciphertext-color 00ff00
--plaintext-color ff0000 --final-color 0000ff
```


## Examples
#### Fireworks
![fireworks_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/af5929b0-43e4-4ebd-80ec-32fd0deec7f8)

#### Rain
![rain_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/ed94a21f-503d-46f3-8510-7a1e83b28314)

#### Decrypt
![decrypt_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/586224f3-6a03-40ae-bdcf-067a6c96cbb5)

#### Spray
![spray_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/d39b4caa-7393-4357-8e27-b0ef9dce756b)

#### Scattered
![scattered_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/ddcf3c65-a91b-4e42-84fc-0c2508a85be5)

#### Expand
![expand_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/9b319e77-d2b7-489e-b59c-c87277ea1285)

#### Burn
![burn_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/ddc8ca36-4157-448b-b10d-573f108361c7)

#### Pour
![pour_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/d5b827a5-3267-47ad-88c7-6fb0b2dbb478)

#### Rowslide
![rowslide_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/fc62bbe3-d75f-4757-b1ef-c14abff2666b)

#### Rowmerge
![rowmerge_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/5cd4d5a1-e82d-42ed-b91c-6ac8061cab44)

#### Columnslide
![columnslide_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/f2ecdc42-415d-47d3-889d-8e8993657b8f)

#### Randomsequence
![randomsequence_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/8ee83d75-6c22-4c0b-8f96-a12301d7a4eb)

#### Verticalslice
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

#### Waves
![waves_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/ed057ac5-4cbb-4f8b-a47b-255574614965)

#### Blackhole
![blackhole_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/18d2a13d-09d1-4c3b-9ad0-f937b2b52d6d)

#### Swarm
![swarm_demo](https://github.com/ChrisBuilds/terminaltexteffects/assets/57874186/133a3e7d-b493-48c3-ace3-3848c89e6e39)


## In-Development Preview
Any effects shown below are in development and will be available in the next release.


## Recent Changes

## 0.4.0

### New Features
 * Waves effect. A wave animation is played over the characters. Wave colors and final colors are configurable.
 * Blackhole effect. Characters spawn scattered as a field of stars. A blackhole forms and consumes the stars then explodes the characters across
   the screen. Characters then 'cool' and ease into position.
 * Swarm effect. Characters a separated into swarms and fly around the output area before landing in position.
 * Animations support easing functions. Easing functions are applied to Scenes using Scene.ease = easing_function.
 * OutputArea has a center attribute that is the center Coord of the output area.
 * Terminal has a random_coord() method which returns a random coordinate. Can specify outside the output area.

### Changes
 * Animation and Motion have been refactored to use direct Scene and Waypoint object references instead of string IDs.
 * base_character.EventHandler uses Scene and Waypoint objects instead of string IDs.
 * graphics.GraphicalEffect renamed to CharacterVisual
 * graphics.Sequence renamed to Frame
 * Animation methods for created Scenes and adding frames to scenes have been refactored to return Scene objects and expose terminal modes, respectively.
 * Easing function api has been simplified. Easing function callables are used directly rather than Enums and function maps.
 * Layer is set on the EffectCharacter object instead of the motion object. The layer is modified through the EventHandler to allow finer control over the layer.
 * Animations not longer sync to specific waypoints, rather, they sync to the progress of the character towards the active waypoint.
 * Animations synced to waypoint progress can now sync to either the distance progression or the step progression.
 * Motion methods which utilize coordinates now use Coord objects rather than tuples.
 * Motion has methods for finding coordinates on a circle and in a circle.

### Bug Fixes
 * Fixed Gradient creating two more steps than specified.
 * Fixed waypoint synced animation index out of range error.

## License

Distributed under the MIT License. See [LICENSE](https://github.com/ChrisBuilds/terminaltexteffects/blob/main/LICENSE.md) for more information.
