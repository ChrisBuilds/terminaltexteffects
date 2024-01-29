import argparse

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils.terminal import Terminal
from terminaltexteffects.utils import graphics, argtypes, easing


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "cycle",
        formatter_class=argtypes.CustomFormatter,
        help="Characters cycle through a set of symbols before landing on the correct symbol.",
        description="Characters cycle through a set of symbols before landing on the correct symbol.",
        epilog=f"""{argtypes.EASING_EPILOG}

Example: terminaltexteffects cycle -a 0.01 --cycling-color ffa15c --discover-color ffffff --final-color 0ed7b1 --easing IN_OUT_CIRC""",
    )
    effect_parser.set_defaults(effect_class=CycleEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.nonnegative_float,
        default=0.01,
        help="Minimum time, in seconds, between animation steps. This value does not normally need to be modified. Use this to increase the playback speed of all aspects of the effect. This will have no impact beyond a certain lower threshold due to the processing speed of your device.",
    )
    effect_parser.add_argument(
        "--cycling-color",
        type=argtypes.color,
        default="ffa15c",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the characters while cycling symbols.",
    )
    effect_parser.add_argument(
        "--discover-color",
        type=argtypes.color,
        default="ffffff",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the character upon landing on the correct symbol.",
    )
    effect_parser.add_argument(
        "--final-color",
        type=argtypes.color,
        default="0ed7b1",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color the character will fade towards after the discover flash.",
    )
    effect_parser.add_argument(
        "--easing",
        default="IN_OUT_CIRC",
        type=argtypes.ease,
        help="Easing function to use for the cycling animation.",
    )


class CycleEffect:
    """Effect that cycles through a set of characters before landing on the correct character."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.animating_chars: list[EffectCharacter] = []

    def prepare_data(self) -> None:
        """Prepares the data for the effect by building the cycling animations."""
        letters_lower = "abcdefghijklmnopqrstuvwxyz"
        letters_upper = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        numbers = "0123456789"
        symbols = "!@#$%^&*()_+-=[]{}\\|;:'\",<.>/?`~"
        flash_final_gradient = graphics.Gradient(self.args.discover_color, self.args.final_color, 10)
        collection = letters_lower + letters_upper + numbers + symbols
        for character in self.terminal.characters:
            if character.input_symbol not in collection:
                collection += character.input_symbol
            character.is_active = True
            cycle_scn = character.animation.new_scene("cycle")
            for symbol in collection:
                cycle_scn.add_frame(symbol, 4, color=self.args.cycling_color)
            for symbol in collection[: collection.index(character.input_symbol)]:
                cycle_scn.add_frame(symbol, 9, color=self.args.cycling_color)
            cycle_scn.ease = self.args.easing
            final_symbol_scn = character.animation.new_scene("final_symbol")
            for color in flash_final_gradient:
                final_symbol_scn.add_frame(character.input_symbol, 10, color=color)
            final_symbol_scn.ease = easing.in_quart
            character.event_handler.register_event(
                EventHandler.Event.SCENE_COMPLETE, cycle_scn, EventHandler.Action.ACTIVATE_SCENE, final_symbol_scn
            )
            character.animation.activate_scene(cycle_scn)
            self.animating_chars.append(character)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        while self.pending_chars or self.animating_chars:
            self.terminal.print()
            self.animate_chars()

            # remove completed chars from animating chars
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
