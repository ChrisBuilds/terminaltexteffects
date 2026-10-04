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
from terminaltexteffects.engine.base_config import (
    BaseConfig,
    FinalGradientDirectionArg,
    FinalGradientStepsArg,
    FinalGradientStopsArg,
)
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Get the command, effect class, and configuration class for the effect.

    Returns:
        tuple[str, type[BaseEffect], type[BaseConfig]]: The command name, effect class, and configuration class.

    """
    return "sweep", Sweep, SweepConfig


@dataclass
class SweepConfig(BaseConfig):
    """Sweep effect configuration dataclass."""

    parser_spec: argutils.ParserSpec = argutils.ParserSpec(
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

    sweep_symbols: tuple[str, ...] = argutils.ArgSpec(
        name="--sweep-symbols",
        type=argutils.Symbol.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=("█", "▓", "▒", "░"),
        metavar=argutils.Symbol.METAVAR,
        help="Space separated list of symbols to use for the sweep shimmer.",
    )  # pyright: ignore[reportAssignmentType]
    "tuple[str, ...] | str : Tuple of symbols to use for the sweep shimmer."

    first_sweep_direction: argutils.CharacterOrder | argutils.CharacterGroup | argutils.CharacterSort = (
        argutils.ArgSpec(
            name="--first-sweep-direction",
            default=argutils.CharacterOrder.COLUMN_RIGHT_TO_LEFT,
            type=argutils.CharacterOrderArg.type_parser,
            metavar=" ".join(argutils.CharacterOrderArg.METAVAR),
            help="Grouping or character sort order for the first sweep, revealing uncolored characters.",
        )
    )  # pyright: ignore[reportAssignmentType]
    "CharacterOrder : Order of the first sweep, revealing uncolored characters."

    reverse_first_sweep_direction: bool = argutils.ArgSpec(
        name="--reverse-first-sweep-direction",
        default=False,
        action="store_true",
        help="Reverse the complete first sweep direction traversal.",
    )  # pyright: ignore[reportAssignmentType]
    "bool : Reverse the complete traversal, preserving group membership."

    second_sweep_direction: argutils.CharacterOrder | argutils.CharacterGroup | argutils.CharacterSort = (
        argutils.ArgSpec(
            name="--second-sweep-direction",
            default=argutils.CharacterOrder.COLUMN_LEFT_TO_RIGHT,
            type=argutils.CharacterOrderArg.type_parser,
            metavar=" ".join(argutils.CharacterOrderArg.METAVAR),
            help="Grouping or character sort order for the second sweep, coloring the characters.",
        )
    )  # pyright: ignore[reportAssignmentType]
    "CharacterOrder : Order of the second sweep, coloring the characters."

    reverse_second_sweep_direction: bool = argutils.ArgSpec(
        name="--reverse-second-sweep-direction",
        default=False,
        action="store_true",
        help="Reverse the complete second sweep direction traversal.",
    )  # pyright: ignore[reportAssignmentType]
    "bool : Reverse the complete traversal, preserving group membership."

    travel_speed: int = argutils.ArgSpec(
        name="--travel-speed",
        type=argutils.PositiveInt.type_parser,
        default=1,
        metavar=argutils.PositiveInt.METAVAR,
        help="Number of sweep easing steps to advance per frame, for both phases. n > 0.",
    )  # pyright: ignore[reportAssignmentType]
    "int : Easing steps per frame for both sweeps; animations advance once per frame. Defaults to 1."

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
        self.dynamic_second_sweep_palette: list[tte.Color] = []
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

        if self.terminal.config.existing_color_handling == "dynamic":
            for character in self.terminal.get_characters():
                if character.animation.input_fg_color is not None:
                    self.dynamic_second_sweep_palette.append(character.animation.input_fg_color)
                if character.animation.input_bg_color is not None:
                    self.dynamic_second_sweep_palette.append(character.animation.input_bg_color)
            if not self.dynamic_second_sweep_palette:
                self.dynamic_second_sweep_palette = list(final_fg_gradient.spectrum)

        for character in self.terminal.get_characters(inner_fill_chars=True, outer_fill_chars=True):
            if not character.is_fill_character:
                if self.terminal.config.existing_color_handling == "dynamic":
                    self.character_final_color_map[character] = tte.ColorPair(
                        fg=character.animation.input_fg_color,
                        bg=character.animation.input_bg_color,
                    )
                else:
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
                    colors=tte.ColorPair(
                        fg=(
                            random.choice(self.dynamic_second_sweep_palette)
                            if self.terminal.config.existing_color_handling == "dynamic"
                            else random.choice(final_fg_gradient.spectrum)
                        ),
                    ),
                )
            second_sweep_scn.add_frame(
                character.input_symbol,
                1,
                colors=(
                    self.character_final_color_map[character]
                    if not character.is_fill_character
                    else (
                        tte.ColorPair()
                        if self.terminal.config.existing_color_handling == "dynamic"
                        else tte.ColorPair(fg="000000")
                    )
                ),
            )

        self.groups_first_sweep = self._get_sweep_groups(
            self.config.first_sweep_direction, reverse=self.config.reverse_first_sweep_direction,
        )
        self.easer = tte.easing.SequenceEaser(
            sequence=self.groups_first_sweep,
            easing_function=tte.easing.in_out_circ,
        )
        self.groups_second_sweep = self._get_sweep_groups(
            self.config.second_sweep_direction, reverse=self.config.reverse_second_sweep_direction,
        )

    def _get_sweep_groups(
        self,
        direction: argutils.CharacterOrder | argutils.CharacterGroup | argutils.CharacterSort,
        *,
        reverse: bool,
    ) -> list[list[tte.EffectCharacter]]:
        """Schedule ordered groups or singletons, including all canvas fill."""
        return self.terminal.get_characters_grouped(
            order=direction,
            reverse=reverse,
            inner_fill_chars=True,
            outer_fill_chars=True,
        )

    def __next__(self) -> str:
        """Return the next frame in the effect."""
        while self.active_characters or not self.complete:
            for _ in range(self.config.travel_speed):
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
                if self.easer.is_complete():
                    break
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
