"""Runs a specular highlight across the text.

Classes:
    Highlight: Runs a specular highlight across the text.
    HighlightConfig: Configuration for the Highlight effect.
    HighlightIterator: Effect iterator for the Highlight effect.
"""

from __future__ import annotations

import typing
from dataclasses import dataclass

from terminaltexteffects import Animation, Color, ColorPair, EffectCharacter, Gradient, easing
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argvalidators
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    """Get the effect class and its configuration class."""
    return Highlight, HighlightConfig


@argclass(
    name="highlight",
    help="Run a specular highlight across the text.",
    description="highlight | Run a specular highlight across the text.",
    epilog=(
        "Example: terminaltexteffects highlight --highlight-brightness 1.5 --highlight-direction "
        "diagonal_bottom_left_to_top_right --highlight-width 8 --final-gradient-stops 8A008A 00D1FF FFFFFF "
        "--final-gradient-steps 12 --final-gradient-direction vertical"
    ),
)
@dataclass
class HighlightConfig(ArgsDataClass):
    """Configuration for the Highlight effect.

    Attributes:
        highlight_brightness (float): Brightness of the highlight color. Values less than 1 will darken the highlight
            color, while values greater than 1 will brighten the highlight color.
        highlight_direction (typing.Literal['column_left_to_right','row_top_to_bottom','row_bottom_to_top', diagonal_top_left_to_bottom_right', 'diagonal_bottom_left_to_top_right', 'diagonal_top_right_to_bottom_left', 'diagonal_bottom_right_to_top_left',]): Direction the highlight will travel.
        highlight_width (int): Width of the highlight. n >= 1
        final_gradient_stops (tuple[Color, ...]): Tuple of colors for the final color gradient. If only one color is
            provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Int or Tuple of ints for the number of gradient steps to use.
            More steps will create a smoother and longer gradient animation.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient.

    """  # noqa: E501 # long type hint for highlight_direction required for mkdocs to associate the name: description pair

    highlight_brightness: float = ArgField(
        cmd_name="--highlight-brightness",
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=1.75,
        metavar=argvalidators.PositiveFloat.METAVAR,
        help="Brightness of the highlight color. Values less than 1 will darken the highlight color, while values "
        "greater than 1 will brighten the highlight color.",
    )  # type: ignore[assignment]
    (
        "float : Brightness of the highlight color. Values less than 1 will darken the highlight color, while "
        "values greater than 1 will brighten the highlight color."
    )

    highlight_direction: typing.Literal[
        "column_left_to_right",
        "row_top_to_bottom",
        "row_bottom_to_top",
        "diagonal_top_left_to_bottom_right",
        "diagonal_bottom_left_to_top_right",
        "diagonal_top_right_to_bottom_left",
        "diagonal_bottom_right_to_top_left",
        "outside_to_center",
        "center_to_outside",
    ] = ArgField(
        cmd_name="--highlight-direction",
        default="diagonal_bottom_left_to_top_right",
        choices=[
            "column_left_to_right",
            "column_right_to_left",
            "row_top_to_bottom",
            "row_bottom_to_top",
            "diagonal_top_left_to_bottom_right",
            "diagonal_bottom_left_to_top_right",
            "diagonal_top_right_to_bottom_left",
            "diagonal_bottom_right_to_top_left",
            "outside_to_center",
            "center_to_outside",
        ],
        help="Direction the highlight will travel.",
    )  # type: ignore[assignment]
    (
        "typing.Literal['column_left_to_right','row_top_to_bottom','row_bottom_to_top',"
        "'diagonal_top_left_to_bottom_right','diagonal_bottom_left_to_top_right',"
        "'diagonal_top_right_to_bottom_left','diagonal_bottom_right_to_top_left',] : Direction the "
        "highlight will travel."
    )

    highlight_width: int = ArgField(
        cmd_name="--highlight-width",
        type_parser=argvalidators.PositiveInt.type_parser,
        default=8,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Width of the highlight. n >= 1",
    )  # type: ignore[assignment]
    "int : Width of the highlight. n >= 1"

    final_gradient_stops: tuple[Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(Color("8A008A"), Color("00D1FF"), Color("FFFFFF")),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied across the canvas). If "
        "only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    (
        "tuple[Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the "
        "characters will be displayed in that color."
    )

    final_gradient_steps: tuple[int, ...] | int = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=12,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a "
        "smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    (
        "tuple[int, ...] | int : Int or Tuple of ints for the number of gradient steps to use. More steps will "
        "create a smoother and longer gradient animation."
    )

    final_gradient_direction: Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=argvalidators.GradientDirection.type_parser,
        default=Gradient.Direction.VERTICAL,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]
    "Gradient.Direction : Direction of the final gradient."

    @classmethod
    def get_effect_class(cls) -> type[Highlight]:
        """Get the effect class associated with this configuration."""
        return Highlight


