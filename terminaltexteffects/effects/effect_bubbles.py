"""Forms bubbles with the characters. Bubbles float down and pop.

Classes:
    Bubbles: Forms bubbles with the characters. Bubbles float down and pop.
    BubblesConfig: Configuration for the Bubbles effect.
    BubblesIterator: Iterates over the Bubbles effect. Does not normally need to be called directly.
"""

import random
import typing
from dataclasses import dataclass

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.engine.base_character import EffectCharacter, EventHandler
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.terminal import Terminal
from terminaltexteffects.utils import easing, geometry, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return Bubbles, BubblesConfig


@argclass(
    name="bubbles",
    help="Characters are formed into bubbles that float down and pop.",
    description="bubbles | Characters are formed into bubbles that float down and pop.",
    epilog=f"""{arg_validators.EASING_EPILOG}

Example: terminaltexteffects bubbles --bubble-colors d33aff 7395c4 43c2a7 02ff7f --pop-color ffffff --final-gradient-stops d33aff 02ff7f --final-gradient-steps 12 --final-gradient-direction diagonal --bubble-speed 0.1 --bubble-delay 50 --pop-condition row --easing IN_OUT_SINE""",
)
@dataclass
class BubblesConfig(ArgsDataClass):
    """Configuration for the Bubbles effect.

    Attributes:
        rainbow (bool): If set, the bubbles will be colored with a rotating rainbow gradient.
        bubble_colors (tuple[graphics.Color, ...]): Tuple of colors for the bubbles. Ignored if --no-rainbow is left as default False.
        pop_color (graphics.Color): Color for the spray emitted when a bubble pops.
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the final gradient.
        bubble_speed (float): Speed of the floating bubbles. Valid values are n > 0.
        bubble_delay (int): Number of frames between bubbles. Valid values are n >= 0.
        pop_condition (str): Condition for a bubble to pop. 'row' will pop the bubble when it reaches the the lowest row for which a character in the bubble originates. 'bottom' will pop the bubble at the bottom row of the terminal. 'anywhere' will pop the bubble randomly, or at the bottom of the terminal.
        easing (typing.Callable): Easing function to use for character movement after a bubble pops.
    """

    rainbow: bool = ArgField(
        cmd_name="--rainbow",
        action="store_true",
        default=False,
        help="If set, the bubbles will be colored with a rotating rainbow gradient.",
    )  # type: ignore[assignment]
    "bool : If set, the bubbles will be colored with a rotating rainbow gradient."

    bubble_colors: tuple[graphics.Color, ...] = ArgField(
        cmd_name="--bubble-colors",
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("d33aff", "7395c4", "43c2a7", "02ff7f"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the bubbles. Ignored if --no-rainbow is left as default False.",
    )  # type: ignore[assignment]
    "tuple[graphics.Color, ...] : Tuple of colors for the bubbles. Ignored if --no-rainbow is left as default False."

    pop_color: graphics.Color = ArgField(
        cmd_name="--pop-color",
        type_parser=arg_validators.Color.type_parser,
        default="ffffff",
        metavar=arg_validators.Color.METAVAR,
        help="Color for the spray emitted when a bubble pops.",
    )  # type: ignore[assignment]
    "graphics.Color : Color for the spray emitted when a bubble pops."

    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("d33aff", "02ff7f"),
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

    bubble_speed: float = ArgField(
        cmd_name="--bubble-speed",
        type_parser=arg_validators.PositiveFloat.type_parser,
        default=0.1,
        metavar=arg_validators.PositiveFloat.METAVAR,
        help="Speed of the floating bubbles. ",
    )  # type: ignore[assignment]
    "float : Speed of the floating bubbles. "

    bubble_delay: int = ArgField(
        cmd_name="--bubble-delay",
        type_parser=arg_validators.PositiveInt.type_parser,
        default=50,
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Number of frames between bubbles.",
    )  # type: ignore[assignment]
    "int : Number of frames between bubbles."

    pop_condition: str = ArgField(
        cmd_name="--pop-condition",
        default="row",
        choices=["row", "bottom", "anywhere"],
        help="Condition for a bubble to pop. 'row' will pop the bubble when it reaches the the lowest row for which a character in the bubble originates. 'bottom' will pop the bubble at the bottom row of the terminal. 'anywhere' will pop the bubble randomly, or at the bottom of the terminal.",
    )  # type: ignore[assignment]
    "str : Condition for a bubble to pop. 'row' will pop the bubble when it reaches the the lowest row for which a character in the bubble originates. 'bottom' will pop the bubble at the bottom row of the terminal. 'anywhere' will pop the bubble randomly, or at the bottom of the terminal."

    movement_easing: easing.EasingFunction = ArgField(
        cmd_name=["--movement-easing"],
        default=easing.in_out_sine,
        type_parser=arg_validators.Ease.type_parser,
        metavar=arg_validators.Ease.METAVAR,
        help="Easing function to use for character movement after a bubble pops.",
    )  # type: ignore[assignment]
    "easing.EasingFunction : Easing function to use for character movement after a bubble pops."

    @classmethod
    def get_effect_class(cls):
        return Bubbles


class BubblesIterator(BaseEffectIterator[BubblesConfig]):
    class _Bubble:
        def __init__(
            self,
            effect: "BubblesIterator",
            origin: Coord,
            characters: list[EffectCharacter],
            terminal: Terminal,
        ):
            self.effect = effect
            self.characters = characters
            self.terminal = terminal
            self.radius = max(len(self.characters) // 5, 1)
            self.origin = origin
            self.anchor_char = self.terminal.add_character(" ", self.origin)
            if self.effect._config.pop_condition == "row":
                self.lowest_row = min([char.input_coord.row for char in self.characters])
            else:
                self.lowest_row = self.effect._terminal.output_area.bottom
            self.set_character_coordinates()
            self.landed = False
            self.make_waypoints()
            self.make_gradients()

        def set_character_coordinates(self) -> None:
            for i, char in enumerate(self.characters):
                point = geometry.find_coords_on_circle(
                    self.anchor_char.motion.current_coord, self.radius, len(self.characters), unique=False
                )[i]
                char.motion.set_coordinate(point)
                if point.row == self.lowest_row:
                    self.landed = True

            if self.effect._config.pop_condition == "anywhere":
                if random.random() < 0.002:
                    self.landed = True

        def make_waypoints(self):
            waypoint_column = random.randint(
                self.effect._terminal.output_area.left, self.effect._terminal.output_area.right
            )
            floor_path = self.anchor_char.motion.new_path(speed=self.effect._config.bubble_speed)
            floor_path.new_waypoint(Coord(waypoint_column, self.lowest_row))
            self.anchor_char.motion.activate_path(floor_path)

        def make_gradients(self) -> None:
            if self.effect._config.rainbow:
                rainbow_gradient = list(self.effect.rainbow_gradient.spectrum)
                gradient_offset = 0
                for character in self.characters:
                    sheen_scene = character.animation.new_scene()
                    for step in rainbow_gradient:
                        sheen_scene.add_frame(character.input_symbol, 5, color=step)
                    gradient_offset += 2
                    gradient_offset %= len(rainbow_gradient)
                    rainbow_gradient = rainbow_gradient[gradient_offset:] + rainbow_gradient[:gradient_offset]
                    character.animation.activate_scene(sheen_scene)
                    if character.animation.active_scene:
                        character.animation.active_scene.is_looping = True

            else:
                bubble_color = random.choice(self.effect._config.bubble_colors)
                for character in self.characters:
                    sheen_scene = character.animation.new_scene()
                    sheen_scene.add_frame(character.input_symbol, 1, color=bubble_color)
                    character.animation.activate_scene(sheen_scene)

        def pop(self) -> None:
            char: EffectCharacter
            point: Coord
            for char, point in zip(
                self.characters,
                geometry.find_coords_on_circle(
                    self.anchor_char.motion.current_coord,
                    self.radius + 3,
                    len(self.characters),
                ),
            ):
                pop_out_path = char.motion.new_path(id="pop_out", speed=0.2, ease=easing.out_expo)
                pop_out_path.new_waypoint(point)
                char.event_handler.register_event(
                    EventHandler.Event.PATH_COMPLETE,
                    pop_out_path,
                    EventHandler.Action.ACTIVATE_PATH,
                    char.motion.paths["final"],
                )
            for character in self.characters:
                character.animation.activate_scene(character.animation.query_scene("pop_1"))
                character.motion.activate_path(character.motion.query_path("pop_out"))

        def activate(self) -> None:
            for char in self.characters:
                self.terminal.set_character_visibility(char, True)

        def move(self) -> None:
            self.anchor_char.motion.move()
            self.set_character_coordinates()
            for character in self.characters:
                character.animation.step_animation()

    def __init__(self, effect: "Bubbles"):
        super().__init__(effect)
        self._pending_chars: list[EffectCharacter] = []
        self._active_chars: list[EffectCharacter] = []
        self._bubbles: list[BubblesIterator._Bubble] = []
        red = "e81416"
        orange = "ffa500"
        yellow = "faeb36"
        green = "79c314"
        blue = "487de7"
        indigo = "4b369d"
        violet = "70369d"
        self.rainbow_gradient = graphics.Gradient(red, orange, yellow, green, blue, indigo, violet, steps=5)
        self._character_final_color_map: dict[EffectCharacter, graphics.Color] = {}
        self._build()

    def _build(self) -> None:
        final_gradient = graphics.Gradient(*self._config.final_gradient_stops, steps=self._config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self._terminal.output_area.top, self._terminal.output_area.right, self._config.final_gradient_direction
        )
        for character in self._terminal.get_characters():
            self._character_final_color_map[character] = final_gradient_mapping[character.input_coord]
            character.layer = 1
            pop_1_scene = character.animation.new_scene(id="pop_1")
            pop_2_scene = character.animation.new_scene()
            pop_1_scene.add_frame("*", 20, color=self._config.pop_color)
            pop_2_scene.add_frame("'", 20, color=self._config.pop_color)
            final_scene = character.animation.new_scene()
            char_final_gradient = graphics.Gradient(
                self._config.pop_color, self._character_final_color_map[character], steps=10
            )
            final_scene.apply_gradient_to_symbols(char_final_gradient, character.input_symbol, 10)
            character.event_handler.register_event(
                EventHandler.Event.SCENE_COMPLETE, pop_1_scene, EventHandler.Action.ACTIVATE_SCENE, pop_2_scene
            )
            character.event_handler.register_event(
                EventHandler.Event.SCENE_COMPLETE,
                pop_2_scene,
                EventHandler.Action.ACTIVATE_SCENE,
                final_scene,
            )
            final_path = character.motion.new_path(
                id="final",
                speed=0.3,
                ease=easing.in_out_expo,
            )
            final_path.new_waypoint(character.input_coord)
            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE, final_path, EventHandler.Action.SET_LAYER, 0
            )

        unbubbled_chars = []
        for char_list in self._terminal.get_characters_grouped(
            grouping=self._terminal.CharacterGroup.ROW_BOTTOM_TO_TOP
        ):
            unbubbled_chars.extend(char_list)
        self._bubbles = []
        while unbubbled_chars:
            bubble_group = []
            if len(unbubbled_chars) < 5:
                bubble_group.extend(unbubbled_chars)
                unbubbled_chars.clear()
            else:
                for _ in range(random.randint(5, min(len(unbubbled_chars), 20))):
                    bubble_group.append(unbubbled_chars.pop(0))
            bubble_origin = Coord(
                random.randint(self._terminal.output_area.left, self._terminal.output_area.right),
                self._terminal.output_area.top,
            )
            new_bubble = BubblesIterator._Bubble(self, bubble_origin, bubble_group, self._terminal)
            self._bubbles.append(new_bubble)
        self.animating_bubbles: list[BubblesIterator._Bubble] = []
        self.steps_since_last_bubble = 0

    def __next__(self) -> str:
        if self.animating_bubbles or self._active_chars or self._bubbles:
            if self._bubbles and self.steps_since_last_bubble >= self._config.bubble_delay:
                next_bubble = self._bubbles.pop(0)
                next_bubble.activate()
                self.animating_bubbles.append(next_bubble)
                self.steps_since_last_bubble = 0
            self.steps_since_last_bubble += 1

            for bubble in self.animating_bubbles:
                if bubble.landed:
                    bubble.pop()
                    self._active_chars.extend(bubble.characters)

            self.animating_bubbles = [bubble for bubble in self.animating_bubbles if not bubble.landed]
            for bubble in self.animating_bubbles:
                bubble.move()
            for character in self._active_chars:
                character.tick()
            next_frame = self._terminal.get_formatted_output_string()

            self._active_chars = [character for character in self._active_chars if character.is_active]
            return next_frame
        else:
            raise StopIteration


class Bubbles(BaseEffect[BubblesConfig]):
    """Forms bubbles with the characters. Bubbles float down and pop.

    Attributes:
        effect_config (BubblesConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.
    """

    _config_cls = BubblesConfig
    _iterator_cls = BubblesIterator

    def __init__(self, input_data: str) -> None:
        """Initialize the effect with the provided input data.

        Args:
            input_data (str): The input data to use for the effect."""
        super().__init__(input_data)
