"""A laser etches characters onto the terminal.

Classes:
    LaserEtch: A laser etches characters onto the terminal.
    LaserEtchConfig: Configuration for the LaserEtch effect.
    LaserEtchIterator: Iterator for the LaserEtch effect.

"""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass

import terminaltexteffects as tte
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.argutils import ArgSpec, CharacterGroup, ParserSpec
from terminaltexteffects.utils.spanningtree.algo.recursivebacktracker import RecursiveBacktracker


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Get the command, effect class, and configuration class for the effect.

    Returns:
        tuple[str, type[BaseEffect], type[BaseConfig]]: The command name, effect class, and configuration class.

    """
    return "laseretch", LaserEtch, LaserEtchConfig


def _etch_pattern_type_parser(value: str) -> CharacterGroup | str:
    if value == "algorithm":
        return "algorithm"
    return argutils.CharacterGroupArg.type_parser(value)


@dataclass
class LaserEtchConfig(BaseConfig):
    """LaserEtch effect configuration dataclass.

    Attributes:
        etch_direction (typing.Literal['column_left_to_right','row_top_to_bottom','row_bottom_to_top',diagonal_top_left_to_bottom_right','diagonal_bottom_left_to_top_right','diagonal_top_right_to_bottom_left','diagonal_bottom_right_to_top_left']): Pattern used to etch the text.
        etch_speed (int): Along with etch_delay, determines the speed at which the characters are etched onto the terminal.
            This value specifies the number of characters to etch simultaneously.
        etch_delay (int): Along with etch_speed, determines the speed at which the characters are etched onto the terminal.
            This values specifies the number of frames to wait before etching the next group of characters.
        cool_gradient_stops (tuple[tte.Color, ...]): Space separated, unquoted, list of colors for the gradient used to
            cool the characters after etching. If only one color is provided, the characters will be displayed in that color.
        laser_gradient_stops (tuple[tte.Color, ...]): Space separated, unquoted, list of colors for the laser gradient.
            If only one color is provided, the characters will be displayed in that color.
        spark_gradient_stops (tuple[tte.Color, ...]): Space separated, unquoted, list of colors for the spark cooling gradient.
            If only one color is provided, the characters will be displayed in that color.
        spark_cooling_frames (int): Number of frames to display each spark cooling gradient step. Increase to slow down the
            rate of cooling.
        final_gradient_stops (tuple[tte.Color, ...]): Space separated, unquoted, list of colors for the character gradient
            (applied across the canvas). If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Space separated, unquoted, list of the number of gradient steps to use.
            More steps will create a smoother and longer gradient animation.
        final_gradient_frames (int): Number of frames to display each gradient step.
            Increase to slow down the gradient animation.
        final_gradient_direction (tte.Gradient.Direction): Direction of the final gradient.

    """  # noqa: E501

    parser_spec: ParserSpec = ParserSpec(
        name="laseretch",
        help="A laser etches characters onto the terminal.",
        description="A laser etches characters onto the terminal.",
        epilog=(
            "Example: terminaltexteffects laseretch --etch-speed 2 --etch-delay 5 --etch-direction "
            "row_top_to_bottom --cool-gradient-stops ffe680 ff7b00 --laser-gradient-stops ffffff 376cff "
            "--spark-gradient-stops ffffff ffe680 ff7b00 1a0900 --spark-cooling-frames 10 --final-gradient-stops "
            "8A008A 00D1FF ffffff --final-gradient-steps 8  --final-gradient-frames 5 "
            "--final-gradient-direction vertical"
        ),
    )

    etch_pattern: CharacterGroup = ArgSpec(
        name="--etch-pattern",
        default="algorithm",
        type=_etch_pattern_type_parser,
        metavar="algorithm " + " ".join(argutils.CharacterGroupArg.METAVAR),
        help="Pattern used to etch the text.",
    )  # pyright: ignore[reportAssignmentType]
    "CharacterGroup: Pattern used to etch the text."

    etch_speed: int = ArgSpec(
        name="--etch-speed",
        type=argutils.PositiveInt.type_parser,
        default=1,
        metavar=argutils.PositiveInt.METAVAR,
        help="Along with etch_delay, determines the speed at which the characters are etched onto the terminal. "
        "This value specifies the number of characters to etch simultaneously.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "int: Along with etch_delay, determines the speed at which the characters are etched onto the terminal. "
        "This value specifies the number of characters to etch simultaneously."
    )

    etch_delay: int = ArgSpec(
        name="--etch-delay",
        type=argutils.NonNegativeInt.type_parser,
        default=1,
        metavar=argutils.NonNegativeInt.METAVAR,
        help="Along with etch_speed, determines the speed at which the characters are etched onto the terminal. "
        "This values specifies the number of frames to wait before etching the next set of characters.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "int: Along with etch_speed, determines the speed at which the characters are etched onto the terminal. "
        "This values specifies the number of frames to wait before etching the next set of characters."
    )

    cool_gradient_stops: tuple[tte.Color, ...] = ArgSpec(
        name="--cool-gradient-stops",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=(tte.Color("#ffe680"), tte.Color("#ff7b00")),
        metavar=argutils.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the gradient used to cool the characters after etching. "
        "If only one color is provided, the characters will be displayed in that color.",
    )  # pyright: ignore[reportAssignmentType]
    "tuple[Color, ...]: Space separated, unquoted, list of colors for the cooling gradient "
    "If only one color is provided, the characters will be displayed in that color."

    laser_gradient_stops: tuple[tte.Color, ...] = ArgSpec(
        name="--laser-gradient-stops",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=(tte.Color("#ffffff"), tte.Color("#376cff")),
        metavar=argutils.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the laser gradient. "
        "If only one color is provided, the characters will be displayed in that color.",
    )  # pyright: ignore[reportAssignmentType]
    "tuple[Color, ...]: Space separated, unquoted, list of colors for the laser gradient. "
    "If only one color is provided, the characters will be displayed in that color."

    spark_gradient_stops: tuple[tte.Color, ...] = ArgSpec(
        name="--spark-gradient-stops",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=(tte.Color("#ffffff"), tte.Color("#ffe680"), tte.Color("#ff7b00"), tte.Color("#1a0900")),
        metavar=argutils.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the spark cooling gradient. "
        "If only one color is provided, the characters will be displayed in that color.",
    )  # pyright: ignore[reportAssignmentType]
    "tuple[Color, ...]: Space separated, unquoted, list of colors for the spark cooling gradient. "
    "If only one color is provided, the characters will be displayed in that color."

    spark_cooling_frames: int = ArgSpec(
        name="--spark-cooling-frames",
        type=argutils.PositiveInt.type_parser,
        default=7,
        metavar=argutils.PositiveInt.METAVAR,
        help="Number of frames to display each spark cooling gradient step. Increase to slow down the rate of cooling.",
    )  # pyright: ignore[reportAssignmentType]
    "int: Number of frames to display each spark cooling gradient step. Increase to slow down the rate of cooling."

    final_gradient_stops: tuple[tte.Color, ...] = ArgSpec(
        name="--final-gradient-stops",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=(tte.Color("#8A008A"), tte.Color("#00D1FF"), tte.Color("#ffffff")),
        metavar=argutils.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied across the canvas). "
        "If only one color is provided, the characters will be displayed in that color.",
    )  # pyright: ignore[reportAssignmentType]
    "tuple[Color, ...]: Space separated, unquoted, list of colors for the character gradient "
    "(applied across the canvas). If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] | int = ArgSpec(
        name="--final-gradient-steps",
        type=argutils.PositiveInt.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=8,
        metavar=argutils.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a "
        "smoother and longer gradient animation.",
    )  # pyright: ignore[reportAssignmentType]
    "tuple[int, ...] | int: Space separated, unquoted, list of the number of gradient steps to use. More steps will "
    "create a smoother and longer gradient animation."

    final_gradient_frames: int = ArgSpec(
        name="--final-gradient-frames",
        type=argutils.PositiveInt.type_parser,
        default=4,
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


class LaserEtchIterator(BaseEffectIterator[LaserEtchConfig]):
    """Iterator for the LaserEtch effect."""

    class Laser:
        """A class to represent a laser beam effect in a terminal.

        The Laser class is responsible for creating and managing a laser beam effect
        in a terminal. It handles the initialization of the laser beam, the creation
        of spark effects, repositioning of the laser beam, emitting sparks, and
        disabling the laser beam.

        Methods:
            reposition(target: Coord) -> None:
                Repositions the laser beam to the target coordinate.
            emit(spark_count: int = 1) -> None:
                Emits a specified number of sparks from the laser beam.
            disable() -> None:
                Disables the laser beam by setting the visibility of the beam characters to False.

        """

        def __init__(
            self,
            terminal: tte.Terminal,
            config: LaserEtchConfig,
            active_chars: set[tte.EffectCharacter],
        ) -> None:
            """Initialize the laser beam.

            Args:
                terminal (Terminal): The effect terminal.
                config (LaserEtchConfig): The effect configuration.
                active_chars (set[EffectCharacter]): The set of active characters in the effect.

            """
            self.terminal = terminal
            self.config = config
            self.active_chars = active_chars
            self.position: tte.Coord = tte.Coord(0, 0)
            row = 0
            col = 0
            self.beam_chars: list[tte.EffectCharacter] = []
            laser_gradient = deque(tte.Gradient(*config.laser_gradient_stops, steps=6, loop=True))
            self.spark_gradient = tte.Gradient(
                *config.spark_gradient_stops,
                steps=(3, 8),
            )
            self.sparks = self._make_sparks()
            while row <= self.terminal.canvas.top:
                symbol = "*" if not self.beam_chars else "/"
                char = self.terminal.add_character(symbol, tte.Coord(col, row))
                char.layer = 2
                self.terminal.set_character_visibility(char, is_visible=True)
                row += 1
                col += 1
                self.beam_chars.append(char)
                laser_scn = char.animation.new_scene(scene_id="laser", is_looping=True)
                for color in laser_gradient:
                    laser_scn.add_frame(char.input_symbol, 3, colors=tte.ColorPair(fg=color))
                laser_gradient.rotate(-1)
                char.animation.activate_scene(laser_scn)

        def _make_sparks(self) -> deque[tte.EffectCharacter]:
            sparks: deque[tte.EffectCharacter] = deque()
            for _ in range(2000):
                new_char = self.terminal.add_character(random.choice((".", ",", "*")), self.position)

                spark_scn = new_char.animation.new_scene(scene_id="spark")
                for color in self.spark_gradient:
                    spark_scn.add_frame(
                        new_char.input_symbol,
                        self.config.spark_cooling_frames,
                        colors=tte.ColorPair(fg=color),
                    )

                new_char.event_handler.register_event(
                    tte.EventHandler.Event.SCENE_COMPLETE,
                    spark_scn,
                    tte.EventHandler.Action.CALLBACK,
                    tte.EventHandler.Callback(lambda c: self.terminal.set_character_visibility(c, is_visible=False)),
                )

                new_char.layer = 2
                sparks.append(new_char)
            return sparks

        def reposition(self, target: tte.Coord) -> None:
            """Reposition the laser beam to the target coordinate.

            Set the coordinate of the laser beam characters based on the target coordinate to
            create the appearance of a laser beam.

            Args:
                target (Coord): The target coordinate for the laser beam.

            """
            self.position = target
            row = target.row
            col = target.column
            for char in self.beam_chars:
                char.motion.set_coordinate(tte.Coord(col, row))
                row += 1
                col += 1
            self.emit_sparks()

        def emit_sparks(self, spark_count: int = 1) -> None:
            """Emit sparks from the laser beam.

            Sets up the spark character Path and activates the Path and Scene for each spark character.
            The spark characters are added to the effect active_characters set.

            Args:
                spark_count (int, optional): Number of spark characters to emit. Defaults to 1.

            """
            for _ in range(spark_count):
                next_spark = self.sparks[-1]
                self.sparks.rotate(1)
                next_spark.motion.set_coordinate(self.position)
                if next_spark.animation.active_scene:
                    next_spark.animation.active_scene.reset_scene()
                self.terminal.set_character_visibility(next_spark, is_visible=True)
                spark_path = next_spark.motion.new_path(ease=tte.easing.out_sine, speed=0.3)
                fall_target_coord = tte.Coord(
                    random.randint(self.position.column - 20, self.position.column + 20),
                    self.terminal.canvas.bottom,
                )
                spark_path.new_waypoint(
                    fall_target_coord,
                    bezier_control=tte.Coord(fall_target_coord.column, self.position.row + random.randint(-10, 20)),
                )
                next_spark.motion.activate_path(spark_path)
                next_spark.animation.activate_scene("spark")
                self.active_chars.add(next_spark)

        def disable(self) -> None:
            """Disable the laser beam by setting the visibility of the beam characters to False."""
            for char in self.beam_chars:
                self.terminal.set_character_visibility(char, is_visible=False)

    def __init__(self, effect: LaserEtch) -> None:
        """Initialize the effect iterator."""
        super().__init__(effect)
        self.character_final_color_map: dict[tte.EffectCharacter, tte.ColorPair] = {}
        self.pending_chars: list[tte.EffectCharacter] = []
        self.build()
        self.char_delay = 0
        self.laser = LaserEtchIterator.Laser(self.terminal, self.config, self.active_characters)
        self.active_characters.update(self.laser.beam_chars)
        self.color_shifted_chars: set[tte.EffectCharacter] = set()

    def build(self) -> None:
        """Build the effect."""
        final_fg_gradient = tte.Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_fg_gradient.build_coordinate_color_mapping(
            self.terminal.canvas.text_bottom,
            self.terminal.canvas.text_top,
            self.terminal.canvas.text_left,
            self.terminal.canvas.text_right,
            self.config.final_gradient_direction,
        )
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = tte.ColorPair(
                fg=final_gradient_mapping[character.input_coord],
            )
            cool_gradient = tte.Gradient(
                *self.config.cool_gradient_stops,
                final_gradient_mapping[character.input_coord],
                steps=8,
            )
            spawn_scn = character.animation.new_scene(scene_id="spawn")
            spawn_scn.add_frame("^", duration=3, colors=tte.ColorPair("#ffe680"))
            for color in cool_gradient:
                spawn_scn.add_frame(character.input_symbol, 3, colors=tte.ColorPair(fg=color))
            character.animation.activate_scene(spawn_scn)
        if self.config.etch_pattern in CharacterGroup._member_names_:
            for n, char_list in enumerate(
                self.terminal.get_characters_grouped(self.config.etch_pattern),
            ):
                if n % 2:
                    self.pending_chars.extend(char_list[::-1])
                else:
                    self.pending_chars.extend(char_list)
        elif self.config.etch_pattern == "algorithm":
            algo = RecursiveBacktracker(self.terminal, limit_to_text_boundary=True)
            while not algo.complete:
                algo.step()
            self.pending_chars = algo.char_link_order

    def __next__(self) -> str:
        """Return the next frame in the effect."""
        while self.pending_chars or self.active_characters:
            if not self.char_delay:
                for _ in range(self.config.etch_speed):
                    if not self.pending_chars:
                        break
                    next_char = self.pending_chars.pop(0)
                    while next_char.input_symbol == " ":
                        if self.pending_chars:
                            next_char = self.pending_chars.pop(0)
                        else:
                            break

                    self.terminal.set_character_visibility(next_char, is_visible=True)
                    self.active_characters.add(next_char)
                    self.laser.reposition(next_char.input_coord)

                self.char_delay = self.config.etch_delay
            else:
                self.char_delay -= 1
            if self.pending_chars:
                self.active_characters.update(self.laser.beam_chars)
            else:
                self.laser.disable()
            self.update()
            return self.frame
        raise StopIteration


class LaserEtch(BaseEffect[LaserEtchConfig]):
    """A laser etches characters onto the terminal."""

    @property
    def _config_cls(self) -> type:
        return LaserEtchConfig

    @property
    def _iterator_cls(self) -> type:
        return LaserEtchIterator
