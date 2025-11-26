"""Runs a specular highlight across the text.

Classes:
    Highlight: Runs a specular highlight across the text.
    HighlightConfig: Configuration for the Highlight effect.
    HighlightIterator: Effect iterator for the Highlight effect.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import Animation, Color, ColorPair, EffectCharacter, Gradient, easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.argutils import ArgSpec, CharacterGroup, ParserSpec


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Get the command, effect class, and configuration class for the effect.

    Returns:
        tuple[str, type[BaseEffect], type[BaseConfig]]: The command name, effect class, and configuration class.

    """
    return "highlight", Highlight, HighlightConfig


@dataclass
class HighlightConfig(BaseConfig):
    """Configuration for the Highlight effect.

    Attributes:
        highlight_brightness (float): Brightness of the highlight color. Values less than 1 will darken the highlight
            color, while values greater than 1 will brighten the highlight color.
        highlight_direction (CharacterGroup): Direction the highlight will travel.
        highlight_width (int): Width of the highlight. n >= 1
        final_gradient_stops (tuple[Color, ...]): Tuple of colors for the final color gradient. If only one color is
            provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Int or Tuple of ints for the number of gradient steps to use.
            More steps will create a smoother and longer gradient animation.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient.

    """

    parser_spec: ParserSpec = ParserSpec(
        name="highlight",
        help="Run a specular highlight across the text.",
        description="highlight | Run a specular highlight across the text.",
        epilog=(
            f"{argutils.EASING_EPILOG}Example: terminaltexteffects highlight --highlight-brightness 1.5 "
            "--highlight-direction "
            "diagonal_bottom_left_to_top_right --highlight-width 8 --final-gradient-stops 8A008A 00D1FF FFFFFF "
            "--final-gradient-steps 12 --final-gradient-direction vertical"
        ),
    )

    highlight_brightness: float = ArgSpec(
        name="--highlight-brightness",
        type=argutils.PositiveFloat.type_parser,
        default=1.75,
        metavar=argutils.PositiveFloat.METAVAR,
        help="Brightness of the highlight color. Values less than 1 will darken the highlight color, while values "
        "greater than 1 will brighten the highlight color.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "float : Brightness of the highlight color. Values less than 1 will darken the highlight color, while "
        "values greater than 1 will brighten the highlight color."
    )

    highlight_direction: CharacterGroup = ArgSpec(
        name="--highlight-direction",
        default=CharacterGroup.DIAGONAL_BOTTOM_LEFT_TO_TOP_RIGHT,
        metavar=" ".join(argutils.CharacterGroupArg.METAVAR),
        help="Direction the highlight will travel.",
        type=argutils.CharacterGroupArg.type_parser,
    )  # pyright: ignore[reportAssignmentType]
    ("CharacterGroup : Direction the highlight will travel.")

    highlight_width: int = ArgSpec(
        name="--highlight-width",
        type=argutils.PositiveInt.type_parser,
        default=8,
        metavar=argutils.PositiveInt.METAVAR,
        help="Width of the highlight. n >= 1",
    )  # pyright: ignore[reportAssignmentType]
    "int : Width of the highlight. n >= 1"

    final_gradient_stops: tuple[Color, ...] = ArgSpec(
        name="--final-gradient-stops",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=(Color("#8A008A"), Color("#00D1FF"), Color("#FFFFFF")),
        metavar=argutils.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied across the canvas). If "
        "only one color is provided, the characters will be displayed in that color.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the "
        "characters will be displayed in that color."
    )

    final_gradient_steps: tuple[int, ...] | int = ArgSpec(
        name="--final-gradient-steps",
        type=argutils.PositiveInt.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=12,
        metavar=argutils.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a "
        "smoother and longer gradient animation.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[int, ...] | int : Int or Tuple of ints for the number of gradient steps to use. More steps will "
        "create a smoother and longer gradient animation."
    )

    final_gradient_direction: Gradient.Direction = ArgSpec(
        name="--final-gradient-direction",
        type=argutils.GradientDirection.type_parser,
        default=Gradient.Direction.VERTICAL,
        metavar=argutils.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # pyright: ignore[reportAssignmentType]
    "Gradient.Direction : Direction of the final gradient."


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
        self.easer = easing.SequenceEaser(
            sequence=self.terminal.get_characters_grouped(self.config.highlight_direction),
            easing_function=easing.in_out_circ,
        )
        self.build()

    def build(self) -> None:
        """Build the effect."""
        final_gradient = Gradient(
            *self.config.final_gradient_stops,
            steps=self.config.final_gradient_steps,
        )
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
            highlight_color = Animation.adjust_color_brightness(
                base_color,
                self.config.highlight_brightness,
            )
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
                specular_highlight_scn.add_frame(
                    character.input_symbol,
                    2,
                    colors=ColorPair(fg=color),
                )
            self.terminal.set_character_visibility(character, is_visible=True)

    def __next__(self) -> str:
        """Return the next frame in the animation."""
        if self.active_characters or not self.easer.is_complete():
            self.easer.step()
            for group in self.easer.added:
                for character in group:
                    character.animation.activate_scene("highlight")
                    self.active_characters.add(character)

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
