# Change Log

## Unreleased

### New Features
* Bouncyballs effect. Balls drop from the top of the output area and bounce before
  settling into position. A gradient is used to transition to the final color after the
  ball has landed. Random colors are used for balls unless specified.

* Unstable effect. Spawn characters jumbled, explode them to the edge of the output area, 
  then reassemble them in the correct layout.

* --no-wrap argument prevents line wrapping.

* --tab-width argument can be used to specify the number of spaces used in place of tab characters.
### Changes
* Added Easing Functions help output for fireworks effect.
* Updated spray effect help output.
* Removed shootingstar effect. It was not particularly interesting.
* Coord type is now hashable and frozen.
* Waypoints are hashable. Can be compared for equality based on row, col pair.
* Scenes can be compared for equality based on id.
* Terminal maintains an input_coord tuple[row, col] -> EffectCharacter map called character_by_input_coord.
* The terminal cursor is now hidden during the effect.

### Bug Fixes
* Fixed animating_chars filter in effect_template to properly remove completed characters.

## 0.2.1

### New Features
* Added explode distance argument to fireworks effect
* Added random_color function to graphics module
### Changes

### Bug Fixes
* Fixed inactive characters in expand effect.