"""Display a gradient that shifts colors across the terminal.

Classes:
    ColorShift: Display a gradient that shifts colors across the terminal.
    ColorShiftConfig: Configuration for the ColorShift effect.
    ColorShiftIterator: Iterator for the ColorShift effect. Does not normally need to be called directly.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import Color, EffectCharacter, EventHandler, Gradient, geometry
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.argutils import ArgSpec, ParserSpec
from terminaltexteffects.utils.graphics import ColorPair


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Get the command, effect class, and configuration class for the effect.

    Returns:
        tuple[str, type[BaseEffect], type[BaseConfig]]: The command name, effect class, and configuration class.

    """
    return "colorshift", ColorShift, ColorShiftConfig


@dataclass
class ColorShiftConfig(BaseConfig):
    """Configuration for the ColorShift effect.

    Attributes:
        gradient_stops (tuple[Color, ...]): Tuple of colors for the gradient. If only one color is provided, the
            characters will be displayed in that color.
        gradient_steps (tuple[int, ...] | int): Tuple of the number of gradient steps to use. More steps will create
            a smoother and longer gradient animation. Valid values are n > 0.
        gradient_frames (int): Number of frames to display each gradient step. Increase to slow down the
            gradient animation.
        no_loop (bool): Do not loop the gradient. If not set, the gradient generation will loop the final gradient
            color back to the first gradient color.
        travel (bool): Display the gradient as a traveling wave.
        travel_direction (Gradient.Direction): Direction the gradient travels across the canvas.
        reverse_travel_direction (bool): Reverse the gradient travel direction.
        cycles (int): Number of times to cycle the gradient. Use 0 for infinite. Valid values are n >= 0.
        skip_final_gradient (bool): Skip the final gradient.
        final_gradient_stops (tuple[Color, ...]): Tuple of colors for the final color gradient. If only one color
            is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Tuple of the number of gradient steps to use for the final
            gradient. More steps will create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient across the canvas.

    """

    parser_spec: ParserSpec = ParserSpec(
        name="colorshift",
        help="Display a gradient that shifts colors across the terminal.",
        description="Display a gradient that shifts colors across the terminal.",
        epilog=(
            "Example: terminaltexteffects colorshift --gradient-stops 0000ff ffffff 0000ff "
            "--gradient-steps 12 --gradient-frames 10 --cycles 3 --travel --travel-direction radial --final-gradient-stops "
            "00c3ff ffff1c --final-gradient-steps 12"
        ),
    )

    gradient_stops: tuple[Color, ...] = ArgSpec(
        name="--gradient-stops",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        default=(
            Color("e81416"),
            Color("ffa500"),
            Color("faeb36"),
            Color("79c314"),
            Color("487de7"),
            Color("4b369d"),
            Color("70369d"),
        ),
        metavar=argutils.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the gradient.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[Color, ...] : Tuple of colors for the gradient. If only one color is provided, the characters will "
        "be displayed in that color."
    )

    gradient_steps: tuple[int, ...] | int = ArgSpec(
        name="--gradient-steps",
        type=argutils.PositiveInt.type_parser,
        nargs="+",
        default=12,
        metavar=argutils.PositiveInt.METAVAR,
        help="Number of gradient steps to use. More steps will create a smoother gradient animation.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[int, ...] | int : Int or Tuple of ints for the number of gradient steps to use. More steps will "
        "create a smoother and longer gradient animation."
    )

    gradient_frames: int = ArgSpec(
        name="--gradient-frames",
        type=argutils.PositiveInt.type_parser,
        default=5,
        metavar=argutils.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step. Increase to slow down the gradient animation.",
    )  # pyright: ignore[reportAssignmentType]
    "int : Number of frames to display each gradient step. Increase to slow down the gradient animation."

    travel: bool = ArgSpec(
        name="--travel",
        default=False,
        action="store_true",
        help="Display the gradient as a traveling wave",
    )  # pyright: ignore[reportAssignmentType]
    "bool : Display the gradient as a traveling wave."

    travel_direction: Gradient.Direction = ArgSpec(
        name="--travel-direction",
        default=Gradient.Direction.HORIZONTAL,
        type=argutils.GradientDirection.type_parser,
        metavar=argutils.GradientDirection.METAVAR,
        help="Direction the gradient travels across the canvas.",
    )  # pyright: ignore[reportAssignmentType]
    "Gradient.Direction : Direction the gradient travels across the canvas."

    reverse_travel_direction: bool = ArgSpec(
        name="--reverse-travel-direction",
        default=False,
        action="store_true",
        help="Reverse the gradient travel direction.",
    )  # pyright: ignore[reportAssignmentType]
    "bool : Reverse the gradient travel direction."

    no_loop: bool = ArgSpec(
        name="--no-loop",
        default=False,
        action="store_true",
        help="Do not loop the gradient. If not set, the gradient generation will loop the final gradient "
        "color back to the first gradient color.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "bool : Do not loop the gradient. If not set, the gradient generation will loop the final gradient color "
        "back to the first gradient color."
    )

    cycles: int = ArgSpec(
        name="--cycles",
        type=argutils.PositiveInt.type_parser,
        default=3,
        metavar=argutils.PositiveInt.METAVAR,
        help="Number of times to cycle the gradient.",
    )  # pyright: ignore[reportAssignmentType]
    "int : Number of times to cycle the gradient. Use 0 for infinite."

    skip_final_gradient: bool = ArgSpec(
        name="--skip-final-gradient",
        default=False,
        action="store_true",
        help="Skip the final gradient.",
    )  # pyright: ignore[reportAssignmentType]
    "bool : Skip the final gradient."

    final_gradient_stops: tuple[Color, ...] = ArgSpec(
        name="--final-gradient-stops",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        default=(
            Color("e81416"),
            Color("ffa500"),
            Color("faeb36"),
            Color("79c314"),
            Color("487de7"),
            Color("4b369d"),
            Color("70369d"),
        ),
        metavar=argutils.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied across the canvas). "
        "If only one color is provided, the characters will be displayed in that color.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the "
        "characters will be displayed in that color."
    )

    final_gradient_steps: tuple[int, ...] | int = ArgSpec(
        name="--final-gradient-steps",
        type=argutils.PositiveInt.type_parser,
        nargs="+",
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


class ColorShiftIterator(BaseEffectIterator[ColorShiftConfig]):
    """Iterator for the ColorShift effect."""

    def __init__(self, effect: ColorShift) -> None:
        """Initialize the iterator with the provided effect.

        Args:
            effect (ColorShift): The effect to use for the iterator.

        """
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self.loop_tracker_map: dict[EffectCharacter, int] = {}
        self.build()

    def loop_tracker(self, character: EffectCharacter) -> None:
        """Track the number of times a character has looped through the gradient."""
        self.loop_tracker_map[character] = self.loop_tracker_map.get(character, 0) + 1
        if self.config.cycles == 0 or (self.loop_tracker_map[character] < self.config.cycles):
            character.animation.activate_scene("gradient")
        elif not self.config.skip_final_gradient:
            character.animation.activate_scene("final_gradient")

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
        gradient = Gradient(*self.config.gradient_stops, steps=self.config.gradient_steps, loop=not self.config.no_loop)
        for character in self.terminal.get_characters():
            self.terminal.set_character_visibility(character, is_visible=True)
            gradient_scn = character.animation.new_scene(scene_id="gradient")
            if self.config.travel:
                if self.config.travel_direction == Gradient.Direction.HORIZONTAL:
                    direction_index = character.input_coord.column / self.terminal.canvas.right
                elif self.config.travel_direction == Gradient.Direction.VERTICAL:
                    direction_index = character.input_coord.row / self.terminal.canvas.top
                elif self.config.travel_direction == Gradient.Direction.DIAGONAL:
                    direction_index = (character.input_coord.row + character.input_coord.column) / (
                        self.terminal.canvas.right + self.terminal.canvas.top
                    )
                else:  # radial
                    direction_index = geometry.find_normalized_distance_from_center(
                        self.terminal.canvas.text_bottom,
                        self.terminal.canvas.text_top,
                        self.terminal.canvas.text_left,
                        self.terminal.canvas.text_right,
                        character.input_coord,
                    )
                shift_distance = int(len(gradient.spectrum) * direction_index)
                if self.config.reverse_travel_direction:
                    shift_distance = shift_distance * -1
                colors = gradient.spectrum[shift_distance:] + gradient.spectrum[:shift_distance]
            else:
                colors = gradient.spectrum
            for color in colors:
                gradient_scn.add_frame(
                    character.input_symbol,
                    self.config.gradient_frames,
                    colors=ColorPair(fg=color),
                )
            final_color_scn = character.animation.new_scene(scene_id="final_gradient")
            for color in Gradient(colors[-1], self.character_final_color_map[character], steps=8):
                final_color_scn.add_frame(
                    character.input_symbol,
                    self.config.gradient_frames,
                    colors=ColorPair(fg=color),
                )
            character.animation.activate_scene(gradient_scn)
            self.active_characters.add(character)
            character.event_handler.register_event(
                EventHandler.Event.SCENE_COMPLETE,
                gradient_scn,
                EventHandler.Action.CALLBACK,
                EventHandler.Callback(self.loop_tracker),
            )

    def __next__(self) -> str:
        """Return the next frame in the animation."""
        if self.pending_chars or self.active_characters:
            # perform effect logic
            self.update()
            return self.frame
        raise StopIteration


class ColorShift(BaseEffect[ColorShiftConfig]):
    """Display a gradient that shifts colors across the terminal."""

    @property
    def _config_cls(self) -> type[ColorShiftConfig]:
        return ColorShiftConfig

    @property
    def _iterator_cls(self) -> type[ColorShiftIterator]:
        return ColorShiftIterator
