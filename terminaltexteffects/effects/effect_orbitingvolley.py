import argparse
from itertools import cycle

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
        "orbittingvolley",
        formatter_class=argtypes.CustomFormatter,
        help="Four launchers orbit the output area firing volleys of characters inward to build the input text from the center out.",
        description="Four launchers orbit the output area firing volleys of characters inward to build the input text from the center out.",
        epilog=f"""{argtypes.EASING_EPILOG}

Example: terminaltexteffects orbittingvolley -a 0.01 --top-launcher-symbol █ --right-launcher-symbol █ --bottom-launcher-symbol █ --left-launcher-symbol █ --final-gradient-stops ffa51f ffa51f 6177b3 6177b3 --final-gradient-steps 6 8 10 --launcher-movement-speed 0.5 --character-movement-speed 1 --volley-size 0.03 --launch-delay 50 --character-easing OUT_SINE""",
    )
    effect_parser.set_defaults(effect_class=OrbittingVolleyEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.nonnegative_float,
        default=0.01,
        help="Minimum time, in seconds, between animation steps. This value does not normally need to be modified. Use this to increase the playback speed of all aspects of the effect. This will have no impact beyond a certain lower threshold due to the processing speed of your device.",
    )
    effect_parser.add_argument(
        "--top-launcher-symbol",
        type=argtypes.symbol,
        default="█",
        metavar="(single character)",
        help="Symbol for the top launcher.",
    )
    effect_parser.add_argument(
        "--right-launcher-symbol",
        type=argtypes.symbol,
        default="█",
        metavar="(single character)",
        help="Symbol for the right launcher.",
    )
    effect_parser.add_argument(
        "--bottom-launcher-symbol",
        type=argtypes.symbol,
        default="█",
        metavar="(single character)",
        help="Symbol for the bottom launcher.",
    )
    effect_parser.add_argument(
        "--left-launcher-symbol",
        type=argtypes.symbol,
        default="█",
        metavar="(single character)",
        help="Symbol for the left launcher.",
    )
    effect_parser.add_argument(
        "--final-gradient-stops",
        type=argtypes.color,
        nargs="+",
        default=["ffa51f", "ffa51f", "6177b3", "6177b3"],
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Space separated, unquoted, list of colors for the wipe gradient.",
    )
    effect_parser.add_argument(
        "--final-gradient-steps",
        type=argtypes.positive_int,
        nargs="+",
        default=[6, 8, 10],
        metavar="(int > 0)",
        help="Number of gradient steps to use. More steps will create a smoother and longer gradient animation. Steps are paired with the colors in --final-gradient-stops.",
    )
    effect_parser.add_argument(
        "--launcher-movement-speed",
        type=argtypes.positive_float,
        default=0.5,
        metavar="(float > 0)",
        help="Speed of the ___.",
    )
    effect_parser.add_argument(
        "--character-movement-speed",
        type=argtypes.positive_float,
        default=1,
        metavar="(float > 0)",
        help="Speed of the ___.",
    )
    effect_parser.add_argument(
        "--volley-size",
        type=argtypes.positive_float,
        default=0.03,
        metavar="(float > 0)",
        help="Percent of total input characters each launcher will fire per volley. Auto lower limit of one character.",
    )
    effect_parser.add_argument(
        "--launch-delay",
        type=argtypes.nonnegative_int,
        default=50,
        metavar="(int >= 0)",
        help="Number of animation ticks to wait between volleys of characters.",
    )
    effect_parser.add_argument(
        "--character-easing",
        default="OUT_SINE",
        type=argtypes.ease,
        help="Easing function to use for launched character movement.",
    )


class Launcher:
    def __init__(self, terminal: Terminal, args: argparse.Namespace, starting_edge_coord: Coord, symbol: str):
        self.terminal = terminal
        self.args = args
        self.character = self.terminal.add_character(symbol, starting_edge_coord)
        self.magazine: list[EffectCharacter] = []

    def build_paths(self) -> None:
        waypoints = [
            Coord(self.terminal.output_area.left, self.terminal.output_area.top),
            Coord(self.terminal.output_area.right, self.terminal.output_area.top),
        ]

        waypoint_start_index = waypoints.index(self.character.input_coord)
        perimeter_path = self.character.motion.new_path(
            speed=self.args.launcher_movement_speed, id="perimeter", layer=2
        )
        for waypoint in waypoints[waypoint_start_index:] + waypoints[:waypoint_start_index]:
            perimeter_path.new_waypoint(waypoint)

    def launch(self) -> EffectCharacter | None:
        if self.magazine:
            next_char = self.magazine.pop(0)
            next_char.motion.set_coordinate(self.character.motion.current_coord)
            input_path = next_char.motion.query_path("input_path")
            next_char.motion.activate_path(input_path)
            self.terminal.set_character_visibility(next_char, True)
        else:
            next_char = None
        return next_char


