import random
import typing
from collections.abc import Iterator
from dataclasses import dataclass

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils import animation, easing, geometry, graphics, motion
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.terminal import Terminal, TerminalConfig


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return SpotlightsEffect, EffectConfig


@argclass(
    name="spotlights",
    help="Spotlights search the text area, illuminating characters, before converging in the center and expanding.",
    description="spotlights | Spotlights search the text area, illuminating characters, before converging in the center and expanding.",
    epilog=f"""{arg_validators.EASING_EPILOG}
Example: terminaltexteffects spotlights --final-gradient-stops ab48ff e7b2b2 fffebd --final-gradient-steps 12 --beam-width-ratio 2.0 --beam-falloff 0.3 --search-duration 750 --search-speed-range 0.25-0.5 --spotlight-count 3""",
)
@dataclass
class EffectConfig(ArgsDataClass):
    """Configuration for the Spotlights effect.

    Attributes:
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the gradient for the final color.
        beam_width_ratio (float): Width of the beam of light as min(width, height) // n of the input text.
        beam_falloff (float): Distance from the edge of the beam where the brightness begins to fall off, as a percentage of total beam width.
        search_duration (int): Duration of the search phase, in animation steps, before the spotlights converge in the center.
        search_speed_range (tuple[float, float]): Range of speeds for the spotlights during the search phase. The speed is a random value between the two provided values.
        spotlight_count (int): Number of spotlights to use.
    """

    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("ab48ff", "e7b2b2", "fffebd"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[graphics.Color, ...] : Tuple of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=arg_validators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] : Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=arg_validators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.VERTICAL,
        metavar=arg_validators.GradientDirection.METAVAR,
        help="Direction of the gradient for the final color.",
    )  # type: ignore[assignment]
    "graphics.Gradient.Direction : Direction of the gradient for the final color."

    beam_width_ratio: float = ArgField(
        cmd_name="--beam-width-ratio",
        type_parser=arg_validators.PositiveFloat.type_parser,
        default=2.0,
        metavar=arg_validators.PositiveFloat.METAVAR,
        help="Width of the beam of light as min(width, height) // n of the input text.",
    )  # type: ignore[assignment]
    "float : Width of the beam of light as min(width, height) // n of the input text."

    beam_falloff: float = ArgField(
        cmd_name="--beam-falloff",
        type_parser=arg_validators.NonNegativeFloat.type_parser,
        default=0.3,
        metavar=arg_validators.NonNegativeFloat.METAVAR,
        help="Distance from the edge of the beam where the brightness begins to fall off, as a percentage of total beam width.",
    )  # type: ignore[assignment]
    "float : Distance from the edge of the beam where the brightness begins to fall off, as a percentage of total beam width."

    search_duration: int = ArgField(
        cmd_name="--search-duration",
        type_parser=arg_validators.PositiveInt.type_parser,
        default=750,
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Duration of the search phase, in animation steps, before the spotlights converge in the center.",
    )  # type: ignore[assignment]
    "int : Duration of the search phase, in animation steps, before the spotlights converge in the center."

    search_speed_range: tuple[float, float] = ArgField(
        cmd_name="--search-speed-range",
        type_parser=arg_validators.PositiveFloatRange.type_parser,
        default=(0.25, 0.5),
        metavar=arg_validators.PositiveFloatRange.METAVAR,
        help="Range of speeds for the spotlights during the search phase. The speed is a random value between the two provided values.",
    )  # type: ignore[assignment]
    "tuple[float, float] : Range of speeds for the spotlights during the search phase. The speed is a random value between the two provided values."

    spotlight_count: int = ArgField(
        cmd_name="--spotlight-count",
        type_parser=arg_validators.PositiveInt.type_parser,
        default=3,
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Number of spotlights to use.",
    )  # type: ignore[assignment]
    "int : Number of spotlights to use."

    @classmethod
    def get_effect_class(cls):
        return SpotlightsEffect


