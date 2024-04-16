import random
import typing
from collections.abc import Iterator
from dataclasses import dataclass

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils import animation, easing, geometry, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.terminal import Terminal, TerminalConfig


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return SwarmEffect, EffectConfig


@argclass(
    name="swarm",
    help="Characters are grouped into swarms and move around the terminal before settling into position.",
    description="swarm | Characters are grouped into swarms and move around the terminal before settling into position.",
    epilog="""Example: terminaltexteffects swarm --base-color 31a0d4 --flash-color f2ea79 --final-gradient-stops 31b900 f0ff65 --final-gradient-steps 12 --swarm-size 0.1 --swarm-coordination 0.80 --swarm-area-count 2-4""",
)
@dataclass
class EffectConfig(ArgsDataClass):
    """Configuration for the Swarm effect.

    Attributes:
        base_color (tuple[graphics.Color, ...]): Tuple of colors for the swarms.
        flash_color (graphics.Color): Color for the character flash. Characters flash when moving.
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the gradient for the final color.
        swarm_size (float): Percent of total characters in each swarm.
        swarm_coordination (float): Percent of characters in a swarm that move as a group.
        swarm_area_count (tuple[int, int]): Range of the number of areas where characters will swarm."""

    base_color: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--base-color"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("31a0d4",),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the swarms",
    )  # type: ignore[assignment]
    """tuple[graphics.Color, ...] : Tuple of colors for the swarms"""

    flash_color: graphics.Color = ArgField(
        cmd_name=["--flash-color"],
        type_parser=arg_validators.Color.type_parser,
        default="f2ea79",
        metavar=arg_validators.Color.METAVAR,
        help="Color for the character flash. Characters flash when moving.",
    )  # type: ignore[assignment]
    """graphics.Color : Color for the character flash. Characters flash when moving."""

    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("31b900", "f0ff65"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[graphics.Color, ...] : Tuple of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name=["--final-gradient-steps"],
        type_parser=arg_validators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] : Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=arg_validators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.HORIZONTAL,
        metavar=arg_validators.GradientDirection.METAVAR,
        help="Direction of the gradient for the final color.",
    )  # type: ignore[assignment]
    "graphics.Gradient.Direction : Direction of the gradient for the final color."

    swarm_size: float = ArgField(
        cmd_name="--swarm-size",
        type_parser=arg_validators.Ratio.type_parser,
        metavar=arg_validators.Ratio.METAVAR,
        default=0.1,
        help="Percent of total characters in each swarm.",
    )  # type: ignore[assignment]
    "float : Percent of total characters in each swarm."

    swarm_coordination: float = ArgField(
        cmd_name="--swarm-coordination",
        type_parser=arg_validators.Ratio.type_parser,
        metavar=arg_validators.Ratio.METAVAR,
        default=0.80,
        help="Percent of characters in a swarm that move as a group.",
    )  # type: ignore[assignment]
    "float : Percent of characters in a swarm that move as a group."

    swarm_area_count: tuple[int, int] = ArgField(
        cmd_name="--swarm-area-count",
        type_parser=arg_validators.IntRange.type_parser,
        metavar=arg_validators.IntRange.METAVAR,
        default=(2, 4),
        help="Range of the number of areas where characters will swarm.",
    )  # type: ignore[assignment]
    "tuple[int, int] : Range of the number of areas where characters will swarm."

    @classmethod
    def get_effect_class(cls):
        return SwarmEffect


