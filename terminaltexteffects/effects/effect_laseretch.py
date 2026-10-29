"""A laser etches characters onto the terminal.

Classes:
    LaserEtch: A laser etches characters onto the terminal.
    LaserEtchConfig: Configuration for the LaserEtch effect.
    LaserEtchIterator: Iterator for the LaserEtch effect.

"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Literal

import terminaltexteffects as tte
from terminaltexteffects.engine.base_config import (
    BaseConfig,
    FinalGradientDirectionArg,
    FinalGradientFramesArg,
    FinalGradientStepsArg,
    FinalGradientStopsArg,
)
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils, geometry3d
from terminaltexteffects.utils.geometry import rasterize_line
from terminaltexteffects.utils.spanningtree.algo.recursivebacktracker import RecursiveBacktracker


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Get the command, effect class, and configuration class for the effect.

    Returns:
        tuple[str, type[BaseEffect], type[BaseConfig]]: The command name, effect class, and configuration class.

    """
    return "laseretch", LaserEtch, LaserEtchConfig


def _etch_pattern_type_parser(
    value: str | argutils.CharacterOrder | argutils.CharacterGroup | argutils.CharacterSort,
) -> argutils.CharacterOrder | Literal["algorithm"]:
    """Normalize the algorithm sentinel or a canonical `CharacterOrder`."""
    if isinstance(value, str) and value == "algorithm":
        return "algorithm"
    return argutils.CharacterOrderArg.type_parser(value)


