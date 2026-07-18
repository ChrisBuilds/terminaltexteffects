"""A playful elephant splashes water to reveal the input text."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from terminaltexteffects.engine.base_config import (
    BaseConfig,
    FinalGradientDirectionArg,
    FinalGradientFramesArg,
    FinalGradientStepsArg,
    FinalGradientStopsArg,
)
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.base_character import EffectCharacter
from terminaltexteffects.engine.terminal import Terminal
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.graphics import Color, ColorPair, Gradient


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command, effect class, and configuration class."""
    return "elephantsplash", ElephantSplash, ElephantSplashConfig


@dataclass
class ElephantSplashConfig(BaseConfig):
    """Configuration for the Elephant Splash effect."""

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

    FULL_POSES = {
        "walk_1": (
            "      __",
            " .---'  '---.",
            "/  _      ( )\\",
            "| / \\      /  |",
            "| \\_/ o   /  |__",
            "\\       /  /  ')",
            " '-.__.-'__/--'",
            "   /_\\   /_\\",
        ),
        "walk_2": (
            "      __",
            " .---'  '---.",
            "/  _      ( )\\",
            "| / \\      /  |",
            "| \\_/ o   /  |__",
            "\\       /  /  ')",
            " '-.__.-'__/--'",
            "   _/\\   /_\\",
        ),
        "walk_3": (
            "      __",
            " .---'  '---.",
            "/  _      ( )\\",
            "| / \\      /  |",
            "| \\_/ o   /  |__",
            "\\       /  /  ')",
            " '-.__.-'__/--'",
            "   /_\\   _/\\",
        ),
        "walk_4": (
            "      __",
            " .---'  '---.",
            "/  _      ( )\\",
            "| / \\      /  |",
            "| \\_/ o   /  |__",
            "\\       /  /  ')",
            " '-.__.-'__/--'",
            "   _/\\   _/\\",
        ),
        "raise_1": (
            "      __",
            " .---'  '---.",
            "/  _      ( )\\",
            "| / \\      /  |",
            "| \\_/ o    \\_|__",
            "\\        __/  ')",
            " '-.___.--'--'",
            "   /_\\   /_\\",
        ),
        "raise_2": (
            "      __",
            " .---'  '---.",
            "/  _      ( )\\",
            "| / \\       \\ |",
            "| \\_/ o      \\|__",
            "\\         __.--'",
            " '-.___.---'",
            "   /_\\   /_\\",
        ),
        "raise_3": (
            "      __",
            " .---'  '---.",
            "/  _      ( )\\",
            "| / \\        \\__",
            "| \\_/ o        _/",
            "\\          __.-'",
            " '-.___.---'",
            "   /_\\   /_\\",
        ),
        "spray_1": (
            "      __",
            " .---'  '---.",
            "/  _      ( )\\",
            "| / \\        \\___",
            "| \\_/ o        _/",
            "\\          __.-'",
            " '-.___.---'",
            "   /_\\   /_\\",
        ),
        "spray_2": (
            "      __",
            " .---'  '---.",
            "/  _     (( ))\\",
            "| / \\        \\___",
            "| \\_/ o        _/",
            "\\          __.-'",
            " '-.___.---'",
            "   /_\\   /_\\",
        ),
        "wiggle_1": (
            "      __",
            " .---'  '---.",
            "/  _      ( )\\",
            "| / \\        \\___",
            "| \\_/ o        _/",
            "\\          __.-'",
            " '-.___.---'",
            "   /_\\   /_\\",
        ),
        "wiggle_2": (
            "      __",
            " .---'  '---.",
            "/  _     (( ))\\",
            "| / \\        \\___",
            "| \\_/ o        _/",
            "\\          __.-'",
            " '-.___.---'",
            "   /_\\   /_\\",
        ),
    }
    COMPACT_POSES = {
        "walk_1": ("   __", " /'  '-.", "| (o)  |__", " \\   /  ')", "  /_\\ /_\\"),
        "walk_2": ("   __", " /'  '-.", "| (o)  |__", " \\   /  ')", "  _/\\ /_\\"),
        "walk_3": ("   __", " /'  '-.", "| (o)  |__", " \\   /  ')", "  /_\\ _/\\"),
        "walk_4": ("   __", " /'  '-.", "| (o)  |__", " \\   /  ')", "  _/\\ _/\\"),
        "raise_1": ("   __", " /'  '-.", "| (o)   \\_", " \\    __/'", "  /_\\ /_\\"),
        "raise_2": ("   __", " /'  '-.", "| (o)    \\__", " \\    __/'", "  /_\\ /_\\"),
        "raise_3": ("   __", " /'  '-.", "| (o)    \\___", " \\    __/'", "  /_\\ /_\\"),
        "spray_1": ("   __", " /'  '-.", "| (o)    \\___", " \\    __/'", "  /_\\ /_\\"),
        "spray_2": ("   __", " /' ((-.", "| (o)    \\___", " \\    __/'", "  /_\\ /_\\"),
        "wiggle_1": ("   __", " /'  '-.", "| (o)    \\___", " \\    __/'", "  /_\\ /_\\"),
        "wiggle_2": ("   __", " /' ((-.", "| (o)    \\___", " \\    __/'", "  /_\\ /_\\"),
    }

    class Elephant:
        """A rigid, pose-driven group of effect-owned characters."""

        def __init__(
            self,
            terminal: Terminal,
            config: ElephantSplashConfig,
            poses: dict[str, tuple[str, ...]],
        ) -> None:
            self.terminal = terminal
            self.config = config
            self.height = max(len(pose) for pose in poses.values())
            self.width = max(len(row) for pose in poses.values() for row in pose)
            self.poses = {
                name: tuple(row.ljust(self.width) for row in (*pose, *("",) * (self.height - len(pose))))
                for name, pose in poses.items()
            }
            baseline = max(
                terminal.canvas.bottom,
                min(terminal.canvas.center_row - self.height // 2, terminal.canvas.top - self.height + 1),
            )
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

        def _coord_for_offset(self, offset: Coord) -> Coord:
            return Coord(
                self.anchor.motion.current_coord.column + offset.column,
                self.anchor.motion.current_coord.row + offset.row,
            )

        def apply_pose(self, pose_name: str) -> None:
            """Apply one fixed ASCII pose to all sprite characters."""
            pose = self.poses[pose_name]
            shadow_color = self.characters[0].animation.adjust_color_brightness(self.config.elephant_color, 0.65)
            for character, offset in self.character_offsets.items():
                row_index = self.height - offset.row - 1
                symbol = pose[row_index][offset.column]
                if symbol == "o" or "(" in pose[row_index][max(0, offset.column - 1) : offset.column + 2]:
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

    class Phase(Enum):
        """Ordered phases in the Elephant Splash choreography."""

        WALK_IN = auto()
        RAISE_TRUNK = auto()
        SPLASH = auto()
        REVEAL = auto()
        WALK_OUT = auto()
        HOLD = auto()
        COMPLETE = auto()

    def __init__(self, effect: ElephantSplash) -> None:
        super().__init__(effect)
        if self.terminal.canvas.width >= 24 and self.terminal.canvas.height >= 10:
            self.sprite_mode = "full"
        elif self.terminal.canvas.width >= 12 and self.terminal.canvas.height >= 6:
            self.sprite_mode = "compact"
        else:
            self.sprite_mode = "fallback"
        self.phase = self.Phase.SPLASH if self.sprite_mode == "fallback" else self.Phase.WALK_IN
        pose_set = self.FULL_POSES if self.sprite_mode == "full" else self.COMPACT_POSES
        self.elephant = self.Elephant(self.terminal, self.config, pose_set) if self.sprite_mode != "fallback" else None
        self.water_pool = None
        self.phase_frame = 0

    def __next__(self) -> str:
        """Advance and render one frame of the effect."""
        if self.phase is self.Phase.WALK_IN and self.elephant is not None:
            self.elephant.tick_walk(self.phase_frame)
            self.phase_frame += 1
            if self.elephant.anchor.motion.movement_is_complete():
                self.phase = self.Phase.RAISE_TRUNK
                self.phase_frame = 0
                self.elephant.apply_pose("raise_1")
            return self.frame
        if self.phase is self.Phase.RAISE_TRUNK and self.elephant is not None:
            pose_index = min(self.phase_frame // 10 + 1, 3)
            self.elephant.apply_pose(f"raise_{pose_index}")
            self.phase_frame += 1
            if self.phase_frame >= 30:
                self.phase = self.Phase.SPLASH
                self.phase_frame = 0
            return self.frame
        raise StopIteration


class ElephantSplash(BaseEffect[ElephantSplashConfig]):
    """A playful elephant splashes water to reveal the input text."""

    @property
    def _config_cls(self) -> type[ElephantSplashConfig]:
        return ElephantSplashConfig

    @property
    def _iterator_cls(self) -> type[ElephantSplashIterator]:
        return ElephantSplashIterator
