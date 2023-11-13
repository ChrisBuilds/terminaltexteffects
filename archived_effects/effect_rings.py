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
        "test",
        formatter_class=argtypes.CustomFormatter,
        help="effect_description",
        description="effect_description",
        epilog=f"""{argtypes.EASING_EPILOG}

Example: effect_example""",
    )
    effect_parser.set_defaults(effect_class=NamedEffect)
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
        default=["f24162", "a24cc2", "58f380", "d9e716", "f25a40"],
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Space separated, unquoted, list of colors for the ___.",
    )
    effect_parser.add_argument(
        "--final-color",
        type=argtypes.valid_color,
        default="9295cd",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the final character.",
    )
    effect_parser.add_argument(
        "--ring-gap",
        type=argtypes.positive_int,
        default=4,
        help="Distance between rings. Lower distance results in more rings on screen. This will impact the ring-break-delay calculation.",
    )
    effect_parser.add_argument(
        "--ring-break-delay",
        type=argtypes.ge_zero,
        default=30,
        help="Delay between rings breaking. Actual delay is calculated as DELAY * number_of_unbroken_rings. Resulting in a faster effect as more rings break.",
    )
    effect_parser.add_argument(
        "--shimmer-time",
        type=argtypes.ge_zero,
        default=300,
        help="Number of animation steps for the final shimmer before transitioning to the final color.",
    )


class Ring:
    def __init__(
        self, radius: int, origin: motion.Coord, ring_coords: list[motion.Coord], ring_gap: int, ring_color: str
    ):
        self.radius = radius
        self.origin: motion.Coord = origin
        self.counter_clockwise_coords = ring_coords
        self.clockwise_coords = ring_coords[::-1]
        self.ring_gap = ring_gap
        self.characters: list[EffectCharacter] = []
        self.rotations = 0
        self.rotation_speed = random.uniform(0.2, 0.5)
        self.gradient = self.make_gradient(ring_color, "ffffff", max(len(self.counter_clockwise_coords) // 3, 1))
        self.gradient_shift = 0

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

        self.characters.append(character)

    def dissolve(self) -> None:
        for character in self.characters:
            pop_coord = random.choice(
                motion.Motion.find_coords_in_circle(character.motion.current_coord, self.ring_gap, 5)
            )
            pop_wpt = character.motion.new_waypoint("pop", pop_coord, speed=0.1, ease=easing.out_expo)
            origin_wpt = character.motion.new_waypoint("origin", self.origin, speed=0.4, ease=easing.in_sine)
            character.event_handler.register_event(
                EventHandler.Event.WAYPOINT_REACHED,
                pop_wpt,
                EventHandler.Action.ACTIVATE_WAYPOINT,
                origin_wpt,
            )
            character.motion.activate_waypoint(pop_wpt)
            character.event_handler.register_event(
                EventHandler.Event.WAYPOINT_REACHED,
                origin_wpt,
                EventHandler.Action.SET_CHARACTER_ACTIVATION_STATE,
                False,
            )


class NamedEffect:
    """Effect that ___."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.uncollapsed_chars: list[EffectCharacter] = []
        self.animating_chars: list[EffectCharacter] = []
        self.ring_chars: list[EffectCharacter] = []
        self.rings: dict[int, Ring] = {}
        self.ring_gap = self.args.ring_gap
        self.final_gradient = graphics.Gradient("ffffff", self.args.final_color, 10)

    def prepare_data(self) -> None:
        """Prepares the data for the effect by ___."""
        for character in self.terminal.characters:
            character.is_active = True
            origin_wpt = character.motion.new_waypoint(
                "origin", self.terminal.output_area.center, speed=0.3, ease=easing.in_expo
            )
            character.event_handler.register_event(
                EventHandler.Event.WAYPOINT_REACHED,
                origin_wpt,
                EventHandler.Action.SET_CHARACTER_ACTIVATION_STATE,
                False,
            )
            final_scene = character.animation.new_scene("final")
            for step in self.final_gradient:
                final_scene.add_frame(character.input_symbol, 6, color=step)
            self.pending_chars.append(character)
            self.uncollapsed_chars.append(character)
        random.shuffle(self.pending_chars)

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

        for character in self.terminal.characters:
            if character not in self.ring_chars:
                character.event_handler.register_event(
                    EventHandler.Event.WAYPOINT_REACHED,
                    origin_wpt,
                    EventHandler.Action.SET_CHARACTER_ACTIVATION_STATE,
                    False,
                )

    def run(self) -> None:
        """Runs the effect."""
        for character in self.terminal.characters:
            self.animating_chars.append(character)
            character.is_active = True
        self.terminal.print()
        self.prepare_data()
        shimmer_time = self.args.shimmer_time
        rings = list(self.rings.values())
        ring_break_delay = self.args.ring_break_delay * len(rings)
        phase = "collapse"
        restored = False
        final_scenes_activated = False
        while phase != "complete":
            self.terminal.print()
            self.animate_chars()
            if phase == "collapse":
                while self.uncollapsed_chars:
                    character = self.uncollapsed_chars.pop(0)
                    character.motion.activate_waypoint(character.motion.waypoints["origin"])
                    self.animating_chars.append(character)
                if not self.animating_chars:
                    phase = "ring"
            elif phase == "ring":
                while self.ring_chars:
                    character = self.ring_chars.pop(0)
                    character.is_active = True
                    character.motion.activate_waypoint(character.motion.waypoints["0"])
                    character.animation.activate_scene(character.animation.scenes["gradient"])
                    self.animating_chars.append(character)
                phase = "pop"
            elif phase == "pop":
                if not ring_break_delay:
                    if rings:
                        ring = rings.pop(0)
                        ring.dissolve()
                        ring_break_delay = self.args.ring_break_delay * len(rings)
                else:
                    ring_break_delay -= 1
                if not self.animating_chars:
                    phase = "restore"
            elif phase == "restore":
                if not restored:
                    restored = True
                    for character in self.terminal.characters:
                        exterior_coord = self.terminal.random_coord(outside_scope=True)
                        character.motion.set_coordinate(exterior_coord)
                        input_wpt = character.motion.new_waypoint(
                            "input", character.input_coord, speed=0.5, ease=easing.out_circ
                        )
                        character.is_active = True
                        character.motion.activate_waypoint(input_wpt)
                        self.animating_chars.append(character)
                if all([character.motion.movement_is_complete() for character in self.animating_chars]):
                    phase = "shimmer"
            elif phase == "shimmer":
                if not shimmer_time:
                    phase = "final"
                shimmer_time -= 1
            elif phase == "final":
                if not final_scenes_activated:
                    final_scenes_activated = True
                    for character in self.terminal.characters:
                        character.animation.activate_scene(character.animation.scenes["final"])
                        self.animating_chars.append(character)
                if not self.animating_chars:
                    phase = "complete"
            if phase not in ("restore", "shimmer"):
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
