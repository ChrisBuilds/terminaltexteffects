import argparse
import random

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils import easing, geometry, graphics, motion
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.terminal import Terminal


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "rings",
        formatter_class=argtypes.CustomFormatter,
        help="Characters are dispersed and form into spinning rings.",
        description="Characters are dispersed and form into spinning rings.",
        epilog="""

Example: terminaltexteffects rings --animation-rate 0.01 --ring-colors ffcc0d ff7326 ff194d bf2669 702a8c --base-color ffffff --ring-gap 6 --spin-duration 200 --disperse-duration 200 --spin-disperse-cycles 3""",
    )
    effect_parser.set_defaults(effect_class=RingsEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.nonnegative_float,
        default=0.01,
        help="Minimum time, in seconds, between animation steps. This value does not normally need to be modified. Use this to increase the playback speed of all aspects of the effect. This will have no impact beyond a certain lower threshold due to the processing speed of your device.",
    )
    effect_parser.add_argument(
        "--ring-colors",
        type=argtypes.color,
        nargs="+",
        default=["8A008A", "00D1FF", "FFFFFF"],
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Space separated, unquoted, list of colors for the rings.",
    )
    effect_parser.add_argument(
        "--final-gradient-stops",
        type=argtypes.color,
        nargs="+",
        default=["8A008A", "00D1FF", "FFFFFF"],
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )
    effect_parser.add_argument(
        "--final-gradient-steps",
        type=argtypes.positive_int,
        nargs="+",
        default=[12],
        metavar="(int > 0)",
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )
    effect_parser.add_argument(
        "--ring-gap",
        type=argtypes.positive_float,
        default=0.1,
        help="Distance between rings as a percent of the smallest output area dimension.",
    )
    effect_parser.add_argument(
        "--spin-duration",
        type=argtypes.positive_int,
        default=200,
        help="Number of animation steps for each cycle of the spin phase.",
    )
    effect_parser.add_argument(
        "--spin-speed",
        type=argtypes.float_range,
        default=(0.25, 1.0),
        metavar="(float range e.g. 0.25-1.0)",
        help="Range of speeds for the rotation of the rings. The speed is randomly selected from this range for each ring.",
    )
    effect_parser.add_argument(
        "--disperse-duration",
        type=argtypes.positive_int,
        default=200,
        help="Number of animation steps spent in the dispersed state between spinning cycles.",
    )
    effect_parser.add_argument(
        "--spin-disperse-cycles",
        type=argtypes.positive_int,
        default=3,
        help="Number of times the animation will cycles between spinning rings and dispersed characters.",
    )


