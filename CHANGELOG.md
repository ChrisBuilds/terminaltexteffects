# Change Log

---

## 0.14.2

---

### Bug Fixes (0.14.2)

* Removed mistakenly added in-development effect.

## 0.14.1

---

### Bug Fixes (0.14.1)

* Removed duplicate keyword arg `action` in `effect_template` `ArgSpec`.


## 0.14.0

---

### New Features (0.14.0)

---

#### New Application Features (0.14.0)

* `random_effect` is now specified as `--random-effect` and supports `--include-effects` or `--exclude-effects` for limiting which effects are available.

#### Application Changes (0.14.0)

* `--version` switch now pull the package version from the package metadata instead of the package `__init__.py`

---

### Changes (0.14.0)

---

#### Engine Changes (0.14.0)

* Added `EasingTracker`, a reusable helper that tracks eased progress, deltas, and completion state for any easing function.
* Replaced `eased_step_function` closure with the new `SequenceEaser`, enabling eased iteration over arbitrary sequences while reporting added, removed, and total elements for each step.
* Renamed `CharacterGroup` center related groupings to `CENTER_TO_OUTSIDE` / `OUTSIDE_TO_CENTER`.
* `CharacterGroup`, `CharacterSort`, and `ColorSort` themselves were relocated from the `Terminal` module into `terminaltexteffects.utils.argutils`, and the terminal now imports them from there so both the CLI and the engine share a single definition of the enums.
* `terminaltexteffects.utils.argutils` introduces dedicated argument-type helpers for `CharacterGroup`, `CharacterSort`, and `ColorSort`.
* `Canvas` now exposes a `text_center` `Coord` computed from `text_center_row`/`text_center_column`, eliminating redundant per-call calculations when effects or sort helpers need the true center of the anchored text.
* Center-to-outside/Outside-to-center `CharacterGroup` calculations within `Terminal` now measure distance from the text center instead of the canvas center, so middle-out and outside-in sorts stay aligned with the rendered text even when it is offset on the canvas.

#### Effects Changes (0.14.0)

* Highlight - Simplified effect logic by offloading to `SequenceEaser`.
* Sweep - Simplified effect logic by offloading to `SequenceEaser`.
* Wipe - Simplified effect logic by offloading to `SequenceEaser`. 
* Wipe - Changed default `--wipe-ease` to `IN_OUT_CIRC`.
* Wipe - Removed `--wipe-ease-stepsize` CLI arg.
* Colorshift - `--travel` renamed `--no-travel`. The default behavior is to travel radially.
* Colorshift - Default `--travel-direction` changed from horizontal to radial.

---

### Bug Fixes (0.14.0)

---

#### Effect Fixes (0.14.0)

* Sweep - Fixed bug when second sweep direction is a grouping of a different length from the first direction. 
* Removed mistakenly added effect dev_worm.

#### Application Fixes (0.14.0)

* CLI now exits with a non-zero status when input files are missing, no input is provided, or no effect is specified.
* CLI detects duplicate effect command registrations.


## 0.13.0

---

### New Features (0.13.0)

---

#### New Effects (0.13.0)

* Thunderstorm - Rain falls across the canvas. Lightning strikes randomly around the canvas. Lightning flashes after reaching the bottom of the canvas, lighting up the text characters. Sparks explode from lightning impact. Text characters glow when lightning travels through them.
* Smoke - Smoke floods the canvas, colorizing any text it passes over.
---

#### New Engine Features (0.13.0)

* Added `geometry.find_coords_on_rect()`, which returns coordinates along the perimeter of a rectangle given a center `Coord`, width, and height. Results are cached for performance.
* Added `--terminal-background-color` to the `TerminalConfig` parser. This will enable terminal themes with background other than black to better display effects with fade in/out components.
* Spanning-tree and search algorithms have been added.
  * PrimsSimple - Unweighted Prims
  * PrimsWeighted
  * RecursiveBacktracker
  * Breadthfirst
* `EffectCharacter` has a new attribute `links` to support creating trees using spanning-tree algorithms.
---

#### New Application Features (0.13.0)

* Support for random effect selection from the command-line. Use effect named `random_effect`. Global configuration options will apply.
* Support for canvas re-use. Use tte option `--reuse-canvas` to restore the cursor to the position of the prior effect canvas.
* Added `terminaltexteffects` entry point.
* `--no-eol` command-line option. Suppress the trailing newline character after an effect.
* `--no-restore-cursor` command-line option. Do not restore cursor visibility after an effect ends.
---

