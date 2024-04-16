import random
import typing
from collections.abc import Iterator
from dataclasses import dataclass

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.base_effect import BaseEffect
from terminaltexteffects.utils import easing, geometry, graphics, motion
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.terminal import Terminal, TerminalConfig


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return RingsEffect, EffectConfig


@argclass(
    name="rings",
    help="Characters are dispersed and form into spinning rings.",
    description="rings | Characters are dispersed and form into spinning rings.",
    epilog="""Example: terminaltexteffects rings --ring-colors ab48ff e7b2b2 fffebd --final-gradient-stops ab48ff e7b2b2 fffebd --final-gradient-steps 12 --ring-gap 0.1 --spin-duration 200 --spin-speed 0.25-1.0 --disperse-duration 200 --spin-disperse-cycles 3""",
)
@dataclass
class EffectConfig(ArgsDataClass):
    """Configurations for the RingsEffect.

    Attributes:
        ring_colors (tuple[graphics.Color, ...]): Tuple of colors for the rings.
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Number of gradient steps to use. More steps will create a smoother and longer gradient animation.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the gradient for the final color.
        ring_gap (float): Distance between rings as a percent of the smallest output area dimension.
        spin_duration (int): Number of animation steps for each cycle of the spin phase.
        spin_speed (tuple[float, float]): Range of speeds for the rotation of the rings. The speed is randomly selected from this range for each ring.
        disperse_duration (int): Number of animation steps spent in the dispersed state between spinning cycles.
        spin_disperse_cycles (int): Number of times the animation will cycles between spinning rings and dispersed characters.
    """

    ring_colors: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--ring-colors"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("ab48ff", "e7b2b2", "fffebd"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the rings.",
    )  # type: ignore[assignment]

    "tuple[graphics.Color] : Tuple of colors for the rings."

    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("ab48ff", "e7b2b2", "fffebd"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]

    "tuple[graphics.Color] : Tuple of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name=["--final-gradient-steps"],
        type_parser=arg_validators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]

    "tuple[int, ...] : Number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=arg_validators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.VERTICAL,
        metavar=arg_validators.GradientDirection.METAVAR,
        help="Direction of the gradient for the final color.",
    )  # type: ignore[assignment]

    "graphics.Gradient.Direction : Direction of the gradient for the final color."

    ring_gap: float = ArgField(
        cmd_name=["--ring-gap"],
        type_parser=arg_validators.PositiveFloat.type_parser,
        default=0.1,
        help="Distance between rings as a percent of the smallest output area dimension.",
    )  # type: ignore[assignment]

    "float : Distance between rings as a percent of the smallest output area dimension."
    spin_duration: int = ArgField(
        cmd_name=["--spin-duration"],
        type_parser=arg_validators.PositiveInt.type_parser,
        default=200,
        help="Number of animation steps for each cycle of the spin phase.",
    )  # type: ignore[assignment]

    "int : Number of animation steps for each cycle of the spin phase."

    spin_speed: tuple[float, float] = ArgField(
        cmd_name=["--spin-speed"],
        type_parser=arg_validators.PositiveFloatRange.type_parser,
        default=(0.25, 1.0),
        metavar=arg_validators.PositiveFloatRange.METAVAR,
        help="Range of speeds for the rotation of the rings. The speed is randomly selected from this range for each ring.",
    )  # type: ignore[assignment]

    "tuple[float, float] : Range of speeds for the rotation of the rings. The speed is randomly selected from this range for each ring."

    disperse_duration: int = ArgField(
        cmd_name=["--disperse-duration"],
        type_parser=arg_validators.PositiveInt.type_parser,
        default=200,
        help="Number of animation steps spent in the dispersed state between spinning cycles.",
    )  # type: ignore[assignment]

    "int : Number of animation steps spent in the dispersed state between spinning cycles."

    spin_disperse_cycles: int = ArgField(
        cmd_name=["--spin-disperse-cycles"],
        type_parser=arg_validators.PositiveInt.type_parser,
        default=3,
        help="Number of times the animation will cycles between spinning rings and dispersed characters.",
    )  # type: ignore[assignment]

    "int : Number of times the animation will cycles between spinning rings and dispersed characters."

    @classmethod
    def get_effect_class(cls):
        return RingsEffect


