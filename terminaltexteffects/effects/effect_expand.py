"""Characters expand from the center.

Classes:
    Expand: Characters expand from the center.
    ExpandConfig: Configuration for the Expand effect.
    ExpandIterator: Iterates over the effect.
"""

from __future__ import annotations

import typing
from dataclasses import dataclass

from terminaltexteffects import Color, EffectCharacter, EventHandler, Gradient, easing
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argvalidators
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    """Get the effect class and its configuration class."""
    return Expand, ExpandConfig


@argclass(
    name="expand",
    help="Expands the text from a single point.",
    description="expand | Expands the text from a single point.",
    epilog=(
        f"{argvalidators.EASING_EPILOG}"
        "Example: terminaltexteffects expand --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 "
        "--final-gradient-frames 5 --movement-speed 0.35 --expand-easing IN_OUT_QUART"
    ),
)
@dataclass
class ExpandConfig(ArgsDataClass):
    """Configuration for the Expand effect.

    Attributes:
        movement_speed (float): Movement speed of the characters.
        expand_easing (easing.EasingFunction): Easing function to use for character movement.
        final_gradient_stops (tuple[Color, ...]): Tuple of colors for the final color gradient. If only one color is
            provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Tuple of the number of gradient steps to use. More steps will
            create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_frames (int): Number of frames to display each gradient step. Increase to slow down the
            gradient animation.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient.

    """

    expand_easing: easing.EasingFunction = ArgField(
        cmd_name="--expand-easing",
        default=easing.in_out_quart,
        type_parser=argvalidators.Ease.type_parser,
        help="Easing function to use for character movement.",
    )  # type: ignore[assignment]
    "easing.EasingFunction : Easing function to use for character movement."

    movement_speed: float = ArgField(
        cmd_name="--movement-speed",
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=0.35,
        metavar=argvalidators.PositiveFloat.METAVAR,
        help="Movement speed of the characters. ",
    )  # type: ignore[assignment]
    "float : Movement speed of the characters. "

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

    final_gradient_frames: int = ArgField(
        cmd_name="--final-gradient-frames",
        type_parser=argvalidators.PositiveInt.type_parser,
        default=5,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step. Increase to slow down the gradient animation.",
    )  # type: ignore[assignment]
    "int : Number of frames to display each gradient step. Increase to slow down the gradient animation."

    final_gradient_direction: Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=argvalidators.GradientDirection.type_parser,
        default=Gradient.Direction.VERTICAL,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]
    "Gradient.Direction : Direction of the final gradient."

    @classmethod
    def get_effect_class(cls) -> type[Expand]:
        """Get the effect class associated with this configuration."""
        return Expand


class ExpandIterator(BaseEffectIterator[ExpandConfig]):
    """Iterates over the Expand effect."""

    def __init__(
        self,
        effect: Expand,
    ) -> None:
        """Initialize the Expand effect iterator.

        Args:
            effect (Expand): The effect to use for the iterator.

        """
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self.build()

    def build(self) -> None:
        """Build the Expand effect."""
        final_gradient = Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.canvas.text_bottom,
            self.terminal.canvas.text_top,
            self.terminal.canvas.text_left,
            self.terminal.canvas.text_right,
            self.config.final_gradient_direction,
        )
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]
        for character in self.terminal.get_characters():
            character.motion.set_coordinate(self.terminal.canvas.center)
            input_coord_path = character.motion.new_path(
                speed=self.config.movement_speed,
                ease=self.config.expand_easing,
            )
            input_coord_path.new_waypoint(character.input_coord)
            self.terminal.set_character_visibility(character, is_visible=True)
            self.active_characters.add(character)
            character.event_handler.register_event(
                EventHandler.Event.PATH_ACTIVATED,
                input_coord_path,
                EventHandler.Action.SET_LAYER,
                1,
            )
            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE,
                input_coord_path,
                EventHandler.Action.SET_LAYER,
                0,
            )
            character.motion.activate_path(input_coord_path)
            gradient_scn = character.animation.new_scene()
            gradient = Gradient(final_gradient.spectrum[0], self.character_final_color_map[character], steps=10)
            gradient_scn.apply_gradient_to_symbols(
                character.input_symbol,
                self.config.final_gradient_frames,
                fg_gradient=gradient,
            )
            character.animation.activate_scene(gradient_scn)

    def __next__(self) -> str:
        """Return the next frame in the animation."""
        if self.active_characters:
            self.update()
            return self.frame
        raise StopIteration


class Expand(BaseEffect[ExpandConfig]):
    """Characters expand from the center.

    Attributes:
        effect_config (ExpandConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.

    """

    @property
    def _config_cls(self) -> type[ExpandConfig]:
        return ExpandConfig

    @property
    def _iterator_cls(self) -> type[ExpandIterator]:
        return ExpandIterator