### Changes (0.13.0)

---

#### Effects Changes (0.13.0)

* Blackhole - Initial consumption motion modified to create the apperance of an gravitational-wave propagating across the canvas.
* Laseretch - New etch-pattern `algorithm` uses the link-order of a text-boundary-bound recursive backtracker algorithm.
* Burn - Character ignite order is based on the link-order of a text-boundary-bound prims simple algorithm.
* Pour - Changed `--movement-speed` to `--movement-speed-range` to add some variation in character falling speed.
* All effects have been adjusted for visual parity at 60 fps.
* All effects are up-imported into `terminaltexteffects.effects` to simplify importing to `from terminaltexteffects.effects import Burn`.

---

#### Engine Changes (0.13.0)

* `animation.set_appearance()` `symbol` argument signature changed from `str` to `str | None`, defaulting to the character's `input_symbol` if not provided.
* `Coord` objects can be unpacked into `(column, row)` tuples for multiple assignment.
* `motion.activate_path()` and `animation.activate_scene()` accept `path_id`/`scene_id` strings OR `Path`/`Scene` instances. The `Path`/`Scene` corresponding to the provided `path_id`/`scene_id` must exist or  a `SceneNotFoundError`/`PathNotFoundError` will be raised.
* `motion.query_path()` accepts an argument directing the action to take if a path with the given `path_id` cannot be found. The default action is to raise a `PathNotFoundError`, but this behavior can be changed to return `None`.
* `animation.query_scene()` accepts an argument directing the action to take if a scene with the given `scene_id` cannot be found. The default action is to raise a `SceneNotFoundError`, but this behavior can be changed to return `None`.
* Events can be registered using `path_id`/`scene_id` in place of the `Path`/`Scene` for `target` and `caller` arguments.
* Frame rate reduced from 100 fps to 60 fps.
* Typed argument parsing and related configuration utilities and classes have been rewritten.
* Terminal distance calculations take into account the cell height/width ratio.
* Completely rewrote modules and classes related to argument parsing and effect/terminal configuration handling. This eliminates the design which forced building multiple configuration objects depending on how the effect was run, and also enabled the random effect option.

### Bug Fixes (0.13.0)

---

#### Engine Fixes (0.13.0)

* Fixed duplicate event registrations by adding prevention logic to the EventHandler. The `register_event` method now raises a `DuplicateEventRegistrationError` when attempting to register the same event-caller-action-target combination.
* Improved the `_handle_event` method docstring with comprehensive documentation.
* `Scene.reset_scene()` now sets `easing_current_step` to `0`.

---

#### Effect Fixes (0.13.0)

* Unstable - Effect properly uses config values for reassembly/explosion speed. These were not referenced previously.

---

## 0.12.2

---

### New Features (0.12.2)

---

#### New Engine Features (0.12.2)

* `--no-eol` option prevents the newline from printing after an effect has ended.

---

## 0.12.1

---

### Bug Fixes (0.12.1)

---

* Fixed bug in ArgField caused by Field init signature change in Python 3.14. This class and parent module will be removed in 0.13.0.

## 0.12.0

---

### New Features (0.12.0)

---

#### New Effects (0.12.0)

* Highlight - Run a specular highlight across the text. Highlight direction, brightness, and width can be specified.
* Laseretch - A laser travels across the terminal, etching characters and emitting sparks.
* Sweep - Sweep across the canvas to reveal uncolored text, reverse sweep to color the text.

#### New Engine Features (0.12.0)

* Background color specification is supported throughout the engine. Methods which accept Color arguments expect a
`ColorPair` object to specify both the foreground and background color.
* New `EventHandler.Action`: `Action.RESET_APPEARANCE` will reset the character appearance to the input character with
no modifications. This eliminates the need to make a `Scene` for this purpose.
* Existing 8/24 bit color sequences in the input data are parsed and handled by the engine. A new `TerminalConfig`
option `--existing-color-handling` is used to control how these sequences are handled.
* `easing.eased_step_function()` allows easing functions to be used generically by returning a closure that produces an
eased value based on the easing function and step size provided when called.
* A new easing function has been added which returns a custom easing fuction based on cubic bezier controls.
* Added custom exceptions.

