"""Text expands in a single row or column in the middle of the canvas then out.

Classes:
    MiddleOut: Text expands in a single row or column in the middle of the canvas then out.
    MiddleOutConfig: Configuration for the Middleout effect.
    MiddleOutIterator: Iterates over the effect's frames. Does not normally need to be called directly.

"""

from __future__ import annotations

import typing
from dataclasses import dataclass

from terminaltexteffects import Color, ColorPair, Coord, EffectCharacter, Gradient, easing
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argvalidators
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    """Get the effect class and its configuration class."""
    return MiddleOut, MiddleOutConfig


@argclass(
    name="middleout",
    help="Text expands in a single row or column in the middle of the canvas then out.",
    description="middleout | Text expands in a single row or column in the middle of the canvas then out.",
    epilog=(
        f"{argvalidators.EASING_EPILOG} Example: terminaltexteffects middleout --starting-color 8A008A "
        "--final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --expand-direction vertical "
        "--center-movement-speed 0.35 --full-movement-speed 0.35 --center-easing IN_OUT_SINE "
        "--full-easing IN_OUT_SINE"
    ),
)
@dataclass
class MiddleOutConfig(ArgsDataClass):
    """Configuration for the Middleout effect.

    Attributes:
        starting_color (Color): Color for the initial text in the center of the canvas.
        expand_direction (typing.Literal["vertical", "horizontal"]): Direction the text will expand. Choices: "
            "vertical, horizontal.
        center_movement_speed (float): Speed of the characters during the initial expansion of the center "
            "vertical/horiztonal. Valid values are n > 0.
        full_movement_speed (float): Speed of the characters during the final full expansion. Valid values are n > 0.
        center_easing (easing.EasingFunction): Easing function to use for initial expansion.
        full_easing (easing.EasingFunction): Easing function to use for full expansion.
        final_gradient_stops (tuple[Color, ...]): Tuple of colors for the final color gradient. If only one color "
            "is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Tuple of the number of gradient steps to use. More steps "
            "will create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient.

    """

    starting_color: Color = ArgField(
        cmd_name="--starting-color",
        type_parser=argvalidators.ColorArg.type_parser,
        default=Color("ffffff"),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Color for the initial text in the center of the canvas.",
    )  # type: ignore[assignment]
    """Color : Color for the initial text in the center of the canvas."""

    expand_direction: typing.Literal["vertical", "horizontal"] = ArgField(
        cmd_name="--expand-direction",
        default="vertical",
        choices=["vertical", "horizontal"],
        help="Direction the text will expand.",
    )  # type: ignore[assignment]
    """str : Direction the text will expand."""

    center_movement_speed: float = ArgField(
        cmd_name="--center-movement-speed",
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=0.35,
        metavar=argvalidators.PositiveFloat.METAVAR,
        help="Speed of the characters during the initial expansion of the center vertical/horiztonal line. ",
    )  # type: ignore[assignment]
    """float : Speed of the characters during the initial expansion of the center vertical/horiztonal line. """

    full_movement_speed: float = ArgField(
        cmd_name="--full-movement-speed",
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=0.35,
        metavar=argvalidators.PositiveFloat.METAVAR,
        help="Speed of the characters during the final full expansion. ",
    )  # type: ignore[assignment]
    """float : Speed of the characters during the final full expansion. """

    center_easing: easing.EasingFunction = ArgField(
        cmd_name="--center-easing",
        default=easing.in_out_sine,
        type_parser=argvalidators.Ease.type_parser,
        help="Easing function to use for initial expansion.",
    )  # type: ignore[assignment]
    """easing.EasingFunction : Easing function to use for initial expansion."""

    full_easing: easing.EasingFunction = ArgField(
        cmd_name="--full-easing",
        default=easing.in_out_sine,
        type_parser=argvalidators.Ease.type_parser,
        help="Easing function to use for full expansion.",
    )  # type: ignore[assignment]
    """easing.EasingFunction : Easing function to use for full expansion."""

    final_gradient_stops: tuple[Color, ...] = ArgField(
        cmd_name="--final-gradient-stops",
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(Color("8A008A"), Color("00D1FF"), Color("FFFFFF")),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied across the canvas). "
        "If only one color is provided, the characters will be displayed in that color.",
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
    """Gradient.Direction : Direction of the final gradient."""

    @classmethod
    def get_effect_class(cls) -> type[MiddleOut]:
        """Get the effect class associated with this configuration."""
        return MiddleOut


class MiddleOutIterator(BaseEffectIterator[MiddleOutConfig]):
    """Iterates over the frames of the MiddleOut effect."""

    def __init__(self, effect: MiddleOut) -> None:
        """Initialize the MiddleOut effect iterator.

        Args:
            effect (MiddleOut): The MiddleOut effect to iterate over.

        """
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self.phase = "center"
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
            character.motion.set_coordinate(self.terminal.canvas.center)
            # setup waypoints
            if self.config.expand_direction == "vertical":
                column = character.input_coord.column
                row = self.terminal.canvas.center_row
            else:
                column = self.terminal.canvas.center_column
                row = character.input_coord.row
            center_path = character.motion.new_path(
                speed=self.config.center_movement_speed,
                ease=self.config.center_easing,
            )
            center_path.new_waypoint(Coord(column, row))
            full_path = character.motion.new_path(
                path_id="full",
                speed=self.config.full_movement_speed,
                ease=self.config.full_easing,
            )
            full_path.new_waypoint(character.input_coord, waypoint_id="full")

            # setup scenes
            full_scene = character.animation.new_scene(scene_id="full")
            full_gradient = Gradient(self.config.starting_color, self.character_final_color_map[character], steps=10)
            full_scene.apply_gradient_to_symbols(character.input_symbol, 10, fg_gradient=full_gradient)

            # initialize character state
            character.motion.activate_path(center_path)
            character.animation.set_appearance(character.input_symbol, ColorPair(fg=self.config.starting_color))
            self.terminal.set_character_visibility(character, is_visible=True)
            self.active_characters.add(character)

    def __next__(self) -> str:
        """Return the next frame in the animation."""
        if self.phase == "center" and not self.active_characters:
            self.phase = "full"
            self.active_characters = set(self.terminal.get_characters())
            for character in self.active_characters:
                character.motion.activate_path(character.motion.query_path("full"))
                character.animation.activate_scene(character.animation.query_scene("full"))
        if self.active_characters:
            self.update()
            return self.frame
        raise StopIteration


class MiddleOut(BaseEffect[MiddleOutConfig]):
    """Text expands in a single row or column in the middle of the canvas then out.

    Attributes:
        effect_config (MiddleOutConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.

    """

    @property
    def _config_cls(self) -> type[MiddleOutConfig]:
        return MiddleOutConfig

    @property
    def _iterator_cls(self) -> type[MiddleOutIterator]:
        return MiddleOutIterator
