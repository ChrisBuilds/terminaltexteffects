"""Launches characters up the screen where they explode like fireworks and fall into place.

Classes:
    Fireworks: Characters explode like fireworks and fall into place.
    FireworksConfig: Configuration for the Fireworks effect.
    FireworksIterator: Iterates over the effect. Does not normally need to be called directly.
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
    return Fireworks, FireworksConfig


@argclass(
    name="fireworks",
    help="Characters launch and explode like fireworks and fall into place.",
    description="fireworks | Characters explode like fireworks and fall into place.",
    epilog=(
        "Example: terminaltexteffects fireworks --firework-colors 88F7E2 44D492 F5EB67 FFA15C FA233E "
        "--firework-symbol o --firework-volume 0.02 --final-gradient-stops 8A008A 00D1FF FFFFFF "
        "--final-gradient-steps 12 --launch-delay 60 --explode-distance 0.1 --explode-anywhere"
    ),
)
@dataclass
class FireworksConfig(ArgsDataClass):
    """Configuration for the Fireworks effect.

    Attributes:
        explode_anywhere (bool): If set, fireworks explode anywhere in the canvas. Otherwise, fireworks explode
            above highest settled row of text.
        firework_colors (tuple[Color, ...]): Tuple of colors from which firework colors will be randomly selected.
        firework_symbol (str): Symbol to use for the firework shell.
        firework_volume (float): Percent of total characters in each firework shell. Valid values are 0 < n <= 1.
        launch_delay (int): Number of frames to wait between launching each firework shell. +/- 0-50 percent
            randomness is applied to this value. Valid values are n >= 0.
        explode_distance (float): Maximum distance from the firework shell origin to the explode waypoint as a
            percentage of the total canvas width. Valid values are 0 < n <= 1.
        final_gradient_stops (tuple[Color, ...]): Tuple of colors for the final color gradient. If only one color
            is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Tuple of the number of gradient steps to use. More steps will
            create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient.

    """

    explode_anywhere: bool = ArgField(
        cmd_name="--explode-anywhere",
        action="store_true",
        default=False,
        help="If set, fireworks explode anywhere in the canvas. Otherwise, fireworks explode above highest settled "
        "row of text.",
    )  # type: ignore[assignment]
    (
        "bool : If set, fireworks explode anywhere in the canvas. Otherwise, fireworks explode above highest "
        "settled row of text."
    )

    firework_colors: tuple[Color, ...] = ArgField(
        cmd_name="--firework-colors",
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(Color("88F7E2"), Color("44D492"), Color("F5EB67"), Color("FFA15C"), Color("FA233E")),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated list of colors from which firework colors will be randomly selected.",
    )  # type: ignore[assignment]
    "tuple[Color, ...] : Tuple of colors from which firework colors will be randomly selected."

    firework_symbol: str = ArgField(
        cmd_name="--firework-symbol",
        type_parser=argvalidators.Symbol.type_parser,
        default="o",
        metavar=argvalidators.Symbol.METAVAR,
        help="Symbol to use for the firework shell.",
    )  # type: ignore[assignment]
    "str : Symbol to use for the firework shell."

    firework_volume: float = ArgField(
        cmd_name="--firework-volume",
        type_parser=argvalidators.NonNegativeRatio.type_parser,
        default=0.02,
        metavar=argvalidators.NonNegativeRatio.METAVAR,
        help="Percent of total characters in each firework shell.",
    )  # type: ignore[assignment]
    "float : Percent of total characters in each firework shell."

    launch_delay: int = ArgField(
        cmd_name="--launch-delay",
        type_parser=argvalidators.NonNegativeInt.type_parser,
        default=60,
        metavar=argvalidators.NonNegativeInt.METAVAR,
        help="Number of frames to wait between launching each firework shell. +/- 0-50 percent randomness is "
        "applied to this value.",
    )  # type: ignore[assignment]
    (
        "int : Number of frames to wait between launching each firework shell. +/- 0-50 percent randomness is "
        "applied to this value."
    )

    explode_distance: float = ArgField(
        cmd_name="--explode-distance",
        default=0.1,
        type_parser=argvalidators.NonNegativeRatio.type_parser,
        metavar=argvalidators.NonNegativeRatio.METAVAR,
        help="Maximum distance from the firework shell origin to the explode waypoint as a percentage of the "
        "total canvas width.",
    )  # type: ignore[assignment]
    (
        "float : Maximum distance from the firework shell origin to the explode waypoint as a percentage of "
        "the total canvas width."
    )

    final_gradient_stops: tuple[Color, ...] = ArgField(
        cmd_name="--final-gradient-stops",
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(Color("8A008A"), Color("00D1FF"), Color("FFFFFF")),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied across the canvas). "
        "If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    (
        "tuple[Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the "
        "characters will be displayed in that color."
    )

    final_gradient_steps: tuple[int, ...] | int = ArgField(
        cmd_name="--final-gradient-steps",
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
    def get_effect_class(cls) -> type[Fireworks]:
        """Get the effect class associated with this configuration."""
        return Fireworks


class FireworksIterator(BaseEffectIterator[FireworksConfig]):
    """Iterator for the Fireworks effect."""

    def __init__(self, effect: Fireworks) -> None:
        """Initialize the Fireworks effect iterator.

        Args:
            effect (Fireworks): The Fireworks effect to iterate over.

        """
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.shells: list[list[EffectCharacter]] = []
        self.firework_volume = max(1, round(self.config.firework_volume * len(self.terminal._input_characters)))
        self.explode_distance = max(1, round(self.terminal.canvas.right * self.config.explode_distance))
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self.launch_delay: int = 0
        self.build()

    def prepare_waypoints(self) -> None:
        """Prepare the waypoints for the characters."""
        firework_shell: list[EffectCharacter] = []
        for character in self.terminal.get_characters():
            if len(firework_shell) == self.firework_volume or not firework_shell:
                origin_x = random.randrange(0, self.terminal.canvas.right)
                self.shells.append(firework_shell)
                firework_shell = []
                min_row = character.input_coord.row if not self.config.explode_anywhere else self.terminal.canvas.bottom
                origin_y = random.randrange(min_row, self.terminal.canvas.top + 1)
                origin_coord = Coord(origin_x, origin_y)
                explode_waypoint_coords = geometry.find_coords_in_circle(origin_coord, self.explode_distance)
            character.motion.set_coordinate(Coord(origin_x, self.terminal.canvas.bottom))  # type: ignore[attr-defined]
            apex_path = character.motion.new_path(path_id="apex_pth", speed=0.2, ease=easing.out_expo, layer=2)
            apex_wpt = apex_path.new_waypoint(origin_coord)  # type: ignore[attr-defined]
            explode_path = character.motion.new_path(speed=random.uniform(0.09, 0.2), ease=easing.out_circ, layer=2)
            explode_wpt = explode_path.new_waypoint(random.choice(explode_waypoint_coords))  # type: ignore[attr-defined]

            bloom_control_point = geometry.find_coord_at_distance(
                apex_wpt.coord,
                explode_wpt.coord,
                self.explode_distance // 2,
            )
            bloom_wpt = explode_path.new_waypoint(
                Coord(bloom_control_point.column, max(1, bloom_control_point.row - 7)),
                bezier_control=bloom_control_point,
            )
            input_path = character.motion.new_path(path_id="input_pth", speed=0.3, ease=easing.in_out_quart, layer=2)
            input_control_point = Coord(bloom_wpt.coord.column, 1)
            input_path.new_waypoint(character.input_coord, bezier_control=input_control_point)
            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE,
                apex_path,
                EventHandler.Action.ACTIVATE_PATH,
                explode_path,
            )
            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE,
                explode_path,
                EventHandler.Action.ACTIVATE_PATH,
                input_path,
            )
            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE,
                input_path,
                EventHandler.Action.SET_LAYER,
                0,
            )

            character.motion.activate_path(apex_path)

            firework_shell.append(character)
        if firework_shell:
            self.shells.append(firework_shell)

    def prepare_scenes(self) -> None:
        """Prepare the scenes for the characters."""
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
        for firework_shell in self.shells:
            shell_color = random.choice(self.config.firework_colors)
            shell_gradient = Gradient(shell_color, Color("FFFFFF"), shell_color, steps=5)
            for character in firework_shell:
                # launch scene
                launch_scn = character.animation.new_scene()
                launch_scn.add_frame(self.config.firework_symbol, 2, colors=ColorPair(fg=shell_color))
                launch_scn.add_frame(self.config.firework_symbol, 1, colors=ColorPair(fg="FFFFFF"))
                launch_scn.is_looping = True
                # bloom scene
                bloom_scn = character.animation.new_scene(sync=Scene.SyncMetric.STEP)
                for color in shell_gradient:
                    bloom_scn.add_frame(character.input_symbol, 3, colors=ColorPair(fg=color))
                # fall scene
                fall_scn = character.animation.new_scene()
                fall_gradient = Gradient(shell_color, self.character_final_color_map[character], steps=15)
                fall_scn.apply_gradient_to_symbols(character.input_symbol, 15, fg_gradient=fall_gradient)
                character.animation.activate_scene(launch_scn)
                character.event_handler.register_event(
                    EventHandler.Event.PATH_COMPLETE,
                    character.motion.query_path("apex_pth"),
                    EventHandler.Action.ACTIVATE_SCENE,
                    bloom_scn,
                )
                character.event_handler.register_event(
                    EventHandler.Event.PATH_ACTIVATED,
                    character.motion.query_path("input_pth"),
                    EventHandler.Action.ACTIVATE_SCENE,
                    fall_scn,
                )

    def build(self) -> None:
        """Build the Fireworks effect."""
        self.prepare_waypoints()
        self.prepare_scenes()

    def __next__(self) -> str:
        """Return the next frame in the animation."""
        if self.shells or self.active_characters:
            if self.shells and self.launch_delay <= 0:
                next_group = self.shells.pop()
                for character in next_group:
                    self.terminal.set_character_visibility(character, is_visible=True)
                    self.active_characters.add(character)
                self.launch_delay = int(self.config.launch_delay * random.uniform(0.5, 1.5))
            self.launch_delay -= 1
            self.update()
            return self.frame

        raise StopIteration


class Fireworks(BaseEffect[FireworksConfig]):
    """Launches characters up the screen where they explode like fireworks and fall into place.

    Attributes:
        effect_config (FireworksConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.

    """

    @property
    def _config_cls(self) -> type[FireworksConfig]:
        return FireworksConfig

    @property
    def _iterator_cls(self) -> type[FireworksIterator]:
        return FireworksIterator
