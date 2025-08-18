"""Forms bubbles with the characters. Bubbles float down and pop.

Classes:
    Bubbles: Forms bubbles with the characters. Bubbles float down and pop.
    BubblesConfig: Configuration for the Bubbles effect.
    BubblesIterator: Iterates over the Bubbles effect. Does not normally need to be called directly.
"""

from __future__ import annotations

import random
import typing
from dataclasses import dataclass

from terminaltexteffects import Color, Coord, EffectCharacter, EventHandler, Gradient, Terminal, easing, geometry
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.argutils import ArgSpec, ParserSpec
from terminaltexteffects.utils.graphics import ColorPair


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Get the command, effect class, and configuration class for the effect.

    Returns:
        tuple[str, type[BaseEffect], type[BaseConfig]]: The command name, effect class, and configuration class.

    """
    return "bubbles", Bubbles, BubblesConfig


@dataclass
class BubblesConfig(BaseConfig):
    """Configuration for the Bubbles effect.

    Attributes:
        rainbow (bool): If set, the bubbles will be colored with a rotating rainbow gradient.
        bubble_colors (tuple[Color, ...]): Tuple of colors for the bubbles. Ignored if --no-rainbow is left as
            default False.
        pop_color (Color): Color for the spray emitted when a bubble pops.
        bubble_speed (float): Speed of the floating bubbles. Valid values are n > 0.
        bubble_delay (int): Number of frames between bubbles. Valid values are n >= 0.
        pop_condition (typing.Literal["row", "bottom", "anywhere"]): Condition for a bubble to pop. 'row' will pop
            the bubble when it reaches the the lowest row for which a character in the bubble originates. 'bottom'
            will pop the bubble at the bottom row of the terminal. 'anywhere' will pop the bubble randomly, or at
            the bottom of the terminal.
        movement_easing (easing.EasingFunction): Easing function to use for character movement after a bubble pops.
        final_gradient_stops (tuple[Color, ...]): Tuple of colors for the final color gradient. If only one color
            is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Tuple of the number of gradient steps to use. More steps
            will create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient.

    """

    parser_spec: ParserSpec = ParserSpec(
        name="bubbles",
        help="Characters are formed into bubbles that float down and pop.",
        description="bubbles | Characters are formed into bubbles that float down and pop.",
        epilog=f"{argutils.EASING_EPILOG}"
        "Example: terminaltexteffects bubbles --bubble-colors d33aff 7395c4 43c2a7 02ff7f --pop-color ffffff "
        "--final-gradient-stops d33aff 02ff7f --final-gradient-steps 12 --final-gradient-direction diagonal "
        "--bubble-speed 0.1 --bubble-delay 50 --pop-condition row --easing IN_OUT_SINE",
    )

    rainbow: bool = ArgSpec(
        name="--rainbow",
        action="store_true",
        default=False,
        help="If set, the bubbles will be colored with a rotating rainbow gradient.",
    )  # pyright: ignore[reportAssignmentType]
    "bool : If set, the bubbles will be colored with a rotating rainbow gradient."

    bubble_colors: tuple[Color, ...] = ArgSpec(
        name="--bubble-colors",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        default=(Color("d33aff"), Color("7395c4"), Color("43c2a7"), Color("02ff7f")),
        metavar=argutils.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the bubbles. Ignored if --no-rainbow is left as "
        "default False.",
    )  # pyright: ignore[reportAssignmentType]
    "tuple[Color, ...] : Tuple of colors for the bubbles. Ignored if --no-rainbow is left as default False."

    pop_color: Color = ArgSpec(
        name="--pop-color",
        type=argutils.ColorArg.type_parser,
        default=Color("ffffff"),
        metavar=argutils.ColorArg.METAVAR,
        help="Color for the spray emitted when a bubble pops.",
    )  # pyright: ignore[reportAssignmentType]
    "Color : Color for the spray emitted when a bubble pops."

    bubble_speed: float = ArgSpec(
        name="--bubble-speed",
        type=argutils.PositiveFloat.type_parser,
        default=0.1,
        metavar=argutils.PositiveFloat.METAVAR,
        help="Speed of the floating bubbles. ",
    )  # pyright: ignore[reportAssignmentType]
    "float : Speed of the floating bubbles. "

    bubble_delay: int = ArgSpec(
        name="--bubble-delay",
        type=argutils.PositiveInt.type_parser,
        default=50,
        metavar=argutils.PositiveInt.METAVAR,
        help="Number of frames between bubbles.",
    )  # pyright: ignore[reportAssignmentType]
    "int : Number of frames between bubbles."

    pop_condition: typing.Literal["row", "bottom", "anywhere"] = ArgSpec(
        name="--pop-condition",
        default="row",
        choices=["row", "bottom", "anywhere"],
        help="Condition for a bubble to pop. 'row' will pop the bubble when it reaches the the lowest row for which "
        "a character in the bubble originates. 'bottom' will pop the bubble at the bottom row of the terminal. "
        "'anywhere' will pop the bubble randomly, or at the bottom of the terminal.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "typing.Literal['row', 'bottom', 'anywhere'] : Condition for a bubble to pop. 'row' will pop the bubble when "
        "it reaches the the lowest row for which a character in the bubble originates. 'bottom' will pop the bubble at "
        "the bottom row of the terminal. 'anywhere' will pop the bubble randomly, or at the bottom of the terminal."
    )

    movement_easing: easing.EasingFunction = ArgSpec(
        name="--movement-easing",
        default=easing.in_out_sine,
        type=argutils.Ease.type_parser,
        metavar=argutils.Ease.METAVAR,
        help="Easing function to use for character movement after a bubble pops.",
    )  # pyright: ignore[reportAssignmentType]
    "easing.EasingFunction : Easing function to use for character movement after a bubble pops."

    final_gradient_stops: tuple[Color, ...] = ArgSpec(
        name="--final-gradient-stops",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        default=(Color("d33aff"), Color("02ff7f")),
        metavar=argutils.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied across the canvas). "
        "If only one color is provided, the characters will be displayed in that color.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the "
        "characters will be displayed in that color."
    )

    final_gradient_steps: tuple[int, ...] | int = ArgSpec(
        name="--final-gradient-steps",
        type=argutils.PositiveInt.type_parser,
        nargs="+",
        default=12,
        metavar=argutils.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a "
        "smoother and longer gradient animation.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[int, ...] | int : Int or Tuple of ints for the number of gradient steps to use. More steps will "
        "create a smoother and longer gradient animation."
    )

    final_gradient_direction: Gradient.Direction = ArgSpec(
        name="--final-gradient-direction",
        type=argutils.GradientDirection.type_parser,
        default=Gradient.Direction.DIAGONAL,
        metavar=argutils.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # pyright: ignore[reportAssignmentType]
    "Gradient.Direction : Direction of the final gradient."


class BubblesIterator(BaseEffectIterator[BubblesConfig]):
    """Iterator for the Bubbles effect."""

    class Bubble:
        """A bubble of characters that float down and pop."""

        def __init__(
            self,
            effect: BubblesIterator,
            origin: Coord,
            characters: list[EffectCharacter],
            terminal: Terminal,
        ) -> None:
            """Initialize the bubble."""
            self.effect = effect
            self.characters = characters
            self.terminal = terminal
            self.radius = max(len(self.characters) // 5, 1)
            self.origin = origin
            self.anchor_char = self.terminal.add_character(" ", self.origin)
            if self.effect.config.pop_condition == "row":
                self.lowest_row = min([char.input_coord.row for char in self.characters])
            else:
                self.lowest_row = self.effect.terminal.canvas.bottom
            self.set_character_coordinates()
            self.landed = False
            self.make_waypoints()
            self.make_gradients()

        def set_character_coordinates(self) -> None:
            """Set the coordinates of the characters in the bubble."""
            for i, char in enumerate(self.characters):
                point = geometry.find_coords_on_circle(
                    self.anchor_char.motion.current_coord,
                    self.radius,
                    len(self.characters),
                    unique=False,
                )[i]
                char.motion.set_coordinate(point)
                if point.row == self.lowest_row:
                    self.landed = True

            if self.effect.config.pop_condition == "anywhere" and random.random() < 0.002:
                self.landed = True

        def make_waypoints(self) -> None:
            """Make the waypoints for the bubble."""
            waypoint_column = random.randint(self.effect.terminal.canvas.left, self.effect.terminal.canvas.right)
            floor_path = self.anchor_char.motion.new_path(speed=self.effect.config.bubble_speed)
            floor_path.new_waypoint(Coord(waypoint_column, self.lowest_row))
            self.anchor_char.motion.activate_path(floor_path)

        def make_gradients(self) -> None:
            """Make the gradients for the bubble."""
            if self.effect.config.rainbow:
                rainbow_gradient = list(self.effect.rainbow_gradient.spectrum)
                gradient_offset = 0
                for character in self.characters:
                    sheen_scene = character.animation.new_scene()
                    for step in rainbow_gradient:
                        sheen_scene.add_frame(character.input_symbol, 5, colors=ColorPair(fg=step))
                    gradient_offset += 2
                    gradient_offset %= len(rainbow_gradient)
                    rainbow_gradient = rainbow_gradient[gradient_offset:] + rainbow_gradient[:gradient_offset]
                    character.animation.activate_scene(sheen_scene)
                    if character.animation.active_scene:
                        character.animation.active_scene.is_looping = True

            else:
                bubble_color = random.choice(self.effect.config.bubble_colors)
                for character in self.characters:
                    sheen_scene = character.animation.new_scene()
                    sheen_scene.add_frame(character.input_symbol, 1, colors=ColorPair(fg=bubble_color))
                    character.animation.activate_scene(sheen_scene)

        def pop(self) -> None:
            """Pop the bubble."""
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
                pop_out_path = char.motion.new_path(path_id="pop_out", speed=0.2, ease=easing.out_expo)
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
            """Activate the bubble."""
            for char in self.characters:
                self.terminal.set_character_visibility(char, is_visible=True)

        def move(self) -> None:
            """Move the bubble."""
            self.anchor_char.motion.move()
            self.set_character_coordinates()
            for character in self.characters:
                character.animation.step_animation()

    def __init__(self, effect: Bubbles) -> None:
        """Initialize the effect iterator."""
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.bubbles: list[BubblesIterator.Bubble] = []
        red = Color("#e81416")
        orange = Color("#ffa500")
        yellow = Color("#faeb36")
        green = Color("#79c314")
        blue = Color("#487de7")
        indigo = Color("#4b369d")
        violet = Color("#70369d")
        self.rainbow_gradient = Gradient(red, orange, yellow, green, blue, indigo, violet, steps=5)
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self.build()

    def build(self) -> None:
        """Build the initial state of the effect."""
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
            character.layer = 1
            pop_1_scene = character.animation.new_scene(scene_id="pop_1")
            pop_2_scene = character.animation.new_scene()
            pop_1_scene.add_frame("*", 20, colors=ColorPair(fg=self.config.pop_color))
            pop_2_scene.add_frame("'", 20, colors=ColorPair(fg=self.config.pop_color))
            final_scene = character.animation.new_scene()
            char_final_gradient = Gradient(self.config.pop_color, self.character_final_color_map[character], steps=10)
            final_scene.apply_gradient_to_symbols(character.input_symbol, 10, fg_gradient=char_final_gradient)
            character.event_handler.register_event(
                EventHandler.Event.SCENE_COMPLETE,
                pop_1_scene,
                EventHandler.Action.ACTIVATE_SCENE,
                pop_2_scene,
            )
            character.event_handler.register_event(
                EventHandler.Event.SCENE_COMPLETE,
                pop_2_scene,
                EventHandler.Action.ACTIVATE_SCENE,
                final_scene,
            )
            final_path = character.motion.new_path(
                path_id="final",
                speed=0.3,
                ease=easing.in_out_expo,
            )
            final_path.new_waypoint(character.input_coord)
            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE,
                final_path,
                EventHandler.Action.SET_LAYER,
                0,
            )

        unbubbled_chars = []
        for char_list in self.terminal.get_characters_grouped(grouping=self.terminal.CharacterGroup.ROW_BOTTOM_TO_TOP):
            unbubbled_chars.extend(char_list)
        self.bubbles = []
        while unbubbled_chars:
            bubble_group = []
            if len(unbubbled_chars) < 5:
                bubble_group.extend(unbubbled_chars)
                unbubbled_chars.clear()
            else:
                for _ in range(random.randint(5, min(len(unbubbled_chars), 20))):
                    bubble_group.append(unbubbled_chars.pop(0))  # noqa: PERF401
            bubble_origin = Coord(
                random.randint(self.terminal.canvas.left, self.terminal.canvas.right),
                self.terminal.canvas.top,
            )
            new_bubble = BubblesIterator.Bubble(self, bubble_origin, bubble_group, self.terminal)
            self.bubbles.append(new_bubble)
        self.animating_bubbles: list[BubblesIterator.Bubble] = []
        self.steps_since_last_bubble = 0

    def __next__(self) -> str:
        """Return the next frame in the animation."""
        if self.animating_bubbles or self.active_characters or self.bubbles:
            if self.bubbles and self.steps_since_last_bubble >= self.config.bubble_delay:
                next_bubble = self.bubbles.pop(0)
                next_bubble.activate()
                self.animating_bubbles.append(next_bubble)
                self.steps_since_last_bubble = 0
            self.steps_since_last_bubble += 1

            for bubble in self.animating_bubbles:
                if bubble.landed:
                    bubble.pop()
                    self.active_characters = self.active_characters.union(bubble.characters)

            self.animating_bubbles = [bubble for bubble in self.animating_bubbles if not bubble.landed]
            for bubble in self.animating_bubbles:
                bubble.move()

            self.update()
            return self.frame
        raise StopIteration


class Bubbles(BaseEffect[BubblesConfig]):
    """Forms bubbles with the characters. Bubbles float down and pop.

    Attributes:
        effect_config (BubblesConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.

    """

    @property
    def _config_cls(self) -> type[BubblesConfig]:
        return BubblesConfig

    @property
    def _iterator_cls(self) -> type[BubblesIterator]:
        return BubblesIterator
