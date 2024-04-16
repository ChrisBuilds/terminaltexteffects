import random
import typing
from collections.abc import Iterator
from dataclasses import dataclass

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.base_effect import BaseEffect
from terminaltexteffects.utils import animation, easing, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.terminal import Terminal, TerminalConfig


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return CrumbleEffect, EffectConfig


@argclass(
    name="crumble",
    help="Characters lose color and crumble into dust, vacuumed up, and reformed.",
    description="crumble | Characters lose color and crumble into dust, vacuumed up, and reformed.",
    epilog="""Example: terminaltexteffects crumble --final-gradient-stops 5CE1FF FF8C00 --final-gradient-steps 12 --final-gradient-direction diagonal""",
)
@dataclass
class EffectConfig(ArgsDataClass):
    """Configuration for the Crumble effect.

    Attributes:
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the gradient for the final color."""

    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("5CE1FF", "FF8C00"),
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
        default=graphics.Gradient.Direction.DIAGONAL,
        metavar=arg_validators.GradientDirection.METAVAR,
        help="Direction of the gradient for the final color.",
    )  # type: ignore[assignment]
    "graphics.Gradient.Direction : Direction of the gradient for the final color."

    @classmethod
    def get_effect_class(cls):
        return CrumbleEffect


class CrumbleEffect(BaseEffect):
    """Characters crumble into dust before being vacuumed up and rebuilt."""

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
        self._character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def build(self) -> None:
        """Prepares the data for the effect by registering events and building scenes/waypoints."""
        self._pending_chars.clear()
        self._active_chars.clear()
        self._character_final_color_map.clear()
        final_gradient = graphics.Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.config.final_gradient_direction
        )
        for character in self.terminal.get_characters():
            self._character_final_color_map[character] = final_gradient_mapping[character.input_coord]
            strengthen_flash_gradient = graphics.Gradient(self._character_final_color_map[character], "ffffff", steps=6)
            strengthen_gradient = graphics.Gradient("ffffff", self._character_final_color_map[character], steps=9)
            weak_color = character.animation.adjust_color_brightness(self._character_final_color_map[character], 0.65)
            dust_color = character.animation.adjust_color_brightness(self._character_final_color_map[character], 0.55)
            weaken_gradient = graphics.Gradient(weak_color, dust_color, steps=9)
            self.terminal.set_character_visibility(character, True)
            # set up initial and falling stage
            initial_scn = character.animation.new_scene()
            initial_scn.add_frame(character.input_symbol, 1, color=weak_color)
            character.animation.activate_scene(initial_scn)
            fall_path = character.motion.new_path(
                speed=0.2,
                ease=easing.out_bounce,
            )
            fall_path.new_waypoint(Coord(character.input_coord.column, self.terminal.output_area.bottom))
            weaken_scn = character.animation.new_scene(id="weaken")
            weaken_scn.apply_gradient_to_symbols(weaken_gradient, character.input_symbol, 6)

            top_path = character.motion.new_path(id="top", speed=0.5, ease=easing.out_quint)
            top_path.new_waypoint(
                Coord(character.input_coord.column, self.terminal.output_area.top),
                bezier_control=Coord(self.terminal.output_area.center_column, self.terminal.output_area.center_row),
            )
            # set up reset stage
            input_path = character.motion.new_path(id="input", speed=0.3)
            input_path.new_waypoint(character.input_coord)
            strengthen_flash_scn = character.animation.new_scene()
            strengthen_flash_scn.apply_gradient_to_symbols(strengthen_flash_gradient, character.input_symbol, 4)
            strengthen_scn = character.animation.new_scene()
            strengthen_scn.apply_gradient_to_symbols(strengthen_gradient, character.input_symbol, 6)
            dust_scn = character.animation.new_scene(sync=animation.SyncMetric.DISTANCE)
            for _ in range(5):
                dust_scn.add_frame(random.choice(["*", ".", ","]), 1, color=dust_color)

            character.event_handler.register_event(
                EventHandler.Event.SCENE_COMPLETE, weaken_scn, EventHandler.Action.ACTIVATE_PATH, fall_path
            )
            character.event_handler.register_event(
                EventHandler.Event.SCENE_COMPLETE, weaken_scn, EventHandler.Action.SET_LAYER, 1
            )
            character.event_handler.register_event(
                EventHandler.Event.SCENE_COMPLETE, weaken_scn, EventHandler.Action.ACTIVATE_SCENE, dust_scn
            )

            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE,
                input_path,
                EventHandler.Action.ACTIVATE_SCENE,
                strengthen_flash_scn,
            )
            character.event_handler.register_event(
                EventHandler.Event.SCENE_COMPLETE,
                strengthen_flash_scn,
                EventHandler.Action.ACTIVATE_SCENE,
                strengthen_scn,
            )
            self._pending_chars.append(character)
        self._built = True

    @property
    def built(self) -> bool:
        """Returns True if the effect has been built."""
        return self._built

    def __iter__(self) -> Iterator[str]:
        """Runs the effect."""
        # Prepare data for the effect
        if not self._built:
            self.build()
        random.shuffle(self._pending_chars)
        fall_delay = 20
        max_fall_delay = 20
        min_fall_delay = 15
        reset = False
        fall_group_maxsize = 1
        stage = "falling"
        unvacuumed_chars = list(self.terminal._input_characters)
        random.shuffle(unvacuumed_chars)
        yield self.terminal.get_formatted_output_string()
        while stage != "complete":
            if stage == "falling":
                if self._pending_chars:
                    if fall_delay == 0:
                        # Determine the size of the next group of falling characters
                        fall_group_size = random.randint(1, fall_group_maxsize)
                        # Add the next group of falling characters to the animating characters list
                        for _ in range(fall_group_size):
                            if self._pending_chars:
                                next_char = self._pending_chars.pop(0)
                                next_char.animation.activate_scene(next_char.animation.query_scene("weaken"))
                                self._active_chars.append(next_char)
                        # Reset the fall delay and adjust the fall group size and delay range
                        fall_delay = random.randint(min_fall_delay, max_fall_delay)
                        if random.randint(1, 10) > 4:  # 60% chance to modify the fall delay and group size
                            fall_group_maxsize += 1
                            min_fall_delay = max(0, min_fall_delay - 1)
                            max_fall_delay = max(0, max_fall_delay - 1)
                    else:
                        fall_delay -= 1
                if not self._pending_chars and not self._active_chars:
                    stage = "vacuuming"
            elif stage == "vacuuming":
                if unvacuumed_chars:
                    for _ in range(random.randint(3, 10)):
                        if unvacuumed_chars:
                            next_char = unvacuumed_chars.pop(0)
                            next_char.motion.activate_path(next_char.motion.query_path("top"))
                            self._active_chars.append(next_char)
                if not self._active_chars:
                    stage = "resetting"

            elif stage == "resetting":
                if not reset:
                    for character in self.terminal.get_characters():
                        character.motion.activate_path(character.motion.query_path("input"))
                        self._active_chars.append(character)
                    reset = True
                if not self._active_chars:
                    stage = "complete"

            yield self.terminal.get_formatted_output_string()
            self._animate_chars()
            self._active_chars = [character for character in self._active_chars if character.is_active]
        self._built = False

    def _animate_chars(self) -> None:
        """Animates the characters by calling the tick method."""
        for character in self._active_chars:
            character.tick()
