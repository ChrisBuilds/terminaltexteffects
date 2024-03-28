import typing
from dataclasses import dataclass

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils import easing, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.terminal import Terminal


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return WavesEffect, WavesEffectArgs


@argclass(
    name="waves",
    formatter_class=arg_validators.CustomFormatter,
    help="Waves travel across the terminal leaving behind the characters.",
    description="waves | Waves travel across the terminal leaving behind the characters.",
    epilog=f"""{arg_validators.EASING_EPILOG}
Example: terminaltexteffects waves --wave-symbols ▁ ▂ ▃ ▄ ▅ ▆ ▇ █ ▇ ▆ ▅ ▄ ▃ ▂ ▁ --wave-gradient-stops f0ff65 ffb102 31a0d4 ffb102 f0ff65 --wave-gradient-steps 6 --final-gradient-stops ffb102 31a0d4 f0ff65 --final-gradient-steps 12 --wave-count 7 --wave-length 2 --wave-easing IN_OUT_SINE""",
)
@dataclass
class WavesEffectArgs(ArgsDataClass):
    wave_symbols: tuple[str, ...] = ArgField(
        cmd_name="--wave-symbols",
        type_parser=arg_validators.Symbol.type_parser,
        default=("▁", "▂", "▃", "▄", "▅", "▆", "▇", "█", "▇", "▆", "▅", "▄", "▃", "▂", "▁"),
        nargs="+",
        metavar=arg_validators.Symbol.METAVAR,
        help="Symbols to use for the wave animation. Multi-character strings will be used in sequence to create an animation.",
    )  # type: ignore[assignment]
    wave_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name="--wave-gradient-stops",
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("f0ff65", "ffb102", "31a0d4", "ffb102", "f0ff65"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    wave_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--wave-gradient-steps",
        type_parser=arg_validators.PositiveInt.type_parser,
        nargs="+",
        default=(6,),
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name="--final-gradient-stops",
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("ffb102", "31a0d4", "f0ff65"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--final-gradient-steps",
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
    wave_count: int = ArgField(
        cmd_name="--wave-count",
        type_parser=arg_validators.PositiveInt.type_parser,
        default=7,
        help="Number of waves to generate. n > 0.",
    )  # type: ignore[assignment]
    wave_length: int = ArgField(
        cmd_name="--wave-length",
        type_parser=arg_validators.PositiveInt.type_parser,
        default=2,
        metavar=arg_validators.PositiveInt.METAVAR,
        help="The number of frames for each step of the wave. Higher wave-lengths will create a slower wave.",
    )  # type: ignore[assignment]
    wave_easing: easing.EasingFunction = ArgField(
        cmd_name="--wave-easing",
        type_parser=arg_validators.Ease.type_parser,
        default=easing.in_out_sine,
        help="Easing function to use for wave travel.",
    )  # type: ignore[assignment]

    @classmethod
    def get_effect_class(cls):
        return WavesEffect


class WavesEffect:
    """Effect that creates waves that travel across the terminal, leaving behind the characters."""

    def __init__(self, terminal: Terminal, args: WavesEffectArgs):
        self.terminal = terminal
        self.args = args
        self.pending_columns: list[list[EffectCharacter]] = []
        self.active_chars: list[EffectCharacter] = []
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def prepare_data(self) -> None:
        """Prepares the data for the effect by creating the wave animations."""
        final_gradient = graphics.Gradient(*self.args.final_gradient_stops, steps=self.args.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.args.final_gradient_direction
        )
        wave_gradient = graphics.Gradient(*self.args.wave_gradient_stops, steps=self.args.wave_gradient_steps)
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]
            wave_scn = character.animation.new_scene()
            wave_scn.ease = self.args.wave_easing
            for _ in range(self.args.wave_count):
                wave_scn.apply_gradient_to_symbols(
                    wave_gradient, self.args.wave_symbols, duration=self.args.wave_length
                )
            final_scn = character.animation.new_scene()
            for step in graphics.Gradient(
                wave_gradient.spectrum[-1],
                self.character_final_color_map[character],
                steps=self.args.final_gradient_steps,
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
