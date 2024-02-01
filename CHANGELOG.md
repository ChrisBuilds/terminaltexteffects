# Change Log

## Unreleased

### New Features
#### Effects
 * Print. Lines are printed one at a time following a print head. Print head performs line feed, carriage return.
 * BinaryPath. Characters are converted into their binary representation. These binary groups travel to their input coordinate and collapse into the original character symbol.
 * Wipe. Performs directional wipes with an optional trailing gradient.
 * Slide. Slides characters into position from outside the terminal view. Characters can be grouped by column, row, or diagonal. Groups can be merged from opposite directions or slide from the same direction.

#### Engine
 * Terminal.get_character() method accepts a Terminal.CharacterSort argument to easily retrieve the input characters in groups sorted by various directions, ex: Terminal.CharacterSort.COLUMN_LEFT_TO_RIGHT
 * Terminal.add_character() method allows adding characters to the effect that are not part of the input text. These characters are added to a separate list (Terminal.non_input_characters) in terminal to allow for iteration over Terminal.characters and adding new characters based on the input characters without modifying the Terminal.characters list during iteration. The added characters are handled the same as input characters by the Terminal.

### Changes
  * Terminal._update_terminal_state() refactored for improved performance.
  * rowslide, columnslide, and rowmerge have been replaced with a single effect, slide.
### Bug Fixes
 * Fixed rare division by zero error in Path.step() when the final segment has a distance of zero and the distance to travel exceeds
   the total distance of the Path.
 * Fixed effects not respecting --no-color argument.
## 0.5.0

### New Features
 * New effect, Vhstape. Lines of characters glitch left and right and lose detail like an old VHS tape.
 * New effect, Crumble. Characters lose color and fall as dust before being vacuumed up and rebuilt.
 * New effect, Rings. Characters are dispersed throughout the output area and form into spinning rings.
 * motion.Motion.chain_paths(list[Paths]) will automatically register Paths with the EventHandler to create
   a chain of paths. Looping is supported.
 * motion.Motion.find_coords_in_rect() will return a random selection of coordinates within a rectangular area. This is faster than using
   find_coords_in_circle() and should be used when the shape of the search area isn't important.
 * Terminal.OutputArea.coord_in_output_area() can be used to determine if a Coord is in the output area.
 * Paths have replaced Waypoints as the motion target specification object. Paths group Waypoints together and allow for easing
   motion and animations across an arbitrary number of Waypoints. Single Waypoint Paths are supported and function the same as
   Waypoints did previously. Paths can be looped with the loop argument. 
 * Quadratic and Cubic bezier curves are supported. Control points are specified in the Waypoint object signature. When a control point
   is specified, motion will be curved from the prior Waypoint to the Waypoint with the control point, using the control point
   to determine the curve. Curves are supported within Paths.
 * New EventHandler.Event PATH_HOLDING is triggered when a Path enters the holding state.
 * New EventHandler.Action SET_CHARACTER_ACTIVATION_STATE can be used to modify the character activation state based on events.
 * New EventHandler.Action SET_COORDINATE can be used to set the character's current_coordinate attribute.
 * Paths have a layer attribute that can be used to automatically adjust the character's layer when the Path is activated.
   Has no effect when Path.layer is None, defaults to None.
 * New EventHandler.Events SEGMENT_ENTERED and SEGMENT_EXITED. These events are triggered when a character enters or exits a segment
   in a Path. The segment is specified using the end Waypoint of the segment. These events will only be called one time for each run
   through the Path. Looping Paths will reset these events to be called again. 


### Changes
 * graphics.Animation.random_color() is now a static method.
 * motion.Motion.find_coords_in_circle() now generates 7*radius coords in each inner-circle.
 * BlackholeEffect uses chain_paths() and benefits from better circle support for a much improved blackhole animation.
 * BlackholeEffect singularity Paths are curved towards center lines.
 * EventHandler.Event.WAYPOINT_REACHED removed and split into two events, PATH_HOLDING and PATH_COMPLETE.
 * EventHandler.Event.PATH_COMPLETE is triggered when the final Path Waypoint is reached AND holding time reaches 0.
 * Fireworks effect uses Paths and curves to create a more realistic firework explosion.
 * Crumble effect uses control points to create a curved vacuuming phase.
 * graphics.Gradient accepts an arbitrary number of color stops. The number of steps applies between each color stop.
 * motion.find_coords_in_circle() and motion.find_coords_in_rect() no longer take a num_points argument. All points in the area are returned.

### Bug Fixes
 * Fixed looping animations when synced to Path not resetting properly.


## 0.4.3

### Changes
 * blackhole radius is based on the output area size, not the input text size.

## 0.4.2

### Changes
 * motion.Motion.find_points_on_circle and motion.Motion.find_points_in_circle now account for the terminal character height/width ratio to
   return points that more closely approximate a circle. All effects which use these functions have been updated to account for this change.

## 0.4.1

### Changes
 * Updated documentation

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