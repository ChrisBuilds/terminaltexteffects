"""Rain characters from the top of the canvas.

Classes:
    Rain: Rain characters from the top of the canvas.
    RainConfig: Configuration for the Rain effect.
    RainIterator: Iterator for the Rain effect. Does not normally need to be called directly.

"""

from __future__ import annotations

import random
import typing
from dataclasses import dataclass

from terminaltexteffects import Color, ColorPair, Coord, EffectCharacter, Gradient, easing
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argvalidators
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    """Get the effect class and its configuration class."""
    return Rain, RainConfig


@argclass(
    name="rain",
    help="Rain characters from the top of the canvas.",
    description="rain | Rain characters from the top of the canvas.",
    epilog=(
        f"{argvalidators.EASING_EPILOG} Example: terminaltexteffects rain --rain-symbols o . , '*' '|' "
        "--rain-colors 00315C 004C8F 0075DB 3F91D9 78B9F2 9AC8F5 B8D8F8 E3EFFC --final-gradient-stops "
        "488bff b2e7de 57eaf7 --final-gradient-steps 12 --movement-speed 0.1-0.2 --easing IN_QUART"
    ),
)
@dataclass
class RainConfig(ArgsDataClass):
    """Configuration for the Rain effect.

    Attributes:
        rain_colors (tuple[Color, ...]): Tuple of colors for the rain drops. Colors are randomly chosen from the tuple.
        movement_speed (tuple[float, float]): Falling speed range of the rain drops. Valid values are n > 0.
        rain_symbols (tuple[str, ...] | str): Tuple of symbols to use for the rain drops. Symbols are randomly chosen "
            "from the tuple.
        final_gradient_stops (tuple[Color, ...]): Tuple of colors for the final color gradient. If only one color is "
            "provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Tuple of the number of gradient steps to use. More steps will "
            "create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient.
        movement_easing (easing.EasingFunction): Easing function to use for character movement.

    """

    rain_colors: tuple[Color, ...] = ArgField(
        cmd_name=["--rain-colors"],
        type_parser=argvalidators.ColorArg.type_parser,
        metavar=argvalidators.ColorArg.METAVAR,
        nargs="+",
        default=(
            Color("00315C"),
            Color("004C8F"),
            Color("0075DB"),
            Color("3F91D9"),
            Color("78B9F2"),
            Color("9AC8F5"),
            Color("B8D8F8"),
            Color("E3EFFC"),
        ),
        help="List of colors for the rain drops. Colors are randomly chosen from the list.",
    )  # type: ignore[assignment]
    "tuple[Color, ...] : Tuple of colors for the rain drops. Colors are randomly chosen from the tuple."

    movement_speed: tuple[float, float] = ArgField(
        cmd_name="--movement-speed",
        type_parser=argvalidators.PositiveFloatRange.type_parser,
        default=(0.1, 0.2),
        metavar=argvalidators.PositiveFloatRange.METAVAR,
        help="Falling speed range of the rain drops.",
    )  # type: ignore[assignment]
    "tuple[float, float] : Falling speed range of the rain drops."

    rain_symbols: tuple[str, ...] = ArgField(
        cmd_name="--rain-symbols",
        type_parser=argvalidators.Symbol.type_parser,
        nargs="+",
        default=("o", ".", ",", "*", "|"),
        metavar=argvalidators.Symbol.METAVAR,
        help="Space separated list of symbols to use for the rain drops. Symbols are randomly chosen from the list.",
    )  # type: ignore[assignment]
    "tuple[str, ...] : Tuple of symbols to use for the rain drops. Symbols are randomly chosen from the tuple."

    final_gradient_stops: tuple[Color, ...] = ArgField(
        cmd_name="--final-gradient-stops",
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(Color("488bff"), Color("b2e7de"), Color("57eaf7")),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied across the canvas). If "
        "only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    (
        "tuple[Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the "
        "characters will be displayed in that color."
    )

    final_gradient_steps: tuple[int, ...] | int = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=12,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a "
        "smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    (
        "tuple[int, ...] | int : Int or Tuple of ints for the number of gradient steps to use. More steps will "
        "create a smoother and longer gradient animation."
    )

    final_gradient_direction: Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=argvalidators.GradientDirection.type_parser,
        default=Gradient.Direction.DIAGONAL,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]
    "Gradient.Direction : Direction of the final gradient."

    movement_easing: easing.EasingFunction = ArgField(
        cmd_name=["--movement-easing"],
        default=easing.in_quart,
        type_parser=argvalidators.Ease.type_parser,
        metavar=argvalidators.Ease.METAVAR,
        help="Easing function to use for character movement.",
    )  # type: ignore[assignment]
    "easing.EasingFunction : Easing function to use for character movement."

    @classmethod
    def get_effect_class(cls) -> type[Rain]:
        """Get the effect class associated with this configuration."""
        return Rain


