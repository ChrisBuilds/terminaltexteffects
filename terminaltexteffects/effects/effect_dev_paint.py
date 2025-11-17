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
from terminaltexteffects.utils.spanningtree.algo.primsweighted import PrimsWeighted


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Get the command, effect class, and configuration class for the effect.

    Returns:
        tuple[str, type[BaseEffect], type[BaseConfig]]: The command name, effect class, and configuration class.

    """
    return "dev_paint", Effect, EffectConfig


@dataclass
class EffectConfig(BaseConfig):
    """Effect configuration dataclass."""

    parser_spec: ParserSpec = ParserSpec(
        name="dev_paint",
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
        self.gen_alg = PrimsWeighted(self.terminal, limit_to_text_boundary=True)
        self.fill_alg = BreadthFirst(
            self.terminal,
            starting_char=self.terminal.get_character_by_input_coord(
                self.terminal.canvas.random_coord(within_text_boundary=True),
            ),
        )
        self.build()

    def build(self) -> None:
        """Build the effect."""
        final_gradient = tte.Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.canvas.text_bottom,
            self.terminal.canvas.text_top,
            self.terminal.canvas.text_left,
            self.terminal.canvas.text_right,
            self.config.final_gradient_direction,
        )
        smoke_gradient = tte.Gradient(
            tte.Color("#242424"),
            tte.Color("#FFFFFF"),
            *self.config.final_gradient_stops[::-1],
            steps=(3, 4),
        )
        smoke_symbols = ("░", "▒", "▓", "▒", "░")
        for character in self.terminal.get_characters(inner_fill_chars=True, outer_fill_chars=True):
            self.terminal.set_character_visibility(character=character, is_visible=True)
            character.animation.set_appearance(character.input_symbol, colors=tte.ColorPair("#7A7A7A"))
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]
            paint_gradient = tte.Gradient(
                *self.config.final_gradient_stops,
                final_gradient_mapping[character.input_coord],
                steps=5,
            )
            paint_chars = (character.input_symbol,)
            paint_scn = character.animation.new_scene(scene_id="paint")
            paint_scn.apply_gradient_to_symbols(paint_chars, duration=5, fg_gradient=paint_gradient)

            smoke_scn = character.animation.new_scene(scene_id="smoke")
            smoke_scn.apply_gradient_to_symbols(smoke_symbols, 3, fg_gradient=smoke_gradient)
            character.event_handler.register_event(
                event=tte.Event.SCENE_COMPLETE,
                caller=smoke_scn,
                action=tte.Action.ACTIVATE_SCENE,
                target=paint_scn,
            )

        while not self.gen_alg.complete:
            self.gen_alg.step()
        if self.fill_alg.starting_char:
            self.fill_alg.starting_char.animation.activate_scene("smoke")
            self.active_characters.add(self.fill_alg.starting_char)
            self.terminal.set_character_visibility(self.fill_alg.starting_char, is_visible=True)

    def __next__(self) -> str:
        """Return the next frame of the effect."""
        if not self.fill_alg.complete or self.active_characters:
            for _ in range(1):
                if not self.fill_alg.complete:
                    self.fill_alg.step()
                    if self.fill_alg.explored_last_step:
                        for char in self.fill_alg.explored_last_step:
                            self.terminal.set_character_visibility(char, is_visible=True)
                            char.animation.activate_scene("smoke")
                            self.active_characters.add(char)

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
