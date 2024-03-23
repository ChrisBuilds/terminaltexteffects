import random
import typing
from dataclasses import dataclass

from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils import arg_validators, easing, geometry, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.terminal import Terminal


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return FireworksEffect, FireworksEffectArgs


@argclass(
    name="fireworks",
    formatter_class=arg_validators.CustomFormatter,
    help="Characters launch and explode like fireworks and fall into place.",
    description="fireworks | Characters explode like fireworks and fall into place.",
    epilog="""Example: terminaltexteffects fireworks --firework-colors 88F7E2 44D492 F5EB67 FFA15C FA233E --firework-symbol o --firework-volume 0.02 --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --launch-delay 60 --explode-distance 0.1 --explode-anywhere""",
)
@dataclass
class FireworksEffectArgs(ArgsDataClass):
    explode_anywhere: bool = ArgField(
        cmd_name="--explode-anywhere",
        action="store_true",
        default=False,
        help="If set, fireworks explode anywhere in the output area. Otherwise, fireworks explode above highest settled row of text.",
    )  # type: ignore[assignment]
    firework_colors: tuple[graphics.Color, ...] = ArgField(
        cmd_name="--firework-colors",
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("88F7E2", "44D492", "F5EB67", "FFA15C", "FA233E"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated list of colors from which firework colors will be randomly selected.",
    )  # type: ignore[assignment]
    firework_symbol: str = ArgField(
        cmd_name="--firework-symbol",
        type_parser=arg_validators.Symbol.type_parser,
        default="o",
        metavar=arg_validators.Symbol.METAVAR,
        help="Symbol to use for the firework shell.",
    )  # type: ignore[assignment]
    firework_volume: float = ArgField(
        cmd_name="--firework-volume",
        type_parser=arg_validators.Ratio.type_parser,
        default=0.02,
        metavar=arg_validators.Ratio.METAVAR,
        help="Percent of total characters in each firework shell.",
    )  # type: ignore[assignment]
    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name="--final-gradient-stops",
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("8A008A", "00D1FF", "FFFFFF"),
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
        default=graphics.Gradient.Direction.HORIZONTAL,
        metavar=arg_validators.GradientDirection.METAVAR,
        help="Direction of the gradient for the final color.",
    )  # type: ignore[assignment]
    launch_delay: int = ArgField(
        cmd_name="--launch-delay",
        type_parser=arg_validators.NonNegativeInt.type_parser,
        default=60,
        metavar=arg_validators.NonNegativeInt.METAVAR,
        help="Number of animation steps to wait between launching each firework shell. +/- 0-50 percent randomness is applied to this value.",
    )  # type: ignore[assignment]
    explode_distance: float = ArgField(
        cmd_name="--explode-distance",
        default=0.1,
        type_parser=arg_validators.Ratio.type_parser,
        metavar=arg_validators.Ratio.METAVAR,
        help="Maximum distance from the firework shell origin to the explode waypoint as a percentage of the total output area width.",
    )  # type: ignore[assignment]

    @classmethod
    def get_effect_class(cls):
        return FireworksEffect


class FireworksEffect:
    """Effect that launches characters up the screen where they explode like fireworks and fall into place."""

    def __init__(self, terminal: Terminal, args: FireworksEffectArgs):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.shells: list[list[EffectCharacter]] = []
        self.firework_volume = max(1, round(self.args.firework_volume * len(self.terminal._input_characters)))
        self.explode_distance = max(1, round(self.terminal.output_area.right * self.args.explode_distance))
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def prepare_waypoints(self) -> None:
        firework_shell: list[EffectCharacter] = []
        for character in self.terminal.get_characters():
            if len(firework_shell) == self.firework_volume or not firework_shell:
                self.shells.append(firework_shell)
                firework_shell = []
                origin_x = random.randrange(0, self.terminal.output_area.right)
                if not self.args.explode_anywhere:
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
            self.shells.append(firework_shell)

    def prepare_scenes(self) -> None:
        final_gradient = graphics.Gradient(*self.args.final_gradient_stops, steps=self.args.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.args.final_gradient_direction
        )
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]
        for firework_shell in self.shells:
            shell_color = random.choice(self.args.firework_colors)
            for character in firework_shell:
                # launch scene
                launch_scn = character.animation.new_scene()
                launch_scn.add_frame(self.args.firework_symbol, 2, color=shell_color)
                launch_scn.add_frame(self.args.firework_symbol, 1, color="FFFFFF")
                launch_scn.is_looping = True
                # bloom scene
                bloom_scn = character.animation.new_scene()
                bloom_scn.add_frame(character.input_symbol, 1, color=shell_color)
                # fall scene
                fall_scn = character.animation.new_scene()
                fall_gradient = graphics.Gradient(shell_color, self.character_final_color_map[character], steps=15)
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

    def prepare_data(self) -> None:
        """Prepares the data for the effect by building the firework shells and scenes."""
        self.prepare_waypoints()
        self.prepare_scenes()

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        launch_delay = 0
        while self.shells or self.active_chars:
            if self.shells and launch_delay == 0:
                next_group = self.shells.pop()
                for character in next_group:
                    self.terminal.set_character_visibility(character, True)
                    self.active_chars.append(character)
                launch_delay = int(self.args.launch_delay * random.uniform(0.5, 1.5))
            self.terminal.print()
            self.animate_chars()
            launch_delay -= 1

            self.active_chars = [character for character in self.active_chars if character.is_active]
        self.terminal.print()

    def animate_chars(self) -> None:
        """Animates the characters by calling the tick method."""
        for character in self.active_chars:
            character.tick()