class RainIterator(BaseEffectIterator[RainConfig]):
    """Iterator for the Rain effect."""

    def __init__(self, effect: Rain) -> None:
        """Initialize the iterator with the provided effect.

        Args:
            effect (Rain): The effect to use for the iterator.

        """
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.group_by_row: dict[int, list[EffectCharacter | None]] = {}
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self.build()

    def build(self) -> None:
        """Build the rain effect."""
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

        for character in self.terminal.get_characters():
            raindrop_color = random.choice(self.config.rain_colors)
            rain_scn = character.animation.new_scene()
            rain_scn.add_frame(random.choice(self.config.rain_symbols), 1, colors=ColorPair(fg=raindrop_color))
            raindrop_gradient = Gradient(raindrop_color, self.character_final_color_map[character], steps=7)
            fade_scn = character.animation.new_scene()
            fade_scn.apply_gradient_to_symbols(character.input_symbol, 5, fg_gradient=raindrop_gradient)
            character.animation.activate_scene(rain_scn)
            character.motion.set_coordinate(Coord(character.input_coord.column, self.terminal.canvas.top))
            input_path = character.motion.new_path(
                speed=random.uniform(self.config.movement_speed[0], self.config.movement_speed[1]),
                ease=self.config.movement_easing,
            )
            input_path.new_waypoint(character.input_coord)

            character.event_handler.register_event(
                character.event_handler.Event.PATH_COMPLETE,
                input_path,
                character.event_handler.Action.ACTIVATE_SCENE,
                fade_scn,
            )
            character.motion.activate_path(input_path)
            self.pending_chars.append(character)
        for character in sorted(self.pending_chars, key=lambda c: c.input_coord.row):
            if character.input_coord.row not in self.group_by_row:
                self.group_by_row[character.input_coord.row] = []
            self.group_by_row[character.input_coord.row].append(character)
        self.pending_chars.clear()

    def __next__(self) -> str:
        """Return the next frame in the animation."""
        if self.group_by_row or self.active_characters or self.pending_chars:
            if not self.pending_chars and self.group_by_row:
                self.pending_chars.extend(self.group_by_row.pop(min(self.group_by_row.keys())))  # type: ignore[arg-type]
            if self.pending_chars:
                for _ in range(random.randint(1, 3)):
                    if self.pending_chars:
                        next_character = self.pending_chars.pop(random.randint(0, len(self.pending_chars) - 1))
                        self.terminal.set_character_visibility(next_character, is_visible=True)
                        self.active_characters.add(next_character)

                    else:
                        break
            self.update()
            return self.frame
        raise StopIteration


class Rain(BaseEffect[RainConfig]):
    """Rain characters from the top of the canvas.

    Attributes:
        effect_config (PourConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.

    """

    @property
    def _config_cls(self) -> type[RainConfig]:
        return RainConfig

    @property
    def _iterator_cls(self) -> type[RainIterator]:
        return RainIterator
