"""Characters are grouped into swarms and move around the terminal before settling into position.

Classes:
    Swarm: Characters are grouped into swarms and move around the terminal before settling into position.
    SwarmConfig: Configuration for the Swarm effect.
    SwarmIterator: Effect iterator for the Swarm effect. Does not normally need to be called directly.
"""

from __future__ import annotations

import random
import typing
from dataclasses import dataclass

from terminaltexteffects import (
    Color,
    ColorPair,
    Coord,
    EffectCharacter,
    EventHandler,
    Gradient,
    Scene,
    easing,
    geometry,
)
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argvalidators
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    """Get the effect class and its configuration class."""
    return Swarm, SwarmConfig


@argclass(
    name="swarm",
    help="Characters are grouped into swarms and move around the terminal before settling into position.",
    description="swarm | Characters are grouped into swarms and move around the terminal before settling "
    "into position.",
    epilog=(
        "Example: terminaltexteffects swarm --base-color 31a0d4 --flash-color f2ea79 --final-gradient-stops "
        "31b900 f0ff65 --final-gradient-steps 12 --swarm-size 0.1 --swarm-coordination 0.80 "
        "--swarm-area-count 2-4"
    ),
)
@dataclass
class SwarmConfig(ArgsDataClass):
    """Configuration for the Swarm effect.

    Attributes:
        base_color (tuple[Color, ...]): Tuple of colors for the swarms.
        flash_color (Color): Color for the character flash. Characters flash when moving.
        swarm_size (float): Percent of total characters in each swarm. Valid values are 0 < n <= 1.
        swarm_coordination (float): Percent of characters in a swarm that move as a group. Valid values are 0 < n <= 1.
        swarm_area_count_range (tuple[int, int]): Range of the number of areas where characters will swarm. Valid
            values are n > 0.
        final_gradient_stops (tuple[Color, ...]): Tuple of colors for the final color gradient. If only one color is
            provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Tuple of the number of gradient steps to use. More steps will
            create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient.

    """

    base_color: tuple[Color, ...] = ArgField(
        cmd_name=["--base-color"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(Color("31a0d4"),),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the swarms",
    )  # type: ignore[assignment]
    """tuple[Color, ...] : Tuple of colors for the swarms"""

    flash_color: Color = ArgField(
        cmd_name=["--flash-color"],
        type_parser=argvalidators.ColorArg.type_parser,
        default=Color("f2ea79"),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Color for the character flash. Characters flash when moving.",
    )  # type: ignore[assignment]
    """Color : Color for the character flash. Characters flash when moving."""

    swarm_size: float = ArgField(
        cmd_name="--swarm-size",
        type_parser=argvalidators.NonNegativeRatio.type_parser,
        metavar=argvalidators.NonNegativeRatio.METAVAR,
        default=0.1,
        help="Percent of total characters in each swarm.",
    )  # type: ignore[assignment]
    "float : Percent of total characters in each swarm."

    swarm_coordination: float = ArgField(
        cmd_name="--swarm-coordination",
        type_parser=argvalidators.NonNegativeRatio.type_parser,
        metavar=argvalidators.NonNegativeRatio.METAVAR,
        default=0.80,
        help="Percent of characters in a swarm that move as a group.",
    )  # type: ignore[assignment]
    "float : Percent of characters in a swarm that move as a group."

    swarm_area_count_range: tuple[int, int] = ArgField(
        cmd_name="--swarm-area-count-range",
        type_parser=argvalidators.PositiveIntRange.type_parser,
        metavar=argvalidators.PositiveIntRange.METAVAR,
        default=(2, 4),
        help="Range of the number of areas where characters will swarm.",
    )  # type: ignore[assignment]
    "tuple[int, int] : Range of the number of areas where characters will swarm."

    final_gradient_stops: tuple[Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(Color("31b900"), Color("f0ff65")),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied across the canvas). If "
        "only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    (
        "tuple[Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the "
        "characters will be displayed in that color."
    )

    final_gradient_steps: tuple[int, ...] | int = ArgField(
        cmd_name=["--final-gradient-steps"],
        type_parser=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=12,
        metavar=argvalidators.PositiveInt.METAVAR,
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
        default=Gradient.Direction.HORIZONTAL,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]
    "Gradient.Direction : Direction of the final gradient."

    @classmethod
    def get_effect_class(cls) -> type[Swarm]:
        """Get the effect class associated with this configuration."""
        return Swarm


