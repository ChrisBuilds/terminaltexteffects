import argparse
import random

from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils.terminal import Terminal
from terminaltexteffects.utils import graphics, argtypes, motion, easing


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "fireworks",
        formatter_class=argtypes.CustomFormatter,
        help="Characters launch and explode like fireworks and fall into place.",
        description="fireworks | Characters explode like fireworks and fall into place.",
        epilog=f"""        
Example: terminaltexteffects fireworks -a 0.01 --firework-colors 88F7E2 44D492 F5EB67 FFA15C FA233E --firework-symbol o --firework-volume 2 --final-color ffffff --launch-delay 60 --explode-distance 10""",
    )
    effect_parser.set_defaults(effect_class=FireworksEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.nonnegative_float,
        default=0.01,
        help="Minimum time, in seconds, between animation steps. This value does not normally need to be modified. Use this to increase the playback speed of all aspects of the effect. This will have no impact beyond a certain lower threshold due to the processing speed of your device.",
    )
    effect_parser.add_argument(
        "--explode-anywhere",
        action="store_true",
        default=False,
        help="If set, fireworks explode anywhere in the output area. Otherwise, fireworks explode above highest settled row of text.",
    )
    effect_parser.add_argument(
        "--firework-colors",
        type=argtypes.color,
        nargs="*",
        default=["88F7E2", "44D492", "F5EB67", "FFA15C", "FA233E"],
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Space separated list of colors from which firework colors will be randomly selected.",
    )
    effect_parser.add_argument(
        "--firework-symbol",
        type=argtypes.symbol,
        default="o",
        metavar="(single character)",
        help="Symbol to use for the firework shell.",
    )
    effect_parser.add_argument(
        "--firework-volume",
        type=argtypes.float_zero_to_one,
        default=0.02,
        metavar="(float 0 < n <= 1)",
        help="Percent of total characters in each firework shell.",
    )
    effect_parser.add_argument(
        "--final-color",
        type=argtypes.color,
        default="ffffff",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the final character.",
    )
    effect_parser.add_argument(
        "--launch-delay",
        type=argtypes.nonnegative_int,
        default=60,
        metavar="(int >= 0)",
        help="Number of animation steps to wait between launching each firework shell.",
    )
    effect_parser.add_argument(
        "--explode-distance",
        default=0.1,
        type=argtypes.float_zero_to_one,
        metavar="(float 0 < n <= 1)",
        help="Maximum distance from the firework shell origin to the explode waypoint as a percentage of the total output area width.",
    )


class FireworksEffect:
    """Effect that launches characters up the screen where they explode like fireworks and fall into place."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.shells: list[list[EffectCharacter]] = []
        if self.args.firework_colors:
            self.firework_colors = self.args.firework_colors
        else:
            self.firework_colors = ["88F7E2", "44D492", "F5EB67", "FFA15C", "FA233E"]
        self.firework_volume = max(1, round(self.args.firework_volume * len(self.terminal._input_characters)))
        self.explode_distance = min(max(1, round(self.terminal.output_area.right * self.args.explode_distance)), 6)

    def prepare_waypoints(self) -> None:
        firework_shell: list[EffectCharacter] = []
        for character in self.terminal._input_characters:
            if len(firework_shell) == self.firework_volume or not firework_shell:
                self.shells.append(firework_shell)
                firework_shell = []
                origin_x = random.randrange(0, self.terminal.output_area.right)
                if not self.args.explode_anywhere:
                    min_row = character.input_coord.row
                else:
                    min_row = self.terminal.output_area.bottom
                origin_y = random.randrange(min_row, self.terminal.output_area.top + 1)
                origin_coord = motion.Coord(origin_x, origin_y)
                explode_waypoint_coords = motion.Motion.find_coords_in_circle(origin_coord, self.explode_distance)
            character.motion.set_coordinate(motion.Coord(origin_x, self.terminal.output_area.bottom))
            apex_path = character.motion.new_path(id="apex_pth", speed=0.2, ease=easing.out_expo)
            apex_wpt = apex_path.new_waypoint(origin_coord)
            explode_path = character.motion.new_path(speed=0.15, ease=easing.out_circ)
            explode_wpt = explode_path.new_waypoint(random.choice(explode_waypoint_coords))

            # TODO: Turn this process into a framework function for making curves when changing direction
            bloom_control_point = motion.Motion.find_coord_at_distance(
                apex_wpt.coord, explode_wpt.coord, self.explode_distance // 2
            )
            bloom_wpt = explode_path.new_waypoint(
                motion.Coord(bloom_control_point.column, max(1, bloom_control_point.row - 7)),
                bezier_control=bloom_control_point,
            )
            input_path = character.motion.new_path(id="input_pth", speed=0.3, ease=easing.in_out_quart)
            input_control_point = motion.Coord(bloom_wpt.coord.column, 1)
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
        for firework_shell in self.shells:
            shell_color = random.choice(self.firework_colors)
            for character in firework_shell:
                # launch scene
                launch_scn = character.animation.new_scene()
                for color in self.firework_colors:
                    launch_scn.add_frame(self.args.firework_symbol, 2, color=shell_color)
                    launch_scn.add_frame(self.args.firework_symbol, 1, color="FFFFFF")
                    launch_scn.is_looping = True
                # bloom scene
                bloom_scn = character.animation.new_scene()
                bloom_scn.add_frame(character.input_symbol, 1, color=shell_color)
                # fall scene
                fall_scn = character.animation.new_scene()
                fall_gradient = graphics.Gradient([shell_color, self.args.final_color], 15)
                for color in fall_gradient:
                    fall_scn.add_frame(character.input_symbol, 15, color=color)
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
                launch_delay = self.args.launch_delay + 1
            self.terminal.print()
            self.animate_chars()
            launch_delay -= 1

            self.active_chars = [character for character in self.active_chars if character.is_active]
        self.terminal.print()

    def animate_chars(self) -> None:
        """Animates the characters by calling the tick method."""
        for character in self.active_chars:
            character.tick()
