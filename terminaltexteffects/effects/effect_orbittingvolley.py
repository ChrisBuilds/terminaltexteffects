import typing
from collections.abc import Iterator
from dataclasses import dataclass
from itertools import cycle

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils import easing, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.terminal import Terminal, TerminalConfig


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return OrbittingVolleyEffect, EffectConfig


@argclass(
    name="orbittingvolley",
    help="Four launchers orbit the output area firing volleys of characters inward to build the input text from the center out.",
    description="orbittingvolley | Four launchers orbit the output area firing volleys of characters inward to build the input text from the center out.",
    epilog=f"""{arg_validators.EASING_EPILOG}
    
Example: terminaltexteffects orbittingvolley --top-launcher-symbol █ --right-launcher-symbol █ --bottom-launcher-symbol █ --left-launcher-symbol █ --final-gradient-stops FFA15C 44D492 --final-gradient-steps 12 --launcher-movement-speed 0.5 --character-movement-speed 1 --volley-size 0.03 --launch-delay 50 --character-easing OUT_SINE""",
)
@dataclass
class EffectConfig(ArgsDataClass):
    """Configuration for the OrbittingVolley effect.

    Attributes:
        top_launcher_symbol (str): Symbol for the top launcher.
        right_launcher_symbol (str): Symbol for the right launcher.
        bottom_launcher_symbol (str): Symbol for the bottom launcher.
        left_launcher_symbol (str): Symbol for the left launcher.
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the gradient for the final color.
        launcher_movement_speed (float): Orbitting speed of the launchers.
        character_movement_speed (float): Speed of the launched characters.
        volley_size (float): Percent of total input characters each launcher will fire per volley. Lower limit of one character.
        launch_delay (int): Number of animation ticks to wait between volleys of characters.
        character_easing (typing.Callable): Easing function to use for launched character movement."""

    top_launcher_symbol: str = ArgField(
        cmd_name="--top-launcher-symbol",
        type_parser=arg_validators.Symbol.type_parser,
        default="█",
        metavar=arg_validators.Symbol.METAVAR,
        help="Symbol for the top launcher.",
    )  # type: ignore[assignment]
    "str : Symbol for the top launcher."

    right_launcher_symbol: str = ArgField(
        cmd_name="--right-launcher-symbol",
        type_parser=arg_validators.Symbol.type_parser,
        default="█",
        metavar=arg_validators.Symbol.METAVAR,
        help="Symbol for the right launcher.",
    )  # type: ignore[assignment]
    "str : Symbol for the right launcher."

    bottom_launcher_symbol: str = ArgField(
        cmd_name="--bottom-launcher-symbol",
        type_parser=arg_validators.Symbol.type_parser,
        default="█",
        metavar=arg_validators.Symbol.METAVAR,
        help="Symbol for the bottom launcher.",
    )  # type: ignore[assignment]
    "str : Symbol for the bottom launcher."

    left_launcher_symbol: str = ArgField(
        cmd_name="--left-launcher-symbol",
        type_parser=arg_validators.Symbol.type_parser,
        default="█",
        metavar=arg_validators.Symbol.METAVAR,
        help="Symbol for the left launcher.",
    )  # type: ignore[assignment]
    "str : Symbol for the left launcher."

    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name="--final-gradient-stops",
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("FFA15C", "44D492"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[graphics.Color, ...] : Tuple of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--final-gradient-steps",
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
        default=graphics.Gradient.Direction.CENTER,
        metavar=arg_validators.GradientDirection.METAVAR,
        help="Direction of the gradient for the final color.",
    )  # type: ignore[assignment]
    "graphics.Gradient.Direction : Direction of the gradient for the final color."

    launcher_movement_speed: float = ArgField(
        cmd_name="--launcher-movement-speed",
        type_parser=arg_validators.PositiveFloat.type_parser,
        default=0.5,
        metavar=arg_validators.PositiveFloat.METAVAR,
        help="Orbitting speed of the launchers.",
    )  # type: ignore[assignment]
    "float : Orbitting speed of the launchers."

    character_movement_speed: float = ArgField(
        cmd_name="--character-movement-speed",
        type_parser=arg_validators.PositiveFloat.type_parser,
        default=1,
        metavar=arg_validators.PositiveFloat.METAVAR,
        help="Speed of the launched characters.",
    )  # type: ignore[assignment]
    "float : Speed of the launched characters."

    volley_size: float = ArgField(
        cmd_name="--volley-size",
        type_parser=arg_validators.Ratio.type_parser,
        default=0.03,
        metavar=arg_validators.Ratio.METAVAR,
        help="Percent of total input characters each launcher will fire per volley. Lower limit of one character.",
    )  # type: ignore[assignment]
    "float : Percent of total input characters each launcher will fire per volley. Lower limit of one character."

    launch_delay: int = ArgField(
        cmd_name="--launch-delay",
        type_parser=arg_validators.NonNegativeInt.type_parser,
        default=50,
        metavar=arg_validators.NonNegativeInt.METAVAR,
        help="Number of animation ticks to wait between volleys of characters.",
    )  # type: ignore[assignment]
    "int : Number of animation ticks to wait between volleys of characters."

    character_easing: easing.EasingFunction = ArgField(
        cmd_name=["--character-easing"],
        default=easing.out_sine,
        type_parser=arg_validators.Ease.type_parser,
        metavar=arg_validators.Ease.METAVAR,
        help="Easing function to use for launched character movement.",
    )  # type: ignore[assignment]
    "easing.EasingFunction : Easing function to use for launched character movement."

    @classmethod
    def get_effect_class(cls):
        return OrbittingVolleyEffect


