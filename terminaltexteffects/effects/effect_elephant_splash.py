"""A playful elephant splashes water to reveal the input text."""

from __future__ import annotations

import random
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

    FULL_POSES: typing.ClassVar[dict[str, tuple[str, ...]]] = {
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
    COMPACT_POSES: typing.ClassVar[dict[str, tuple[str, ...]]] = {
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
            """Create a pose-driven elephant on the supplied terminal."""
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
            """Return the rightmost visible coordinate in the current pose."""
            pose = self.poses[self.current_pose]
            occupied_offsets = [
                Coord(column, self.height - row_index - 1)
                for row_index, row in enumerate(pose)
                for column, symbol in enumerate(row)
                if symbol != " "
            ]
            return self._coord_for_offset(max(occupied_offsets, key=lambda offset: (offset.column, offset.row)))

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
        """Build the responsive sprite, branding scenes, and particle pool."""
        super().__init__(effect)
        if self.terminal.canvas.width >= 24 and self.terminal.canvas.height >= 10:
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
        self.elephant = self.Elephant(self.terminal, self.config, pose_set) if self.sprite_mode != "fallback" else None
        self.water_pool = self._make_water_pool() if self.sprite_mode != "fallback" else None
        self.phase_frame = 0
        self.droplets_emitted = 0
        self.next_reveal_group = 0

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
        target_character = random.choice(self.input_characters)
        target = target_character.input_coord
        if target == origin:
            alternate_column = (
                self.terminal.canvas.right if origin.column != self.terminal.canvas.right else self.terminal.canvas.left
            )
            target = Coord(alternate_column, target.row)

        def configure_droplet(particle: EffectCharacter) -> None:
            control_row = min(
                self.terminal.canvas.top,
                max(origin.row, target.row) + random.randint(3, 6),
            )
            control = Coord((origin.column + target.column) // 2, control_row)
            droplet_path = particle.motion.new_path(speed=0.6, ease=easing.out_sine)
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
            self.Phase.RAISE_TRUNK: self._step_raise_trunk,
            self.Phase.SPLASH: self._step_splash,
            self.Phase.REVEAL: self._step_reveal,
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
        self.elephant.tick_walk(self.phase_frame)
        self.phase_frame += 1
        if self.elephant.anchor.motion.movement_is_complete():
            self.phase = self.Phase.RAISE_TRUNK
            self.phase_frame = 0
            self.elephant.apply_pose("raise_1")

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
        remaining = len(self.water_pool) - self.droplets_emitted
        for _ in range(min(4, remaining)):
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
                self.elephant.start_walk_out()
                self.phase = self.Phase.WALK_OUT
            else:
                self.phase = self.Phase.HOLD
            self.phase_frame = 0

    def _step_walk_out(self) -> None:
        """Advance the elephant beyond the right edge and hide its helpers."""
        assert self.elephant is not None
        self.elephant.tick_walk(self.phase_frame)
        self.phase_frame += 1
        if self.elephant.anchor.motion.movement_is_complete():
            self.elephant.hide()
            self.phase = self.Phase.HOLD
            self.phase_frame = 0

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
