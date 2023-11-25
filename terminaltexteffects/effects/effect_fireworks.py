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
        epilog=f"""{argtypes.EASING_EPILOG}
        
Example: terminaltexteffects fireworks -a 0.01 --firework-colors 88F7E2 44D492 F5EB67 FFA15C FA233E --final-color 000000 --launch-delay 30 --launch-easing OUT_EXPO --launch-speed 0.2 --explode-easing OUT_QUAD --explode-speed 0.3 --fall-easing IN_SINE --fall-speed 0.6""",
    )
    effect_parser.set_defaults(effect_class=FireworksEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.valid_animationrate,
        default=0.01,
        help="Time, in seconds, between animation steps.",
    )
    effect_parser.add_argument(
        "--explode-anywhere",
        action="store_true",
        default=False,
        help="If set, fireworks explode anywhere in the output area. Otherwise, fireworks explode above highest settled row of text.",
    )
    effect_parser.add_argument(
        "--firework-colors",
        type=argtypes.valid_color,
        nargs="*",
        default=0,
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Space separated list of colors from which firework colors will be randomly selected.",
    )
    effect_parser.add_argument(
        "--firework-symbol",
        type=argtypes.valid_symbol,
        default="⯏",
        metavar="(single character)",
        help="Symbol to use for the firework shell. Defaults to ⯏.",
    )
    effect_parser.add_argument(
        "--firework-volume",
        type=argtypes.positive_int,
        default=3,
        metavar="(int > 0)",
        help="Percent of total characters in each firework shell. Defaults to 3.",
    )
    effect_parser.add_argument(
        "--final-color",
        type=argtypes.valid_color,
        default="ffffff",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the final character. Defaults to white.",
    )
    effect_parser.add_argument(
        "--launch-delay",
        type=argtypes.ge_zero,
        default=60,
        metavar="(int >= 0)",
        help="Number of animation steps to wait between launching each firework shell.",
    )
    effect_parser.add_argument(
        "--explode-distance",
        default=6,
        type=argtypes.positive_int,
        metavar="(int > 0)",
        help="Maximum distance a character can travel as a part of the firework explosion.",
    )


class FireworksEffect:
    """Effect that launches characters up the screen where they explode like fireworks and fall into place."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.animating_chars: list[EffectCharacter] = []
        self.shells: list[list[EffectCharacter]] = []
        if self.args.firework_colors:
            self.firework_colors = self.args.firework_colors
        else:
            self.firework_colors = ["88F7E2", "44D492", "F5EB67", "FFA15C", "FA233E"]
        self.firework_volume = max(1, round((self.args.firework_volume * 0.01) * len(self.terminal.characters)))
        self.explode_distance = min(max(1, self.terminal.output_area.right // 10), 8)

    def prepare_waypoints(self) -> None:
        firework_shell: list[EffectCharacter] = []
        for character in self.terminal.characters:
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
                explode_waypoint_coords = motion.Motion.find_coords_in_circle(
                    origin_coord, self.explode_distance, self.firework_volume
                )
            character.motion.set_coordinate(motion.Coord(origin_x, self.terminal.output_area.bottom))
            # apex_path = character.motion.new_path("apex_pth", speed=0.2, ease=easing.out_expo)
            apex_path = character.motion.new_path("apex_pth", speed=0.2)
            apex_wpt = apex_path.new_waypoint("apex_wpt", origin_coord)
            # explode_path = character.motion.new_path("explode_pth", speed=0.3, ease=easing.out_quad)
            explode_path = character.motion.new_path("explode_pth", speed=0.3)
            explode_wpt = explode_path.new_waypoint("explode_wpt", random.choice(explode_waypoint_coords))

            # TODO: Turn this process into a framework function for making curves when changing direction
            control_point = motion.Motion.find_coord_at_distance(
                apex_wpt.coord, explode_wpt.coord, self.explode_distance // 2
            )
            fall_wpt = explode_path.new_waypoint(
                "fall",
                motion.Coord(control_point.column, max(1, control_point.row - (apex_wpt.coord.row // 2))),
                bezier_control=control_point,
            )
            fall_control_point = motion.Coord(fall_wpt.coord.column, fall_wpt.coord.row - 5)
            input_coord_wpt = explode_path.new_waypoint(
                "input_coord", character.input_coord, bezier_control=fall_control_point
            )
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

            character.motion.activate_path(apex_path)

            firework_shell.append(character)
        if firework_shell:
            self.shells.append(firework_shell)

    def prepare_scenes(self) -> None:
        for firework_shell in self.shells:
            shell_color = random.choice(self.firework_colors)
            for character in firework_shell:
                # launch scene
                launch_scn = character.animation.new_scene("launch")
                for color in self.firework_colors:
                    launch_scn.add_frame(self.args.firework_symbol, 2, color=shell_color)
                    launch_scn.add_frame(self.args.firework_symbol, 1, color="FFFFFF")
                    launch_scn.is_looping = True
                # bloom scene
                bloom_scn = character.animation.new_scene("bloom")
                bloom_gradient = graphics.Gradient(shell_color, self.args.final_color, 15)
                for color in bloom_gradient:
                    bloom_scn.add_frame(character.input_symbol, 15, color=color)
                character.animation.activate_scene(launch_scn)
                character.event_handler.register_event(
                    EventHandler.Event.PATH_COMPLETE,
                    character.motion.paths["apex_pth"],
                    EventHandler.Action.ACTIVATE_SCENE,
                    bloom_scn,
                )

    def prepare_data(self) -> None:
        """Prepares the data for the effect by ___."""
        self.prepare_waypoints()
        self.prepare_scenes()

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        launch_delay = 0
        while self.shells or self.animating_chars:
            if self.shells and launch_delay == 0:
                next_group = self.shells.pop()
                for character in next_group:
                    character.is_active = True
                    self.animating_chars.append(character)
                launch_delay = self.args.launch_delay + 1
            self.terminal.print()
            self.animate_chars()
            launch_delay -= 1

            # remove completed chars from animating chars
            self.animating_chars = [
                animating_char
                for animating_char in self.animating_chars
                if not animating_char.animation.active_scene_is_complete()
                or not animating_char.motion.movement_is_complete()
            ]
        self.terminal.print()

    def animate_chars(self) -> None:
        """Animates the characters by calling the move method and step animation."""
        for animating_char in self.animating_chars:
            animating_char.motion.move()
            animating_char.animation.step_animation()
