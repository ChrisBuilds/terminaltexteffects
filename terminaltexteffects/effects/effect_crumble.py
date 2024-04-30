"""Characters crumble into dust before being vacuumed up and reformed.

Classes:
    Crumble: Characters crumble into dust before being vacuumed up and reformed.
    CrumbleConfig: Configuration for the Crumble effect.
    CrumbleIterator: Iterates over the Crumble effect. Does not normally need to be called directly.

"""

import random
import typing
from dataclasses import dataclass

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.engine import animation
from terminaltexteffects.engine.base_character import EffectCharacter, EventHandler
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import easing, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return Crumble, CrumbleConfig


@argclass(
    name="crumble",
    help="Characters lose color and crumble into dust, vacuumed up, and reformed.",
    description="crumble | Characters lose color and crumble into dust, vacuumed up, and reformed.",
    epilog="""Example: terminaltexteffects crumble --final-gradient-stops 5CE1FF FF8C00 --final-gradient-steps 12 --final-gradient-direction diagonal""",
)
@dataclass
class CrumbleConfig(ArgsDataClass):
    """Configuration for the Crumble effect.

    Attributes:
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the final gradient."""

    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("5CE1FF", "FF8C00"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[graphics.Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color."

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
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]
    "graphics.Gradient.Direction : Direction of the final gradient."

    @classmethod
    def get_effect_class(cls):
        return Crumble


class CrumbleIterator(BaseEffectIterator[CrumbleConfig]):
    def __init__(self, effect: "Crumble"):
        super().__init__(effect)

        self._pending_chars: list[EffectCharacter] = []
        self._active_chars: list[EffectCharacter] = []
        self._character_final_color_map: dict[EffectCharacter, graphics.Color] = {}
        self._build()

    def _build(self) -> None:
        final_gradient = graphics.Gradient(*self._config.final_gradient_stops, steps=self._config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self._terminal.output_area.top, self._terminal.output_area.right, self._config.final_gradient_direction
        )
        for character in self._terminal.get_characters():
            self._character_final_color_map[character] = final_gradient_mapping[character.input_coord]
            strengthen_flash_gradient = graphics.Gradient(self._character_final_color_map[character], "ffffff", steps=6)
            strengthen_gradient = graphics.Gradient("ffffff", self._character_final_color_map[character], steps=9)
            weak_color = character.animation.adjust_color_brightness(self._character_final_color_map[character], 0.65)
            dust_color = character.animation.adjust_color_brightness(self._character_final_color_map[character], 0.55)
            weaken_gradient = graphics.Gradient(weak_color, dust_color, steps=9)
            self._terminal.set_character_visibility(character, True)
            # set up initial and falling stage
            initial_scn = character.animation.new_scene()
            initial_scn.add_frame(character.input_symbol, 1, color=weak_color)
            character.animation.activate_scene(initial_scn)
            fall_path = character.motion.new_path(
                speed=0.2,
                ease=easing.out_bounce,
            )
            fall_path.new_waypoint(Coord(character.input_coord.column, self._terminal.output_area.bottom))
            weaken_scn = character.animation.new_scene(id="weaken")
            weaken_scn.apply_gradient_to_symbols(weaken_gradient, character.input_symbol, 6)

            top_path = character.motion.new_path(id="top", speed=0.5, ease=easing.out_quint)
            top_path.new_waypoint(
                Coord(character.input_coord.column, self._terminal.output_area.top),
                bezier_control=Coord(self._terminal.output_area.center_column, self._terminal.output_area.center_row),
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
        random.shuffle(self._pending_chars)
        self.fall_delay = 20
        self.max_fall_delay = 20
        self.min_fall_delay = 15
        self.reset = False
        self.fall_group_maxsize = 1
        self.stage = "falling"
        self.unvacuumed_chars = list(self._terminal._input_characters)
        random.shuffle(self.unvacuumed_chars)

    def __next__(self) -> str:
        if self.stage != "complete":
            if self.stage == "falling":
                if self._pending_chars:
                    if self.fall_delay == 0:
                        # Determine the size of the next group of falling characters
                        fall_group_size = random.randint(1, self.fall_group_maxsize)
                        # Add the next group of falling characters to the animating characters list
                        for _ in range(fall_group_size):
                            if self._pending_chars:
                                next_char = self._pending_chars.pop(0)
                                next_char.animation.activate_scene(next_char.animation.query_scene("weaken"))
                                self._active_chars.append(next_char)
                        # Reset the fall delay and adjust the fall group size and delay range
                        self.fall_delay = random.randint(self.min_fall_delay, self.max_fall_delay)
                        if random.randint(1, 10) > 4:  # 60% chance to modify the fall delay and group size
                            self.fall_group_maxsize += 1
                            self.min_fall_delay = max(0, self.min_fall_delay - 1)
                            self.max_fall_delay = max(0, self.max_fall_delay - 1)
                    else:
                        self.fall_delay -= 1
                if not self._pending_chars and not self._active_chars:
                    self.stage = "vacuuming"
            elif self.stage == "vacuuming":
                if self.unvacuumed_chars:
                    for _ in range(random.randint(3, 10)):
                        if self.unvacuumed_chars:
                            next_char = self.unvacuumed_chars.pop(0)
                            next_char.motion.activate_path(next_char.motion.query_path("top"))
                            self._active_chars.append(next_char)
                if not self._active_chars:
                    self.stage = "resetting"

            elif self.stage == "resetting":
                if not self.reset:
                    for character in self._terminal.get_characters():
                        character.motion.activate_path(character.motion.query_path("input"))
                        self._active_chars.append(character)
                    self.reset = True
                if not self._active_chars:
                    self.stage = "complete"

            next_frame = self._terminal.get_formatted_output_string()
            for character in self._active_chars:
                character.tick()
            self._active_chars = [character for character in self._active_chars if character.is_active]
            return next_frame
        else:
            raise StopIteration


class Crumble(BaseEffect[CrumbleConfig]):
    """Characters crumble into dust before being vacuumed up and reformed.

    Attributes:
        effect_config (CrumbleConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.
    """

    _config_cls = CrumbleConfig
    _iterator_cls = CrumbleIterator

    def __init__(self, input_data: str) -> None:
        """Initialize the effect with the provided input data.

        Args:
            input_data (str): The input data to use for the effect."""
        super().__init__(input_data)
