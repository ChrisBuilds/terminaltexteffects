import argparse
import random

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils import graphics
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.terminal import Terminal


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "unstable",
        formatter_class=argtypes.CustomFormatter,
        help="Spawn characters jumbled, explode them to the edge of the output area, then reassemble them in the correct layout.",
        description="unstable | Spawn characters jumbled, explode them to the edge of the output area, then reassemble them in the correct layout.",
        epilog=f"""{argtypes.EASING_EPILOG}

Example: terminaltexteffects unstable --unstable-color ff9200 --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --explosion-ease OUT_EXPO --explosion-speed 0.75 --reassembly-ease OUT_EXPO --reassembly-speed 0.75""",
    )
    effect_parser.set_defaults(effect_class=UnstableEffect)
    effect_parser.add_argument(
        "--unstable-color",
        type=argtypes.color,
        default="ff9200",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color transitioned to as the characters become unstable.",
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
        "--explosion-ease",
        default="OUT_EXPO",
        type=argtypes.ease,
        help="Easing function to use for character movement during the explosion.",
    )
    effect_parser.add_argument(
        "--explosion-speed",
        type=argtypes.positive_float,
        default=0.75,
        metavar="(float > 0)",
        help="Speed of characters during explosion. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )
    effect_parser.add_argument(
        "--reassembly-ease",
        default="OUT_EXPO",
        type=argtypes.ease,
        help="Easing function to use for character reassembly.",
    )
    effect_parser.add_argument(
        "--reassembly-speed",
        type=argtypes.positive_float,
        default=0.75,
        metavar="(float > 0)",
        help="Speed of characters during reassembly. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )


class UnstableEffect:
    """Effect that spawns characters jumbled, explodes them to the edge of the output area,
    then reassembles them in the correct layout."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.jumbled_coords: dict[EffectCharacter, Coord] = dict()
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def prepare_data(self) -> None:
        """Prepares the data for the effect by jumbling the character positions and
        choosing a location on the perimeter of the output area for the character to travel
        after exploding. Creates all waypoints and scenes for the characters."""
        final_gradient = graphics.Gradient(self.args.final_gradient_stops, self.args.final_gradient_steps)

        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient.get_color_at_fraction(
                character.input_coord.row / self.terminal.output_area.top
            )

        character_coords = [character.input_coord for character in self.terminal.get_characters()]
        for character in self.terminal.get_characters():
            pos = random.randint(0, 3)
            match pos:
                case 0:
                    col = self.terminal.output_area.left
                    row = random.randint(1, self.terminal.output_area.top)
                case 1:
                    col = self.terminal.output_area.right
                    row = random.randint(1, self.terminal.output_area.top)
                case 2:
                    col = random.randint(1, self.terminal.output_area.right)
                    row = self.terminal.output_area.bottom
                case 3:
                    col = random.randint(1, self.terminal.output_area.right)
                    row = self.terminal.output_area.top
            jumbled_coord = character_coords.pop(random.randint(0, len(character_coords) - 1))
            self.jumbled_coords[character] = jumbled_coord
            character.motion.set_coordinate(jumbled_coord)
            explosion_path = character.motion.new_path(id="explosion", speed=1.25, ease=self.args.explosion_ease)
            explosion_path.new_waypoint(Coord(col, row))
            reassembly_path = character.motion.new_path(id="reassembly", speed=0.75, ease=self.args.reassembly_ease)
            reassembly_path.new_waypoint(character.input_coord)
            unstable_gradient = graphics.Gradient(
                [self.character_final_color_map[character], self.args.unstable_color], 25
            )
            rumble_scn = character.animation.new_scene(id="rumble")
            rumble_scn.apply_gradient_to_symbols(
                unstable_gradient,
                character.input_symbol,
                10,
            )
            final_color = graphics.Gradient([self.args.unstable_color, self.character_final_color_map[character]], 12)
            final_scn = character.animation.new_scene(id="final")
            final_scn.apply_gradient_to_symbols(final_color, character.input_symbol, 5)
            character.animation.activate_scene(rumble_scn)
            self.terminal.set_character_visibility(character, True)

    def move_all_to_waypoint(self, path_id) -> None:
        for character in self.terminal.get_characters():
            if path_id == "reassembly":
                character.animation.activate_scene(character.animation.query_scene("final"))
            self.active_chars.append(character)
            character.motion.activate_path(character.motion.query_path(path_id))
        while self.active_chars:
            self.terminal.print()
            self.animate_chars()
            if path_id == "reassembly":
                self.active_chars = [
                    character
                    for character in self.active_chars
                    if not character.motion.current_coord == character.motion.query_path(path_id).waypoints[0].coord
                    or not character.animation.active_scene_is_complete()
                ]
            else:
                self.active_chars = [
                    character
                    for character in self.active_chars
                    if not character.motion.current_coord == character.motion.query_path(path_id).waypoints[0].coord
                ]

    def rumble(self) -> None:
        max_rumble_steps = 250
        current_rumble_steps = 0
        rumble_mod_delay = 20
        while current_rumble_steps < max_rumble_steps:
            if current_rumble_steps > 30 and current_rumble_steps % rumble_mod_delay == 0:
                row_offset = random.choice([-1, 0, 1])
                column_offset = random.choice([-1, 0, 1])
                for character in self.terminal.get_characters():
                    character.motion.set_coordinate(
                        Coord(
                            character.motion.current_coord.column + column_offset,
                            character.motion.current_coord.row + row_offset,
                        )
                    )
                    character.animation.step_animation()
                self.terminal.print()
                for character in self.terminal.get_characters():
                    character.motion.set_coordinate(self.jumbled_coords[character])
                rumble_mod_delay -= 1
                rumble_mod_delay = max(rumble_mod_delay, 1)
            else:
                for character in self.terminal.get_characters():
                    character.animation.step_animation()
                self.terminal.print()

            current_rumble_steps += 1

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        explosion_hold_time = 50
        self.rumble()
        self.move_all_to_waypoint("explosion")
        while explosion_hold_time:
            self.terminal.print()
            self.animate_chars()
            explosion_hold_time -= 1
        self.move_all_to_waypoint("reassembly")

    def animate_chars(self) -> None:
        """Animates the characters by calling the tick method."""
        for character in self.active_chars:
            character.tick()
