"""Effect Description.

Classes:

"""

from __future__ import annotations

import random
from dataclasses import dataclass

import terminaltexteffects as tte
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.argutils import ArgSpec, ParserSpec


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Get the command, effect class, and configuration class for the effect.

    Returns:
        tuple[str, type[BaseEffect], type[BaseConfig]]: The command name, effect class, and configuration class.

    """
    return "spaceflight", Effect, EffectConfig


@dataclass
class EffectConfig(BaseConfig):
    """Effect configuration dataclass."""

    parser_spec: ParserSpec = ParserSpec(
        name="spaceflight",
        help="effect_description",
        description="effect_description",
        epilog=f"""{argutils.EASING_EPILOG}
    """,
    )

    color_single: tte.Color = ArgSpec(
        name="--color-single",
        type=argutils.ColorArg.type_parser,
        default=tte.Color(0),
        metavar=argutils.ColorArg.METAVAR,
        help="Color for the ___.",
    )  # pyright: ignore[reportAssignmentType]
    "Color: Color for the ___."

    final_gradient_stops: tuple[tte.Color, ...] = ArgSpec(
        name="--final-gradient-stops",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=(tte.Color("#8A008A"), tte.Color("#00D1FF"), tte.Color("#FFFFFF")),
        metavar=argutils.ColorArg.METAVAR,
        help=(
            "Space separated, unquoted, list of colors for the character gradient (applied across the canvas). "
            "If only one color is provided, the characters will be displayed in that color."
        ),
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[Color, ...]: Space separated, unquoted, list of colors for the character gradient "
        "(applied across the canvas). If only one color is provided, the characters will be displayed in that color."
    )

    final_gradient_steps: tuple[int, ...] | int = ArgSpec(
        name="--final-gradient-steps",
        type=argutils.PositiveInt.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=12,
        metavar=argutils.PositiveInt.METAVAR,
        help=(
            "Space separated, unquoted, list of the number of gradient steps to use. More steps will "
            "create a smoother and longer gradient animation."
        ),
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[int, ...] | int: Space separated, unquoted, list of the number of gradient steps to use. More "
        "steps will create a smoother and longer gradient animation."
    )

    final_gradient_frames: int = ArgSpec(
        name="--final-gradient-frames",
        type=argutils.PositiveInt.type_parser,
        default=5,
        metavar=argutils.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step. Increase to slow down the gradient animation.",
    )  # pyright: ignore[reportAssignmentType]
    "int: Number of frames to display each gradient step. Increase to slow down the gradient animation."

    final_gradient_direction: tte.Gradient.Direction = ArgSpec(
        name="--final-gradient-direction",
        type=argutils.GradientDirection.type_parser,
        default=tte.Gradient.Direction.VERTICAL,
        metavar=argutils.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # pyright: ignore[reportAssignmentType]
    "Gradient.Direction : Direction of the final gradient."

    movement_speed: float = ArgSpec(
        name="--movement-speed",
        type=argutils.PositiveFloat.type_parser,
        default=1,
        metavar=argutils.PositiveFloat.METAVAR,
        help="Speed of the ___.",
    )  # pyright: ignore[reportAssignmentType]
    "float: Speed of the ___."

    easing: tte.easing.EasingFunction = ArgSpec(
        name="--easing",
        default=tte.easing.in_out_sine,
        type=argutils.Ease.type_parser,
        help="Easing function to use for character movement.",
    )  # pyright: ignore[reportAssignmentType]
    "easing.EasingFunction: Easing function to use for character movement."


class EffectIterator(BaseEffectIterator[EffectConfig]):
    """Effect iterator for the NamedEffect effect."""

    def __init__(self, effect: Effect) -> None:
        """Initialize the effect iterator.

        Args:
            effect (NamedEffect): The effect to iterate over.

        """
        super().__init__(effect)
        self.pending_chars: list[tte.EffectCharacter] = []
        self.character_final_color_map: dict[tte.EffectCharacter, tte.Color] = {}
        self.available_stars: set[tte.EffectCharacter] = set()
        self.active_stars: set[tte.EffectCharacter] = set()
        self.travel_frames = 0
        self.build()

    def reset_star(self, star: tte.EffectCharacter) -> None:
        """Reset a star to the center of the canvas.

        Args:
            star (EffectCharacter): The star to reset.

        """
        star.motion.set_coordinate(self.terminal.canvas.center)
        self.available_stars.add(star)
        star.motion.activate_path("star")
        star.animation.activate_scene("approach")
        self.terminal.set_character_visibility(star, is_visible=False)

    def spawn_star(self) -> None:
        """Pop an available star and make it visible and active."""
        if not self.available_stars:
            return
        new_star = self.available_stars.pop()
        self.terminal.set_character_visibility(new_star, is_visible=True)
        self.active_characters.add(new_star)

    def build(self) -> None:
        """Build the effect."""
        final_gradient = tte.Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.canvas.text_bottom,
            self.terminal.canvas.text_top,
            self.terminal.canvas.text_left,
            self.terminal.canvas.text_right,
            self.config.final_gradient_direction,
        )
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]
            character.animation.set_appearance(colors=tte.ColorPair(self.character_final_color_map[character]))
            character.motion.set_coordinate(self.terminal.canvas.center)
            arrive_path = character.motion.new_path(
                path_id="arrive",
                speed=random.uniform(0.1, 0.4),
                hold_time=random.randint(300, 900),
            )
            arrive_path.new_waypoint(character.input_coord)
            depart_path = character.motion.new_path(speed=random.uniform(0.4, 0.7))
            if character.input_coord == self.terminal.canvas.center:
                depart_path.new_waypoint(self.terminal.canvas.random_coord(outside_scope=True))
            else:
                depart_path.new_waypoint(
                    tte.geometry.extrapolate_along_ray(
                        self.terminal.canvas.center,
                        character.input_coord,
                        self.terminal.canvas.width,
                    ),
                )
            character.event_handler.register_event(
                tte.Event.PATH_COMPLETE,
                caller=arrive_path,
                action=tte.Action.ACTIVATE_PATH,
                target=depart_path,
            )
            character.motion.activate_path(arrive_path)
            character.layer = 2
            self.pending_chars.append(character)

        for _ in range(500):
            starting_symbol = random.choice([".", "`", "'", ","])
            star_char = self.terminal.add_character(starting_symbol, coord=self.terminal.canvas.center)
            approach_scn = star_char.animation.new_scene(scene_id="approach", sync=tte.Scene.SyncMetric.DISTANCE)
            approach_scn.add_frame(symbol=starting_symbol, duration=random.randint(1, 3))
            approach_scn.add_frame(symbol=random.choice(["*", "-", "x", "~", "."]), duration=1)
            star_path = star_char.motion.new_path(
                path_id="star",
                speed=random.uniform(0.01, 0.4),
                ease=tte.easing.in_quart,
            )
            star_path.new_waypoint(self.terminal.canvas.random_coord(outside_scope=True))
            star_char.motion.activate_path(star_path)
            star_char.animation.activate_scene("approach")
            star_char.event_handler.register_event(
                tte.Event.PATH_COMPLETE,
                star_path,
                action=tte.Action.CALLBACK,
                target=tte.EventHandler.Callback(self.reset_star),
            )
            self.available_stars.add(star_char)

        for _ in range(self.terminal.canvas.height * self.terminal.canvas.width // 20):
            stationary_star = self.terminal.add_character(
                symbol=random.choice([".", "`", "'", ",", "*"]),
                coord=self.terminal.canvas.random_coord(),
            )
            self.terminal.set_character_visibility(stationary_star, is_visible=True)

    def __next__(self) -> str:
        """Return the next frame of the effect."""
        if self.active_characters or self.available_stars:
            if self.travel_frames > 300:
                while self.pending_chars:
                    character = self.pending_chars.pop()
                    self.active_characters.add(character)
                    self.terminal.set_character_visibility(character, is_visible=True)
            if random.random() < 0.5:
                for _ in range(random.randint(1, 4)):
                    self.spawn_star()
            self.travel_frames += 1
            self.update()
            return self.frame
        raise StopIteration


class Effect(BaseEffect[EffectConfig]):
    """Effect description."""

    @property
    def _config_cls(self) -> type[EffectConfig]:
        return EffectConfig

    @property
    def _iterator_cls(self) -> type[EffectIterator]:
        return EffectIterator
