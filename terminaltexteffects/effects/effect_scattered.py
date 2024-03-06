import argparse

from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils import argtypes, graphics, terminal
from terminaltexteffects.utils.geometry import Coord


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "scattered",
        formatter_class=argtypes.CustomFormatter,
        help="Move the characters into place from random starting locations.",
        description="scattered | Move the characters into place from random starting locations.",
        epilog=f"""{argtypes.EASING_EPILOG}
        
Example: terminaltexteffects scattered --movement-speed 0.5 --easing IN_OUT_BACK""",
    )
    effect_parser.set_defaults(effect_class=ScatteredEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.nonnegative_float,
        default=0.01,
        help="Time between animation steps.",
    )
    effect_parser.add_argument(
        "--gradient-stops",
        type=argtypes.Color,
        nargs="+",
        default=["8A008A", "00D1FF", "FFFFFF"],
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Space separated, unquoted, list of colors for the character gradient. If only one color is provided, the characters will be displayed in that color.",
    )
    effect_parser.add_argument(
        "--gradient-steps",
        type=argtypes.positive_int,
        default=[12],
        metavar="(int > 0)",
        help="Number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )
    effect_parser.add_argument(
        "--gradient-frames",
        type=argtypes.positive_int,
        default=12,
        metavar="(int > 0)",
        help="Number of frames to display each gradient step.",
    )
    effect_parser.add_argument(
        "--movement-speed",
        type=argtypes.positive_float,
        default=0.5,
        metavar="(float > 0)",
        help="Movement speed of the characters. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )
    effect_parser.add_argument(
        "--easing",
        default="IN_OUT_BACK",
        type=argtypes.ease,
        help="Easing function to use for character movement.",
    )


class ScatteredEffect:
    """Effect that moves the characters into position from random starting locations."""

    def __init__(self, terminal: terminal.Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def prepare_data(self) -> None:
        """Prepares the data for the effect by scattering the characters within range of the input width and height."""
        final_gradient = graphics.Gradient(self.args.gradient_stops, self.args.gradient_steps)

        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient.get_color_at_fraction(
                character.input_coord.row / self.terminal.output_area.top
            )
        for character in self.terminal.get_characters():
            if self.terminal.output_area.right < 2 or self.terminal.output_area.top < 2:
                character.motion.set_coordinate(Coord(1, 1))
            else:
                character.motion.set_coordinate(self.terminal.output_area.random_coord())
            input_coord_path = character.motion.new_path(speed=self.args.movement_speed, ease=self.args.easing)
            input_coord_path.new_waypoint(character.input_coord)
            character.event_handler.register_event(
                EventHandler.Event.PATH_ACTIVATED, input_coord_path, EventHandler.Action.SET_LAYER, 1
            )
            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE, input_coord_path, EventHandler.Action.SET_LAYER, 0
            )
            character.motion.activate_path(input_coord_path)
            self.terminal.set_character_visibility(character, True)
            gradient_scn = character.animation.new_scene()
            char_gradient = graphics.Gradient(
                [final_gradient.spectrum[0], self.character_final_color_map[character]], 10
            )
            gradient_scn.apply_gradient_to_symbols(char_gradient, character.input_symbol, self.args.gradient_frames)
            character.animation.activate_scene(gradient_scn)
            self.active_chars.append(character)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        self.terminal.print()
        while self.pending_chars or self.active_chars:
            self.animate_chars()
            self.active_chars = [character for character in self.active_chars if character.is_active]
            self.terminal.print()

    def animate_chars(self) -> None:
        for character in self.active_chars:
            character.tick()
