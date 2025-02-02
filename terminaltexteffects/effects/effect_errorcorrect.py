"""Swaps characters from an incorrect initial position to the correct position.

Classes:
    ErrorCorrect: Swaps characters from an incorrect initial position to the correct position.
    ErrorCorrectConfig: Configuration for the ErrorCorrect effect.
    ErrorCorrectIterator: Iterates over the effect. Does not normally need to be called directly.
"""

from __future__ import annotations

import random
import typing
from dataclasses import dataclass

from terminaltexteffects import Color, EffectCharacter, EventHandler, Gradient, Scene
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argvalidators
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.graphics import ColorPair


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    """Get the effect class and its configuration class."""
    return ErrorCorrect, ErrorCorrectConfig


@argclass(
    name="errorcorrect",
    help="Some characters start in the wrong position and are corrected in sequence.",
    description="errorcorrect | Some characters start in the wrong position and are corrected in sequence.",
    epilog=(
        f"{argvalidators.EASING_EPILOG}"
        "Example: terminaltexteffects errorcorrect --error-pairs 0.1 --swap-delay 10 --error-color e74c3c "
        "--correct-color 45bf55 --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 "
        "--movement-speed 0.5"
    ),
)
@dataclass
class ErrorCorrectConfig(ArgsDataClass):
    """Configuration for the ErrorCorrect effect.

    Attributes:
        error_pairs (float): Percent of characters that are in the wrong position. This is a float between 0 and
            1.0. 0.2 means 20 percent of the characters will be in the wrong position. Valid values are 0 < n <= 1.0.
        swap_delay (int): Number of frames between swaps. Valid values are n >= 0.
        error_color (Color): Color for the characters that are in the wrong position.
        correct_color (Color): Color for the characters once corrected, this is a gradient from error-color and
            fades to final-color.
        final_gradient_stops (tuple[Color, ...]): Tuple of colors for the final color gradient. If only one color
            is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Tuple of the number of gradient steps to use. More steps
            will create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient.
        movement_speed (float): Speed of the characters while moving to the correct position. Valid values are n > 0.

    """

    error_pairs: float = ArgField(
        cmd_name="--error-pairs",
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=0.1,
        metavar="(int > 0)",
        help="Percent of characters that are in the wrong position. This is a float between 0 and 1.0. 0.2 means "
        "20 percent of the characters will be in the wrong position.",
    )  # type: ignore[assignment]
    (
        "float : Percent of characters that are in the wrong position. This is a float between 0 and 1.0. 0.2 "
        "means 20 percent of the characters will be in the wrong position."
    )

    swap_delay: int = ArgField(
        cmd_name="--swap-delay",
        type_parser=argvalidators.PositiveInt.type_parser,
        default=10,
        metavar="(int > 0)",
        help="Number of frames between swaps.",
    )  # type: ignore[assignment]
    "int : Number of frames between swaps."

    error_color: Color = ArgField(
        cmd_name=["--error-color"],
        type_parser=argvalidators.ColorArg.type_parser,
        default=Color("e74c3c"),
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the characters that are in the wrong position.",
    )  # type: ignore[assignment]
    "Color : Color for the characters that are in the wrong position."

    correct_color: Color = ArgField(
        cmd_name=["--correct-color"],
        type_parser=argvalidators.ColorArg.type_parser,
        default=Color("45bf55"),
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the characters once corrected, this is a gradient from error-color and fades to final-color.",
    )  # type: ignore[assignment]
    "Color : Color for the characters once corrected, this is a gradient from error-color and fades to final-color."

    movement_speed: float = ArgField(
        cmd_name="--movement-speed",
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=0.5,
        metavar="(float > 0)",
        help="Speed of the characters while moving to the correct position. ",
    )  # type: ignore[assignment]
    "float : Speed of the characters while moving to the correct position. "

    final_gradient_stops: tuple[Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(Color("8A008A"), Color("00D1FF"), Color("FFFFFF")),
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Space separated, unquoted, list of colors for the character gradient (applied across the canvas). "
        "If only one color is provided, the characters will be displayed in that color.",
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
        metavar="(int > 0)",
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
        default=Gradient.Direction.VERTICAL,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]
    "Gradient.Direction : Direction of the final gradient."

    @classmethod
    def get_effect_class(cls) -> type[ErrorCorrect]:
        """Get the effect class associated with this configuration."""
        return ErrorCorrect