class SpotlightsEffect:
    def __init__(
        self,
        input_data: str,
        effect_config: EffectConfig = EffectConfig(),
        terminal_config: TerminalConfig = TerminalConfig(),
    ):
        """Initializes the effect.

        Args:
            input_data (str): The input data to apply the effect to.
            effect_config (EffectConfig): The configuration for the effect.
            terminal_config (TerminalConfig): The configuration for the terminal.
        """
        self.terminal = Terminal(input_data, terminal_config)
        self.config = effect_config
        self._built = False
        self._pending_chars: list[EffectCharacter] = []
        self._active_chars: list[EffectCharacter] = []
        self._illuminated_chars: set[EffectCharacter] = set()
        self._character_color_map: dict[EffectCharacter, tuple[graphics.Color, graphics.Color]] = {}  # (bright, dark)

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
                    speed=random.uniform(self.config.search_speed_range[0], self.config.search_speed_range[1]),
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
        for spotlight in self._spotlights:
            coords_in_range.extend(geometry.find_coords_in_circle(spotlight.motion.current_coord, range))
        chars_in_range: set[EffectCharacter] = set()
        for coord in coords_in_range:
            character = self.terminal.get_character_by_input_coord(coord)
            if character and character.symbol != " ":
                chars_in_range.add(character)
        chars_no_longer_in_range = self._illuminated_chars - chars_in_range
        for character in chars_no_longer_in_range:
            character.animation.set_appearance(
                character.input_symbol,
                self._character_color_map[character][1],
            )

        for character in chars_in_range:
            distance = min(
                [
                    geometry.find_length_of_line(
                        spotlight.motion.current_coord, character.input_coord, double_row_diff=True
                    )
                    for spotlight in self._spotlights
                ]
            )

            if distance > range * (1 - self.config.beam_falloff):
                brightness_factor = max(
                    1 - (distance - range * (1 - self.config.beam_falloff)) / (range * self.config.beam_falloff), 0.2
                )
                adjusted_color = animation.Animation.adjust_color_brightness(
                    self._character_color_map[character][0], brightness_factor
                )
            else:
                adjusted_color = self._character_color_map[character][0]
            character.animation.set_appearance(character.input_symbol, adjusted_color)
        self._illuminated_chars = chars_in_range

    def build(self) -> None:
        self._pending_chars.clear()
        self._active_chars.clear()
        self._character_color_map.clear()
        self._illuminated_chars.clear()
        self._spotlights: list[EffectCharacter] = self.make_spotlights(self.config.spotlight_count)
        final_gradient = graphics.Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.config.final_gradient_direction
        )
        for character in self.terminal.get_characters():
            color_bright = final_gradient_mapping[character.input_coord]
            self.terminal.set_character_visibility(character, True)
            color_dark = animation.Animation.adjust_color_brightness(color_bright, 0.2)
            self._character_color_map[character] = (color_bright, color_dark)
            character.animation.set_appearance(character.input_symbol, color_dark)
        self._built = True

    @property
    def built(self) -> bool:
        """Returns True if the effect has been built."""
        return self._built

    def __iter__(self) -> Iterator[str]:
        """Runs the effect."""
        if not self._built:
            self.build()
        illuminate_range = int(
            max(min(self.terminal.output_area.right, self.terminal.output_area.top) // self.config.beam_width_ratio, 1)
        )
        search_duration = self.config.search_duration
        searching = True
        complete = False
        for spotlight in self._spotlights:
            spotlight_path_start = spotlight.motion.query_path("0")
            spotlight.motion.activate_path(spotlight_path_start)
            self._active_chars.append(spotlight)
        while not complete:
            self.illuminate_chars(illuminate_range)
            if searching:
                search_duration -= 1
                if not search_duration:
                    for spotlight in self._spotlights:
                        spotlight_path_center = spotlight.motion.query_path("center")
                        spotlight.motion.activate_path(spotlight_path_center)
                    searching = False
            if not any([spotlight.motion.active_path for spotlight in self._spotlights]):
                while len(self._spotlights) > 1:
                    self._spotlights.pop()
                illuminate_range += 1
                if illuminate_range > max(self.terminal.output_area.right, self.terminal.output_area.top) // 1.5:
                    complete = True

            yield self.terminal.get_formatted_output_string()
            self._animate_chars()
        self._built = False

    def _animate_chars(self) -> None:
        """Animates the characters by calling the tick method on all active characters."""
        for character in self._active_chars:
            character.tick()
