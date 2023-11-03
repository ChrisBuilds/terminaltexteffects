import argparse
import random

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils.terminal import Terminal
from terminaltexteffects.utils import graphics, argtypes


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "errorcorrect",
        formatter_class=argtypes.CustomFormatter,
        help="Some characters start in the wrong position and are corrected in sequence.",
        description="Some characters start in the wrong position and are corrected in sequence.",
        epilog=f"""{argtypes.EASING_EPILOG}

Example: terminaltexteffects errorcorrect -a 0.01 --error-pairs 12 --swap-delay 70 --error-color e74c3c --correct-color 45bf55 
         --final-color ffffff --movement-speed 0.5""",
    )
    effect_parser.set_defaults(effect_class=ErrorCorrectEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.valid_animationrate,
        default=0.01,
        help="Time, in seconds, between animation steps.",
    )
    effect_parser.add_argument(
        "--error-pairs",
        type=argtypes.positive_int,
        default=12,
        metavar="(int > 0)",
        help="Number of character pairs to swap.",
    )
    effect_parser.add_argument(
        "--swap-delay",
        type=argtypes.positive_int,
        default=70,
        metavar="(int > 0)",
        help="Number of animation steps between swaps.",
    )
    effect_parser.add_argument(
        "--error-color",
        type=argtypes.valid_color,
        default="e74c3c",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the characters that are in the wrong position.",
    )
    effect_parser.add_argument(
        "--correct-color",
        type=argtypes.valid_color,
        default="45bf55",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the characters once corrected, this is a gradient from error-color and fades to final-color.",
    )
    effect_parser.add_argument(
        "--final-color",
        type=argtypes.valid_color,
        default="ffffff",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the characters in their correct position.",
    )
    effect_parser.add_argument(
        "--movement-speed",
        type=argtypes.valid_speed,
        default=0.5,
        metavar="(float > 0)",
        help="Speed of the characters while moving to the correct position. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )


class ErrorCorrectEffect:
    """Effect that swaps characters from an incorrect initial position to the correct position."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.animating_chars: list[EffectCharacter] = []
        self.swapped: list[tuple[EffectCharacter, EffectCharacter]] = []

    def prepare_data(self) -> None:
        """Prepares the data for the effect by swapping positions and generating animations and waypoints."""
        for character in self.terminal.characters:
            spawn_scene = character.animation.new_scene("spawn")
            spawn_scene.add_frame(character.input_symbol, 1, color=self.args.final_color)
            character.animation.activate_scene(spawn_scene)
            character.is_active = True
        all_characters: list[EffectCharacter] = list(self.terminal.characters)
        correcting_gradient = graphics.Gradient(self.args.error_color, self.args.correct_color, 10)
        final_gradient = graphics.Gradient(self.args.correct_color, self.args.final_color, 10)
        block_symbol = "▓"
        block_wipe_start = ("▁", "▂", "▃", "▄", "▅", "▆", "▇", "█")
        block_wipe_end = ("▇", "▆", "▅", "▄", "▃", "▂", "▁")
        for _ in range(self.args.error_pairs):
            if len(all_characters) < 2:
                break
            char1 = all_characters.pop(random.randrange(len(all_characters)))
            char2 = all_characters.pop(random.randrange(len(all_characters)))
            char1.motion.set_coordinate(char2.input_coord)
            char1_input_coord_waypoint = char1.motion.new_waypoint(
                "input_coord",
                char1.input_coord,
                speed=self.args.movement_speed,
            )
            char2.motion.set_coordinate(char1.input_coord)
            char2_input_coord_waypoint = char2.motion.new_waypoint(
                "input_coord",
                char2.input_coord,
                speed=self.args.movement_speed,
            )
            self.swapped.append((char1, char2))
            for character in (char1, char2):
                first_block_wipe = character.animation.new_scene("first_block_wipe")
                last_block_wipe = character.animation.new_scene("last_block_wipe")
                for block in block_wipe_start:
                    first_block_wipe.add_frame(block, 3, color=self.args.error_color)
                for block in block_wipe_end:
                    last_block_wipe.add_frame(block, 3, color=self.args.correct_color)
                initial_scene = character.animation.new_scene("initial")
                initial_scene.add_frame(character.input_symbol, 1, color=self.args.error_color)
                character.animation.activate_scene(initial_scene)
                error_scene = character.animation.new_scene("error")
                for _ in range(10):
                    error_scene.add_frame(block_symbol, 3, color=self.args.error_color)
                    error_scene.add_frame(character.input_symbol, 3, color="ffffff")
                correcting_scene = character.animation.new_scene("correcting", sync=graphics.SyncMetric.DISTANCE)
                for step in correcting_gradient:
                    correcting_scene.add_frame("█", 3, color=step)
                final_scene = character.animation.new_scene("final")
                for step in final_gradient:
                    final_scene.add_frame(character.input_symbol, 3, color=step)
                character.event_handler.register_event(
                    EventHandler.Event.SCENE_COMPLETE,
                    error_scene,
                    EventHandler.Action.ACTIVATE_SCENE,
                    first_block_wipe,
                )
                character.event_handler.register_event(
                    EventHandler.Event.SCENE_COMPLETE,
                    first_block_wipe,
                    EventHandler.Action.ACTIVATE_SCENE,
                    correcting_scene,
                )
                character.event_handler.register_event(
                    EventHandler.Event.SCENE_COMPLETE,
                    first_block_wipe,
                    EventHandler.Action.ACTIVATE_WAYPOINT,
                    character.motion.waypoints["input_coord"],
                )
                character.event_handler.register_event(
                    EventHandler.Event.WAYPOINT_ACTIVATED,
                    character.motion.waypoints["input_coord"],
                    EventHandler.Action.SET_LAYER,
                    1,
                )
                character.event_handler.register_event(
                    EventHandler.Event.WAYPOINT_REACHED,
                    character.motion.waypoints["input_coord"],
                    EventHandler.Action.SET_LAYER,
                    0,
                )

                character.event_handler.register_event(
                    EventHandler.Event.WAYPOINT_REACHED,
                    character.motion.waypoints["input_coord"],
                    EventHandler.Action.ACTIVATE_SCENE,
                    last_block_wipe,
                )
                character.event_handler.register_event(
                    EventHandler.Event.SCENE_COMPLETE,
                    last_block_wipe,
                    EventHandler.Action.ACTIVATE_SCENE,
                    final_scene,
                )

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        while self.swapped or self.animating_chars:
            swap_delay = self.args.swap_delay
            if self.swapped:
                next_pair = self.swapped.pop(0)
                for char in next_pair:
                    char.animation.activate_scene(char.animation.scenes["error"])
                    self.animating_chars.append(char)
            while swap_delay:
                self.terminal.print()
                self.animate_chars()

                self.animating_chars = [
                    animating_char
                    for animating_char in self.animating_chars
                    if not animating_char.animation.active_scene_is_complete()
                    or not animating_char.motion.movement_is_complete()
                ]
                if not self.animating_chars:
                    pass
                swap_delay -= 1
        self.terminal.print()

    def animate_chars(self) -> None:
        """Animates the characters by calling the move method and step animation. Move characters prior to stepping animation
        to ensure waypoint synced animations have the latest waypoint progress information."""
        for animating_char in self.animating_chars:
            animating_char.motion.move()
            animating_char.animation.step_animation()
