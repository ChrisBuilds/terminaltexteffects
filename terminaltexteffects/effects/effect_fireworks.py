import random
import typing
from collections.abc import Iterator
from dataclasses import dataclass

from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils import arg_validators, easing, geometry, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.terminal import Terminal, TerminalConfig


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return FireworksEffect, EffectConfig


@argclass(
    name="fireworks",
    help="Characters launch and explode like fireworks and fall into place.",
    description="fireworks | Characters explode like fireworks and fall into place.",
    epilog="""Example: terminaltexteffects fireworks --firework-colors 88F7E2 44D492 F5EB67 FFA15C FA233E --firework-symbol o --firework-volume 0.02 --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --launch-delay 60 --explode-distance 0.1 --explode-anywhere""",
)
@dataclass
class EffectConfig(ArgsDataClass):
    """Configuration for the Fireworks effect.

    Attributes:
        explode_anywhere (bool): If set, fireworks explode anywhere in the output area. Otherwise, fireworks explode above highest settled row of text.
        firework_colors (tuple[graphics.Color, ...]): Tuple of colors from which firework colors will be randomly selected.
        firework_symbol (str): Symbol to use for the firework shell.
        firework_volume (float): Percent of total characters in each firework shell.
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the gradient for the final color.
        launch_delay (int): Number of animation steps to wait between launching each firework shell. +/- 0-50 percent randomness is applied to this value.
        explode_distance (float): Maximum distance from the firework shell origin to the explode waypoint as a percentage of the total output area width."""

    explode_anywhere: bool = ArgField(
        cmd_name="--explode-anywhere",
        action="store_true",
        default=False,
        help="If set, fireworks explode anywhere in the output area. Otherwise, fireworks explode above highest settled row of text.",
    )  # type: ignore[assignment]
    "bool : If set, fireworks explode anywhere in the output area. Otherwise, fireworks explode above highest settled row of text."

    firework_colors: tuple[graphics.Color, ...] = ArgField(
        cmd_name="--firework-colors",
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("88F7E2", "44D492", "F5EB67", "FFA15C", "FA233E"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated list of colors from which firework colors will be randomly selected.",
    )  # type: ignore[assignment]
    "tuple[graphics.Color, ...] : Tuple of colors from which firework colors will be randomly selected."

    firework_symbol: str = ArgField(
        cmd_name="--firework-symbol",
        type_parser=arg_validators.Symbol.type_parser,
        default="o",
        metavar=arg_validators.Symbol.METAVAR,
        help="Symbol to use for the firework shell.",
    )  # type: ignore[assignment]
    "str : Symbol to use for the firework shell."

    firework_volume: float = ArgField(
        cmd_name="--firework-volume",
        type_parser=arg_validators.Ratio.type_parser,
        default=0.02,
        metavar=arg_validators.Ratio.METAVAR,
        help="Percent of total characters in each firework shell.",
    )  # type: ignore[assignment]
    "float : Percent of total characters in each firework shell."

    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name="--final-gradient-stops",
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("8A008A", "00D1FF", "FFFFFF"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[graphics.Color, ...] : Tuple of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=arg_validators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] : Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=arg_validators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.HORIZONTAL,
        metavar=arg_validators.GradientDirection.METAVAR,
        help="Direction of the gradient for the final color.",
    )  # type: ignore[assignment]
    "graphics.Gradient.Direction : Direction of the gradient for the final color."

    launch_delay: int = ArgField(
        cmd_name="--launch-delay",
        type_parser=arg_validators.NonNegativeInt.type_parser,
        default=60,
        metavar=arg_validators.NonNegativeInt.METAVAR,
        help="Number of animation steps to wait between launching each firework shell. +/- 0-50 percent randomness is applied to this value.",
    )  # type: ignore[assignment]
    "int : Number of animation steps to wait between launching each firework shell. +/- 0-50 percent randomness is applied to this value."

    explode_distance: float = ArgField(
        cmd_name="--explode-distance",
        default=0.1,
        type_parser=arg_validators.Ratio.type_parser,
        metavar=arg_validators.Ratio.METAVAR,
        help="Maximum distance from the firework shell origin to the explode waypoint as a percentage of the total output area width.",
    )  # type: ignore[assignment]
    "float : Maximum distance from the firework shell origin to the explode waypoint as a percentage of the total output area width."

    @classmethod
    def get_effect_class(cls):
        return FireworksEffect


