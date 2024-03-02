import argparse
import random

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils import easing, geometry, graphics, motion
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.terminal import Terminal


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "spotlights",
        formatter_class=argtypes.CustomFormatter,
        help="Spotlights search the text area, illuminating characters, before converging in the center and expanding.",
        description="Spotlights search the text area, illuminating characters, before converging in the center and expanding.",
        epilog=f"""{argtypes.EASING_EPILOG}

Example: terminaltexteffects spotlights -a 0.01 --gradient-stops 8A008A 00D1FF FFFFFF --gradient-steps 12 --beam-width-ratio 2 --beam-falloff 0.3 --search-duration 750 --search-speed-range 0.25-0.5""",
    )
    effect_parser.set_defaults(effect_class=SpotlightsEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.nonnegative_float,
        default=0.01,
        help="Minimum time, in seconds, between animation steps. This value does not normally need to be modified. Use this to increase the playback speed of all aspects of the effect. This will have no impact beyond a certain lower threshold due to the processing speed of your device.",
    )
    effect_parser.add_argument(
        "--gradient-stops",
        type=argtypes.color,
        nargs="*",
        default=["8A008A", "00D1FF", "FFFFFF"],
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )
    effect_parser.add_argument(
        "--gradient-steps",
        type=argtypes.positive_int,
        nargs="*",
        default=[12],
        metavar="(int > 0)",
        help="Number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )
    effect_parser.add_argument(
        "--beam-width-ratio",
        type=argtypes.positive_float,
        default=2.0,
        metavar="(float > 0)",
        help="Width of the beam of light as min(width, height) // n of the input text.",
    )
    effect_parser.add_argument(
        "--beam-falloff",
        type=argtypes.nonnegative_float,
        default=0.3,
        metavar="(float >= 0)",
        help="Distance from the edge of the beam where the brightness begins to fall off, as a percentage of total beam width.",
    )
    effect_parser.add_argument(
        "--search-duration",
        type=argtypes.positive_int,
        default=750,
        metavar="(int > 0)",
        help="Duration of the search phase, in animation steps, before the spotlights converge in the center.",
    )
    effect_parser.add_argument(
        "--search-speed-range",
        type=argtypes.float_range,
        default=(0.25, 0.5),
        metavar="(e.g. 0.25-0.5)",
        help="Range of speeds for the spotlights during the search phase. The speed is a random value between the two provided values.",
    )
    effect_parser.add_argument(
        "--spotlight-count",
        type=argtypes.positive_int,
        default=3,
        metavar="(int > 0)",
        help="Number of spotlights to use.",
    )


class SpotlightsEffect:
    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.spotlights: list[EffectCharacter] = self.make_spotlights(self.args.spotlight_count)
        self.illuminated_chars: set[EffectCharacter] = set()
        self.character_color_map: dict[EffectCharacter, tuple[graphics.Color, graphics.Color]] = {}  # (bright, dark)

    def make_spotlights(self, num_spotlights: int) -> list[EffectCharacter]:
        spotlights: list[EffectCharacter] = []
        minimum_distance = self.terminal.output_area.right // 4
        for _ in range(num_spotlights):
            spotlight = self.terminal.add_character("O", self.terminal.output_area.random_coord(outside_scope=True))
            spotlights.append(spotlight)

            spotlight_target_coords: list[Coord] = []
            last_coord = self.terminal.output_area.random_coord()
            spotlight_target_coords.append(last_coord)
            for _ in range(10):
                next_coord = self.find_coord_at_minimum_distance(last_coord, minimum_distance)
                spotlight_target_coords.append(next_coord)
                last_coord = next_coord

            paths: list[motion.Path] = []
            for coord in spotlight_target_coords:
                path = spotlight.motion.new_path(
                    speed=random.uniform(self.args.search_speed_range[0], self.args.search_speed_range[1]),
                    ease=easing.in_out_quad,
                    id=str(len(paths)),
                )
                path.new_waypoint(coord, bezier_control=self.terminal.output_area.random_coord(outside_scope=True))
                paths.append(path)
            spotlight.motion.chain_paths(paths, loop=True)

            path = spotlight.motion.new_path(speed=0.5, ease=easing.in_out_sine, id="center")
            path.new_waypoint(self.terminal.output_area.center)

        return spotlights

    def find_coord_at_minimum_distance(self, origin_coord: Coord, minimum_distance: int) -> Coord:
        coord_found = False
        while not coord_found:
            coord = self.terminal.output_area.random_coord()
            distance = geometry.find_length_of_line(origin_coord, coord)
            if distance >= minimum_distance:
                coord_found = True
        return coord

    def illuminate_chars(self, range: int) -> None:
        coords_in_range: list[Coord] = []
        for spotlight in self.spotlights:
            coords_in_range.extend(geometry.find_coords_in_circle(spotlight.motion.current_coord, range))
        chars_in_range: set[EffectCharacter] = set()
        for coord in coords_in_range:
            character = self.terminal.get_character_by_input_coord(coord)
            if character:
                chars_in_range.add(character)
        chars_no_longer_in_range = self.illuminated_chars - chars_in_range
        for character in chars_no_longer_in_range:
            character.animation.set_appearance(
                character.input_symbol,
                self.character_color_map[character][1],
            )

        for character in chars_in_range:
            distance = min(
                [
                    geometry.find_length_of_line(
                        spotlight.motion.current_coord, character.input_coord, double_row_diff=True
                    )
                    for spotlight in self.spotlights
                ]
            )

            if distance > range * (1 - self.args.beam_falloff):
                brightness_factor = max(
                    1 - (distance - range * (1 - self.args.beam_falloff)) / (range * self.args.beam_falloff), 0.2
                )
                adjusted_color = graphics.Animation.adjust_color_brightness(
                    self.character_color_map[character][0], brightness_factor
                )
            else:
                adjusted_color = self.character_color_map[character][0]
            character.animation.set_appearance(character.input_symbol, adjusted_color)
        self.illuminated_chars = chars_in_range

    def prepare_data(self) -> None:
        base_gradient = graphics.Gradient(self.args.gradient_stops, self.args.gradient_steps)
        for character in self.terminal.get_characters():
            color_bright = base_gradient.get_color_at_fraction(
                character.input_coord.row / self.terminal.output_area.top
            )
            self.terminal.set_character_visibility(character, True)
            color_dark = graphics.Animation.adjust_color_brightness(color_bright, 0.2)
            self.character_color_map[character] = (color_bright, color_dark)
            character.animation.set_appearance(character.input_symbol, color_dark)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        illuminate_range = int(
            max(min(self.terminal.output_area.right, self.terminal.output_area.top) // self.args.beam_width_ratio, 1)
        )
        search_duration = self.args.search_duration
        searching = True
        complete = False
        for spotlight in self.spotlights:
            spotlight_path_start = spotlight.motion.query_path("0")
            spotlight.motion.activate_path(spotlight_path_start)
            self.active_chars.append(spotlight)
        while not complete:
            self.illuminate_chars(illuminate_range)
            if searching:
                search_duration -= 1
                if not search_duration:
                    for spotlight in self.spotlights:
                        spotlight_path_center = spotlight.motion.query_path("center")
                        spotlight.motion.activate_path(spotlight_path_center)
                    searching = False
            if not any([spotlight.motion.active_path for spotlight in self.spotlights]):
                while len(self.spotlights) > 1:
                    self.spotlights.pop()
                illuminate_range += 1
                if illuminate_range > max(self.terminal.output_area.right, self.terminal.output_area.top) // 1.5:
                    complete = True

            self.terminal.print()
            self.animate_chars()

    def animate_chars(self) -> None:
        """Animates the characters by calling the tick method on all active characters."""
        for character in self.active_chars:
            character.tick()
