"""Effect that draws the characters spawning at varying rates from a single point."""

import random
import typing
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum, auto

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils import easing, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.terminal import Terminal, TerminalConfig


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return SprayEffect, EffectConfig


@argclass(
    name="spray",
    help="Draws the characters spawning at varying rates from a single point.",
    description="spray | Draws the characters spawning at varying rates from a single point.",
    epilog=f"""{arg_validators.EASING_EPILOG}    
Example: terminaltexteffects spray --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --spray-position e --spray-volume 0.005 --movement-speed 0.4-1.0 --movement-easing OUT_EXPO""",
)
@dataclass
class EffectConfig(ArgsDataClass):
    """Configuration for the Spray effect.

    Attributes:
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the gradient for the final color.
        spray_position (str): Position for the spray origin.
        spray_volume (float): Number of characters to spray per tick as a percent of the total number of characters.
        movement_speed (tuple[float, float]): Movement speed of the characters.
        movement_easing (typing.Callable): Easing function to use for character movement."""

    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("8A008A", "00D1FF", "FFFFFF"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[graphics.Color, ...] : Tuple of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color."

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
        help="Direction of the gradient for the final color.",
    )  # type: ignore[assignment]
    "graphics.Gradient.Direction : Direction of the gradient for the final color."

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
        return SprayEffect


class SprayPosition(Enum):
    """Position for the spray origin."""

    N = auto()
    NE = auto()
    E = auto()
    SE = auto()
    S = auto()
    SW = auto()
    W = auto()
    NW = auto()
    CENTER = auto()


class SprayEffect:
    """Effect that draws the characters spawning at varying rates from a single point."""

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
        self._character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def build(self) -> None:
        """Prepares the data for the effect by starting all of the characters from a point based on SparklerPosition."""
        self._pending_chars.clear()
        self._active_chars.clear()
        self._character_final_color_map.clear()
        self._spray_position = {
            "n": SprayPosition.N,
            "ne": SprayPosition.NE,
            "e": SprayPosition.E,
            "se": SprayPosition.SE,
            "s": SprayPosition.S,
            "sw": SprayPosition.SW,
            "w": SprayPosition.W,
            "nw": SprayPosition.NW,
            "center": SprayPosition.CENTER,
        }.get(self.config.spray_position, SprayPosition.E)
        final_gradient = graphics.Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.config.final_gradient_direction
        )
        for character in self.terminal.get_characters():
            self._character_final_color_map[character] = final_gradient_mapping[character.input_coord]
        spray_origin_map = {
            SprayPosition.CENTER: (self.terminal.output_area.center),
            SprayPosition.N: Coord(self.terminal.output_area.right // 2, self.terminal.output_area.top),
            SprayPosition.NW: Coord(self.terminal.output_area.left, self.terminal.output_area.top),
            SprayPosition.W: Coord(self.terminal.output_area.left, self.terminal.output_area.top // 2),
            SprayPosition.SW: Coord(self.terminal.output_area.left, self.terminal.output_area.bottom),
            SprayPosition.S: Coord(self.terminal.output_area.right // 2, self.terminal.output_area.bottom),
            SprayPosition.SE: Coord(self.terminal.output_area.right - 1, self.terminal.output_area.bottom),
            SprayPosition.E: Coord(self.terminal.output_area.right - 1, self.terminal.output_area.top // 2),
            SprayPosition.NE: Coord(self.terminal.output_area.right - 1, self.terminal.output_area.top),
        }

        for character in self.terminal.get_characters():
            character.motion.set_coordinate(spray_origin_map[self._spray_position])
            input_coord_path = character.motion.new_path(
                speed=random.uniform(self.config.movement_speed[0], self.config.movement_speed[1]),
                ease=self.config.movement_easing,
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
        self._built = True

    @property
    def built(self) -> bool:
        """Returns True if the effect has been built."""
        return self._built

    def __iter__(self) -> Iterator[str]:
        """Runs the effect."""
        if not self._built:
            self.build()
        volume = max(int(len(self._pending_chars) * self.config.spray_volume), 1)
        while self._pending_chars or self._active_chars:
            if self._pending_chars:
                for _ in range(random.randint(1, volume)):
                    if self._pending_chars:
                        next_character = self._pending_chars.pop()
                        self.terminal.set_character_visibility(next_character, True)
                        self._active_chars.append(next_character)

            self._animate_chars()
            yield self.terminal.get_formatted_output_string()
            self._active_chars = [character for character in self._active_chars if character.is_active]
        self._built = False

    def _animate_chars(self) -> None:
        for character in self._active_chars:
            character.tick()
