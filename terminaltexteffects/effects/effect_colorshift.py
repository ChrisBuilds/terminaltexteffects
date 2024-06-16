"""Display a gradient that shifts colors across the terminal.

Classes:
    ColorShift: Display a gradient that shifts colors across the terminal.
    ColorShiftConfig: Configuration for the ColorShift effect.
    ColorShiftIterator: Iterator for the ColorShift effect. Does not normally need to be called directly.
"""

from __future__ import annotations

import typing
from dataclasses import dataclass

import terminaltexteffects.utils.argvalidators as argvalidators
from terminaltexteffects.engine.base_character import EffectCharacter, EventHandler
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import geometry
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.graphics import Color, Gradient


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return ColorShift, ColorShiftConfig


@argclass(
    name="colorshift",
    help="Display a gradient that shifts colors across the terminal.",
    description="Display a gradient that shifts colors across the terminal.",
    epilog="""Example: terminaltexteffects colorshift --gradient-stops 0000ff ffffff 0000ff --gradient-steps 12
           --gradient-frames 10 --cycles 3 --travel --travel-direction radial --loop --final-gradient-stops 00c3ff ffff1c --final-gradient-steps 12""",
)
@dataclass
class ColorShiftConfig(ArgsDataClass):
    """Configuration for the ColorShift effect.

    Attributes:
        gradient_stops (tuple[Color, ...]): Tuple of colors for the gradient. If only one color is provided, the characters will be displayed in that color.
        gradient_steps (tuple[int, ...] | int): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. Valid values are n > 0.
        gradient_frames (int): Number of frames to display each gradient step. Increase to slow down the gradient animation.
        gradient_direction (Gradient.Direction): Direction of the gradient across the canvas.
        loop_gradient (bool): Loop the gradient. This causes the final gradient color to transition back to the first gradient color.
        travel (bool): Display the gradient as a traveling wave.
        travel_direction (Gradient.Direction): Direction the gradient travels across the canvas.
        reverse_travel_direction (bool): Reverse the gradient travel direction.
        cycles (int): Number of times to cycle the gradient. Use 0 for infinite. Valid values are n >= 0.
        skip_final_gradient (bool): Skip the final gradient.
        final_gradient_stops (tuple[Color, ...]): Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Tuple of the number of gradient steps to use for the final gradient. More steps will create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient across the canvas.
    """

    gradient_stops: tuple[Color, ...] = ArgField(
        cmd_name=["--gradient-stops"],
        type_parser=argvalidators.ColorArg.type_parser,
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
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the gradient.",
    )  # type: ignore[assignment]
    "tuple[Color, ...] : Tuple of colors for the gradient. If only one color is provided, the characters will be displayed in that color."

    gradient_steps: tuple[int, ...] | int = ArgField(
        cmd_name="--gradient-steps",
        type_parser=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=12,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Number of gradient steps to use. More steps will create a smoother gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] | int : Int or Tuple of ints for the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    gradient_frames: int = ArgField(
        cmd_name="--gradient-frames",
        type_parser=argvalidators.PositiveInt.type_parser,
        default=5,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step. Increase to slow down the gradient animation.",
    )  # type: ignore[assignment]
    "int : Number of frames to display each gradient step. Increase to slow down the gradient animation."

    travel: bool = ArgField(
        cmd_name="--travel",
        action="store_true",
        help="Display the gradient as a traveling wave",
    )  # type: ignore[assignment]
    "bool : Display the gradient as a traveling wave."

    travel_direction: Gradient.Direction = ArgField(
        cmd_name="--travel-direction",
        default=Gradient.Direction.HORIZONTAL,
        type_parser=argvalidators.GradientDirection.type_parser,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction the gradient travels across the canvas.",
    )  # type: ignore[assignment]
    "Gradient.Direction : Direction the gradient travels across the canvas."

    reverse_travel_direction: bool = ArgField(
        cmd_name="--reverse-travel-direction",
        action="store_true",
        help="Reverse the gradient travel direction.",
    )  # type: ignore[assignment]
    "bool : Reverse the gradient travel direction."

    loop_gradient: bool = ArgField(
        cmd_name="--loop-gradient",
        action="store_true",
        help="Loop the gradient. This causes the final gradient color to transition back to the first gradient color.",
    )  # type: ignore[assignment]
    "bool : Loop the gradient. This causes the final gradient color to transition back to the first gradient color."

    cycles: int = ArgField(
        cmd_name="--cycles",
        type_parser=argvalidators.PositiveInt.type_parser,
        default=3,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Number of times to cycle the gradient.",
    )  # type: ignore[assignment]
    "int : Number of times to cycle the gradient. Use 0 for infinite."

    skip_final_gradient: bool = ArgField(
        cmd_name="--skip-final-gradient",
        action="store_true",
        help="Skip the final gradient.",
    )  # type: ignore[assignment]
    "bool : Skip the final gradient."

    final_gradient_stops: tuple[Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=argvalidators.ColorArg.type_parser,
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
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] | int = ArgField(
        cmd_name=["--final-gradient-steps"],
        type_parser=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=12,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] | int : Int or Tuple of ints for the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_direction: Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=argvalidators.GradientDirection.type_parser,
        default=Gradient.Direction.VERTICAL,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]
    "Gradient.Direction : Direction of the final gradient."

    @classmethod
    def get_effect_class(cls):
        return ColorShift