### Changes (0.12.0)

---

#### Effects Changes (0.12.0)

* Spotlights - The maximum size of the beam is limited to the smaller of the two canvas dimensions and the minimum size
is limited to 1.
* Spray - Argument spray_volume is limited to 0 < n <= 1.
* Colorshift - `--loop` has been renamed `--no-loop`. Looping the gradient is now default.
* All effects which apply a gradient across the text build the gradient mapping based on the text dimensions regardless
of the canvas size. This fixes truncated gradients where parts of the gradient map were assigned to empty coordinates.
* Some effects support dynamic handling of color sequences in the input data.
* Blackhole - Star characters changed to ASCII only to improve supported fonts.

#### Engine Changes (0.12.0)

* Frame rate timing is enforced within the `BaseEffectIterator` when accessing the `frame` property, rather than within the
`Terminal` on calls to `print()`. This enables frame timing when iterating without requiring the use of the `terminal_output()` context manager.
* The frame rate can be set to `0` to run without a limit.
* Removed unused method Segment.get_coord_on_segment().
* Activating a Path with no segments will raise a ValueError.
* `base_effect.active_characters` was refactored from a list to a set.
* Bezier curves are no longer limited to two control points. Any number of control points can be specified in calls to
`Path.new_waypoint()`, however, performance may suffer with large numbers of control points along unique paths.
* Caching has been implemented for all geometry functions significantly improving performance in cases where many
characters are traveling along the same Path.
* Reorganized the most common API class imports up to the package level.
* Moved the SyncMetric Enum from the Animation module top level into the Scene class.
* `Scene.apply_gradient_symbols()` accepts two gradients, one for the foreground and one for the background.

### Bug Fixes (0.12.0)

---

#### Effects Fixes (0.12.0)

* VHSTape - Fixed glitch wave lines not appearing for some canvas/input_text size ratios.
* Fireworks - Fixed launch_delay set to 0 causing an infinite loop.
* Spotlights - Fixed infinite loop caused by very small beam_width_ratio values.
* Overflow - Fixed effect ignoring `--final-gradient-direction` argument.

#### Engine Fixes (0.12.0)

* Fixed Color() objects not treating rgb colors initialized with/without the hash as equal. Ex: Color('#ffffff') and Color('ffffff')
* Gradients initialized with a tuple of steps including the value 0 will raise a ValueError as expected. Ex: Gradient(Color('ff0000'), Color('00ff00'), Color('0000ff'), steps=(4,0))
* Fixed infinite loop when a new scene is created without an id and a scene has been deleted resuling in the length of the scenes dict corresponding to an existing scene id.
* Fixed `Canvas` center calculations being off by one for odd widths/heights due to floor division.
* Fixed `Gradient.get_color_at_fraction` rounding resulting in over-representing colors in the middle of the spectrum.
* `Gradient.build_coordinate_color_mapping` signature changed to required full bounding box specification. This allows the effect to selectively build based on the text/canvas/terminal dimensions and reduces build time by by reducing the map size when possible.
* Adds a call to `ansitools.dec_save_cursor_position` after each call to `ansitools.dec_restore_cursor_position` to address some terminals clearing the saved data after the restore.

#### Other (0.12.0)

* Fixed Canvas width/height docstrings and help output to correctly indicate 0/-1 matching terminal device/input text.

---

## 0.11.0

---

### New Features (0.11.0)

---

#### New Effects (0.11.0)

* Matrix effect. Matrix digital rain effect with that ends with a final curtain and character resolve phase.

#### New Engine Features (0.11.0)

* Canvas is now arbitrarily sizeable. (`-1` matches the input text dimension, `0` matches the terminal dimension)
* Canvas can be anchored around the terminal.
* Text can be anchored around the Canvas.
* Canvas new attributes `text_[left/right/top/bottom]` and `text_width/height` and `text_center_row/center_column`.
* Version switch (--version, -v)

### Changes (0.11.0)

---

#### Effects Changes (0.11.0)

* Slice effect calculates the center of the text absolutely rather than by average line length.
* Print effect no longer moves the print head to the start of each line, only back to the first character on the next line.
* Many effects were updated to support anchoring within the Canvas.

#### Engine Changes (0.11.0)

