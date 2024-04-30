"""Spotlights search the text area, illuminating characters, before converging in the center and expanding.

Classes:
    Spotlights: Spotlights search the text area, illuminating characters, before converging in the center and expanding.
    SpotlightsConfig: Configuration for the Spotlights effect.
    SpotlightsIterator: Effect iterator for the Spotlights effect. Does not normally need to be called directly.
"""

import random
import typing
from dataclasses import dataclass

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.engine import animation, motion
from terminaltexteffects.engine.base_character import EffectCharacter
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import easing, geometry, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return Spotlights, SpotlightsConfig


@argclass(
    name="spotlights",
    help="Spotlights search the text area, illuminating characters, before converging in the center and expanding.",
    description="spotlights | Spotlights search the text area, illuminating characters, before converging in the center and expanding.",
    epilog=f"""{arg_validators.EASING_EPILOG}
Example: terminaltexteffects spotlights --final-gradient-stops ab48ff e7b2b2 fffebd --final-gradient-steps 12 --beam-width-ratio 2.0 --beam-falloff 0.3 --search-duration 750 --search-speed-range 0.25-0.5 --spotlight-count 3""",
)
@dataclass
class SpotlightsConfig(ArgsDataClass):
    """Configuration for the Spotlights effect.

    Attributes:
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the final gradient.
        beam_width_ratio (float): Width of the beam of light as min(width, height) // n of the input text. Valid values are n > 0.
        beam_falloff (float): Distance from the edge of the beam where the brightness begins to fall off, as a percentage of total beam width. Valid values are 0 <= n <= 1.
        search_duration (int): Duration of the search phase, in frames, before the spotlights converge in the center. Valid values are n > 0.
        search_speed_range (tuple[float, float]): Range of speeds for the spotlights during the search phase. The speed is a random value between the two provided values. Valid values are n > 0.
        spotlight_count (int): Number of spotlights to use. Valid values are n > 0.
    """

    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("ab48ff", "e7b2b2", "fffebd"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[graphics.Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color."

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
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]
    "graphics.Gradient.Direction : Direction of the final gradient."

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
        help="Duration of the search phase, in frames, before the spotlights converge in the center.",
    )  # type: ignore[assignment]
    "int : Duration of the search phase, in frames, before the spotlights converge in the center."

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
        return Spotlights