class _Ring:
    def __init__(
        self,
        config: EffectConfig,
        radius: int,
        origin: Coord,
        ring_coords: list[Coord],
        ring_gap: int,
        ring_color: graphics.Color,
        character_color_map: dict[EffectCharacter, graphics.Color],
    ):
        self.config = config
        self._built = False
        self.radius = radius
        self.origin: Coord = origin
        self.counter_clockwise_coords = ring_coords
        self.clockwise_coords = ring_coords[::-1]
        self.ring_gap = ring_gap
        self.ring_color = ring_color
        self.characters: list[EffectCharacter] = []
        self.character_last_ring_path: dict[EffectCharacter, motion.Path] = {}
        self.rotations = 0
        self.rotation_speed = random.uniform(self.config.spin_speed[0], self.config.spin_speed[1])
        self.character_color_map = character_color_map

    def add_character(self, character: EffectCharacter, clockwise: int) -> None:
        # make gradient scene
        gradient_scn = character.animation.new_scene(id="gradient")
        char_gradient = graphics.Gradient(self.character_color_map[character], self.ring_color, steps=8)
        gradient_scn.apply_gradient_to_symbols(char_gradient, character.input_symbol, 5)

        # make rotation waypoints
        ring_paths: list[motion.Path] = []
        character_starting_index = len(self.characters)
        if clockwise:
            coords = self.clockwise_coords
        else:
            coords = self.counter_clockwise_coords
        for coord in coords[character_starting_index:] + coords[:character_starting_index]:
            ring_path = character.motion.new_path(id=str(len(ring_paths)), speed=self.rotation_speed)
            ring_path.new_waypoint(coord, id=str(len(ring_path.waypoints)))
            ring_paths.append(ring_path)
        self.character_last_ring_path[character] = ring_paths[0]
        # make disperse scene
        disperse_scn = character.animation.new_scene(is_looping=False, id="disperse")
        disperse_gradient = graphics.Gradient(self.ring_color, self.character_color_map[character], steps=8)
        disperse_scn.apply_gradient_to_symbols(disperse_gradient, character.input_symbol, 16)
        character.motion.chain_paths(ring_paths, loop=True)
        self.characters.append(character)

    def make_disperse_waypoints(self, character: EffectCharacter, origin: Coord) -> motion.Path:
        """Make the Path for the character to follow when the ring disperses.

        Args:
            character (EffectCharacter): Character to disperse.
            origin (Coord): Origin coordinate for the character.

        Returns:
            motion.Path: the Path to follow.
        """
        disperse_coords = geometry.find_coords_in_rect(origin, self.ring_gap)
        character.motion.paths.pop("disperse", None)
        disperse_path = character.motion.new_path(speed=0.1, loop=True, id="disperse")
        for _ in range(5):
            disperse_path.new_waypoint(disperse_coords[random.randrange(0, len(disperse_coords))])
        return disperse_path

    def disperse(self) -> None:
        """Disperse the characters from the ring."""
        for character in self.characters:
            if character.motion.active_path is not None:
                self.character_last_ring_path[character] = character.motion.active_path
            else:
                self.character_last_ring_path[character] = character.motion.paths["0"]
            character.motion.activate_path(self.make_disperse_waypoints(character, character.motion.current_coord))
            character.animation.activate_scene(character.animation.query_scene("disperse"))

    def spin(self) -> None:
        for character in self.characters:
            condense_path = character.motion.new_path(speed=0.1)
            condense_path.new_waypoint(self.character_last_ring_path[character].waypoints[0].coord)
            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE,
                condense_path,
                EventHandler.Action.ACTIVATE_PATH,
                self.character_last_ring_path[character],
            )
            character.motion.activate_path(condense_path)
            character.animation.activate_scene(character.animation.query_scene("gradient"))


