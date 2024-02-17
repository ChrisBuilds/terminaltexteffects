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
        type=argtypes.nonnegative_float,
        default=0.01,
        help="Minimum time, in seconds, between animation steps. This value does not normally need to be modified. Use this to increase the playback speed of all aspects of the effect. This will have no impact beyond a certain lower threshold due to the processing speed of your device.",
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
        type=argtypes.color,
        default="e74c3c",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the characters that are in the wrong position.",
    )
    effect_parser.add_argument(
        "--correct-color",
        type=argtypes.color,
        default="45bf55",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the characters once corrected, this is a gradient from error-color and fades to final-color.",
    )
    effect_parser.add_argument(
        "--final-color",
        type=argtypes.color,
        default="ffffff",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the characters in their correct position.",
    )
    effect_parser.add_argument(
        "--movement-speed",
        type=argtypes.positive_float,
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
        self.active_chars: list[EffectCharacter] = []
        self.swapped: list[tuple[EffectCharacter, EffectCharacter]] = []

    def prepare_data(self) -> None:
        """Prepares the data for the effect by swapping positions and generating animations and waypoints."""
        for character in self.terminal._input_characters:
            spawn_scene = character.animation.new_scene()
            spawn_scene.add_frame(character.input_symbol, 1, color=self.args.final_color)
            character.animation.activate_scene(spawn_scene)
            self.terminal.set_character_visibility(character, True)
        all_characters: list[EffectCharacter] = list(self.terminal._input_characters)
        correcting_gradient = graphics.Gradient([self.args.error_color, self.args.correct_color], 10)
        final_gradient = graphics.Gradient([self.args.correct_color, self.args.final_color], 10)
        block_symbol = "▓"
        block_wipe_start = ("▁", "▂", "▃", "▄", "▅", "▆", "▇", "█")
        block_wipe_end = ("▇", "▆", "▅", "▄", "▃", "▂", "▁")
        for _ in range(self.args.error_pairs):
            if len(all_characters) < 2:
                break
            char1 = all_characters.pop(random.randrange(len(all_characters)))
            char2 = all_characters.pop(random.randrange(len(all_characters)))
            char1.motion.set_coordinate(char2.input_coord)
            char1_input_coord_path = char1.motion.new_path(id="input_coord", speed=self.args.movement_speed)
            char1_input_coord_path.new_waypoint(char1.input_coord)
            char2.motion.set_coordinate(char1.input_coord)
            char2_input_coord_path = char2.motion.new_path(id="input_coord", speed=self.args.movement_speed)
            char2_input_coord_path.new_waypoint(char2.input_coord)
            self.swapped.append((char1, char2))
            for character in (char1, char2):
                first_block_wipe = character.animation.new_scene()
                last_block_wipe = character.animation.new_scene()
                for block in block_wipe_start:
                    first_block_wipe.add_frame(block, 3, color=self.args.error_color)
                for block in block_wipe_end:
                    last_block_wipe.add_frame(block, 3, color=self.args.correct_color)
                initial_scene = character.animation.new_scene()
                initial_scene.add_frame(character.input_symbol, 1, color=self.args.error_color)
                character.animation.activate_scene(initial_scene)
                error_scene = character.animation.new_scene(id="error")
                for _ in range(10):
                    error_scene.add_frame(block_symbol, 3, color=self.args.error_color)
                    error_scene.add_frame(character.input_symbol, 3, color="ffffff")
                correcting_scene = character.animation.new_scene(sync=graphics.SyncMetric.DISTANCE)
                for step in correcting_gradient:
                    correcting_scene.add_frame("█", 3, color=step)
                final_scene = character.animation.new_scene()
                for step in final_gradient:
                    final_scene.add_frame(character.input_symbol, 3, color=step)
                input_coord_path = character.motion.query_path("input_coord")
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
                    EventHandler.Action.ACTIVATE_PATH,
                    input_coord_path,
                )
                character.event_handler.register_event(
                    EventHandler.Event.PATH_ACTIVATED,
                    input_coord_path,
                    EventHandler.Action.SET_LAYER,
                    1,
                )
                character.event_handler.register_event(
                    EventHandler.Event.PATH_COMPLETE,
                    input_coord_path,
                    EventHandler.Action.SET_LAYER,
                    0,
                )

                character.event_handler.register_event(
                    EventHandler.Event.PATH_COMPLETE,
                    input_coord_path,
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
        while self.swapped or self.active_chars:
            swap_delay = self.args.swap_delay
            if self.swapped:
                next_pair = self.swapped.pop(0)
                for char in next_pair:
                    char.animation.activate_scene(char.animation.query_scene("error"))
                    self.active_chars.append(char)
            while swap_delay:
                self.terminal.print()
                self.animate_chars()

                self.active_chars = [character for character in self.active_chars if character.is_active()]
                if not self.active_chars:
                    pass
                swap_delay -= 1
        self.terminal.print()

    def animate_chars(self) -> None:
        """Animates the characters by calling the tick method on all active characters."""
        for character in self.active_chars:
            character.tick()
