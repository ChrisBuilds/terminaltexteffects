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
        type=argtypes.valid_animationrate,
        default=0.01,
        help="Time, in seconds, between animation steps.",
    )
    effect_parser.add_argument(
        "--wave-deep-color",
        type=argtypes.valid_color,
        default="4651e3",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the deepest part of the wave. A gradient is generated between the shallow and deep parts of the wave.",
    )
    effect_parser.add_argument(
        "--wave-shallow-color",  # make more descriptive
        type=argtypes.valid_color,
        default="57FB92",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the shallow part of the wave. A gradient is generated between the shallow and deep parts of the wave..",
    )
    effect_parser.add_argument(
        "--final-color",
        type=argtypes.valid_color,
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
        type=argtypes.valid_ease,
        help="Easing function to use for wave travel.",
    )


class WavesEffect:
    """Effect that creates waves that travel across the terminal, leaving behind the characters."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_columns: list[list[EffectCharacter]] = []
        self.animating_chars: list[EffectCharacter] = []

    def prepare_data(self) -> None:
        """Prepares the data for the effect by creating the wave animations."""
        block_wipe_start = ("▁", "▂", "▃", "▄", "▅", "▆", "▇", "█")
        block_wipe_end = ("▇", "▆", "▅", "▄", "▃", "▂", "▁")
        wave_gradient_light = graphics.Gradient(self.args.wave_shallow_color, self.args.wave_deep_color, 8)
        wave_gradient_dark = graphics.Gradient(self.args.wave_deep_color, self.args.wave_shallow_color, 8)
        wave_gradient = list(wave_gradient_light) + list(wave_gradient_dark)[1:]
        colored_waves = list(zip(block_wipe_start + block_wipe_end, wave_gradient))
        final_gradient = graphics.Gradient(self.args.wave_shallow_color, self.args.final_color, 8)
        for character in self.terminal.characters:
            wave_scn = character.animation.new_scene("wave")
            wave_scn.ease = self.args.wave_easing
            for _ in range(self.args.wave_count):
                for block, color in colored_waves:
                    wave_scn.add_frame(block, 3, color=color)
            final_scn = character.animation.new_scene("final")
            for step in final_gradient:
                final_scn.add_frame(character.input_symbol, 15, color=step)
            character.event_handler.register_event(
                EventHandler.Event.SCENE_COMPLETE, wave_scn, EventHandler.Action.ACTIVATE_SCENE, final_scn
            )
            character.animation.activate_scene(wave_scn)
        columns = self.terminal.input_by_column()
        for _, column in columns.items():
            self.pending_columns.append(column)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        while self.pending_columns or self.animating_chars:
            if self.pending_columns:
                next_column = self.pending_columns.pop(0)
                for character in next_column:
                    character.is_active = True
                    self.animating_chars.append(character)
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
