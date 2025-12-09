"""Sweep across the canvas to reveal uncolored text, reverse sweep to color the text.

Classes:
    Sweep: Sweep across the canvas to reveal uncolored text, reverse sweep to color the text.
    SweepConfig: Configuration for the Sweep effect.
    SweepIterator: Iterator for the Sweep effect.


"""

from __future__ import annotations

import random
from dataclasses import dataclass

import terminaltexteffects as tte
from terminaltexteffects.engine.base_config import BaseConfig, FinalGradientDirectionArg, FinalGradientStepsArg, FinalGradientStopsArg
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.argutils import ArgSpec, CharacterGroup, ParserSpec


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Get the command, effect class, and configuration class for the effect.

    Returns:
        tuple[str, type[BaseEffect], type[BaseConfig]]: The command name, effect class, and configuration class.

    """
    return "sweep", Sweep, SweepConfig


@dataclass
class SweepConfig(BaseConfig):
    """Sweep effect configuration dataclass."""

    parser_spec: ParserSpec = ParserSpec(
        name="sweep",
        help="Sweep across the canvas to reveal uncolored text, reverse sweep to color the text.",
        description="sweep | Sweep across the canvas to reveal uncolored text, reverse sweep to color the text.",
        epilog=(
            f"{argutils.EASING_EPILOG}Example: terminaltexteffects sweep --sweep-symbols '█' '▓' '▒' '░' "
            "--first-sweep-direction "
            "column_right_to_left --second-sweep-direction column_left_to_right --final-gradient-stops 8A008A "
            "00D1FF ffffff --final-gradient-steps 8 --final-gradient-direction vertical"
        ),
    )

    sweep_symbols: tuple[str, ...] = ArgSpec(
        name="--sweep-symbols",
        type=argutils.Symbol.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=("█", "▓", "▒", "░"),
        metavar=argutils.Symbol.METAVAR,
        help="Space separated list of symbols to use for the sweep shimmer.",
    )  # pyright: ignore[reportAssignmentType]
    "tuple[str, ...] | str : Tuple of symbols to use for the sweep shimmer."

    first_sweep_direction: CharacterGroup = ArgSpec(
        name="--first-sweep-direction",
        default=CharacterGroup.COLUMN_RIGHT_TO_LEFT,
        type=argutils.CharacterGroupArg.type_parser,
        help="Direction of the first sweep, revealing uncolored characters.",
    )  # pyright: ignore[reportAssignmentType]
    "CharacterGroup : Direction of the first sweep, revealing uncolored characters."

    second_sweep_direction: CharacterGroup = ArgSpec(
        name="--second-sweep-direction",
        default=CharacterGroup.COLUMN_LEFT_TO_RIGHT,
        type=argutils.CharacterGroupArg.type_parser,
        help="Direction of the second sweep, coloring the characters.",
    )  # pyright: ignore[reportAssignmentType]
    "CharacterGroup : Direction of the second sweep, coloring the characters."

    final_gradient_stops: tuple[tte.Color, ...] = FinalGradientStopsArg(
        default=(tte.Color("#8A008A"), tte.Color("#00D1FF"), tte.Color("#ffffff")),
        help=(
            "Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). "
            "If only one color is provided, the characters will be displayed in that color."
        ),
    )  # pyright: ignore[reportAssignmentType]
    "tuple[Color, ...]: Space separated, unquoted, list of colors for the character gradient "
    "(applied from bottom to top). If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] | int = FinalGradientStepsArg(
        default=8,
    )  # pyright: ignore[reportAssignmentType]
    "tuple[int, ...] | int: Space separated, unquoted, list of the number of gradient steps to use. More steps will "
    "create a smoother and longer gradient animation."

    final_gradient_direction: tte.Gradient.Direction = FinalGradientDirectionArg(
        default=tte.Gradient.Direction.VERTICAL,
    )  # pyright: ignore[reportAssignmentType]
    "Gradient.Direction : Direction of the final gradient."


class SweepIterator(BaseEffectIterator[SweepConfig]):
    """Iterator for the sweep effect."""

    def __init__(self, effect: Sweep) -> None:
        """Initialize the effect iterator."""
        super().__init__(effect)
        self.character_final_color_map: dict[tte.EffectCharacter, tte.ColorPair] = {}
        self.complete = False
        self.phase = "first sweep"
        self.easer: tte.easing.SequenceEaser
        self.build()

    def build(self) -> None:
        """Build the effect."""
        final_fg_gradient = tte.Gradient(
            *self.config.final_gradient_stops,
            steps=self.config.final_gradient_steps,
        )
        final_gradient_mapping = final_fg_gradient.build_coordinate_color_mapping(
            self.terminal.canvas.text_bottom,
            self.terminal.canvas.text_top,
            self.terminal.canvas.text_left,
            self.terminal.canvas.text_right,
            self.config.final_gradient_direction,
        )
        shades_of_gray = [
            tte.Color("#A0A0A0"),
            tte.Color("#808080"),
            tte.Color("#404040"),
            tte.Color("#202020"),
            tte.Color("#101010"),
        ]

        for character in self.terminal.get_characters(inner_fill_chars=True, outer_fill_chars=True):
            if not character.is_fill_character:
                self.character_final_color_map[character] = tte.ColorPair(
                    fg=final_gradient_mapping[character.input_coord],
                )
            initial_sweep_scn = character.animation.new_scene(scene_id="initial_sweep")
            for char in self.config.sweep_symbols:
                initial_sweep_scn.add_frame(
                    char,
                    5,
                    colors=tte.ColorPair(fg=random.choice(shades_of_gray)),
                )
            initial_sweep_scn.add_frame(character.input_symbol, 1, colors=tte.ColorPair("#808080"))
            second_sweep_scn = character.animation.new_scene(scene_id="second_sweep")
            for char in self.config.sweep_symbols:
                second_sweep_scn.add_frame(
                    char,
                    5,
                    colors=tte.ColorPair(fg=random.choice(final_fg_gradient.spectrum)),
                )
            second_sweep_scn.add_frame(
                character.input_symbol,
                1,
                colors=tte.ColorPair(
                    fg=final_gradient_mapping[character.input_coord] if not character.is_fill_character else "000000",
                ),
            )

        self.groups_first_sweep = self.terminal.get_characters_grouped(
            self.config.first_sweep_direction,
            inner_fill_chars=True,
            outer_fill_chars=True,
        )
        self.easer = tte.easing.SequenceEaser(
            sequence=self.groups_first_sweep,
            easing_function=tte.easing.in_out_circ,
        )
        self.groups_second_sweep = self.terminal.get_characters_grouped(
            self.config.second_sweep_direction,
            inner_fill_chars=True,
            outer_fill_chars=True,
        )

    def __next__(self) -> str:
        """Return the next frame in the effect."""
        while self.active_characters or not self.complete:
            self.easer.step()
            group: list[tte.EffectCharacter]
            for group in self.easer.added:
                for character in group:
                    if self.phase == "first sweep":
                        self.terminal.set_character_visibility(character, is_visible=True)
                    character.animation.activate_scene(
                        "initial_sweep" if self.phase == "first sweep" else "second_sweep",
                    )
                self.active_characters.update(group)
            if self.easer.is_complete() and self.phase == "first sweep":
                self.easer.sequence = self.groups_second_sweep
                self.easer.reset()
                self.phase = "second sweep"
            elif self.easer.is_complete() and self.phase == "second sweep":
                self.complete = True
            self.update()
            return self.frame
        raise StopIteration


class Sweep(BaseEffect[SweepConfig]):
    """Sweep across the canvas to reveal uncolored text, reverse sweep to color the text."""

    @property
    def _config_cls(self) -> type[SweepConfig]:
        return SweepConfig

    @property
    def _iterator_cls(self) -> type[SweepIterator]:
        return SweepIterator