class Launcher:
    def __init__(self, terminal: Terminal, args: EffectConfig, starting_edge_coord: Coord, symbol: str):
        self.terminal = terminal
        self.args = args
        self.character = self.terminal.add_character(symbol, starting_edge_coord)
        self.magazine: list[EffectCharacter] = []

    def build_paths(self) -> None:
        waypoints = [
            Coord(self.terminal.output_area.left, self.terminal.output_area.top),
            Coord(self.terminal.output_area.right, self.terminal.output_area.top),
        ]

        waypoint_start_index = waypoints.index(self.character.input_coord)
        perimeter_path = self.character.motion.new_path(
            speed=self.args.launcher_movement_speed, id="perimeter", layer=2
        )
        for waypoint in waypoints[waypoint_start_index:] + waypoints[:waypoint_start_index]:
            perimeter_path.new_waypoint(waypoint)

    def launch(self) -> EffectCharacter | None:
        if self.magazine:
            next_char = self.magazine.pop(0)
            next_char.motion.set_coordinate(self.character.motion.current_coord)
            input_path = next_char.motion.query_path("input_path")
            next_char.motion.activate_path(input_path)
            self.terminal.set_character_visibility(next_char, True)
        else:
            next_char = None
        return next_char


class OrbittingVolleyEffect:
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
        self.final_gradient = graphics.Gradient(
            *self.config.final_gradient_stops, steps=self.config.final_gradient_steps
        )
        self._character_final_color_map: dict[EffectCharacter, graphics.Color] = {}
        self.final_gradient_coordinate_map: dict[Coord, graphics.Color] = (
            self.final_gradient.build_coordinate_color_mapping(
                self.terminal.output_area.top, self.terminal.output_area.right, self.config.final_gradient_direction
            )
        )

    def build(self) -> None:
        self._pending_chars.clear()
        self._active_chars.clear()
        self._character_final_color_map.clear()
        for character in self.terminal.get_characters():
            self._character_final_color_map[character] = self.final_gradient_coordinate_map[character.input_coord]
            input_path = character.motion.new_path(
                speed=self.config.character_movement_speed, ease=self.config.character_easing, id="input_path", layer=1
            )
            input_path.new_waypoint(character.input_coord)
            character.animation.set_appearance(character.input_symbol, self._character_final_color_map[character])

        self._built = True

    def set_launcher_coordinates(self, parent: Launcher, child: Launcher) -> None:
        """Sets the coordinates for the child launcher."""
        parent_progress = parent.character.motion.current_coord.column / self.terminal.output_area.right
        if child.character.input_coord == Coord(self.terminal.output_area.right, self.terminal.output_area.top):
            child_row = self.terminal.output_area.top - int((self.terminal.output_area.top * parent_progress))
            child.character.motion.set_coordinate(Coord(self.terminal.output_area.right, max(1, child_row)))
        elif child.character.input_coord == Coord(self.terminal.output_area.right, self.terminal.output_area.bottom):
            child_column = self.terminal.output_area.right - int((self.terminal.output_area.right * parent_progress))
            child.character.motion.set_coordinate(Coord(max(1, child_column), self.terminal.output_area.bottom))
        elif child.character.input_coord == Coord(self.terminal.output_area.left, self.terminal.output_area.bottom):
            child_row = self.terminal.output_area.bottom + int((self.terminal.output_area.top * parent_progress))
            child.character.motion.set_coordinate(
                Coord(self.terminal.output_area.left, min(self.terminal.output_area.top, child_row))
            )
        color = self.final_gradient_coordinate_map[child.character.motion.current_coord]
        child.character.animation.set_appearance(child.character.input_symbol, color)

    @property
    def built(self) -> bool:
        """Returns True if the effect has been built."""
        return self._built

    def __iter__(self) -> Iterator[str]:
        """Runs the effect."""
        if not self._built:
            self.build()
        launchers: list[Launcher] = []
        for coord, symbol in (
            (
                Coord(self.terminal.output_area.left, self.terminal.output_area.top),
                self.config.top_launcher_symbol,
            ),
            (
                Coord(self.terminal.output_area.right, self.terminal.output_area.top),
                self.config.right_launcher_symbol,
            ),
            (
                Coord(self.terminal.output_area.right, self.terminal.output_area.bottom),
                self.config.bottom_launcher_symbol,
            ),
            (
                Coord(self.terminal.output_area.left, self.terminal.output_area.bottom),
                self.config.left_launcher_symbol,
            ),
        ):
            launcher = Launcher(self.terminal, self.config, coord, symbol)
            launcher.character.layer = 2
            self.terminal.set_character_visibility(launcher.character, True)
            self._active_chars.append(launcher.character)
            launchers.append(launcher)
        main_launcher = launchers[0]
        main_launcher.character.animation.set_appearance(
            main_launcher.character.input_symbol, self.final_gradient.spectrum[-1]
        )
        main_launcher.build_paths()
        main_launcher.character.motion.activate_path(main_launcher.character.motion.query_path("perimeter"))
        sorted_chars = []
        for char_list in self.terminal.get_characters_grouped(Terminal.CharacterGroup.CENTER_TO_OUTSIDE_DIAMONDS):
            sorted_chars.extend(char_list)
        for launcher, character in zip(cycle(launchers), sorted_chars):
            launcher.magazine.append(character)
        delay = 0
        while any([launcher.magazine for launcher in launchers]) or len(self._active_chars) > 1:
            if main_launcher.character.motion.active_path is None:
                perimeter_path = main_launcher.character.motion.query_path("perimeter")
                main_launcher.character.motion.set_coordinate(perimeter_path.waypoints[0].coord)
                main_launcher.character.motion.activate_path(perimeter_path)
                self._active_chars.append(main_launcher.character)
            main_launcher.character.animation.set_appearance(
                self.config.top_launcher_symbol,
                self.final_gradient_coordinate_map[main_launcher.character.motion.current_coord],
            )
            for launcher in launchers[1:]:
                self.set_launcher_coordinates(main_launcher, launcher)
            if not delay:
                for launcher in launchers:
                    characters_to_launch = max(
                        int((self.config.volley_size * len(self.terminal._input_characters)) / 4), 1
                    )
                    for _ in range(characters_to_launch):
                        next_char = launcher.launch()
                        if next_char:
                            self._active_chars.append(next_char)
                delay = self.config.launch_delay
            else:
                delay -= 1

            yield self.terminal.get_formatted_output_string()
            self._animate_chars()
            self._active_chars = [character for character in self._active_chars if character.is_active]
        for launcher in launchers:
            self.terminal.set_character_visibility(launcher.character, False)
            yield self.terminal.get_formatted_output_string()
        self._built = False

    def _animate_chars(self) -> None:
        """Animates the characters by calling the tick method on all active characters."""
        for character in self._active_chars:
            character.tick()
