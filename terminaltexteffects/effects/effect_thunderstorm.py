"""Create a Thunderstorm in the terminal.

Classes:
    - Thunderstorm: Effect class for the Thunderstorm effect.
    - ThunderstormConfig: Configuration for the Thunderstorm effect.
    - ThunderstormIterator: Iterates over the effect. Does not normally need to be called directly.

"""

from __future__ import annotations

import random
import time
import typing
from dataclasses import dataclass

import terminaltexteffects as tte
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.argutils import ArgSpec, ParserSpec

if typing.TYPE_CHECKING:
    from terminaltexteffects.engine.base_character import EffectCharacter


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Get the command, effect class, and configuration class for the effect.

    Returns:
        tuple[str, type[BaseEffect], type[BaseConfig]]: The command name, effect class, and configuration class.

    """
    return "thunderstorm", Thunderstorm, ThunderstormConfig


@dataclass
class ThunderstormConfig(BaseConfig):
    """Effect configuration dataclass."""

    parser_spec: ParserSpec = ParserSpec(
        name="thunderstorm",
        help="Create a thunderstorm in the terminal.",
        description="thunderstorm | Create a thunderstorm in the terminal.",
        epilog=(
            "terminaltexteffects thunderstorm --lightning-color 68A3E8 "
            "--glowing-text-color EF5411 --text-glow-time 10 "
            "--raindrop-symbols '\\' '.' ',' --spark-symbols '*' '.' '`' "
            "--spark-glow-color ff4d00 --spark-glow-time 30 "
            "--storm-time 10 "
            "--final-gradient-stops 8A008A 00D1FF FFFFFF "
            "--final-gradient-steps 12 --final-gradient-frames 5 "
            "--final-gradient-direction vertical"
        ),
    )

    lightning_color: tte.Color = ArgSpec(
        name="--lightning-color",
        type=argutils.ColorArg.type_parser,
        default=tte.Color("#68A3E8"),
        metavar=argutils.ColorArg.METAVAR,
        help="Color for the lightning strike.",
    )  # pyright: ignore[reportAssignmentType]
    "Color: Color for the lightning strike."

    glowing_text_color: tte.Color = ArgSpec(
        name="--glowing-text-color",
        type=argutils.ColorArg.type_parser,
        default=tte.Color("#EF5411"),
        metavar=argutils.ColorArg.METAVAR,
        help="Color for the text when glowing after a lightning strike.",
    )  # pyright: ignore[reportAssignmentType]
    "Color: Color for the text when glowing after a lightning strike."

    text_glow_time: int = ArgSpec(
        name="--text-glow-time",
        type=argutils.PositiveInt.type_parser,
        default=6,
        metavar=argutils.PositiveInt.METAVAR,
        help="Duration, in number of frames, for the glowing/cooling animation for post-lightning text glow.",
    )  # pyright: ignore[reportAssignmentType]
    "int: Duration, in number of frames, for the glowing/cooling animation for post-lightning text glow."

    raindrop_symbols: tuple[str, ...] = ArgSpec(
        name="--raindrop-symbols",
        type=argutils.Symbol.type_parser,
        default=("\\", ".", ","),
        nargs="+",
        action=argutils.TupleAction,
        metavar=argutils.Symbol.METAVAR,
        help="Symbols to use for the raindrops.",
    )  # pyright: ignore[reportAssignmentType]
    "tuple[str, ...]: Symbols to use for the raindrops."

    spark_symbols: tuple[str, ...] = ArgSpec(
        name="--spark-symbols",
        type=argutils.Symbol.type_parser,
        default=("*", ".", "'"),
        nargs="+",
        action=argutils.TupleAction,
        metavar=argutils.Symbol.METAVAR,
        help="Symbols to use for the lightning impact sparks.",
    )  # pyright: ignore[reportAssignmentType]
    "tuple[str, ...]: Symbols to use for the lightning impact sparks."

    spark_glow_color: tte.Color = ArgSpec(
        name="--spark-glow-color",
        type=argutils.ColorArg.type_parser,
        default=tte.Color("#ff4d00"),
        metavar=argutils.ColorArg.METAVAR,
        help="Color for the spark glow after a lightning strike.",
    )  # pyright: ignore[reportAssignmentType]
    "Color: Color for the spark glow after a lightning strike."

    spark_glow_time: int = ArgSpec(
        name="--spark-glow-time",
        type=argutils.PositiveInt.type_parser,
        default=18,
        metavar=argutils.PositiveInt.METAVAR,
        help="Duration, in number of frames, for the cooling animation for post-lightning sparks.",
    )  # pyright: ignore[reportAssignmentType]
    "int: Duration, in number of frames, for the cooling animation for post-lightning sparks."

    storm_time: int = ArgSpec(
        name="--storm-time",
        type=argutils.PositiveInt.type_parser,
        default=12,
        metavar=argutils.PositiveInt.METAVAR,
        help="Duration, in seconds, the storm will occur.",
    )  # pyright: ignore[reportAssignmentType]
    "int: Duration, in seconds, the storm will occur."

    final_gradient_stops: tuple[tte.Color, ...] = ArgSpec(
        name="--final-gradient-stops",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=(tte.Color("#8A008A"), tte.Color("#00D1FF"), tte.Color("#FFFFFF")),
        metavar=argutils.ColorArg.METAVAR,
        help=(
            "Space separated, unquoted, list of colors for the character gradient (applied across the canvas). "
            "If only one color is provided, the characters will be displayed in that color."
        ),
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[Color, ...]: Space separated, unquoted, list of colors for the character gradient "
        "(applied across the canvas). If only one color is provided, the characters will be displayed in that color."
    )

    final_gradient_steps: tuple[int, ...] = ArgSpec(
        name="--final-gradient-steps",
        type=argutils.PositiveInt.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=(12,),
        metavar=argutils.PositiveInt.METAVAR,
        help=(
            "Space separated, unquoted, list of the number of gradient steps to use. More steps will "
            "create a smoother and longer gradient animation."
        ),
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[int, ...]: Space separated, unquoted, list of the number of gradient steps to use. More "
        "steps will create a smoother and longer gradient animation."
    )

    final_gradient_frames: int = ArgSpec(
        name="--final-gradient-frames",
        type=argutils.PositiveInt.type_parser,
        default=3,
        metavar=argutils.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step. Increase to slow down the gradient animation.",
    )  # pyright: ignore[reportAssignmentType]
    "int: Number of frames to display each gradient step. Increase to slow down the gradient animation."

    final_gradient_direction: tte.Gradient.Direction = ArgSpec(
        name="--final-gradient-direction",
        type=argutils.GradientDirection.type_parser,
        default=tte.Gradient.Direction.VERTICAL,
        metavar=argutils.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # pyright: ignore[reportAssignmentType]
    "Gradient.Direction : Direction of the final gradient."


class ThunderstormIterator(BaseEffectIterator[ThunderstormConfig]):
    """Effect iterator for the NamedEffect effect."""

    def __init__(self, effect: Thunderstorm) -> None:
        """Initialize the effect iterator.

        Args:
            effect (NamedEffect): The effect to iterate over.

        """
        super().__init__(effect)
        self.character_final_color_map: dict[tte.EffectCharacter, tte.Color] = {}
        self.delay = 0
        self.strike_progression_delay = 0
        self.rain_drops: list[tte.EffectCharacter] = []
        self.pending_strike_chars: list[EffectCharacter] = []
        self.available_strike_chars: list[EffectCharacter] = []
        self.active_strike_chars: list[EffectCharacter] = []
        self.pending_sparks: list[EffectCharacter] = []
        self.available_sparks: list[EffectCharacter] = []
        self.pending_glow_chars: list[EffectCharacter] = []
        self.strike_in_progress: bool = False
        self.flashing: bool = False
        self.strike_branch_chance = 0.05
        self.phase: str = "pre-storm"
        self.storm_start_time = time.monotonic()
        self.build()

    def build(self) -> None:
        """Build the effect."""
        final_gradient = tte.Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.canvas.text_bottom,
            self.terminal.canvas.text_top,
            self.terminal.canvas.text_left,
            self.terminal.canvas.text_right,
            self.config.final_gradient_direction,
        )
        self.build_raindrop_characters()
        self.build_spark_characters()
        self.build_strike_characters()

        # setup scenes on text characters
        all_chars = self.terminal.get_characters()
        for text_char in all_chars:
            faded_color = tte.Animation.adjust_color_brightness(
                final_gradient_mapping[text_char.input_coord],
                brightness=0.65,
            )
            # post-strike glow and cool scene
            glow_gradient = tte.Gradient(self.config.glowing_text_color, faded_color, steps=7)
            glow_scn = text_char.animation.new_scene(scene_id="glow")
            for color in glow_gradient:
                glow_scn.add_frame(symbol=text_char.input_symbol, colors=tte.ColorPair(fg=color), duration=6)

            # fade before storm scene
            fade_gradient = tte.Gradient(final_gradient_mapping[text_char.input_coord], faded_color, steps=7)
            fade_scn = text_char.animation.new_scene(scene_id="fade")
            for color in fade_gradient:
                fade_scn.add_frame(symbol=text_char.input_symbol, colors=tte.ColorPair(fg=color), duration=12)

            unfade_gradient = list(fade_gradient)[::-1]
            unfade_scn = text_char.animation.new_scene(scene_id="unfade")
            for color in unfade_gradient:
                unfade_scn.add_frame(symbol=text_char.input_symbol, colors=tte.ColorPair(fg=color), duration=12)

            # lightning flash scene
            lightning_flash_color = tte.Animation.adjust_color_brightness(
                final_gradient_mapping[text_char.input_coord],
                brightness=1.7,
            )
            strike_scn = text_char.animation.new_scene(scene_id="flash")
            flash_gradient = tte.Gradient(faded_color, lightning_flash_color, steps=7, loop=True)
            for color in flash_gradient:
                strike_scn.add_frame(symbol=text_char.input_symbol, colors=tte.ColorPair(fg=color), duration=6)

            self.terminal.set_character_visibility(text_char, is_visible=True)

        # setup a reference character callback to indicate when the pre-storm fade has completed
        def fade_complete(*_: typing.Any) -> None:
            self.phase = "storm"
            self.storm_start_time = time.monotonic()

        reference_char = all_chars[0]
        reference_char.event_handler.register_event(
            event=tte.Event.SCENE_COMPLETE,
            caller="fade",
            action=tte.Action.CALLBACK,
            target=tte.EventHandler.Callback(fade_complete),
        )

    def set_strike_in_progress_false(self, *_: typing.Any) -> None:
        """Reset the strike in progress flag."""
        self.strike_in_progress = False

    def make_char_glow(self, strike_char: tte.EffectCharacter) -> None:
        """Activate the 'cool' scene on any text character behind a strike character.

        Args:
            strike_char (tte.EffectCharacter): Strike character.

        """
        input_char = self.terminal.get_character_by_input_coord(strike_char.motion.current_coord)
        if input_char and input_char.is_visible:
            input_char.animation.activate_scene("glow")
            self.pending_glow_chars.append(input_char)

    def get_next_strike_char(self) -> tte.EffectCharacter:
        """Get the next available strike character.

        If no characters are available, new ones will be created.

        Returns:
            tte.EffectCharacter: The next available strike character.

        """
        if not self.available_strike_chars:
            self.build_strike_characters(20)
        strike_char = self.available_strike_chars.pop()
        strike_char.animation.scenes.clear()
        strike_char.event_handler.registered_events.clear()
        return strike_char

    def get_next_spark_char(self) -> tte.EffectCharacter:
        """Get the next available spark character.

        If no characters are available, new ones will be created.

        Returns:
            tte.EffectCharacter: The next available spark character.

        """
        if not self.available_sparks:
            self.build_spark_characters(20)
        spark_char = self.available_sparks.pop()
        spark_char.motion.paths.clear()
        spark_char.event_handler.registered_events.clear()
        return spark_char

    def setup_sparks_for_impact(self) -> None:
        """Configure sparks for the impact of a lightning strike."""
        # setup sparks at lightning strike bottom impact
        last_strike_char = self.pending_strike_chars[-1]
        for _ in range(random.randint(6, 10)):
            spark_char = self.get_next_spark_char()
            spark_char.motion.set_coordinate(last_strike_char.motion.current_coord)

            spark_path = spark_char.motion.new_path(
                speed=random.uniform(0.1, 0.25),
                ease=tte.easing.out_quint,
                hold_time=30,
            )
            spark_target = tte.Coord(
                column=last_strike_char.motion.current_coord.column + random.randint(4, 20) * random.choice((1, -1)),
                row=self.terminal.canvas.bottom,
            )
            bezier_column = last_strike_char.motion.current_coord.column - (
                (last_strike_char.motion.current_coord.column - spark_target.column) // 2
            )
            spark_path.new_waypoint(
                coord=spark_target,
                bezier_control=tte.Coord(column=bezier_column, row=random.randint(1, self.terminal.canvas.top)),
            )
            spark_char.event_handler.register_event(
                event=tte.Event.PATH_COMPLETE,
                caller=spark_path,
                action=tte.Action.CALLBACK,
                target=tte.EventHandler.Callback(lambda c: self.terminal.set_character_visibility(c, is_visible=False)),
            )
            spark_char.event_handler.register_event(
                event=tte.Event.PATH_COMPLETE,
                caller=spark_path,
                action=tte.Action.CALLBACK,
                target=tte.EventHandler.Callback(lambda c: self.available_sparks.append(c)),
            )

            spark_char.animation.activate_scene("glow")
            spark_char.motion.activate_path(spark_path)
            self.pending_sparks.append(spark_char)

    def setup_lightning_strike(self, branch_neighbor: tte.EffectCharacter | None = None) -> None:
        """Build a lightning strike effect."""
        if branch_neighbor is not None:
            column, row = branch_neighbor.motion.current_coord
            row = branch_neighbor.motion.current_coord.row
        else:
            column = random.randint(1, self.terminal.canvas.right)
            row = self.terminal.canvas.top

        while row >= self.terminal.canvas.bottom:
            if not self.available_strike_chars:
                self.build_strike_characters(20)
            if branch_neighbor is not None:
                if branch_neighbor.input_symbol == "/":
                    column += 1
                    symbol = random.choice(("|", "\\"))
                elif branch_neighbor.input_symbol == "\\":
                    column -= 1
                    symbol = random.choice(("|", "/"))
                else:
                    delta = random.choice((-1, 1))
                    column += delta
                    symbol = "\\" if delta == 1 else "/"
            else:
                symbol = random.choice(("\\", "/", "|"))

            strike_char = self.get_next_strike_char()
            strike_char.motion.set_coordinate(tte.Coord(column, row))
            strike_char.animation.set_appearance(symbol=symbol, colors=tte.ColorPair(fg=self.config.lightning_color))
            row -= 1
            if symbol == "\\":
                column += 1
            elif symbol == "/":
                column -= 1

            self.pending_strike_chars.append(strike_char)
            if random.random() < self.strike_branch_chance and branch_neighbor is None:
                self.strike_branch_chance -= 0.01
                self.setup_lightning_strike(branch_neighbor=strike_char)
            branch_neighbor = None
        self.strike_branch_chance = 0.05
        self.setup_sparks_for_impact()

    def build_raindrop_characters(self, count: int = 50) -> None:
        """Build raindrop characters."""
        for _ in range(count):
            spawn_column = random.randint(1 - self.terminal.canvas.top, self.terminal.canvas.right)
            rain_char = self.terminal.add_character(
                symbol=random.choice(self.config.raindrop_symbols),
                coord=tte.Coord(column=spawn_column - 1, row=self.terminal.canvas.top + 1),
            )
            rain_char.layer = 1
            rain_char.animation.set_appearance(
                symbol=rain_char.input_symbol,
                colors=tte.ColorPair(fg=tte.Color("#aaaaff")),
            )
            fall_path = rain_char.motion.new_path(path_id="fall", speed=1)
            fall_path.new_waypoint(
                tte.Coord(column=spawn_column + self.terminal.canvas.top, row=self.terminal.canvas.bottom - 1),
            )
            rain_char.motion.activate_path(fall_path)

            rain_char.event_handler.register_event(
                tte.Event.PATH_COMPLETE,
                fall_path,
                tte.Action.CALLBACK,
                rain_char.event_handler.Callback(lambda c: self.rain_drops.append(c)),
            )

            self.terminal.set_character_visibility(rain_char, is_visible=True)
            self.rain_drops.append(rain_char)

    def build_spark_characters(self, count: int = 100) -> None:
        """Build spark characters for the lightning strike effect."""
        spark_gradient = tte.Gradient(
            self.config.spark_glow_color,
            self.terminal.config.terminal_background_color,
            steps=7,
        )
        for _ in range(count):
            spark = self.terminal.add_character(
                symbol=random.choice(self.config.spark_symbols),
                coord=tte.Coord(1, 1),
            )
            spark.layer = 2

            spark_scn = spark.animation.new_scene(scene_id="glow", ease=tte.easing.in_circ)
            for color in spark_gradient:
                spark_scn.add_frame(
                    symbol=spark.input_symbol,
                    colors=tte.ColorPair(fg=color),
                    duration=self.config.spark_glow_time,
                )
            self.available_sparks.append(spark)

    def build_strike_characters(self, count: int = 200) -> None:
        """Build strike characters for the lightning strike effect."""
        for _ in range(count):
            strike_char = self.terminal.add_character(
                symbol="|",
                coord=tte.Coord(1, 1),
            )
            self.available_strike_chars.append(strike_char)

    def lightning_strike(self) -> None:
        """Trigger a lightning strike effect."""
        self.setup_lightning_strike()
        strike_base_color = self.config.lightning_color
        strike_flash_color = tte.Animation.adjust_color_brightness(strike_base_color, 1.7)
        strike_gradient = tte.Gradient(
            strike_base_color,
            strike_flash_color,
            steps=7,
            loop=True,
        )
        fade_gradient = tte.Gradient(strike_base_color, self.terminal.config.terminal_background_color, steps=6)
        layer = 1
        flash_ease = tte.easing.make_easing(0, 1.6, 1, random.uniform(-0.6, 0.4))
        for strike_char in self.pending_strike_chars:
            flash_scn = strike_char.animation.new_scene(scene_id="flash", ease=flash_ease)
            for color in strike_gradient:
                flash_scn.add_frame(
                    symbol=strike_char.animation.current_character_visual.symbol,
                    colors=tte.ColorPair(fg=color),
                    duration=6,
                )
            fade_scn = strike_char.animation.new_scene(scene_id="fade")
            for color in fade_gradient:
                fade_scn.add_frame(
                    symbol=strike_char.animation.current_character_visual.symbol,
                    colors=tte.ColorPair(fg=color),
                    duration=2,
                )
            strike_char.layer = layer
            strike_char.event_handler.register_event(
                event=tte.Event.SCENE_COMPLETE,
                caller=flash_scn,
                action=tte.Action.ACTIVATE_SCENE,
                target=fade_scn,
            )
            strike_char.event_handler.register_event(
                event=tte.Event.SCENE_COMPLETE,
                caller=fade_scn,
                action=tte.Action.CALLBACK,
                target=tte.EventHandler.Callback(lambda c: self.terminal.set_character_visibility(c, is_visible=False)),
            )
            strike_char.event_handler.register_event(
                event=tte.Event.SCENE_COMPLETE,
                caller=fade_scn,
                action=tte.Action.CALLBACK,
                target=tte.EventHandler.Callback(self.make_char_glow),
            )
            strike_char.event_handler.register_event(
                event=tte.Event.SCENE_COMPLETE,
                caller=fade_scn,
                action=tte.Action.CALLBACK,
                target=tte.EventHandler.Callback(lambda c: self.available_strike_chars.append(c)),
            )

        for text_char in self.terminal.get_characters():
            flash_scene = text_char.animation.query_scene("flash")
            flash_scene.ease = flash_ease  # pyright: ignore[reportOptionalMemberAccess]

    def step_lightning_strike(self) -> None:
        """Progress the lightning strike effect."""
        if self.strike_progression_delay:
            self.strike_progression_delay -= 1
            return
        if self.pending_strike_chars:
            for _ in range(random.randint(1, 3)):
                if not self.pending_strike_chars:
                    break
                next_strike_char = self.pending_strike_chars.pop(0)
                self.active_strike_chars.append(next_strike_char)
                self.terminal.set_character_visibility(next_strike_char, is_visible=True)
                self.strike_progression_delay = 1

                # if the last strike_char was activated, activate the sparks
                # and setup the post-fade callback to indicate the strike has
                # ended
                if not self.pending_strike_chars:
                    while self.pending_sparks:
                        spark = self.pending_sparks.pop()
                        self.terminal.set_character_visibility(spark, is_visible=True)
                        self.active_characters.add(spark)
                    next_strike_char.event_handler.register_event(
                        event=tte.Event.SCENE_COMPLETE,
                        caller="fade",
                        action=tte.Action.CALLBACK,
                        target=tte.EventHandler.Callback(self.set_strike_in_progress_false),
                    )

                    # activate the flash scene on all strike chars and text
                    for strike_char in self.active_strike_chars:
                        strike_char.animation.activate_scene("flash")
                        self.active_characters.add(strike_char)
                    self.active_strike_chars.clear()

                    for text_char in self.terminal.get_characters():
                        text_char.animation.activate_scene("flash")
                        self.active_characters.add(text_char)

    def rain(self) -> None:
        """Handle the rain effect."""
        if self.rain_drops:
            if not self.delay:
                for _ in range(random.randint(1, 6)):
                    if not self.rain_drops:
                        self.build_raindrop_characters(20)
                    drop = self.rain_drops.pop(random.randint(0, len(self.rain_drops) - 1))
                    drop.motion.set_coordinate(drop.input_coord)
                    fall_path = drop.motion.query_path("fall")
                    fall_path.speed = random.uniform(0.5, 1.5)
                    drop.motion.activate_path(fall_path)
                    self.active_characters.add(drop)
                self.delay = random.randint(1, 7)
            else:
                self.delay -= 1

    def pre_storm_text_fade(self) -> None:
        """Activate the fade effect for all text characters before the storm."""
        for char in self.terminal.get_characters():
            char.animation.activate_scene("fade")
            self.active_characters.add(char)

    def post_storm_text_fade_in(self) -> None:
        """Active the fade in scene for all text characters after the storm clears."""
        for char in self.terminal.get_characters():
            char.animation.activate_scene("unfade")
            self.active_characters.add(char)

    def __next__(self) -> str:
        """Return the next frame of the effect."""
        if self.active_characters or self.phase != "complete":
            if self.phase == "pre-storm":
                self.pre_storm_text_fade()
                self.phase = "waiting"
            elif self.phase == "storm":
                self.rain()
                if not self.strike_in_progress and random.random() < 0.008:
                    self.strike_in_progress = True
                    self.lightning_strike()
                if self.strike_in_progress:
                    self.step_lightning_strike()

                for char in self.pending_glow_chars:
                    self.active_characters.add(char)
                self.pending_glow_chars.clear()
                if (time.monotonic() - self.storm_start_time) >= self.config.storm_time and not self.strike_in_progress:
                    self.post_storm_text_fade_in()
                    self.phase = "complete"
            self.update()
            return self.frame
        raise StopIteration


class Thunderstorm(BaseEffect[ThunderstormConfig]):
    """Create a thunderstorm in the terminal.

    Rain falls across the canvas. Lightning strikes illuminate the scene and
    cause sparks at the point of impact. Characters struck by lightning glow.
    """

    @property
    def _config_cls(self) -> type[ThunderstormConfig]:
        return ThunderstormConfig

    @property
    def _iterator_cls(self) -> type[ThunderstormIterator]:
        return ThunderstormIterator