class Ring:
    def __init__(
        self,
        args: argparse.Namespace,
        radius: int,
        origin: Coord,
        ring_coords: list[Coord],
        ring_gap: int,
        ring_color: str,
        character_color_map: dict[EffectCharacter, graphics.Color],
    ):
        self.args = args
        self.radius = radius
        self.origin: Coord = origin
        self.counter_clockwise_coords = ring_coords
        self.clockwise_coords = ring_coords[::-1]
        self.ring_gap = ring_gap
        self.ring_color = ring_color
        self.characters: list[EffectCharacter] = []
        self.character_last_ring_path: dict[EffectCharacter, motion.Path] = {}
        self.rotations = 0
        self.rotation_speed = random.uniform(self.args.spin_speed[0], self.args.spin_speed[1])
        self.character_color_map = character_color_map

    def add_character(self, character: EffectCharacter, clockwise: int) -> None:
        # make gradient scene
        gradient_scn = character.animation.new_scene(id="gradient")
        char_gradient = graphics.Gradient([self.character_color_map[character], self.ring_color], 8)
        gradient_scn.apply_gradient_to_symbols(char_gradient, character.input_symbol, 5)

        # make rotation waypoints
        ring_paths: list[motion.Path] = []
        character_starting_index = len(self.characters)
        if clockwise:
            coords = self.clockwise_coords
        else:
            coords = self.counter_clockwise_coords
        for coord in coords[character_starting_index:] + coords[:character_starting_index]:
            ring_path = character.motion.new_path(id=str(len(ring_paths)), speed=self.rotation_speed)
            ring_path.new_waypoint(coord, id=str(len(ring_path.waypoints)))
            ring_paths.append(ring_path)
        self.character_last_ring_path[character] = ring_paths[0]
        # make disperse scene
        disperse_scn = character.animation.new_scene(is_looping=False, id="disperse")
        disperse_gradient = graphics.Gradient([self.ring_color, self.character_color_map[character]], 8)
        disperse_scn.apply_gradient_to_symbols(disperse_gradient, character.input_symbol, 16)
        character.motion.chain_paths(ring_paths, loop=True)
        self.characters.append(character)

    def make_disperse_waypoints(self, character: EffectCharacter, origin: Coord) -> motion.Path:
        """Make the Path for the character to follow when the ring disperses.

        Args:
            character (EffectCharacter): Character to disperse.
            origin (Coord): Origin coordinate for the character.

        Returns:
            motion.Path: the Path to follow.
        """
        disperse_coords = geometry.find_coords_in_rect(origin, self.ring_gap)
        character.motion.paths.pop("disperse", None)
        disperse_path = character.motion.new_path(speed=0.1, loop=True, id="disperse")
        for _ in range(5):
            disperse_path.new_waypoint(disperse_coords[random.randrange(0, len(disperse_coords))])
        return disperse_path

    def disperse(self) -> None:
        """Disperse the characters from the ring."""
        for character in self.characters:
            if character.motion.active_path is not None:
                self.character_last_ring_path[character] = character.motion.active_path
            else:
                self.character_last_ring_path[character] = character.motion.paths["0"]
            character.motion.activate_path(self.make_disperse_waypoints(character, character.motion.current_coord))
            character.animation.activate_scene(character.animation.query_scene("disperse"))

    def spin(self) -> None:
        for character in self.characters:
            condense_path = character.motion.new_path(speed=0.1)
            condense_path.new_waypoint(self.character_last_ring_path[character].waypoints[0].coord)
            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE,
                condense_path,
                EventHandler.Action.ACTIVATE_PATH,
                self.character_last_ring_path[character],
            )
            character.motion.activate_path(condense_path)
            character.animation.activate_scene(character.animation.query_scene("gradient"))


