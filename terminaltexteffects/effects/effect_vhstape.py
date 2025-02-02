"""Lines of characters glitch left and right and lose detail like an old VHS tape.

Classes:
    VHSTape: Lines of characters glitch left and right and lose detail like an old VHS tape.
    VHSTapeConfig: Configuration for the VHSTape effect.
    VHSTapeIterator: Effect iterator for the VHSTape effect. Does not normally need to be called directly.
"""

from __future__ import annotations

import random
import typing
from dataclasses import dataclass

from terminaltexteffects import Color, ColorPair, Coord, EffectCharacter, EventHandler, Gradient, Scene
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argvalidators
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    """Get the effect class and its configuration class."""
    return VHSTape, VHSTapeConfig


@argclass(
    name="vhstape",
    help="Lines of characters glitch left and right and lose detail like an old VHS tape.",
    description="vhstape | Lines of characters glitch left and right and lose detail like an old VHS tape.",
    epilog=(
        "Example: terminaltexteffects vhstape --final-gradient-stops ab48ff e7b2b2 fffebd "
        "--final-gradient-steps 12 --glitch-line-colors ffffff ff0000 00ff00 0000ff ffffff --glitch-wave-colors "
        "ffffff ff0000 00ff00 0000ff ffffff --noise-colors 1e1e1f 3c3b3d 6d6c70 a2a1a6 cbc9cf ffffff "
        "--glitch-line-chance 0.05 --noise-chance 0.004 --total-glitch-time 1000"
    ),
)
@dataclass
class VHSTapeConfig(ArgsDataClass):
    """Configuration for the VHSTape effect.

    Attributes:
        glitch_line_colors (tuple[Color, ...]): Tuple of colors for the characters when a single line is glitching.
            Colors are applied in order as an animation.
        glitch_wave_colors (tuple[Color, ...]): Tuple of colors for the characters in lines that are part of the
            glitch wave. Colors are applied in order as an animation.
        noise_colors (tuple[Color, ...]): Tuple of colors for the characters during the noise phase.
        glitch_line_chance (float): Chance that a line will glitch on any given frame.
        noise_chance (float): Chance that all characters will experience noise on any given frame. Valid values are 0
            <= n <= 1.
        total_glitch_time (int): Total time, in frames, that the glitching phase will last. Valid values are n > 0.
        final_gradient_stops (tuple[Color, ...]): Tuple of colors for the final color gradient. If only one color is
            provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Tuple of the number of gradient steps to use. More steps will
            create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient.

    """

    glitch_line_colors: tuple[Color, ...] = ArgField(
        cmd_name="--glitch-line-colors",
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(Color("ffffff"), Color("ff0000"), Color("00ff00"), Color("0000ff"), Color("ffffff")),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the characters when a single line is glitching. Colors "
        "are applied in order as an animation.",
    )  # type: ignore[assignment]
    (
        "tuple[Color, ...] : Tuple of colors for the characters when a single line is glitching. Colors are "
        "applied in order as an animation."
    )

    glitch_wave_colors: tuple[Color, ...] = ArgField(
        cmd_name="--glitch-wave-colors",
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(Color("ffffff"), Color("ff0000"), Color("00ff00"), Color("0000ff"), Color("ffffff")),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the characters in lines that are part of the glitch wave. "
        "Colors are applied in order as an animation.",
    )  # type: ignore[assignment]
    (
        "tuple[Color, ...] : Tuple of colors for the characters in lines that are part of the glitch wave. Colors "
        "are applied in order as an animation."
    )

    noise_colors: tuple[Color, ...] = ArgField(
        cmd_name="--noise-colors",
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(Color("1e1e1f"), Color("3c3b3d"), Color("6d6c70"), Color("a2a1a6"), Color("cbc9cf"), Color("ffffff")),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the characters during the noise phase.",
    )  # type: ignore[assignment]
    "tuple[Color, ...] : Tuple of colors for the characters during the noise phase."

    glitch_line_chance: float = ArgField(
        cmd_name="--glitch-line-chance",
        type_parser=argvalidators.NonNegativeRatio.type_parser,
        default=0.05,
        metavar=argvalidators.NonNegativeRatio.METAVAR,
        help="Chance that a line will glitch on any given frame.",
    )  # type: ignore[assignment]
    "float : Chance that a line will glitch on any given frame."

    noise_chance: float = ArgField(
        cmd_name="--noise-chance",
        type_parser=argvalidators.NonNegativeRatio.type_parser,
        default=0.004,
        metavar=argvalidators.NonNegativeRatio.METAVAR,
        help="Chance that all characters will experience noise on any given frame.",
    )  # type: ignore[assignment]
    "float : Chance that all characters will experience noise on any given frame."

    total_glitch_time: int = ArgField(
        cmd_name="--total-glitch-time",
        type_parser=argvalidators.PositiveInt.type_parser,
        default=1000,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Total time, frames, that the glitching phase will last.",
    )  # type: ignore[assignment]
    "int : Total time, frames, that the glitching phase will last."

    final_gradient_stops: tuple[Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(Color("ab48ff"), Color("e7b2b2"), Color("fffebd")),
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
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create "
        "a smoother and longer gradient animation.",
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
    "Gradient.Direction : Direction of the final gradient."

    @classmethod
    def get_effect_class(cls) -> type[VHSTape]:
        """Get the effect class associated with this configuration."""
        return VHSTape


class VHSTapeIterator(BaseEffectIterator[VHSTapeConfig]):
    """Effect iterator for the VHSTape effect."""

    class Line:
        """Line of characters for the VHSTape effect."""

        def __init__(
            self,
            characters: list[EffectCharacter],
            args: VHSTapeConfig,
            character_final_color_map: dict[EffectCharacter, Color],
        ) -> None:
            """Initialize the line of characters.

            Args:
                characters (list[EffectCharacter]): The characters in the line.
                args (VHSTapeConfig): Configuration for the effect.
                character_final_color_map (dict[EffectCharacter, Color]): Mapping of characters to their final colors.

            """
            self.characters = characters
            self.args = args
            self.character_final_color_map = character_final_color_map
            self.build_line_effects()

        def build_line_effects(self) -> None:
            """Build the effects for the line of characters."""
            glitch_line_colors = self.args.glitch_line_colors
            snow_chars = ["#", "*", ".", ":"]
            noise_colors = self.args.noise_colors
            offset = random.randint(4, 25)
            direction = random.choice((-1, 1))
            hold_time = random.randint(1, 50)
            for character in self.characters:
                # make glitch and restore waypoints
                glitch_path = character.motion.new_path(path_id="glitch", speed=2, hold_time=hold_time)
                glitch_path.new_waypoint(
                    Coord(character.input_coord.column + (offset * direction), character.input_coord.row),
                    waypoint_id="glitch",
                )
                restore_path = character.motion.new_path(path_id="restore", speed=2)
                restore_path.new_waypoint(character.input_coord, waypoint_id="restore")
                # make glitch wave waypoints
                glitch_wave_mid_path = character.motion.new_path(path_id="glitch_wave_mid", speed=2)
                glitch_wave_mid_path.new_waypoint(
                    Coord(character.input_coord.column + 8, character.input_coord.row),
                    waypoint_id="glitch_wave_mid",
                )
                glitch_wave_end_path = character.motion.new_path(path_id="glitch_wave_end", speed=2)
                glitch_wave_end_path.new_waypoint(
                    Coord(character.input_coord.column + 14, character.input_coord.row),
                    waypoint_id="glitch_wave_end",
                )

                # make glitch scenes
                base_scn = character.animation.new_scene(scene_id="base")
                base_scn.add_frame(
                    character.input_symbol,
                    duration=1,
                    colors=ColorPair(fg=self.character_final_color_map[character]),
                )
                glitch_scn_forward = character.animation.new_scene(
                    scene_id="rgb_glitch_fwd",
                    sync=Scene.SyncMetric.STEP,
                )
                for color in glitch_line_colors:
                    glitch_scn_forward.add_frame(character.input_symbol, duration=1, colors=ColorPair(fg=color))
                glitch_scn_backward = character.animation.new_scene(
                    scene_id="rgb_glitch_bwd",
                    sync=Scene.SyncMetric.STEP,
                )
                for color in glitch_line_colors[::-1]:
                    glitch_scn_backward.add_frame(character.input_symbol, duration=1, colors=ColorPair(fg=color))
                snow_scn = character.animation.new_scene(scene_id="snow")
                for _ in range(25):
                    snow_scn.add_frame(
                        random.choice(snow_chars),
                        duration=2,
                        colors=ColorPair(fg=random.choice(noise_colors)),
                    )
                snow_scn.add_frame(
                    character.input_symbol,
                    duration=1,
                    colors=ColorPair(fg=self.character_final_color_map[character]),
                )
                final_snow_scn = character.animation.new_scene(scene_id="final_snow")
                final_redraw_scn = character.animation.new_scene(scene_id="final_redraw")
                final_redraw_scn.add_frame("█", duration=10, colors=ColorPair(fg="ffffff"))
                final_redraw_scn.add_frame(
                    character.input_symbol,
                    duration=1,
                    colors=ColorPair(fg=self.character_final_color_map[character]),
                )

                for _ in range(50):
                    final_snow_scn.add_frame(
                        random.choice(snow_chars),
                        duration=2,
                        colors=ColorPair(fg=random.choice(noise_colors)),
                    )
                # register events
                character.event_handler.register_event(
                    EventHandler.Event.PATH_COMPLETE,
                    glitch_path,
                    EventHandler.Action.ACTIVATE_PATH,
                    restore_path,
                )
                character.event_handler.register_event(
                    EventHandler.Event.PATH_ACTIVATED,
                    glitch_path,
                    EventHandler.Action.ACTIVATE_SCENE,
                    glitch_scn_forward,
                )
                character.event_handler.register_event(
                    EventHandler.Event.PATH_ACTIVATED,
                    restore_path,
                    EventHandler.Action.ACTIVATE_SCENE,
                    glitch_scn_backward,
                )
                character.event_handler.register_event(
                    EventHandler.Event.PATH_ACTIVATED,
                    glitch_wave_mid_path,
                    EventHandler.Action.ACTIVATE_SCENE,
                    glitch_scn_forward,
                )
                character.event_handler.register_event(
                    EventHandler.Event.PATH_ACTIVATED,
                    glitch_wave_end_path,
                    EventHandler.Action.ACTIVATE_SCENE,
                    glitch_scn_forward,
                )
                character.event_handler.register_event(
                    EventHandler.Event.SCENE_COMPLETE,
                    glitch_scn_backward,
                    EventHandler.Action.ACTIVATE_SCENE,
                    base_scn,
                )

        def snow(self) -> None:
            """Activate the snow animation for the line."""
            for character in self.characters:
                character.animation.activate_scene(character.animation.query_scene("snow"))

        def set_hold_time(self, hold_time: int) -> None:
            """Set the hold time for the glitch and restore paths."""
            for character in self.characters:
                character.motion.paths["glitch"].hold_time = hold_time

        def glitch(self, *, final: bool = False) -> None:
            """Activate the glitch animation for the line.

            Args:
                final (bool, optional): If final, set hold times to 0. Defaults to False.

            """
            for character in self.characters:
                glitch_path = character.motion.query_path("glitch")
                restore_path = character.motion.query_path("restore")
                if final:
                    glitch_path.hold_time = 0
                    restore_path.hold_time = 0
                glitch_path.speed = 40 / random.randint(20, 40)
                restore_path.speed = 40 / random.randint(20, 40)
                character.motion.activate_path(glitch_path)

        def restore(self) -> None:
            """Activate the restore animation for the line."""
            for character in self.characters:
                restore_path = character.motion.query_path("restore")
                restore_path.speed = 40 / random.randint(20, 40)
                character.motion.activate_path(restore_path)

        def activate_path(self, path_id: str) -> None:
            """Activate the specified path for the line.

            Args:
                path_id (str): The ID of the path to activate.

            """
            for character in self.characters:
                character.motion.activate_path(character.motion.query_path(path_id))

        def line_movement_complete(self) -> bool:
            """Check if the movement of the line is complete.

            Returns:
                bool: True if the movement of the line is complete, False otherwise.

            """
            return all(character.motion.movement_is_complete() for character in self.characters)

    def __init__(self, effect: VHSTape) -> None:
        """Initialize the effect iterator.

        Args:
            effect (VHSTape): The effect to use for the iterator.

        """
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.lines: dict[int, VHSTapeIterator.Line] = {}
        self.active_glitch_wave_top: int | None = None
        self.active_glitch_wave_lines: list[VHSTapeIterator.Line] = []
        self.active_glitch_lines: list[VHSTapeIterator.Line] = []
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
        for row_index, characters in enumerate(
            self.terminal.get_characters_grouped(grouping=self.terminal.CharacterGroup.ROW_BOTTOM_TO_TOP),
        ):
            self.lines[row_index] = VHSTapeIterator.Line(characters, self.config, self.character_final_color_map)
        for character in self.terminal.get_characters():
            self.terminal.set_character_visibility(character, is_visible=True)
            character.animation.activate_scene(character.animation.query_scene("base"))
        self._glitching_steps_elapsed = 0
        self._phase = "glitching"
        self._to_redraw = list(self.lines.values())
        self._redrawing = False

    def glitch_wave(self) -> None:
        """Move the glitch wave."""
        if not self.active_glitch_wave_top:
            if self.terminal.canvas.text_height >= 3:
                # choose a wave top index in the top half of the canvas or at least 3 rows up
                self.active_glitch_wave_top = self.terminal.canvas.text_bottom + random.randint(
                    max((3, round(self.terminal.canvas.text_height * 0.5))),
                    self.terminal.canvas.text_height,
                )
            else:
                # not enough room for a wave
                return

        # if all lines have completed movement, proceed to move/restore wave
        if all(line.line_movement_complete() for line in self.active_glitch_wave_lines):
            if self.active_glitch_wave_lines:
                # only move 30% of the time
                wave_top_delta = (1 if random.random() < 0.3 else -1) if random.random() < 0.3 else 0
                self.active_glitch_wave_top += wave_top_delta
                # clamp wave top to canvas
                self.active_glitch_wave_top = max(2, min(self.active_glitch_wave_top, self.terminal.canvas.text_top))
            # get the lines for the wave
            new_wave_lines: list[VHSTapeIterator.Line] = []
            for line_index in range(self.active_glitch_wave_top - 2, self.active_glitch_wave_top + 1):
                adjusted_line_index = line_index - (self.terminal.canvas.text_bottom - 1)
                if adjusted_line_index in self.lines:
                    new_wave_lines.append(self.lines[adjusted_line_index])

            # restore any lines that are no longer part of the wave
            for line in self.active_glitch_wave_lines:
                if line not in new_wave_lines:
                    line.restore()
                    self.active_characters = self.active_characters.union(line.characters)
            self.active_glitch_wave_lines = new_wave_lines

            if self.active_glitch_wave_top < self.terminal.canvas.text_bottom + 2:
                # wave at bottom, restore lines
                for line in self.active_glitch_wave_lines:
                    line.restore()
                    self.active_characters = self.active_characters.union(line.characters)
                self.active_glitch_wave_top = None
                self.active_glitch_wave_lines = []

            else:
                for line, path_id in zip(
                    self.active_glitch_wave_lines,
                    ("glitch_wave_mid", "glitch_wave_end", "glitch_wave_mid"),
                ):
                    line.activate_path(path_id)
                    self.active_characters = self.active_characters.union(line.characters)

    def __next__(self) -> str:
        """Return the next frame in the animation."""
        if self._phase != "complete" or self.active_characters:
            if self._phase == "glitching":
                # Check if all active glitch wave lines have completed their movement, if so move the wave
                if not self.active_glitch_wave_lines or all(
                    line.line_movement_complete() for line in self.active_glitch_wave_lines
                ):
                    self.glitch_wave()
                # Remove completed glitch lines from active glitch lines
                self.active_glitch_lines = [
                    line for line in self.active_glitch_lines if not line.line_movement_complete()
                ]
                # Randomly add new glitch lines
                if random.random() < self.config.glitch_line_chance and len(self.active_glitch_lines) < 3:
                    glitch_line: VHSTapeIterator.Line = random.choice(list(self.lines.values()))
                    if glitch_line not in self.active_glitch_wave_lines and glitch_line not in self.active_glitch_lines:
                        glitch_line.set_hold_time(random.randint(30, 120))
                        self.active_glitch_lines.append(glitch_line)
                        glitch_line.glitch()
                        self.active_characters = self.active_characters.union(glitch_line.characters)
                # Randomly add noise to all lines
                if random.random() < self.config.noise_chance:
                    for line in self.lines.values():
                        line.snow()
                        if line not in self.active_glitch_wave_lines and line not in self.active_glitch_lines:
                            self.active_characters = self.active_characters.union(line.characters)
                self._glitching_steps_elapsed += 1
                # Check if glitching time has reached the total glitch time
                if self._glitching_steps_elapsed >= self.config.total_glitch_time:
                    # Restore glitch wave lines
                    for line in self.active_glitch_wave_lines:
                        line.restore()
                    # Restore glitch lines
                    for line in self.active_glitch_lines:
                        line.restore()
                    self._phase = "noise"

            elif self._phase == "noise":
                # Activate final snow animation for all characters
                if not self.active_characters:
                    for character in self.terminal.get_characters():
                        character.animation.activate_scene(character.animation.query_scene("final_snow"))
                        self.active_characters.add(character)
                    self._phase = "redraw"

            elif self._phase == "redraw":
                # Redraw lines one by one
                if self._redrawing or not self.active_characters:
                    self._redrawing = True
                    if self._to_redraw:
                        next_line = self._to_redraw.pop()
                        for character in next_line.characters:
                            character.animation.activate_scene(character.animation.query_scene("final_redraw"))
                            self.active_characters.add(character)
                    else:
                        self._phase = "complete"
            self.update()
            return self.frame
        raise StopIteration


class VHSTape(BaseEffect[VHSTapeConfig]):
    """Lines of characters glitch left and right and lose detail like an old VHS tape.

    Attributes:
        effect_config (VHSTapeConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.

    """

    @property
    def _config_cls(self) -> type[VHSTapeConfig]:
        return VHSTapeConfig

    @property
    def _iterator_cls(self) -> type[VHSTapeIterator]:
        return VHSTapeIterator
