import argparse
import random

from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils.terminal import Terminal
from terminaltexteffects.utils import graphics, argtypes, motion


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
        default=8,
        metavar="(int > 0)",
        help="Number of characters in each firework shell. Defaults to 8.",
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
        default=30,
        metavar="(int >= 0)",
        help="Number of animation steps to wait between launching each firework shell.",
    )
    effect_parser.add_argument(
        "--launch-easing",
        default="OUT_EXPO",
        type=argtypes.valid_ease,
        help="Easing function to use firework launch.",
    )
    effect_parser.add_argument(
        "--launch-speed",
        type=argtypes.valid_speed,
        default=0.2,
        metavar="(float > 0)",
        help="Firework launch speed. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )
    effect_parser.add_argument(
        "--explode-distance",
        default=10,
        type=argtypes.positive_int,
        metavar="(int > 0)",
        help="Maximum distance a character can travel as a part of the firework explosion.",
    )
    effect_parser.add_argument(
        "--explode-easing",
        default="OUT_QUAD",
        type=argtypes.valid_ease,
        help="Easing function to use firework explosion.",
    )
    effect_parser.add_argument(
        "--explode-speed",
        type=argtypes.valid_speed,
        default=0.3,
        metavar="(float > 0)",
        help="Firework explode speed. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )
    effect_parser.add_argument(
        "--fall-easing",
        default="IN_OUT_CUBIC",
        type=argtypes.valid_ease,
        help="Easing function to use for characters falling into place.",
    )
    effect_parser.add_argument(
        "--fall-speed",
        type=argtypes.valid_speed,
        default=0.4,
        metavar="(float > 0)",
        help="Character fall speed. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
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

    def prepare_waypoints(self) -> None:
        firework_shell: list[EffectCharacter] = []
        origin_x = random.randrange(0, self.terminal.output_area.right)
        origin_y = random.randrange(0, self.terminal.output_area.top)
        origin_coord = motion.Coord(origin_x, origin_y)
        for character in self.terminal.characters:
            if len(firework_shell) == self.args.firework_volume:
                self.shells.append(firework_shell)
                firework_shell = []
                origin_x = random.randrange(0, self.terminal.output_area.right)
                if not self.args.explode_anywhere:
                    min_row = character.input_coord.row
                else:
                    min_row = self.terminal.output_area.bottom
                origin_y = random.randrange(min_row, self.terminal.output_area.top + 1)
                origin_coord = motion.Coord(origin_x, origin_y)
            point_on_circle = random.choice(
                character.motion.find_coords_on_circle(
                    origin_coord, random.randrange(1, self.args.explode_distance), self.args.firework_volume
                )
            )
            character.motion.set_coordinate(motion.Coord(origin_x, self.terminal.output_area.bottom))
            apex_wpt = character.motion.new_waypoint(
                "apex",
                origin_coord,
                speed=self.args.launch_speed,
                ease=self.args.launch_easing,
            )
            explode_wpt = character.motion.new_waypoint(
                "explode",
                point_on_circle,
                speed=self.args.explode_speed,
                ease=self.args.explode_easing,
            )
            input_coord_wpt = character.motion.new_waypoint(
                "input_coord",
                character.input_coord,
                speed=self.args.fall_speed,
                ease=self.args.fall_easing,
            )
            character.event_handler.register_event(
                EventHandler.Event.WAYPOINT_ACTIVATED, apex_wpt, EventHandler.Action.SET_LAYER, 2
            )
            character.event_handler.register_event(
                EventHandler.Event.WAYPOINT_ACTIVATED, input_coord_wpt, EventHandler.Action.SET_LAYER, 1
            )
            character.event_handler.register_event(
                EventHandler.Event.WAYPOINT_REACHED, input_coord_wpt, EventHandler.Action.SET_LAYER, 0
            )
            character.event_handler.register_event(
                EventHandler.Event.WAYPOINT_REACHED,
                apex_wpt,
                EventHandler.Action.ACTIVATE_WAYPOINT,
                explode_wpt,
            )
            character.event_handler.register_event(
                EventHandler.Event.WAYPOINT_REACHED,
                explode_wpt,
                EventHandler.Action.ACTIVATE_WAYPOINT,
                input_coord_wpt,
            )
            character.motion.activate_waypoint(apex_wpt)

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
                    EventHandler.Event.WAYPOINT_REACHED,
                    character.motion.waypoints["apex"],
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
            animating_char.animation.step_animation()
            animating_char.motion.move()
