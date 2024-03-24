import random
import typing
from dataclasses import dataclass

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils import easing, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.terminal import Terminal


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return UnstableEffect, UnstableEffectArgs


@argclass(
    name="unstable",
    formatter_class=arg_validators.CustomFormatter,
    help="Spawn characters jumbled, explode them to the edge of the output area, then reassemble them in the correct layout.",
    description="unstable | Spawn characters jumbled, explode them to the edge of the output area, then reassemble them in the correct layout.",
    epilog=f"""{arg_validators.EASING_EPILOG}
    
    Example: terminaltexteffects unstable --unstable-color ff9200 --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --explosion-ease OUT_EXPO --explosion-speed 0.75 --reassembly-ease OUT_EXPO --reassembly-speed 0.75""",
)
@dataclass
class UnstableEffectArgs(ArgsDataClass):
    unstable_color: graphics.Color = ArgField(
        cmd_name=["--unstable-color"],
        type_parser=arg_validators.Color.type_parser,
        default="ff9200",
        metavar=arg_validators.Color.METAVAR,
        help="Color transitioned to as the characters become unstable.",
    )  # type: ignore[assignment]
    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("8A008A", "00D1FF", "FFFFFF"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name=["--final-gradient-steps"],
        type_parser=arg_validators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=arg_validators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.VERTICAL,
        metavar=arg_validators.GradientDirection.METAVAR,
        help="Direction of the gradient for the final color.",
    )  # type: ignore[assignment]
    explosion_ease: easing.EasingFunction = ArgField(
        cmd_name=["--explosion-ease"],
        type_parser=arg_validators.Ease.type_parser,
        default=easing.out_expo,
        help="Easing function to use for character movement during the explosion.",
    )  # type: ignore[assignment]
    explosion_speed: float = ArgField(
        cmd_name=["--explosion-speed"],
        type_parser=arg_validators.PositiveFloat.type_parser,
        default=0.75,
        metavar=arg_validators.PositiveFloat.METAVAR,
        help="Speed of characters during explosion. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )  # type: ignore[assignment]
    reassembly_ease: easing.EasingFunction = ArgField(
        cmd_name=["--reassembly-ease"],
        type_parser=arg_validators.Ease.type_parser,
        default=easing.out_expo,
        help="Easing function to use for character reassembly.",
    )  # type: ignore[assignment]
    reassembly_speed: float = ArgField(
        cmd_name=["--reassembly-speed"],
        type_parser=arg_validators.PositiveFloat.type_parser,
        default=0.75,
        metavar=arg_validators.PositiveFloat.METAVAR,
        help="Speed of characters during reassembly. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )  # type: ignore[assignment]

    @classmethod
    def get_effect_class(cls):
        return UnstableEffect


class UnstableEffect:
    """Effect that spawns characters jumbled, explodes them to the edge of the output area,
    then reassembles them in the correct layout."""

    def __init__(self, terminal: Terminal, args: UnstableEffectArgs):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.jumbled_coords: dict[EffectCharacter, Coord] = dict()
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def prepare_data(self) -> None:
        """Prepares the data for the effect by jumbling the character positions and
        choosing a location on the perimeter of the output area for the character to travel
        after exploding. Creates all waypoints and scenes for the characters."""
        final_gradient = graphics.Gradient(*self.args.final_gradient_stops, steps=self.args.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.args.final_gradient_direction
        )
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]
        character_coords = [character.input_coord for character in self.terminal.get_characters()]
        for character in self.terminal.get_characters():
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
            character.motion.set_coordinate(jumbled_coord)
            explosion_path = character.motion.new_path(id="explosion", speed=1.25, ease=self.args.explosion_ease)
            explosion_path.new_waypoint(Coord(col, row))
            reassembly_path = character.motion.new_path(id="reassembly", speed=0.75, ease=self.args.reassembly_ease)
            reassembly_path.new_waypoint(character.input_coord)
            unstable_gradient = graphics.Gradient(
                self.character_final_color_map[character], self.args.unstable_color, steps=25
            )
            rumble_scn = character.animation.new_scene(id="rumble")
            rumble_scn.apply_gradient_to_symbols(
                unstable_gradient,
                character.input_symbol,
                10,
            )
            final_color = graphics.Gradient(
                self.args.unstable_color, self.character_final_color_map[character], steps=12
            )
            final_scn = character.animation.new_scene(id="final")
            final_scn.apply_gradient_to_symbols(final_color, character.input_symbol, 5)
            character.animation.activate_scene(rumble_scn)
            self.terminal.set_character_visibility(character, True)

    def move_all_to_waypoint(self, path_id) -> None:
        for character in self.terminal.get_characters():
            if path_id == "reassembly":
                character.animation.activate_scene(character.animation.query_scene("final"))
            self.active_chars.append(character)
            character.motion.activate_path(character.motion.query_path(path_id))
        while self.active_chars:
            self.terminal.print()
            self.animate_chars()
            if path_id == "reassembly":
                self.active_chars = [
                    character
                    for character in self.active_chars
                    if not character.motion.current_coord == character.motion.query_path(path_id).waypoints[0].coord
                    or not character.animation.active_scene_is_complete()
                ]
            else:
                self.active_chars = [
                    character
                    for character in self.active_chars
                    if not character.motion.current_coord == character.motion.query_path(path_id).waypoints[0].coord
                ]

    def rumble(self) -> None:
        max_rumble_steps = 250
        current_rumble_steps = 0
        rumble_mod_delay = 20
        while current_rumble_steps < max_rumble_steps:
            if current_rumble_steps > 30 and current_rumble_steps % rumble_mod_delay == 0:
                row_offset = random.choice([-1, 0, 1])
                column_offset = random.choice([-1, 0, 1])
                for character in self.terminal.get_characters():
                    character.motion.set_coordinate(
                        Coord(
                            character.motion.current_coord.column + column_offset,
                            character.motion.current_coord.row + row_offset,
                        )
                    )
                    character.animation.step_animation()
                self.terminal.print()
                for character in self.terminal.get_characters():
                    character.motion.set_coordinate(self.jumbled_coords[character])
                rumble_mod_delay -= 1
                rumble_mod_delay = max(rumble_mod_delay, 1)
            else:
                for character in self.terminal.get_characters():
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
        """Animates the characters by calling the tick method."""
        for character in self.active_chars:
            character.tick()
