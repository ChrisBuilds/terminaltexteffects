"""Sparks: columns of text appear from left to right, each character throwing off a spark.

An Effect Guide example for the Particles pattern.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from terminaltexteffects import CharacterOrder, Color, ColorPair, Coord, EffectCharacter, ParticlePool, easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils

SPARK_COLORS = (Color("#ffffff"), Color("#ffd000"), Color("#ff6000"))
TICKS_BETWEEN_COLUMNS = 2


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "sparks", Sparks, SparksConfig


@dataclass
class SparksConfig(BaseConfig):
    """Configuration for the Sparks effect."""

    parser_spec = argutils.ParserSpec(
        name="sparks",
        help="Columns of text appear from left to right, each character throwing off a spark.",
        description="sparks | Columns of text appear from left to right, each character throwing off a spark.",
        epilog="Example: tte sparks --max-sparks 8",
    )
    max_sparks: int = argutils.ArgSpec(
        name="--max-sparks",
        type=argutils.PositiveInt.type_parser,
        default=60,
        metavar=argutils.PositiveInt.METAVAR,
        help="Most sparks on screen at once.",
    )  # pyright: ignore[reportAssignmentType]
    "int : Most sparks on screen at once."


class SparksIterator(BaseEffectIterator[SparksConfig]):
    """Produce the frames of the Sparks effect."""

    def __init__(self, effect: Sparks) -> None:
        """Create the spark pool and queue the columns."""
        super().__init__(effect)
        self.ticks = 0
        self.pending_columns = self.terminal.get_characters_grouped(order=CharacterOrder.COLUMN_LEFT_TO_RIGHT)
        self.pending_columns.reverse()  # So pop() takes the leftmost column.
        self.sparks = ParticlePool(
            self.terminal,
            self.active_characters,
            "*",
            max_size=self.config.max_sparks,
            initializer=self.initialize_spark,
        )

    def initialize_spark(self, spark: EffectCharacter) -> None:
        """Set up a new spark once: its layer, its fading scene, and its return to the pool."""
        spark.layer = 1
        scene = spark.animation.new_scene(scene_id="fade")
        for symbol, color in zip("*+.", SPARK_COLORS):
            scene.add_frame(symbol, 6, colors=ColorPair(fg=color))
        self.sparks.reclaim_on_event(spark, caller=scene)

    def launch_spark(self, spark: EffectCharacter) -> None:
        """Send a spark up and to one side from where it was emitted, and start its fade."""
        start = spark.motion.current_coord
        path = spark.motion.new_path(speed=0.4, ease=easing.out_quad)
        path.new_waypoint(Coord(start.column + random.randint(-3, 3), start.row + random.randint(1, 3)))
        spark.motion.activate_path(path)
        scene = spark.animation.query_scene("fade")
        scene.reset_scene()
        spark.animation.activate_scene(scene)

    def __next__(self) -> str:
        """Reveal the next column every few ticks and return the frame."""
        if not self.pending_columns and not self.active_characters:
            raise StopIteration
        if self.pending_columns and self.ticks % TICKS_BETWEEN_COLUMNS == 0:
            for character in self.pending_columns.pop():
                self.terminal.set_character_visibility(character, is_visible=True)
                self.sparks.emit(character.input_coord, self.launch_spark)
        self.ticks += 1
        self.update()
        return self.frame


class Sparks(BaseEffect[SparksConfig]):
    """Columns of text appear from left to right, each character throwing off a spark."""

    @property
    def _config_cls(self) -> type[SparksConfig]:
        return SparksConfig

    @property
    def _iterator_cls(self) -> type[SparksIterator]:
        return SparksIterator
