"""Text is scattered across the output area and moves into position.

Classes:
    Scattered: Move the characters into place from random starting locations.
    ScatteredConfig: Configuration for the Scattered effect.
    ScatteredIterator: Effect iterator for the effect. Does not normally need to be called directly.
"""

import typing
from dataclasses import dataclass

from terminaltexteffects.engine.base_character import EffectCharacter, EventHandler
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argvalidators, easing, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return Scattered, ScatteredConfig


@argclass(
    name="scattered",
    help="Text is scattered across the output area and moves into position.",
    description="scattered | Text is scattered across the output area and moves into position.",
    epilog=f"""{argvalidators.EASING_EPILOG}
Example: terminaltexteffects scattered --final-gradient-stops ff9048 ab9dff bdffea --final-gradient-steps 12 --final-gradient-frames 12 --movement-speed 0.5 --movement-easing IN_OUT_BACK""",
)
@dataclass
class ScatteredConfig(ArgsDataClass):
    """Configuration for the effect.

    Attributes:
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the character gradient. If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_frames (int): Number of frames to display each gradient step.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the final gradient.
        movement_speed (float): Movement speed of the characters. Valid values are n > 0.
        movement_easing (easing.EasingFunction): Easing function to use for character movement."""

    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=("ff9048", "ab9dff", "bdffea"),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient. If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[graphics.Color, ...] : Tuple of colors for the character gradient. If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=argvalidators.PositiveInt.type_parser,
        default=(12,),
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] : Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_frames: int = ArgField(
        cmd_name="--final-gradient-frames",
        type_parser=argvalidators.PositiveInt.type_parser,
        default=12,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step.",
    )  # type: ignore[assignment]
    "int : Number of frames to display each gradient step."

    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=argvalidators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.VERTICAL,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]
    "graphics.Gradient.Direction : Direction of the final gradient."

    movement_speed: float = ArgField(
        cmd_name="--movement-speed",
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=0.3,
        metavar=argvalidators.PositiveFloat.METAVAR,
        help="Movement speed of the characters. ",
    )  # type: ignore[assignment]
    "float : Movement speed of the characters. "

    movement_easing: easing.EasingFunction = ArgField(
        cmd_name="--movement-easing",
        default=easing.in_out_back,
        type_parser=argvalidators.Ease.type_parser,
        help="Easing function to use for character movement.",
    )  # type: ignore[assignment]
    "easing.EasingFunction : Easing function to use for character movement."

    @classmethod
    def get_effect_class(cls):
        return Scattered


class ScatteredIterator(BaseEffectIterator[ScatteredConfig]):
    def __init__(self, effect: "Scattered") -> None:
        super().__init__(effect)
        self._pending_chars: list[EffectCharacter] = []
        self._active_chars: list[EffectCharacter] = []
        self._character_final_color_map: dict[EffectCharacter, graphics.Color] = {}
        self._build()

    def _build(self) -> None:
        final_gradient = graphics.Gradient(*self._config.final_gradient_stops, steps=self._config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self._terminal.output_area.top, self._terminal.output_area.right, self._config.final_gradient_direction
        )
        for character in self._terminal.get_characters():
            self._character_final_color_map[character] = final_gradient_mapping[character.input_coord]
            if self._terminal.output_area.right < 2 or self._terminal.output_area.top < 2:
                character.motion.set_coordinate(Coord(1, 1))
            else:
                character.motion.set_coordinate(self._terminal.output_area.random_coord())
            input_coord_path = character.motion.new_path(
                speed=self._config.movement_speed, ease=self._config.movement_easing
            )
            input_coord_path.new_waypoint(character.input_coord)
            character.event_handler.register_event(
                EventHandler.Event.PATH_ACTIVATED, input_coord_path, EventHandler.Action.SET_LAYER, 1
            )
            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE, input_coord_path, EventHandler.Action.SET_LAYER, 0
            )
            character.motion.activate_path(input_coord_path)
            self._terminal.set_character_visibility(character, True)
            gradient_scn = character.animation.new_scene()
            char_gradient = graphics.Gradient(
                final_gradient.spectrum[0], self._character_final_color_map[character], steps=10
            )
            gradient_scn.apply_gradient_to_symbols(
                char_gradient, character.input_symbol, self._config.final_gradient_frames
            )
            character.animation.activate_scene(gradient_scn)
            self._active_chars.append(character)
        self._initial_hold_frames = 25

    def __next__(self) -> str:
        if self._pending_chars or self._active_chars:
            if self._initial_hold_frames:
                self._initial_hold_frames -= 1
                return self._terminal.get_formatted_output_string()
            for character in self._active_chars:
                character.tick()
            self._active_chars = [character for character in self._active_chars if character.is_active]
            return self._terminal.get_formatted_output_string()
        else:
            raise StopIteration


class Scattered(BaseEffect[ScatteredConfig]):
    """Text is scattered across the output area and moves into position.

    Attributes:
        effect_config (ScatteredConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.
    """

    _config_cls = ScatteredConfig
    _iterator_cls = ScatteredIterator

    def __init__(self, input_data: str) -> None:
        """Initialize the effect with the provided input data.

        Args:
            input_data (str): The input data to use for the effect."""
        super().__init__(input_data)
