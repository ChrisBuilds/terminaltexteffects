"""The text tumbles in from the distance as a flat sheet, spins, and settles into place.

Classes:
    MySpin: The text tumbles in from the distance as a flat sheet, spins, and settles into place.
    MySpinConfig: Configuration for the MySpin effect.
    MySpinIterator: Iterates over the effect. Does not normally need to be called directly.
"""

from __future__ import annotations

import typing
from dataclasses import dataclass

from terminaltexteffects import Body, Color, ColorPair, EffectCharacter, Gradient, Scene, Vec3, easing
from terminaltexteffects.engine.base_config import (
    BaseConfig,
    FinalGradientDirectionArg,
    FinalGradientStepsArg,
    FinalGradientStopsArg,
)
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Get the command, effect class, and configuration class for the effect.

    Returns:
        tuple[str, type[BaseEffect], type[BaseConfig]]: The command name, effect class, and configuration class.

    """
    return "myspin", MySpin, MySpinConfig


@dataclass
class MySpinConfig(BaseConfig):
    """Configuration for the MySpin effect.

    Attributes:
        spin_turns (float): Number of turns about the vertical axis before the text settles. Valid values are n > 0.
        spin_frames (int): Number of frames from the start of the spin until the text settles. Valid values are n > 0.
        spin_easing (easing.EasingFunction): Easing function for the spin and the approach.
        start_distance (float): How far behind the canvas the text starts, in columns. Valid values are n >= 0.
        perspective (float): Strength of the perspective. 0 is a flat view. Valid values are n >= 0.
        shadow_color (Color): Color of the text when it faces away from the light.
        hide_back (bool): Hide the text while its back faces the viewer, instead of showing it mirrored in shadow.
        final_gradient_stops (tuple[Color, ...]): Tuple of colors for the final color gradient. If only one color
            is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Tuple of the number of gradient steps to use. More steps will
            create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient.

    """

    parser_spec: argutils.ParserSpec = argutils.ParserSpec(
        name="myspin",
        help="The text tumbles in from the distance as a flat sheet, spins, and settles into place.",
        description="myspin | The text tumbles in from the distance as a flat sheet, spins, and settles into place.",
        epilog=(
            f"{argutils.EASING_EPILOG} Example: terminaltexteffects myspin --spin-turns 2 --spin-frames 240 "
            "--spin-easing OUT_CUBIC --start-distance 200 --perspective 1 --shadow-color 303030 "
            "--final-gradient-stops 8A008A 00D1FF ffffff --final-gradient-steps 12 "
            "--final-gradient-direction vertical"
        ),
    )

    spin_turns: float = argutils.ArgSpec(
        name="--spin-turns",
        type=argutils.PositiveFloat.type_parser,
        default=2.0,
        metavar=argutils.PositiveFloat.METAVAR,
        help="Number of turns about the vertical axis before the text settles.",
    )  # pyright: ignore[reportAssignmentType]
    "float : Number of turns about the vertical axis before the text settles."

    spin_frames: int = argutils.ArgSpec(
        name="--spin-frames",
        type=argutils.PositiveInt.type_parser,
        default=240,
        metavar=argutils.PositiveInt.METAVAR,
        help="Number of frames from the start of the spin until the text settles.",
    )  # pyright: ignore[reportAssignmentType]
    "int : Number of frames from the start of the spin until the text settles."

    spin_easing: easing.EasingFunction = argutils.ArgSpec(
        name="--spin-easing",
        type=argutils.Ease.type_parser,
        default=easing.out_cubic,
        help="Easing function for the spin and the approach.",
    )  # pyright: ignore[reportAssignmentType]
    "easing.EasingFunction : Easing function for the spin and the approach."

    start_distance: float = argutils.ArgSpec(
        name="--start-distance",
        type=argutils.NonNegativeFloat.type_parser,
        default=200.0,
        metavar=argutils.NonNegativeFloat.METAVAR,
        help="How far behind the canvas the text starts, in columns.",
    )  # pyright: ignore[reportAssignmentType]
    "float : How far behind the canvas the text starts, in columns."

    perspective: float = argutils.ArgSpec(
        name="--perspective",
        type=argutils.NonNegativeFloat.type_parser,
        default=1.0,
        metavar=argutils.NonNegativeFloat.METAVAR,
        help="Strength of the perspective. 0 is a flat view.",
    )  # pyright: ignore[reportAssignmentType]
    "float : Strength of the perspective. 0 is a flat view."

    shadow_color: Color = argutils.ArgSpec(
        name="--shadow-color",
        type=argutils.ColorArg.type_parser,
        default=Color("#303030"),
        metavar=argutils.ColorArg.METAVAR,
        help="Color of the text when it faces away from the light.",
    )  # pyright: ignore[reportAssignmentType]
    "Color : Color of the text when it faces away from the light."

    hide_back: bool = argutils.ArgSpec(
        name="--hide-back",
        default=False,
        action="store_true",
        help="Hide the text while its back faces the viewer, instead of showing it mirrored in shadow.",
    )  # pyright: ignore[reportAssignmentType]
    "bool : Hide the text while its back faces the viewer, instead of showing it mirrored in shadow."

    final_gradient_stops: tuple[Color, ...] = FinalGradientStopsArg(
        default=(Color("#8A008A"), Color("#00D1FF"), Color("#FFFFFF")),
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the "
        "characters will be displayed in that color."
    )

    final_gradient_steps: tuple[int, ...] | int = FinalGradientStepsArg(
        default=12,
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[int, ...] | int : Int or Tuple of ints for the number of gradient steps to use. More steps will "
        "create a smoother and longer gradient animation."
    )

    final_gradient_direction: Gradient.Direction = FinalGradientDirectionArg(
        default=Gradient.Direction.VERTICAL,
    )  # pyright: ignore[reportAssignmentType]
    "Gradient.Direction : Direction of the final gradient."


class MySpinIterator(BaseEffectIterator[MySpinConfig]):
    """Iterator for the MySpin effect."""

    SHADE_STEPS = 10
    """Number of colors between the shadow color and a character's final color."""

    def __init__(self, effect: MySpin) -> None:
        """Move the text plane far behind the canvas and queue its approach and spin.

        Args:
            effect (MySpin): The effect to iterate over.

        """
        super().__init__(effect)
        self.final_colors: dict[EffectCharacter, ColorPair] = {}
        self.world = self.terminal.world
        self.build()

    def build(self) -> None:
        """Build the effect."""
        world = self.world
        world.camera.set_perspective(self.config.perspective)
        world.set_light("front")
        dynamic = self.terminal.config.existing_color_handling == "dynamic"
        final_gradient = Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.canvas.text_bottom,
            self.terminal.canvas.text_top,
            self.terminal.canvas.text_left,
            self.terminal.canvas.text_right,
            self.config.final_gradient_direction,
        )
        # Spaces are invisible, so only those with an input background color are worth shading and showing.
        characters = [
            character
            for character in self.terminal.get_characters()
            if character.input_symbol != " " or character.animation.input_bg_color is not None
        ]
        for character in characters:
            if dynamic:
                colors = ColorPair(fg=character.animation.input_fg_color, bg=character.animation.input_bg_color)
            else:
                colors = ColorPair(fg=final_gradient_mapping[character.input_coord])
            self.final_colors[character] = colors
            # The light on its spot picks the frame: shadow when the text faces away, the final color facing
            # the viewer. The background, if any, stays the same, and input colors without a foreground keep their
            # colors throughout.
            scene = character.animation.new_scene(sync=Scene.SyncMetric.LIGHT)
            if colors.fg is None:
                scene.add_frame(character.input_symbol, 1, colors=colors)
            else:
                shade = Gradient(self.config.shadow_color, typing.cast("Color", colors.fg), steps=self.SHADE_STEPS)
                for color in shade.spectrum:
                    scene.add_frame(character.input_symbol, 1, colors=ColorPair(fg=color, bg=colors.bg))
            character.animation.activate_scene(scene)
            self.terminal.set_character_visibility(character, is_visible=True)
            self.active_characters.add(character)

        self.sheet = world.text_plane
        self.sheet.hide_facing_away = self.config.hide_back
        frames, ease = self.config.spin_frames, self.config.spin_easing
        if self.config.start_distance:
            self.sheet.position = Vec3(0, 0, -self.config.start_distance)
            approach = self.sheet.motion.new_path(speed=self.config.start_distance / frames, ease=ease)
            approach.new_waypoint(Vec3(0, 0, 0))
            self.sheet.motion.activate_path(approach)
        self.sheet.random_pose()
        self.sheet.settle("y", turns=self.config.spin_turns, frames=frames, ease=ease)
        self.sheet.on_complete(self.finish)

    def finish(self, sheet: Body) -> None:
        """Put the text plane back at rest and show the characters in their final colors."""
        sheet.reset()
        for character, colors in self.final_colors.items():
            character.animation.deactivate_scene()
            character.animation.set_appearance(character.input_symbol, colors)

    def __next__(self) -> str:
        """Return the next frame in the animation."""
        if self.world.animating or self.active_characters:
            self.update()
            return self.frame
        raise StopIteration


class MySpin(BaseEffect[MySpinConfig]):
    """The text tumbles in from the distance as a flat sheet, spins, and settles into place.

    Attributes:
        effect_config (MySpinConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.

    """

    @property
    def _config_cls(self) -> type[MySpinConfig]:
        return MySpinConfig

    @property
    def _iterator_cls(self) -> type[MySpinIterator]:
        return MySpinIterator
