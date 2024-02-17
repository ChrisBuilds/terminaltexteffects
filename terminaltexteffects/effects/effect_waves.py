import argparse

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
        "waves",
        formatter_class=argtypes.CustomFormatter,
        help="Waves travel across the terminal leaving behind the characters.",
        description="Waves travel across the terminal leaving behind the characters.",
        epilog=f"""{argtypes.EASING_EPILOG}

Example: terminaltexteffects waves -a 0.01 --wave-deep-color 4651e3 --wave-shallow-color 57FB92 --final-color 80F7E6 --wave-count 6 --wave-easing IN_OUT_SINE""",
    )
    effect_parser.set_defaults(effect_class=WavesEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.nonnegative_float,
        default=0.01,
        help="Minimum time, in seconds, between animation steps. This value does not normally need to be modified. Use this to increase the playback speed of all aspects of the effect. This will have no impact beyond a certain lower threshold due to the processing speed of your device.",
    )
    effect_parser.add_argument(
        "--wave-deep-color",
        type=argtypes.color,
        default="4651e3",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the deepest part of the wave. A gradient is generated between the shallow and deep parts of the wave.",
    )
    effect_parser.add_argument(
        "--wave-shallow-color",  # make more descriptive
        type=argtypes.color,
        default="57FB92",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the shallow part of the wave. A gradient is generated between the shallow and deep parts of the wave..",
    )
    effect_parser.add_argument(
        "--final-color",
        type=argtypes.color,
        default="80F7E6",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the final character. A gradient is generated between the shallow part of the wave and the final color.",
    )
    effect_parser.add_argument(
        "--wave-count",
        type=argtypes.positive_int,
        default=6,
        help="Number of waves to generate. n > 0.",
    )
    effect_parser.add_argument(
        "--wave-easing",
        default="IN_OUT_SINE",
        type=argtypes.ease,
        help="Easing function to use for wave travel.",
    )


class WavesEffect:
    """Effect that creates waves that travel across the terminal, leaving behind the characters."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_columns: list[list[EffectCharacter]] = []
        self.active_chars: list[EffectCharacter] = []

    def prepare_data(self) -> None:
        """Prepares the data for the effect by creating the wave animations."""
        block_wipe_start = ("▁", "▂", "▃", "▄", "▅", "▆", "▇", "█")
        block_wipe_end = ("▇", "▆", "▅", "▄", "▃", "▂", "▁")
        wave_gradient_light = graphics.Gradient([self.args.wave_shallow_color, self.args.wave_deep_color], 8)
        wave_gradient_dark = graphics.Gradient([self.args.wave_deep_color, self.args.wave_shallow_color], 8)
        wave_gradient = list(wave_gradient_light) + list(wave_gradient_dark)[1:]
        colored_waves = list(zip(block_wipe_start + block_wipe_end, wave_gradient))
        final_gradient = graphics.Gradient([self.args.wave_shallow_color, self.args.final_color], 8)
        for character in self.terminal._input_characters:
            wave_scn = character.animation.new_scene()
            wave_scn.ease = self.args.wave_easing
            for _ in range(self.args.wave_count):
                for block, color in colored_waves:
                    wave_scn.add_frame(block, 3, color=color)
            final_scn = character.animation.new_scene()
            for step in final_gradient:
                final_scn.add_frame(character.input_symbol, 15, color=step)
            character.event_handler.register_event(
                EventHandler.Event.SCENE_COMPLETE, wave_scn, EventHandler.Action.ACTIVATE_SCENE, final_scn
            )
            character.animation.activate_scene(wave_scn)
        for column in self.terminal.get_characters_sorted(sort_order=self.terminal.CharacterSort.COLUMN_LEFT_TO_RIGHT):
            self.pending_columns.append(column)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        while self.pending_columns or self.active_chars:
            if self.pending_columns:
                next_column = self.pending_columns.pop(0)
                for character in next_column:
                    self.terminal.set_character_visibility(character, True)
                    self.active_chars.append(character)
            self.terminal.print()
            self.animate_chars()

            self.active_chars = [character for character in self.active_chars if character.is_active()]

    def animate_chars(self) -> None:
        """Animates the characters by calling the tick method on all active characters."""
        for character in self.active_chars:
            character.tick()
