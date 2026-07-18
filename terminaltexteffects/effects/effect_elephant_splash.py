"""A playful elephant splashes water to reveal the input text."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from terminaltexteffects.engine.base_config import (
    BaseConfig,
    FinalGradientDirectionArg,
    FinalGradientFramesArg,
    FinalGradientStepsArg,
    FinalGradientStopsArg,
)
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.graphics import Color, Gradient


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command, effect class, and configuration class."""
    return "elephantsplash", ElephantSplash, ElephantSplashConfig


@dataclass
class ElephantSplashConfig(BaseConfig):
    """Configuration for the Elephant Splash effect."""

    parser_spec: argutils.ParserSpec = argutils.ParserSpec(
        name="elephantsplash",
        help="A playful elephant splashes water to reveal the input text.",
        description="elephantsplash | A playful elephant splashes water to reveal the input text.",
        epilog=(
            "Example: terminaltexteffects --canvas-width 0 --canvas-height 0 --anchor-canvas c "
            "--anchor-text c elephantsplash"
        ),
    )

    elephant_color: Color = argutils.ArgSpec(
        name="--elephant-color",
        type=argutils.ColorArg.type_parser,
        default=Color("#8B5CF6"),
        metavar=argutils.ColorArg.METAVAR,
        help="Primary color of the elephant.",
    )  # pyright: ignore[reportAssignmentType]
    elephant_highlight_color: Color = argutils.ArgSpec(
        name="--elephant-highlight-color",
        type=argutils.ColorArg.type_parser,
        default=Color("#C4B5FD"),
        metavar=argutils.ColorArg.METAVAR,
        help="Highlight color used for the elephant's ears, eye, and smile.",
    )  # pyright: ignore[reportAssignmentType]
    water_colors: tuple[Color, ...] = argutils.ArgSpec(
        name="--water-colors",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=(Color("#38BDF8"), Color("#7DD3FC"), Color("#E0F2FE")),
        metavar=argutils.ColorArg.METAVAR,
        help="Colors used for the water droplets and splash reveal.",
    )  # pyright: ignore[reportAssignmentType]
    movement_speed: float = argutils.ArgSpec(
        name="--movement-speed",
        type=argutils.PositiveFloat.type_parser,
        default=0.35,
        metavar=argutils.PositiveFloat.METAVAR,
        help="Speed of the elephant's entrance and exit.",
    )  # pyright: ignore[reportAssignmentType]
    final_gradient_stops: tuple[Color, ...] = FinalGradientStopsArg(
        default=(Color("#8B5CF6"), Color("#C4B5FD"), Color("#F5F3FF")),
    )  # pyright: ignore[reportAssignmentType]
    final_gradient_steps: tuple[int, ...] | int = FinalGradientStepsArg(default=12)  # pyright: ignore[reportAssignmentType]
    final_gradient_frames: int = FinalGradientFramesArg(default=4)  # pyright: ignore[reportAssignmentType]
    final_gradient_direction: Gradient.Direction = FinalGradientDirectionArg(
        default=Gradient.Direction.RADIAL,
    )  # pyright: ignore[reportAssignmentType]
    final_hold_frames: int = argutils.ArgSpec(
        name="--final-hold-frames",
        type=argutils.NonNegativeInt.type_parser,
        default=120,
        metavar=argutils.NonNegativeInt.METAVAR,
        help="Number of frames to hold the completed branding. Zero still emits one clean final frame.",
    )  # pyright: ignore[reportAssignmentType]


class ElephantSplashIterator(BaseEffectIterator[ElephantSplashConfig]):
    """Iterator for the Elephant Splash effect."""

    class Phase(Enum):
        """Ordered phases in the Elephant Splash choreography."""

        WALK_IN = auto()
        RAISE_TRUNK = auto()
        SPLASH = auto()
        REVEAL = auto()
        WALK_OUT = auto()
        HOLD = auto()
        COMPLETE = auto()

    def __init__(self, effect: ElephantSplash) -> None:
        super().__init__(effect)
        if self.terminal.canvas.width >= 24 and self.terminal.canvas.height >= 10:
            self.sprite_mode = "full"
        elif self.terminal.canvas.width >= 12 and self.terminal.canvas.height >= 6:
            self.sprite_mode = "compact"
        else:
            self.sprite_mode = "fallback"
        self.phase = self.Phase.SPLASH if self.sprite_mode == "fallback" else self.Phase.WALK_IN

    def __next__(self) -> str:
        """Stop until the effect lifecycle is implemented."""
        raise StopIteration


class ElephantSplash(BaseEffect[ElephantSplashConfig]):
    """A playful elephant splashes water to reveal the input text."""

    @property
    def _config_cls(self) -> type[ElephantSplashConfig]:
        return ElephantSplashConfig

    @property
    def _iterator_cls(self) -> type[ElephantSplashIterator]:
        return ElephantSplashIterator
