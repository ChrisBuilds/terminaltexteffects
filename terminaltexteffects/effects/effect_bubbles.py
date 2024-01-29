import argparse
import random

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.base_character import EventHandler
from terminaltexteffects.utils.terminal import Terminal
from terminaltexteffects.utils import graphics, argtypes, motion, easing


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "bubbles",
        formatter_class=argtypes.CustomFormatter,
        help="Characters are formed into bubbles that float down and pop.",
        description="Characters are formed into bubbles that float down and pop.",
        epilog=f"""{argtypes.EASING_EPILOG}

Example: terminaltexteffects bubbles -a 0.01 --pop-color ff9600 --final-color 252525 --bubble-speed 0.1 --bubble-delay 50 --easing IN_OUT_SINE""",
    )
    effect_parser.set_defaults(effect_class=BubblesEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.nonnegative_float,
        default=0.01,
        help="Minimum time, in seconds, between animation steps. This value does not normally need to be modified. Use this to increase the playback speed of all aspects of the effect. This will have no impact beyond a certain lower threshold due to the processing speed of your device.",
    )
    effect_parser.add_argument(
        "--no-rainbow",
        action="store_true",
        help="If set, the bubbles will not be colored with a rainbow gradient.",
    )
    effect_parser.add_argument(
        "--bubble-color",
        type=argtypes.color,
        default="ffffff",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the bubbles. Ignored if --no-rainbow is left as default False.",
    )
    effect_parser.add_argument(
        "--pop-color",
        type=argtypes.color,
        default="ffffff",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the spray emitted when a bubble pops.",
    )
    effect_parser.add_argument(
        "--final-color",
        type=argtypes.color,
        default="ffffff",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the final character.",
    )
    effect_parser.add_argument(
        "--bubble-speed",
        type=argtypes.positive_float,
        default=0.1,
        metavar="(float > 0)",
        help="Speed of the floating bubbles. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )
    effect_parser.add_argument(
        "--bubble-delay",
        type=argtypes.positive_int,
        default=50,
        metavar="(int > 0)",
        help="Number of animation steps between bubbles.",
    )
    effect_parser.add_argument(
        "--pop-condition",
        default="row",
        choices=["row", "bottom", "anywhere"],
        help="Condition for a bubble to pop. 'row' will pop the bubble when it reaches the the lowest row for which a character in the bubble originates. 'bottom' will pop the bubble at the bottom row of the terminal. 'anywhere' will pop the bubble randomly, or at the bottom of the terminal.",
    )
    effect_parser.add_argument(
        "--easing",
        default="IN_OUT_SINE",
        type=argtypes.ease,
        help="Easing function to use for character movement after a bubble pops.",
    )


class Bubble:
    def __init__(
        self,
        effect: "BubblesEffect",
        origin: motion.Coord,
        characters: list[EffectCharacter],
    ):
        self.effect = effect
        self.characters = characters
        self.radius = max(len(self.characters) // 5, 1)
        self.origin = origin
        self.anchor_char = EffectCharacter(" ", origin.column, origin.row)
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
            point = self.anchor_char.motion.find_coords_on_circle(
                self.anchor_char.motion.current_coord,
                self.radius,
                len(self.characters),
            )[i]
            char.motion.set_coordinate(point)
            if point.row == self.lowest_row:
                self.landed = True

        if self.effect.args.pop_condition == "anywhere":
            if random.random() < 0.002:
                self.landed = True

    def make_waypoints(self):
        waypoint_column = random.randint(self.effect.terminal.output_area.left, self.effect.terminal.output_area.right)
        floor_path = self.anchor_char.motion.new_path("floor", speed=self.effect.args.bubble_speed)
        floor_waypoint = floor_path.new_waypoint("floor", motion.Coord(waypoint_column, self.lowest_row))
        self.anchor_char.motion.activate_path(floor_path)

    def make_gradients(self) -> None:
        if self.effect.args.no_rainbow:
            for character in self.characters:
                sheen_scene = character.animation.new_scene("sheen")
                sheen_scene.add_frame(character.input_symbol, 1, color=self.effect.args.bubble_color)
                character.animation.activate_scene(sheen_scene)
        else:
            rainbow_gradient = list(self.effect.rainbow_gradient.spectrum)
            gradient_offset = 0
            for character in self.characters:
                sheen_scene = character.animation.new_scene("sheen")
                for step in rainbow_gradient:
                    sheen_scene.add_frame(character.input_symbol, 5, color=step)
                gradient_offset += 2
                gradient_offset %= len(rainbow_gradient)
                rainbow_gradient = rainbow_gradient[gradient_offset:] + rainbow_gradient[:gradient_offset]
                character.animation.activate_scene(sheen_scene)
                if character.animation.active_scene:
                    character.animation.active_scene.is_looping = True

    def pop(self) -> None:
        char: EffectCharacter
        point: motion.Coord
        for char, point in zip(
            self.characters,
            self.anchor_char.motion.find_coords_on_circle(
                self.anchor_char.motion.current_coord,
                self.radius + 3,
                len(self.characters),
            ),
        ):
            pop_out_path = char.motion.new_path("pop_out", speed=0.2, ease=easing.out_expo)
            pop_out_waypoint = pop_out_path.new_waypoint("pop_out", point)
            char.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE,
                pop_out_path,
                EventHandler.Action.ACTIVATE_PATH,
                char.motion.paths["final"],
            )
        for character in self.characters:
            character.animation.activate_scene(character.animation.scenes["pop_1"])
            character.motion.activate_path(character.motion.paths["pop_out"])

    def activate(self) -> None:
        for char in self.characters:
            char.is_active = True

    def move(self) -> None:
        self.anchor_char.motion.move()
        self.set_character_coordinates()
        for character in self.characters:
            character.animation.step_animation()


class BubblesEffect:
    """Effect that ___."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.animating_chars: list[EffectCharacter] = []
        self.bubbles: list[Bubble] = []
        red = "e81416"
        orange = "ffa500"
        yellow = "faeb36"
        green = "79c314"
        blue = "487de7"
        indigo = "4b369d"
        violet = "70369d"
        self.rainbow_gradient = graphics.Gradient([red, orange, yellow, green, blue, indigo, violet], 5)

    def prepare_data(self) -> None:
        """Prepares the data for the effect by ___."""
        final_gradient = graphics.Gradient([self.args.pop_color, self.args.final_color], 10)
        for character in self.terminal.characters:
            character.layer = 1
            pop_1_scene = character.animation.new_scene("pop_1")
            pop_2_scene = character.animation.new_scene("pop_2")
            pop_1_scene.add_frame("*", 25, color=self.args.pop_color)
            pop_2_scene.add_frame("'", 25, color=self.args.pop_color)
            final_scene = character.animation.new_scene("final")
            for step in final_gradient:
                final_scene.add_frame(character.input_symbol, 5, color=step)
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
                "final",
                speed=0.3,
                ease=easing.in_out_expo,
            )
            final_waypoint = final_path.new_waypoint("final", character.input_coord)
            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE, final_path, EventHandler.Action.SET_LAYER, 0
            )

        unbubbled_chars = []
        for char_list in self.terminal.get_characters(sort_order=self.terminal.CharacterSort.ROW_BOTTOM_TO_TOP):
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
            bubble_origin = motion.Coord(
                random.randint(self.terminal.output_area.left, self.terminal.output_area.right),
                self.terminal.output_area.top,
            )
            new_bubble = Bubble(self, bubble_origin, bubble_group)
            self.bubbles.append(new_bubble)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        animating_bubbles: list[Bubble] = []
        steps_since_last_bubble = 0
        while animating_bubbles or self.animating_chars or self.bubbles:
            if self.bubbles and steps_since_last_bubble >= self.args.bubble_delay:
                next_bubble = self.bubbles.pop(0)
                next_bubble.activate()
                animating_bubbles.append(next_bubble)
                steps_since_last_bubble = 0
            steps_since_last_bubble += 1

            for bubble in animating_bubbles:
                if bubble.landed:
                    bubble.pop()
                    self.animating_chars.extend(bubble.characters)

            animating_bubbles = [bubble for bubble in animating_bubbles if not bubble.landed]
            self.animate_bubbles(animating_bubbles)
            self.animate_chars()
            self.terminal.print()

            # remove completed chars from animating chars
            self.animating_chars = [
                animating_char
                for animating_char in self.animating_chars
                if not animating_char.animation.active_scene_is_complete()
                or not animating_char.motion.movement_is_complete()
            ]

    def animate_bubbles(self, animating_bubbles: list[Bubble]) -> None:
        for bubble in animating_bubbles:
            bubble.move()

    def animate_chars(self) -> None:
        """Animates the characters by calling the move method and step animation."""
        for animating_char in self.animating_chars:
            animating_char.animation.step_animation()
            animating_char.motion.move()
