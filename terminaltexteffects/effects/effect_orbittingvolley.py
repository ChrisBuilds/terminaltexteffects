"""Four launchers orbit the canvas firing volleys of characters inward to build the input text from the center out.

Classes:
    OrbittingVolley: Four launchers orbit the canvas firing volleys of characters inward to build the input text from
        the center out.
    OrbittingVolleyConfig: Configuration for the OrbittingVolley effect.
    OrbittingVolleyIterator: Effect iterator for OrbittingVolley. Does not normally need to be called directly.
"""

from __future__ import annotations

import typing
from dataclasses import dataclass
from itertools import cycle

from terminaltexteffects import Color, ColorPair, Coord, EffectCharacter, EventHandler, Gradient, Terminal, easing
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argvalidators
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    """Get the effect class and its configuration class."""
    return OrbittingVolley, OrbittingVolleyConfig


@argclass(
    name="orbittingvolley",
    help=(
        "Four launchers orbit the canvas firing volleys of characters inward to build the input text "
        "from the center out."
    ),
    description=(
        "orbittingvolley | Four launchers orbit the canvas firing volleys of characters inward to build "
        "the input text from the center out."
    ),
    epilog=(
        f"{argvalidators.EASING_EPILOG} Example: terminaltexteffects orbittingvolley --top-launcher-symbol █ "
        "--right-launcher-symbol █ --bottom-launcher-symbol █ --left-launcher-symbol █ "
        "--final-gradient-stops FFA15C 44D492 --final-gradient-steps 12 --launcher-movement-speed 0.5 "
        "--character-movement-speed 1 --volley-size 0.03 --launch-delay 50 --character-easing OUT_SINE"
    ),
)
@dataclass
class OrbittingVolleyConfig(ArgsDataClass):
    """Configuration for the OrbittingVolley effect.

    Attributes:
        top_launcher_symbol (str): Symbol for the top launcher.
        right_launcher_symbol (str): Symbol for the right launcher.
        bottom_launcher_symbol (str): Symbol for the bottom launcher.
        left_launcher_symbol (str): Symbol for the left launcher.
        launcher_movement_speed (float): Orbitting speed of the launchers. Valid values are n > 0.
        character_movement_speed (float): Speed of the launched characters. Valid values are n > 0.
        volley_size (float): Percent of total input characters each launcher will fire per volley. Lower limit of "
            "one character. Valid values are 0 < n <= 1.
        launch_delay (int): Number of animation ticks to wait between volleys of characters. Valid values are n >= 0.
        character_easing (easing.EasingFunction): Easing function to use for launched character movement.
        final_gradient_stops (tuple[Color, ...]): Tuple of colors for the final color gradient. If only one "
            "color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Tuple of the number of gradient steps to use. More steps "
            "will create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient.

    """

    top_launcher_symbol: str = ArgField(
        cmd_name="--top-launcher-symbol",
        type_parser=argvalidators.Symbol.type_parser,
        default="█",
        metavar=argvalidators.Symbol.METAVAR,
        help="Symbol for the top launcher.",
    )  # type: ignore[assignment]
    "str : Symbol for the top launcher."

    right_launcher_symbol: str = ArgField(
        cmd_name="--right-launcher-symbol",
        type_parser=argvalidators.Symbol.type_parser,
        default="█",
        metavar=argvalidators.Symbol.METAVAR,
        help="Symbol for the right launcher.",
    )  # type: ignore[assignment]
    "str : Symbol for the right launcher."

    bottom_launcher_symbol: str = ArgField(
        cmd_name="--bottom-launcher-symbol",
        type_parser=argvalidators.Symbol.type_parser,
        default="█",
        metavar=argvalidators.Symbol.METAVAR,
        help="Symbol for the bottom launcher.",
    )  # type: ignore[assignment]
    "str : Symbol for the bottom launcher."

    left_launcher_symbol: str = ArgField(
        cmd_name="--left-launcher-symbol",
        type_parser=argvalidators.Symbol.type_parser,
        default="█",
        metavar=argvalidators.Symbol.METAVAR,
        help="Symbol for the left launcher.",
    )  # type: ignore[assignment]
    "str : Symbol for the left launcher."

    launcher_movement_speed: float = ArgField(
        cmd_name="--launcher-movement-speed",
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=0.5,
        metavar=argvalidators.PositiveFloat.METAVAR,
        help="Orbitting speed of the launchers.",
    )  # type: ignore[assignment]
    "float : Orbitting speed of the launchers."

    character_movement_speed: float = ArgField(
        cmd_name="--character-movement-speed",
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=1,
        metavar=argvalidators.PositiveFloat.METAVAR,
        help="Speed of the launched characters.",
    )  # type: ignore[assignment]
    "float : Speed of the launched characters."

    volley_size: float = ArgField(
        cmd_name="--volley-size",
        type_parser=argvalidators.NonNegativeRatio.type_parser,
        default=0.03,
        metavar=argvalidators.NonNegativeRatio.METAVAR,
        help="Percent of total input characters each launcher will fire per volley. Lower limit of one character.",
    )  # type: ignore[assignment]
    "float : Percent of total input characters each launcher will fire per volley. Lower limit of one character."

    launch_delay: int = ArgField(
        cmd_name="--launch-delay",
        type_parser=argvalidators.NonNegativeInt.type_parser,
        default=50,
        metavar=argvalidators.NonNegativeInt.METAVAR,
        help="Number of animation ticks to wait between volleys of characters.",
    )  # type: ignore[assignment]
    "int : Number of animation ticks to wait between volleys of characters."

    character_easing: easing.EasingFunction = ArgField(
        cmd_name=["--character-easing"],
        default=easing.out_sine,
        type_parser=argvalidators.Ease.type_parser,
        metavar=argvalidators.Ease.METAVAR,
        help="Easing function to use for launched character movement.",
    )  # type: ignore[assignment]
    "easing.EasingFunction : Easing function to use for launched character movement."

    final_gradient_stops: tuple[Color, ...] = ArgField(
        cmd_name="--final-gradient-stops",
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(Color("FFA15C"), Color("44D492")),
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
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create "
        "a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    (
        "tuple[int, ...] | int : Int or Tuple of ints for the number of gradient steps to use. More steps will "
        "create a smoother and longer gradient animation."
    )

    final_gradient_direction: Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=argvalidators.GradientDirection.type_parser,
        default=Gradient.Direction.RADIAL,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]
    "Gradient.Direction : Direction of the final gradient."

    @classmethod
    def get_effect_class(cls) -> type[OrbittingVolley]:
        """Get the effect class associated with this configuration."""
        return OrbittingVolley