class ErrorCorrectIterator(BaseEffectIterator[ErrorCorrectConfig]):
    """Iterates over the ErrorCorrect effect."""

    def __init__(self, effect: ErrorCorrect) -> None:
        """Initialize the iterator.

        Args:
            effect (ErrorCorrect): The effect to use for the iterator.

        """
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.swapped: list[tuple[EffectCharacter, EffectCharacter]] = []
        self.swap_delay = 0
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self.build()

    def build(self) -> None:
        """Build the initial state of the effect."""
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
            spawn_scene = character.animation.new_scene()
            spawn_scene.add_frame(
                character.input_symbol,
                1,
                colors=ColorPair(fg=self.character_final_color_map[character]),
            )
            character.animation.activate_scene(spawn_scene)
            self.terminal.set_character_visibility(character, is_visible=True)
        all_characters: list[EffectCharacter] = list(self.terminal._input_characters)
        correcting_gradient = Gradient(self.config.error_color, self.config.correct_color, steps=10)
        block_symbol = "▓"
        block_wipe_start = ("▁", "▂", "▃", "▄", "▅", "▆", "▇", "█")
        block_wipe_end = ("▇", "▆", "▅", "▄", "▃", "▂", "▁")
        for _ in range(int(self.config.error_pairs * len(self.terminal.get_characters()))):
            if len(all_characters) < 2:
                break
            char1 = all_characters.pop(random.randrange(len(all_characters)))
            char2 = all_characters.pop(random.randrange(len(all_characters)))
            char1.motion.set_coordinate(char2.input_coord)
            char1_input_coord_path = char1.motion.new_path(path_id="input_coord", speed=self.config.movement_speed)
            char1_input_coord_path.new_waypoint(char1.input_coord)
            char2.motion.set_coordinate(char1.input_coord)
            char2_input_coord_path = char2.motion.new_path(path_id="input_coord", speed=self.config.movement_speed)
            char2_input_coord_path.new_waypoint(char2.input_coord)
            self.swapped.append((char1, char2))
            for character in (char1, char2):
                first_block_wipe = character.animation.new_scene()
                last_block_wipe = character.animation.new_scene()
                for block in block_wipe_start:
                    first_block_wipe.add_frame(block, 3, colors=ColorPair(fg=self.config.error_color))
                for block in block_wipe_end:
                    last_block_wipe.add_frame(block, 3, colors=ColorPair(fg=self.config.correct_color))
                initial_scene = character.animation.new_scene()
                initial_scene.add_frame(character.input_symbol, 1, colors=ColorPair(fg=self.config.error_color))
                character.animation.activate_scene(initial_scene)
                error_scene = character.animation.new_scene(scene_id="error")
                for _ in range(10):
                    error_scene.add_frame(block_symbol, 3, colors=ColorPair(fg=self.config.error_color))
                    error_scene.add_frame(character.input_symbol, 3, colors=ColorPair(fg="ffffff"))
                correcting_scene = character.animation.new_scene(sync=Scene.SyncMetric.DISTANCE)
                correcting_scene.apply_gradient_to_symbols("█", 3, fg_gradient=correcting_gradient)
                final_scene = character.animation.new_scene()
                char_final_gradient = Gradient(
                    self.config.correct_color,
                    self.character_final_color_map[character],
                    steps=10,
                )
                final_scene.apply_gradient_to_symbols(character.input_symbol, 3, fg_gradient=char_final_gradient)
                input_coord_path = character.motion.query_path("input_coord")
                character.event_handler.register_event(
                    EventHandler.Event.SCENE_COMPLETE,
                    error_scene,
                    EventHandler.Action.ACTIVATE_SCENE,
                    first_block_wipe,
                )
                character.event_handler.register_event(
                    EventHandler.Event.SCENE_COMPLETE,
                    first_block_wipe,
                    EventHandler.Action.ACTIVATE_SCENE,
                    correcting_scene,
                )
                character.event_handler.register_event(
                    EventHandler.Event.SCENE_COMPLETE,
                    first_block_wipe,
                    EventHandler.Action.ACTIVATE_PATH,
                    input_coord_path,
                )
                character.event_handler.register_event(
                    EventHandler.Event.PATH_ACTIVATED,
                    input_coord_path,
                    EventHandler.Action.SET_LAYER,
                    1,
                )
                character.event_handler.register_event(
                    EventHandler.Event.PATH_COMPLETE,
                    input_coord_path,
                    EventHandler.Action.SET_LAYER,
                    0,
                )

                character.event_handler.register_event(
                    EventHandler.Event.PATH_COMPLETE,
                    input_coord_path,
                    EventHandler.Action.ACTIVATE_SCENE,
                    last_block_wipe,
                )
                character.event_handler.register_event(
                    EventHandler.Event.SCENE_COMPLETE,
                    last_block_wipe,
                    EventHandler.Action.ACTIVATE_SCENE,
                    final_scene,
                )

    def __next__(self) -> str:
        """Return the next frame in the animation."""
        if self.swapped and not self.swap_delay:
            next_pair = self.swapped.pop(0)
            for char in next_pair:
                char.animation.activate_scene(char.animation.query_scene("error"))
                self.active_characters.add(char)
            self.swap_delay = self.config.swap_delay
        elif self.swap_delay:
            self.swap_delay -= 1
        if self.active_characters:
            self.update()
            return self.frame
        raise StopIteration


class ErrorCorrect(BaseEffect[ErrorCorrectConfig]):
    """Swaps characters from an incorrect initial position to the correct position.

    Attributes:
        effect_config (ErrorCorrectConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.

    """

    @property
    def _config_cls(self) -> type[ErrorCorrectConfig]:
        return ErrorCorrectConfig

    @property
    def _iterator_cls(self) -> type[ErrorCorrectIterator]:
        return ErrorCorrectIterator
