"""Performs a wipe across the terminal to reveal characters.

Classes:
    Wipe: Performs a wipe across the terminal to reveal characters.
    WipeConfig: Configuration for the Wipe effect.
    WipeIterator: Effect iterator for the Wipe effect. Does not normally need to be called directly.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import Color, EffectCharacter, Gradient, easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.argutils import ArgSpec, CharacterGroup, ParserSpec


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Get the command, effect class, and configuration class for the effect.

    Returns:
        tuple[str, type[BaseEffect], type[BaseConfig]]: The command name, effect class, and configuration class.

    """
    return "wipe", Wipe, WipeConfig


@dataclass
class WipeConfig(BaseConfig):
    """Configuration for the Wipe effect.

    Attributes:
        wipe_direction (CharacterGroup): Direction the text will wipe.
        wipe_delay (int): Number of frames to wait before adding the next character group. Increase, to
            slow down the effect. Valid values are n >= 0.
        final_gradient_stops (tuple[Color, ...]): Tuple of colors for the wipe gradient.
        final_gradient_steps (tuple[int, ...] | int): Tuple of the number of gradient steps to use. More steps will
            create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_frames (int): Number of frames to display each gradient step. Increase to slow down the
            gradient animation.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient.

    """

    parser_spec: ParserSpec = ParserSpec(
        name="wipe",
        help="Wipes the text across the terminal to reveal characters.",
        description="wipe | Wipes the text across the terminal to reveal characters.",
        epilog=(
            f"{argutils.EASING_EPILOG} Example: terminaltexteffects wipe --wipe-direction "
            "diagonal_bottom_left_to_top_right "
            "--final-gradient-stops 833ab4 fd1d1d fcb045 --final-gradient-steps 12 "
            "--final-gradient-frames 5 --wipe-delay 0"
        ),
    )

    wipe_direction: CharacterGroup = ArgSpec(
        name="--wipe-direction",
        default="diagonal_bottom_left_to_top_right",
        type=argutils.CharacterGroupArg.type_parser,
        help="Direction the text will wipe.",
    )  # pyright: ignore[reportAssignmentType]
    "CharacterGroup : Direction the text will wipe."

    wipe_delay: int = ArgSpec(
        name="--wipe-delay",
        type=argutils.NonNegativeInt.type_parser,
        default=0,
        metavar=argutils.NonNegativeInt.METAVAR,
        help="Number of frames to wait before adding the next character group. Increase, to slow down the effect.",
    )  # pyright: ignore[reportAssignmentType]
    "int : Number of frames to wait before adding the next character group. Increase, to slow down the effect."

    wipe_ease: easing.EasingFunction = ArgSpec(
        name="--wipe-ease",
        type=argutils.Ease.type_parser,
        default=easing.in_out_circ,
        help="Easing function to use for the wipe effect.",
    )  # pyright: ignore[reportAssignmentType]
    "easing.EasingFunction : Easing function to use for the wipe effect."

    final_gradient_stops: tuple[Color, ...] = ArgSpec(
        name="--final-gradient-stops",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=(Color("#833ab4"), Color("#fd1d1d"), Color("#fcb045")),
        metavar=argutils.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the wipe gradient.",
    )  # pyright: ignore[reportAssignmentType]
    "tuple[Color, ...] : Tuple of colors for the wipe gradient."

    final_gradient_steps: tuple[int, ...] | int = ArgSpec(
        name="--final-gradient-steps",
        type=argutils.PositiveInt.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=12,
        metavar=argutils.PositiveInt.METAVAR,
        help="Number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[int, ...] | int : Int or Tuple of ints for the number of gradient steps to use. More steps will "
        "create a smoother and longer gradient animation."
    )

    final_gradient_frames: int = ArgSpec(
        name="--final-gradient-frames",
        type=argutils.PositiveInt.type_parser,
        default=3,
        metavar=argutils.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step. Increase to slow down the gradient animation.",
    )  # pyright: ignore[reportAssignmentType]
    "int : Number of frames to display each gradient step. Increase to slow down the gradient animation."

    final_gradient_direction: Gradient.Direction = ArgSpec(
        name="--final-gradient-direction",
        type=argutils.GradientDirection.type_parser,
        default=Gradient.Direction.VERTICAL,
        metavar=argutils.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # pyright: ignore[reportAssignmentType]
    "Gradient.Direction : Direction of the final gradient."


class WipeIterator(BaseEffectIterator[WipeConfig]):
    """Effect iterator for the Wipe effect."""

    def __init__(self, effect: Wipe) -> None:
        """Initialize the effect iterator.

        Args:
            effect (Wipe): The effect to use for the iterator.

        """
        super().__init__(effect)
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self.easer = easing.SequenceEaser(
            self.terminal.get_characters_grouped(self.config.wipe_direction),
            easing_function=self.config.wipe_ease,
        )
        self._wipe_delay = self.config.wipe_delay
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
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]
            wipe_scn = character.animation.new_scene(scene_id="wipe")
            wipe_gradient = Gradient(
                final_gradient.spectrum[0],
                self.character_final_color_map[character],
                steps=self.config.final_gradient_steps,
            )
            wipe_scn.apply_gradient_to_symbols(
                character.input_symbol,
                self.config.final_gradient_frames,
                fg_gradient=wipe_gradient,
            )

    def __next__(self) -> str:
        """Return the next frame in the animation."""
        if self.active_characters or not self.easer.is_complete():
            if self._wipe_delay == 0:
                self.easer.step()
                for group in self.easer.added:
                    for character in group:
                        character.animation.activate_scene("wipe")
                        self.terminal.set_character_visibility(character, is_visible=True)
                        self.active_characters.add(character)
                for group in self.easer.removed:
                    for character in group:
                        character.animation.deactivate_scene()
                        character.animation.query_scene("wipe").reset_scene()
                        self.terminal.set_character_visibility(character, is_visible=False)
                self._wipe_delay = self.config.wipe_delay
            self.update()
            return self.frame

        raise StopIteration


class Wipe(BaseEffect[WipeConfig]):
    """Performs a wipe across the terminal to reveal characters.

    Attributes:
        effect_config (WipeConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.

    """

    @property
    def _config_cls(self) -> type[WipeConfig]:
        return WipeConfig

    @property
    def _iterator_cls(self) -> type[WipeIterator]:
        return WipeIterator