* Performance improvements to geometry functions related to circles. (10.0.1)
* Gradient's support indexing and slicing.
* EffectCharacter objects no longer have a `symbol` attribute. Instead, the `Animation` class has a new attribute
`current_character_visual` which provides access to a `symbol` and `color` attribute reflecting the character's current
symbol and color. The prior `EffectCharacter.symbol` attribute was unreliable and represented both a formatted and
unformatted symbol depending on when it was accessed. In addition, the `color` attribute is now a `Color` object and the
color code has been moved into the `_color_code` attribute.
* EffectCharacter objects have a new attribute `is_fill_character: bool`.

---

#### Effects Fixes (0.11.0)

* Fixed swarm effect not handling the first swarm (bottom right characters) resulting in missing characters in the
output. (10.0.1)

#### Other (0.11.0)

* Keyboard Interrupts are handled gracefully while effects are animating.

---

## 0.10.1

---

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

## 0.9.3

---

### New Features (0.9.3)

---

#### New Engine Features (0.9.3)

* Added argument to the `BaseEffect.terminal_output()` context manager. `end_symbol` (default `\n`) is used to specify
the symbol that will be printed after the effect completes. Set to `''` or `' '` to enable animated prompts.

### Changes (0.9.3)

---

#### Engine Changes (0.9.3)

* Removed unnecessary write calls for cursor positioning on every frame.
* Separated functionality related to cursor positioning and frame timing out of `Terminal.print()` and into
`Terminal.enforce_framerate()`, `Terminal.prep_canvas()` and `Terminal.move_cursor_to_top()`.

### Bug Fixes (0.9.3)

---

#### Engine Fixes (0.9.3)

* Fixed the canvas of an effect being 1 row less than specified via the `Terminal.terminal_height` attribute. This
  was caused by mixing use of `print()` and `sys.stdout.write()`.

---

## 0.9.1

---

### New Features (0.9.1)

---

#### New Engine Features (0.9.1)

* Terminal dimension auto-detection supports automatically detecting a single dimensions.

### Changes (0.9.1)

---

#### Effects Changes (0.9.1)

* All effects have been updated to use the new `update()` method and `frame` property of
  `base_effect.BaseEffectIterator`. See Engine Changes for more info.

#### Engine Changes (0.9.1)

* `base_effect.BaseEffectIterator` now has an `update()` method which calls the `tick()` method of all active characters
  and manages the `active_characters` list.
* `base_effect.BaseEffectIterator` has a `frame` property which calls `Terminal.get_formatted_output_string()` and
  returns the string.
* `TerminalConfig.terminal_dimensions` has been split into `TerminalConfig.terminal_width` and
  `TerminalConfig.terminal_height` to simplify the command line argument for dimensions and make it more obvious which
  dimension is being specified when interacting with `effect.terminal_config`.

#### Other Changes (0.9.1)

### Bug Fixes (0.9.1)

---

#### Engine Fixes (0.9.1)

* Fixed division by zero error when the terminal height was set to 1.

## 0.9.0

---

### New Features (0.9.0)

---

#### New Engine Features (0.9.0)

* Linear easing function added.

### Changes (0.9.0)

---

#### Other Changes (0.9.0)

* Major re-organization of the codebase and significant documentation changes and additions.

## 0.8.0

---

### New Features (0.8.0)

---

#### New Engine Features (0.8.0)

* Library support: TTE effects are now importable. All effects are iterators that return strings for each frame of the output. See README for more information.
* Terminal: New terminal argument (--terminal-dimensions) allows specification of the terminal dimensions without relying on auto-detection. Especially useful in cases where TTE is being used as a library in non-terminal or TUI contexts.
* Terminal: New terminal argument (--ignore-terminal-dimensions) causes the canvas dimensions to match the input data dimensions without regard to the terminal.

### Changes (0.8.0)

---

#### Effects Changes (0.8.0)

* Scattered. Holds scrambled text at the start for a few frames.
* Scattered. Lowered default movement-speed from 0.5 to 0.3.

#### Engine Changes (0.8.0)

