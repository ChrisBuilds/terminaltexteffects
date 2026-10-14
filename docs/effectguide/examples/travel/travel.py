"""Travel: move every character home along a path.

An Effect Guide example for the Motion chapter.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import Coord, easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "travel", Travel, TravelConfig


@dataclass
class TravelConfig(BaseConfig):
    """Configuration for the Travel effect."""

    parser_spec = argutils.ParserSpec(
        name="travel",
        help="Moves every character home along a path.",
        description="travel | Moves every character home along a path.",
        epilog=f"{argutils.EASING_EPILOG}Example: tte travel --ease out_bounce",
    )
    speed: float = argutils.ArgSpec(
        name="--speed",
        type=argutils.PositiveFloat.type_parser,
        default=0.5,
        metavar=argutils.PositiveFloat.METAVAR,
        help="Distance each character moves per frame.",
    )  # pyright: ignore[reportAssignmentType]
    "float : Distance each character moves per frame."

    ease: easing.EasingFunction = argutils.ArgSpec(
        name="--ease",
        type=argutils.Ease.type_parser,
        default=easing.linear,
        metavar=argutils.Ease.METAVAR,
        help="Easing function applied to each path.",
    )  # pyright: ignore[reportAssignmentType]
    "easing.EasingFunction : Easing function applied to each path."

    curve: bool = argutils.ArgSpec(
        name="--curve",
        default=False,
        action="store_true",
        help="Start in the bottom left corner and curve home through the bottom right corner.",
    )  # pyright: ignore[reportAssignmentType]
    "bool : Start in the bottom left corner and curve home through the bottom right corner."


class TravelIterator(BaseEffectIterator[TravelConfig]):
    """Produce the frames of the Travel effect."""

    def __init__(self, effect: Travel) -> None:
        """Give every character a path home and start it moving."""
        super().__init__(effect)
        canvas = self.terminal.canvas
        for character in self.terminal.get_characters():
            path = character.motion.new_path(speed=self.config.speed, ease=self.config.ease)
            if self.config.curve:
                character.motion.set_coordinate(Coord(canvas.left, canvas.bottom))
                path.new_waypoint(character.input_coord, bezier_control=Coord(canvas.right, canvas.bottom))
            else:
                character.motion.set_coordinate(Coord(canvas.left, character.input_coord.row))
                path.new_waypoint(character.input_coord)
            character.motion.activate_path(path)
            self.terminal.set_character_visibility(character, is_visible=True)
            self.active_characters.add(character)

    def __next__(self) -> str:
        """Move the characters one step and return the frame."""
        if self.active_characters:
            self.update()
            return self.frame
        raise StopIteration


class Travel(BaseEffect[TravelConfig]):
    """Moves every character home along a path."""

    @property
    def _config_cls(self) -> type[TravelConfig]:
        return TravelConfig

    @property
    def _iterator_cls(self) -> type[TravelIterator]:
        return TravelIterator
