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
    return BouncyBallsEffect, BouncyBallsEffectArgs


@argclass(
    name="bouncyballs",
    formatter_class=arg_validators.CustomFormatter,
    help="Characters are bouncy balls falling from the top of the output area.",
    description="bouncyballs | Characters are bouncy balls falling from the top of the output area.",
    epilog=f"""{arg_validators.EASING_EPILOG}
Example: terminaltexteffects bouncyballs --ball-colors d1f4a5 96e2a4 5acda9 --ball-symbols o "*" O 0 . --final-gradient-stops f8ffae 43c6ac --final-gradient-steps 12 --final-gradient-direction diagonal --ball-delay 7 --movement-speed 0.25 --easing OUT_BOUNCE""",
)
@dataclass
class BouncyBallsEffectArgs(ArgsDataClass):
    ball_colors: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--ball-colors"],
        type_parser=arg_validators.Color.type_parser,
        metavar=arg_validators.Color.METAVAR,
        nargs="+",
        default=("d1f4a5", "96e2a4", "5acda9"),
        help="Space separated list of colors from which ball colors will be randomly selected. If no colors are provided, the colors are random.",
    )  # type: ignore[assignment]
    ball_symbols: tuple[str, ...] = ArgField(
        cmd_name="--ball-symbols",
        type_parser=arg_validators.Symbol.type_parser,
        nargs="+",
        default=("*", "o", "O", "0", "."),
        metavar=arg_validators.Symbol.METAVAR,
        help="Space separated list of symbols to use for the balls.",
    )  # type: ignore[assignment]
    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("f8ffae", "43c6ac"),
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
        default=graphics.Gradient.Direction.DIAGONAL,
        metavar=arg_validators.GradientDirection.METAVAR,
        help="Direction of the gradient for the final color.",
    )  # type: ignore[assignment]
    ball_delay: int = ArgField(
        cmd_name="--ball-delay",
        type_parser=arg_validators.NonNegativeInt.type_parser,
        default=7,
        metavar=arg_validators.NonNegativeInt.METAVAR,
        help="Number of animation steps between ball drops, increase to reduce ball drop rate.",
    )  # type: ignore[assignment]
    movement_speed: float = ArgField(
        cmd_name="--movement-speed",
        type_parser=arg_validators.PositiveFloat.type_parser,
        default=0.25,
        metavar=arg_validators.PositiveFloat.METAVAR,
        help="Movement speed of the characters. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )  # type: ignore[assignment]
    easing: typing.Callable = ArgField(
        cmd_name="--easing",
        type_parser=arg_validators.Ease.type_parser,
        default=easing.out_bounce,
        help="Easing function to use for character movement.",
    )  # type: ignore[assignment]

    @classmethod
    def get_effect_class(cls):
        return BouncyBallsEffect


class BouncyBallsEffect:
    """Effect that displays the text as bouncy balls falling from the top of the output area."""

    def __init__(self, terminal: Terminal, args: BouncyBallsEffectArgs):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.group_by_row: dict[int, list[EffectCharacter | None]] = {}
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def prepare_data(self) -> None:
        """Prepares the data for the effect by assigning colors and waypoints and
        organizing the characters by row."""
        final_gradient = graphics.Gradient(*self.args.final_gradient_stops, steps=self.args.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.args.final_gradient_direction
        )
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]
            color = random.choice(self.args.ball_colors)
            symbol = random.choice(self.args.ball_symbols)
            ball_scene = character.animation.new_scene()
            ball_scene.add_frame(symbol, 1, color=color)
            final_scene = character.animation.new_scene()
            char_final_gradient = graphics.Gradient(color, self.character_final_color_map[character], steps=10)
            final_scene.apply_gradient_to_symbols(char_final_gradient, character.input_symbol, 10)
            character.motion.set_coordinate(
                Coord(character.input_coord.column, int(self.terminal.output_area.top * random.uniform(1.0, 1.5)))
            )
            input_coord_path = character.motion.new_path(speed=self.args.movement_speed, ease=self.args.easing)
            input_coord_path.new_waypoint(character.input_coord)
            character.motion.activate_path(input_coord_path)
            character.animation.activate_scene(ball_scene)
            character.event_handler.register_event(
                character.event_handler.Event.PATH_COMPLETE,
                input_coord_path,
                character.event_handler.Action.ACTIVATE_SCENE,
                final_scene,
            )
            self.pending_chars.append(character)
        for character in sorted(self.pending_chars, key=lambda c: c.input_coord.row):
            if character.input_coord.row not in self.group_by_row:
                self.group_by_row[character.input_coord.row] = []
            self.group_by_row[character.input_coord.row].append(character)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        self.pending_chars.clear()
        ball_delay = 0
        while self.group_by_row or self.active_chars or self.pending_chars:
            if not self.pending_chars and self.group_by_row:
                self.pending_chars.extend(self.group_by_row.pop(min(self.group_by_row.keys())))  # type: ignore
            if self.pending_chars:
                if ball_delay == 0:
                    for _ in range(random.randint(2, 6)):
                        if self.pending_chars:
                            next_character = self.pending_chars.pop(random.randint(0, len(self.pending_chars) - 1))
                            self.terminal.set_character_visibility(next_character, True)
                            self.active_chars.append(next_character)
                        else:
                            break
                    ball_delay = self.args.ball_delay
                else:
                    ball_delay -= 1

            self.animate_chars()
            self.active_chars = [character for character in self.active_chars if character.is_active]
            self.terminal.print()

    def animate_chars(self) -> None:
        """Animates the characters by calling the tick method."""
        for character in self.active_chars:
            character.tick()