@dataclass
class LaserEtchConfig(BaseConfig):
    """LaserEtch effect configuration dataclass.

    Attributes:
        reverse_etch_pattern (bool): Reverse the complete traversal while preserving group membership.
        etch_pattern (`CharacterOrder` | `Literal['algorithm']`): Character order used
            to etch the text. `algorithm` follows a recursive backtracker. Spatial patterns reverse
            alternate groups for serpentine traversal; individual patterns use the exact sorted order,
            including clockwise and counterclockwise single, double, and quad spirals.
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

    parser_spec: argutils.ParserSpec = argutils.ParserSpec(
        name="laseretch",
        help="A laser etches characters onto the terminal.",
        description="A laser etches characters onto the terminal.",
        epilog=(
            "Example: terminaltexteffects laseretch --etch-pattern algorithm --etch-speed 1 --etch-delay 1 "
            "--cool-gradient-stops ffe680 ff7b00 --laser-gradient-stops ffffff 376cff "
            "--spark-gradient-stops ffffff ffe680 ff7b00 1a0900 --spark-cooling-frames 7 --final-gradient-stops "
            "8A008A 00D1FF ffffff --final-gradient-steps 8 --final-gradient-frames 4 "
            "--final-gradient-direction vertical"
        ),
    )

    etch_pattern: argutils.CharacterOrder | argutils.CharacterGroup | argutils.CharacterSort | Literal["algorithm"] = (
        argutils.ArgSpec(
            name="--etch-pattern",
            default="algorithm",
            type=_etch_pattern_type_parser,
            metavar="algorithm " + " ".join(argutils.CharacterOrderArg.METAVAR),
            help="Pattern used to etch the text: algorithm, serpentine character groups, or exact character sorts.",
        )
    )  # pyright: ignore[reportAssignmentType]
    "CharacterOrder | Literal['algorithm']: Pattern used to etch the text."

    reverse_etch_pattern: bool = argutils.ArgSpec(
        name="--reverse-etch-pattern",
        default=False,
        action="store_true",
        help="Reverse the complete etch pattern traversal.",
    )  # pyright: ignore[reportAssignmentType]
    "bool : Reverse the complete traversal, preserving group membership."

    etch_speed: int = argutils.ArgSpec(
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

    etch_delay: int = argutils.ArgSpec(
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

    cool_gradient_stops: tuple[tte.Color, ...] = argutils.ArgSpec(
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

    laser_gradient_stops: tuple[tte.Color, ...] = argutils.ArgSpec(
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

    spark_gradient_stops: tuple[tte.Color, ...] = argutils.ArgSpec(
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

    spark_cooling_frames: int = argutils.ArgSpec(
        name="--spark-cooling-frames",
        type=argutils.PositiveInt.type_parser,
        default=7,
        metavar=argutils.PositiveInt.METAVAR,
        help="Number of frames to display each spark cooling gradient step. Increase to slow down the rate of cooling.",
    )  # pyright: ignore[reportAssignmentType]
    "int: Number of frames to display each spark cooling gradient step. Increase to slow down the rate of cooling."

    final_gradient_stops: tuple[tte.Color, ...] = FinalGradientStopsArg(
        default=(tte.Color("#8A008A"), tte.Color("#00D1FF"), tte.Color("#ffffff")),
    )  # pyright: ignore[reportAssignmentType]
    "tuple[Color, ...]: Space separated, unquoted, list of colors for the character gradient "
    "(applied across the canvas). If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] | int = FinalGradientStepsArg(
        default=8,
    )  # pyright: ignore[reportAssignmentType]
    "tuple[int, ...] | int: Space separated, unquoted, list of the number of gradient steps to use. More steps will "
    "create a smoother and longer gradient animation."

    final_gradient_frames: int = FinalGradientFramesArg(
        default=4,
    )  # pyright: ignore[reportAssignmentType]
    "int: Number of frames to display each gradient step. Increase to slow down the gradient animation."

    final_gradient_direction: tte.Gradient.Direction = FinalGradientDirectionArg(
        default=tte.Gradient.Direction.VERTICAL,
    )  # pyright: ignore[reportAssignmentType]
    "Gradient.Direction : Direction of the final gradient."


class LaserEtchIterator(BaseEffectIterator[LaserEtchConfig]):
    """Iterator for the LaserEtch effect."""

    class Laser:
        """A class to represent a laser beam effect in a terminal.

        The laser is mounted at a fixed point in the 3D world, above the top of the canvas and halfway between the
        camera and the text plane. Its beam is a straight segment from that point down to the character being
        etched on the text plane, so the beam swings around the mount as the etch moves across the text.

        Methods:
            reposition(target: Coord) -> None:
                Repositions the laser beam to the target coordinate.
            shimmer() -> None:
                Advances the beam's color cycle by one frame.
            emit(spark_count: int = 1) -> None:
                Emits a specified number of sparks from the laser beam.
            disable() -> None:
                Disables the laser beam by setting the visibility of the beam characters to False.

        """

        MOUNT_ROWS_ABOVE_CANVAS = 4
        "int: How many rows above the canvas top the mount appears to sit, as seen by the camera."

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
            self.world = terminal.world
            canvas = terminal.canvas
            camera = self.world.camera
            # Halfway between the eye and the text plane, on the ray through a cell above the canvas.
            self.mount = camera.cell_to_world(
                tte.Coord(canvas.center_column, canvas.top + self.MOUNT_ROWS_ABOVE_CANVAS),
                z=camera.position.z / 2,
            )
            self.laser_gradient = tuple(tte.Gradient(*config.laser_gradient_stops, steps=6, loop=True))
            self.spark_gradient = tte.Gradient(
                *config.spark_gradient_stops,
                steps=(3, 8),
            )
            self.sparks_pool = self._make_sparks_pool()
            # A beam is at most one cell per step along its longer axis on screen.
            beam_length = max(canvas.width, canvas.height + self.MOUNT_ROWS_ABOVE_CANVAS) + 1
            self.beam_chars: list[tte.EffectCharacter] = []
            for _ in range(beam_length):
                char = self.terminal.add_character(" ", canvas.center)
                char.layer = 2
                char.attach(self.world.root, at=self.mount)
                self.beam_chars.append(char)
            self.lit_chars: list[tte.EffectCharacter] = []
            self.beam_symbol = "|"
            self.frame = 0

        def _make_sparks_pool(self) -> tte.ParticlePool:
            def initialize_sparks(spark_char: tte.EffectCharacter) -> None:
                spark_char.layer = 2
                spark_scn = spark_char.animation.new_scene(scene_id="spark")
                for color in self.spark_gradient:
                    spark_scn.add_frame(
                        spark_char.input_symbol,
                        self.config.spark_cooling_frames,
                        colors=tte.ColorPair(fg=color),
                    )

            sparks_pool = tte.ParticlePool(
                self.terminal,
                self.active_chars,
                symbols=(".", ",", "*"),
                initial_count=2000,
                initializer=initialize_sparks,
            )
            for spark in sparks_pool.particles:
                sparks_pool.reclaim_on_event(spark, spark.animation.query_scene("spark"))
            return sparks_pool

        def reposition(self, target: tte.Coord) -> None:
            """Reposition the laser beam to the target coordinate.

            Lay the beam characters along the segment from the mount to the target on the text plane. Each one is
            placed in the world on the viewing ray of one cell of the segment's projection, at the depth the
            segment has there, so the beam reads as an unbroken line in front of the text.

            Args:
                target (Coord): The target coordinate for the laser beam.

            """
            self.position = target
            camera = self.world.camera
            canvas = self.terminal.canvas
            tip = camera.project(self.world.text_plane.to_world((target.column, target.row, 0)))
            mount = camera.project(self.mount)
            if tip is None or mount is None:
                return
            self.beam_symbol = geometry3d.line_symbol(
                mount.column - tip.column,
                mount.row - tip.row,
                camera.row_scale,
            )
            cells = rasterize_line(tip.coord, mount.coord)
            steps = max(len(cells) - 1, 1)
            lit_chars: list[tte.EffectCharacter] = []
            for step, cell in enumerate(cells):
                if not canvas.coord_is_in_canvas(cell):
                    continue
                t = step / steps
                # Under perspective, reciprocal depth is what changes linearly along the line on screen.
                depth = (
                    tip.depth + (mount.depth - tip.depth) * t
                    if camera.orthographic
                    else 1 / ((1 - t) / tip.depth + t / mount.depth)
                )
                ray_origin, ray_direction = camera.ray(cell)
                char = self.beam_chars[len(lit_chars)]
                char.motion.position = ray_origin + ray_direction * depth
                lit_chars.append(char)
            for char in self.lit_chars[len(lit_chars) :]:
                self.terminal.set_character_visibility(char, is_visible=False)
            for char in lit_chars[len(self.lit_chars) :]:
                self.terminal.set_character_visibility(char, is_visible=True)
            self.lit_chars = lit_chars
            self._paint_beam()
            self.emit_sparks()

        def shimmer(self) -> None:
            """Advance the beam's color cycle by one frame, so colors flow along the beam."""
            self.frame += 1
            self._paint_beam()

        def _paint_beam(self) -> None:
            """Draw the lit beam characters, with the tip at the target and the beam symbol following its slope."""
            gradient = self.laser_gradient
            offset = self.frame // 3
            for index, char in enumerate(self.lit_chars):
                char.animation.set_appearance_if_changed(
                    "*" if index == 0 else self.beam_symbol,
                    tte.ColorPair(fg=gradient[(index + offset) % len(gradient)]),
                )

        def emit_sparks(self, spark_count: int = 1) -> None:
            """Emit sparks from the laser beam.

            Sets up the spark character Path and activates the Path and Scene for each spark character.

            Args:
                spark_count (int, optional): Number of spark characters to emit. Defaults to 1.

            """

            def setup_spark_path(spark_char: tte.EffectCharacter) -> None:
                spark_char.motion.set_coordinate(self.position)
                spark_path = spark_char.motion.new_path(ease=tte.easing.out_sine, speed=0.3)
                fall_target_coord = tte.Coord(
                    random.randint(self.position.column - 20, self.position.column + 20),
                    self.terminal.canvas.bottom,
                )
                spark_path.new_waypoint(
                    fall_target_coord,
                    bezier_control=tte.Coord(fall_target_coord.column, self.position.row + random.randint(-10, 20)),
                )
                spark_char.motion.activate_path(spark_path)
                spark_char.animation.activate_scene("spark")

            for _ in range(spark_count):
                self.sparks_pool.emit(self.position, on_emit=setup_spark_path)

        def disable(self) -> None:
            """Disable the laser beam by setting the visibility of the beam characters to False."""
            for char in self.lit_chars:
                self.terminal.set_character_visibility(char, is_visible=False)
            self.lit_chars = []

    def __init__(self, effect: LaserEtch) -> None:
        """Initialize the effect iterator."""
        super().__init__(effect)
        self.character_final_color_map: dict[tte.EffectCharacter, tte.ColorPair] = {}
        self.pending_chars: list[tte.EffectCharacter] = []
        self.build()
        self.char_delay = 0
        self.laser = LaserEtchIterator.Laser(self.terminal, self.config, self.active_characters)
        self.color_shifted_chars: set[tte.EffectCharacter] = set()

    @staticmethod
    def _has_input_colors(character: tte.EffectCharacter) -> bool:
        return any((character.animation.input_fg_color, character.animation.input_bg_color))

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
            final_fg_color: tte.Color | None
            final_bg_color: tte.Color | None
            if self.terminal.config.existing_color_handling == "dynamic":
                self.character_final_color_map[character] = tte.ColorPair(
                    fg=character.animation.input_fg_color,
                    bg=character.animation.input_bg_color,
                )
                final_fg_color = self.character_final_color_map[character].fg
                final_bg_color = self.character_final_color_map[character].bg
                cool_gradient = tte.Gradient(
                    *self.config.cool_gradient_stops,
                    steps=8,
                )
            else:
                self.character_final_color_map[character] = tte.ColorPair(
                    fg=final_gradient_mapping[character.input_coord],
                )
                final_fg_color = self.character_final_color_map[character].fg
                final_bg_color = self.character_final_color_map[character].bg
                cool_gradient = tte.Gradient(
                    *self.config.cool_gradient_stops,
                    final_gradient_mapping[character.input_coord],
                    steps=8,
                )
            spawn_scn = character.animation.new_scene(scene_id="spawn")
            spawn_scn.add_frame("^", duration=3, colors=tte.ColorPair("#ffe680"))
            for color in cool_gradient:
                spawn_scn.add_frame(character.input_symbol, 3, colors=tte.ColorPair(fg=color))
            if self.terminal.config.existing_color_handling == "dynamic":
                if final_fg_color or final_bg_color:
                    fg_gradient = (
                        tte.Gradient(cool_gradient.spectrum[-1], final_fg_color, steps=8) if final_fg_color else None
                    )
                    bg_gradient = (
                        tte.Gradient(cool_gradient.spectrum[-1], final_bg_color, steps=8) if final_bg_color else None
                    )
                    spawn_scn.apply_gradient_to_symbols(
                        character.input_symbol,
                        3,
                        fg_gradient=fg_gradient,
                        bg_gradient=bg_gradient,
                    )
                else:
                    white_cooldown = tte.Gradient(cool_gradient.spectrum[-1], tte.Color("#ffffff"), steps=8)
                    spawn_scn.apply_gradient_to_symbols(
                        character.input_symbol,
                        3,
                        fg_gradient=white_cooldown,
                    )
                    spawn_scn.add_frame(character.input_symbol, 3, colors=tte.ColorPair())
            character.animation.activate_scene(spawn_scn)
        if self.config.etch_pattern == "algorithm":
            algo = RecursiveBacktracker(self.terminal, limit_to_text_boundary=True)
            while not algo.complete:
                algo.step()
            self.pending_chars = algo.char_link_order
            if self.config.reverse_etch_pattern:
                self.pending_chars.reverse()
        else:
            self.pending_chars = self.terminal.get_characters(
                order=self.config.etch_pattern,
                serpentine=True,
                reverse=self.config.reverse_etch_pattern,
            )

    def __next__(self) -> str:
        """Return the next frame in the effect."""
        while self.pending_chars or self.active_characters:
            if not self.char_delay:
                for _ in range(self.config.etch_speed):
                    if not self.pending_chars:
                        break
                    next_char = self.pending_chars.pop(0)
                    while next_char.input_symbol == " " and not self._has_input_colors(next_char):
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
                self.laser.shimmer()
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
