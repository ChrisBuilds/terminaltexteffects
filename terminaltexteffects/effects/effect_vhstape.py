import random
import typing
from dataclasses import dataclass

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils import animation, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.terminal import Terminal


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return VHSTapeEffect, VHSTapeEffectArgs


@argclass(
    name="vhstape",
    formatter_class=arg_validators.CustomFormatter,
    help="Lines of characters glitch left and right and lose detail like an old VHS tape.",
    description="vhstape | Lines of characters glitch left and right and lose detail like an old VHS tape.",
    epilog="""Example: terminaltexteffects vhstape --final-gradient-stops ab48ff e7b2b2 fffebd --final-gradient-steps 12 --glitch-line-colors ffffff ff0000 00ff00 0000ff ffffff --glitch-wave-colors ffffff ff0000 00ff00 0000ff ffffff --noise-colors 1e1e1f 3c3b3d 6d6c70 a2a1a6 cbc9cf ffffff --glitch-line-chance 0.05 --noise-chance 0.004 --total-glitch-time 1000""",
)
@dataclass
class VHSTapeEffectArgs(ArgsDataClass):
    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("ab48ff", "e7b2b2", "fffebd"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=arg_validators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=arg_validators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.VERTICAL,
        metavar=arg_validators.GradientDirection.METAVAR,
        help="Direction of the gradient for the final color.",
    )  # type: ignore[assignment]
    glitch_line_colors: tuple[graphics.Color, ...] = ArgField(
        cmd_name="--glitch-line-colors",
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("ffffff", "ff0000", "00ff00", "0000ff", "ffffff"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the characters when a single line is glitching. Colors are applied in order as an animation.",
    )  # type: ignore[assignment]
    glitch_wave_colors: tuple[graphics.Color, ...] = ArgField(
        cmd_name="--glitch-wave-colors",
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("ffffff", "ff0000", "00ff00", "0000ff", "ffffff"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the characters in lines that are part of the glitch wave. Colors are applied in order as an animation.",
    )  # type: ignore[assignment]
    noise_colors: tuple[graphics.Color, ...] = ArgField(
        cmd_name="--noise-colors",
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("1e1e1f", "3c3b3d", "6d6c70", "a2a1a6", "cbc9cf", "ffffff"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the characters during the noise phase.",
    )  # type: ignore[assignment]
    glitch_line_chance: float = ArgField(
        cmd_name="--glitch-line-chance",
        type_parser=arg_validators.Ratio.type_parser,
        default=0.05,
        metavar=arg_validators.Ratio.METAVAR,
        help="Chance that a line will glitch on any given frame.",
    )  # type: ignore[assignment]
    noise_chance: float = ArgField(
        cmd_name="--noise-chance",
        type_parser=arg_validators.Ratio.type_parser,
        default=0.004,
        metavar=arg_validators.Ratio.METAVAR,
        help="Chance that all characters will experience noise on any given frame.",
    )  # type: ignore[assignment]
    total_glitch_time: int = ArgField(
        cmd_name="--total-glitch-time",
        type_parser=arg_validators.PositiveInt.type_parser,
        default=1000,
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Total time, animation steps, that the glitching phase will last.",
    )  # type: ignore[assignment]

    @classmethod
    def get_effect_class(cls):
        return VHSTapeEffect


class Line:
    """
    Represents a line of characters with various effects.

    Args:
        characters (list[EffectCharacter]): List of EffectCharacter objects representing the characters in the line.
        args (argparse.Namespace): Namespace object containing command-line arguments.

    Attributes:
        characters (list[EffectCharacter]): List of EffectCharacter objects representing the characters in the line.
        args (argparse.Namespace): Namespace object containing command-line arguments.

    Methods:
        build_line_effects(): Builds the line effects for each character.
        snow(): Activates the snow animation for each character.
        set_hold_time(hold_time: int): Sets the hold time for glitch waypoints for each character.
        glitch(final=False): Activates the glitch animation for each character.
        restore(): Activates the restore animation for each character.
        activate_waypoint(waypoint_id: str): Activates a specific waypoint for each character.
        line_movement_complete(): Checks if the movement of all characters in the line is complete.

    """

    def __init__(
        self,
        characters: list[EffectCharacter],
        args: VHSTapeEffectArgs,
        character_final_color_map: dict[EffectCharacter, graphics.Color],
    ) -> None:
        self.characters = characters
        self.args = args
        self.character_final_color_map = character_final_color_map
        self.build_line_effects()

    def build_line_effects(self) -> None:
        glitch_line_colors = self.args.glitch_line_colors
        snow_chars = ["#", "*", ".", ":"]
        noise_colors = self.args.noise_colors
        offset = random.randint(4, 25)
        direction = random.choice((-1, 1))
        hold_time = random.randint(1, 50)
        for character in self.characters:
            # make glitch and restore waypoints
            glitch_path = character.motion.new_path(id="glitch", speed=2, hold_time=hold_time)
            glitch_path.new_waypoint(
                Coord(character.input_coord.column + (offset * direction), character.input_coord.row),
                id="glitch",
            )
            restore_path = character.motion.new_path(id="restore", speed=2)
            restore_path.new_waypoint(character.input_coord, id="restore")
            # make glitch wave waypoints
            glitch_wave_mid_path = character.motion.new_path(id="glitch_wave_mid", speed=2)
            glitch_wave_mid_path.new_waypoint(
                Coord(character.input_coord.column + 8, character.input_coord.row), id="glitch_wave_mid"
            )
            glitch_wave_end_path = character.motion.new_path(id="glitch_wave_end", speed=2)
            glitch_wave_end_path.new_waypoint(
                Coord(character.input_coord.column + 14, character.input_coord.row), id="glitch_wave_end"
            )

            # make glitch scenes
            base_scn = character.animation.new_scene(id="base")
            base_scn.add_frame(character.input_symbol, duration=1, color=self.character_final_color_map[character])
            glitch_scn_forward = character.animation.new_scene(id="rgb_glitch_fwd", sync=animation.SyncMetric.STEP)
            for color in glitch_line_colors:
                glitch_scn_forward.add_frame(character.input_symbol, duration=1, color=color)
            glitch_scn_backward = character.animation.new_scene(id="rgb_glitch_bwd", sync=animation.SyncMetric.STEP)
            for color in glitch_line_colors[::-1]:
                glitch_scn_backward.add_frame(character.input_symbol, duration=1, color=color)
            snow_scn = character.animation.new_scene(id="snow")
            for _ in range(25):
                snow_scn.add_frame(random.choice(snow_chars), duration=2, color=random.choice(noise_colors))
            snow_scn.add_frame(character.input_symbol, duration=1, color=self.character_final_color_map[character])
            final_snow_scn = character.animation.new_scene(id="final_snow")
            final_redraw_scn = character.animation.new_scene(id="final_redraw")
            final_redraw_scn.add_frame("█", duration=10, color="ffffff")
            final_redraw_scn.add_frame(
                character.input_symbol, duration=1, color=self.character_final_color_map[character]
            )

            for _ in range(50):
                final_snow_scn.add_frame(random.choice(snow_chars), duration=2, color=random.choice(noise_colors))
            # register events
            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE, glitch_path, EventHandler.Action.ACTIVATE_PATH, restore_path
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
                EventHandler.Event.SCENE_COMPLETE, glitch_scn_backward, EventHandler.Action.ACTIVATE_SCENE, base_scn
            )

    def snow(self) -> None:
        """
        Activates the snow animation for each character in the effect.
        """
        for character in self.characters:
            character.animation.activate_scene(character.animation.query_scene("snow"))

    def set_hold_time(self, hold_time: int) -> None:
        """
        Set the hold time for each character's glitch motion.

        Args:
            hold_time (int): The hold time in animation steps.

        Returns:
            None
        """
        for character in self.characters:
            character.motion.paths["glitch"].hold_time = hold_time

    def glitch(self, final=False) -> None:
        """
        Apply glitch effect to the characters.

        Args:
            final (bool): If True, set hold_time to 0 for glitch and restore waypoints.

        Returns:
            None
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
        for character in self.characters:
            restore_path = character.motion.query_path("restore")
            restore_path.speed = 40 / random.randint(20, 40)
            character.motion.activate_path(restore_path)

    def activate_path(self, path_id: str) -> None:
        for character in self.characters:
            character.motion.activate_path(character.motion.query_path(path_id))

    def line_movement_complete(self):
        return all(character.motion.movement_is_complete() for character in self.characters)


class VHSTapeEffect:
    """
    Represents a VHS tape effect for terminal text.

    Attributes:
        terminal (Terminal): The terminal object.
        args (VHSTapeEffectArgs): The command-line arguments.
        pending_chars (list[EffectCharacter]): The list of pending effect characters.
        animating_chars (list[EffectCharacter]): The list of animating effect characters.
        lines (dict[int, Line]): The dictionary of lines indexed by row index.
        active_glitch_wave_top (int | None): The top row index of the active glitch wave, or None if no active wave.
        active_glitch_wave_lines (list[Line]): The list of lines in the active glitch wave.
        active_glitch_lines (list[Line]): The list of active glitch lines.
    """

    def __init__(self, terminal: Terminal, args: VHSTapeEffectArgs):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.lines: dict[int, Line] = {}
        self.active_glitch_wave_top: int | None = None
        self.active_glitch_wave_lines: list[Line] = []
        self.active_glitch_lines: list[Line] = []
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def prepare_data(self) -> None:
        final_gradient = graphics.Gradient(*self.args.final_gradient_stops, steps=self.args.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.args.final_gradient_direction
        )
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]
        for row_index, characters in enumerate(
            self.terminal.get_characters_grouped(grouping=self.terminal.CharacterGroup.ROW_BOTTOM_TO_TOP)
        ):
            self.lines[row_index] = Line(characters, self.args, self.character_final_color_map)
        for character in self.terminal.get_characters():
            self.terminal.set_character_visibility(character, True)
            character.animation.activate_scene(character.animation.query_scene("base"))

    def glitch_wave(self) -> None:
        if not self.active_glitch_wave_top:
            if self.terminal.output_area.top >= 3:
                # choose a wave top index in the top half of the output area or at least 3 rows up
                self.active_glitch_wave_top = random.randint(
                    max((3, round(self.terminal.output_area.top * 0.5))), self.terminal.output_area.top
                )
            else:
                # not enough room for a wave
                return

        # if all lines have completed movement, proceed to move/restore wave
        if all(line.line_movement_complete() for line in self.active_glitch_wave_lines):
            if self.active_glitch_wave_lines:
                # only move 30% of the time
                if random.random() < 0.3:
                    # if moving, only move up 10% of the time
                    if random.random() < 0.3:
                        wave_top_delta = 1
                    else:
                        wave_top_delta = -1
                else:
                    wave_top_delta = 0
                self.active_glitch_wave_top += wave_top_delta
                # clamp wave top to output area
                self.active_glitch_wave_top = max(2, min(self.active_glitch_wave_top, self.terminal.output_area.top))
            # get the lines for the wave
            new_wave_lines: list[Line] = []
            for line_index in range(self.active_glitch_wave_top - 2, self.active_glitch_wave_top + 1):
                if line_index in self.lines:
                    new_wave_lines.append(self.lines[line_index])

            # restore any lines that are no longer part of the wave
            for line in self.active_glitch_wave_lines:
                if line not in new_wave_lines:
                    line.restore()
                    self.active_chars.extend(line.characters)
            self.active_glitch_wave_lines = new_wave_lines

            if self.active_glitch_wave_top < 3:
                # wave at bottom, restore lines
                for line in self.active_glitch_wave_lines:
                    line.restore()
                    self.active_chars.extend(line.characters)
                self.active_glitch_wave_top = None
                self.active_glitch_wave_lines = []

            else:
                for line, path_id in zip(
                    self.active_glitch_wave_lines, ("glitch_wave_mid", "glitch_wave_end", "glitch_wave_mid")
                ):
                    line.activate_path(path_id)
                    self.active_chars.extend(line.characters)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()

        self.terminal.print()
        glitching_steps_elapsed = 0
        phase = "glitching"
        to_redraw = list(self.lines.values())
        redrawing = False
        while phase != "complete" or self.active_chars:
            if phase == "glitching":
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
                if random.random() < self.args.glitch_line_chance and len(self.active_glitch_lines) < 3:
                    glitch_line: Line = random.choice(list(self.lines.values()))
                    if glitch_line not in self.active_glitch_wave_lines and glitch_line not in self.active_glitch_lines:
                        glitch_line.set_hold_time(random.randint(30, 120))
                        self.active_glitch_lines.append(glitch_line)
                        glitch_line.glitch()
                        self.active_chars.extend(glitch_line.characters)
                # Randomly add noise to all lines
                if random.random() < self.args.noise_chance:
                    for line in self.lines.values():
                        line.snow()
                        if line not in self.active_glitch_wave_lines and line not in self.active_glitch_lines:
                            self.active_chars.extend(line.characters)
                glitching_steps_elapsed += 1
                # Check if glitching time has reached the total glitch time
                if glitching_steps_elapsed >= self.args.total_glitch_time:
                    # Restore glitch wave lines
                    for line in self.active_glitch_wave_lines:
                        line.restore()
                    # Restore glitch lines
                    for line in self.active_glitch_lines:
                        line.restore()
                    phase = "noise"

            elif phase == "noise":
                # Activate final snow animation for all characters
                if not self.active_chars:
                    for character in self.terminal.get_characters():
                        character.animation.activate_scene(character.animation.query_scene("final_snow"))
                        self.active_chars.append(character)
                    phase = "redraw"

            elif phase == "redraw":
                # Redraw lines one by one
                if redrawing or not self.active_chars:
                    redrawing = True
                    if to_redraw:
                        next_line = to_redraw.pop()
                        for character in next_line.characters:
                            character.animation.activate_scene(character.animation.query_scene("final_redraw"))
                            self.active_chars.append(character)
                    else:
                        phase = "complete"
            self.animate_chars()
            self.terminal.print()

            self.active_chars = [character for character in self.active_chars if character.is_active]

    def animate_chars(self) -> None:
        """Animates the characters by calling the tick method on all active characters."""
        for character in self.active_chars:
            character.tick()
