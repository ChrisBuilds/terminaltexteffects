"""Characters fall from the top of the canvas as bouncy balls before settling into place.

Classes:
    BouncyBalls: Characters fall from the top of the canvas as bouncy balls before settling into place.
    BouncyBallsConfig: Configuration for the BouncyBalls effect.
    BouncyBallsIterator: Iterator for the BouncyBalls effect. Does not normally need to be called directly.

"""

from __future__ import annotations

import random
import typing
from dataclasses import dataclass

from terminaltexteffects import Color, Coord, EffectCharacter, Gradient, easing
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argvalidators
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.graphics import ColorPair


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    """Get the effect class and its configuration class."""
    return BouncyBalls, BouncyBallsConfig


@argclass(
    name="bouncyballs",
    help="Characters are bouncy balls falling from the top of the canvas.",
    description="bouncyballs | Characters are bouncy balls falling from the top of the canvas.",
    epilog=f"{argvalidators.EASING_EPILOG}"
    "Example: terminaltexteffects bouncyballs --ball-colors d1f4a5 96e2a4 5acda9 --ball-symbols o '*' O 0 . "
    "--final-gradient-stops f8ffae 43c6ac --final-gradient-steps 12 --final-gradient-direction diagonal "
    "--ball-delay 7 --movement-speed 0.25 --easing OUT_BOUNCE",
)
@dataclass
class BouncyBallsConfig(ArgsDataClass):
    """Configuration for the BouncyBalls effect.

    Attributes:
        ball_colors (tuple[Color, ...]): Tuple of colors from which ball colors will be randomly selected.
            If no colors are provided, the colors are random.
        ball_symbols (tuple[str, ...] | str): Tuple of symbols to use for the balls.
        final_gradient_stops (tuple[Color, ...]): Tuple of colors for the final color gradient. If only one color
            is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Tuple of the number of gradient steps to use. More steps
            will create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient.
        ball_delay (int): Number of frames between ball drops, increase to reduce ball drop rate.
            Valid values are n > 0.
        movement_speed (float): Movement speed of the characters.  Valid values are n > 0.
        easing (easing.EasingFunction): Easing function to use for character movement.

    """

    ball_colors: tuple[Color, ...] = ArgField(
        cmd_name=["--ball-colors"],
        type_parser=argvalidators.ColorArg.type_parser,
        metavar=argvalidators.ColorArg.METAVAR,
        nargs="+",
        default=(Color("d1f4a5"), Color("96e2a4"), Color("5acda9")),
        help="Space separated list of colors from which ball colors will be randomly selected. If no colors are "
        "provided, the colors are random.",
    )  # type: ignore[assignment]
    "tuple[Color, ...] : Tuple of colors from which ball colors will be randomly selected. If no colors are "
    "provided, the colors are random."

    ball_symbols: tuple[str, ...] = ArgField(
        cmd_name="--ball-symbols",
        type_parser=argvalidators.Symbol.type_parser,
        nargs="+",
        default=("*", "o", "O", "0", "."),
        metavar=argvalidators.Symbol.METAVAR,
        help="Space separated list of symbols to use for the balls.",
    )  # type: ignore[assignment]
    "tuple[str, ...] | str : Tuple of symbols to use for the balls."

    ball_delay: int = ArgField(
        cmd_name="--ball-delay",
        type_parser=argvalidators.NonNegativeInt.type_parser,
        default=7,
        metavar=argvalidators.NonNegativeInt.METAVAR,
        help="Number of frames between ball drops, increase to reduce ball drop rate.",
    )  # type: ignore[assignment]
    "int : Number of frames between ball drops, increase to reduce ball drop rate."

    movement_speed: float = ArgField(
        cmd_name="--movement-speed",
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=0.25,
        metavar=argvalidators.PositiveFloat.METAVAR,
        help="Movement speed of the characters. ",
    )  # type: ignore[assignment]
    "float : Movement speed of the characters. "

    movement_easing: easing.EasingFunction = ArgField(
        cmd_name="--movement-easing",
        type_parser=argvalidators.Ease.type_parser,
        default=easing.out_bounce,
        help="Easing function to use for character movement.",
    )  # type: ignore[assignment]
    "easing.EasingFunction : Easing function to use for character movement."

    final_gradient_stops: tuple[Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(Color("f8ffae"), Color("43c6ac")),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied across the canvas). "
        "If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the "
    "characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] | int = ArgField(
        cmd_name=["--final-gradient-steps"],
        type_parser=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=12,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a "
        "smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] | int : Int or Tuple of ints for the number of gradient steps to use. More steps will create "
    "a smoother and longer gradient animation."

    final_gradient_direction: Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=argvalidators.GradientDirection.type_parser,
        default=Gradient.Direction.DIAGONAL,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]
    "Gradient.Direction : Direction of the final gradient."

    @classmethod
    def get_effect_class(cls) -> type[BouncyBalls]:
        """Get the effect class associated with this configuration."""
        return BouncyBalls


