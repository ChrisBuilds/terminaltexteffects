import typing
from collections.abc import Iterator
from dataclasses import dataclass

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils import easing, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.terminal import Terminal, TerminalConfig


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return WavesEffect, EffectConfig


@argclass(
    name="waves",
    help="Waves travel across the terminal leaving behind the characters.",
    description="waves | Waves travel across the terminal leaving behind the characters.",
    epilog=f"""{arg_validators.EASING_EPILOG}
Example: terminaltexteffects waves --wave-symbols ▁ ▂ ▃ ▄ ▅ ▆ ▇ █ ▇ ▆ ▅ ▄ ▃ ▂ ▁ --wave-gradient-stops f0ff65 ffb102 31a0d4 ffb102 f0ff65 --wave-gradient-steps 6 --final-gradient-stops ffb102 31a0d4 f0ff65 --final-gradient-steps 12 --wave-count 7 --wave-length 2 --wave-easing IN_OUT_SINE""",
)
@dataclass
class EffectConfig(ArgsDataClass):
    """Configuration for the Waves effect.

    Attributes:
        wave_symbols (tuple[str, ...]): Symbols to use for the wave animation. Multi-character strings will be used in sequence to create an animation.
        wave_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
        wave_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the gradient for the final color.
        wave_count (int): Number of waves to generate. n > 0."""

    wave_symbols: tuple[str, ...] = ArgField(
        cmd_name="--wave-symbols",
        type_parser=arg_validators.Symbol.type_parser,
        default=("▁", "▂", "▃", "▄", "▅", "▆", "▇", "█", "▇", "▆", "▅", "▄", "▃", "▂", "▁"),
        nargs="+",
        metavar=arg_validators.Symbol.METAVAR,
        help="Symbols to use for the wave animation. Multi-character strings will be used in sequence to create an animation.",
    )  # type: ignore[assignment]
    "tuple[str, ...] : Symbols to use for the wave animation. Multi-character strings will be used in sequence to create an animation."

    wave_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name="--wave-gradient-stops",
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("f0ff65", "ffb102", "31a0d4", "ffb102", "f0ff65"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[graphics.Color, ...] : Tuple of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color."

    wave_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--wave-gradient-steps",
        type_parser=arg_validators.PositiveInt.type_parser,
        nargs="+",
        default=(6,),
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] : Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name="--final-gradient-stops",
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("ffb102", "31a0d4", "f0ff65"),
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
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] : Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=arg_validators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.DIAGONAL,
        metavar=arg_validators.GradientDirection.METAVAR,
        help="Direction of the gradient for the final color.",
    )  # type: ignore[assignment]
    "graphics.Gradient.Direction : Direction of the gradient for the final color."

    wave_count: int = ArgField(
        cmd_name="--wave-count",
        type_parser=arg_validators.PositiveInt.type_parser,
        default=7,
        help="Number of waves to generate. n > 0.",
    )  # type: ignore[assignment]
    "int : Number of waves to generate. n > 0."

    wave_length: int = ArgField(
        cmd_name="--wave-length",
        type_parser=arg_validators.PositiveInt.type_parser,
        default=2,
        metavar=arg_validators.PositiveInt.METAVAR,
        help="The number of frames for each step of the wave. Higher wave-lengths will create a slower wave.",
    )  # type: ignore[assignment]
    "int : The number of frames for each step of the wave. Higher wave-lengths will create a slower wave."

    wave_easing: easing.EasingFunction = ArgField(
        cmd_name="--wave-easing",
        type_parser=arg_validators.Ease.type_parser,
        default=easing.in_out_sine,
        help="Easing function to use for wave travel.",
    )  # type: ignore[assignment]
    "easing.EasingFunction : Easing function to use for wave travel."

    @classmethod
    def get_effect_class(cls):
        return WavesEffect


class WavesEffect:
    """Effect that creates waves that travel across the terminal, leaving behind the characters."""

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
        self._pending_columns: list[list[EffectCharacter]] = []
        self._active_chars: list[EffectCharacter] = []
        self._character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def build(self) -> None:
        """Prepares the data for the effect by creating the wave animations."""
        self._pending_columns.clear()
        self._active_chars.clear()
        self._character_final_color_map.clear()
        final_gradient = graphics.Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.config.final_gradient_direction
        )
        wave_gradient = graphics.Gradient(*self.config.wave_gradient_stops, steps=self.config.wave_gradient_steps)
        for character in self.terminal.get_characters():
            self._character_final_color_map[character] = final_gradient_mapping[character.input_coord]
            wave_scn = character.animation.new_scene()
            wave_scn.ease = self.config.wave_easing
            for _ in range(self.config.wave_count):
                wave_scn.apply_gradient_to_symbols(
                    wave_gradient, self.config.wave_symbols, duration=self.config.wave_length
                )
            final_scn = character.animation.new_scene()
            for step in graphics.Gradient(
                wave_gradient.spectrum[-1],
                self._character_final_color_map[character],
                steps=self.config.final_gradient_steps,
            ):
                final_scn.add_frame(character.input_symbol, 10, color=step)
            character.event_handler.register_event(
                EventHandler.Event.SCENE_COMPLETE, wave_scn, EventHandler.Action.ACTIVATE_SCENE, final_scn
            )
            character.animation.activate_scene(wave_scn)
        for column in self.terminal.get_characters_grouped(grouping=self.terminal.CharacterGroup.COLUMN_LEFT_TO_RIGHT):
            self._pending_columns.append(column)
        self._built = True

    @property
    def built(self) -> bool:
        """Returns True if the effect has been built."""
        return self._built

    def __iter__(self) -> Iterator[str]:
        """Runs the effect."""
        if not self._built:
            self.build()
        while self._pending_columns or self._active_chars:
            if self._pending_columns:
                next_column = self._pending_columns.pop(0)
                for character in next_column:
                    self.terminal.set_character_visibility(character, True)
                    self._active_chars.append(character)
            yield self.terminal.get_formatted_output_string()
            self._animate_chars()

            self._active_chars = [character for character in self._active_chars if character.is_active]

        self._built = False

    def _animate_chars(self) -> None:
        """Animates the characters by calling the tick method on all active characters."""
        for character in self._active_chars:
            character.tick()