* graphics.Gradient ```__iter___()``` refactored to return a generator. No longer improperly implements the iterator protocol by resetting index in ```___iter__()```.
* Terminal: Argument --animation-rate is now --frame-rate and is specified as a target frames per second.
* Terminal: Argument --no-wrap is now --wrap-text and defaults to False.
* Terminal: If a terminal object is instantiated without a TerminalConfig passed, it will instantiate a new TerminalConfig.
* Terminal: Terminal.get_formatted_output_string() will return a string representing the current frame.
* Terminal: Terminal.print() will print the frame to the terminal and handle cursor position. The optional argument (enforce_frame_rate: bool = True) determines if the frame rate set at Terminal.config.frame_rate is enforced. If set to False, the print will occur without delay.
* New argument validator for terminal dimensions (argvalidators.TerminalDeminsions).
* New module base_effect.py:
* base_effect.BaseEffect:
  * This is an abstract class which forms the base iterable for all effects and provides the terminal_output() context manager.
* base_effect.BaseEffectIterator:
  * This is an abstract class which provides the functionality to enable iteration over effects.

### Bug Fixes (0.8.0)

---

#### Engine Fixes (0.8.0)

* Fixed Argfield nargs type from str to str | int.
* Implemented custom formatter into argsdataclass.py argument parsing.

## 0.7.0

---

### New Features

#### New Effects (0.7.0)

* Beams. Light beams travel across the canvas and illuminate the characters behind them.
* Overflow. The input text is scrambled by row and repeated randomly, scrolling up the terminal, before eventually displaying in the correct order.
* OrbitingVolley. Characters fire from launcher which orbit canvas.
* Spotlights. Spotlights search the text area, illuminating characters, before converging in the center and expanding.

#### New Engine Features (0.7.0)

* Gradients now support multiple step specification to control the distance between each stop pair. For example:
  graphics.Gradient(RED, BLUE, YELLOW, steps=(2,5)) results in a spectrum of RED -> (1 step) -> BLUE -> (4 steps) -> YELLOW
* graphics.Gradient.get_color_at_fraction(fraction: float) will return a color at the given fraction of the spectrum when provided a float between 0 and 1, inclusive. This can be used to match the color to a ratio/ For example, the character height in the terminal.
* graphics.Gradient.build_coordinate_color_mapping() will map gradient colors to coordinates in the terminal and supports a Gradient.Direction argument to enable gradients in the following directions: horizontal, vertical, diagonal, center
* graphics.Gradient, if printed, will show a colored spectrum and the description of its stops and steps.
* The Scene class has a new method: apply_gradient_to_symbols(). This method will iterate over a list of symbols and apply the colors from a gradient to the symbols. A frame with the symbol will be added for each color starting from the last color used in the previous symbol, up to the the index determined by the ratio of the current symbol's index in the symbols list to the total length of the list. This method allows scenes to automatically create frames from a list of symbols and gradient of arbitrary length while ensuring every symbol and color is displayed.
* On instatiation, Terminal creates EffectCharacters for every coordinate in the canvas that does not have an input character. These EffectCharacters have the symbol " " and are stored in Terminal._fill_characters as well as added to Terminal.character_by_input_coord.
* argvalidators.IntRange will validate a range specified as "int-int" and return a tuple[int,int].
* argvalidators.FloatRange will validate a range of floats specified as "float-float" and return a tuple[float, float].
* character.animation.set_appearance(symbol, color) will set the character symbol and color directly. If a Scene is active, the appearance will be overwritten with the Scene frame on the next call to step_animation(). This method is intended for the occasion where a full scene isn't needed, or the appearance needs to be set based on conditions not compatible with Scenes or the EventHandler. For example, setting the color based on the terminal row.
* Terminal.CharacterSort enums moved to Terminal.CharacterGroup, Terminal.CharacterSort is now used for sorting and return a flat list of characters.
* Terminal.CharacterSort has new sort methods, TOP_TO_BOTTOM_LEFT_TO_RIGHT, TOP_TO_BOTTOM_RIGHT_TO_LEFT, BOTTOM_TO_TOP_LEFT_TO_RIGHT, BOTTOM_TO_TOP_RIGHT_TO_LEFT, OUTSIDE_ROW_TO_MIDDLE, MIDDLE_ROW_TO_OUTSIDE
* New Terminal.CharacterGroup options, CENTER_TO_OUTSIDE_DIAMONDS and OUTSIDE_TO_CENTER_DIAMONS
* graphics.Animation.adjust_color_brightness(color: graphics.Color, brightness: float) will convert the color to HSL, adjust the brightness to the given level, and return
  an RGB hex string.
