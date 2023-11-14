import argparse
import random

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils.terminal import Terminal
from terminaltexteffects.utils import graphics, motion, argtypes, easing


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
        epilog=f"""

Example: terminaltexteffects rings --animation-rate 0.01 --ring-colors ffcc0d ff7326 ff194d bf2669 702a8c --base-color ffffff --ring-gap 6 --spin-duration 200 --disperse-duration 200 --spin-disperse-cycles 3""",
    )
    effect_parser.set_defaults(effect_class=RingsEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.valid_animationrate,
        default=0.01,
        help="Time, in seconds, between animation steps.",
    )
    effect_parser.add_argument(
        "--ring-colors",
        type=argtypes.valid_color,
        nargs="*",
        default=["ffcc0d", "ff7326", "ff194d", "bf2669", "702a8c"],
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Space separated, unquoted, list of colors for the rings.",
    )
    effect_parser.add_argument(
        "--base-color",
        type=argtypes.valid_color,
        default="ffffff",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the characters when they are not in rings.",
    )
    effect_parser.add_argument(
        "--ring-gap",
        type=argtypes.positive_int,
        default=6,
        help="Distance between rings. Lower distance results in more rings on screen.",
    )
    effect_parser.add_argument(
        "--spin-duration",
        type=argtypes.positive_int,
        default=200,
        help="Number of animation steps for each cycle of the spin phase.",
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
        radius: int,
        origin: motion.Coord,
        ring_coords: list[motion.Coord],
        ring_gap: int,
        ring_color: str,
        base_color: str,
    ):
        self.radius = radius
        self.origin: motion.Coord = origin
        self.counter_clockwise_coords = ring_coords
        self.clockwise_coords = ring_coords[::-1]
        self.ring_gap = ring_gap
        self.ring_color = ring_color
        self.characters: list[EffectCharacter] = []
        self.character_last_ring_wpt: dict[EffectCharacter, motion.Waypoint] = {}
        self.rotations = 0
        self.rotation_speed = random.uniform(0.2, 0.5)
        self.gradient = self.make_gradient(ring_color, "ffffff", max(len(self.counter_clockwise_coords) // 3, 1))
        self.gradient_shift = 0
        self.disperse_gradient = graphics.Gradient(self.ring_color, base_color, 7)

    def make_gradient(self, start_color: str, end_color: str, steps: int) -> list[str]:
        gradient = graphics.Gradient(start_color, end_color, steps)
        full_gradient = list(gradient) + list(gradient)[::-1]
        return full_gradient

    def add_character(self, character: EffectCharacter, clockwise: int) -> None:
        # make gradient scene
        gradient_scn = character.animation.new_scene("gradient", is_looping=True)
        for step in self.gradient[self.gradient_shift :] + self.gradient[: self.gradient_shift]:
            gradient_scn.add_frame(character.input_symbol, 1, color=step)
        self.gradient_shift += 1
        # make rotation waypoints
        waypoints: list[motion.Waypoint] = []
        character_starting_index = len(self.characters)
        if clockwise:
            coords = self.clockwise_coords
        else:
            coords = self.counter_clockwise_coords
        for coord in coords[character_starting_index:] + coords[:character_starting_index]:
            waypoints.append(character.motion.new_waypoint(str(len(waypoints)), coord, speed=self.rotation_speed))
        character.motion.chain_waypoints(waypoints, loop=True)
        self.character_last_ring_wpt[character] = waypoints[0]
        # make disperse scene
        disperse_scn = character.animation.new_scene("disperse", is_looping=False)
        for step in self.disperse_gradient:
            disperse_scn.add_frame(character.input_symbol, 16, color=step)

        self.characters.append(character)

    def make_disperse_waypoints(self, character: EffectCharacter, origin: motion.Coord) -> motion.Waypoint:
        """Make waypoints for a character to disperse from the ring. Register the waypoints and return the first waypoint.

        Args:
            character (EffectCharacter): Character to disperse.
            origin (motion.Coord): Origin coordinate for the character.

        Returns:
            motion.Waypoint: the first waypoint.
        """
        disperse_coords = motion.Motion.find_coords_in_rect(origin, self.ring_gap, 5)
        disperse_wpts = [
            character.motion.new_waypoint(str(len(character.motion.waypoints)), coord, speed=0.1)
            for coord in disperse_coords
        ]
        start_wpt = disperse_wpts[0]
        character.motion.chain_waypoints(disperse_wpts, loop=True)
        return start_wpt

    def disperse(self) -> None:
        """Disperse the characters from the ring."""
        for character in self.characters:
            if character.motion.active_waypoint is not None:
                self.character_last_ring_wpt[character] = character.motion.active_waypoint
            else:
                self.character_last_ring_wpt[character] = character.motion.waypoints["0"]
            character.motion.activate_waypoint(self.make_disperse_waypoints(character, character.motion.current_coord))
            character.animation.activate_scene(character.animation.scenes["disperse"])

    def spin(self) -> None:
        for character in self.characters:
            condense_wpt = character.motion.new_waypoint(
                str(len(character.motion.waypoints)),
                self.character_last_ring_wpt[character].coord,
                speed=0.1,
                ease=easing.in_quart,
            )
            character.event_handler.register_event(
                EventHandler.Event.WAYPOINT_COMPLETE,
                condense_wpt,
                EventHandler.Action.ACTIVATE_WAYPOINT,
                self.character_last_ring_wpt[character],
            )
            character.motion.activate_waypoint(self.character_last_ring_wpt[character])
            character.animation.activate_scene(character.animation.scenes["gradient"])


class RingsEffect:
    """Effect that forms the characters into rings."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.animating_chars: list[EffectCharacter] = []
        self.ring_chars: list[EffectCharacter] = []
        self.non_ring_chars: list[EffectCharacter] = []
        self.rings: dict[int, Ring] = {}
        self.ring_gap = self.args.ring_gap

    def prepare_data(self) -> None:
        """Prepares the data for the effect by building rings and associated animations/waypoints."""
        for character in self.terminal.characters:
            start_scn = character.animation.new_scene("start")
            start_scn.add_frame(character.input_symbol, 1, color=self.args.base_color)
            home_wpt = character.motion.new_waypoint("home", character.input_coord, speed=0.8, ease=easing.out_quad)
            character.animation.activate_scene(start_scn)
            character.is_active = True
            self.pending_chars.append(character)

        random.shuffle(self.pending_chars)
        # make rings
        for radius in range(1, max(self.terminal.output_area.right, self.terminal.output_area.top), self.ring_gap):
            ring_coords: list[motion.Coord] = []
            circle_coords = motion.Motion.find_coords_on_circle(self.terminal.output_area.center, radius, 7 * radius)
            # check if any part of the ring is in the output area, if not, stop creating rings
            if not any([self.terminal.output_area.coord_in_output_area(coord) for coord in circle_coords]):
                break
            # remove any duplicate coords
            for coord in circle_coords:
                if coord not in ring_coords:
                    ring_coords.append(coord)
            self.rings[radius] = Ring(
                radius,
                self.terminal.output_area.center,
                ring_coords,
                self.ring_gap,
                random.choice(self.args.ring_colors),
                self.args.base_color,
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
        for character in self.terminal.characters:
            if character not in self.ring_chars:
                color = random.choice(self.args.ring_colors)
                external_wpt = character.motion.new_waypoint(
                    "external", self.terminal.random_coord(outside_scope=True), speed=0.7, ease=easing.out_cubic
                )
                # make disperse gradient
                color = random.choice(self.args.ring_colors)
                disperse_gradient_front = graphics.Gradient(self.args.base_color, color, 7)
                disperse_gradient_back = graphics.Gradient(color, self.args.base_color, 7)
                disperse_scn = character.animation.new_scene(
                    "disperse", is_looping=False, sync=graphics.SyncMetric.DISTANCE
                )
                for step in disperse_gradient_front:
                    disperse_scn.add_frame(character.input_symbol, 2, color=step)
                for step in disperse_gradient_back:
                    disperse_scn.add_frame(character.input_symbol, 2, color=step)
                    self.non_ring_chars.append(character)
                    character.event_handler.register_event(
                        EventHandler.Event.WAYPOINT_COMPLETE,
                        external_wpt,
                        EventHandler.Action.SET_CHARACTER_ACTIVATION_STATE,
                        False,
                    )
                character.event_handler.register_event(
                    EventHandler.Event.WAYPOINT_ACTIVATED,
                    external_wpt,
                    EventHandler.Action.ACTIVATE_SCENE,
                    disperse_scn,
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
                            disperse_wpt = ring.make_disperse_waypoints(
                                character, character.motion.waypoints["0"].coord
                            )
                            initial_wpt = character.motion.new_waypoint(
                                "initial", disperse_wpt.coord, speed=0.3, ease=easing.out_cubic
                            )
                            character.event_handler.register_event(
                                EventHandler.Event.WAYPOINT_COMPLETE,
                                initial_wpt,
                                EventHandler.Action.ACTIVATE_WAYPOINT,
                                disperse_wpt,
                            )
                            character.animation.activate_scene(character.animation.scenes["disperse"])
                            character.motion.activate_waypoint(initial_wpt)
                            self.animating_chars.append(character)

                    for character in self.non_ring_chars:
                        character.motion.activate_waypoint(character.motion.waypoints["external"])
                        self.animating_chars.append(character)

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
                        for character in self.terminal.characters:
                            character.is_active = True
                            if "external" in character.motion.waypoints:
                                self.animating_chars.append(character)
                            character.motion.activate_waypoint(character.motion.waypoints["home"])
                            character.animation.activate_scene(character.animation.scenes["disperse"])
                    else:
                        disperse_time_remaining = self.args.disperse_duration
                        for ring in rings:
                            ring.disperse()
                        phase = "disperse"

                else:
                    spin_time_remaining -= 1

            elif phase == "final":
                if not self.animating_chars:
                    phase = "complete"

            self.terminal.print()
            self.animate_chars()
            self.animating_chars = [
                animating_char
                for animating_char in self.animating_chars
                if not animating_char.animation.active_scene_is_complete()
                or not animating_char.motion.movement_is_complete()
            ]

    def animate_chars(self) -> None:
        """Animates the characters by calling the move method and step animation. Move characters prior to stepping animation
        to ensure waypoint synced animations have the latest waypoint progress information."""
        for animating_char in self.animating_chars:
            animating_char.motion.move()
            animating_char.animation.step_animation()
