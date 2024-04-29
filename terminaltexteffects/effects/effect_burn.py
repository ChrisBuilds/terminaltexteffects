"""Characters are ignited and burn up the screen.

Classes:
    Burn: Characters are ignited and burn up the screen.
    BurnConfig: Configuration for the Burn effect.
    BurnIterator: Iterates over the Burn effect. Does not normally need to be called directly.

"""

import random
import typing
from dataclasses import dataclass

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return Burn, BurnConfig


@argclass(
    name="burn",
    help="Burns vertically in the output area.",
    description="burn | Burn the output area.",
    epilog="Example: terminaltexteffects burn --starting-color 837373 --burn-colors ffffff fff75d fe650d 8a003c 510100 --final-gradient-stops 00c3ff ffff1c --final-gradient-steps 12",
)
@dataclass
class BurnConfig(ArgsDataClass):
    """Configuration for the Burn effect.

    Attributes:
        starting_color (graphics.Color): Color of the characters before they start to burn.
        burn_colors (tuple[graphics.Color, ...]): Colors transitioned through as the characters burn.
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the final gradient."""

    starting_color: graphics.Color = ArgField(
        cmd_name="--starting-color",
        type_parser=arg_validators.Color.type_parser,
        default="837373",
        metavar=arg_validators.Color.METAVAR,
        help="Color of the characters before they start to burn.",
    )  # type: ignore[assignment]
    "graphics.Color : Color of the characters before they start to burn."

    burn_colors: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--burn-colors"],
        type_parser=arg_validators.Color.type_parser,
        default=("ffffff", "fff75d", "fe650d", "8A003C", "510100"),
        nargs="+",
        metavar=arg_validators.Color.METAVAR,
        help="Colors transitioned through as the characters burn.",
    )  # type: ignore[assignment]
    "tuple[graphics.Color, ...] : Colors transitioned through as the characters burn."

    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("00c3ff", "ffff1c"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[graphics.Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name=["--final-gradient-steps"],
        type_parser=arg_validators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] : Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=arg_validators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.VERTICAL,
        metavar=arg_validators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]
    "graphics.Gradient.Direction : Direction of the final gradient."

    @classmethod
    def get_effect_class(cls):
        return Burn


class BurnIterator(BaseEffectIterator[BurnConfig]):
    def __init__(self, effect: "Burn"):
        super().__init__(effect)
        self._pending_chars: list[EffectCharacter] = []
        self._active_chars: list[EffectCharacter] = []
        self._character_final_color_map: dict[EffectCharacter, graphics.Color] = {}
        self._build()

    def _build(self) -> None:
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
        final_gradient = graphics.Gradient(*self._config.final_gradient_stops, steps=self._config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self._terminal.output_area.top, self._terminal.output_area.right, self._config.final_gradient_direction
        )
        for character in self._terminal.get_characters():
            self._character_final_color_map[character] = final_gradient_mapping[character.input_coord]
        fire_gradient = graphics.Gradient(*self._config.burn_colors, steps=10)
        groups = {
            column_index: column
            for column_index, column in enumerate(
                self._terminal.get_characters_grouped(grouping=self._terminal.CharacterGroup.COLUMN_LEFT_TO_RIGHT)
            )
        }

        def groups_remaining(rows) -> bool:
            return any(row for row in rows.values())

        while groups_remaining(groups):
            keys = [key for key in groups.keys() if groups[key]]
            next_char = groups[random.choice(keys)].pop(0)
            self._terminal.set_character_visibility(next_char, True)
            next_char.animation.set_appearance(next_char.input_symbol, color=self._config.starting_color)
            burn_scn = next_char.animation.new_scene(id="burn")
            burn_scn.apply_gradient_to_symbols(fire_gradient, vertical_build_order, 12)
            final_color_scn = next_char.animation.new_scene()
            for color in graphics.Gradient(
                fire_gradient.spectrum[-1], self._character_final_color_map[next_char], steps=8
            ):
                final_color_scn.add_frame(next_char.input_symbol, 4, color=color)
            next_char.event_handler.register_event(
                EventHandler.Event.SCENE_COMPLETE, burn_scn, EventHandler.Action.ACTIVATE_SCENE, final_color_scn
            )

            self._pending_chars.append(next_char)

    def __next__(self) -> str:
        if self._pending_chars or self._active_chars:
            for _ in range(random.randint(2, 4)):
                if self._pending_chars:
                    next_char = self._pending_chars.pop(0)
                    next_char.animation.activate_scene(next_char.animation.query_scene("burn"))
                    # self.terminal.set_character_visibility(next_char, True)
                    self._active_chars.append(next_char)

            for character in self._active_chars:
                character.animation.step_animation()

            self._active_chars = [character for character in self._active_chars if character.is_active]
            return self._terminal.get_formatted_output_string()
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
