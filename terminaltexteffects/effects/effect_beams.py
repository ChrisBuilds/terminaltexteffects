"""Creates beams which travel over the canvas illuminating the characters.

Classes:
    Beams: Creates beams which travel over the canvas illuminating the characters.
    BeamsConfig: Configuration for the Beams effect.
    BeamsIterator: Iterates over the Beams effect. Does not normally need to be called directly.
"""

from __future__ import annotations

import random
import typing
from dataclasses import dataclass

import terminaltexteffects as tte
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argvalidators
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    """Return the Beams effect class and its configuration class."""
    return Beams, BeamsConfig


@argclass(
    name="beams",
    help="Create beams which travel over the canvas illuminating the characters behind them.",
    description="beams | Create beams which travel over the canvas illuminating the characters behind them.",
    epilog=(
        "Example: terminaltexteffects beams --beam-row-symbols ▂ ▁ _ --beam-column-symbols ▌ ▍ ▎ ▏ --beam-delay "
        "10 --beam-row-speed-range 10-40 --beam-column-speed-range 6-10 --beam-gradient-stops ffffff 00D1FF "
        "8A008A --beam-gradient-steps 2 8 --beam-gradient-frames 2 --final-gradient-stops 8A008A 00D1FF "
        "ffffff --final-gradient-steps 12 --final-gradient-frames 5 --final-gradient-direction vertical "
        "--final-wipe-speed 1"
    ),
)
@dataclass
class BeamsConfig(ArgsDataClass):
    """Configuration for the Beams effect.

    Attributes:
        beam_row_symbols (tuple[str, ...] | str): Symbols to use for the beam effect when moving along a row. Strings
            will be used in sequence to create an animation.
        beam_column_symbols (tuple[str, ...] | str): Symbols to use for the beam effect when moving along a column.
            Strings will be used in sequence to create an animation.
        beam_delay (int): Number of frames to wait before adding the next group of beams. Beams are added in groups
            of size random(1, 5). Valid values are n > 0.
        beam_row_speed_range (tuple[int, int]): Speed range of the beam when moving along a row. Valid values are n > 0.
        beam_column_speed_range (tuple[int, int]): Speed range of the beam when moving along a column.
            Valid values are n > 0.
        beam_gradient_stops (tuple[tte.Color, ...]): Tuple of colors for the beam, a gradient will be created between
            the colors.
        beam_gradient_steps (tuple[int, ...] | int): Tuple of the number of gradient steps to use. More steps will
            create a smoother and longer gradient animation. Steps are paired with the colors in final-gradient-stops.
            Valid values are n > 0.
        beam_gradient_frames (int): Number of frames to display each gradient step. Increase to slow down the gradient
            animation. Valid values are n > 0.
        final_gradient_stops (tuple[tte.Color, ...]): Tuple of colors for the wipe gradient.
        final_gradient_steps (tuple[int, ...] | int): Tuple of the number of gradient steps to use. More steps will
            create a smoother and longer gradient animation. Steps are paired with the colors in final-gradient-stops.
            Valid values are n > 0.
        final_gradient_frames (int): Number of frames to display each gradient step. Increase to slow down the
            gradient animation.
        final_gradient_direction (tte.Gradient.Direction): Direction of the final gradient.
        final_wipe_speed (int): Speed of the final wipe as measured in diagonal groups activated per frame.
            Valid values are n > 0.

    """

    beam_row_symbols: tuple[str, ...] | str = ArgField(
        cmd_name="--beam-row-symbols",
        type_parser=argvalidators.Symbol.type_parser,
        nargs="+",
        default=("▂", "▁", "_"),
        metavar=argvalidators.Symbol.METAVAR,
        help=(
            "Symbols to use for the beam effect when moving along a row. "
            "Strings will be used in sequence to create an animation."
        ),
    )  # type: ignore[assignment]

    (
        "tuple[str, ...] | str : Symbols to use for the beam effect when moving along a row. "
        "Strings will be used in sequence to create an animation."
    )

    beam_column_symbols: tuple[str, ...] | str = ArgField(
        cmd_name="--beam-column-symbols",
        type_parser=argvalidators.Symbol.type_parser,
        nargs="+",
        default=("▌", "▍", "▎", "▏"),
        metavar=argvalidators.Symbol.METAVAR,
        help=(
            "Symbols to use for the beam effect when moving along a column. "
            "Strings will be used in sequence to create an animation."
        ),
    )  # type: ignore[assignment]

    (
        "tuple[str, ...] | str : Symbols to use for the beam effect when moving along a column. "
        "Strings will be used in sequence to create an animation."
    )

    beam_delay: int = ArgField(
        cmd_name="--beam-delay",
        type_parser=argvalidators.PositiveInt.type_parser,
        default=10,
        metavar=argvalidators.PositiveInt.METAVAR,
        help=(
            "Number of frames to wait before adding the next group of beams. "
            "Beams are added in groups of size random(1, 5)."
        ),
    )  # type: ignore[assignment]

    (
        "int : Number of frames to wait before adding the next group of beams. "
        "Beams are added in groups of size random(1, 5)."
    )

    beam_row_speed_range: tuple[int, int] = ArgField(
        cmd_name="--beam-row-speed-range",
        type_parser=argvalidators.PositiveIntRange.type_parser,
        default=(10, 40),
        metavar=argvalidators.PositiveIntRange.METAVAR,
        help="Speed range of the beam when moving along a row.",
    )  # type: ignore[assignment]

    "tuple[int, int] : Speed range of the beam when moving along a row."

    beam_column_speed_range: tuple[int, int] = ArgField(
        cmd_name="--beam-column-speed-range",
        type_parser=argvalidators.PositiveIntRange.type_parser,
        default=(6, 10),
        metavar=argvalidators.PositiveIntRange.METAVAR,
        help="Speed range of the beam when moving along a column.",
    )  # type: ignore[assignment]

    "tuple[int, int] : Speed range of the beam when moving along a column."

    beam_gradient_stops: tuple[tte.Color, ...] = ArgField(
        cmd_name="--beam-gradient-stops",
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(tte.Color("ffffff"), tte.Color("00D1FF"), tte.Color("8A008A")),
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Space separated, unquoted, list of colors for the beam, a gradient will be created between the colors.",
    )  # type: ignore[assignment]

    "tuple[tte.Color, ...] : Tuple of colors for the beam, a gradient will be created between the colors."

    beam_gradient_steps: tuple[int, ...] | int = ArgField(
        cmd_name="--beam-gradient-steps",
        type_parser=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=(2, 8),
        metavar=argvalidators.PositiveInt.METAVAR,
        help=(
            "Space separated, unquoted, numbers for the of gradient steps to use. "
            "More steps will create a smoother and longer gradient animation. "
            "Steps are paired with the colors in final-gradient-stops."
        ),
    )  # type: ignore[assignment]

    (
        "tuple[int, ...] | int : Int or Tuple of ints for the number of gradient steps to use. "
        "More steps will create a smoother and longer gradient animation. "
        "Steps are paired with the colors in final-gradient-stops."
    )

    beam_gradient_frames: int = ArgField(
        cmd_name="--beam-gradient-frames",
        type_parser=argvalidators.PositiveInt.type_parser,
        default=2,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step. Increase to slow down the gradient animation.",
    )  # type: ignore[assignment]

    "int : Number of frames to display each gradient step. Increase to slow down the gradient animation."

    final_gradient_stops: tuple[tte.Color, ...] = ArgField(
        cmd_name="--final-gradient-stops",
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(tte.Color("8A008A"), tte.Color("00D1FF"), tte.Color("ffffff")),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the wipe gradient.",
    )  # type: ignore[assignment]

    "tuple[tte.Color, ...] : Tuple of colors for the wipe gradient."

    final_gradient_steps: tuple[int, ...] | int = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=12,
        metavar=argvalidators.PositiveInt.METAVAR,
        help=(
            "Space separated, unquoted, numbers for the of gradient steps to use. "
            "More steps will create a smoother and longer gradient animation. "
            "Steps are paired with the colors in final-gradient-stops."
        ),
    )  # type: ignore[assignment]

    (
        "tuple[int, ...] | int : Int or Tuple of ints for the number of gradient steps to use. "
        "More steps will create a smoother and longer gradient animation. "
        "Steps are paired with the colors in final-gradient-stops."
    )

    final_gradient_frames: int = ArgField(
        cmd_name="--final-gradient-frames",
        type_parser=argvalidators.PositiveInt.type_parser,
        default=5,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step. Increase to slow down the gradient animation.",
    )  # type: ignore[assignment]

    "int : Number of frames to display each gradient step. Increase to slow down the gradient animation."

    final_gradient_direction: tte.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=argvalidators.GradientDirection.type_parser,
        default=tte.Gradient.Direction.VERTICAL,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]

    "tte.Gradient.Direction : Direction of the final gradient."

    final_wipe_speed: int = ArgField(
        cmd_name="--final-wipe-speed",
        type_parser=argvalidators.PositiveInt.type_parser,
        default=1,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Speed of the final wipe as measured in diagonal groups activated per frame.",
    )  # type: ignore[assignment]

    "int : Speed of the final wipe as measured in diagonal groups activated per frame."

    @classmethod
    def get_effect_class(cls) -> type[Beams]:
        """Return the effect class associated with this configuration."""
        return Beams


