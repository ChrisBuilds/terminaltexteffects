import argparse
import random

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils import graphics
from terminaltexteffects.utils.terminal import Terminal


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "beams",
        formatter_class=argtypes.CustomFormatter,
        help="Create beams which travel over the output area illuminating the characters behind them.",
        description="Create beams which travel over the output area illuminating the characters behind them.",
        epilog="""Example: terminaltexteffects beam -a 0.01 --beam-row-symbols ▂▁_ --beam-column-symbols ▌▍▎▏ --beam-delay 10 --beam-gradient-stops ffffff 00D1FF 8A008A --beam-gradient-steps 2 8 --beam-gradient-frames 2 --text-glow-color 00D1FF --text-fade-color 333333 --final-gradient-stops 8A008A 00D1FF ffffff --final-gradient-steps 6 --final-gradient-frames 5 --final-wipe-speed 1""",
    )
    effect_parser.set_defaults(effect_class=BeamsEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.nonnegative_float,
        default=0.01,
        help="Minimum time, in seconds, between animation steps. This value does not normally need to be modified. Use this to increase the playback speed of all aspects of the effect. This will have no impact beyond a certain lower threshold due to the processing speed of your device.",
    )
    effect_parser.add_argument(
        "--beam-row-symbols",
        type=argtypes.symbol_multiple,
        default="▂▁_",
        metavar="(ASCII/UTF-8 character string)",
        help="Symbols to use for the beam effect when moving along a row. Multi-character strings will be used in sequence to create an animation.",
    )
    effect_parser.add_argument(
        "--beam-column-symbols",
        type=argtypes.symbol_multiple,
        default="▌▍▎▏",
        metavar="(ASCII/UTF-8 character string)",
        help="Symbols to use for the beam effect when moving along a column. Multi-character strings will be used in sequence to create an animation.",
    )
    effect_parser.add_argument(
        "--beam-delay",
        type=argtypes.positive_int,
        default=10,
        metavar="(int > 0)",
        help="Number of frames to wait before adding the next group of beams. Beams are added in groups of size random(1, 5).",
    )
    effect_parser.add_argument(
        "--beam-row-min-speed",
        type=argtypes.positive_int,
        default=10,
        metavar="(int > 0)",
        help="Minimum speed of the beam when moving along a row.",
    )
    effect_parser.add_argument(
        "--beam-row-max-speed",
        type=argtypes.positive_int,
        default=40,
        metavar="(int > 0)",
        help="Maximum speed of the beam when moving along a row.",
    )
    effect_parser.add_argument(
        "--beam-column-min-speed",
        type=argtypes.positive_int,
        default=6,
        metavar="(int > 0)",
        help="Minimum speed of the beam when moving along a column.",
    )
    effect_parser.add_argument(
        "--beam-column-max-speed",
        type=argtypes.positive_int,
        default=10,
        metavar="(int > 0)",
        help="Maximum speed of the beam when moving along a column.",
    )
    effect_parser.add_argument(
        "--beam-gradient-stops",
        type=argtypes.color,
        nargs="+",
        default=["ffffff", "00D1FF", "8A008A"],
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Space separated, unquoted, list of colors for the beam, a gradient will be created between the colors.",
    )
    effect_parser.add_argument(
        "--beam-gradient-steps",
        type=argtypes.positive_int,
        nargs="+",
        default=[2, 8],
        metavar="(int > 0)",
        help="Space separated, unquoted, numbers for the of gradient steps to use. More steps will create a smoother and longer gradient animation. Steps are paired with the colors in final-gradient-stops.",
    )
    effect_parser.add_argument(
        "--beam-gradient-frames",
        type=argtypes.positive_int,
        default=2,
        metavar="(int > 0)",
        help="Number of frames to display each gradient step.",
    )
    effect_parser.add_argument(
        "--final-gradient-stops",
        type=argtypes.color,
        nargs="+",
        default=["8A008A", "00D1FF", "ffffff"],
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Space separated, unquoted, list of colors for the wipe gradient.",
    )
    effect_parser.add_argument(
        "--final-gradient-steps",
        type=argtypes.positive_int,
        nargs="+",
        default=[12],
        metavar="(int > 0)",
        help="Space separated, unquoted, numbers for the of gradient steps to use. More steps will create a smoother and longer gradient animation. Steps are paired with the colors in final-gradient-stops.",
    )
    effect_parser.add_argument(
        "--final-gradient-frames",
        type=argtypes.positive_int,
        default=5,
        metavar="(int > 0)",
        help="Number of frames to display each gradient step.",
    )
    effect_parser.add_argument(
        "--final-wipe-speed",
        type=argtypes.positive_int,
        default=1,
        metavar="(int > 0)",
        help="Speed of the final wipe as measured in diagonal groups activated per frame.",
    )