class SwarmIterator(BaseEffectIterator[SwarmConfig]):
    """Effect iterator for the Swarm effect."""

    def __init__(
        self,
        effect: Swarm,
    ) -> None:
        """Initialize the Swarm effect iterator.

        Args:
            effect (Swarm): The effect to use for the iterator.

        """
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.swarms: list[list[EffectCharacter]] = []
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self.build()

    def make_swarms(self, swarm_size: int) -> None:
        """Create swarms of characters.

        Args:
            swarm_size (int): The size of each swarm.

        """
        unswarmed_characters = self.terminal.get_characters(
            sort=self.terminal.CharacterSort.BOTTOM_TO_TOP_RIGHT_TO_LEFT,
        )

        while unswarmed_characters:
            new_swarm: list[EffectCharacter] = []
            for _ in range(swarm_size):
                if unswarmed_characters:
                    new_swarm.append(unswarmed_characters.pop())
                else:
                    break
            self.swarms.append(new_swarm)
        final_swarm = self.swarms.pop()
        if len(final_swarm) < swarm_size // 2:
            self.swarms[-1].extend(final_swarm)
        else:
            self.swarms.append(final_swarm)

    def build(self) -> None:  # noqa: PLR0915
        """Build the initial state of the effect."""
        swarm_size: int = max(round(len(self.terminal.get_characters()) * self.config.swarm_size), 1)
        self.make_swarms(swarm_size)
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
        flash_list = [self.config.flash_color for _ in range(10)]
        for swarm in self.swarms:
            swarm_gradient = Gradient(random.choice(self.config.base_color), self.config.flash_color, steps=7)
            swarm_gradient_mirror = list(swarm_gradient) + flash_list + list(swarm_gradient)[::-1]
            swarm_area_coordinate_map: dict[Coord, list[Coord]] = {}
            swarm_spawn = self.terminal.canvas.random_coord(outside_scope=True)
            swarm_areas: list[Coord] = []
            swarm_area_count = random.randint(
                self.config.swarm_area_count_range[0],
                self.config.swarm_area_count_range[1],
            )
            # create areas where characters will swarm
            last_focus_coord = swarm_spawn
            radius = max(min(self.terminal.canvas.right, self.terminal.canvas.top) // 2, 1)
            while len(swarm_areas) < swarm_area_count:
                potential_focus_coords = geometry.find_coords_on_circle(last_focus_coord, radius)
                random.shuffle(potential_focus_coords)
                for coord in potential_focus_coords:
                    if self.terminal.canvas.coord_is_in_canvas(coord):
                        next_focus_coord = coord
                        break
                else:
                    next_focus_coord = self.terminal.canvas.random_coord()
                swarm_areas.append(next_focus_coord)
                swarm_area_coordinate_map[last_focus_coord] = geometry.find_coords_in_circle(
                    last_focus_coord,
                    max(min(self.terminal.canvas.right, self.terminal.canvas.top) // 6, 1) * 2,
                )
                last_focus_coord = next_focus_coord

            # assign characters waypoints for swarm areas and inner waypoints within the swarm areas
            for character in swarm:
                swarm_area_count = 0
                character.motion.set_coordinate(swarm_spawn)
                flash_scn = character.animation.new_scene(sync=Scene.SyncMetric.DISTANCE)
                for step in swarm_gradient_mirror:
                    flash_scn.add_frame(character.input_symbol, 1, colors=ColorPair(fg=step))
                for swarm_area_coords in swarm_area_coordinate_map.values():
                    swarm_area_name = f"{swarm_area_count}_swarm_area"
                    swarm_area_count += 1
                    origin_path = character.motion.new_path(path_id=swarm_area_name, speed=0.25, ease=easing.out_sine)
                    origin_path.new_waypoint(random.choice(swarm_area_coords), waypoint_id=swarm_area_name)
                    character.event_handler.register_event(
                        EventHandler.Event.PATH_ACTIVATED,
                        origin_path,
                        EventHandler.Action.ACTIVATE_SCENE,
                        flash_scn,
                    )
                    character.event_handler.register_event(
                        EventHandler.Event.PATH_ACTIVATED,
                        origin_path,
                        EventHandler.Action.SET_LAYER,
                        1,
                    )
                    character.event_handler.register_event(
                        EventHandler.Event.PATH_COMPLETE,
                        origin_path,
                        EventHandler.Action.DEACTIVATE_SCENE,
                        flash_scn,
                    )
                    inner_paths = 0
                    total_inner_paths = 2
                    while inner_paths < total_inner_paths:
                        next_coord = random.choice(swarm_area_coords)
                        inner_paths += 1
                        inner_path = character.motion.new_path(
                            path_id=str(len(character.motion.paths)),
                            speed=0.1,
                            ease=easing.in_out_sine,
                        )
                        inner_path.new_waypoint(next_coord, waypoint_id=str(len(character.motion.paths)))
                # create landing waypoint and scene
                input_path = character.motion.new_path(speed=0.3, ease=easing.in_out_quad)
                input_path.new_waypoint(character.input_coord)
                input_scn = character.animation.new_scene()
                for step in Gradient(self.config.flash_color, self.character_final_color_map[character], steps=10):
                    input_scn.add_frame(character.input_symbol, 3, colors=ColorPair(fg=step))
                character.event_handler.register_event(
                    EventHandler.Event.PATH_COMPLETE,
                    input_path,
                    EventHandler.Action.ACTIVATE_SCENE,
                    input_scn,
                )
                character.event_handler.register_event(
                    EventHandler.Event.PATH_COMPLETE,
                    input_path,
                    EventHandler.Action.SET_LAYER,
                    0,
                )
                character.event_handler.register_event(
                    EventHandler.Event.PATH_ACTIVATED,
                    input_path,
                    EventHandler.Action.ACTIVATE_SCENE,
                    flash_scn,
                )
                character.motion.chain_paths(list(character.motion.paths.values()))
        self.call_next = True
        self.active_swarm_area = "0_swarm_area"

    def __next__(self) -> str:
        """Return the next frame in the animation."""
        if self.swarms or self.active_characters:
            if self.swarms and self.call_next:
                self.call_next = False
                self.current_swarm = self.swarms.pop()
                self.active_swarm_area = "0_swarm_area"
                for character in self.current_swarm:
                    character.motion.activate_path(character.motion.query_path("0_swarm_area"))
                    self.terminal.set_character_visibility(character, is_visible=True)
                    self.active_characters.add(character)
            if len(self.active_characters) < len(self.current_swarm):  # some of the characters have landed
                self.call_next = True
            if self.current_swarm:
                for character in self.current_swarm:
                    if (
                        character.motion.active_path
                        and character.motion.active_path.path_id != self.active_swarm_area
                        and "swarm_area" in character.motion.active_path.path_id
                        and int(character.motion.active_path.path_id[0]) > int(self.active_swarm_area[0])
                    ):
                        self.active_swarm_area = character.motion.active_path.path_id
                        for other in self.current_swarm:
                            if other is not character and random.random() < self.config.swarm_coordination:
                                other.motion.activate_path(other.motion.paths[self.active_swarm_area])
                        break

            self.update()
            return self.frame
        raise StopIteration


class Swarm(BaseEffect[SwarmConfig]):
    """Characters are grouped into swarms and move around the terminal before settling into position.

    Attributes:
        effect_config (SwarmConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.

    """

    @property
    def _config_cls(self) -> type[SwarmConfig]:
        return SwarmConfig

    @property
    def _iterator_cls(self) -> type[SwarmIterator]:
        return SwarmIterator
