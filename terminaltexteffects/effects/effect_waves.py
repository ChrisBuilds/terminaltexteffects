import argparse

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils import graphics
from terminaltexteffects.utils.terminal import Terminal


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
        "--wave-symbols",
        type=argtypes.symbol_multiple,
        default="▁▂▃▄▅▆▇█▇▆▅▄▃▂▁",
        metavar="(ASCII/UTF-8 character string)",
        help="Symbols to use for the wave animation. Multi-character strings will be used in sequence to create an animation.",
    )
    effect_parser.add_argument(
        "--wave-gradient-stops",
        type=argtypes.color,
        nargs="+",
        default=["8A008A", "00D1FF", "FFFFFF", "00D1FF", "8A008A"],
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )
    effect_parser.add_argument(
        "--wave-gradient-steps",
        type=argtypes.positive_int,
        nargs="+",
        default=[6],
        metavar="(int > 0)",
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )
    effect_parser.add_argument(
        "--final-gradient-stops",
        type=argtypes.color,
        nargs="+",
        default=["8A008A", "00D1FF", "FFFFFF"],
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )
    effect_parser.add_argument(
        "--final-gradient-steps",
        type=argtypes.positive_int,
        nargs="+",
        default=[12],
        metavar="(int > 0)",
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )
    effect_parser.add_argument(
        "--wave-count",
        type=argtypes.positive_int,
        default=7,
        help="Number of waves to generate. n > 0.",
    )
    effect_parser.add_argument(
        "--wave-length",
        type=argtypes.positive_int,
        default=2,
        metavar="(int > 0)",
        help="The number of frames for each step of the wave. Higher wave-lengths will create a slower wave.",
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
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def prepare_data(self) -> None:
        """Prepares the data for the effect by creating the wave animations."""
        final_gradient = graphics.Gradient(self.args.final_gradient_stops, self.args.final_gradient_steps)

        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient.get_color_at_fraction(
                character.input_coord.row / self.terminal.output_area.top
            )

        wave_gradient = graphics.Gradient(self.args.wave_gradient_stops, self.args.wave_gradient_steps)
        for character in self.terminal.get_characters():
            wave_scn = character.animation.new_scene()
            wave_scn.ease = self.args.wave_easing
            for _ in range(self.args.wave_count):
                wave_scn.apply_gradient_to_symbols(
                    wave_gradient, self.args.wave_symbols, duration=self.args.wave_length
                )
            final_scn = character.animation.new_scene()
            for step in graphics.Gradient(
                [wave_gradient.spectrum[-1], self.character_final_color_map[character]],
                self.args.final_gradient_steps,
            ):
                final_scn.add_frame(character.input_symbol, 10, color=step)
            character.event_handler.register_event(
                EventHandler.Event.SCENE_COMPLETE, wave_scn, EventHandler.Action.ACTIVATE_SCENE, final_scn
            )
            character.animation.activate_scene(wave_scn)
        for column in self.terminal.get_characters_grouped(grouping=self.terminal.CharacterGroup.COLUMN_LEFT_TO_RIGHT):
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

            self.active_chars = [character for character in self.active_chars if character.is_active]

    def animate_chars(self) -> None:
        """Animates the characters by calling the tick method on all active characters."""
        for character in self.active_chars:
            character.tick()
