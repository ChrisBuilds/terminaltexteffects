"""Waves travel across the terminal leaving behind the characters.

Classes:
    Waves: Creates waves that travel across the terminal, leaving behind the characters.
    WavesConfig: Configuration for the Waves effect.
    WavesIterator: Iterates over the effect. Does not normally need to be called directly.
"""

from __future__ import annotations

import typing
from dataclasses import dataclass

from terminaltexteffects import Color, ColorPair, EffectCharacter, EventHandler, Gradient, easing
from terminaltexteffects.engine.base_config import ArgSpec, BaseConfig, ParserSpec
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argvalidators


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Get the command, effect class, and configuration class for the effect.

    Returns:
        tuple[str, type[BaseEffect], type[BaseConfig]]: The command name, effect class, and configuration class.

    """
    return "waves", Waves, WavesConfig


@dataclass
class WavesConfig(BaseConfig):
    """Configuration for the Waves effect.

    Attributes:
        wave_symbols (tuple[str, ...] | str): Symbols to use for the wave animation. Multi-character strings will be
            used in sequence to create an animation.
        wave_gradient_stops (tuple[Color, ...]): Tuple of colors for the final color gradient. If only one color is
            provided, the characters will be displayed in that color.
        wave_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a
            smoother and longer gradient animation. Valid values are n > 0.
        wave_count (int): Number of waves to generate. Valid values are n > 0.
        wave_length (int): The number of frames for each step of the wave. Higher wave-lengths will create a slower
            wave. Valid values are n > 0.
        wave_direction (typing.Literal['column_left_to_right','column_right_to_left','row_top_to_bottom','row_bottom_to_top','center_to_outside','outside_to_center']): Direction of the wave.
        wave_easing (easing.EasingFunction): Easing function to use for wave travel.
        final_gradient_stops (tuple[Color, ...]): Tuple of colors for the final color gradient. If only one color is
            provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Tuple of the number of gradient steps to use. More steps will
            create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient.

    """  # noqa: E501

    parser_spec: ParserSpec = ParserSpec(
        name="waves",
        help="Waves travel across the terminal leaving behind the characters.",
        description="waves | Waves travel across the terminal leaving behind the characters.",
        epilog=(
            f"{argvalidators.EASING_EPILOG} Example: terminaltexteffects waves --wave-symbols ▁ ▂ ▃ ▄ ▅ ▆ ▇ █ "
            "▇ ▆ ▅ ▄ ▃ ▂ ▁ --wave-gradient-stops f0ff65 ffb102 31a0d4 ffb102 f0ff65 --wave-gradient-steps 6 "
            "--final-gradient-stops ffb102 31a0d4 f0ff65 --final-gradient-steps 12 --wave-count 7 --wave-length 2 "
            "--wave-easing IN_OUT_SINE"
        ),
    )

    wave_symbols: tuple[str, ...] = ArgSpec(
        name="--wave-symbols",
        type=argvalidators.Symbol.type_parser,
        default=("▁", "▂", "▃", "▄", "▅", "▆", "▇", "█", "▇", "▆", "▅", "▄", "▃", "▂", "▁"),
        nargs="+",
        metavar=argvalidators.Symbol.METAVAR,
        help="Symbols to use for the wave animation. Multi-character strings will be used in sequence to create an "
        "animation.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[str, ...] : Symbols to use for the wave animation. Multi-character strings will be used in sequence to "
        "create an animation."
    )

    wave_gradient_stops: tuple[Color, ...] = ArgSpec(
        name="--wave-gradient-stops",
        type=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(Color("#f0ff65"), Color("#ffb102"), Color("#31a0d4"), Color("#ffb102"), Color("#f0ff65")),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied across the canvas). If "
        "only one color is provided, the characters will be displayed in that color.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the "
        "characters will be displayed in that color."
    )

    wave_gradient_steps: tuple[int, ...] = ArgSpec(
        name="--wave-gradient-steps",
        type=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=(6,),
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a "
        "smoother and longer gradient animation.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[int, ...] : Tuple of the number of gradient steps to use. More steps will create a smoother and "
        "longer gradient animation."
    )

    wave_count: int = ArgSpec(
        name="--wave-count",
        type=argvalidators.PositiveInt.type_parser,
        default=7,
        help="Number of waves to generate. n > 0.",
    )  # pyright: ignore[reportAssignmentType]
    "int : Number of waves to generate. n > 0."

    wave_length: int = ArgSpec(
        name="--wave-length",
        type=argvalidators.PositiveInt.type_parser,
        default=2,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="The number of frames for each step of the wave. Higher wave-lengths will create a slower wave.",
    )  # pyright: ignore[reportAssignmentType]
    "int : The number of frames for each step of the wave. Higher wave-lengths will create a slower wave."

    wave_direction: typing.Literal[
        "column_left_to_right",
        "column_right_to_left",
        "row_top_to_bottom",
        "row_bottom_to_top",
        "center_to_outside",
        "outside_to_center",
    ] = ArgSpec(
        name="--wave-direction",
        default="column_left_to_right",
        help="Direction of the wave.",
        choices=[
            "column_left_to_right",
            "column_right_to_left",
            "row_top_to_bottom",
            "row_bottom_to_top",
            "center_to_outside",
            "outside_to_center",
        ],
    )  # pyright: ignore[reportAssignmentType]
    "typing.Literal['column_left_to_right','column_right_to_left','row_top_to_bottom','row_bottom_to_top','center_to_outside','outside_to_center']"

    wave_easing: easing.EasingFunction = ArgSpec(
        name="--wave-easing",
        type=argvalidators.Ease.type_parser,
        default=easing.in_out_sine,
        help="Easing function to use for wave travel.",
    )  # pyright: ignore[reportAssignmentType]
    "easing.EasingFunction : Easing function to use for wave travel."

    final_gradient_stops: tuple[Color, ...] = ArgSpec(
        name="--final-gradient-stops",
        type=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(Color("#ffb102"), Color("#31a0d4"), Color("#f0ff65")),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied across the canvas). "
        "If only one color is provided, the characters will be displayed in that color.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the "
        "characters will be displayed in that color."
    )

    final_gradient_steps: tuple[int, ...] | int = ArgSpec(
        name="--final-gradient-steps",
        type=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=12,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create "
        "a smoother and longer gradient animation.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[int, ...] | int : Int or Tuple of ints for the number of gradient steps to use. More steps "
        "will create a smoother and longer gradient animation."
    )

    final_gradient_direction: Gradient.Direction = ArgSpec(
        name="--final-gradient-direction",
        type=argvalidators.GradientDirection.type_parser,
        default=Gradient.Direction.DIAGONAL,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # pyright: ignore[reportAssignmentType]
    "Gradient.Direction : Direction of the final gradient."


class WavesIterator(BaseEffectIterator[WavesConfig]):
    """Iterator for the Waves effect."""

    def __init__(self, effect: Waves) -> None:
        """Initialize the iterator with the provided effect.

        Args:
            effect (Waves): The effect to iterate over.

        """
        super().__init__(effect)
        self.pending_columns: list[list[EffectCharacter]] = []
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self.build()

    def build(self) -> None:
        """Build the effect."""
        final_gradient = Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.canvas.text_bottom,
            self.terminal.canvas.text_top,
            self.terminal.canvas.text_left,
            self.terminal.canvas.text_right,
            self.config.final_gradient_direction,
        )
        wave_gradient = Gradient(*self.config.wave_gradient_stops, steps=self.config.wave_gradient_steps)
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]
            wave_scn = character.animation.new_scene()
            wave_scn.ease = self.config.wave_easing
            for _ in range(self.config.wave_count):
                wave_scn.apply_gradient_to_symbols(
                    self.config.wave_symbols,
                    duration=self.config.wave_length,
                    fg_gradient=wave_gradient,
                )
            final_scn = character.animation.new_scene()
            for step in Gradient(
                wave_gradient.spectrum[-1],
                self.character_final_color_map[character],
                steps=self.config.final_gradient_steps,
            ):
                final_scn.add_frame(character.input_symbol, 10, colors=ColorPair(fg=step))
            character.event_handler.register_event(
                EventHandler.Event.SCENE_COMPLETE,
                wave_scn,
                EventHandler.Action.ACTIVATE_SCENE,
                final_scn,
            )
            character.animation.activate_scene(wave_scn)
        grouping_map = {
            "column_left_to_right": self.terminal.CharacterGroup.COLUMN_LEFT_TO_RIGHT,
            "column_right_to_left": self.terminal.CharacterGroup.COLUMN_RIGHT_TO_LEFT,
            "row_top_to_bottom": self.terminal.CharacterGroup.ROW_TOP_TO_BOTTOM,
            "row_bottom_to_top": self.terminal.CharacterGroup.ROW_BOTTOM_TO_TOP,
            "center_to_outside": self.terminal.CharacterGroup.CENTER_TO_OUTSIDE_DIAMONDS,
            "outside_to_center": self.terminal.CharacterGroup.OUTSIDE_TO_CENTER_DIAMONDS,
        }

        for column in self.terminal.get_characters_grouped(grouping=grouping_map[self.config.wave_direction]):
            self.pending_columns.append(column)

    def __next__(self) -> str:
        """Return the next frame in the animation."""
        if self.pending_columns or self.active_characters:
            if self.pending_columns:
                next_column = self.pending_columns.pop(0)
                for character in next_column:
                    self.terminal.set_character_visibility(character, is_visible=True)
                    self.active_characters.add(character)
            self.update()
            return self.frame
        raise StopIteration


class Waves(BaseEffect[WavesConfig]):
    """Creates waves that travel across the terminal, leaving behind the characters.

    Attributes:
        effect_config (ExpandConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.

    """

    @property
    def _config_cls(self) -> type[WavesConfig]:
        return WavesConfig

    @property
    def _iterator_cls(self) -> type[WavesIterator]:
        return WavesIterator
