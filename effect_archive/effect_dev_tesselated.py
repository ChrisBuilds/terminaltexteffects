"""Effect Description.

Classes:

"""

from __future__ import annotations

from dataclasses import dataclass

import terminaltexteffects as tte
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.argutils import ArgSpec, ParserSpec
from terminaltexteffects.utils.spanningtree.algo.breadthfirst import BreadthFirst
from terminaltexteffects.utils.spanningtree.algo.primssimple import PrimsSimple


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Get the command, effect class, and configuration class for the effect.

    Returns:
        tuple[str, type[BaseEffect], type[BaseConfig]]: The command name, effect class, and configuration class.

    """
    return "tess", Effect, EffectConfig


@dataclass
class EffectConfig(BaseConfig):
    """Effect configuration dataclass."""

    parser_spec: ParserSpec = ParserSpec(
        name="tess",
        help="effect_description",
        description="effect_description",
        epilog=f"""{argutils.EASING_EPILOG}
    """,
    )

    color_single: tte.Color = ArgSpec(
        name="--color-single",
        type=argutils.ColorArg.type_parser,
        default=tte.Color(0),
        metavar=argutils.ColorArg.METAVAR,
        help="Color for the ___.",
    )  # pyright: ignore[reportAssignmentType]
    "Color: Color for the ___."

    final_gradient_stops: tuple[tte.Color, ...] = ArgSpec(
        name="--final-gradient-stops",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        default=(tte.Color("#8A008A"), tte.Color("#00D1FF"), tte.Color("#FFFFFF")),
        metavar=argutils.ColorArg.METAVAR,
        help=(
            "Space separated, unquoted, list of colors for the character gradient (applied across the canvas). "
            "If only one color is provided, the characters will be displayed in that color."
        ),
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[Color, ...]: Space separated, unquoted, list of colors for the character gradient "
        "(applied across the canvas). If only one color is provided, the characters will be displayed in that color."
    )

    final_gradient_steps: tuple[int, ...] | int = ArgSpec(
        name="--final-gradient-steps",
        type=argutils.PositiveInt.type_parser,
        nargs="+",
        default=12,
        metavar=argutils.PositiveInt.METAVAR,
        help=(
            "Space separated, unquoted, list of the number of gradient steps to use. More steps will "
            "create a smoother and longer gradient animation."
        ),
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[int, ...] | int: Space separated, unquoted, list of the number of gradient steps to use. More "
        "steps will create a smoother and longer gradient animation."
    )

    final_gradient_frames: int = ArgSpec(
        name="--final-gradient-frames",
        type=argutils.PositiveInt.type_parser,
        default=5,
        metavar=argutils.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step. Increase to slow down the gradient animation.",
    )  # pyright: ignore[reportAssignmentType]
    "int: Number of frames to display each gradient step. Increase to slow down the gradient animation."

    final_gradient_direction: tte.Gradient.Direction = ArgSpec(
        name="--final-gradient-direction",
        type=argutils.GradientDirection.type_parser,
        default=tte.Gradient.Direction.VERTICAL,
        metavar=argutils.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # pyright: ignore[reportAssignmentType]
    "Gradient.Direction : Direction of the final gradient."

    movement_speed: float = ArgSpec(
        name="--movement-speed",
        type=argutils.PositiveFloat.type_parser,
        default=1,
        metavar=argutils.PositiveFloat.METAVAR,
        help="Speed of the ___.",
    )  # pyright: ignore[reportAssignmentType]
    "float: Speed of the ___."

    easing: tte.easing.EasingFunction = ArgSpec(
        name="--easing",
        default=tte.easing.in_out_sine,
        type=argutils.Ease.type_parser,
        help="Easing function to use for character movement.",
    )  # pyright: ignore[reportAssignmentType]
    "easing.EasingFunction: Easing function to use for character movement."


class EffectIterator(BaseEffectIterator[EffectConfig]):
    """Effect iterator for the NamedEffect effect."""

    def __init__(self, effect: Effect) -> None:
        """Initialize the effect iterator.

        Args:
            effect (NamedEffect): The effect to iterate over.

        """
        super().__init__(effect)
        self.pending_chars: list[tte.EffectCharacter] = []
        self.character_final_color_map: dict[tte.EffectCharacter, tte.Color] = {}
        self.prims = PrimsSimple(
            self.terminal,
            starting_char=self.terminal.get_character_by_input_coord(
                self.terminal.canvas.text_center,
            ),
        )
        self.breadth_first = BreadthFirst(
            self.terminal,
            starting_char=self.terminal.get_character_by_input_coord(
                self.terminal.canvas.text_center,
            ),
            limit_to_text_boundary=True,
        )
        self.state = "pulse"
        self.sequence_easer = tte.easing.SequenceEaser(
            self.terminal.get_characters(),
            easing_function=tte.easing.in_out_expo,
        )
        self.chars_activated = 0
        self.total_chars = len(
            self.terminal.get_characters(inner_fill_chars=True, outer_fill_chars=True),
        )
        self.build()

    def build(self) -> None:
        """Build the effect."""
        tesselated_chars = [("/", "_", "\\", "_"), ("\\", "_", "/", "_")]
        final_gradient = tte.Gradient(
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
        glow_gradient = tte.Gradient(
            tte.Color("#000000"),
            tte.Color("#1F00AC"),
            tte.Color("#00EEFF"),
            tte.Color("#FFFFFF"),
            tte.Color("#00EEFF"),
            tte.Color("#1F00AC"),
            steps=(3, 3, 3, 3, 3),
            loop=True,
        )
        for character in self.terminal.get_characters(inner_fill_chars=True, outer_fill_chars=True):
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]

            character.animation.set_appearance(
                colors=tte.ColorPair(
                    fg=self.character_final_color_map[character],
                ),
            )
            self.terminal.set_character_visibility(character, is_visible=True)
            char = tesselated_chars[character.input_coord.row % 2][character.input_coord.column % 4]
            glow_scn = character.animation.new_scene(scene_id="glow")
            for color in glow_gradient:
                glow_scn.add_frame(symbol=char, duration=1, colors=tte.ColorPair(fg=color))
            glow_scn.add_frame(
                symbol=character.input_symbol,
                duration=1,
                colors=tte.ColorPair(fg=final_gradient_mapping[character.input_coord]),
            )
        while not self.prims.complete:
            self.prims.step()

    def __next__(self) -> str:
        """Return the next frame of the effect."""
        if self.active_characters or self.state != "complete":
            self.update()
            return self.frame
        raise StopIteration


class Effect(BaseEffect[EffectConfig]):
    """Effect description."""

    @property
    def _config_cls(self) -> type[EffectConfig]:
        return EffectConfig

    @property
    def _iterator_cls(self) -> type[EffectIterator]:
        return EffectIterator