class RingsEffect(BaseEffect):
    """Effect that forms the characters into rings.

    Args:
        input_data (str): Input data to be displayed.
        effect_config (EffectConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.
    """

    def __init__(
        self,
        input_data: str,
        effect_config: EffectConfig = EffectConfig(),
        terminal_config: TerminalConfig = TerminalConfig(),
    ):
        self.terminal = Terminal(input_data, terminal_config)
        self.config = effect_config
        self._built = False
        self._pending_chars: list[EffectCharacter] = []
        self._active_chars: list[EffectCharacter] = []
        self._ring_chars: list[EffectCharacter] = []
        self._non_ring_chars: list[EffectCharacter] = []
        self._rings: dict[int, _Ring] = {}
        self.ring_gap = int(
            max(round(min(self.terminal.output_area.top, self.terminal.output_area.right) * self.config.ring_gap), 1)
        )
        self._character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def build(self) -> None:
        """Prepares the data for the effect by building rings and associated animations/waypoints."""
        self._pending_chars.clear()
        self._active_chars.clear()
        self._ring_chars.clear()
        self._non_ring_chars.clear()
        self._rings.clear()
        self._character_final_color_map.clear()
        self.ring_gap = int(
            max(round(min(self.terminal.output_area.top, self.terminal.output_area.right) * self.config.ring_gap), 1)
        )
        final_gradient = graphics.Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.config.final_gradient_direction
        )
        for character in self.terminal.get_characters():
            self._character_final_color_map[character] = final_gradient_mapping[character.input_coord]
            start_scn = character.animation.new_scene()
            start_scn.add_frame(character.input_symbol, 1, color=self._character_final_color_map[character])
            home_path = character.motion.new_path(speed=0.8, ease=easing.out_quad, id="home")
            home_path.new_waypoint(character.input_coord)
            character.animation.activate_scene(start_scn)
            self.terminal.set_character_visibility(character, True)
            self._pending_chars.append(character)

        random.shuffle(self._pending_chars)
        # make rings
        for radius in range(1, max(self.terminal.output_area.right, self.terminal.output_area.top), self.ring_gap):
            ring_coords = geometry.find_coords_on_circle(
                self.terminal.output_area.center, radius, 7 * radius, unique=True
            )
            # check if any part of the ring is in the output area, if not, stop creating rings
            if (
                len([coord for coord in ring_coords if self.terminal.output_area.coord_is_in_output_area(coord)])
                / len(ring_coords)
                < 0.25
            ):
                break

            self._rings[radius] = _Ring(
                self.config,
                radius,
                self.terminal.output_area.center,
                ring_coords,
                self.ring_gap,
                self.config.ring_colors[len(self._rings) % len(self.config.ring_colors)],
                self._character_final_color_map,
            )
        # assign characters to rings
        ring_count = 0
        for ring in self._rings.values():
            for _ in ring.counter_clockwise_coords:
                if self._pending_chars:
                    next_character = self._pending_chars.pop(0)
                    # set rings to rotate in opposite directions
                    ring.add_character(next_character, clockwise=ring_count % 2)
                    self._ring_chars.append(next_character)
            ring_count += 1

        # make external waypoints for characters not in rings
        for character in self.terminal.get_characters():
            if character not in self._ring_chars:
                external_path = character.motion.new_path(id="external", speed=0.8, ease=easing.out_sine)
                external_path.new_waypoint(self.terminal.output_area.random_coord(outside_scope=True))

                self._non_ring_chars.append(character)
                character.event_handler.register_event(
                    EventHandler.Event.PATH_COMPLETE,
                    external_path,
                    EventHandler.Action.CALLBACK,
                    EventHandler.Callback(self.terminal.set_character_visibility, False),
                )
        self._built = True

    @property
    def built(self) -> bool:
        """Returns True if the effect has been built."""
        return self._built

    def __iter__(self) -> Iterator[str]:
        """Runs the effect."""
        if not self.built:
            self.build()
        rings = list(self._rings.values())
        phase = "start"
        initial_disperse_complete = False
        spin_time_remaining = self.config.spin_duration
        disperse_time_remaining = self.config.disperse_duration
        cycles_remaining = self.config.spin_disperse_cycles
        initial_phase_time_remaining = 100
        while phase != "complete":
            if phase == "start":
                if not initial_phase_time_remaining:
                    phase = "disperse"
                else:
                    initial_phase_time_remaining -= 1

            elif phase == "disperse":
                if not initial_disperse_complete:
                    initial_disperse_complete = True
                    for ring in rings:
                        for character in ring.characters:
                            disperse_path = ring.make_disperse_waypoints(
                                character, character.motion.paths["0"].waypoints[0].coord
                            )
                            initial_path = character.motion.new_path(speed=0.3, ease=easing.out_cubic)
                            initial_path.new_waypoint(disperse_path.waypoints[0].coord)
                            character.event_handler.register_event(
                                EventHandler.Event.PATH_COMPLETE,
                                initial_path,
                                EventHandler.Action.ACTIVATE_PATH,
                                disperse_path,
                            )
                            character.animation.activate_scene(character.animation.query_scene("disperse"))
                            character.motion.activate_path(initial_path)
                            self._active_chars.append(character)

                    for character in self._non_ring_chars:
                        character.motion.activate_path(character.motion.query_path("external"))
                        self._active_chars.append(character)

                else:
                    if not disperse_time_remaining:
                        phase = "spin"
                        cycles_remaining -= 1
                        spin_time_remaining = self.config.spin_duration
                        for ring in rings:
                            ring.spin()
                    else:
                        disperse_time_remaining -= 1

            elif phase == "spin":
                if not spin_time_remaining:
                    if not cycles_remaining:
                        phase = "final"
                        for character in self.terminal.get_characters():
                            self.terminal.set_character_visibility(character, True)
                            character.motion.activate_path(character.motion.query_path("home"))
                            self._active_chars.append(character)
                            if "external" in character.motion.paths:
                                continue
                            character.animation.activate_scene(character.animation.query_scene("disperse"))
                    else:
                        disperse_time_remaining = self.config.disperse_duration
                        for ring in rings:
                            ring.disperse()
                        phase = "disperse"

                else:
                    spin_time_remaining -= 1

            elif phase == "final":
                if not self._active_chars:
                    phase = "complete"

            yield self.terminal.get_formatted_output_string()
            self._animate_chars()
            self._active_chars = [character for character in self._active_chars if character.is_active]
        self._built = False

    def _animate_chars(self) -> None:
        """Animates the characters by calling the tick method on all active characters."""
        for character in self._active_chars:
            character.tick()
