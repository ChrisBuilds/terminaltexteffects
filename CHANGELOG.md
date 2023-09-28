# Change Log

## Unreleased

### New Features
* Bouncyballs effect. Balls drop from the top of the output area and bounce before
  settling into position. A gradient is used to transition to the final color after the
  ball has landed. Random colors are used for balls unless specified.

* Unstable effect. Spawn characters jumbled, explode them to the edge of the output area, 
  then reassemble them in the correct layout.
### Changes
* Added Easing Functions help output to fireworks effect epilog.
* Updated spray effect help output.
* Removed shootingstar effect. It was not particularly interesting.

### Bug Fixes
* Fixed animating_chars filter in effect_template to properly remove completed characters.

## 0.2.1

### New Features
* Added explode distance argument to fireworks effect
* Added random_color function to graphics module
### Changes

### Bug Fixes
* Fixed inactive characters in expand effect.