class FireworksEffect:
    """Effect that launches characters up the screen where they explode like fireworks and fall into place."""

    def __init__(
        self,
        input_data: str,
        effect_config: EffectConfig = EffectConfig(),
        terminal_config: TerminalConfig = TerminalConfig(),
    ):
        """Initializes the effect.

        Args:
            input_data (str): The input data to apply the effect to.
            effect_config (EffectConfig): The configuration for the effect.
            terminal_config (TerminalConfig): The configuration for the terminal.
        """
        self.terminal = Terminal(input_data, terminal_config)
        self.config = effect_config
        self._built = False
        self._pending_chars: list[EffectCharacter] = []
        self._active_chars: list[EffectCharacter] = []
        self._shells: list[list[EffectCharacter]] = []
        self.firework_volume = max(1, round(self.config.firework_volume * len(self.terminal._input_characters)))
        self.explode_distance = max(1, round(self.terminal.output_area.right * self.config.explode_distance))
        self._character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def prepare_waypoints(self) -> None:
        firework_shell: list[EffectCharacter] = []
        for character in self.terminal.get_characters():
            if len(firework_shell) == self.firework_volume or not firework_shell:
                self._shells.append(firework_shell)
                firework_shell = []
                origin_x = random.randrange(0, self.terminal.output_area.right)
                if not self.config.explode_anywhere:
                    min_row = character.input_coord.row
                else:
                    min_row = self.terminal.output_area.bottom
                origin_y = random.randrange(min_row, self.terminal.output_area.top + 1)
                origin_coord = Coord(origin_x, origin_y)
                explode_waypoint_coords = geometry.find_coords_in_circle(origin_coord, self.explode_distance)
            character.motion.set_coordinate(Coord(origin_x, self.terminal.output_area.bottom))
            apex_path = character.motion.new_path(id="apex_pth", speed=0.2, ease=easing.out_expo)
            apex_wpt = apex_path.new_waypoint(origin_coord)
            explode_path = character.motion.new_path(speed=0.15, ease=easing.out_circ)
            explode_wpt = explode_path.new_waypoint(random.choice(explode_waypoint_coords))

            bloom_control_point = geometry.find_coord_at_distance(
                apex_wpt.coord, explode_wpt.coord, self.explode_distance // 2
            )
            bloom_wpt = explode_path.new_waypoint(
                Coord(bloom_control_point.column, max(1, bloom_control_point.row - 7)),
                bezier_control=bloom_control_point,
            )
            input_path = character.motion.new_path(id="input_pth", speed=0.3, ease=easing.in_out_quart)
            input_control_point = Coord(bloom_wpt.coord.column, 1)
            input_path.new_waypoint(character.input_coord, bezier_control=input_control_point)
            character.event_handler.register_event(
                EventHandler.Event.PATH_ACTIVATED, apex_path, EventHandler.Action.SET_LAYER, 2
            )
            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE, explode_path, EventHandler.Action.SET_LAYER, 0
            )
            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE,
                apex_path,
                EventHandler.Action.ACTIVATE_PATH,
                explode_path,
            )
            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE, explode_path, EventHandler.Action.ACTIVATE_PATH, input_path
            )

            character.motion.activate_path(apex_path)

            firework_shell.append(character)
        if firework_shell:
            self._shells.append(firework_shell)

    def prepare_scenes(self) -> None:
        final_gradient = graphics.Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.config.final_gradient_direction
        )
        for character in self.terminal.get_characters():
            self._character_final_color_map[character] = final_gradient_mapping[character.input_coord]
        for firework_shell in self._shells:
            shell_color = random.choice(self.config.firework_colors)
            for character in firework_shell:
                # launch scene
                launch_scn = character.animation.new_scene()
                launch_scn.add_frame(self.config.firework_symbol, 2, color=shell_color)
                launch_scn.add_frame(self.config.firework_symbol, 1, color="FFFFFF")
                launch_scn.is_looping = True
                # bloom scene
                bloom_scn = character.animation.new_scene()
                bloom_scn.add_frame(character.input_symbol, 1, color=shell_color)
                # fall scene
                fall_scn = character.animation.new_scene()
                fall_gradient = graphics.Gradient(shell_color, self._character_final_color_map[character], steps=15)
                fall_scn.apply_gradient_to_symbols(fall_gradient, character.input_symbol, 15)
                character.animation.activate_scene(launch_scn)
                character.event_handler.register_event(
                    EventHandler.Event.PATH_COMPLETE,
                    character.motion.query_path("apex_pth"),
                    EventHandler.Action.ACTIVATE_SCENE,
                    bloom_scn,
                )
                character.event_handler.register_event(
                    EventHandler.Event.PATH_ACTIVATED,
                    character.motion.query_path("input_pth"),
                    EventHandler.Action.ACTIVATE_SCENE,
                    fall_scn,
                )

    def build(self) -> None:
        """Prepares the data for the effect by building the firework shells and scenes."""
        self._pending_chars.clear()
        self._active_chars.clear()
        self._character_final_color_map.clear()
        self._shells.clear()
        self.prepare_waypoints()
        self.prepare_scenes()
        self._built = True

    @property
    def built(self) -> bool:
        """Returns True if the effect has been built."""
        return self._built

    def __iter__(self) -> Iterator[str]:
        """Runs the effect."""
        if not self._built:
            self.build()
        launch_delay = 0
        while self._shells or self._active_chars:
            if self._shells and launch_delay == 0:
                next_group = self._shells.pop()
                for character in next_group:
                    self.terminal.set_character_visibility(character, True)
                    self._active_chars.append(character)
                launch_delay = int(self.config.launch_delay * random.uniform(0.5, 1.5))
            yield self.terminal.get_formatted_output_string()
            self._animate_chars()
            launch_delay -= 1

            self._active_chars = [character for character in self._active_chars if character.is_active]
        yield self.terminal.get_formatted_output_string()
        self._built = False

    def _animate_chars(self) -> None:
        """Animates the characters by calling the tick method."""
        for character in self._active_chars:
            character.tick()