class SwarmEffect:
    """Characters behave with swarm characteristics before flying into position."""

    def __init__(
        self,
        input_data: str,
        effect_config: EffectConfig = EffectConfig(),
        terminal_config: TerminalConfig = TerminalConfig(),
    ):
        """Initializes the effect.

        Args:
            input_data (str): The input data to apply the effect to.
            effect_config (EffectConfig): The configuration for the effect.
            terminal_config (TerminalConfig): The configuration for the terminal.
        """
        self.terminal = Terminal(input_data, terminal_config)
        self.config = effect_config
        self._built = False
        self._pending_chars: list[EffectCharacter] = []
        self._active_chars: list[EffectCharacter] = []
        self._swarms: list[list[EffectCharacter]] = []
        self._character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def make_swarms(self, swarm_size: int) -> None:
        unswarmed_characters = list(self.terminal._input_characters[::-1])
        while unswarmed_characters:
            new_swarm: list[EffectCharacter] = []
            for _ in range(swarm_size):
                if unswarmed_characters:
                    new_swarm.append(unswarmed_characters.pop())
                else:
                    break
            self._swarms.append(new_swarm)

    def build(self) -> None:
        """Prepares the data for the effect by creating swarms of characters and setting waypoints and animations."""
        self._pending_chars.clear()
        self._active_chars.clear()
        self._character_final_color_map.clear()
        self._swarms.clear()
        swarm_size: int = max(round(len(self.terminal._input_characters) * self.config.swarm_size), 1)
        self.make_swarms(swarm_size)
        final_gradient = graphics.Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.config.final_gradient_direction
        )
        for character in self.terminal.get_characters():
            self._character_final_color_map[character] = final_gradient_mapping[character.input_coord]
        flash_list = [self.config.flash_color for _ in range(10)]
        for swarm in self._swarms:
            swarm_gradient = graphics.Gradient(random.choice(self.config.base_color), self.config.flash_color, steps=7)
            swarm_gradient_mirror = list(swarm_gradient) + flash_list + list(swarm_gradient)[::-1]
            swarm_area_coordinate_map: dict[Coord, list[Coord]] = {}
            swarm_spawn = self.terminal.output_area.random_coord(outside_scope=True)
            swarm_areas: list[Coord] = []
            swarm_area_count = random.randint(self.config.swarm_area_count[0], self.config.swarm_area_count[1])
            # create areas where characters will swarm
            last_focus_coord = swarm_spawn
            radius = max(min(self.terminal.output_area.right, self.terminal.output_area.top) // 2, 1)
            while len(swarm_areas) < swarm_area_count:
                potential_focus_coords = geometry.find_coords_on_circle(last_focus_coord, radius)
                random.shuffle(potential_focus_coords)
                for coord in potential_focus_coords:
                    if self.terminal.output_area.coord_is_in_output_area(coord):
                        next_focus_coord = coord
                        break
                else:
                    next_focus_coord = self.terminal.output_area.random_coord()
                swarm_areas.append(next_focus_coord)
                swarm_area_coordinate_map[last_focus_coord] = geometry.find_coords_in_circle(
                    last_focus_coord,
                    max(min(self.terminal.output_area.right, self.terminal.output_area.top) // 6, 1) * 2,
                )
                last_focus_coord = next_focus_coord

            # assign characters waypoints for swarm areas and inner waypoints within the swarm areas
            for character in swarm:
                swarm_area_count = 0
                character.motion.set_coordinate(swarm_spawn)
                flash_scn = character.animation.new_scene(sync=animation.SyncMetric.DISTANCE)
                for step in swarm_gradient_mirror:
                    flash_scn.add_frame(character.input_symbol, 1, color=step)
                for _, swarm_area_coords in swarm_area_coordinate_map.items():
                    swarm_area_name = f"{swarm_area_count}_swarm_area"
                    swarm_area_count += 1
                    origin_path = character.motion.new_path(id=swarm_area_name, speed=0.25, ease=easing.out_sine)
                    origin_path.new_waypoint(random.choice(swarm_area_coords), id=swarm_area_name)
                    character.event_handler.register_event(
                        EventHandler.Event.PATH_ACTIVATED, origin_path, EventHandler.Action.ACTIVATE_SCENE, flash_scn
                    )
                    character.event_handler.register_event(
                        EventHandler.Event.PATH_ACTIVATED, origin_path, EventHandler.Action.SET_LAYER, 1
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
                            id=str(len(character.motion.paths)), speed=0.1, ease=easing.in_out_sine
                        )
                        inner_path.new_waypoint(next_coord, id=str(len(character.motion.paths)))
                # create landing waypoint and scene
                input_path = character.motion.new_path(speed=0.3, ease=easing.in_out_quad)
                input_path.new_waypoint(character.input_coord)
                input_scn = character.animation.new_scene()
                for step in graphics.Gradient(
                    self.config.flash_color, self._character_final_color_map[character], steps=10
                ):
                    input_scn.add_frame(character.input_symbol, 3, color=step)
                character.event_handler.register_event(
                    EventHandler.Event.PATH_COMPLETE, input_path, EventHandler.Action.ACTIVATE_SCENE, input_scn
                )
                character.event_handler.register_event(
                    EventHandler.Event.PATH_COMPLETE, input_path, EventHandler.Action.SET_LAYER, 0
                )
                character.event_handler.register_event(
                    EventHandler.Event.PATH_ACTIVATED, input_path, EventHandler.Action.ACTIVATE_SCENE, flash_scn
                )
                character.motion.chain_paths(list(character.motion.paths.values()))
        self._built = True

    @property
    def built(self) -> bool:
        """Returns True if the effect has been built."""
        return self._built

    def __iter__(self) -> Iterator[str]:
        """Runs the effect."""
        if not self._built:
            self.build()
        call_next = True
        active_swarm_area = "0_swarm_area"
        while self._swarms or self._active_chars:
            if self._swarms and call_next:
                call_next = False
                current_swarm = self._swarms.pop()
                active_swarm_area = "0_swarm_area"
                for character in current_swarm:
                    character.motion.activate_path(character.motion.query_path("0_swarm_area"))
                    self.terminal.set_character_visibility(character, True)
                    self._active_chars.append(character)
            yield self.terminal.get_formatted_output_string()
            self._animate_chars()
            if len(self._active_chars) < len(current_swarm):
                call_next = True
            if current_swarm:
                for character in current_swarm:
                    if (
                        character.motion.active_path
                        and character.motion.active_path.path_id != active_swarm_area
                        and "swarm_area" in character.motion.active_path.path_id
                        and int(character.motion.active_path.path_id[0]) > int(active_swarm_area[0])
                    ):
                        active_swarm_area = character.motion.active_path.path_id
                        for other in current_swarm:
                            if other is not character and random.random() < self.config.swarm_coordination:
                                other.motion.activate_path(other.motion.paths[active_swarm_area])
                        break

            self._active_chars = [character for character in self._active_chars if character.is_active]
        self._built = False

    def _animate_chars(self) -> None:
        """Animates the characters by calling the tick method."""
        for character in self._active_chars:
            character.tick()