class Group:
    def __init__(self, characters: list[EffectCharacter], direction: str, terminal: Terminal, args: argparse.Namespace):
        self.characters = characters
        self.direction: str = direction
        self.terminal = terminal
        direction_speed_range = {
            "row": (args.beam_row_min_speed, args.beam_row_max_speed),
            "column": (args.beam_column_min_speed, args.beam_column_max_speed),
        }
        self.speed = random.randint(direction_speed_range[direction][0], direction_speed_range[direction][1]) * 0.1
        self.next_character_counter: float = 0
        if self.direction == "row":
            self.characters.sort(key=lambda character: character.input_coord.column)
        elif self.direction == "column":
            self.characters.sort(key=lambda character: character.input_coord.row)
        if random.choice([True, False]):
            self.characters.reverse()

    def increment_next_character_counter(self) -> None:
        self.next_character_counter += self.speed

    def get_next_character(self) -> EffectCharacter | None:
        self.next_character_counter -= 1
        next_character = self.characters.pop(0)
        if next_character.animation.active_scene:
            next_character.animation.active_scene.reset_scene()
            return_value = None
        else:
            self.terminal.set_character_visibility(next_character, True)
            return_value = next_character
        next_character.animation.activate_scene(next_character.animation.query_scene("beam_" + self.direction))
        return return_value

    def complete(self) -> bool:
        return not self.characters


class BeamsEffect:
    """Effect that creates beams which travel over the output area illuminated the characters behind them."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_groups: list[Group] = []
        self.active_chars: list[EffectCharacter] = []
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

        if (self.args.beam_row_min_speed > self.args.beam_row_max_speed) or (
            self.args.beam_column_min_speed > self.args.beam_column_max_speed
        ):
            raise ValueError("Minimum speed cannot be greater than maximum speed.")

    def prepare_data(self) -> None:  # testing
        final_gradient = graphics.Gradient(self.args.final_gradient_stops, self.args.final_gradient_steps)

        for character in self.terminal.get_characters(fill_chars=True):
            self.character_final_color_map[character] = final_gradient.get_color_at_fraction(
                character.input_coord.row / self.terminal.output_area.top
            )

        beam_gradient = graphics.Gradient(self.args.beam_gradient_stops, steps=self.args.beam_gradient_steps)
        groups: list[Group] = []
        for row in self.terminal.get_characters_grouped(Terminal.CharacterGroup.ROW_TOP_TO_BOTTOM, fill_chars=True):
            groups.append(Group(row, "row", self.terminal, self.args))
        for column in self.terminal.get_characters_grouped(
            Terminal.CharacterGroup.COLUMN_LEFT_TO_RIGHT, fill_chars=True
        ):
            groups.append(Group(column, "column", self.terminal, self.args))
        for group in groups:
            for character in group.characters:
                beam_row_scn = character.animation.new_scene(id="beam_row")
                beam_column_scn = character.animation.new_scene(id="beam_column")
                beam_row_scn.apply_gradient_to_symbols(
                    beam_gradient, self.args.beam_row_symbols, self.args.beam_gradient_frames
                )
                beam_column_scn.apply_gradient_to_symbols(
                    beam_gradient, self.args.beam_column_symbols, self.args.beam_gradient_frames
                )
                faded_color = character.animation.adjust_color_brightness(
                    self.character_final_color_map[character], 0.3
                )
                fade_gradient = graphics.Gradient([self.character_final_color_map[character], faded_color], steps=10)
                beam_row_scn.apply_gradient_to_symbols(fade_gradient, character.input_symbol, 5)
                beam_column_scn.apply_gradient_to_symbols(fade_gradient, character.input_symbol, 5)
                brighten_gradient = graphics.Gradient(
                    [faded_color, self.character_final_color_map[character]], steps=10
                )
                brigthen_scn = character.animation.new_scene(id="brighten")
                brigthen_scn.apply_gradient_to_symbols(
                    brighten_gradient, character.input_symbol, self.args.final_gradient_frames
                )
        self.pending_groups = groups
        random.shuffle(self.pending_groups)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        active_groups: list[Group] = []
        delay = 0
        phase = "beams"
        final_wipe_groups = self.terminal.get_characters_grouped(
            Terminal.CharacterGroup.DIAGONAL_TOP_LEFT_TO_BOTTOM_RIGHT
        )
        while phase != "complete" or self.active_chars:
            if phase == "beams":
                if not delay:
                    if self.pending_groups:
                        for _ in range(random.randint(1, 5)):
                            if self.pending_groups:
                                active_groups.append(self.pending_groups.pop(0))
                    delay = self.args.beam_delay
                else:
                    delay -= 1
                for group in active_groups:
                    group.increment_next_character_counter()
                    if int(group.next_character_counter) > 1:
                        for _ in range(int(group.next_character_counter)):
                            if not group.complete():
                                next_char = group.get_next_character()
                                if next_char:
                                    self.active_chars.append(next_char)
                active_groups = [group for group in active_groups if not group.complete()]
                if not self.pending_groups and not active_groups and not self.active_chars:
                    phase = "final_wipe"
            elif phase == "final_wipe":
                if final_wipe_groups:
                    for _ in range(self.args.final_wipe_speed):
                        if not final_wipe_groups:
                            break
                        next_group = final_wipe_groups.pop(0)
                        for character in next_group:
                            character.animation.activate_scene(character.animation.query_scene("brighten"))
                            self.terminal.set_character_visibility(character, True)
                            self.active_chars.append(character)
                else:
                    phase = "complete"
            self.terminal.print()
            self.animate_chars()

            self.active_chars = [character for character in self.active_chars if character.is_active]
        self.terminal.print()

    def animate_chars(self) -> None:
        """Animates the characters by calling the tick method on all active characters."""
        for character in self.active_chars:
            character.tick()