* CTRL-C keyboard interrupt during a running effect will exit gracefully.
* geometry.find_coords_in_circle() has been rewritten to find all coords which fall in an ellipse. The result is a circle due to the height/width ratio of terminal cells. This function now finds all terminal coordinates within the 'circle' rather than an arbitrary subset.
* All command line arguments are typed allowing for more easily defined and tested effect args.

### Changes (0.7.0)

#### Effects Changes (0.7.0)

* All effects have been updated to use the latest API calls for improved performance.
* All effects support gradients for the final appearance.
* All effects support gradient direction.
* All effects have had their default colors refreshed.
* ErrorCorrect swap-delay lowered and error-pairs specification changed to percent float.
* Rain effect supports character specification for rain drops and movement speed range for the rain drop falling speed.
* Print effect uses the row final gradient color for the print head color.
* RandomSequence effect accepts a starting color and a speed.
* Rings effect prepares faster. Ring colors are set in order of appearance in the ring-colors argument. Ring spin speed is configurable. Rings with less than 25% visible characters based on radius are no longer generated. Ring gap is set as a percent of the smallest canvas dimension.
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

#### Engine Changes (0.7.0)

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
* argtypes.py has been renamed argvalidators.py and all functions have been refactored into classes with a METAVAR class member and a type_parser method.
* easing.EasingFunction type alias used anywhere an easing function is accepted.
* Exceptions raised are no longer caught in a except clause. Only a finally clause is used to restore the cursor. Tracebacks are useful.

#### Other Changes (0.7.0)

* More tests have been added.

### Bug Fixes (0.7.0)

#### Effects Fixes (0.7.0)

* All effects with command line options that accept variable length arguments which require at least 1 argument will present an error message when the option is called with 0 arguments.

#### Engine Fixes (0.7.0)

