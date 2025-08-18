"""Text is scattered across the canvas and moves into position.

Classes:
    Scattered: Move the characters into place from random starting locations.
    ScatteredConfig: Configuration for the Scattered effect.
    ScatteredIterator: Effect iterator for the effect. Does not normally need to be called directly.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import Color, Coord, EffectCharacter, EventHandler, Gradient, Scene, easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.argutils import ArgSpec, ParserSpec


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Get the command, effect class, and configuration class for the effect.

    Returns:
        tuple[str, type[BaseEffect], type[BaseConfig]]: The command name, effect class, and configuration class.

    """
    return "scattered", Scattered, ScatteredConfig


@dataclass
class ScatteredConfig(BaseConfig):
    """Configuration for the effect.

    Attributes:
        movement_speed (float): Movement speed of the characters. Valid values are n > 0.
        movement_easing (easing.EasingFunction): Easing function to use for character movement.
        final_gradient_stops (tuple[Color, ...]): Tuple of colors for the character gradient. If only one color is "
            "provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Tuple of the number of gradient steps to use. More steps will "
            "create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_frames (int): Number of frames to display each gradient step. Increase to slow down the "
            "gradient animation.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient.

    """

    parser_spec: ParserSpec = ParserSpec(
        name="scattered",
        help="Text is scattered across the canvas and moves into position.",
        description="scattered | Text is scattered across the canvas and moves into position.",
        epilog=(
            f"{argutils.EASING_EPILOG} Example: terminaltexteffects scattered --final-gradient-stops ff9048 "
            "ab9dff bdffea --final-gradient-steps 12 --final-gradient-frames 12 --movement-speed 0.5 "
            "--movement-easing IN_OUT_BACK"
        ),
    )

    movement_speed: float = ArgSpec(
        name="--movement-speed",
        type=argutils.PositiveFloat.type_parser,
        default=0.3,
        metavar=argutils.PositiveFloat.METAVAR,
        help="Movement speed of the characters. ",
    )  # pyright: ignore[reportAssignmentType]
    "float : Movement speed of the characters. "

    movement_easing: easing.EasingFunction = ArgSpec(
        name="--movement-easing",
        default=easing.in_out_back,
        type=argutils.Ease.type_parser,
        help="Easing function to use for character movement.",
    )  # pyright: ignore[reportAssignmentType]
    "easing.EasingFunction : Easing function to use for character movement."

    final_gradient_stops: tuple[Color, ...] = ArgSpec(
        name="--final-gradient-stops",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        default=(Color("ff9048"), Color("ab9dff"), Color("bdffea")),
        metavar=argutils.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient. If only one color is provided, "
        "the characters will be displayed in that color.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[Color, ...] : Tuple of colors for the character gradient. If only one color is provided, the "
        "characters will be displayed in that color."
    )

    final_gradient_steps: tuple[int, ...] | int = ArgSpec(
        name="--final-gradient-steps",
        type=argutils.PositiveInt.type_parser,
        default=12,
        metavar=argutils.PositiveInt.METAVAR,
        help="Number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[int, ...] | int : Int or Tuple of ints for the number of gradient steps to use. More steps will create "
        "a smoother and longer gradient animation."
    )

    final_gradient_frames: int = ArgSpec(
        name="--final-gradient-frames",
        type=argutils.PositiveInt.type_parser,
        default=12,
        metavar=argutils.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step. Increase to slow down the gradient animation.",
    )  # pyright: ignore[reportAssignmentType]
    "int : Number of frames to display each gradient step. Increase to slow down the gradient animation."

    final_gradient_direction: Gradient.Direction = ArgSpec(
        name="--final-gradient-direction",
        type=argutils.GradientDirection.type_parser,
        default=Gradient.Direction.VERTICAL,
        metavar=argutils.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # pyright: ignore[reportAssignmentType]
    "Gradient.Direction : Direction of the final gradient."

    @classmethod
    def get_effect_class(cls) -> type[Scattered]:
        """Get the effect class associated with this configuration."""
        return Scattered


class ScatteredIterator(BaseEffectIterator[ScatteredConfig]):
    """Effect iterator for the effect."""

    def __init__(self, effect: Scattered) -> None:
        """Initialize the effect iterator."""
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self.build()

    def build(self) -> None:
        """Build the effect."""
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
            if self.terminal.canvas.right < 2 or self.terminal.canvas.top < 2:
                character.motion.set_coordinate(Coord(1, 1))
            else:
                character.motion.set_coordinate(self.terminal.canvas.random_coord())
            input_coord_path = character.motion.new_path(
                speed=self.config.movement_speed,
                ease=self.config.movement_easing,
            )
            input_coord_path.new_waypoint(character.input_coord)
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
            character.motion.activate_path(input_coord_path)
            self.terminal.set_character_visibility(character, is_visible=True)
            gradient_scn = character.animation.new_scene(sync=Scene.SyncMetric.DISTANCE)
            char_gradient = Gradient(final_gradient.spectrum[0], self.character_final_color_map[character], steps=10)
            gradient_scn.apply_gradient_to_symbols(
                character.input_symbol,
                self.config.final_gradient_frames,
                fg_gradient=char_gradient,
            )
            character.animation.activate_scene(gradient_scn)
            self.active_characters.add(character)
        self._initial_hold_frames = 25

    def __next__(self) -> str:
        """Return the next frame in the animation."""
        if self.pending_chars or self.active_characters:
            if self._initial_hold_frames:
                self._initial_hold_frames -= 1
                return self.frame
            self.update()
            return self.frame
        raise StopIteration


class Scattered(BaseEffect[ScatteredConfig]):
    """Text is scattered across the canvas and moves into position.

    Attributes:
        effect_config (ScatteredConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.

    """

    @property
    def _config_cls(self) -> type[ScatteredConfig]:
        return ScatteredConfig

    @property
    def _iterator_cls(self) -> type[ScatteredIterator]:
        return ScatteredIterator
