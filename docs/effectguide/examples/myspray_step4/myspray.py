"""MySpray, tutorial step 4: draw moving characters in front of settled ones.

Events move each character to layer 1 while it flies and back to layer 0 when it lands.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from terminaltexteffects import Coord, EffectCharacter, EventHandler, easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "myspray", MySpray, MySprayConfig


@dataclass
class MySprayConfig(BaseConfig):
    """Configuration for the MySpray effect. It has no options yet."""

    parser_spec = argutils.ParserSpec(
        name="myspray",
        help="Sprays the characters from a single point.",
        description="myspray | Sprays the characters from a single point.",
        epilog="Example: tte myspray",
    )


class MySprayIterator(BaseEffectIterator[MySprayConfig]):
    """Produce the frames of the MySpray effect."""

    def __init__(self, effect: MySpray) -> None:
        """Set up every character before the first frame."""
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.build()

    def build(self) -> None:
        """Give every character a path home from the spray origin, and queue it for release."""
        canvas = self.terminal.canvas
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
        spray_origin = spray_origin_map["e"]
        for character in self.terminal.get_characters():
            character.motion.set_coordinate(spray_origin)
            input_coord_path = character.motion.new_path(
                speed=random.uniform(0.6, 1.4),
                ease=easing.out_expo,
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
            self.pending_chars.append(character)
        random.shuffle(self.pending_chars)
        # Release up to 0.5% of the characters per frame, and at least one.
        self._volume = max(int(len(self.pending_chars) * 0.005), 1)

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
