# Change Log

## Unreleased

### New Features
 * Cycle effect. Characters cycle through a list of symbols before landing on the correct symbol.
 * Waves effect. A wave animation is played over the characters. Wave colors and final colors are configurable.
 * Animations support easing functions. Easing functions are applied to Scenes using Scene.ease = easing_function.

### Changes
 * Animation and Motion have been refactored to use direct Scene and Waypoint object references instead of string IDs.
 * base_character.EventHandler uses Scene and Waypoint objects instead of string IDs.
 * graphics.GraphicalEffect renamed to CharacterVisual
 * graphics.Sequence renamed to Frame
 * Animation methods for created Scenes and adding frames to scenes have been refactored to return Scene objects and expose terminal modes, respectively.
 * Easing function api has been simplified. Easing function callables are used directly rather than Enums and function maps.
 * Layer is set on the EffectCharacter object instead of the motion object. The layer is modified through the EventHandler to allow finer control over the layer.

### Bug Fixes
 * Fixed Gradient creating two more steps than specified.

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

## 0.2.1

### New Features
* Added explode distance argument to fireworks effect
* Added random_color function to graphics module
### Changes

### Bug Fixes
* Fixed inactive characters in expand effect.