class HighlightIterator(BaseEffectIterator[HighlightConfig]):
    """Effect iterator for the Highlight effect."""

    def __init__(self, effect: Highlight) -> None:
        """Initialize the Highlight effect iterator.

        Args:
            effect (Highlight): The Highlight effect to iterate over.

        """
        super().__init__(effect)
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self.pending_characters: list[list[EffectCharacter]] = []
        self.easer = easing.eased_step_function(easing.in_out_circ, 0.01)
        self.groups_activated = 0
        self.sort_map = {
            "column_left_to_right": self.terminal.CharacterGroup.COLUMN_LEFT_TO_RIGHT,
            "column_right_to_left": self.terminal.CharacterGroup.COLUMN_RIGHT_TO_LEFT,
            "row_top_to_bottom": self.terminal.CharacterGroup.ROW_TOP_TO_BOTTOM,
            "row_bottom_to_top": self.terminal.CharacterGroup.ROW_BOTTOM_TO_TOP,
            "diagonal_top_left_to_bottom_right": self.terminal.CharacterGroup.DIAGONAL_TOP_LEFT_TO_BOTTOM_RIGHT,
            "diagonal_bottom_left_to_top_right": self.terminal.CharacterGroup.DIAGONAL_BOTTOM_LEFT_TO_TOP_RIGHT,
            "diagonal_top_right_to_bottom_left": self.terminal.CharacterGroup.DIAGONAL_TOP_RIGHT_TO_BOTTOM_LEFT,
            "diagonal_bottom_right_to_top_left": self.terminal.CharacterGroup.DIAGONAL_BOTTOM_RIGHT_TO_TOP_LEFT,
            "center_to_outside": self.terminal.CharacterGroup.CENTER_TO_OUTSIDE_DIAMONDS,
            "outside_to_center": self.terminal.CharacterGroup.OUTSIDE_TO_CENTER_DIAMONDS,
        }
        self.pending_characters = self.terminal.get_characters_grouped(self.sort_map[self.config.highlight_direction])
        self.total_groups = len(self.pending_characters)
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
        for character in self.terminal.get_characters():
            base_color = final_gradient_mapping[character.input_coord]
            self.character_final_color_map[character] = base_color
            highlight_color = Animation.adjust_color_brightness(base_color, self.config.highlight_brightness)
            highlight_gradient = Gradient(
                base_color,
                highlight_color,
                highlight_color,
                base_color,
                steps=(3, self.config.highlight_width, 3),
            )
            character.animation.set_appearance(character.input_symbol, ColorPair(fg=base_color))
            specular_highlight_scn = character.animation.new_scene(scene_id="highlight")
            for color in highlight_gradient:
                specular_highlight_scn.add_frame(character.input_symbol, 2, colors=ColorPair(fg=color))
            self.terminal.set_character_visibility(character, is_visible=True)
            self.active_characters.add(character)

    def __next__(self) -> str:
        """Return the next frame in the animation."""
        if self.active_characters or self.pending_characters:
            _, eased_percentage = self.easer()
            while (self.groups_activated / self.total_groups) < eased_percentage:
                if self.pending_characters:
                    next_group = self.pending_characters.pop(0)
                    for character in next_group:
                        scn = character.animation.query_scene("highlight")
                        character.animation.activate_scene(scn)
                        self.active_characters.add(character)
                    self.groups_activated += 1

            self.update()
            return self.frame

        raise StopIteration


class Highlight(BaseEffect[HighlightConfig]):
    """Run a specular highlight across the text."""

    @property
    def _config_cls(self) -> type[HighlightConfig]:
        return HighlightConfig

    @property
    def _iterator_cls(self) -> type[HighlightIterator]:
        return HighlightIterator
