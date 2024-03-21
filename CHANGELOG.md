# Change Log

## Unreleased

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
 * character.animation.set_appearance(symbol, color) will set the character symbol in color directly. If a Scene is active, the appearance will be overwritten with the Scene frame on the next call to step_animation(). This method is intended for the occasion where a full scene isn't needed, or the appearance needs to be set based on conditions not compatible with Scenes or the EventHandler. For example, setting the color based on the terminal row. 
 * Terminal.CharacterSort enums moved to Terminal.CharacterGroup, Terminal.CharacterSort is now used for sorting and return a flat list of characters.
 * Terminal.CharacterSort has new sort methods, TOP_TO_BOTTOM_LEFT_TO_RIGHT, TOP_TO_BOTTOM_RIGHT_TO_LEFT, BOTTOM_TO_TOP_LEFT_TO_RIGHT, BOTTOM_TO_TOP_RIGHT_TO_LEFT, OUTSIDE_ROW_TO_MIDDLE, MIDDLE_ROW_TO_OUTSIDE
 * New Terminal.CharacterGroup options, CENTER_TO_OUTSIDE_DIAMONDS and OUTSIDE_TO_CENTER_DIAMONS
 * graphics.Animation.adjust_color_brightness(color: str, brightness: float) will convert the color to HSL, adjust the brightness to the given level, and return 
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
 * Decrypt effect supports gradient specification for ciphertext and plaintext
 * Beams effect uses Animation.adjust_color_brightness() to lower the background character brightness and shows the lighter color when the beam passes by.
 * Crumble effect uses Animation.adjust_color_brightness() to set the weak and dust colors based on the final gradient.
 * Fireworks effect launch_delay argument has a +/- 0-50% randomness applied. 
 * Bubbles effect --no-rainbow changed to --rainbow and default set to False.
 * Bubbles effect --bubble-color changed to --bubble-colors. Bubble color is randomly chosen from the colors unless --rainbow is used.
 * Burn effect burns faster with some randomness in speed.
 * Burn effect final color fades in from the burned color.

#### Engine
 * Geometry related methods have been removed from the motion class. They are now located at terminaltexteffects.utils.geometry as separate functions.
 * The Coord() object definition has been moved from the motion module to the geometry module.
 * Terminal.add_character() takes a geometry.Coord() argument to set the character's input_coordinate.
 * EffectCharacters have a unique ID set by the Terminal on instatiation. As a result, all EffectCharacters should be created using Terminal.add_character().
 * EffectCharacters added by the effect are stored in Terminal._added_characters.
 * Retrieving EffectCharacters from the terminal should no longer be done via accessing the lists of characters [_added_characters, _fill_characters, _input_characters], but should be retrieved via Terminal.get_characters() and Terminal.get_characters_sorted(). 
 * Setting EffectCharacter visibility is now done via Terminal.set_character_visibility(). This enables the terminal to keep track of all visible characters without needing to iterate over all characters on every call to _update_terminal_state().
 * EventHandler.Action.SET_CHARACTER_VISIBILITY_STATE has been removed as visibilty state is handled by the Terminal. To enable visibility state changes through the event system, us a CALLBACK action with target EventHandler.Callback(terminal.set_character_visibility, True/False).
 * geometry.find_points_on_circle() num_points arg renamed to points_limit and new arg unique: bool, added to remove any duplicate Coords.
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