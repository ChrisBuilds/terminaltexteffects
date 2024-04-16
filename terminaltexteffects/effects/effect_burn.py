import random
import typing
from collections.abc import Iterator
from dataclasses import dataclass

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.base_effect import BaseEffect
from terminaltexteffects.utils import graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.terminal import Terminal, TerminalConfig


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return BurnEffect, EffectConfig


@argclass(
    name="burn",
    help="Burns vertically in the output area.",
    description="burn | Burn the output area.",
    epilog="Example: terminaltexteffects burn --starting-color 837373 --burn-colors ffffff fff75d fe650d 8a003c 510100 --final-gradient-stops 00c3ff ffff1c --final-gradient-steps 12",
)
@dataclass
class EffectConfig(ArgsDataClass):
    """Configuration for the Burn effect.

    Attributes:
        starting_color (graphics.Color): Color of the characters before they start to burn.
        burn_colors (tuple[graphics.Color, ...]): Colors transitioned through as the characters burn.
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the gradient for the final color."""

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
    "tuple[graphics.Color, ...] : Tuple of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color."

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
        help="Direction of the gradient for the final color.",
    )  # type: ignore[assignment]
    "graphics.Gradient.Direction : Direction of the gradient for the final color."

    @classmethod
    def get_effect_class(cls):
        return BurnEffect


class BurnEffect(BaseEffect):
    """Effect that burns up the screen."""

    def __init__(
        self,
        input_data: str,
        effect_config: EffectConfig = EffectConfig(),
        terminal_config: TerminalConfig = TerminalConfig(),
    ):
        """Initializes the effect.

        Args:
            input_data (str): The input data to apply the effect to.
            effect_config (EffectConfig): The configuration for the effect.
            terminal_config (TerminalConfig): The configuration for the terminal.
        """
        self.terminal = Terminal(input_data, terminal_config)
        self.config = effect_config
        self._built = False
        self._pending_chars: list[EffectCharacter] = []
        self._active_chars: list[EffectCharacter] = []
        self._character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def build(self) -> None:
        """Prepares the data for the effect by building the burn animation and organizing the data into columns."""
        self._pending_chars.clear()
        self._active_chars.clear()
        self._character_final_color_map.clear()
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
        final_gradient = graphics.Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.config.final_gradient_direction
        )
        for character in self.terminal.get_characters():
            self._character_final_color_map[character] = final_gradient_mapping[character.input_coord]
        fire_gradient = graphics.Gradient(*self.config.burn_colors, steps=10)
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
            for color in graphics.Gradient(
                fire_gradient.spectrum[-1], self._character_final_color_map[next_char], steps=8
            ):
                final_color_scn.add_frame(next_char.input_symbol, 4, color=color)
            next_char.event_handler.register_event(
                EventHandler.Event.SCENE_COMPLETE, burn_scn, EventHandler.Action.ACTIVATE_SCENE, final_color_scn
            )

            self._pending_chars.append(next_char)
        self._built = True

    @property
    def built(self) -> bool:
        """Returns True if the effect has been built."""
        return self._built

    def __iter__(self) -> Iterator[str]:
        """Runs the effect."""
        if not self._built:
            self.build()
        while self._pending_chars or self._active_chars:
            for _ in range(random.randint(2, 4)):
                if self._pending_chars:
                    next_char = self._pending_chars.pop(0)
                    next_char.animation.activate_scene(next_char.animation.query_scene("burn"))
                    # self.terminal.set_character_visibility(next_char, True)
                    self._active_chars.append(next_char)

            self._animate_chars()

            self._active_chars = [character for character in self._active_chars if character.is_active]
            yield self.terminal.get_formatted_output_string()
        self._built = False

    def _animate_chars(self) -> None:
        """Animates the characters by calling the tick method."""
        for character in self._active_chars:
            character.animation.step_animation()
