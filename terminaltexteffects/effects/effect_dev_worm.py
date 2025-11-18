"""Effect Description.

Classes:

"""

from __future__ import annotations

import random
from dataclasses import dataclass

import terminaltexteffects as tte
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.argutils import ArgSpec, ParserSpec
from terminaltexteffects.utils.spanningtree.algo.aldousbroder import AldousBroder


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Get the command, effect class, and configuration class for the effect.

    Returns:
        tuple[str, type[BaseEffect], type[BaseConfig]]: The command name, effect class, and configuration class.

    """
    return "dev_worm", Effect, EffectConfig


@dataclass
class EffectConfig(BaseConfig):
    """Effect configuration dataclass."""

    parser_spec: ParserSpec = ParserSpec(
        name="dev_worm",
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
        action=argutils.TupleAction,
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
        action=argutils.TupleAction,
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
        self.alg = AldousBroder(self.terminal)
        self.worm_body: list[tte.EffectCharacter] = []
        self.worm_body_dir_map = {"north": "|", "south": "|", "east": "-", "west": "-"}
        self.skipped_frames = 0
        self.speed_up = 4
        self.build()

    def update_worm(self) -> None:
        current_pos = self.alg.char_last_linked or self.alg.linked_char_last_visited
        if current_pos is None:
            return
        current_pos.animation.set_appearance("o")
        self.worm_body.insert(0, current_pos)

        if len(self.worm_body) > 1:
            for direction, symbol in self.worm_body_dir_map.items():
                if current_pos is self.worm_body[1].neighbors.get(direction):
                    self.worm_body[1].animation.set_appearance(symbol)
                    break
            if len(self.worm_body) > 9:
                removed_char = self.worm_body.pop()
                if removed_char not in self.worm_body:
                    removed_char.animation.set_appearance(
                        removed_char.input_symbol,
                        colors=tte.ColorPair(self.character_final_color_map.get(removed_char)),
                    )

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
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]

        for char in self.terminal.get_characters(inner_fill_chars=True, outer_fill_chars=True):
            char.animation.set_appearance(
                "█",
                colors=tte.ColorPair(random.choice(("#5E3501", "#422601", "#A86002", "#584730", "#8A7861"))),
            )
            self.terminal.set_character_visibility(char, is_visible=True)

    def __next__(self) -> str:
        """Return the next frame of the effect."""
        if not self.alg.complete or self.active_characters:
            if not self.alg.complete:
                self.alg.step()
                self.update_worm()
                while not self.alg.char_last_linked and self.skipped_frames < self.speed_up:
                    self.alg.step()
                    self.update_worm()
                    self.skipped_frames += 1
                if self.skipped_frames > self.speed_up:
                    self.speed_up += 1
                self.skipped_frames = 0
                if linked_char := self.alg.char_last_linked:
                    self.speed_up = 4
                    linked_char.animation.set_appearance(
                        symbol=linked_char.input_symbol,
                        colors=tte.ColorPair(self.character_final_color_map.get(linked_char)),
                    )

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