class SpotlightsIterator(BaseEffectIterator[SpotlightsConfig]):
    def __init__(self, effect: "Spotlights") -> None:
        super().__init__(effect)
        self._pending_chars: list[EffectCharacter] = []
        self._active_chars: list[EffectCharacter] = []
        self._illuminated_chars: set[EffectCharacter] = set()
        self._character_color_map: dict[EffectCharacter, tuple[graphics.Color, graphics.Color]] = {}  # (bright, dark)
        self._build()

    def _make_spotlights(self, num_spotlights: int) -> list[EffectCharacter]:
        spotlights: list[EffectCharacter] = []
        minimum_distance = self._terminal.output_area.right // 4
        for _ in range(num_spotlights):
            spotlight = self._terminal.add_character("O", self._terminal.output_area.random_coord(outside_scope=True))
            spotlights.append(spotlight)

            spotlight_target_coords: list[Coord] = []
            last_coord = self._terminal.output_area.random_coord()
            spotlight_target_coords.append(last_coord)
            for _ in range(10):
                next_coord = self._find_coord_at_minimum_distance(last_coord, minimum_distance)
                spotlight_target_coords.append(next_coord)
                last_coord = next_coord

            paths: list[motion.Path] = []
            for coord in spotlight_target_coords:
                path = spotlight.motion.new_path(
                    speed=random.uniform(self._config.search_speed_range[0], self._config.search_speed_range[1]),
                    ease=easing.in_out_quad,
                    id=str(len(paths)),
                )
                path.new_waypoint(coord, bezier_control=self._terminal.output_area.random_coord(outside_scope=True))
                paths.append(path)
            spotlight.motion.chain_paths(paths, loop=True)

            path = spotlight.motion.new_path(speed=0.5, ease=easing.in_out_sine, id="center")
            path.new_waypoint(self._terminal.output_area.center)

        return spotlights

    def _find_coord_at_minimum_distance(self, origin_coord: Coord, minimum_distance: int) -> Coord:
        coord_found = False
        while not coord_found:
            coord = self._terminal.output_area.random_coord()
            distance = geometry.find_length_of_line(origin_coord, coord)
            if distance >= minimum_distance:
                coord_found = True
        return coord

    def _illuminate_chars(self, range: int) -> None:
        coords_in_range: list[Coord] = []
        for spotlight in self._spotlights:
            coords_in_range.extend(geometry.find_coords_in_circle(spotlight.motion.current_coord, range))
        chars_in_range: set[EffectCharacter] = set()
        for coord in coords_in_range:
            character = self._terminal.get_character_by_input_coord(coord)
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

            if distance > range * (1 - self._config.beam_falloff):
                brightness_factor = max(
                    1 - (distance - range * (1 - self._config.beam_falloff)) / (range * self._config.beam_falloff), 0.2
                )
                adjusted_color = animation.Animation.adjust_color_brightness(
                    self._character_color_map[character][0], brightness_factor
                )
            else:
                adjusted_color = self._character_color_map[character][0]
            character.animation.set_appearance(character.input_symbol, adjusted_color)
        self._illuminated_chars = chars_in_range

    def _build(self) -> None:
        self._spotlights: list[EffectCharacter] = self._make_spotlights(self._config.spotlight_count)
        final_gradient = graphics.Gradient(*self._config.final_gradient_stops, steps=self._config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self._terminal.output_area.top, self._terminal.output_area.right, self._config.final_gradient_direction
        )
        for character in self._terminal.get_characters():
            color_bright = final_gradient_mapping[character.input_coord]
            self._terminal.set_character_visibility(character, True)
            color_dark = animation.Animation.adjust_color_brightness(color_bright, 0.2)
            self._character_color_map[character] = (color_bright, color_dark)
            character.animation.set_appearance(character.input_symbol, color_dark)
        self._illuminate_range = int(
            max(
                min(self._terminal.output_area.right, self._terminal.output_area.top) // self._config.beam_width_ratio,
                1,
            )
        )
        self._search_duration = self._config.search_duration
        self._searching = True
        self._complete = False
        for spotlight in self._spotlights:
            spotlight_path_start = spotlight.motion.query_path("0")
            spotlight.motion.activate_path(spotlight_path_start)
            self._active_chars.append(spotlight)

    def __next__(self) -> str:
        if not self._complete:
            self._illuminate_chars(self._illuminate_range)
            if self._searching:
                self._search_duration -= 1
                if not self._search_duration:
                    for spotlight in self._spotlights:
                        spotlight_path_center = spotlight.motion.query_path("center")
                        spotlight.motion.activate_path(spotlight_path_center)
                    self._searching = False
            if not any([spotlight.motion.active_path for spotlight in self._spotlights]):
                while len(self._spotlights) > 1:
                    self._spotlights.pop()
                self._illuminate_range += 1
                if (
                    self._illuminate_range
                    > max(self._terminal.output_area.right, self._terminal.output_area.top) // 1.5
                ):
                    self._complete = True

            for character in self._active_chars:
                character.tick()
            return self._terminal.get_formatted_output_string()
        else:
            raise StopIteration


class Spotlights(BaseEffect[SpotlightsConfig]):
    """Spotlights search the text area, illuminating characters, before converging in the center and expanding.

    Attributes:
        effect_config (SpotlightsConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.
    """

    _config_cls = SpotlightsConfig
    _iterator_cls = SpotlightsIterator

    def __init__(self, input_data: str) -> None:
        """Initialize the effect with the provided input data.

        Args:
            input_data (str): The input data to use for the effect."""
        super().__init__(input_data)
