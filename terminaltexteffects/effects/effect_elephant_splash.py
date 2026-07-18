"""A playful elephant splashes water to reveal the input text."""

from __future__ import annotations

import typing
from dataclasses import dataclass
from enum import Enum, auto

from terminaltexteffects.engine.base_character import EffectCharacter, EventHandler
from terminaltexteffects.engine.base_config import (
    BaseConfig,
    FinalGradientDirectionArg,
    FinalGradientFramesArg,
    FinalGradientStepsArg,
    FinalGradientStopsArg,
)
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.effect_support.particles import ParticlePool
from terminaltexteffects.utils import argutils, easing, geometry
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.graphics import Color, ColorPair, Gradient

if typing.TYPE_CHECKING:
    from terminaltexteffects.engine.terminal import Terminal


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command, effect class, and configuration class."""
    return "elephantsplash", ElephantSplash, ElephantSplashConfig


@dataclass
class ElephantSplashConfig(BaseConfig):
    """Configuration for the Elephant Splash effect.

    Attributes:
        elephant_color: Primary color of the elephant.
        elephant_highlight_color: Highlight color for the elephant's expressive details.
        water_colors: Colors used by droplets and the initial branding splash.
        movement_speed: Speed of the elephant's entrance and exit paths.
        final_gradient_stops: Colors used for the completed branding gradient.
        final_gradient_steps: Number of steps between final gradient stops.
        final_gradient_frames: Frames displayed for each branding cooling step.
        final_gradient_direction: Direction of the completed branding gradient.
        final_hold_frames: Frames to hold the completed branding before stopping.

    """

    parser_spec: argutils.ParserSpec = argutils.ParserSpec(
        name="elephantsplash",
        help="A playful elephant splashes water to reveal the input text.",
        description="elephantsplash | A playful elephant splashes water to reveal the input text.",
        epilog=(
            "Example: terminaltexteffects --canvas-width 0 --canvas-height 0 --anchor-canvas c "
            "--anchor-text c elephantsplash"
        ),
    )

    elephant_color: Color = argutils.ArgSpec(
        name="--elephant-color",
        type=argutils.ColorArg.type_parser,
        default=Color("#8B5CF6"),
        metavar=argutils.ColorArg.METAVAR,
        help="Primary color of the elephant.",
    )  # pyright: ignore[reportAssignmentType]
    elephant_highlight_color: Color = argutils.ArgSpec(
        name="--elephant-highlight-color",
        type=argutils.ColorArg.type_parser,
        default=Color("#C4B5FD"),
        metavar=argutils.ColorArg.METAVAR,
        help="Highlight color used for the elephant's ears, eye, and smile.",
    )  # pyright: ignore[reportAssignmentType]
    water_colors: tuple[Color, ...] = argutils.ArgSpec(
        name="--water-colors",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=(Color("#38BDF8"), Color("#7DD3FC"), Color("#E0F2FE")),
        metavar=argutils.ColorArg.METAVAR,
        help="Colors used for the water droplets and splash reveal.",
    )  # pyright: ignore[reportAssignmentType]
    movement_speed: float = argutils.ArgSpec(
        name="--movement-speed",
        type=argutils.PositiveFloat.type_parser,
        default=0.35,
        metavar=argutils.PositiveFloat.METAVAR,
        help="Speed of the elephant's entrance and exit.",
    )  # pyright: ignore[reportAssignmentType]
    final_gradient_stops: tuple[Color, ...] = FinalGradientStopsArg(
        default=(Color("#8B5CF6"), Color("#C4B5FD"), Color("#F5F3FF")),
    )  # pyright: ignore[reportAssignmentType]
    final_gradient_steps: tuple[int, ...] | int = FinalGradientStepsArg(default=12)  # pyright: ignore[reportAssignmentType]
    final_gradient_frames: int = FinalGradientFramesArg(default=4)  # pyright: ignore[reportAssignmentType]
    final_gradient_direction: Gradient.Direction = FinalGradientDirectionArg(
        default=Gradient.Direction.RADIAL,
    )  # pyright: ignore[reportAssignmentType]
    final_hold_frames: int = argutils.ArgSpec(
        name="--final-hold-frames",
        type=argutils.NonNegativeInt.type_parser,
        default=120,
        metavar=argutils.NonNegativeInt.METAVAR,
        help="Number of frames to hold the completed branding. Zero still emits one clean final frame.",
    )  # pyright: ignore[reportAssignmentType]


class ElephantSplashIterator(BaseEffectIterator[ElephantSplashConfig]):
    """Iterator for the Elephant Splash effect."""

    DRINK_FRAMES: typing.ClassVar[int] = 72
    CELEBRATE_FRAMES: typing.ClassVar[int] = 48

    _FULL_TRUNK_DOWN: typing.ClassVar[tuple[str, ...]] = (
        '              _..---""""---.._',
        "         _.-''                 ``-.",
        "      .-'                         `.",
        "     /                       .--.    \\__",
        "~\\  /                       /    \\  o   `.",
        "  \\|                       | (  ) |    `.   \\",
        "   |                        \\    /      > |   |",
        "   |                         `--'         |   |",
        "   |                                 |     |",
        "   |       ___                       |     |",
        "    \\___.-'   `-.____                |     |",
        "      |  |    |  |     |  |    |  |     |",
        "      |  |    |  |     |  |    |  |     |",
        "      |  |    |  |     |  |    |  |    /",
        "     /__\\   /__\\    /__\\   /__\\   \\__/",
    )
    _FULL_TRUNK_MID: typing.ClassVar[tuple[str, ...]] = (
        '              _..---""""---.._',
        "         _.-''                 ``-.",
        "      .-'                         `.",
        "     /                       .--.    \\__",
        "~\\  /                       /    \\  o   `-.",
        "  \\|                       | (  ) |    `.     `-.",
        "   |                        \\    /      >      `--~",
        "   |                         `--'       |",
        "   |                                    |",
        "   |       ___                          |",
        "    \\___.-'   `-.____                   |",
        "      |  |    |  |     |  |    |  |",
        "      |  |    |  |     |  |    |  |",
        "      |  |    |  |     |  |    |  |",
        "     /__\\   /__\\    /__\\   /__\\",
    )
    _FULL_TRUNK_UP: typing.ClassVar[tuple[str, ...]] = (
        '              _..---""""---.._            __.-~',
        "         _.-''                 ``-.       .'  `.",
        "      .-'                         `.    /      |",
        "     /                       .--.    \\__/      /",
        "~\\  /                       /    \\  o       _.'",
        "  \\|                       | (  ) |  ___.-'",
        "   |                        \\    /  / >",
        "   |                         `--'       |",
        "   |                                    |",
        "   |       ___                          |",
        "    \\___.-'   `-.____                   |",
        "      |  |    |  |     |  |    |  |",
        "      |  |    |  |     |  |    |  |",
        "      |  |    |  |     |  |    |  |",
        "     /__\\   /__\\    /__\\   /__\\",
    )
    _FULL_TRUNK_UP_WIGGLE: typing.ClassVar[tuple[str, ...]] = (
        '              _..---""""---.._            __.-~',
        "         _.-''                 ``-.       .'  `.",
        "      .-'                         `.    /      |",
        "     /                       .--.    \\__/      /",
        "~\\  /                       /    \\  o       _.'",
        "  \\|                       |((  ))|  ___.-'",
        "   |                        \\    /  / >",
        "   |                         `--'       |",
        "   |                                    |",
        "   |       ___                          |",
        "    \\___.-'   `-.____                   |",
        "      |  |    |  |     |  |    |  |",
        "      |  |    |  |     |  |    |  |",
        "      |  |    |  |     |  |    |  |",
        "     /__\\   /__\\    /__\\   /__\\",
    )
    FULL_POSES: typing.ClassVar[dict[str, tuple[str, ...]]] = {
        "walk_1": _FULL_TRUNK_DOWN,
        "walk_2": (
            *_FULL_TRUNK_DOWN[:-4],
            "      |  |     | |     |  |     | |     |",
            "       \\ |     | |      \\ |     | |     |",
            "       | |     | |      | |     | |    /",
            "      /__\\   /__\\     /__\\   /__\\   \\__/",
        ),
        "walk_3": (
            *_FULL_TRUNK_DOWN[:-4],
            "       | |     |  |     | |     |  |     |",
            "       | |      \\ |     | |      \\ |     |",
            "       | |      | |     | |      | |    /",
            "      /__\\    /__\\   /__\\    /__\\  \\__/",
        ),
        "walk_4": (
            *_FULL_TRUNK_DOWN[:-4],
            "      |  |     | |      | |     |  |     |",
            "       \\ |     | |      | |      \\ |     |",
            "       | |     | |      | |      | |    /",
            "      /__\\   /__\\     /__\\    /__\\  \\__/",
        ),
        "drink_1": (*_FULL_TRUNK_DOWN[:-1], "     /__\\   /__\\    /__\\   /__\\   \\__~"),
        "drink_2": (*_FULL_TRUNK_DOWN[:-1], "     /__\\   /__\\    /__\\   /__\\   \\__o"),
        "drink_3": (*_FULL_TRUNK_DOWN[:-1], "     /__\\   /__\\    /__\\   /__\\   \\__."),
        "raise_1": _FULL_TRUNK_DOWN,
        "raise_2": _FULL_TRUNK_MID,
        "raise_3": _FULL_TRUNK_UP,
        "spray_1": _FULL_TRUNK_UP,
        "spray_2": _FULL_TRUNK_UP_WIGGLE,
        "wiggle_1": _FULL_TRUNK_UP,
        "wiggle_2": _FULL_TRUNK_UP_WIGGLE,
    }
    FULL_TRUNK_TIP_ROWS: typing.ClassVar[dict[str, int]] = {
        "walk_1": 14,
        "walk_2": 14,
        "walk_3": 14,
        "walk_4": 14,
        "drink_1": 14,
        "drink_2": 14,
        "drink_3": 14,
        "raise_1": 14,
        "raise_2": 6,
        "raise_3": 0,
        "spray_1": 0,
        "spray_2": 0,
        "wiggle_1": 0,
        "wiggle_2": 0,
    }
    COMPACT_POSES: typing.ClassVar[dict[str, tuple[str, ...]]] = {
        "walk_1": ("   __", " /'  '-.", "| (o)  |__", " \\   /  ')", "  /_\\ /_\\"),
        "walk_2": ("   __", " /'  '-.", "| (o)  |__", " \\   /  ')", "  _/\\ /_\\"),
        "walk_3": ("   __", " /'  '-.", "| (o)  |__", " \\   /  ')", "  /_\\ _/\\"),
        "walk_4": ("   __", " /'  '-.", "| (o)  |__", " \\   /  ')", "  _/\\ _/\\"),
        "drink_1": ("   __", " /'  '-.", "| (o)    \\", " \\    __ \\", "  /_\\ /_\\ \\~"),
        "drink_2": ("   __", " /'  '-.", "| (o)    \\", " \\    __ \\", "  /_\\ /_\\ \\o"),
        "drink_3": ("   __", " /'  '-.", "| (o)    \\", " \\    __ \\", "  /_\\ /_\\ \\."),
        "raise_1": ("   __", " /'  '-.", "| (o)   \\_", " \\    __/'", "  /_\\ /_\\"),
        "raise_2": ("   __", " /'  '-.", "| (o)    \\__", " \\    __/'", "  /_\\ /_\\"),
        "raise_3": ("   __", " /'  '-.", "| (o)   \\___", " \\    __/'", "  /_\\ /_\\"),
        "spray_1": ("   __", " /'  '-.", "| (o)   \\___", " \\    __/'", "  /_\\ /_\\"),
        "spray_2": ("   __", " /' ((-.", "| (o)   \\___", " \\    __/'", "  /_\\ /_\\"),
        "wiggle_1": ("   __", " /'  '-.", "| (o)   \\___", " \\    __/'", "  /_\\ /_\\"),
        "wiggle_2": ("   __", " /' ((-.", "| (o)   \\___", " \\    __/'", "  /_\\ /_\\"),
    }
    COMPACT_TRUNK_TIP_ROWS: typing.ClassVar[dict[str, int]] = {
        "walk_1": 3,
        "walk_2": 3,
        "walk_3": 3,
        "walk_4": 3,
        "drink_1": 4,
        "drink_2": 4,
        "drink_3": 4,
        "raise_1": 2,
        "raise_2": 2,
        "raise_3": 2,
        "spray_1": 2,
        "spray_2": 2,
        "wiggle_1": 2,
        "wiggle_2": 2,
    }

    class Elephant:
        """A rigid, pose-driven group of effect-owned characters."""

        def __init__(
            self,
            terminal: Terminal,
            config: ElephantSplashConfig,
            poses: dict[str, tuple[str, ...]],
            trunk_tip_rows: dict[str, int],
        ) -> None:
            """Create a pose-driven elephant on the supplied terminal."""
            self.terminal = terminal
            self.config = config
            self.height = max(len(pose) for pose in poses.values())
            self.width = max(len(row) for pose in poses.values() for row in pose)
            self.poses = {
                name: tuple(row.ljust(self.width) for row in (*pose, *("",) * (self.height - len(pose))))
                for name, pose in poses.items()
            }
            self.trunk_tip_offsets = {
                name: Coord(
                    max(column for column, symbol in enumerate(self.poses[name][row_index]) if symbol != " "),
                    self.height - row_index - 1,
                )
                for name, row_index in trunk_tip_rows.items()
            }
            baseline = terminal.canvas.bottom
            self.start_coord = Coord(terminal.canvas.left - self.width, baseline)
            self.anchor = terminal.add_character(" ", self.start_coord)
            target_column = max(
                terminal.canvas.left,
                min(terminal.canvas.center_column - self.width // 2, terminal.canvas.right - self.width + 1),
            )
            self.target_coord = Coord(target_column, baseline)
            self.character_offsets: dict[EffectCharacter, Coord] = {}
            occupied_offsets = {
                Coord(column, self.height - row_index - 1)
                for pose in self.poses.values()
                for row_index, row in enumerate(pose)
                for column, symbol in enumerate(row)
                if symbol != " "
            }
            for offset in sorted(occupied_offsets, key=lambda coord: (coord.row, coord.column)):
                character = terminal.add_character(" ", self._coord_for_offset(offset))
                character.layer = 2
                terminal.set_character_visibility(character, is_visible=True)
                self.character_offsets[character] = offset
            self.characters = list(self.character_offsets)
            self.current_pose = "walk_1"
            entrance_path = self.anchor.motion.new_path(path_id="walk_in", speed=config.movement_speed)
            entrance_path.new_waypoint(self.target_coord)
            self.anchor.motion.activate_path(entrance_path)
            self.apply_pose(self.current_pose)

        def _coord_for_offset(self, offset: Coord, anchor_coord: Coord | None = None) -> Coord:
            anchor_coord = anchor_coord or self.anchor.motion.current_coord
            return Coord(
                anchor_coord.column + offset.column,
                anchor_coord.row + offset.row,
            )

        def trunk_coord_for_pose(self, pose_name: str, anchor_coord: Coord | None = None) -> Coord:
            """Return the declared trunk-tip coordinate for one pose."""
            return self._coord_for_offset(self.trunk_tip_offsets[pose_name], anchor_coord)

        def apply_pose(self, pose_name: str) -> None:
            """Apply one fixed ASCII pose to all sprite characters."""
            pose = self.poses[pose_name]
            shadow_color = self.characters[0].animation.adjust_color_brightness(self.config.elephant_color, 0.65)
            for character, offset in self.character_offsets.items():
                row_index = self.height - offset.row - 1
                symbol = pose[row_index][offset.column]
                if symbol in {"o", ">"} or "(" in pose[row_index][max(0, offset.column - 1) : offset.column + 2]:
                    color = self.config.elephant_highlight_color
                elif offset.row <= 1:
                    color = shadow_color
                else:
                    color = self.config.elephant_color
                character.animation.set_appearance(symbol, ColorPair(fg=color))
                character.motion.set_coordinate(self._coord_for_offset(offset))
            self.current_pose = pose_name

        def tick_walk(self, frame: int) -> None:
            """Advance the anchor and apply the corresponding walking pose."""
            self.anchor.motion.move()
            pose_name = f"walk_{(frame // 8) % 4 + 1}"
            self.apply_pose(pose_name)

        def start_walk_out(self) -> None:
            """Activate the path that carries the elephant beyond the right edge."""
            exit_path = self.anchor.motion.new_path(path_id="walk_out", speed=self.config.movement_speed)
            exit_path.new_waypoint(Coord(self.terminal.canvas.right + 1, self.anchor.motion.current_coord.row))
            self.anchor.motion.activate_path(exit_path)

        def hide(self) -> None:
            """Hide every visible sprite character."""
            for character in self.characters:
                self.terminal.set_character_visibility(character, is_visible=False)

        @property
        def trunk_coord(self) -> Coord:
            """Return the declared trunk-tip coordinate in the current pose."""
            return self.trunk_coord_for_pose(self.current_pose)

    class Puddle:
        """A small effect-owned water source resting on the canvas floor."""

        def __init__(
            self,
            terminal: Terminal,
            colors: tuple[Color, ...],
            width: int,
            height: int,
            near_column: int,
        ) -> None:
            """Create a visible, canvas-bounded row of water characters."""
            self.terminal = terminal
            self.colors = colors
            self.width = width
            self.height = height
            self.start_column = max(terminal.canvas.left, min(near_column, terminal.canvas.right - width + 1))
            symbol_rows = ("  .~~~~~~~~~.  ", ".~~~~~~~~~~~~~.") if height == 2 else ("~~~",)
            self.characters: list[EffectCharacter] = []
            for row_offset, symbols in enumerate(reversed(symbol_rows)):
                for column_offset, symbol in enumerate(symbols):
                    character = terminal.add_character(
                        symbol,
                        Coord(self.start_column + column_offset, terminal.canvas.bottom + row_offset),
                    )
                    character.layer = 2
                    character.animation.set_appearance(
                        symbol,
                        ColorPair(fg=colors[(row_offset + column_offset) % len(colors)]),
                    )
                    terminal.set_character_visibility(character, is_visible=True)
                    self.characters.append(character)

        @property
        def visible_count(self) -> int:
            """Return the number of water characters currently on screen."""
            return sum(character in self.terminal._visible_characters for character in self.characters)

        def ripple(self, frame: int) -> None:
            """Animate bright surface ripples without changing the puddle footprint."""
            ripple_step = frame // 6
            bubble_column = 2 + ripple_step * 2 % max(1, self.width - 4)
            for index, character in enumerate(self.characters):
                row_offset, column_offset = divmod(index, self.width)
                if self.height == 1:
                    symbol = "~" if (column_offset + ripple_step) % 2 else "_"
                elif row_offset == 0:
                    symbol = "." if column_offset in {0, self.width - 1} else "~_"[(column_offset + ripple_step) % 2]
                elif column_offset == bubble_column:
                    symbol = "o"
                elif 2 <= column_offset < self.width - 2 and (column_offset + ripple_step) % 3 == 0:
                    symbol = "~"
                else:
                    symbol = " "
                color = self.colors[(row_offset + column_offset + ripple_step) % len(self.colors)]
                character.animation.set_appearance(symbol, ColorPair(fg=color))

        def shrink_to(self, visible_count: int) -> None:
            """Keep a centred subset visible to make the puddle contract."""
            visible_column_count = min(
                self.width,
                (max(0, visible_count) + self.height - 1) // self.height,
            )
            center = (self.width - 1) / 2
            visible_columns = set(
                sorted(range(self.width), key=lambda column: abs(column - center))[:visible_column_count],
            )
            for index, character in enumerate(self.characters):
                _, column_offset = divmod(index, self.width)
                self.terminal.set_character_visibility(character, is_visible=column_offset in visible_columns)

    class Phase(Enum):
        """Ordered phases in the Elephant Splash choreography."""

        WALK_IN = auto()
        DRINK = auto()
        RAISE_TRUNK = auto()
        SPLASH = auto()
        REVEAL = auto()
        CELEBRATE = auto()
        WALK_OUT = auto()
        HOLD = auto()
        COMPLETE = auto()

    def __init__(self, effect: ElephantSplash) -> None:
        """Build the responsive sprite, branding scenes, and particle pool."""
        super().__init__(effect)
        full_sprite_width = max(len(row) for pose in self.FULL_POSES.values() for row in pose)
        full_sprite_height = max(len(pose) for pose in self.FULL_POSES.values())
        if self.terminal.canvas.width >= full_sprite_width and self.terminal.canvas.height >= full_sprite_height:
            self.sprite_mode = "full"
        elif self.terminal.canvas.width >= 12 and self.terminal.canvas.height >= 6:
            self.sprite_mode = "compact"
        else:
            self.sprite_mode = "fallback"
        self.phase = self.Phase.SPLASH if self.sprite_mode == "fallback" else self.Phase.WALK_IN
        self.input_characters = self.terminal.get_characters()
        self.reveal_groups: list[list[EffectCharacter]] = [[] for _ in range(12)]
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self._build_branding_reveal()
        pose_set = self.FULL_POSES if self.sprite_mode == "full" else self.COMPACT_POSES
        trunk_tip_rows = self.FULL_TRUNK_TIP_ROWS if self.sprite_mode == "full" else self.COMPACT_TRUNK_TIP_ROWS
        self.elephant = (
            self.Elephant(self.terminal, self.config, pose_set, trunk_tip_rows)
            if self.sprite_mode != "fallback"
            else None
        )
        puddle_width = 3 if self.sprite_mode == "compact" else 15
        puddle_height = 1 if self.sprite_mode == "compact" else 2
        drinking_tip = (
            self.elephant.trunk_coord_for_pose("drink_1", self.elephant.target_coord)
            if self.elephant is not None
            else None
        )
        self.puddle = (
            self.Puddle(
                self.terminal,
                self.config.water_colors,
                puddle_width,
                puddle_height,
                drinking_tip.column + 1,
            )
            if drinking_tip is not None
            else None
        )
        self.intake_characters = self._make_intake_characters()
        self.water_pool = self._make_water_pool() if self.sprite_mode != "fallback" else None
        self.phase_frame = 0
        self.droplets_emitted = 0
        self.next_reveal_group = 0

    def _make_intake_characters(self) -> list[EffectCharacter]:
        """Create a small hidden stream used while the elephant drinks."""
        if self.elephant is None or self.puddle is None:
            return []
        count = 3 if self.sprite_mode == "full" else 1
        origin = Coord(
            self.puddle.start_column + self.puddle.width // 2,
            self.terminal.canvas.bottom + self.puddle.height - 1,
        )
        intake_characters: list[EffectCharacter] = []
        for index in range(count):
            character = self.terminal.add_character((".", "o", "*")[index], origin)
            character.layer = 3
            character.animation.set_appearance(
                (".", "o", "*")[index],
                ColorPair(fg=self.config.water_colors[index % len(self.config.water_colors)]),
            )
            self.terminal.set_character_visibility(character, is_visible=False)
            intake_characters.append(character)
        return intake_characters

    def _animate_intake(self) -> None:
        """Pull a cycling line of bubbles from the puddle toward the trunk."""
        assert self.elephant is not None
        assert self.puddle is not None
        origin = Coord(
            self.puddle.start_column + self.puddle.width // 2,
            self.terminal.canvas.bottom + self.puddle.height - 1,
        )
        destination = self.elephant.trunk_coord
        for index, character in enumerate(self.intake_characters):
            progress = ((self.phase_frame // 3 + index * 3) % 10 + 1) / 10
            coord = Coord(
                round(origin.column + (destination.column - origin.column) * progress),
                round(origin.row + (destination.row - origin.row) * progress),
            )
            character.motion.set_coordinate(coord)
            symbol = (".", "o", "*")[(self.phase_frame // 4 + index) % 3]
            color = self.config.water_colors[(self.phase_frame // 6 + index) % len(self.config.water_colors)]
            character.animation.set_appearance(symbol, ColorPair(fg=color))
            self.terminal.set_character_visibility(character, is_visible=True)

    def _build_branding_reveal(self) -> None:
        """Prepare hidden input characters and their bounded radial reveal scenes."""
        final_gradient = Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_color_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.canvas.text_bottom,
            self.terminal.canvas.text_top,
            self.terminal.canvas.text_left,
            self.terminal.canvas.text_right,
            self.config.final_gradient_direction,
        )
        water_start = self.config.water_colors[0]
        water_finish = self.config.water_colors[-1]
        for character in self.input_characters:
            character.layer = 1
            self.terminal.set_character_visibility(character, is_visible=False)
            self.character_final_color_map[character] = final_color_mapping[character.input_coord]
            normalized_distance = geometry.find_normalized_distance_from_center(
                self.terminal.canvas.text_bottom,
                self.terminal.canvas.text_top,
                self.terminal.canvas.text_left,
                self.terminal.canvas.text_right,
                character.input_coord,
            )
            band_index = min(int(normalized_distance * len(self.reveal_groups)), len(self.reveal_groups) - 1)
            self.reveal_groups[band_index].append(character)

            reveal_scene = character.animation.new_scene(scene_id="reveal")
            reveal_scene.add_frame(".", 2, colors=ColorPair(fg=water_start))
            reveal_scene.add_frame("*", 2, colors=ColorPair(fg=water_finish))
            if self.terminal.config.existing_color_handling == "dynamic":
                fg_gradient = (
                    Gradient(water_finish, character.animation.input_fg_color, steps=8)
                    if character.animation.input_fg_color
                    else None
                )
                bg_gradient = (
                    Gradient(water_finish, character.animation.input_bg_color, steps=8)
                    if character.animation.input_bg_color
                    else None
                )
                if fg_gradient or bg_gradient:
                    reveal_scene.apply_gradient_to_symbols(
                        character.input_symbol,
                        self.config.final_gradient_frames,
                        fg_gradient=fg_gradient,
                        bg_gradient=bg_gradient,
                    )
                else:
                    reveal_scene.add_frame(
                        character.input_symbol,
                        self.config.final_gradient_frames,
                        colors=ColorPair(),
                    )
            else:
                cooling_gradient = Gradient(
                    water_finish,
                    self.character_final_color_map[character],
                    steps=8,
                )
                reveal_scene.apply_gradient_to_symbols(
                    character.input_symbol,
                    self.config.final_gradient_frames,
                    fg_gradient=cooling_gradient,
                )

    def _make_water_pool(self) -> ParticlePool:
        """Create a fixed-size pool of reusable water droplets."""

        def initialize_droplet(particle: EffectCharacter) -> None:
            particle.layer = 3
            droplet_scene = particle.animation.new_scene(scene_id="droplet", is_looping=True)
            for water_color in self.config.water_colors:
                droplet_scene.add_frame(particle.input_symbol, 3, colors=ColorPair(fg=water_color))

        droplet_count = 16 if self.sprite_mode == "compact" else min(48, max(24, (len(self.input_characters) + 1) // 2))
        return ParticlePool(
            self.terminal,
            self.active_characters,
            symbols=(".", "o", "*", "'"),
            initial_count=droplet_count,
            max_size=droplet_count,
            initializer=initialize_droplet,
        )

    def _emit_droplet(self) -> None:
        """Emit one curved droplet from the elephant's trunk."""
        if self.elephant is None or self.water_pool is None:
            return
        origin = self.elephant.trunk_coord
        ordered_targets = sorted(
            self.input_characters,
            key=lambda character: (character.input_coord.column, character.input_coord.row),
        )
        target_character = ordered_targets[self.droplets_emitted % len(ordered_targets)]
        target = target_character.input_coord
        if target == origin:
            alternate_column = (
                self.terminal.canvas.right if origin.column != self.terminal.canvas.right else self.terminal.canvas.left
            )
            target = Coord(alternate_column, target.row)

        def configure_droplet(particle: EffectCharacter) -> None:
            control_row = min(
                self.terminal.canvas.top,
                max(origin.row, target.row) + 3 + self.droplets_emitted % 4,
            )
            control = Coord((origin.column + target.column) // 2, control_row)
            droplet_path = particle.motion.new_path(speed=1.6, ease=easing.out_sine)
            droplet_path.new_waypoint(target, bezier_control=control)
            particle.motion.activate_path(droplet_path)
            particle.animation.activate_scene("droplet")
            self.water_pool.reclaim_on_event(
                particle,
                droplet_path,
                event=EventHandler.Event.PATH_COMPLETE,
            )

        emitted = self.water_pool.emit(origin, on_emit=configure_droplet)
        if emitted is not None:
            self.droplets_emitted += 1

    def __next__(self) -> str:
        """Advance and render one frame of the effect."""
        phase_handlers: dict[ElephantSplashIterator.Phase, typing.Callable[[], None]] = {
            self.Phase.WALK_IN: self._step_walk_in,
            self.Phase.DRINK: self._step_drink,
            self.Phase.RAISE_TRUNK: self._step_raise_trunk,
            self.Phase.SPLASH: self._step_splash,
            self.Phase.REVEAL: self._step_reveal,
            self.Phase.CELEBRATE: self._step_celebrate,
            self.Phase.WALK_OUT: self._step_walk_out,
            self.Phase.HOLD: self._step_hold,
        }
        handler = phase_handlers.get(self.phase)
        if handler is None:
            raise StopIteration
        handler()
        return self.frame

    def _step_walk_in(self) -> None:
        """Advance the walking entrance by one frame."""
        assert self.elephant is not None
        assert self.puddle is not None
        self.puddle.ripple(self.phase_frame)
        self.elephant.tick_walk(self.phase_frame)
        self.phase_frame += 1
        if self.elephant.anchor.motion.movement_is_complete():
            self.phase = self.Phase.DRINK
            self.phase_frame = 0

    def _step_drink(self) -> None:
        """Lower the trunk and consume the puddle from its edges inward."""
        assert self.elephant is not None
        assert self.puddle is not None
        self.puddle.ripple(self.phase_frame)
        pose_index = min(self.phase_frame // (self.DRINK_FRAMES // 3) + 1, 3)
        self.elephant.apply_pose(f"drink_{pose_index}")
        self._animate_intake()
        self.phase_frame += 1
        remaining_water = (
            len(self.puddle.characters) - self.phase_frame * len(self.puddle.characters) // self.DRINK_FRAMES
        )
        self.puddle.shrink_to(max(0, remaining_water))
        if self.phase_frame >= self.DRINK_FRAMES:
            for character in self.intake_characters:
                self.terminal.set_character_visibility(character, is_visible=False)
            self.phase = self.Phase.RAISE_TRUNK
            self.phase_frame = 0

    def _step_raise_trunk(self) -> None:
        """Advance the three-pose trunk raise by one frame."""
        assert self.elephant is not None
        pose_index = min(self.phase_frame // 10 + 1, 3)
        self.elephant.apply_pose(f"raise_{pose_index}")
        self.phase_frame += 1
        if self.phase_frame >= 30:
            self.phase = self.Phase.SPLASH
            self.phase_frame = 0

    def _step_splash(self) -> None:
        """Advance either the particle splash or the tiny-canvas fallback."""
        if self.elephant is None:
            symbol = "." if self.phase_frame < 3 else "*"
            color = self.config.water_colors[0] if self.phase_frame < 3 else self.config.water_colors[-1]
            for character in self.input_characters:
                self.terminal.set_character_visibility(character, is_visible=True)
                character.animation.set_appearance(symbol, ColorPair(fg=color))
            self.phase_frame += 1
            if self.phase_frame >= 6:
                self.phase = self.Phase.REVEAL
                self.phase_frame = 0
            return
        assert self.water_pool is not None
        self.elephant.apply_pose(f"spray_{(self.phase_frame // 8) % 2 + 1}")
        if self.droplets_emitted < len(self.water_pool):
            self._emit_droplet()
        self.update()
        self.phase_frame += 1
        if self.droplets_emitted == len(self.water_pool) and len(self.water_pool.available) == len(self.water_pool):
            self.phase = self.Phase.REVEAL
            self.phase_frame = 0

    def _step_reveal(self) -> None:
        """Release one radial band every two frames and await scene completion."""
        if self.phase_frame % 2 == 0 and self.next_reveal_group < len(self.reveal_groups):
            for character in self.reveal_groups[self.next_reveal_group]:
                self.terminal.set_character_visibility(character, is_visible=True)
                character.animation.activate_scene("reveal")
                self.active_characters.add(character)
            self.next_reveal_group += 1
        if self.elephant is not None:
            self.elephant.apply_pose(f"wiggle_{(self.phase_frame // 8) % 2 + 1}")
        self.update()
        self.phase_frame += 1
        input_characters_are_active = any(character in self.active_characters for character in self.input_characters)
        if self.next_reveal_group == len(self.reveal_groups) and not input_characters_are_active:
            if self.elephant is not None:
                self.phase = self.Phase.CELEBRATE
                self.phase_frame = 0
            else:
                self.phase = self.Phase.HOLD
                self.phase_frame = 1

    def _step_celebrate(self) -> None:
        """Wiggle in place beside the completed branding before leaving."""
        assert self.elephant is not None
        self.elephant.apply_pose(f"wiggle_{(self.phase_frame // 12) % 2 + 1}")
        self.phase_frame += 1
        if self.phase_frame >= self.CELEBRATE_FRAMES:
            self.elephant.start_walk_out()
            self.phase = self.Phase.WALK_OUT
            self.phase_frame = 0

    def _step_walk_out(self) -> None:
        """Advance the elephant beyond the right edge and hide its helpers."""
        assert self.elephant is not None
        self.elephant.tick_walk(self.phase_frame)
        self.phase_frame += 1
        if self.elephant.anchor.motion.movement_is_complete():
            self.elephant.hide()
            self.phase = self.Phase.HOLD
            self.phase_frame = 1

    def _step_hold(self) -> None:
        """Hold the clean final branding frame for the configured duration."""
        if self.phase_frame >= max(1, self.config.final_hold_frames):
            self.phase = self.Phase.COMPLETE
            raise StopIteration
        self.phase_frame += 1


class ElephantSplash(BaseEffect[ElephantSplashConfig]):
    """A playful elephant splashes water to reveal the input text."""

    @property
    def _config_cls(self) -> type[ElephantSplashConfig]:
        return ElephantSplashConfig

    @property
    def _iterator_cls(self) -> type[ElephantSplashIterator]:
        return ElephantSplashIterator
