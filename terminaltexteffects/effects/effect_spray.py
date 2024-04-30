"""Sprays the characters from a single point.

Classes:
    Spray: Sprays the characters from a single point.
    SprayConfig: Configuration for the Spray effect.
    SprayIterator: Iterates over the effect. Does not normally need to be called directly.
"""

import random
import typing
from dataclasses import dataclass
from enum import Enum, auto

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.engine.base_character import EffectCharacter, EventHandler
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import easing, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return Spray, SprayConfig


@argclass(
    name="spray",
    help="Draws the characters spawning at varying rates from a single point.",
    description="spray | Draws the characters spawning at varying rates from a single point.",
    epilog=f"""{arg_validators.EASING_EPILOG}    
Example: terminaltexteffects spray --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --spray-position e --spray-volume 0.005 --movement-speed 0.4-1.0 --movement-easing OUT_EXPO""",
)
@dataclass
class SprayConfig(ArgsDataClass):
    """Configuration for the Spray effect.

    Attributes:
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the final gradient.
        spray_position (str): Position for the spray origin. Valid values are n, ne, e, se, s, sw, w, nw, center.
        spray_volume (float): Number of characters to spray per tick as a percent of the total number of characters. Valid values are 0 < n <= 1.
        movement_speed (tuple[float, float]): Movement speed of the characters. Valid values are n > 0.
        movement_easing (typing.Callable): Easing function to use for character movement."""

    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("8A008A", "00D1FF", "FFFFFF"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[graphics.Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name=["--final-gradient-steps"],
        type_parser=arg_validators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
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

    spray_position: str = ArgField(
        cmd_name="--spray-position",
        choices=["n", "ne", "e", "se", "s", "sw", "w", "nw", "center"],
        default="e",
        help="Position for the spray origin.",
    )  # type: ignore[assignment]
    "str : Position for the spray origin."

    spray_volume: float = ArgField(
        cmd_name="--spray-volume",
        type_parser=arg_validators.PositiveFloat.type_parser,
        default=0.005,
        metavar=arg_validators.PositiveFloat.METAVAR,
        help="Number of characters to spray per tick as a percent of the total number of characters.",
    )  # type: ignore[assignment]
    "float : Number of characters to spray per tick as a percent of the total number of characters."

    movement_speed: tuple[float, float] = ArgField(
        cmd_name="--movement-speed",
        type_parser=arg_validators.PositiveFloatRange.type_parser,
        default=(0.4, 1.0),
        metavar=arg_validators.PositiveFloatRange.METAVAR,
        help="Movement speed of the characters.",
    )  # type: ignore[assignment]
    "tuple[float, float] : Movement speed of the characters."

    movement_easing: easing.EasingFunction = ArgField(
        cmd_name="--movement-easing",
        type_parser=arg_validators.Ease.type_parser,
        default=easing.out_expo,
        help="Easing function to use for character movement.",
    )  # type: ignore[assignment]
    "easing.EasingFunction : Easing function to use for character movement."

    @classmethod
    def get_effect_class(cls):
        return Spray


class SprayIterator(BaseEffectIterator[SprayConfig]):
    class _SprayPosition(Enum):
        N = auto()
        NE = auto()
        E = auto()
        SE = auto()
        S = auto()
        SW = auto()
        W = auto()
        NW = auto()
        CENTER = auto()

    def __init__(
        self,
        effect: "Spray",
    ) -> None:
        super().__init__(effect)
        self._pending_chars: list[EffectCharacter] = []
        self._active_chars: list[EffectCharacter] = []
        self._character_final_color_map: dict[EffectCharacter, graphics.Color] = {}
        self._build()

    def _build(self) -> None:
        self._spray_position = {
            "n": SprayIterator._SprayPosition.N,
            "ne": SprayIterator._SprayPosition.NE,
            "e": SprayIterator._SprayPosition.E,
            "se": SprayIterator._SprayPosition.SE,
            "s": SprayIterator._SprayPosition.S,
            "sw": SprayIterator._SprayPosition.SW,
            "w": SprayIterator._SprayPosition.W,
            "nw": SprayIterator._SprayPosition.NW,
            "center": SprayIterator._SprayPosition.CENTER,
        }.get(self._config.spray_position, SprayIterator._SprayPosition.E)
        final_gradient = graphics.Gradient(*self._config.final_gradient_stops, steps=self._config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self._terminal.output_area.top, self._terminal.output_area.right, self._config.final_gradient_direction
        )
        for character in self._terminal.get_characters():
            self._character_final_color_map[character] = final_gradient_mapping[character.input_coord]
        spray_origin_map = {
            SprayIterator._SprayPosition.CENTER: (self._terminal.output_area.center),
            SprayIterator._SprayPosition.N: Coord(
                self._terminal.output_area.right // 2, self._terminal.output_area.top
            ),
            SprayIterator._SprayPosition.NW: Coord(self._terminal.output_area.left, self._terminal.output_area.top),
            SprayIterator._SprayPosition.W: Coord(self._terminal.output_area.left, self._terminal.output_area.top // 2),
            SprayIterator._SprayPosition.SW: Coord(self._terminal.output_area.left, self._terminal.output_area.bottom),
            SprayIterator._SprayPosition.S: Coord(
                self._terminal.output_area.right // 2, self._terminal.output_area.bottom
            ),
            SprayIterator._SprayPosition.SE: Coord(
                self._terminal.output_area.right - 1, self._terminal.output_area.bottom
            ),
            SprayIterator._SprayPosition.E: Coord(
                self._terminal.output_area.right - 1, self._terminal.output_area.top // 2
            ),
            SprayIterator._SprayPosition.NE: Coord(
                self._terminal.output_area.right - 1, self._terminal.output_area.top
            ),
        }

        for character in self._terminal.get_characters():
            character.motion.set_coordinate(spray_origin_map[self._spray_position])
            input_coord_path = character.motion.new_path(
                speed=random.uniform(self._config.movement_speed[0], self._config.movement_speed[1]),
                ease=self._config.movement_easing,
            )
            input_coord_path.new_waypoint(character.input_coord)
            character.event_handler.register_event(
                EventHandler.Event.PATH_ACTIVATED, input_coord_path, EventHandler.Action.SET_LAYER, 1
            )
            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE, input_coord_path, EventHandler.Action.SET_LAYER, 0
            )
            droplet_scn = character.animation.new_scene()
            spray_gradient = graphics.Gradient(
                random.choice(final_gradient.spectrum), self._character_final_color_map[character], steps=7
            )
            droplet_scn.apply_gradient_to_symbols(spray_gradient, character.input_symbol, 20)
            character.animation.activate_scene(droplet_scn)
            character.motion.activate_path(input_coord_path)
            self._pending_chars.append(character)
        random.shuffle(self._pending_chars)
        self._volume = max(int(len(self._pending_chars) * self._config.spray_volume), 1)

    def __next__(self) -> str:
        if self._pending_chars or self._active_chars:
            if self._pending_chars:
                for _ in range(random.randint(1, self._volume)):
                    if self._pending_chars:
                        next_character = self._pending_chars.pop()
                        self._terminal.set_character_visibility(next_character, True)
                        self._active_chars.append(next_character)

            for character in self._active_chars:
                character.tick()
            self._active_chars = [character for character in self._active_chars if character.is_active]
            return self._terminal.get_formatted_output_string()
        else:
            raise StopIteration


class Spray(BaseEffect[SprayConfig]):
    """Sprays the characters from a single point.

    Attributes:
        effect_config (SprayConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.
    """

    _config_cls = SprayConfig
    _iterator_cls = SprayIterator

    def __init__(self, input_data: str) -> None:
        """Initialize the effect with the provided input data.

        Args:
            input_data (str): The input data to use for the effect."""
        super().__init__(input_data)