class ColorShiftIterator(BaseEffectIterator[ColorShiftConfig]):
    def __init__(self, effect: "ColorShift") -> None:
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self.loop_tracker_map: dict[EffectCharacter, int] = {}
        self.build()

    def loop_tracker(self, character: EffectCharacter) -> None:
        self.loop_tracker_map[character] = self.loop_tracker_map.get(character, 0) + 1
        if self.config.cycles == 0 or (self.loop_tracker_map[character] < self.config.cycles):
            character.animation.activate_scene(character.animation.query_scene("gradient"))
        else:
            if not self.config.skip_final_gradient:
                character.animation.activate_scene(character.animation.query_scene("final_gradient"))

    def build(self) -> None:
        final_gradient = Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.canvas.top, self.terminal.canvas.right, self.config.final_gradient_direction
        )
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]
        gradient = Gradient(
            *self.config.gradient_stops, steps=self.config.gradient_steps, loop=self.config.loop_gradient
        )
        for character in self.terminal.get_characters():
            self.terminal.set_character_visibility(character, True)
            gradient_scn = character.animation.new_scene(id="gradient")
            if self.config.travel:
                if self.config.travel_direction == Gradient.Direction.HORIZONTAL:
                    direction_index = character.input_coord.column / self.terminal.canvas.right
                elif self.config.travel_direction == Gradient.Direction.VERTICAL:
                    direction_index = character.input_coord.row / self.terminal.canvas.top
                elif self.config.travel_direction == Gradient.Direction.DIAGONAL:
                    direction_index = (character.input_coord.row + character.input_coord.column) / (
                        self.terminal.canvas.right + self.terminal.canvas.top
                    )
                elif self.config.travel_direction == Gradient.Direction.RADIAL:
                    direction_index = geometry.find_normalized_distance_from_center(
                        self.terminal.canvas.height,
                        self.terminal.canvas.width,
                        character.input_coord,
                    )
                shift_distance = int(len(gradient.spectrum) * direction_index)
                if self.config.reverse_travel_direction:
                    shift_distance = shift_distance * -1
                colors = gradient.spectrum[shift_distance:] + gradient.spectrum[:shift_distance]
            else:
                colors = gradient.spectrum
            for color in colors:
                gradient_scn.add_frame(character.input_symbol, self.config.gradient_frames, color=color)
            final_color_scn = character.animation.new_scene(id="final_gradient")
            for color in Gradient(colors[-1], self.character_final_color_map[character], steps=8):
                final_color_scn.add_frame(character.input_symbol, self.config.gradient_frames, color=color)
            character.animation.activate_scene(gradient_scn)
            self.active_characters.append(character)
            character.event_handler.register_event(
                EventHandler.Event.SCENE_COMPLETE,
                gradient_scn,
                EventHandler.Action.CALLBACK,
                EventHandler.Callback(self.loop_tracker),
            )

    def __next__(self) -> str:
        if self.pending_chars or self.active_characters:
            # perform effect logic
            self.update()
            return self.frame
        else:
            raise StopIteration


class ColorShift(BaseEffect[ColorShiftConfig]):
    """Display a gradient that shifts colors across the terminal."""

    _config_cls = ColorShiftConfig
    _iterator_cls = ColorShiftIterator

    def __init__(self, input_data: str) -> None:
        """Initialize the effect with the provided input data.

        Args:
            input_data (str): The input data to use for the effect."""
        super().__init__(input_data)
