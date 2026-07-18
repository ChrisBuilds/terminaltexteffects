"""Catch scattered input characters with fishing hooks and place them into position."""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

from terminaltexteffects.engine.base_config import (
    BaseConfig,
    FinalGradientDirectionArg,
    FinalGradientStepsArg,
    FinalGradientStopsArg,
)
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.effect_support import ParticlePool, ParticleReset
from terminaltexteffects.utils import argutils, easing
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.graphics import Color, ColorPair, Gradient

if TYPE_CHECKING:
    from terminaltexteffects.engine.base_character import EffectCharacter


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command, effect class, and config class for discovery."""
    return "fishing", Fishing, FishingConfig


@dataclass
class FishingConfig(BaseConfig):
    """Configuration for the Fishing effect."""

    parser_spec: argutils.ParserSpec = argutils.ParserSpec(
        name="fishing",
        help="Fishing hooks catch scattered characters and reel them into place.",
        description="fishing | Fishing hooks catch scattered characters and reel them into place.",
        epilog=(
            "Example: terminaltexteffects fishing --hook-count 3 --line-color D6F6FF "
            "--water-colors 0B7285 1098AD 66D9E8 --cast-speed 0.75 --reel-speed 1.25 "
            "--cast-delay 4 --wrong-catch-chance 0.05 --final-gradient-stops 1E90FF 00D1B2 FFE66D "
            "--final-gradient-steps 12 --final-gradient-direction horizontal"
        ),
    )

    hook_count: int = argutils.ArgSpec(
        name="--hook-count",
        type=argutils.PositiveInt.type_parser,
        default=3,
        metavar=argutils.PositiveInt.METAVAR,
        help="Maximum number of fishing hooks working concurrently.",
    )  # pyright: ignore[reportAssignmentType]
    line_color: Color = argutils.ArgSpec(
        name="--line-color",
        type=argutils.ColorArg.type_parser,
        default=Color("#D6F6FF"),
        metavar=argutils.ColorArg.METAVAR,
        help="Color used for fishing lines and hooks.",
    )  # pyright: ignore[reportAssignmentType]
    water_colors: tuple[Color, ...] = argutils.ArgSpec(
        name="--water-colors",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=(Color("#0B7285"), Color("#1098AD"), Color("#66D9E8")),
        metavar=argutils.ColorArg.METAVAR,
        help="Colors used while input characters swim before being caught.",
    )  # pyright: ignore[reportAssignmentType]
    cast_speed: float = argutils.ArgSpec(
        name="--cast-speed",
        type=argutils.PositiveFloat.type_parser,
        default=0.75,
        metavar=argutils.PositiveFloat.METAVAR,
        help="Speed at which hooks slide and cast toward swimming characters.",
    )  # pyright: ignore[reportAssignmentType]
    reel_speed: float = argutils.ArgSpec(
        name="--reel-speed",
        type=argutils.PositiveFloat.type_parser,
        default=1.25,
        metavar=argutils.PositiveFloat.METAVAR,
        help="Speed used while reeling catches and returning hooks.",
    )  # pyright: ignore[reportAssignmentType]
    cast_delay: int = argutils.ArgSpec(
        name="--cast-delay",
        type=argutils.NonNegativeInt.type_parser,
        default=4,
        metavar=argutils.NonNegativeInt.METAVAR,
        help="Frames between casts and between each hook's initial start.",
    )  # pyright: ignore[reportAssignmentType]
    wrong_catch_chance: float = argutils.ArgSpec(
        name="--wrong-catch-chance",
        type=argutils.NonNegativeRatio.type_parser,
        default=0.05,
        metavar=argutils.NonNegativeRatio.METAVAR,
        help="One-time probability that each hook catches harmless junk before a real target.",
    )  # pyright: ignore[reportAssignmentType]
    final_gradient_stops: tuple[Color, ...] = FinalGradientStopsArg(
        default=(Color("#1E90FF"), Color("#00D1B2"), Color("#FFE66D")),
    )  # pyright: ignore[reportAssignmentType]
    final_gradient_steps: tuple[int, ...] | int = FinalGradientStepsArg(default=12)  # pyright: ignore[reportAssignmentType]
    final_gradient_direction: Gradient.Direction = FinalGradientDirectionArg(
        default=Gradient.Direction.HORIZONTAL,
    )  # pyright: ignore[reportAssignmentType]


class HookPhase(Enum):
    """Current lifecycle phase for one fishing hook."""

    WAITING = auto()
    CASTING = auto()
    BITING = auto()
    REELING = auto()
    TRANSPORTING = auto()
    LOWERING = auto()
    RELEASING = auto()
    WRONG_CATCH = auto()
    RETURNING = auto()
    FINISHED = auto()


@dataclass
class HookState:
    """State owned by one independently progressing fishing hook."""

    home_column: int
    hook_character: EffectCharacter
    line_characters: list[EffectCharacter]
    assignments: deque[EffectCharacter] = field(default_factory=deque)
    phase: HookPhase = HookPhase.WAITING
    target: EffectCharacter | None = None
    delay: int = 0
    path_count: int = 0
    bite_ticks_remaining: int = 0
    bite_origin: Coord | None = None
    caught_character: EffectCharacter | None = None
    release_ticks_remaining: int = 0
    wrong_catch_pending: bool = False
    wrong_catches_used: int = 0
    junk_character: EffectCharacter | None = None
    casting_junk: bool = False
    wrong_stage: str = ""
    wrong_ticks_remaining: int = 0
    returning_from_wrong: bool = False


class FishingIterator(BaseEffectIterator[FishingConfig]):
    """Iterator for the Fishing effect."""

    BITE_FRAMES = 4
    RELEASE_FRAMES = 3
    WRONG_SHAKE_FRAMES = 4
    FINAL_HOLD_FRAMES = 6

    def __init__(self, effect: Fishing) -> None:  # noqa: PLR0915
        """Initialize the Fishing iterator."""
        super().__init__(effect)
        self.catchable_characters = [
            character for character in self.terminal.get_characters() if character.input_symbol != " "
        ]
        final_gradient = Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.canvas.text_bottom,
            self.terminal.canvas.text_top,
            self.terminal.canvas.text_left,
            self.terminal.canvas.text_right,
            self.config.final_gradient_direction,
        )
        self.character_final_color_map: dict[EffectCharacter, ColorPair] = {}
        for character in self.terminal.get_characters():
            if self.terminal.config.existing_color_handling == "dynamic":
                self.character_final_color_map[character] = ColorPair(
                    fg=character.animation.input_fg_color,
                    bg=character.animation.input_bg_color,
                )
            else:
                self.character_final_color_map[character] = ColorPair(
                    fg=final_gradient_mapping[character.input_coord],
                )
        hook_count = min(self.config.hook_count, len(self.catchable_characters), self.terminal.canvas.width)
        if hook_count == 1:
            home_columns = [self.terminal.canvas.center_column]
        elif hook_count > 1:
            home_columns = [
                self.terminal.canvas.left + round(index * (self.terminal.canvas.width - 1) / (hook_count - 1))
                for index in range(hook_count)
            ]
        else:
            home_columns = []
        self.hooks: list[HookState] = []
        for hook_index, column in enumerate(home_columns):
            hook_character = self.terminal.add_character("J", Coord(column, self.terminal.canvas.top))
            hook_character.animation.set_appearance("J", ColorPair(fg=self.config.line_color))
            hook_character.layer = 12 + (hook_index * 3)
            self.terminal.set_character_visibility(hook_character, is_visible=True)
            line_characters = [
                self.terminal.add_character("|", Coord(column, self.terminal.canvas.top))
                for _ in range(max(self.terminal.canvas.height - 1, 0))
            ]
            for line_character in line_characters:
                line_character.animation.set_appearance("|", ColorPair(fg=self.config.line_color))
                line_character.layer = 10 + (hook_index * 3)
            self.hooks.append(
                HookState(
                    home_column=column,
                    hook_character=hook_character,
                    line_characters=line_characters,
                    delay=hook_index * self.config.cast_delay,
                    wrong_catch_pending=random.random() < self.config.wrong_catch_chance,
                ),
            )
        top_row_coordinates = [
            Coord(column, self.terminal.canvas.top)
            for column in range(self.terminal.canvas.left, self.terminal.canvas.right + 1)
        ]
        underwater_coordinates = [
            Coord(column, row)
            for row in range(self.terminal.canvas.bottom, self.terminal.canvas.top)
            for column in range(self.terminal.canvas.left, self.terminal.canvas.right + 1)
        ]
        random.shuffle(top_row_coordinates)
        random.shuffle(underwater_coordinates)
        available_coordinates = top_row_coordinates + underwater_coordinates
        self.character_start_coord_map: dict[EffectCharacter, Coord] = {}
        for character in self.catchable_characters:
            start_coord = available_coordinates.pop()
            if start_coord == character.input_coord and available_coordinates:
                alternative_coord = available_coordinates.pop()
                available_coordinates.append(start_coord)
                start_coord = alternative_coord
            self.character_start_coord_map[character] = start_coord
            character.motion.set_coordinate(start_coord)
        sorted_targets = sorted(
            self.catchable_characters,
            key=lambda character: (character.input_coord.column, -character.input_coord.row, character.character_id),
        )
        if self.hooks:
            base_size, larger_region_count = divmod(len(sorted_targets), len(self.hooks))
            target_index = 0
            for hook_index, hook in enumerate(self.hooks):
                region_size = base_size + (1 if hook_index < larger_region_count else 0)
                region = sorted_targets[target_index : target_index + region_size]
                target_index += region_size
                region.sort(
                    key=lambda character: (
                        abs(self.character_start_coord_map[character].column - hook.home_column),
                        -self.character_start_coord_map[character].row,
                        character.character_id,
                    ),
                )
                hook.assignments.extend(region)
        self.character_water_color_map: dict[EffectCharacter, Color] = {}
        swim_speed = max(min(self.config.cast_speed * 0.2, 0.25), 0.05)
        for character in self.catchable_characters:
            water_color = random.choice(self.config.water_colors)
            self.character_water_color_map[character] = water_color
            character.animation.set_appearance(character.input_symbol, ColorPair(fg=water_color))
            character.layer = 1
            self.terminal.set_character_visibility(character, is_visible=True)
            start_coord = self.character_start_coord_map[character]
            neighboring_coordinates = [
                Coord(start_coord.column + column_delta, start_coord.row + row_delta)
                for column_delta, row_delta in ((-1, 0), (1, 0), (0, -1), (0, 1))
                if self.terminal.canvas.coord_is_in_canvas(
                    Coord(start_coord.column + column_delta, start_coord.row + row_delta),
                )
            ]
            if neighboring_coordinates:
                swim_out = character.motion.new_path(
                    speed=swim_speed,
                    ease=easing.in_out_sine,
                    hold_time=3,
                    path_id="swim_out",
                )
                swim_out.new_waypoint(random.choice(neighboring_coordinates))
                swim_back = character.motion.new_path(
                    speed=swim_speed,
                    ease=easing.in_out_sine,
                    hold_time=3,
                    path_id="swim_back",
                )
                swim_back.new_waypoint(start_coord)
                character.motion.chain_paths([swim_out, swim_back], loop=True)
                character.motion.activate_path(swim_out)
                self.active_characters.add(character)

        def initialize_ripple(ripple: EffectCharacter) -> None:
            ripple.layer = 50
            ripple_scene = ripple.animation.new_scene(scene_id="ripple")
            ripple_scene.add_frame("~", 1, colors=ColorPair(fg=self.config.water_colors[-1]))
            ripple_scene.add_frame("-", 1, colors=ColorPair(fg=self.config.water_colors[-1]))
            ripple_scene.add_frame(".", 1, colors=ColorPair(fg=self.config.water_colors[0]))

        self.ripple_pool = ParticlePool(
            self.terminal,
            self.active_characters,
            "~",
            initial_count=len(self.hooks),
            max_size=len(self.hooks),
            coord=Coord(self.terminal.canvas.left, self.terminal.canvas.bottom),
            initializer=initialize_ripple,
        )
        for ripple in self.ripple_pool.particles:
            self.ripple_pool.reclaim_on_event(ripple, ripple.animation.query_scene("ripple"))

        def initialize_junk(junk: EffectCharacter) -> None:
            junk.layer = 11
            junk.animation.set_appearance(junk.input_symbol, ColorPair(fg=self.config.water_colors[-1]))

        junk_count = len(self.hooks) if self.config.wrong_catch_chance > 0 else 0
        self.junk_pool = ParticlePool(
            self.terminal,
            self.active_characters,
            ("?", "#", "*"),
            initial_count=junk_count,
            max_size=len(self.hooks),
            coord=Coord(self.terminal.canvas.left, self.terminal.canvas.bottom),
            initializer=initialize_junk,
        )
        self._cleanup_complete = False
        self._final_hold_frames_remaining = 0

    def _sync_line(self, hook: HookState) -> None:
        """Resize and reposition a hook's reusable vertical fishing line."""
        hook_coord = hook.hook_character.motion.current_coord
        visible_line_length = max(self.terminal.canvas.top - hook_coord.row, 0)
        for index, line_character in enumerate(hook.line_characters):
            if index < visible_line_length:
                line_character.motion.set_coordinate(Coord(hook_coord.column, hook_coord.row + index + 1))
                self.terminal.set_character_visibility(line_character, is_visible=True)
            else:
                self.terminal.set_character_visibility(line_character, is_visible=False)

    def _start_cast(self, hook: HookState) -> None:
        """Select the next assigned target and cast the hook toward it."""
        if hook.target is None:
            hook.target = hook.assignments.popleft()
        if hook.wrong_catch_pending:
            hook.junk_character = self.junk_pool.acquire(
                reset=ParticleReset(clear_paths=True, clear_scenes=True, clear_events=True),
            )
            assert hook.junk_character is not None
            target_coord = hook.target.motion.current_coord
            neighboring_coordinates = [
                Coord(target_coord.column + column_delta, target_coord.row + row_delta)
                for column_delta, row_delta in ((-1, 0), (1, 0), (0, -1), (0, 1))
                if self.terminal.canvas.coord_is_in_canvas(
                    Coord(target_coord.column + column_delta, target_coord.row + row_delta),
                )
            ]
            junk_coord = random.choice(neighboring_coordinates) if neighboring_coordinates else target_coord
            hook.junk_character.motion.set_coordinate(junk_coord)
            hook.junk_character.animation.set_appearance(
                hook.junk_character.input_symbol,
                ColorPair(fg=self.config.water_colors[-1]),
            )
            self.terminal.set_character_visibility(hook.junk_character, is_visible=True)
            target_coord = junk_coord
            hook.casting_junk = True
            hook.wrong_catch_pending = False
        else:
            hook.target.motion.deactivate_path()
            target_coord = hook.target.motion.current_coord
        approach_coord = Coord(target_coord.column, min(self.terminal.canvas.top, target_coord.row + 1))
        hook.path_count += 1
        cast_path = hook.hook_character.motion.new_path(
            speed=self.config.cast_speed,
            ease=easing.in_out_sine,
            path_id=f"cast_{hook.path_count}",
        )
        top_target_coord = Coord(target_coord.column, self.terminal.canvas.top)
        cast_path.new_waypoint(top_target_coord)
        if approach_coord != top_target_coord:
            cast_path.new_waypoint(approach_coord)
        hook.hook_character.motion.activate_path(cast_path)
        self.active_characters.add(hook.hook_character)
        hook.phase = HookPhase.CASTING

    def _start_wrong_catch(self, hook: HookState) -> None:
        """Attach auxiliary junk and reel it only a short distance."""
        assert hook.junk_character is not None
        hook.caught_character = hook.junk_character
        hook.path_count += 1
        wrong_reel_path = hook.hook_character.motion.new_path(
            speed=self.config.reel_speed,
            ease=easing.out_sine,
            path_id=f"wrong_reel_{hook.path_count}",
        )
        wrong_reel_path.new_waypoint(
            Coord(
                hook.hook_character.motion.current_coord.column,
                min(self.terminal.canvas.top, hook.hook_character.motion.current_coord.row + 2),
            ),
        )
        hook.hook_character.motion.activate_path(wrong_reel_path)
        self.active_characters.add(hook.hook_character)
        hook.wrong_stage = "reeling"
        hook.phase = HookPhase.WRONG_CATCH

    def _advance_wrong_catch(self, hook: HookState) -> None:
        """Finish the bounded wrong-catch reel and shake before retrying the real target."""
        assert hook.junk_character is not None
        if hook.wrong_stage == "reeling" and hook.hook_character.motion.active_path is None:
            hook.wrong_stage = "shaking"
            hook.wrong_ticks_remaining = self.WRONG_SHAKE_FRAMES
        elif hook.wrong_stage == "shaking" and hook.wrong_ticks_remaining:
            symbol = "!" if hook.wrong_ticks_remaining % 2 else hook.junk_character.input_symbol
            hook.junk_character.animation.set_appearance(symbol, ColorPair(fg=self.config.water_colors[-1]))
            hook.wrong_ticks_remaining -= 1
        elif hook.wrong_stage == "shaking":
            self.junk_pool.reclaim(hook.junk_character)
            hook.junk_character = None
            hook.caught_character = None
            hook.casting_junk = False
            hook.wrong_stage = ""
            hook.wrong_catches_used += 1
            self._start_returning(hook, retry_target=True)

    def _wiggle_target(self, hook: HookState) -> None:
        """Move the selected target by one cell during the bite cue."""
        assert hook.target is not None
        assert hook.bite_origin is not None
        direction = -1 if hook.bite_ticks_remaining % 2 == 0 else 1
        horizontal_coord = Coord(hook.bite_origin.column + direction, hook.bite_origin.row)
        if self.terminal.canvas.coord_is_in_canvas(horizontal_coord):
            hook.target.motion.set_coordinate(horizontal_coord)
        else:
            vertical_coord = Coord(hook.bite_origin.column, hook.bite_origin.row + direction)
            hook.target.motion.set_coordinate(
                vertical_coord if self.terminal.canvas.coord_is_in_canvas(vertical_coord) else hook.bite_origin,
            )
        hook.bite_ticks_remaining -= 1

    def _start_reeling(self, hook: HookState) -> None:
        """Attach the selected input character and reel it toward the travel row."""
        assert hook.target is not None
        if hook.bite_origin is not None:
            hook.target.motion.set_coordinate(hook.bite_origin)
        hook.caught_character = hook.target
        hook.caught_character.layer = hook.hook_character.layer - 1
        travel_row = max(hook.hook_character.motion.current_coord.row, self.terminal.canvas.top - 1)
        hook.path_count += 1
        reel_path = hook.hook_character.motion.new_path(
            speed=self.config.reel_speed,
            ease=easing.out_sine,
            path_id=f"reel_{hook.path_count}",
        )
        reel_path.new_waypoint(Coord(hook.hook_character.motion.current_coord.column, travel_row))
        hook.hook_character.motion.activate_path(reel_path)
        self.active_characters.add(hook.hook_character)
        hook.phase = HookPhase.REELING

    def _emit_ripple(self, coord: Coord) -> None:
        """Emit one short pooled ripple at a bite coordinate."""

        def activate_ripple(ripple: EffectCharacter) -> None:
            ripple.animation.activate_scene("ripple")

        self.ripple_pool.emit(
            coord,
            on_emit=activate_ripple,
            reset=ParticleReset(clear_paths=True, clear_scenes=False, clear_events=False),
        )

    def _start_transporting(self, hook: HookState) -> None:
        """Move a reeled catch horizontally toward its final column."""
        assert hook.target is not None
        hook.path_count += 1
        transport_path = hook.hook_character.motion.new_path(
            speed=self.config.reel_speed,
            ease=easing.in_out_sine,
            path_id=f"transport_{hook.path_count}",
        )
        transport_path.new_waypoint(
            Coord(hook.target.input_coord.column, hook.hook_character.motion.current_coord.row),
        )
        hook.hook_character.motion.activate_path(transport_path)
        self.active_characters.add(hook.hook_character)
        hook.phase = HookPhase.TRANSPORTING

    def _start_lowering(self, hook: HookState) -> None:
        """Lower an attached catch to the release row above its destination."""
        assert hook.target is not None
        release_hook_row = min(self.terminal.canvas.top, hook.target.input_coord.row + 1)
        hook.path_count += 1
        lowering_path = hook.hook_character.motion.new_path(
            speed=self.config.reel_speed,
            ease=easing.in_sine,
            path_id=f"lower_{hook.path_count}",
        )
        lowering_path.new_waypoint(Coord(hook.target.input_coord.column, release_hook_row))
        hook.hook_character.motion.activate_path(lowering_path)
        self.active_characters.add(hook.hook_character)
        hook.phase = HookPhase.LOWERING

    def _set_final_appearance(self, character: EffectCharacter) -> None:
        """Restore one input character's exact symbol and intended final colors."""
        character.animation.deactivate_scene()
        character.animation.set_appearance(character.input_symbol, self.character_final_color_map[character])

    def _start_releasing(self, hook: HookState) -> None:
        """Place and detach the caught character at its immutable input coordinate."""
        assert hook.target is not None
        hook.target.motion.deactivate_path()
        hook.target.motion.set_coordinate(hook.target.input_coord)
        hook.target.layer = 0
        self._set_final_appearance(hook.target)
        self.terminal.set_character_visibility(hook.target, is_visible=True)
        hook.caught_character = None
        hook.release_ticks_remaining = self.RELEASE_FRAMES
        hook.phase = HookPhase.RELEASING

    def _start_returning(self, hook: HookState, *, retry_target: bool = False) -> None:
        """Reel an empty hook to the top and slide it back to its home column."""
        hook.path_count += 1
        return_path = hook.hook_character.motion.new_path(
            speed=self.config.reel_speed,
            ease=easing.out_sine,
            path_id=f"return_{hook.path_count}",
        )
        current_column = hook.hook_character.motion.current_coord.column
        top_current_column = Coord(current_column, self.terminal.canvas.top)
        return_path.new_waypoint(top_current_column)
        home_coord = Coord(hook.home_column, self.terminal.canvas.top)
        if home_coord != top_current_column:
            return_path.new_waypoint(home_coord)
        hook.hook_character.motion.activate_path(return_path)
        self.active_characters.add(hook.hook_character)
        hook.returning_from_wrong = retry_target
        hook.phase = HookPhase.RETURNING

    def _finish_returning(self, hook: HookState) -> None:
        """Reset a returned hook for its next target or hide it permanently."""
        if not hook.returning_from_wrong:
            hook.target = None
            hook.bite_origin = None
        hook.caught_character = None
        if hook.returning_from_wrong or hook.assignments:
            hook.delay = self.config.cast_delay
            hook.phase = HookPhase.WAITING
        else:
            hook.phase = HookPhase.FINISHED
            self.terminal.set_character_visibility(hook.hook_character, is_visible=False)
            for line_character in hook.line_characters:
                self.terminal.set_character_visibility(line_character, is_visible=False)
        hook.returning_from_wrong = False

    def _sync_caught_character(self, hook: HookState) -> None:
        """Keep an attached input character immediately below its hook when possible."""
        if hook.caught_character is None:
            return
        hook_coord = hook.hook_character.motion.current_coord
        caught_row = hook_coord.row - 1 if hook_coord.row > self.terminal.canvas.bottom else hook_coord.row
        hook.caught_character.motion.set_coordinate(Coord(hook_coord.column, caught_row))

    def _cleanup(self) -> None:
        """Hide every auxiliary and force all input characters into their exact final state."""
        for auxiliary in self.terminal.get_characters(input_chars=False, added_chars=True):
            auxiliary.motion.deactivate_path()
            auxiliary.animation.deactivate_scene()
            self.terminal.set_character_visibility(auxiliary, is_visible=False)
        for junk in self.junk_pool.particles:
            self.junk_pool.reclaim(junk)
        for character in self.terminal.get_characters():
            character.motion.deactivate_path()
            character.motion.set_coordinate(character.input_coord)
            character.layer = 0
            self._set_final_appearance(character)
            self.terminal.set_character_visibility(character, is_visible=True)
        self.active_characters.clear()
        self._cleanup_complete = True
        self._final_hold_frames_remaining = self.FINAL_HOLD_FRAMES - 1

    def __next__(self) -> str:
        """Advance the Fishing choreography and return the next rendered frame."""
        if self._cleanup_complete:
            if self._final_hold_frames_remaining:
                self._final_hold_frames_remaining -= 1
                return self.frame
            raise StopIteration

        for hook in self.hooks:
            if hook.phase is HookPhase.CASTING and hook.hook_character.motion.active_path is None:
                if hook.casting_junk:
                    self._start_wrong_catch(hook)
                else:
                    hook.phase = HookPhase.BITING
                    hook.bite_ticks_remaining = self.BITE_FRAMES
                    assert hook.target is not None
                    hook.bite_origin = hook.target.motion.current_coord
                    self._emit_ripple(hook.bite_origin)
            elif hook.phase is HookPhase.BITING:
                if hook.bite_ticks_remaining:
                    self._wiggle_target(hook)
                else:
                    self._start_reeling(hook)
            elif hook.phase is HookPhase.REELING and hook.hook_character.motion.active_path is None:
                self._start_transporting(hook)
            elif hook.phase is HookPhase.TRANSPORTING and hook.hook_character.motion.active_path is None:
                self._start_lowering(hook)
            elif hook.phase is HookPhase.LOWERING and hook.hook_character.motion.active_path is None:
                self._start_releasing(hook)
            elif hook.phase is HookPhase.RELEASING:
                if hook.release_ticks_remaining:
                    hook.release_ticks_remaining -= 1
                else:
                    self._start_returning(hook)
            elif hook.phase is HookPhase.WRONG_CATCH:
                self._advance_wrong_catch(hook)
            elif hook.phase is HookPhase.RETURNING and hook.hook_character.motion.active_path is None:
                self._finish_returning(hook)
            elif hook.phase is HookPhase.WAITING and hook.assignments:
                if hook.delay:
                    hook.delay -= 1
                else:
                    self._start_cast(hook)

        self.update()
        for hook in self.hooks:
            self._sync_caught_character(hook)
            self._sync_line(hook)
        if not self.hooks or all(hook.phase is HookPhase.FINISHED for hook in self.hooks):
            self._cleanup()
        return self.frame


class Fishing(BaseEffect[FishingConfig]):
    """Catch scattered characters and reel them into their final text positions."""

    @property
    def _config_cls(self) -> type[FishingConfig]:
        return FishingConfig

    @property
    def _iterator_cls(self) -> type[FishingIterator]:
        return FishingIterator
