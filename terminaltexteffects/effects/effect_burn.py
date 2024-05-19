"""Characters are ignited and burn up the screen.

Classes:
    Burn: Characters are ignited and burn up the screen.
    BurnConfig: Configuration for the Burn effect.
    BurnIterator: Iterates over the Burn effect. Does not normally need to be called directly.

"""

import random
import typing
from dataclasses import dataclass

import terminaltexteffects.utils.argvalidators as argvalidators
from terminaltexteffects.engine.base_character import EffectCharacter, EventHandler
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.graphics import Color, Gradient


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return Burn, BurnConfig


@argclass(
    name="burn",
    help="Burns vertically in the canvas.",
    description="burn | Burn the canvas.",
    epilog="Example: terminaltexteffects burn --starting-color 837373 --burn-colors ffffff fff75d fe650d 8a003c 510100 --final-gradient-stops 00c3ff ffff1c --final-gradient-steps 12",
)
@dataclass
class BurnConfig(ArgsDataClass):
    """Configuration for the Burn effect.

    Attributes:
        starting_color (Color): Color of the characters before they start to burn.
        burn_colors (tuple[Color, ...]): Colors transitioned through as the characters burn.
        final_gradient_stops (tuple[Color, ...]): Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient."""

    starting_color: Color = ArgField(
        cmd_name="--starting-color",
        type_parser=argvalidators.ColorArg.type_parser,
        default=Color("837373"),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Color of the characters before they start to burn.",
    )  # type: ignore[assignment]
    "Color : Color of the characters before they start to burn."

    burn_colors: tuple[Color, ...] = ArgField(
        cmd_name=["--burn-colors"],
        type_parser=argvalidators.ColorArg.type_parser,
        default=(Color("ffffff"), Color("fff75d"), Color("fe650d"), Color("8A003C"), Color("510100")),
        nargs="+",
        metavar=argvalidators.ColorArg.METAVAR,
        help="Colors transitioned through as the characters burn.",
    )  # type: ignore[assignment]
    "tuple[Color, ...] : Colors transitioned through as the characters burn."

    final_gradient_stops: tuple[Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(Color("00c3ff"), Color("ffff1c")),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] | int = ArgField(
        cmd_name=["--final-gradient-steps"],
        type_parser=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=12,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] | int : Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_direction: Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=argvalidators.GradientDirection.type_parser,
        default=Gradient.Direction.VERTICAL,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]
    "Gradient.Direction : Direction of the final gradient."

    @classmethod
    def get_effect_class(cls):
        return Burn


class BurnIterator(BaseEffectIterator[BurnConfig]):
    def __init__(self, effect: "Burn"):
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self.build()

    def build(self) -> None:
        vertical_build_order = [
            "'",
            ".",
            "▖",
            "▙",
            "█",
            "▜",
            "▀",
            "▝",
            ".",
        ]
        final_gradient = Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.config.final_gradient_direction
        )
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]
        fire_gradient = Gradient(*self.config.burn_colors, steps=10)
        groups = {
            column_index: column
            for column_index, column in enumerate(
                self.terminal.get_characters_grouped(grouping=self.terminal.CharacterGroup.COLUMN_LEFT_TO_RIGHT)
            )
        }

        def groups_remaining(rows) -> bool:
            return any(row for row in rows.values())

        while groups_remaining(groups):
            keys = [key for key in groups.keys() if groups[key]]
            next_char = groups[random.choice(keys)].pop(0)
            self.terminal.set_character_visibility(next_char, True)
            next_char.animation.set_appearance(next_char.input_symbol, color=self.config.starting_color)
            burn_scn = next_char.animation.new_scene(id="burn")
            burn_scn.apply_gradient_to_symbols(fire_gradient, vertical_build_order, 12)
            final_color_scn = next_char.animation.new_scene()
            for color in Gradient(fire_gradient.spectrum[-1], self.character_final_color_map[next_char], steps=8):
                final_color_scn.add_frame(next_char.input_symbol, 4, color=color)
            next_char.event_handler.register_event(
                EventHandler.Event.SCENE_COMPLETE, burn_scn, EventHandler.Action.ACTIVATE_SCENE, final_color_scn
            )

            self.pending_chars.append(next_char)

    def __next__(self) -> str:
        if self.pending_chars or self.active_characters:
            for _ in range(random.randint(2, 4)):
                if self.pending_chars:
                    next_char = self.pending_chars.pop(0)
                    next_char.animation.activate_scene(next_char.animation.query_scene("burn"))
                    self.active_characters.append(next_char)

            self.update()
            return self.frame
        else:
            raise StopIteration


class Burn(BaseEffect[BurnConfig]):
    """Characters are ignited and burn up the screen.

    Attributes:
        effect_config (BurnConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.
    """

    _config_cls = BurnConfig
    _iterator_cls = BurnIterator

    def __init__(self, input_data: str) -> None:
        """Initialize the effect with the provided input data.

        Args:
            input_data (str): The input data to use for the effect."""
        super().__init__(input_data)
