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
        "blackhole",
        formatter_class=argtypes.CustomFormatter,
        help="Characters are consumed by a black hole and explode outwards.",
        description="Characters are consumed by a black hole and explode outwards.",
        epilog=f"""
Example: terminaltexteffects blackhole -a 0.01 --star-colors ffcc0d ff7326 ff194d bf2669 702a8c 049dbf --final-color 00a7c2""",
    )
    effect_parser.set_defaults(effect_class=BlackholeEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.valid_animationrate,
        default=0.01,
        help="Time, in seconds, between animation steps.",
    )
    effect_parser.add_argument(
        "--blackhole-color",
        type=argtypes.valid_color,
        default="ffffff",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the stars that comprise the blackhole border.",
    )
    effect_parser.add_argument(
        "--star-colors",
        type=argtypes.valid_color,
        nargs="*",
        default=["ffcc0d", "ff7326", "ff194d", "bf2669", "702a8c", "049dbf"],
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="List of colors from which character colors will be chosen and applied after the explosion, but before the cooldown to final color.",
    )
    effect_parser.add_argument(
        "--final-color",
        type=argtypes.valid_color,
        default="00a7c2",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Final color that characters will shift to after exploding.",
    )


class BlackholeEffect:
    """Effect that creates a blackhole in a starfield, consumes the stars, and explodes the input characters out to position."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.animating_chars: list[EffectCharacter] = []
        self.blackhole_chars: list[EffectCharacter] = []
        self.awaiting_consumption_chars: list[EffectCharacter] = []
        self.blackhole_radius = max(
            min(round(self.terminal.input_width * 0.4), round(self.terminal.input_height * 0.4)), 4
        )

    def prepare_blackhole(self) -> None:
        star_symbols = [
            "*",
            "✸",
            "✺",
            "✹",
            "✷",
            "✵",
            "✴",
            "✶",
            "⋆",
            "'",
            ".",
            "⬫",
            "⬪",
            "⬩",
            "⬨",
            "⬧",
            "⬦",
            "⬥",
        ]
        starfield_colors = graphics.Gradient("4a4a4d", "ffffff", 6).colors
        gradient_map = {}
        for color in starfield_colors:
            gradient_map[color] = graphics.Gradient(color, "000000", 10)
        available_chars = list(self.terminal.characters)
        while len(self.blackhole_chars) < self.blackhole_radius * 3 and available_chars:
            self.blackhole_chars.append(available_chars.pop(random.randrange(0, len(available_chars))))
        black_hole_ring_positions = motion.Motion.find_coords_on_circle(
            self.terminal.output_area.center, self.blackhole_radius, len(self.blackhole_chars)
        )
        for character in self.blackhole_chars:
            next_pos = black_hole_ring_positions.pop(0)
            blackhole_wpt = character.motion.new_waypoint("blackhole", next_pos, speed=0.5, ease=easing.in_out_sine)
            blackhole_scn = character.animation.new_scene("blackhole")
            blackhole_scn.add_frame("✸", 1, color=self.args.blackhole_color)
            character.event_handler.register_event(
                EventHandler.Event.WAYPOINT_ACTIVATED, blackhole_wpt, EventHandler.Action.SET_LAYER, 1
            )
        for character in self.terminal.characters:
            character.is_active = True
            starting_scn = character.animation.new_scene("starting")
            star_symbol = random.choice(star_symbols)
            star_color = random.choice(starfield_colors)
            starting_scn.add_frame(star_symbol, 1, color=star_color)
            character.animation.activate_scene(starting_scn)
            if character not in self.blackhole_chars:
                character.motion.set_coordinate(self.terminal.random_coord())
                singluarity_wpt = character.motion.new_waypoint(
                    "singularity",
                    self.terminal.output_area.center,
                    speed=0.3,
                    ease=easing.in_expo,
                )
                consumed_scn = character.animation.new_scene("consumed")
                for color in gradient_map[star_color]:
                    consumed_scn.add_frame(star_symbol, 1, color=color)
                consumed_scn.add_frame(" ", 1)
                consumed_scn.sync = graphics.SyncMetric.DISTANCE
                character.event_handler.register_event(
                    EventHandler.Event.WAYPOINT_ACTIVATED, singluarity_wpt, EventHandler.Action.SET_LAYER, 2
                )
                character.event_handler.register_event(
                    EventHandler.Event.WAYPOINT_ACTIVATED,
                    singluarity_wpt,
                    EventHandler.Action.ACTIVATE_SCENE,
                    consumed_scn,
                )
                self.awaiting_consumption_chars.append(character)
        random.shuffle(self.awaiting_consumption_chars)

    def rotate_blackhole(self) -> None:
        self.blackhole_chars = self.blackhole_chars[2:] + self.blackhole_chars[:2]
        black_hole_ring_positions = motion.Motion.find_coords_on_circle(
            self.terminal.output_area.center, self.blackhole_radius, len(self.blackhole_chars)
        )
        for character in self.blackhole_chars:
            next_pos = black_hole_ring_positions.pop(0)
            rotate_wpt = character.motion.new_waypoint("rotate", next_pos, speed=0.1)
            character.motion.activate_waypoint(rotate_wpt)
            if character not in self.animating_chars:
                self.animating_chars.append(character)

    def collapse_blackhole(self) -> None:
        black_hole_ring_positions = motion.Motion.find_coords_on_circle(
            self.terminal.output_area.center, self.blackhole_radius + 4, len(self.blackhole_chars)
        )
        unstable_symbols = ["◦", "◎", "◉", "●", "◉", "◎", "◦"]
        point_char_made = False
        for character in self.blackhole_chars:
            next_pos = black_hole_ring_positions.pop(0)
            expand_wpt = character.motion.new_waypoint("expand", next_pos, speed=0.1, ease=easing.in_expo)
            collapse_wpt = character.motion.new_waypoint(
                "collapse",
                self.terminal.output_area.center,
                speed=0.3,
                ease=easing.in_expo,
            )
            character.event_handler.register_event(
                EventHandler.Event.WAYPOINT_REACHED, expand_wpt, EventHandler.Action.ACTIVATE_WAYPOINT, collapse_wpt
            )
            if not point_char_made:
                point_scn = character.animation.new_scene("point")
                for _ in range(3):
                    for symbol in unstable_symbols:
                        point_scn.add_frame(symbol, 6, color=random.choice(self.args.star_colors))
                character.event_handler.register_event(
                    EventHandler.Event.WAYPOINT_REACHED, collapse_wpt, EventHandler.Action.ACTIVATE_SCENE, point_scn
                )
                character.event_handler.register_event(
                    EventHandler.Event.WAYPOINT_REACHED, collapse_wpt, EventHandler.Action.SET_LAYER, 3
                )
                point_char_made = True

            character.motion.activate_waypoint(expand_wpt)
            self.animating_chars.append(character)

    def explode_singularity(self) -> None:
        star_colors = ["ffcc0d", "ff7326", "ff194d", "bf2669", "702a8c" "049dbf"]
        for character in self.terminal.characters:
            nearby_coord = motion.Motion.find_coords_on_circle(character.input_coord, 4, 5)[random.randrange(0, 5)]
            nearby_wpt = character.motion.new_waypoint(
                "nearby_wpt",
                nearby_coord,
                speed=random.randint(2, 3) / 10,
                ease=easing.out_expo,
            )
            input_wpt = character.motion.new_waypoint(
                "input_wpt",
                character.input_coord,
                speed=random.randint(3, 5) / 100,
                ease=easing.in_cubic,
            )
            explode_scn = character.animation.new_scene("explode")
            explode_star_color = random.choice(star_colors)
            explode_scn.add_frame(character.input_symbol, 1, color=explode_star_color)
            cooling_scn = character.animation.new_scene("cooling")
            cooling_gradient = graphics.Gradient(explode_star_color, self.args.final_color, 10)
            for color in cooling_gradient:
                cooling_scn.add_frame(character.input_symbol, 20, color=color)
            character.event_handler.register_event(
                EventHandler.Event.WAYPOINT_REACHED, nearby_wpt, EventHandler.Action.ACTIVATE_WAYPOINT, input_wpt
            )
            character.event_handler.register_event(
                EventHandler.Event.WAYPOINT_REACHED, nearby_wpt, EventHandler.Action.ACTIVATE_SCENE, cooling_scn
            )
            character.animation.activate_scene(explode_scn)
            character.motion.activate_waypoint(nearby_wpt)
            self.animating_chars.append(character)

    def prepare_data(self) -> None:
        """Prepares the data for the effect by ___."""
        self.prepare_blackhole()

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        formation_delay = max(100 // len(self.blackhole_chars), 10)
        f_delay = formation_delay
        next_char_consuming_delay = 0
        max_consume = max(min(int(0.1 * len(self.terminal.characters)), 15), 2)
        phase = "forming"
        awaiting_blackhole_chars = list(self.blackhole_chars)
        while self.animating_chars or phase != "complete":
            if phase == "forming":
                if awaiting_blackhole_chars:
                    if not f_delay:
                        next_char = awaiting_blackhole_chars.pop(0)
                        next_char.motion.activate_waypoint(next_char.motion.waypoints["blackhole"])
                        next_char.animation.activate_scene(next_char.animation.scenes["blackhole"])
                        self.animating_chars.append(next_char)
                        f_delay = formation_delay
                    else:
                        f_delay -= 1
                else:
                    if not self.animating_chars:
                        phase = "consuming"
            elif phase == "consuming":
                if self.awaiting_consumption_chars:
                    if not next_char_consuming_delay:
                        for _ in range(random.randrange(1, max_consume)):
                            if self.awaiting_consumption_chars:
                                next_char = self.awaiting_consumption_chars.pop(0)
                                next_char.motion.activate_waypoint(next_char.motion.waypoints["singularity"])
                                self.animating_chars.append(next_char)
                            else:
                                break
                        max_consume += 1
                        next_char_consuming_delay = random.randrange(0, 10)
                    else:
                        next_char_consuming_delay -= 1

                else:
                    if not self.animating_chars:
                        phase = "collapsing"
                if all([character.motion.active_waypoint is None for character in self.blackhole_chars]):
                    self.rotate_blackhole()
            elif phase == "collapsing":
                if all([character.motion.active_waypoint is None for character in self.blackhole_chars]):
                    self.collapse_blackhole()
                    phase = "exploding"
            elif phase == "exploding":
                if all(
                    [
                        character.motion.active_waypoint is None and character.animation.active_scene is None
                        for character in self.blackhole_chars
                    ]
                ):
                    self.explode_singularity()
                    phase = "complete"

            self.animate_chars()
            self.terminal.print()

            # remove completed chars from animating chars
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
