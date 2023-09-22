"""Creates a rain effect where characters fall from the top of the terminal."""

import argparse
import random

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects.utils import graphics
from terminaltexteffects import base_character, base_effect
from terminaltexteffects.utils.terminal import Terminal


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "rain",
        formatter_class=argtypes.CustomFormatter,
        help="Rain characters from the top of the output area.",
        description="rain | Rain characters from the top of the output area.",
        epilog=f"""{argtypes.EASING_EPILOG}
        
Example: terminaltexteffects rain -a 0.01 --rain-colors 39 45 51 21""",
    )
    effect_parser.set_defaults(effect_class=RainEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.valid_animationrate,
        default=0.01,
        help="Time, in seconds, between animation steps.",
    )
    effect_parser.add_argument(
        "--rain-colors",
        type=argtypes.valid_color,
        nargs="*",
        default=0,
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="List of colors for the rain drops. Colors are randomly chosen from the list.",
    )
    effect_parser.add_argument(
        "--final-color",
        type=argtypes.valid_color,
        default="ffffff",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the final character.",
    )
    effect_parser.add_argument(
        "--movement-speed",
        type=argtypes.valid_speed,
        default=0.5,
        metavar="(float > 0)",
        help="Falling speed of the rain drops. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )
    effect_parser.add_argument(
        "--easing",
        default="IN_QUART",
        type=argtypes.valid_ease,
        help="Easing function to use for character movement.",
    )


class RainEffect(base_effect.Effect):
    """Creates a rain effect where characters fall from the top of the output area."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        super().__init__(terminal, args)
        self.group_by_row: dict[int, list[base_character.EffectCharacter | None]] = {}

    def prepare_data(self) -> None:
        """Prepares the data for the effect by setting all characters y position to the input height and sorting by target y."""
        if self.args.rain_colors:
            rain_colors = self.args.rain_colors
        else:
            rain_colors = [39, 45, 51, 21, 117, 159]
        rain_characters = ["o", ".", ",", "*", "|"]

        for character in self.terminal.characters:
            raindrop_color = random.choice(rain_colors)
            character.animator.add_effect_to_scene("rain", random.choice(rain_characters), raindrop_color, 1)
            raindrop_gradient = graphics.gradient(raindrop_color, self.args.final_color, 7)
            for color in raindrop_gradient:
                character.animator.add_effect_to_scene("fade", character.input_symbol, color, 5)
            character.animator.activate_scene("rain")
            character.motion.set_coordinate(character.input_coord.column, self.terminal.output_area.top)
            character.motion.new_waypoint(
                "input_coord",
                character.input_coord.column,
                character.input_coord.row,
                speed=self.args.movement_speed,
                ease=self.args.easing,
            )
            character.event_handler.register_event(
                character.event_handler.Event.WAYPOINT_REACHED,
                "input_coord",
                character.event_handler.Action.ACTIVATE_SCENE,
                "fade",
            )
            character.motion.activate_waypoint("input_coord")
            self.pending_chars.append(character)
        for character in sorted(self.pending_chars, key=lambda c: c.input_coord.row):
            if character.input_coord.row not in self.group_by_row:
                self.group_by_row[character.input_coord.row] = []
            self.group_by_row[character.input_coord.row].append(character)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        self.pending_chars.clear()
        self.terminal.print()
        while self.group_by_row or self.animating_chars or self.pending_chars:
            if not self.pending_chars and self.group_by_row:
                self.pending_chars.extend(self.group_by_row.pop(min(self.group_by_row.keys())))  # type: ignore
            if self.pending_chars:
                for _ in range(random.randint(1, 3)):
                    if self.pending_chars:
                        next_character = self.pending_chars.pop(random.randint(0, len(self.pending_chars) - 1))
                        next_character.is_active = True
                        self.animating_chars.append(next_character)

                    else:
                        break
            self.animate_chars()
            # remove completed chars from animating chars
            self.animating_chars = [
                animating_char
                for animating_char in self.animating_chars
                if not animating_char.animator.is_active_scene_complete()
                or not animating_char.motion.movement_complete()
            ]
            self.terminal.print()

    def animate_chars(self) -> None:
        """Animates the characters by calling the move method and getting the next symbol from the animator."""
        for animating_char in self.animating_chars:
            animating_char.animator.step_animation()
            animating_char.motion.move()
