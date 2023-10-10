import argparse

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects import base_effect
from terminaltexteffects.utils.terminal import Terminal
from terminaltexteffects.utils import graphics, argtypes


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "middleout",
        formatter_class=argtypes.CustomFormatter,
        help="Text expands in a single row or column in the middle of the output area then out.",
        description="Text expands in a single row or column in the middle of the output area then out.",
        epilog=f"""{argtypes.EASING_EPILOG}

Example: terminaltexteffects middleout -a 0.01 --expand-direction horizontal --center-movement-speed 0.35 
         --full-movement-speed 0.35 --center-easing IN_OUT_SINE --full-easing IN_OUT_SINE 
         --center-expand-color 00ff00 --full-expand-color 0000ff --starting-color ff0000""",
    )
    effect_parser.set_defaults(effect_class=MiddleoutEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.valid_animationrate,
        default=0.01,
        help="Time, in seconds, between animation steps.",
    )
    effect_parser.add_argument(
        "--starting-color",
        type=argtypes.valid_color,
        default="ffffff",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the initial text in the center of the output area.",
    )
    effect_parser.add_argument(
        "--center-expand-color",
        type=argtypes.valid_color,
        default="ffffff",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the row or column as it expands.",
    )
    effect_parser.add_argument(
        "--full-expand-color",
        type=argtypes.valid_color,
        default="ffffff",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the full text as it expands.",
    )
    effect_parser.add_argument(
        "--expand-direction",
        default="vertical",
        choices=["vertical", "horizontal"],
        help="Direction the text will expand.",
    )
    effect_parser.add_argument(
        "--center-movement-speed",
        type=argtypes.valid_speed,
        default=0.35,
        metavar="(float > 0)",
        help="Speed of the characters during the initial expansion of the center vertical/horiztonal line. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )
    effect_parser.add_argument(
        "--full-movement-speed",
        type=argtypes.valid_speed,
        default=0.35,
        metavar="(float > 0)",
        help="Speed of the characters during the final full expansion. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )
    effect_parser.add_argument(
        "--center-easing",
        default="IN_OUT_SINE",
        type=argtypes.valid_ease,
        help="Easing function to use for initial expansion.",
    )
    effect_parser.add_argument(
        "--full-easing",
        default="IN_OUT_SINE",
        type=argtypes.valid_ease,
        help="Easing function to use for full expansion.",
    )


class MiddleoutEffect(base_effect.Effect):
    """Effect that ___."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        super().__init__(terminal, args)
        self.center_gradient = graphics.Gradient(self.args.starting_color, self.args.center_expand_color, 10)
        self.full_gradient = graphics.Gradient(self.args.center_expand_color, self.args.full_expand_color, 10)

    def prepare_data(self) -> None:
        """Prepares the data for the effect."""
        for character in self.terminal.characters:
            character.motion.set_coordinate(
                self.terminal.output_area.center_column, self.terminal.output_area.center_row
            )
            # setup scenes
            for step in self.center_gradient:
                character.animation.add_effect_to_scene("center", character.input_symbol, step, 2)
            for step in self.full_gradient:
                character.animation.add_effect_to_scene("full", character.input_symbol, step, 2)
            character.animation.scenes["full"].waypoint_sync_id = "full"
            character.animation.activate_scene("center")

            # setup waypoints
            if self.args.expand_direction == "vertical":
                column = character.input_coord.column
                row = self.terminal.output_area.center_row
            else:
                column = self.terminal.output_area.center_column
                row = character.input_coord.row
            character.motion.new_waypoint(
                "center",
                column,
                row,
                speed=self.args.center_movement_speed,
                ease=self.args.center_easing,
            )
            character.motion.new_waypoint(
                "full",
                character.input_coord.column,
                character.input_coord.row,
                speed=self.args.full_movement_speed,
                ease=self.args.full_easing,
            )
            # initialize character state
            character.motion.activate_waypoint("center")
            character.animation.activate_scene("center")
            character.is_active = True
            self.animating_chars.append(character)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        final = False
        while self.pending_chars or self.animating_chars:
            if all([character.motion.active_waypoint == None for character in self.animating_chars]):
                final = True
                for character in self.animating_chars:
                    character.motion.activate_waypoint("full")
                    character.animation.activate_scene("full")
            self.terminal.print()
            self.animate_chars()
            if final:
                self.animating_chars = [
                    animating_char
                    for animating_char in self.animating_chars
                    if not animating_char.animation.active_scene_is_complete()
                    or not animating_char.motion.movement_is_complete()
                ]

    def animate_chars(self) -> None:
        """Animates the characters by calling the move method and step animation."""
        for animating_char in self.animating_chars:
            animating_char.motion.move()
            animating_char.animation.step_animation()
