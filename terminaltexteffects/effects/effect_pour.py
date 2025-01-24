"""Pours the characters back and forth from the top, bottom, left, or right.

Classes:
    Pour: Pours the characters back and forth from the top, bottom, left, or right.
    PourConfig: Configuration for the Pour effect.
    PourIterator: Iterates over the frames of the Pour effect. Does not normally need to be called directly.
"""

from __future__ import annotations

import typing
from dataclasses import dataclass
from enum import Enum, auto

from terminaltexteffects import Color, Coord, EffectCharacter, Gradient, Terminal, easing
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argvalidators
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    """Get the effect class and its configuration class."""
    return Pour, PourConfig


@argclass(
    name="pour",
    help="Pours the characters into position from the given direction.",
    description="pour | Pours the characters into position from the given direction.",
    epilog=(
        f"{argvalidators.EASING_EPILOG} Example: terminaltexteffects pour --pour-direction down "
        "--movement-speed 0.2 --gap 1 --starting-color FFFFFF --final-gradient-stops 8A008A 00D1FF FFFFFF "
        "--easing IN_QUAD"
    ),
)
@dataclass
class PourConfig(ArgsDataClass):
    """Configuration for the Pour effect.

    Attributes:
        pour_direction (str): Direction the text will pour. Valid values are "up", "down", "left", and "right".
        pour_speed (int): Number of characters poured in per tick. Increase to speed up the effect. "
            "Valid values are n > 0.
        movement_speed (float): Movement speed of the characters. Valid values are n > 0.
        gap (int): Number of frames to wait between each character in the pour effect. Increase to slow down effect "
            "and create a more defined back and forth motion. Valid values are n >= 0.
        starting_color (Color): Color of the characters before the gradient starts.
        final_gradient_stops (tuple[Color, ...]): Tuple of colors for the character gradient. If only one color "
            "is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Number of gradient steps to use. More steps will create a "
            "smoother and longer gradient animation.
        final_gradient_frames (int): Number of frames to display each gradient step. Increase to slow down the "
            "gradient animation.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient.
        easing (easing.EasingFunction): Easing function to use for character movement.

    """

    pour_direction: typing.Literal["up", "down", "left", "right"] = ArgField(
        cmd_name=["--pour-direction"],
        default="down",
        choices=["up", "down", "left", "right"],
        help="Direction the text will pour.",
    )  # type: ignore[assignment]
    "typing.Literal['up', 'down', 'left', 'right'] : Direction the text will pour."

    pour_speed: int = ArgField(
        cmd_name="--pour-speed",
        type_parser=argvalidators.PositiveInt.type_parser,
        default=1,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Number of characters poured in per tick. Increase to speed up the effect.",
    )  # type: ignore[assignment]
    "int : Number of characters poured in per tick. Increase to speed up the effect."

    movement_speed: float = ArgField(
        cmd_name="--movement-speed",
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=0.2,
        metavar=argvalidators.PositiveFloat.METAVAR,
        help="Movement speed of the characters. ",
    )  # type: ignore[assignment]
    "float : Movement speed of the characters."

    gap: int = ArgField(
        cmd_name="--gap",
        type_parser=argvalidators.NonNegativeInt.type_parser,
        default=1,
        metavar=argvalidators.NonNegativeInt.METAVAR,
        help="Number of frames to wait between each character in the pour effect. Increase to slow down effect "
        "and create a more defined back and forth motion.",
    )  # type: ignore[assignment]
    "int : Number of frames to wait between each character in the pour effect."

    starting_color: Color = ArgField(
        cmd_name=["--starting-color"],
        type_parser=argvalidators.ColorArg.type_parser,
        default=Color("ffffff"),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Color of the characters before the gradient starts.",
    )  # type: ignore[assignment]
    "Color : Color of the characters before the gradient starts."

    final_gradient_stops: tuple[Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(Color("8A008A"), Color("00D1FF"), Color("FFFFFF")),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient. If only one color is provided, "
        "the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[Color, ...] : Tuple of colors for the character gradient."

    final_gradient_steps: tuple[int, ...] | int = ArgField(
        cmd_name=["--final-gradient-steps"],
        type_parser=argvalidators.PositiveInt.type_parser,
        default=12,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] | int : Int or Tuple of ints for the number of gradient steps to use."

    final_gradient_frames: int = ArgField(
        cmd_name=["--final-gradient-frames"],
        type_parser=argvalidators.PositiveInt.type_parser,
        default=10,
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

    movement_easing: easing.EasingFunction = ArgField(
        cmd_name="--movement-easing",
        default=easing.in_quad,
        type_parser=argvalidators.Ease.type_parser,
        help="Easing function to use for character movement.",
    )  # type: ignore[assignment]
    "easing.EasingFunction : Easing function to use for character movement."

    @classmethod
    def get_effect_class(cls) -> type[Pour]:
        """Get the effect class associated with this configuration."""
        return Pour


class PourIterator(BaseEffectIterator[PourConfig]):
    """Iterator for the Pour effect."""

    class PourDirection(Enum):
        """Pour direction enumeration."""

        UP = auto()
        DOWN = auto()
        LEFT = auto()
        RIGHT = auto()

    def __init__(self, effect: Pour) -> None:
        """Initialize the iterator with the provided effect.

        Args:
            effect (Pour): The effect to use for the iterator.

        """
        super().__init__(effect)
        self.pending_groups: list[list[EffectCharacter]] = []
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self.build()

    def build(self) -> None:
        """Build the initial state of the effect."""
        self._pour_direction = {
            "down": PourIterator.PourDirection.DOWN,
            "up": PourIterator.PourDirection.UP,
            "left": PourIterator.PourDirection.LEFT,
            "right": PourIterator.PourDirection.RIGHT,
        }.get(self.config.pour_direction, PourIterator.PourDirection.DOWN)
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
        sort_map = {
            PourIterator.PourDirection.DOWN: Terminal.CharacterGroup.ROW_BOTTOM_TO_TOP,
            PourIterator.PourDirection.UP: Terminal.CharacterGroup.ROW_TOP_TO_BOTTOM,
            PourIterator.PourDirection.LEFT: Terminal.CharacterGroup.COLUMN_LEFT_TO_RIGHT,
            PourIterator.PourDirection.RIGHT: Terminal.CharacterGroup.COLUMN_RIGHT_TO_LEFT,
        }
        groups = self.terminal.get_characters_grouped(grouping=sort_map[self._pour_direction])
        for i, group in enumerate(groups):
            for character in group:
                self.terminal.set_character_visibility(character, is_visible=False)
                if self._pour_direction == PourIterator.PourDirection.DOWN:
                    character.motion.set_coordinate(Coord(character.input_coord.column, self.terminal.canvas.top))
                elif self._pour_direction == PourIterator.PourDirection.UP:
                    character.motion.set_coordinate(Coord(character.input_coord.column, self.terminal.canvas.bottom))
                elif self._pour_direction == PourIterator.PourDirection.LEFT:
                    character.motion.set_coordinate(Coord(self.terminal.canvas.right, character.input_coord.row))
                elif self._pour_direction == PourIterator.PourDirection.RIGHT:
                    character.motion.set_coordinate(Coord(self.terminal.canvas.left, character.input_coord.row))
                input_coord_path = character.motion.new_path(
                    speed=self.config.movement_speed,
                    ease=self.config.movement_easing,
                )
                input_coord_path.new_waypoint(character.input_coord)
                character.motion.activate_path(input_coord_path)

                pour_gradient = Gradient(
                    self.config.starting_color,
                    self.character_final_color_map[character],
                    steps=self.config.final_gradient_steps,
                )
                pour_scn = character.animation.new_scene()
                pour_scn.apply_gradient_to_symbols(
                    character.input_symbol,
                    self.config.final_gradient_frames,
                    fg_gradient=pour_gradient,
                )
                character.animation.activate_scene(pour_scn)
            if i % 2 == 0:
                self.pending_groups.append(group)
            else:
                self.pending_groups.append(group[::-1])
        self.gap = 0
        self.current_group = self.pending_groups.pop(0)

    def __next__(self) -> str:
        """Return the next frame in the animation."""
        if self.pending_groups or self.active_characters or self.current_group:
            if not self.current_group and self.pending_groups:
                self.current_group = self.pending_groups.pop(0)
            if self.current_group:
                if not self.gap:
                    for _ in range(self.config.pour_speed):
                        if self.current_group:
                            next_character = self.current_group.pop(0)
                            self.terminal.set_character_visibility(next_character, is_visible=True)
                            self.active_characters.add(next_character)
                    self.gap = self.config.gap
                else:
                    self.gap -= 1
            self.update()
            return self.frame
        raise StopIteration


class Pour(BaseEffect[PourConfig]):
    """Pours the characters back and forth from the top, bottom, left, or right.

    Attributes:
        effect_config (PourConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.

    """

    @property
    def _config_cls(self) -> type[PourConfig]:
        return PourConfig

    @property
    def _iterator_cls(self) -> type[PourIterator]:
        return PourIterator
