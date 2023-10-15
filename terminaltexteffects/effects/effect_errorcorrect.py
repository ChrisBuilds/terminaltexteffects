import argparse
import random

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects import base_character, base_effect
from terminaltexteffects.base_character import EventHandler
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
        "--error-color",  # make more descriptive
        type=argtypes.valid_color,
        default="e74c3c",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the characters that are in the wrong position.",
    )
    effect_parser.add_argument(
        "--correct-color",  # make more descriptive
        type=argtypes.valid_color,
        default="45bf55",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the characters once corrected, this is a gradient from error-color and fades to final-color.",
    )
    effect_parser.add_argument(
        "--final-color",  # make more descriptive
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


class ErrorCorrectEffect(base_effect.Effect):
    """Effect that swaps characters from an incorrect initial position to the correct position."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        super().__init__(terminal, args)
        self.swapped: list[tuple[base_character.EffectCharacter, base_character.EffectCharacter]] = []

    def prepare_data(self) -> None:
        """Prepares the data for the effect by swapping positions and generating animations and waypoints."""
        for character in self.terminal.characters:
            character.animation.add_effect_to_scene("spawn", character.input_symbol, self.args.final_color, 1)
            character.animation.activate_scene("spawn")
            character.is_active = True
        all_characters: list[base_character.EffectCharacter] = list(self.terminal.characters)
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
            char1.motion.set_coordinate(char2.input_coord.column, char2.input_coord.row)
            char1.motion.new_waypoint(
                "input_coord",
                char1.input_coord.column,
                char1.input_coord.row,
                self.args.movement_speed,
                layer=1,
            )
            char2.motion.set_coordinate(char1.input_coord.column, char1.input_coord.row)
            char2.motion.new_waypoint(
                "input_coord",
                char2.input_coord.column,
                char2.input_coord.row,
                self.args.movement_speed,
                layer=1,
            )
            self.swapped.append((char1, char2))
            for character in (char1, char2):
                for block in block_wipe_start:
                    character.animation.add_effect_to_scene("circles_start", block, self.args.error_color, 3)
                for block in block_wipe_end:
                    character.animation.add_effect_to_scene("circles_end", block, self.args.correct_color, 3)
                character.animation.add_effect_to_scene("initial", character.input_symbol, self.args.error_color, 1)
                character.animation.activate_scene("initial")
                for _ in range(10):
                    character.animation.add_effect_to_scene("error", block_symbol, self.args.error_color, 3)
                    character.animation.add_effect_to_scene("error", character.input_symbol, "ffffff", 3)
                for step in correcting_gradient:
                    character.animation.add_effect_to_scene("correcting", "█", step, 3)
                character.animation.scenes["correcting"].waypoint_sync_id = "input_coord"
                for step in final_gradient:
                    character.animation.add_effect_to_scene("final", character.input_symbol, step, 3)
                character.event_handler.register_event(
                    EventHandler.Event.SCENE_COMPLETE,
                    "circles_start",
                    EventHandler.Action.ACTIVATE_WAYPOINT,
                    "input_coord",
                )
                character.event_handler.register_event(
                    EventHandler.Event.SCENE_COMPLETE, "error", EventHandler.Action.ACTIVATE_SCENE, "circles_start"
                )
                character.event_handler.register_event(
                    EventHandler.Event.SCENE_COMPLETE, "circles_start", EventHandler.Action.ACTIVATE_SCENE, "correcting"
                )
                character.event_handler.register_event(
                    EventHandler.Event.WAYPOINT_REACHED,
                    "input_coord",
                    EventHandler.Action.ACTIVATE_SCENE,
                    "circles_end",
                )
                character.event_handler.register_event(
                    EventHandler.Event.SCENE_COMPLETE, "circles_end", EventHandler.Action.ACTIVATE_SCENE, "final"
                )

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        while self.swapped or self.animating_chars:
            swap_delay = self.args.swap_delay
            if self.swapped:
                next_pair = self.swapped.pop(0)
                for char in next_pair:
                    char.animation.activate_scene("error")
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