class BouncyBallsIterator(BaseEffectIterator[BouncyBallsConfig]):
    """Iterator for the BouncyBalls effect."""

    def __init__(self, effect: BouncyBalls) -> None:
        """Initialize the effect iterator.

        Args:
            effect (BouncyBalls): The effect to use for the iterator.

        """
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.group_by_row: dict[int, list[EffectCharacter | None]] = {}
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self.build()

    def build(self) -> None:
        """Build the initial state of the effect."""
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
            color = random.choice(self.config.ball_colors)
            symbol = random.choice(self.config.ball_symbols)
            ball_scene = character.animation.new_scene()
            ball_scene.add_frame(symbol, 1, colors=ColorPair(fg=color))
            final_scene = character.animation.new_scene()
            char_final_gradient = Gradient(color, self.character_final_color_map[character], steps=10)
            final_scene.apply_gradient_to_symbols(character.input_symbol, 10, fg_gradient=char_final_gradient)
            character.motion.set_coordinate(
                Coord(character.input_coord.column, int(self.terminal.canvas.top * random.uniform(1.0, 1.5))),
            )
            input_coord_path = character.motion.new_path(
                speed=self.config.movement_speed,
                ease=self.config.movement_easing,
            )
            input_coord_path.new_waypoint(character.input_coord)
            character.motion.activate_path(input_coord_path)
            character.animation.activate_scene(ball_scene)
            character.event_handler.register_event(
                character.event_handler.Event.PATH_COMPLETE,
                input_coord_path,
                character.event_handler.Action.ACTIVATE_SCENE,
                final_scene,
            )
            self.pending_chars.append(character)
        for character in sorted(self.pending_chars, key=lambda c: c.input_coord.row):
            if character.input_coord.row not in self.group_by_row:
                self.group_by_row[character.input_coord.row] = []
            self.group_by_row[character.input_coord.row].append(character)
        self.pending_chars.clear()
        self.ball_delay = 0

    def __next__(self) -> str:
        """Return the next frame in the animation."""
        if self.group_by_row or self.active_characters or self.pending_chars:
            if not self.pending_chars and self.group_by_row:
                self.pending_chars.extend(self.group_by_row.pop(min(self.group_by_row.keys())))  # type: ignore[arg-type]
            if self.pending_chars:
                if self.ball_delay == 0:
                    for _ in range(random.randint(2, 6)):
                        if self.pending_chars:
                            next_character = self.pending_chars.pop(random.randint(0, len(self.pending_chars) - 1))
                            self.terminal.set_character_visibility(next_character, is_visible=True)
                            self.active_characters.add(next_character)
                        else:
                            break
                    self.ball_delay = self.config.ball_delay
                else:
                    self.ball_delay -= 1

            self.update()
            return self.frame
        raise StopIteration


class BouncyBalls(BaseEffect[BouncyBallsConfig]):
    """Characters fall from the top of the canvas as bouncy balls before settling into place.

    Attributes:
        effect_config (BouncyBallsConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.

    """

    @property
    def _config_cls(self) -> type[BouncyBallsConfig]:
        return BouncyBallsConfig

    @property
    def _iterator_cls(self) -> type[BouncyBallsIterator]:
        return BouncyBallsIterator
