"""MySpray, tutorial step 7: honor colors in the input.

With `--existing-color-handling dynamic`, characters keep their input colors instead of the final gradient.
"""

from __future__ import annotations

import random
import typing
from dataclasses import dataclass

from terminaltexteffects import Color, ColorPair, Coord, EffectCharacter, EventHandler, Gradient, easing
from terminaltexteffects.engine.base_config import (
    BaseConfig,
    FinalGradientDirectionArg,
    FinalGradientStepsArg,
    FinalGradientStopsArg,
)
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "myspray", MySpray, MySprayConfig


@dataclass
class MySprayConfig(BaseConfig):
    """Configuration for the MySpray effect."""

    parser_spec = argutils.ParserSpec(
        name="myspray",
        help="Sprays the characters from a single point.",
        description="myspray | Sprays the characters from a single point.",
        epilog="Example: tte myspray --spray-position center --final-gradient-direction radial",
    )

    spray_position: typing.Literal["n", "ne", "e", "se", "s", "sw", "w", "nw", "center"] = argutils.ArgSpec(
        name="--spray-position",
        choices=["n", "ne", "e", "se", "s", "sw", "w", "nw", "center"],
        default="e",
        help="Position for the spray origin.",
    )  # pyright: ignore[reportAssignmentType]
    "typing.Literal['n', 'ne', 'e', 'se', 's', 'sw', 'w', 'nw', 'center'] : Position for the spray origin."

    spray_volume: float = argutils.ArgSpec(
        name="--spray-volume",
        type=argutils.PositiveRatio.type_parser,
        default=0.005,
        metavar=argutils.PositiveRatio.METAVAR,
        help="Number of characters to spray per tick as a fraction of the total number of characters.",
    )  # pyright: ignore[reportAssignmentType]
    "float : Number of characters to spray per tick as a fraction of the total number of characters."

    movement_speed_range: tuple[float, float] = argutils.ArgSpec(
        name="--movement-speed-range",
        type=argutils.PositiveFloatRange.type_parser,
        default=(0.6, 1.4),
        metavar=argutils.PositiveFloatRange.METAVAR,
        help="Movement speed range of the characters.",
    )  # pyright: ignore[reportAssignmentType]
    "tuple[float, float] : Movement speed range of the characters."

    movement_easing: easing.EasingFunction = argutils.ArgSpec(
        name="--movement-easing",
        type=argutils.Ease.type_parser,
        default=easing.out_expo,
        metavar=argutils.Ease.METAVAR,
        help="Easing function to use for character movement.",
    )  # pyright: ignore[reportAssignmentType]
    "easing.EasingFunction : Easing function to use for character movement."

    final_gradient_stops: tuple[Color, ...] = FinalGradientStopsArg(
        default=(Color("#8A008A"), Color("#00D1FF"), Color("#FFFFFF")),
    )  # pyright: ignore[reportAssignmentType]
    "tuple[Color, ...] : Colors for the final gradient. With one color, the characters are shown in that color."

    final_gradient_steps: tuple[int, ...] | int = FinalGradientStepsArg(
        default=12,
    )  # pyright: ignore[reportAssignmentType]
    "tuple[int, ...] | int : Number of steps between each pair of final gradient stops."

    final_gradient_direction: Gradient.Direction = FinalGradientDirectionArg(
        default=Gradient.Direction.VERTICAL,
    )  # pyright: ignore[reportAssignmentType]
    "Gradient.Direction : Direction of the final gradient across the text."


class MySprayIterator(BaseEffectIterator[MySprayConfig]):
    """Produce the frames of the MySpray effect."""

    def __init__(self, effect: MySpray) -> None:
        """Set up every character before the first frame."""
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.build()

    def build(self) -> None:
        """Give every character a path home and a droplet scene, and queue it for release."""
        canvas = self.terminal.canvas
        final_gradient = Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            canvas.text_bottom,
            canvas.text_top,
            canvas.text_left,
            canvas.text_right,
            self.config.final_gradient_direction,
        )
        spray_origin_map = {
            "center": canvas.center,
            "n": Coord(canvas.center_column, canvas.top),
            "nw": Coord(canvas.left, canvas.top),
            "w": Coord(canvas.left, canvas.center_row),
            "sw": Coord(canvas.left, canvas.bottom),
            "s": Coord(canvas.center_column, canvas.bottom),
            "se": Coord(canvas.right - 1, canvas.bottom),
            "e": Coord(canvas.right - 1, canvas.center_row),
            "ne": Coord(canvas.right - 1, canvas.top),
        }
        spray_origin = spray_origin_map[self.config.spray_position]
        dynamic = self.terminal.config.existing_color_handling == "dynamic"
        for character in self.terminal.get_characters():
            character.motion.set_coordinate(spray_origin)
            input_coord_path = character.motion.new_path(
                speed=random.uniform(*self.config.movement_speed_range),
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
            droplet_scn = character.animation.new_scene()
            if dynamic:
                # Show the input colors, with no fade, for as long as the gradient scene would play.
                input_colors = ColorPair(fg=character.animation.input_fg_color, bg=character.animation.input_bg_color)
                droplet_scn.add_frame(character.input_symbol, 160, colors=input_colors)
            else:
                spray_gradient = Gradient(
                    random.choice(final_gradient.spectrum),
                    final_gradient_mapping[character.input_coord],
                    steps=7,
                )
                droplet_scn.apply_gradient_to_symbols(character.input_symbol, 20, fg_gradient=spray_gradient)
            character.animation.activate_scene(droplet_scn)
            character.motion.activate_path(input_coord_path)
            self.pending_chars.append(character)
        random.shuffle(self.pending_chars)
        # Release up to `spray_volume` of the characters per frame, and at least one.
        self._volume = max(int(len(self.pending_chars) * self.config.spray_volume), 1)

    def __next__(self) -> str:
        """Release a few characters, advance the animation, and return the frame."""
        if self.pending_chars or self.active_characters:
            for _ in range(random.randint(1, self._volume)):
                if self.pending_chars:
                    next_character = self.pending_chars.pop()
                    self.terminal.set_character_visibility(next_character, is_visible=True)
                    self.active_characters.add(next_character)
            self.update()
            return self.frame
        raise StopIteration


class MySpray(BaseEffect[MySprayConfig]):
    """Sprays the characters from a single point."""

    @property
    def _config_cls(self) -> type[MySprayConfig]:
        return MySprayConfig

    @property
    def _iterator_cls(self) -> type[MySprayIterator]:
        return MySprayIterator