class OrbittingVolleyIterator(BaseEffectIterator[OrbittingVolleyConfig]):
    """Effect iterator for OrbittingVolley."""

    class Launcher:
        """A launcher that fires characters inward to build the input text from the center out."""

        def __init__(
            self,
            terminal: Terminal,
            args: OrbittingVolleyConfig,
            starting_edge_coord: Coord,
            symbol: str,
        ) -> None:
            """Initialize the launcher.

            Args:
                terminal (Terminal): The effect Terminal.
                args (OrbittingVolleyConfig): Configuration for the effect.
                starting_edge_coord (Coord): The starting coordinate for the launcher.
                symbol (str): The symbol to use for the launcher.

            """
            self.terminal = terminal
            self.args = args
            self.character = self.terminal.add_character(symbol, starting_edge_coord)
            self.magazine: list[EffectCharacter] = []

        def build_paths(self) -> None:
            """Build the paths for the launcher."""
            waypoints = [
                Coord(self.terminal.canvas.left, self.terminal.canvas.top),
                Coord(self.terminal.canvas.right, self.terminal.canvas.top),
            ]

            waypoint_start_index = waypoints.index(self.character.input_coord)
            perimeter_path = self.character.motion.new_path(
                speed=self.args.launcher_movement_speed,
                path_id="perimeter",
                layer=2,
            )
            for waypoint in waypoints[waypoint_start_index:] + waypoints[:waypoint_start_index]:
                perimeter_path.new_waypoint(waypoint)

        def launch(self) -> EffectCharacter | None:
            """Launch a character from the magazine."""
            if self.magazine:
                next_char = self.magazine.pop(0)
                next_char.motion.set_coordinate(self.character.motion.current_coord)
                input_path = next_char.motion.query_path("input_path")
                next_char.motion.activate_path(input_path)
                self.terminal.set_character_visibility(next_char, is_visible=True)
            else:
                next_char = None
            return next_char

    def __init__(self, effect: OrbittingVolley) -> None:
        """Initialize the effect iterator."""
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.final_gradient = Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self.final_gradient_coordinate_map: dict[Coord, Color] = self.final_gradient.build_coordinate_color_mapping(
            self.terminal.canvas.text_bottom,
            self.terminal.canvas.text_top,
            self.terminal.canvas.text_left,
            self.terminal.canvas.text_right,
            self.config.final_gradient_direction,
        )
        self.launcher_gradient_coordinate_map: dict[Coord, Color] = self.final_gradient.build_coordinate_color_mapping(
            self.terminal.canvas.bottom,
            self.terminal.canvas.top,
            self.terminal.canvas.left,
            self.terminal.canvas.right,
            self.config.final_gradient_direction,
        )
        self.complete = False
        self.build()

    def build(self) -> None:
        """Build the initial state of the effect."""
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = self.final_gradient_coordinate_map[character.input_coord]
            input_path = character.motion.new_path(
                speed=self.config.character_movement_speed,
                ease=self.config.character_easing,
                path_id="input_path",
                layer=1,
            )
            input_path.new_waypoint(character.input_coord)
            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE,
                input_path,
                EventHandler.Action.SET_LAYER,
                0,
            )
            character.animation.set_appearance(
                character.input_symbol,
                ColorPair(fg=self.character_final_color_map[character]),
            )
        self._launchers: list[OrbittingVolleyIterator.Launcher] = []
        for coord, symbol in (
            (
                Coord(self.terminal.canvas.left, self.terminal.canvas.top),
                self.config.top_launcher_symbol,
            ),
            (
                Coord(self.terminal.canvas.right, self.terminal.canvas.top),
                self.config.right_launcher_symbol,
            ),
            (
                Coord(self.terminal.canvas.right, self.terminal.canvas.bottom),
                self.config.bottom_launcher_symbol,
            ),
            (
                Coord(self.terminal.canvas.left, self.terminal.canvas.bottom),
                self.config.left_launcher_symbol,
            ),
        ):
            launcher = OrbittingVolleyIterator.Launcher(self.terminal, self.config, coord, symbol)
            launcher.character.layer = 2
            self.terminal.set_character_visibility(launcher.character, is_visible=True)
            self.active_characters.add(launcher.character)
            self._launchers.append(launcher)
        self._main_launcher = self._launchers[0]
        self._main_launcher.character.animation.set_appearance(
            self._main_launcher.character.input_symbol,
            ColorPair(fg=self.final_gradient.spectrum[-1]),
        )
        self._main_launcher.build_paths()
        self._main_launcher.character.motion.activate_path(self._main_launcher.character.motion.query_path("perimeter"))
        self._sorted_chars = []
        for char_list in self.terminal.get_characters_grouped(Terminal.CharacterGroup.CENTER_TO_OUTSIDE_DIAMONDS):
            self._sorted_chars.extend(char_list)
        for launcher, character in zip(cycle(self._launchers), self._sorted_chars):
            launcher.magazine.append(character)
        self._delay = 0

    def _set_launcher_coordinates(self, parent: Launcher, child: Launcher) -> None:
        parent_progress = parent.character.motion.current_coord.column / self.terminal.canvas.right
        if child.character.input_coord == Coord(self.terminal.canvas.right, self.terminal.canvas.top):
            child_row = self.terminal.canvas.top - int(self.terminal.canvas.top * parent_progress)
            child.character.motion.set_coordinate(Coord(self.terminal.canvas.right, max(1, child_row)))
        elif child.character.input_coord == Coord(self.terminal.canvas.right, self.terminal.canvas.bottom):
            child_column = self.terminal.canvas.right - int(self.terminal.canvas.right * parent_progress)
            child.character.motion.set_coordinate(Coord(max(1, child_column), self.terminal.canvas.bottom))
        elif child.character.input_coord == Coord(self.terminal.canvas.left, self.terminal.canvas.bottom):
            child_row = self.terminal.canvas.bottom + int(self.terminal.canvas.top * parent_progress)
            child.character.motion.set_coordinate(
                Coord(self.terminal.canvas.left, min(self.terminal.canvas.top, child_row)),
            )
        color = self.launcher_gradient_coordinate_map[child.character.motion.current_coord]
        child.character.animation.set_appearance(child.character.input_symbol, ColorPair(fg=color))

    def __next__(self) -> str:
        """Return the next frame in the animation."""
        if any(launcher.magazine for launcher in self._launchers) or len(self.active_characters) > 1:
            if self._main_launcher.character.motion.active_path is None:
                perimeter_path = self._main_launcher.character.motion.query_path("perimeter")
                self._main_launcher.character.motion.set_coordinate(perimeter_path.waypoints[0].coord)
                self._main_launcher.character.motion.activate_path(perimeter_path)
                self.active_characters.add(self._main_launcher.character)
            self._main_launcher.character.animation.set_appearance(
                self.config.top_launcher_symbol,
                ColorPair(
                    fg=self.launcher_gradient_coordinate_map[self._main_launcher.character.motion.current_coord],
                ),
            )
            for launcher in self._launchers[1:]:
                self._set_launcher_coordinates(self._main_launcher, launcher)
            if not self._delay:
                for launcher in self._launchers:
                    characters_to_launch = max(
                        int((self.config.volley_size * len(self.terminal._input_characters)) / 4),
                        1,
                    )
                    for _ in range(characters_to_launch):
                        next_char = launcher.launch()
                        if next_char:
                            self.active_characters.add(next_char)
                self._delay = self.config.launch_delay
            else:
                self._delay -= 1

            self.update()
            return self.frame
        if not self.complete:
            self.complete = True
            for launcher in self._launchers:
                self.terminal.set_character_visibility(launcher.character, is_visible=False)
            return self.frame
        raise StopIteration


class OrbittingVolley(BaseEffect[OrbittingVolleyConfig]):
    """Four launchers orbit the canvas firing volleys of characters inward to build the input text from the center out.

    Attributes:
        effect_config (OrbittingVolleyConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.

    """

    @property
    def _config_cls(self) -> type[OrbittingVolleyConfig]:
        return OrbittingVolleyConfig

    @property
    def _iterator_cls(self) -> type[OrbittingVolleyIterator]:
        return OrbittingVolleyIterator