* Fixed division by zero error in geometry.find_coord_at_distance() when the origin coord and the target coord are the same.
* Fixed gradient generating an extra color in the spectrum when the initial color pair was repeated. Ex: Gradient('ffffff','000000','ffffff','000000, steps=5) would result in the third color 'ffffff' being added to the spectrum when it was already present as the end of the generation from '000000'->'ffffff'.

## 0.6.0

### New Features (0.6.0)

#### New Effects (0.6.0)

* Print. Lines are printed one at a time following a print head. Print head performs line feed, carriage return.
* BinaryPath. Characters are converted into their binary representation. These binary groups travel to their input coordinate and collapse into the original character symbol.
* Wipe. Performs directional wipes with an optional trailing gradient.
* Slide. Slides characters into position from outside the terminal view. Characters can be grouped by column, row, or diagonal. Groups can be merged from opposite directions or slide from the same direction.
* SynthGrid. Creates a gradient colored grid in which blocks of characters dissolve into the input text.

#### New Engine Features (0.6.0)

* Terminal.get_character() method accepts a Terminal.CharacterSort argument to easily retrieve the input characters in groups sorted by various directions, ex: Terminal.CharacterSort.COLUMN_LEFT_TO_RIGHT
* Terminal.add_character() method allows adding characters to the effect that are not part of the input text. These characters are added to a separate list (Terminal.non_input_characters) in terminal to allow for iteration over Terminal.characters and adding new characters based on the input characters without modifying the Terminal.characters list during iteration. The added characters are handled the same as input characters by the Terminal.
* New EventHandler Action, Callback. The Action target can be any callable and will pass the character as the first argument, followed by any additional arguments provided. Uses new EventHandler.Callback type with signature EventHandler.Callback(typing.Callable, *args)
* graphics.Gradient() objects specified with a single color will create a list of the single color with length *steps*. This enables gradients to be specified via command line arguments while supporting an arbitrary number of colors > 0, without needing to perform any checking in the effect logic.

### Changes (0.6.0)

### Effects Changes (0.6.0)

* Rowslide, Columnslide, and Rowmerge have been replaced with a single effect, Slide.
* Many classic effects now support gradient specification which includes stops, steps, and frames to enable greater customization.
* Randomsequence effect supports gradient specification.
* Scattered effect supports gradient specification.
* Expand effect supports gradient specification.
* Pour effect now has a back and forth pouring animation and supports gradient specification.

#### Engine Changes (0.6.0)

* Terminal._update_terminal_state() refactored for improved performance.
* EffectCharacter.tick() will progress motion and animation by one step. This solves the problem of running Animation.step_animation() before Motion.move() and desyncing Path synced animations.
* EffectCharacter.is_active has been renamed to EffectCharacter.is_visible.
* EffectCharacter.is_active() can be used to check if motion/animation is in progress.
* graphics.Animation.new_scene(), motion.Motion.new_path(), and Path.new_waypoint() all support automatic IDs. If no ID is provided a unique ID is automatically generated.

### Bug Fixes (0.6.0)

* Fixed rare division by zero error in Path.step() when the final segment has a distance of zero and the distance to travel exceeds
   the total distance of the Path.
* Fixed effects not respecting --no-color argument.

## 0.5.0

### New Features (0.5.0)

* New effect, Vhstape. Lines of characters glitch left and right and lose detail like an old VHS tape.
* New effect, Crumble. Characters lose color and fall as dust before being vacuumed up and rebuilt.
* New effect, Rings. Characters are dispersed throughout the canvas and form into spinning rings.
* motion.Motion.chain_paths(list[Paths]) will automatically register Paths with the EventHandler to create
   a chain of paths. Looping is supported.
* motion.Motion.find_coords_in_rect() will return a random selection of coordinates within a rectangular area. This is faster than using
   find_coords_in_circle() and should be used when the shape of the search area isn't important.
* Terminal.Canvas.coord_in_canvas() can be used to determine if a Coord is in the canvas.
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

### Changes (0.5.0)

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

### Bug Fixes (0.5.0)

* Fixed looping animations when synced to Path not resetting properly.

## 0.4.3

### Changes (0.4.3)

* blackhole radius is based on the canvas size, not the input text size.

## 0.4.2

### Changes (0.4.2)

* motion.Motion.find_points_on_circle and motion.Motion.find_points_in_circle now account for the terminal character height/width ratio to
   return points that more closely approximate a circle. All effects which use these functions have been updated to account for this change.

## 0.4.1

### Changes (0.4.1)

* Updated documentation

## 0.4.0

### New Features (0.4.0)

* Waves effect. A wave animation is played over the characters. Wave colors and final colors are configurable.
* Blackhole effect. Characters spawn scattered as a field of stars. A blackhole forms and consumes the stars then explodes the characters across
   the screen. Characters then 'cool' and ease into position.
* Swarm effect. Characters a separated into swarms and fly around the canvas before landing in position.
* Animations support easing functions. Easing functions are applied to Scenes using Scene.ease = easing_function.
* Canvas has a center attribute that is the center Coord of the canvas.
* Terminal has a random_coord() method which returns a random coordinate. Can specify outside the canvas.

### Changes (0.4.0)

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

### Bug Fixes (0.4.0)

* Fixed Gradient creating two more steps than specified.
* Fixed waypoint synced animation index out of range error.

## 0.3.1

### New Features (0.3.1)

* Bouncyballs effect. Balls drop from the top of the canvas and bounce before
  settling into position. A gradient is used to transition to the final color after the
  ball has landed. Random colors are used for balls unless specified.

* Unstable effect. Spawn characters jumbled, explode to the edge of the canvas,
  then reassemble them in the correct layout.

* Bubble effect. Characters are formed into bubbles and fall down the screen before popping.

* Middleout effect. Characters start as a single character in the center of the canvas. A row or column
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

### Changes (0.3.1)

* Added Easing Functions help output for fireworks effect.
* Updated spray effect help output.
* Removed shootingstar effect. It was not particularly interesting.
* Coord type is now hashable and frozen.
* Waypoints are hashable. Can be compared for equality based on row, col pair.
* Scenes can be compared for equality based on id.
* Terminal maintains an input_coord tuple[row, col] -> EffectCharacter map called character_by_input_coord.
* The terminal cursor is now hidden during the effect.
* The find_points_on_circle method in the motion module is now a static method.
* Terminal.Canvas has center_row and center_column attributes.
* Added layers to effects.

### Bug Fixes (0.3.1)

* Fixed animating_chars filter in effect_template to properly remove completed characters.
* Initial symbol assignment when activating a scene no longer increases played_frames count.
* Waypoints and Animations completed are deactivated to prevent repeated event triggering.
* Fixed step_animation in graphics module handling of looping animations. It will no longer deactivate the animation.

## 0.2.1

### New Features (0.2.1)

* Added explode distance argument to fireworks effect
* Added random_color function to graphics module

### Changes (0.2.1)

### Bug Fixes (0.2.1)

* Fixed inactive characters in expand effect.
