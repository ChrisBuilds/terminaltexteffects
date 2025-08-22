"""Characters are ignited and burn up the screen.

Classes:
    Burn: Characters are ignited and burn up the screen.
    BurnConfig: Configuration for the Burn effect.
    BurnIterator: Iterates over the Burn effect. Does not normally need to be called directly.

"""

from __future__ import annotations

import random
from dataclasses import dataclass

from terminaltexteffects import Color, EffectCharacter, EventHandler, Gradient
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.argutils import ArgSpec, ParserSpec
from terminaltexteffects.utils.graphics import ColorPair


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Get the command, effect class, and configuration class for the effect.

    Returns:
        tuple[str, type[BaseEffect], type[BaseConfig]]: The command name, effect class, and configuration class.

    """
    return "burn", Burn, BurnConfig


@dataclass
class BurnConfig(BaseConfig):
    """Configuration for the Burn effect.

    Attributes:
        starting_color (Color): Color of the characters before they start to burn.
        burn_colors (tuple[Color, ...]): Colors transitioned through as the characters burn.
        final_gradient_stops (tuple[Color, ...]): Tuple of colors for the final color gradient. If only one color
            is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Tuple of the number of gradient steps to use. More steps will
            create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient.

    """

    parser_spec: ParserSpec = ParserSpec(
        name="burn",
        help="Burns vertically in the canvas.",
        description="burn | Burn the canvas.",
        epilog=(
            "Example: terminaltexteffects burn --starting-color 837373 --burn-colors ffffff fff75d fe650d 8a003c "
            "510100 --final-gradient-stops 00c3ff ffff1c --final-gradient-steps 12"
        ),
    )

    starting_color: Color = ArgSpec(
        name="--starting-color",
        type=argutils.ColorArg.type_parser,
        default=Color("837373"),
        metavar=argutils.ColorArg.METAVAR,
        help="Color of the characters before they start to burn.",
    )  # pyright: ignore[reportAssignmentType]
    "Color : Color of the characters before they start to burn."

    burn_colors: tuple[Color, ...] = ArgSpec(
        name="--burn-colors",
        type=argutils.ColorArg.type_parser,
        default=(Color("ffffff"), Color("fff75d"), Color("fe650d"), Color("8A003C"), Color("510100")),
        nargs="+",
        metavar=argutils.ColorArg.METAVAR,
        help="Colors transitioned through as the characters burn.",
    )  # pyright: ignore[reportAssignmentType]
    "tuple[Color, ...] : Colors transitioned through as the characters burn."

    final_gradient_stops: tuple[Color, ...] = ArgSpec(
        name="--final-gradient-stops",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        default=(Color("00c3ff"), Color("ffff1c")),
        metavar=argutils.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied across the canvas). "
        "If only one color is provided, the characters will be displayed in that color.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the "
        "characters will be displayed in that color."
    )

    final_gradient_steps: tuple[int, ...] | int = ArgSpec(
        name="--final-gradient-steps",
        type=argutils.PositiveInt.type_parser,
        nargs="+",
        default=12,
        metavar=argutils.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a "
        "smoother and longer gradient animation.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[int, ...] | int : Int or Tuple of ints for the number of gradient steps to use. More steps will "
        "create a smoother and longer gradient animation."
    )

    final_gradient_direction: Gradient.Direction = ArgSpec(
        name="--final-gradient-direction",
        type=argutils.GradientDirection.type_parser,
        default=Gradient.Direction.VERTICAL,
        metavar=argutils.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # pyright: ignore[reportAssignmentType]
    "Gradient.Direction : Direction of the final gradient."


class BurnIterator(BaseEffectIterator[BurnConfig]):
    """Iterator for the Burn effect."""

    def __init__(self, effect: Burn) -> None:
        """Initialize the Burn effect iterator.

        Args:
            effect (Burn): The effect to use for the iterator.

        """
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self.build()

    def build(self) -> None:
        """Build the Burn effect."""
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
            self.terminal.canvas.text_bottom,
            self.terminal.canvas.text_top,
            self.terminal.canvas.text_left,
            self.terminal.canvas.text_right,
            self.config.final_gradient_direction,
        )
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]
        fire_gradient = Gradient(*self.config.burn_colors, steps=10)
        groups = dict(
            enumerate(
                self.terminal.get_characters_grouped(grouping=self.terminal.CharacterGroup.COLUMN_LEFT_TO_RIGHT),
            ),
        )

        def groups_remaining(rows: dict[int, list[EffectCharacter]]) -> bool:
            """Check if there are any groups remaining."""
            return any(row for row in rows.values())

        while groups_remaining(groups):
            keys = [key for key in groups if groups[key]]
            next_char = groups[random.choice(keys)].pop(0)
            self.terminal.set_character_visibility(next_char, is_visible=True)
            next_char.animation.set_appearance(
                next_char.input_symbol,
                colors=ColorPair(fg=self.config.starting_color),
            )
            burn_scn = next_char.animation.new_scene(scene_id="burn")
            burn_scn.apply_gradient_to_symbols(vertical_build_order, 12, fg_gradient=fire_gradient)
            final_color_scn = next_char.animation.new_scene()
            for color in Gradient(fire_gradient.spectrum[-1], self.character_final_color_map[next_char], steps=8):
                final_color_scn.add_frame(next_char.input_symbol, 4, colors=ColorPair(fg=color))
            next_char.event_handler.register_event(
                EventHandler.Event.SCENE_COMPLETE,
                burn_scn,
                EventHandler.Action.ACTIVATE_SCENE,
                final_color_scn,
            )

            self.pending_chars.append(next_char)

    def __next__(self) -> str:
        """Return the next frame in the animation."""
        if self.pending_chars or self.active_characters:
            for _ in range(random.randint(2, 4)):
                if self.pending_chars:
                    next_char = self.pending_chars.pop(0)
                    next_char.animation.activate_scene("burn")
                    self.active_characters.add(next_char)

            self.update()
            return self.frame
        raise StopIteration


class Burn(BaseEffect[BurnConfig]):
    """Characters are ignited and burn up the screen.

    Attributes:
        effect_config (BurnConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.

    """

    @property
    def _config_cls(self) -> type[BurnConfig]:
        return BurnConfig

    @property
    def _iterator_cls(self) -> type[BurnIterator]:
        return BurnIterator
