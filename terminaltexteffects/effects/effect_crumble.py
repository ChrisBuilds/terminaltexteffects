import argparse
import random

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils import easing, graphics
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.terminal import Terminal


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "crumble",
        formatter_class=argtypes.CustomFormatter,
        help="Characters lose color and crumble into dust, vacuumed up, and reformed.",
        description="Characters lose color and crumble into dust, vacuumed up, and reformed.",
        epilog=f"""{argtypes.EASING_EPILOG}

Example: terminaltexteffects --effect crumble --animation-rate 0.01 --initial-color 0088bb --dust-colors dadad1 766b69 848789 747a8a --final-color 0088bb""",
    )
    effect_parser.set_defaults(effect_class=CrumbleEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.nonnegative_float,
        default=0.01,
        help="Minimum time, in seconds, between animation steps. This value does not normally need to be modified. Use this to increase the playback speed of all aspects of the effect. This will have no impact beyond a certain lower threshold due to the processing speed of your device.",
    )
    effect_parser.add_argument(
        "--initial-color",
        type=argtypes.color,
        default="0088bb",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the characters at the start of the effect.",
    )
    effect_parser.add_argument(
        "--dust-colors",
        type=argtypes.color,
        nargs="*",
        default=["dadad1", "766b69", "848789", "747a8a"],
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Space separated, unquoted, list of colors for the dust particles.",
    )
    effect_parser.add_argument(
        "--final-color",
        type=argtypes.color,
        default="0eeaff",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the final character.",
    )


class CrumbleEffect:
    """Characters crumble into dust before being vacuumed up and rebuilt."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []

    def prepare_data(self) -> None:
        """Prepares the data for the effect by registering events and building scenes/waypoints."""
        strengthen_flash_gradient = graphics.Gradient([self.args.final_color, "ffffff"], 6)
        strengthen_gradient = graphics.Gradient(["ffffff", self.args.final_color], 9)

        for character in self.terminal._input_characters:
            dust_color = random.choice(self.args.dust_colors)
            weaken_gradient = graphics.Gradient([self.args.initial_color, dust_color], 9)
            self.terminal.set_character_visibility(character, True)
            # set up initial and falling stage
            initial_scn = character.animation.new_scene()
            initial_scn.add_frame(character.input_symbol, 1, color=self.args.initial_color)
            character.animation.activate_scene(initial_scn)
            fall_path = character.motion.new_path(
                speed=0.2,
                ease=easing.out_bounce,
            )
            fall_path.new_waypoint(Coord(character.input_coord.column, self.terminal.output_area.bottom))
            weaken_scn = character.animation.new_scene(id="weaken")
            for color_step in weaken_gradient:
                weaken_scn.add_frame(character.input_symbol, 6, color=color_step)

            top_path = character.motion.new_path(id="top", speed=0.3, ease=easing.out_quint)
            top_path.new_waypoint(
                Coord(character.input_coord.column, self.terminal.output_area.top),
                bezier_control=Coord(self.terminal.output_area.center_column, self.terminal.output_area.center_row),
            )
            # set up reset stage
            input_path = character.motion.new_path(id="input", speed=0.3)
            input_path.new_waypoint(character.input_coord)
            strengthen_flash_scn = character.animation.new_scene()
            for color_step in strengthen_flash_gradient:
                strengthen_flash_scn.add_frame(character.input_symbol, 4, color=color_step)
            strengthen_scn = character.animation.new_scene()
            for color_step in strengthen_gradient:
                strengthen_scn.add_frame(character.input_symbol, 6, color=color_step)
            dust_scn = character.animation.new_scene(sync=graphics.SyncMetric.DISTANCE)
            for _ in range(5):
                dust_scn.add_frame(random.choice(["*", ".", ","]), 1, color=dust_color)

            character.event_handler.register_event(
                EventHandler.Event.SCENE_COMPLETE, weaken_scn, EventHandler.Action.ACTIVATE_PATH, fall_path
            )
            character.event_handler.register_event(
                EventHandler.Event.SCENE_COMPLETE, weaken_scn, EventHandler.Action.SET_LAYER, 1
            )
            character.event_handler.register_event(
                EventHandler.Event.SCENE_COMPLETE, weaken_scn, EventHandler.Action.ACTIVATE_SCENE, dust_scn
            )

            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE,
                input_path,
                EventHandler.Action.ACTIVATE_SCENE,
                strengthen_flash_scn,
            )
            character.event_handler.register_event(
                EventHandler.Event.SCENE_COMPLETE,
                strengthen_flash_scn,
                EventHandler.Action.ACTIVATE_SCENE,
                strengthen_scn,
            )
            self.pending_chars.append(character)

    def run(self) -> None:
        """Runs the effect."""
        # Prepare data for the effect
        self.prepare_data()
        random.shuffle(self.pending_chars)
        fall_delay = 20
        max_fall_delay = 20
        min_fall_delay = 15
        reset = False
        fall_group_maxsize = 1
        stage = "falling"
        unvacuumed_chars = list(self.terminal._input_characters)
        random.shuffle(unvacuumed_chars)
        self.terminal.print()
        while stage != "complete":
            if stage == "falling":
                if self.pending_chars:
                    if fall_delay == 0:
                        # Determine the size of the next group of falling characters
                        fall_group_size = random.randint(1, fall_group_maxsize)
                        # Add the next group of falling characters to the animating characters list
                        for _ in range(fall_group_size):
                            if self.pending_chars:
                                next_char = self.pending_chars.pop(0)
                                next_char.animation.activate_scene(next_char.animation.query_scene("weaken"))
                                self.active_chars.append(next_char)
                        # Reset the fall delay and adjust the fall group size and delay range
                        fall_delay = random.randint(min_fall_delay, max_fall_delay)
                        if random.randint(1, 10) > 4:  # 60% chance to modify the fall delay and group size
                            fall_group_maxsize += 1
                            min_fall_delay = max(0, min_fall_delay - 1)
                            max_fall_delay = max(0, max_fall_delay - 1)
                    else:
                        fall_delay -= 1
                if not self.pending_chars and not self.active_chars:
                    stage = "vacuuming"
            elif stage == "vacuuming":
                if unvacuumed_chars:
                    for _ in range(random.randint(3, 10)):
                        if unvacuumed_chars:
                            next_char = unvacuumed_chars.pop(0)
                            next_char.motion.activate_path(next_char.motion.query_path("top"))
                            self.active_chars.append(next_char)
                if not self.active_chars:
                    stage = "resetting"

            elif stage == "resetting":
                if not reset:
                    for character in self.terminal._input_characters:
                        character.motion.activate_path(character.motion.query_path("input"))
                        self.active_chars.append(character)
                    reset = True
                if not self.active_chars:
                    stage = "complete"

            self.terminal.print()
            self.animate_chars()
            self.active_chars = [character for character in self.active_chars if character.is_active]

    def animate_chars(self) -> None:
        """Animates the characters by calling the tick method."""
        for character in self.active_chars:
            character.tick()