class RingsEffect:
    """Effect that forms the characters into rings."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.ring_chars: list[EffectCharacter] = []
        self.non_ring_chars: list[EffectCharacter] = []
        self.rings: dict[int, Ring] = {}
        self.ring_gap = int(
            max(round(min(self.terminal.output_area.top, self.terminal.output_area.right) * self.args.ring_gap), 1)
        )
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def prepare_data(self) -> None:
        """Prepares the data for the effect by building rings and associated animations/waypoints."""
        final_gradient = graphics.Gradient(self.args.final_gradient_stops, self.args.final_gradient_steps)
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient.get_color_at_fraction(
                character.input_coord.row / self.terminal.output_area.top
            )
            start_scn = character.animation.new_scene()
            start_scn.add_frame(character.input_symbol, 1, color=self.character_final_color_map[character])
            home_path = character.motion.new_path(speed=0.8, ease=easing.out_quad, id="home")
            home_path.new_waypoint(character.input_coord)
            character.animation.activate_scene(start_scn)
            self.terminal.set_character_visibility(character, True)
            self.pending_chars.append(character)

        random.shuffle(self.pending_chars)
        # make rings
        for radius in range(1, max(self.terminal.output_area.right, self.terminal.output_area.top), self.ring_gap):
            ring_coords = geometry.find_coords_on_circle(
                self.terminal.output_area.center, radius, 7 * radius, unique=True
            )
            # check if any part of the ring is in the output area, if not, stop creating rings
            if (
                len([coord for coord in ring_coords if self.terminal.output_area.coord_is_in_output_area(coord)])
                / len(ring_coords)
                < 0.25
            ):
                break

            self.rings[radius] = Ring(
                self.args,
                radius,
                self.terminal.output_area.center,
                ring_coords,
                self.ring_gap,
                self.args.ring_colors[len(self.rings) % len(self.args.ring_colors)],
                self.character_final_color_map,
            )
        # assign characters to rings
        ring_count = 0
        for ring in self.rings.values():
            for _ in ring.counter_clockwise_coords:
                if self.pending_chars:
                    next_character = self.pending_chars.pop(0)
                    # set rings to rotate in opposite directions
                    ring.add_character(next_character, clockwise=ring_count % 2)
                    self.ring_chars.append(next_character)
            ring_count += 1

        # make external waypoints for characters not in rings
        for character in self.terminal.get_characters():
            if character not in self.ring_chars:
                external_path = character.motion.new_path(id="external", speed=0.8, ease=easing.out_sine)
                external_path.new_waypoint(self.terminal.output_area.random_coord(outside_scope=True))

                self.non_ring_chars.append(character)
                character.event_handler.register_event(
                    EventHandler.Event.PATH_COMPLETE,
                    external_path,
                    EventHandler.Action.CALLBACK,
                    EventHandler.Callback(self.terminal.set_character_visibility, False),
                )

    def run(self) -> None:
        """Runs the effect."""

        self.prepare_data()
        rings = list(self.rings.values())
        phase = "start"
        initial_disperse_complete = False
        spin_time_remaining = self.args.spin_duration
        disperse_time_remaining = self.args.disperse_duration
        cycles_remaining = self.args.spin_disperse_cycles
        initial_phase_time_remaining = 100
        while phase != "complete":
            if phase == "start":
                if not initial_phase_time_remaining:
                    phase = "disperse"
                else:
                    initial_phase_time_remaining -= 1

            elif phase == "disperse":
                if not initial_disperse_complete:
                    initial_disperse_complete = True
                    for ring in rings:
                        for character in ring.characters:
                            disperse_path = ring.make_disperse_waypoints(
                                character, character.motion.paths["0"].waypoints[0].coord
                            )
                            initial_path = character.motion.new_path(speed=0.3, ease=easing.out_cubic)
                            initial_path.new_waypoint(disperse_path.waypoints[0].coord)
                            character.event_handler.register_event(
                                EventHandler.Event.PATH_COMPLETE,
                                initial_path,
                                EventHandler.Action.ACTIVATE_PATH,
                                disperse_path,
                            )
                            character.animation.activate_scene(character.animation.query_scene("disperse"))
                            character.motion.activate_path(initial_path)
                            self.active_chars.append(character)

                    for character in self.non_ring_chars:
                        character.motion.activate_path(character.motion.query_path("external"))
                        self.active_chars.append(character)

                else:
                    if not disperse_time_remaining:
                        phase = "spin"
                        cycles_remaining -= 1
                        spin_time_remaining = self.args.spin_duration
                        for ring in rings:
                            ring.spin()
                    else:
                        disperse_time_remaining -= 1

            elif phase == "spin":
                if not spin_time_remaining:
                    if not cycles_remaining:
                        phase = "final"
                        for character in self.terminal.get_characters():
                            self.terminal.set_character_visibility(character, True)
                            character.motion.activate_path(character.motion.query_path("home"))
                            self.active_chars.append(character)
                            if "external" in character.motion.paths:
                                continue
                            character.animation.activate_scene(character.animation.query_scene("disperse"))
                    else:
                        disperse_time_remaining = self.args.disperse_duration
                        for ring in rings:
                            ring.disperse()
                        phase = "disperse"

                else:
                    spin_time_remaining -= 1

            elif phase == "final":
                if not self.active_chars:
                    phase = "complete"

            self.terminal.print()
            self.animate_chars()
            self.active_chars = [character for character in self.active_chars if character.is_active]

    def animate_chars(self) -> None:
        """Animates the characters by calling the tick method on all active characters."""
        for character in self.active_chars:
            character.tick()