class BeamsIterator(BaseEffectIterator[BeamsConfig]):
    """Iterator for the Beams effect."""

    class Group:
        """Represents a group of characters."""

        def __init__(
            self,
            characters: list[tte.EffectCharacter],
            direction: str,
            terminal: tte.Terminal,
            args: BeamsConfig,
        ) -> None:
            """Initialize the Group."""
            self.characters = characters
            self.direction: str = direction
            self.terminal = terminal
            direction_speed_range = {
                "row": (args.beam_row_speed_range[0], args.beam_row_speed_range[1]),
                "column": (args.beam_column_speed_range[0], args.beam_column_speed_range[1]),
            }
            self.speed = random.randint(direction_speed_range[direction][0], direction_speed_range[direction][1]) * 0.1
            self.next_character_counter: float = 0
            if self.direction == "row":
                self.characters.sort(key=lambda character: character.input_coord.column)
            elif self.direction == "column":
                self.characters.sort(key=lambda character: character.input_coord.row)
            if random.choice([True, False]):
                self.characters.reverse()

        def increment_next_character_counter(self) -> None:
            """Increment the counter for the next character."""
            self.next_character_counter += self.speed

        def get_next_character(self) -> tte.EffectCharacter | None:
            """Get the next character in the group.

            If the next character is already active, determined by having an active scene, the active
            scene is reset and None is returned. Otherwise, the next character is returned and the character
            is made visible.

            Returns:
                tte.EffectCharacter | None: The next character if the character or None if the character is
                    already active.

            """
            self.next_character_counter -= 1
            next_character = self.characters.pop(0)
            if next_character.animation.active_scene:
                next_character.animation.active_scene.reset_scene()
                return_value = None
            else:
                self.terminal.set_character_visibility(next_character, is_visible=True)
                return_value = next_character
            next_character.animation.activate_scene(next_character.animation.query_scene("beam_" + self.direction))
            return return_value

        def complete(self) -> bool:
            """Check if the group is complete.

            Returns:
                bool: True if the group is complete, False otherwise.

            """
            return not self.characters

    def __init__(self, effect: Beams) -> None:
        """Initialize the BeamsIterator.

        Args:
            effect (Beams): The Beams effect instance.

        """
        super().__init__(effect)
        self.pending_groups: list[BeamsIterator.Group] = []
        self.character_final_color_map: dict[tte.EffectCharacter, tte.ColorPair] = {}
        self.active_groups: list[BeamsIterator.Group] = []
        self.delay = 0
        self.phase = "beams"
        self.final_wipe_groups = self.terminal.get_characters_grouped(
            tte.Terminal.CharacterGroup.DIAGONAL_TOP_LEFT_TO_BOTTOM_RIGHT,
        )
        self.build()

    def build(self) -> None:
        """Build the initial state for the Beams effect."""
        final_gradient = tte.Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.canvas.text_bottom,
            self.terminal.canvas.text_top,
            self.terminal.canvas.text_left,
            self.terminal.canvas.text_right,
            self.config.final_gradient_direction,
        )
        for character in self.terminal.get_characters(outer_fill_chars=True, inner_fill_chars=True):
            if character.is_fill_character:
                self.character_final_color_map[character] = tte.ColorPair(fg="000000")
                continue
            if self.terminal.config.existing_color_handling == "dynamic" and self.preexisting_colors_present:
                fg_color = tte.Color("ffffff")
                bg_color = None
                if character.animation.input_fg_color:
                    fg_color = character.animation.input_fg_color
                if character.animation.input_bg_color:
                    bg_color = character.animation.input_bg_color
                self.character_final_color_map[character] = tte.ColorPair(fg=fg_color, bg=bg_color)
            else:
                self.character_final_color_map[character] = tte.ColorPair(
                    fg=final_gradient_mapping[character.input_coord],
                )

        beam_gradient = tte.Gradient(*self.config.beam_gradient_stops, steps=self.config.beam_gradient_steps)
        groups: list[BeamsIterator.Group] = []
        for row in self.terminal.get_characters_grouped(
            tte.Terminal.CharacterGroup.ROW_TOP_TO_BOTTOM,
            outer_fill_chars=True,
            inner_fill_chars=True,
        ):
            groups.append(BeamsIterator.Group(row, "row", self.terminal, self.config))  # noqa: PERF401
        for column in self.terminal.get_characters_grouped(
            tte.Terminal.CharacterGroup.COLUMN_LEFT_TO_RIGHT,
            outer_fill_chars=True,
            inner_fill_chars=True,
        ):
            groups.append(BeamsIterator.Group(column, "column", self.terminal, self.config))  # noqa: PERF401
        for group in groups:
            for character in group.characters:
                beam_row_scn = character.animation.new_scene(scene_id="beam_row")
                beam_column_scn = character.animation.new_scene(scene_id="beam_column")
                brigthen_scn = character.animation.new_scene(scene_id="brighten")
                beam_row_scn.apply_gradient_to_symbols(
                    self.config.beam_row_symbols,
                    self.config.beam_gradient_frames,
                    fg_gradient=beam_gradient,
                )
                beam_column_scn.apply_gradient_to_symbols(
                    self.config.beam_column_symbols,
                    self.config.beam_gradient_frames,
                    fg_gradient=beam_gradient,
                )
                fg_fade_gradient = bg_fade_gradient = fg_brighten_gradient = bg_brighten_gradient = None
                char_fg_color = self.character_final_color_map[character].fg_color
                char_bg_color = self.character_final_color_map[character].bg_color
                if char_fg_color:
                    faded_fg_color = character.animation.adjust_color_brightness(char_fg_color, 0.3)
                    fg_fade_gradient = tte.Gradient(char_fg_color, faded_fg_color, steps=10)
                    fg_brighten_gradient = tte.Gradient(faded_fg_color, char_fg_color, steps=10)
                if char_bg_color:
                    faded_bg_color = character.animation.adjust_color_brightness(char_bg_color, 0.3)
                    bg_fade_gradient = tte.Gradient(char_bg_color, faded_bg_color, steps=10)
                    bg_brighten_gradient = tte.Gradient(faded_bg_color, char_bg_color, steps=10)

                beam_row_scn.apply_gradient_to_symbols(
                    character.input_symbol,
                    5,
                    fg_gradient=fg_fade_gradient,
                    bg_gradient=bg_fade_gradient,
                )
                beam_column_scn.apply_gradient_to_symbols(
                    character.input_symbol,
                    5,
                    fg_gradient=fg_fade_gradient,
                    bg_gradient=bg_fade_gradient,
                )
                brigthen_scn.apply_gradient_to_symbols(
                    character.input_symbol,
                    self.config.final_gradient_frames,
                    fg_gradient=fg_brighten_gradient,
                    bg_gradient=bg_brighten_gradient,
                )

        self.pending_groups = groups
        random.shuffle(self.pending_groups)

    def __next__(self) -> str:
        """Return the next frame in the effect."""
        if self.phase != "complete" or self.active_characters:
            if self.phase == "beams":
                if not self.delay:
                    if self.pending_groups:
                        for _ in range(random.randint(1, 5)):
                            if self.pending_groups:
                                self.active_groups.append(self.pending_groups.pop(0))
                    self.delay = self.config.beam_delay
                else:
                    self.delay -= 1
                for group in self.active_groups:
                    group.increment_next_character_counter()
                    if int(group.next_character_counter) > 1:
                        for _ in range(int(group.next_character_counter)):
                            if not group.complete():
                                next_char = group.get_next_character()
                                if next_char:
                                    self.active_characters.add(next_char)
                self.active_groups = [group for group in self.active_groups if not group.complete()]
                if not self.pending_groups and not self.active_groups and not self.active_characters:
                    self.phase = "final_wipe"
            elif self.phase == "final_wipe":
                if self.final_wipe_groups:
                    for _ in range(self.config.final_wipe_speed):
                        if not self.final_wipe_groups:
                            break
                        next_group = self.final_wipe_groups.pop(0)
                        for character in next_group:
                            character.animation.activate_scene(character.animation.query_scene("brighten"))
                            self.terminal.set_character_visibility(character, is_visible=True)
                            self.active_characters.add(character)
                else:
                    self.phase = "complete"
            self.update()
            return self.frame
        raise StopIteration


class Beams(BaseEffect[BeamsConfig]):
    """Creates beams which travel over the canvas illuminating the characters.

    Attributes:
        effect_config (BeamsConfig): Configuration for the effect.
        terminal_config (tte.TerminalConfig): Configuration for the terminal.

    """

    @property
    def _config_cls(self) -> type[BeamsConfig]:
        return BeamsConfig

    @property
    def _iterator_cls(self) -> type[BeamsIterator]:
        return BeamsIterator
