import argparse
import random

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils.terminal import Terminal
from terminaltexteffects.utils import graphics, motion, argtypes, easing


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
        type=argtypes.valid_animationrate,
        default=0.01,
        help="Time, in seconds, between animation steps.",
    )
    effect_parser.add_argument(
        "--initial-color",
        type=argtypes.valid_color,
        default="0088bb",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the characters at the start of the effect.",
    )
    effect_parser.add_argument(
        "--dust-colors",
        type=argtypes.valid_color,
        nargs="*",
        default=["dadad1", "766b69", "848789", "747a8a"],
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Space separated, unquoted, list of colors for the dust particles.",
    )
    effect_parser.add_argument(
        "--final-color",
        type=argtypes.valid_color,
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
        self.animating_chars: list[EffectCharacter] = []

    def prepare_data(self) -> None:
        """Prepares the data for the effect by registering events and building scenes/waypoints."""
        strengthen_flash_gradient = graphics.Gradient(self.args.final_color, "ffffff", 6)
        strengthen_gradient = graphics.Gradient("ffffff", self.args.final_color, 9)

        for character in self.terminal.characters:
            dust_color = random.choice(self.args.dust_colors)
            weaken_gradient = graphics.Gradient(self.args.initial_color, dust_color, 9)
            character.is_active = True
            # set up initial and falling stage
            initial_scn = character.animation.new_scene("initial")
            initial_scn.add_frame(character.input_symbol, 1, color=self.args.initial_color)
            character.animation.activate_scene(initial_scn)
            fall_path = character.motion.new_path(
                "fall",
                speed=0.2,
                ease=easing.out_bounce,
            )
            fall_wpt = fall_path.new_waypoint(
                "fall", motion.Coord(character.input_coord.column, self.terminal.output_area.bottom)
            )
            weaken_scn = character.animation.new_scene("weaken")
            for color_step in weaken_gradient:
                weaken_scn.add_frame(character.input_symbol, 6, color=color_step)

            # set up vacuuming stage
            bottom_vac_path = character.motion.new_path("bottom_vac", speed=0.3, ease=easing.in_quint)
            bottom_vac_wpt = bottom_vac_path.new_waypoint(
                "bottom_vac",
                motion.Coord(
                    self.terminal.output_area.center_column,
                    round(self.terminal.output_area.top * random.uniform(0.1, 0.3)),
                ),
                bezier_control=motion.Coord(self.terminal.output_area.center_column, 1),
            )
            top_vac_path = character.motion.new_path("top_vac", speed=0.3)
            top_vac_wpt = top_vac_path.new_waypoint(
                "top_vac",
                motion.Coord(
                    self.terminal.output_area.center_column,
                    round(self.terminal.output_area.top * random.uniform(0.7, 0.9)),
                ),
            )
            top_path = character.motion.new_path("top", speed=0.3, ease=easing.out_quint)
            top_wpt = top_path.new_waypoint(
                "top",
                motion.Coord(character.input_coord.column, self.terminal.output_area.top),
                bezier_control=motion.Coord(self.terminal.output_area.center_column, self.terminal.output_area.top),
            )
            # set up reset stage
            input_path = character.motion.new_path("input", speed=0.3)
            input_wpt = input_path.new_waypoint("input", character.input_coord)
            strengthen_flash_scn = character.animation.new_scene("strengthen_flash")
            for color_step in strengthen_flash_gradient:
                strengthen_flash_scn.add_frame(character.input_symbol, 4, color=color_step)
            strengthen_scn = character.animation.new_scene("strengthen")
            for color_step in strengthen_gradient:
                strengthen_scn.add_frame(character.input_symbol, 6, color=color_step)
            dust_scn = character.animation.new_scene("dust", sync=graphics.SyncMetric.DISTANCE)
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
                EventHandler.Event.PATH_COMPLETE, bottom_vac_path, EventHandler.Action.ACTIVATE_PATH, top_vac_path
            )
            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE, top_vac_path, EventHandler.Action.ACTIVATE_PATH, top_path
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
        vacuumed = False
        reset = False
        fall_group_maxsize = 1
        stage = "falling"
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
                                next_char.animation.activate_scene(next_char.animation.scenes["weaken"])
                                self.animating_chars.append(next_char)
                        # Reset the fall delay and adjust the fall group size and delay range
                        fall_delay = random.randint(min_fall_delay, max_fall_delay)
                        if random.randint(1, 10) > 4:  # 60% chance to modify the fall delay and group size
                            fall_group_maxsize += 1
                            min_fall_delay = max(0, min_fall_delay - 1)
                            max_fall_delay = max(0, max_fall_delay - 1)
                    else:
                        fall_delay -= 1
                if not self.pending_chars and not self.animating_chars:
                    stage = "vacuuming"
            elif stage == "vacuuming":
                if not vacuumed:
                    for character in self.terminal.characters:
                        character.motion.activate_path(character.motion.paths["bottom_vac"])
                        self.animating_chars.append(character)
                    vacuumed = True
                if not self.animating_chars:
                    stage = "resetting"

            elif stage == "resetting":
                if not reset:
                    for character in self.terminal.characters:
                        character.motion.activate_path(character.motion.paths["input"])
                        self.animating_chars.append(character)
                    reset = True
                if not self.animating_chars:
                    stage = "complete"

            self.terminal.print()
            self.animate_chars()
            self.animating_chars = [
                animating_char
                for animating_char in self.animating_chars
                if not animating_char.animation.active_scene_is_complete()
                or not animating_char.motion.movement_is_complete()
            ]

    def animate_chars(self) -> None:
        """Animates the characters by calling the move method and step animation. Move characters prior to stepping animation
        to ensure waypoint synced animations have the latest waypoint progress information."""
        for animating_char in self.animating_chars:
            animating_char.motion.move()
            animating_char.animation.step_animation()