class OrbittingVolleyEffect:
    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.final_gradient = graphics.Gradient(self.args.final_gradient_stops, self.args.final_gradient_steps)

    def prepare_data(self) -> None:
        for character in self.terminal.get_characters():
            input_path = character.motion.new_path(
                speed=self.args.character_movement_speed, ease=self.args.character_easing, id="input_path", layer=1
            )
            input_path.new_waypoint(character.input_coord)
            character_height_ratio = character.input_coord.row / self.terminal.output_area.top
            character.animation.set_appearance(
                character.input_symbol, self.final_gradient.get_color_at_fraction(character_height_ratio)
            )

    def set_launcher_coordinates(self, parent: Launcher, child: Launcher) -> None:
        """Sets the coordinates for the child launcher."""
        parent_progress = parent.character.motion.current_coord.column / self.terminal.output_area.right
        if child.character.input_coord == Coord(self.terminal.output_area.right, self.terminal.output_area.top):
            child_row = self.terminal.output_area.top - int((self.terminal.output_area.top * parent_progress))
            child.character.motion.set_coordinate(Coord(self.terminal.output_area.right, max(1, child_row)))
        elif child.character.input_coord == Coord(self.terminal.output_area.right, self.terminal.output_area.bottom):
            child_column = self.terminal.output_area.right - int((self.terminal.output_area.right * parent_progress))
            child.character.motion.set_coordinate(Coord(max(1, child_column), self.terminal.output_area.bottom))
        elif child.character.input_coord == Coord(self.terminal.output_area.left, self.terminal.output_area.bottom):
            child_row = self.terminal.output_area.bottom + int((self.terminal.output_area.top * parent_progress))
            child.character.motion.set_coordinate(
                Coord(self.terminal.output_area.left, min(self.terminal.output_area.top, child_row))
            )
        color = self.final_gradient.get_color_at_fraction(
            child.character.motion.current_coord.row / self.terminal.output_area.top
        )
        child.character.animation.set_appearance(child.character.input_symbol, color)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        launchers: list[Launcher] = []
        for coord, symbol in (
            (
                Coord(self.terminal.output_area.left, self.terminal.output_area.top),
                self.args.top_launcher_symbol,
            ),
            (
                Coord(self.terminal.output_area.right, self.terminal.output_area.top),
                self.args.right_launcher_symbol,
            ),
            (
                Coord(self.terminal.output_area.right, self.terminal.output_area.bottom),
                self.args.bottom_launcher_symbol,
            ),
            (
                Coord(self.terminal.output_area.left, self.terminal.output_area.bottom),
                self.args.left_launcher_symbol,
            ),
        ):
            launcher = Launcher(self.terminal, self.args, coord, symbol)
            launcher.character.layer = 2
            self.terminal.set_character_visibility(launcher.character, True)
            self.active_chars.append(launcher.character)
            launchers.append(launcher)
        main_launcher = launchers[0]
        main_launcher.character.animation.set_appearance(
            main_launcher.character.input_symbol, self.final_gradient.spectrum[-1]
        )
        main_launcher.build_paths()
        main_launcher.character.motion.activate_path(main_launcher.character.motion.query_path("perimeter"))
        sorted_chars = []
        for char_list in self.terminal.get_characters_grouped(Terminal.CharacterGroup.CENTER_TO_OUTSIDE_DIAMONDS):
            sorted_chars.extend(char_list)
        for launcher, character in zip(cycle(launchers), sorted_chars):
            launcher.magazine.append(character)
        delay = 0
        while any([launcher.magazine for launcher in launchers]) or len(self.active_chars) > 1:
            if main_launcher.character.motion.active_path is None:
                perimeter_path = main_launcher.character.motion.query_path("perimeter")
                main_launcher.character.motion.set_coordinate(perimeter_path.waypoints[0].coord)
                main_launcher.character.motion.activate_path(perimeter_path)
                self.active_chars.append(main_launcher.character)
            for launcher in launchers[1:]:
                self.set_launcher_coordinates(main_launcher, launcher)
            if not delay:
                for launcher in launchers:
                    characters_to_launch = max(
                        int((self.args.volley_size * len(self.terminal._input_characters)) / 4), 1
                    )
                    for _ in range(characters_to_launch):
                        next_char = launcher.launch()
                        if next_char:
                            self.active_chars.append(next_char)
                delay = self.args.launch_delay
            else:
                delay -= 1

            self.terminal.print()
            self.animate_chars()
            self.active_chars = [character for character in self.active_chars if character.is_active]
        for launcher in launchers:
            self.terminal.set_character_visibility(launcher.character, False)
            self.terminal.print()

    def animate_chars(self) -> None:
        """Animates the characters by calling the tick method on all active characters."""
        for character in self.active_chars:
            character.tick()
