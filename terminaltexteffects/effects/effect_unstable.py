import argparse
import random

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects import base_character, base_effect
from terminaltexteffects.utils.terminal import Terminal
from terminaltexteffects.utils import graphics, argtypes


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "unstable",
        formatter_class=argtypes.CustomFormatter,
        help="Spawn characters jumbled, explode them to the edge of the output area, then reassemble them in the correct layout.",
        description="unstable | Spawn characters jumbled, explode them to the edge of the output area, then reassemble them in the correct layout.",
        epilog=f"""{argtypes.EASING_EPILOG}

Example: terminaltexteffects unstable -a 0.01 --initial-color ffffff --unstable-color ff9200 --final-color ffffff --explosion-ease OUT_EXPO --explosion-speed 0.75 --reassembly-ease OUT_EXPO --reassembly-speed 0.75""",
    )
    effect_parser.set_defaults(effect_class=UnstableEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.valid_animationrate,
        default=0.01,
        help="Time, in seconds, between animation steps.",
    )
    effect_parser.add_argument(
        "--initial-color",
        type=argtypes.valid_color,
        default="ffffff",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the characters when the effect starts.",
    )
    effect_parser.add_argument(
        "--unstable-color",
        type=argtypes.valid_color,
        default="ff9200",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color transitioned to as the characters become unstable.",
    )
    effect_parser.add_argument(
        "--final-color",
        type=argtypes.valid_color,
        default="ffffff",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color transitioned to as the characters reassemble.",
    )
    effect_parser.add_argument(
        "--explosion-ease",
        default="OUT_EXPO",
        type=argtypes.valid_ease,
        help="Easing function to use for character movement during the explosion.",
    )
    effect_parser.add_argument(
        "--explosion-speed",
        type=argtypes.valid_speed,
        default=0.75,
        metavar="(float > 0)",
        help="Speed of characters during explosion. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )
    effect_parser.add_argument(
        "--reassembly-ease",
        default="OUT_EXPO",
        type=argtypes.valid_ease,
        help="Easing function to use for character reassembly.",
    )
    effect_parser.add_argument(
        "--reassembly-speed",
        type=argtypes.valid_speed,
        default=0.75,
        metavar="(float > 0)",
        help="Speed of characters during reassembly. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )


class UnstableEffect(base_effect.Effect):
    """Effect that spawns characters jumbled, explodes them to the edge of the output area,
    then reassembles them in the correct layout."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        super().__init__(terminal, args)
        self.jumbled_coords: dict[base_character.EffectCharacter, base_character.motion.Coord] = dict()

    def prepare_data(self) -> None:
        """Prepares the data for the effect by jumbling the character positions and
        choosing a location on the perimeter of the output area for the character to travel
        after exploding. Creates all waypoints and scenes for the characters."""
        character_coords = [character.input_coord for character in self.terminal.characters]
        for character in self.terminal.characters:
            pos = random.randint(0, 3)
            match pos:
                case 0:
                    col = self.terminal.output_area.left
                    row = random.randint(1, self.terminal.output_area.top)
                case 1:
                    col = self.terminal.output_area.right
                    row = random.randint(1, self.terminal.output_area.top)
                case 2:
                    col = random.randint(1, self.terminal.output_area.right)
                    row = self.terminal.output_area.bottom
                case 3:
                    col = random.randint(1, self.terminal.output_area.right)
                    row = self.terminal.output_area.top
            jumbled_coord = character_coords.pop(random.randint(0, len(character_coords) - 1))
            self.jumbled_coords[character] = jumbled_coord
            character.motion.set_coordinate(jumbled_coord.column, jumbled_coord.row)
            character.motion.new_waypoint("explosion", col, row, speed=0.75, ease=self.args.explosion_ease)
            character.motion.new_waypoint(
                "reassembly",
                character.input_coord.column,
                character.input_coord.row,
                speed=0.75,
                ease=self.args.reassembly_ease,
            )
            unstable_gradient = graphics.gradient(self.args.initial_color, self.args.unstable_color, 25)
            for step in unstable_gradient:
                character.animation.add_effect_to_scene("rumble", character.input_symbol, step, 10)
            final_color = graphics.gradient(self.args.unstable_color, self.args.final_color, 12)
            for step in final_color:
                character.animation.add_effect_to_scene("final", character.input_symbol, step, 5)
            character.animation.activate_scene("rumble")
            character.is_active = True

    def move_all_to_waypoint(self, waypoint_id) -> None:
        for character in self.terminal.characters:
            if waypoint_id == "reassembly":
                character.animation.activate_scene("final")
            self.animating_chars.append(character)
            character.motion.activate_waypoint(waypoint_id)
        while self.animating_chars:
            self.terminal.print()
            self.animate_chars()
            if waypoint_id == "reassembly":
                self.animating_chars = [
                    animating_char
                    for animating_char in self.animating_chars
                    if not animating_char.motion.current_coord == animating_char.motion.waypoints[waypoint_id].coord
                    or not animating_char.animation.active_scene_is_complete()
                ]
            else:
                self.animating_chars = [
                    animating_char
                    for animating_char in self.animating_chars
                    if not animating_char.motion.current_coord == animating_char.motion.waypoints[waypoint_id].coord
                ]

    def rumble(self) -> None:
        max_rumble_steps = 250
        current_rumble_steps = 0
        rumble_mod_delay = 20
        while current_rumble_steps < max_rumble_steps:
            if current_rumble_steps > 30 and current_rumble_steps % rumble_mod_delay == 0:
                row_offset = random.choice([-1, 0, 1])
                column_offset = random.choice([-1, 0, 1])
                for character in self.terminal.characters:
                    character.motion.set_coordinate(
                        character.motion.current_coord.column + column_offset,
                        character.motion.current_coord.row + row_offset,
                    )
                    character.animation.step_animation()
                self.terminal.print()
                for character in self.terminal.characters:
                    character.motion.set_coordinate(
                        self.jumbled_coords[character].column, self.jumbled_coords[character].row
                    )
                rumble_mod_delay -= 1
                rumble_mod_delay = max(rumble_mod_delay, 1)
            else:
                for character in self.terminal.characters:
                    character.animation.step_animation()
                self.terminal.print()

            current_rumble_steps += 1

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        explosion_hold_time = 50
        self.rumble()
        self.move_all_to_waypoint("explosion")
        while explosion_hold_time:
            self.terminal.print()
            self.animate_chars()
            explosion_hold_time -= 1
        self.move_all_to_waypoint("reassembly")

    def animate_chars(self) -> None:
        """Animates the characters by calling the move method and step animation."""
        for animating_char in self.animating_chars:
            animating_char.animation.step_animation()
            animating_char.motion.move()
