"""Waves travel across the terminal leaving behind the characters.

Classes:
    Waves: Creates waves that travel across the terminal, leaving behind the characters.
    WavesConfig: Configuration for the Waves effect.
    WavesIterator: Iterates over the effect. Does not normally need to be called directly.
"""

import typing
from dataclasses import dataclass

import terminaltexteffects.utils.argvalidators as argvalidators
from terminaltexteffects.engine.base_character import EffectCharacter, EventHandler
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import easing, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return Waves, WavesConfig


@argclass(
    name="waves",
    help="Waves travel across the terminal leaving behind the characters.",
    description="waves | Waves travel across the terminal leaving behind the characters.",
    epilog=f"""{argvalidators.EASING_EPILOG}
Example: terminaltexteffects waves --wave-symbols ▁ ▂ ▃ ▄ ▅ ▆ ▇ █ ▇ ▆ ▅ ▄ ▃ ▂ ▁ --wave-gradient-stops f0ff65 ffb102 31a0d4 ffb102 f0ff65 --wave-gradient-steps 6 --final-gradient-stops ffb102 31a0d4 f0ff65 --final-gradient-steps 12 --wave-count 7 --wave-length 2 --wave-easing IN_OUT_SINE""",
)
@dataclass
class WavesConfig(ArgsDataClass):
    """Configuration for the Waves effect.

    Attributes:
        wave_symbols (tuple[str, ...] | str): Symbols to use for the wave animation. Multi-character strings will be used in sequence to create an animation.
        wave_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color.
        wave_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the final gradient.
        wave_count (int): Number of waves to generate. Valid values are n > 0."""

    wave_symbols: tuple[str, ...] = ArgField(
        cmd_name="--wave-symbols",
        type_parser=argvalidators.Symbol.type_parser,
        default=("▁", "▂", "▃", "▄", "▅", "▆", "▇", "█", "▇", "▆", "▅", "▄", "▃", "▂", "▁"),
        nargs="+",
        metavar=argvalidators.Symbol.METAVAR,
        help="Symbols to use for the wave animation. Multi-character strings will be used in sequence to create an animation.",
    )  # type: ignore[assignment]
    "tuple[str, ...] : Symbols to use for the wave animation. Multi-character strings will be used in sequence to create an animation."

    wave_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name="--wave-gradient-stops",
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=("f0ff65", "ffb102", "31a0d4", "ffb102", "f0ff65"),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[graphics.Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color."

    wave_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--wave-gradient-steps",
        type_parser=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=(6,),
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] | int : Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name="--final-gradient-stops",
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=("ffb102", "31a0d4", "f0ff65"),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[graphics.Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] | int = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=12,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] | int : Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=argvalidators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.DIAGONAL,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]
    "graphics.Gradient.Direction : Direction of the final gradient."

    wave_count: int = ArgField(
        cmd_name="--wave-count",
        type_parser=argvalidators.PositiveInt.type_parser,
        default=7,
        help="Number of waves to generate. n > 0.",
    )  # type: ignore[assignment]
    "int : Number of waves to generate. n > 0."

    wave_length: int = ArgField(
        cmd_name="--wave-length",
        type_parser=argvalidators.PositiveInt.type_parser,
        default=2,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="The number of frames for each step of the wave. Higher wave-lengths will create a slower wave.",
    )  # type: ignore[assignment]
    "int : The number of frames for each step of the wave. Higher wave-lengths will create a slower wave."

    wave_easing: easing.EasingFunction = ArgField(
        cmd_name="--wave-easing",
        type_parser=argvalidators.Ease.type_parser,
        default=easing.in_out_sine,
        help="Easing function to use for wave travel.",
    )  # type: ignore[assignment]
    "easing.EasingFunction : Easing function to use for wave travel."

    @classmethod
    def get_effect_class(cls):
        return Waves


class WavesIterator(BaseEffectIterator[WavesConfig]):
    def __init__(self, effect: "Waves") -> None:
        super().__init__(effect)
        self.pending_columns: list[list[EffectCharacter]] = []
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}
        self.build()

    def build(self) -> None:
        final_gradient = graphics.Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.config.final_gradient_direction
        )
        wave_gradient = graphics.Gradient(*self.config.wave_gradient_stops, steps=self.config.wave_gradient_steps)
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]
            wave_scn = character.animation.new_scene()
            wave_scn.ease = self.config.wave_easing
            for _ in range(self.config.wave_count):
                wave_scn.apply_gradient_to_symbols(
                    wave_gradient, self.config.wave_symbols, duration=self.config.wave_length
                )
            final_scn = character.animation.new_scene()
            for step in graphics.Gradient(
                wave_gradient.spectrum[-1],
                self.character_final_color_map[character],
                steps=self.config.final_gradient_steps,
            ):
                final_scn.add_frame(character.input_symbol, 10, color=step)
            character.event_handler.register_event(
                EventHandler.Event.SCENE_COMPLETE, wave_scn, EventHandler.Action.ACTIVATE_SCENE, final_scn
            )
            character.animation.activate_scene(wave_scn)
        for column in self.terminal.get_characters_grouped(grouping=self.terminal.CharacterGroup.COLUMN_LEFT_TO_RIGHT):
            self.pending_columns.append(column)

    def __next__(self) -> str:
        if self.pending_columns or self.active_characters:
            if self.pending_columns:
                next_column = self.pending_columns.pop(0)
                for character in next_column:
                    self.terminal.set_character_visibility(character, True)
                    self.active_characters.append(character)
            self.update()
            return self.frame
        else:
            raise StopIteration


class Waves(BaseEffect[WavesConfig]):
    """Creates waves that travel across the terminal, leaving behind the characters.

    Attributes:
        effect_config (ExpandConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.
    """

    _config_cls = WavesConfig
    _iterator_cls = WavesIterator

    def __init__(self, input_data: str) -> None:
        """Initialize the effect with the provided input data.

        Args:
            input_data (str): The input data to use for the effect."""
        super().__init__(input_data)
