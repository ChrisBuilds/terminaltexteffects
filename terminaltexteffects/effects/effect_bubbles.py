import random
import typing
from dataclasses import dataclass

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils import easing, geometry, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.terminal import Terminal


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return BubblesEffect, BubblesEffectArgs


@argclass(
    name="bubbles",
    formatter_class=arg_validators.CustomFormatter,
    help="Characters are formed into bubbles that float down and pop.",
    description="bubbles | Characters are formed into bubbles that float down and pop.",
    epilog=f"""{arg_validators.EASING_EPILOG}

Example: terminaltexteffects bubbles --bubble-colors d33aff 7395c4 43c2a7 02ff7f --pop-color ffffff --final-gradient-stops d33aff 02ff7f --final-gradient-steps 12 --final-gradient-direction diagonal --bubble-speed 0.1 --bubble-delay 50 --pop-condition row --easing IN_OUT_SINE""",
)
@dataclass
class BubblesEffectArgs(ArgsDataClass):
    rainbow: bool = ArgField(
        cmd_name="--rainbow",
        action="store_true",
        default=False,
        help="If set, the bubbles will be colored with a rotating rainbow gradient.",
    )  # type: ignore[assignment]
    bubble_colors: tuple[graphics.Color, ...] = ArgField(
        cmd_name="--bubble-colors",
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("d33aff", "7395c4", "43c2a7", "02ff7f"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the bubbles. Ignored if --no-rainbow is left as default False.",
    )  # type: ignore[assignment]
    pop_color: graphics.Color = ArgField(
        cmd_name="--pop-color",
        type_parser=arg_validators.Color.type_parser,
        default="ffffff",
        metavar=arg_validators.Color.METAVAR,
        help="Color for the spray emitted when a bubble pops.",
    )  # type: ignore[assignment]
    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("d33aff", "02ff7f"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=arg_validators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=arg_validators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.DIAGONAL,
        metavar=arg_validators.GradientDirection.METAVAR,
        help="Direction of the gradient for the final color.",
    )  # type: ignore[assignment]
    bubble_speed: float = ArgField(
        cmd_name="--bubble-speed",
        type_parser=arg_validators.PositiveFloat.type_parser,
        default=0.1,
        metavar=arg_validators.PositiveFloat.METAVAR,
        help="Speed of the floating bubbles. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )  # type: ignore[assignment]
    bubble_delay: int = ArgField(
        cmd_name="--bubble-delay",
        type_parser=arg_validators.PositiveInt.type_parser,
        default=50,
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Number of animation steps between bubbles.",
    )  # type: ignore[assignment]
    pop_condition: str = ArgField(
        cmd_name="--pop-condition",
        default="row",
        choices=["row", "bottom", "anywhere"],
        help="Condition for a bubble to pop. 'row' will pop the bubble when it reaches the the lowest row for which a character in the bubble originates. 'bottom' will pop the bubble at the bottom row of the terminal. 'anywhere' will pop the bubble randomly, or at the bottom of the terminal.",
    )  # type: ignore[assignment]
    easing: typing.Callable = ArgField(
        cmd_name=["--easing"],
        default=easing.in_out_sine,
        type_parser=arg_validators.Ease.type_parser,
        metavar=arg_validators.Ease.METAVAR,
        help="Easing function to use for character movement after a bubble pops.",
    )  # type: ignore[assignment]

    @classmethod
    def get_effect_class(cls):
        return BubblesEffect


class Bubble:
    def __init__(
        self,
        effect: "BubblesEffect",
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
        if self.effect.args.pop_condition == "row":
            self.lowest_row = min([char.input_coord.row for char in self.characters])
        else:
            self.lowest_row = self.effect.terminal.output_area.bottom
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

        if self.effect.args.pop_condition == "anywhere":
            if random.random() < 0.002:
                self.landed = True

    def make_waypoints(self):
        waypoint_column = random.randint(self.effect.terminal.output_area.left, self.effect.terminal.output_area.right)
        floor_path = self.anchor_char.motion.new_path(speed=self.effect.args.bubble_speed)
        floor_path.new_waypoint(Coord(waypoint_column, self.lowest_row))
        self.anchor_char.motion.activate_path(floor_path)

    def make_gradients(self) -> None:
        if self.effect.args.rainbow:
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
            bubble_color = random.choice(self.effect.args.bubble_colors)
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


class BubblesEffect:
    """Effect that forms circles with the characters. Circles float down and pop into the characters."""

    def __init__(self, terminal: Terminal, args: BubblesEffectArgs):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.bubbles: list[Bubble] = []
        red = "e81416"
        orange = "ffa500"
        yellow = "faeb36"
        green = "79c314"
        blue = "487de7"
        indigo = "4b369d"
        violet = "70369d"
        self.rainbow_gradient = graphics.Gradient(red, orange, yellow, green, blue, indigo, violet, steps=5)
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def prepare_data(self) -> None:
        final_gradient = graphics.Gradient(*self.args.final_gradient_stops, steps=self.args.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.args.final_gradient_direction
        )
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]
            character.layer = 1
            pop_1_scene = character.animation.new_scene(id="pop_1")
            pop_2_scene = character.animation.new_scene()
            pop_1_scene.add_frame("*", 20, color=self.args.pop_color)
            pop_2_scene.add_frame("'", 20, color=self.args.pop_color)
            final_scene = character.animation.new_scene()
            char_final_gradient = graphics.Gradient(
                self.args.pop_color, self.character_final_color_map[character], steps=10
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
                    bubble_group.append(unbubbled_chars.pop(0))
            bubble_origin = Coord(
                random.randint(self.terminal.output_area.left, self.terminal.output_area.right),
                self.terminal.output_area.top,
            )
            new_bubble = Bubble(self, bubble_origin, bubble_group, self.terminal)
            self.bubbles.append(new_bubble)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        animating_bubbles: list[Bubble] = []
        steps_since_last_bubble = 0
        while animating_bubbles or self.active_chars or self.bubbles:
            if self.bubbles and steps_since_last_bubble >= self.args.bubble_delay:
                next_bubble = self.bubbles.pop(0)
                next_bubble.activate()
                animating_bubbles.append(next_bubble)
                steps_since_last_bubble = 0
            steps_since_last_bubble += 1

            for bubble in animating_bubbles:
                if bubble.landed:
                    bubble.pop()
                    self.active_chars.extend(bubble.characters)

            animating_bubbles = [bubble for bubble in animating_bubbles if not bubble.landed]
            self.animate_bubbles(animating_bubbles)
            self.animate_chars()
            self.terminal.print()

            self.active_chars = [character for character in self.active_chars if character.is_active]

    def animate_bubbles(self, animating_bubbles: list[Bubble]) -> None:
        for bubble in animating_bubbles:
            bubble.move()

    def animate_chars(self) -> None:
        """Animates the characters by calling the tick method."""
        for character in self.active_chars:
            character.tick()
