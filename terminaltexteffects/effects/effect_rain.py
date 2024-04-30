"""Rain characters from the top of the output area.

Classes:
    Rain: Rain characters from the top of the output area.
    RainConfig: Configuration for the Rain effect.
    RainIterator: Iterator for the Rain effect. Does not normally need to be called directly.

"""

import random
import typing
from dataclasses import dataclass

import terminaltexteffects.utils.argvalidators as argvalidators
from terminaltexteffects.engine.base_character import EffectCharacter
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import easing, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return Rain, RainConfig


@argclass(
    name="rain",
    help="Rain characters from the top of the output area.",
    description="rain | Rain characters from the top of the output area.",
    epilog=f"""{argvalidators.EASING_EPILOG} 
Example: terminaltexteffects rain --rain-symbols o . , "*" "|" --rain-colors 00315C 004C8F 0075DB 3F91D9 78B9F2 9AC8F5 B8D8F8 E3EFFC --final-gradient-stops 488bff b2e7de 57eaf7 --final-gradient-steps 12 --movement-speed 0.1-0.2 --easing IN_QUART""",
)
@dataclass
class RainConfig(ArgsDataClass):
    """Configuration for the Rain effect.

    Attributes:
        rain_colors (tuple[graphics.Color, ...]): Tuple of colors for the rain drops. Colors are randomly chosen from the tuple.
        movement_speed (tuple[float, float]): Falling speed range of the rain drops. Valid values are n > 0.
        rain_symbols (tuple[str, ...]): Tuple of symbols to use for the rain drops. Symbols are randomly chosen from the tuple.
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the final gradient.
        easing (typing.Callable): Easing function to use for character movement."""

    rain_colors: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--rain-colors"],
        type_parser=argvalidators.Color.type_parser,
        metavar=argvalidators.Color.METAVAR,
        nargs="+",
        default=("00315C", "004C8F", "0075DB", "3F91D9", "78B9F2", "9AC8F5", "B8D8F8", "E3EFFC"),
        help="List of colors for the rain drops. Colors are randomly chosen from the list.",
    )  # type: ignore[assignment]
    "tuple[graphics.Color, ...] : Tuple of colors for the rain drops. Colors are randomly chosen from the tuple."

    movement_speed: tuple[float, float] = ArgField(
        cmd_name="--movement-speed",
        type_parser=argvalidators.PositiveFloatRange.type_parser,
        default=(0.1, 0.2),
        metavar=argvalidators.PositiveFloatRange.METAVAR,
        help="Falling speed range of the rain drops.",
    )  # type: ignore[assignment]
    "tuple[float, float] : Falling speed range of the rain drops."

    rain_symbols: tuple[str, ...] = ArgField(
        cmd_name="--rain-symbols",
        type_parser=argvalidators.Symbol.type_parser,
        nargs="+",
        default=("o", ".", ",", "*", "|"),
        metavar=argvalidators.Symbol.METAVAR,
        help="Space separated list of symbols to use for the rain drops. Symbols are randomly chosen from the list.",
    )  # type: ignore[assignment]
    "tuple[str, ...] : Tuple of symbols to use for the rain drops. Symbols are randomly chosen from the tuple."

    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name="--final-gradient-stops",
        type_parser=argvalidators.Color.type_parser,
        nargs="+",
        default=("488bff", "b2e7de", "57eaf7"),
        metavar=argvalidators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[graphics.Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] : Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=argvalidators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.DIAGONAL,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]
    "graphics.Gradient.Direction : Direction of the final gradient."

    movement_easing: easing.EasingFunction = ArgField(
        cmd_name=["--movement-easing"],
        default=easing.in_quart,
        type_parser=argvalidators.Ease.type_parser,
        metavar=argvalidators.Ease.METAVAR,
        help="Easing function to use for character movement.",
    )  # type: ignore[assignment]
    "easing.EasingFunction : Easing function to use for character movement."

    @classmethod
    def get_effect_class(cls):
        return Rain


class RainIterator(BaseEffectIterator[RainConfig]):
    def __init__(self, effect: "Rain") -> None:
        super().__init__(effect)
        self._pending_chars: list[EffectCharacter] = []
        self._active_chars: list[EffectCharacter] = []
        self._group_by_row: dict[int, list[EffectCharacter | None]] = {}
        self._character_final_color_map: dict[EffectCharacter, graphics.Color] = {}
        self._build()

    def _build(self) -> None:
        final_gradient = graphics.Gradient(*self._config.final_gradient_stops, steps=self._config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self._terminal.output_area.top, self._terminal.output_area.right, self._config.final_gradient_direction
        )
        for character in self._terminal.get_characters():
            self._character_final_color_map[character] = final_gradient_mapping[character.input_coord]

        for character in self._terminal.get_characters():
            raindrop_color = random.choice(self._config.rain_colors)
            rain_scn = character.animation.new_scene()
            rain_scn.add_frame(random.choice(self._config.rain_symbols), 1, color=raindrop_color)
            raindrop_gradient = graphics.Gradient(raindrop_color, self._character_final_color_map[character], steps=7)
            fade_scn = character.animation.new_scene()
            fade_scn.apply_gradient_to_symbols(raindrop_gradient, character.input_symbol, 5)
            character.animation.activate_scene(rain_scn)
            character.motion.set_coordinate(Coord(character.input_coord.column, self._terminal.output_area.top))
            input_path = character.motion.new_path(
                speed=random.uniform(self._config.movement_speed[0], self._config.movement_speed[1]),
                ease=self._config.movement_easing,
            )
            input_path.new_waypoint(character.input_coord)

            character.event_handler.register_event(
                character.event_handler.Event.PATH_COMPLETE,
                input_path,
                character.event_handler.Action.ACTIVATE_SCENE,
                fade_scn,
            )
            character.motion.activate_path(input_path)
            self._pending_chars.append(character)
        for character in sorted(self._pending_chars, key=lambda c: c.input_coord.row):
            if character.input_coord.row not in self._group_by_row:
                self._group_by_row[character.input_coord.row] = []
            self._group_by_row[character.input_coord.row].append(character)
        self._pending_chars.clear()

    def __next__(self) -> str:
        if self._group_by_row or self._active_chars or self._pending_chars:
            if not self._pending_chars and self._group_by_row:
                self._pending_chars.extend(self._group_by_row.pop(min(self._group_by_row.keys())))  # type: ignore
            if self._pending_chars:
                for _ in range(random.randint(1, 3)):
                    if self._pending_chars:
                        next_character = self._pending_chars.pop(random.randint(0, len(self._pending_chars) - 1))
                        self._terminal.set_character_visibility(next_character, True)
                        self._active_chars.append(next_character)

                    else:
                        break
            for character in self._active_chars:
                character.tick()

            self._active_chars = [character for character in self._active_chars if character.is_active]
            return self._terminal.get_formatted_output_string()
        else:
            raise StopIteration


class Rain(BaseEffect[RainConfig]):
    """Rain characters from the top of the output area.

    Attributes:
        effect_config (PourConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.
    """

    _config_cls = RainConfig
    _iterator_cls = RainIterator

    def __init__(self, input_data: str) -> None:
        """Initialize the effect with the provided input data.

        Args:
            input_data (str): The input data to use for the effect."""
        super().__init__(input_data)
