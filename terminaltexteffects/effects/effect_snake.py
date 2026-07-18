"""Snakes carry input characters through orthogonal paths and assemble the final text."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import cast

from terminaltexteffects import Color, ColorPair, Coord, EffectCharacter, EventHandler, Gradient
from terminaltexteffects.engine.base_config import (
    BaseConfig,
    FinalGradientDirectionArg,
    FinalGradientStepsArg,
    FinalGradientStopsArg,
)
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the CLI command, effect class, and configuration class."""
    return "snake", Snake, SnakeConfig


@dataclass
class SnakeConfig(BaseConfig):
    """Configuration for the Snake effect."""

    parser_spec: argutils.ParserSpec = argutils.ParserSpec(
        name="snake",
        help="Snakes carry characters through the canvas and assemble the input text.",
        description="snake | Snakes carry characters through the canvas and assemble the input text.",
        epilog=(
            "Example: terminaltexteffects snake --snake-count 4 --snake-colors 22c55e 84cc16 a3e635 "
            "--movement-speed 1 --spawn-delay 3 --head-symbol ● --final-gradient-stops 22c55e 84cc16 fde047 "
            "--final-gradient-steps 12 --final-gradient-direction horizontal"
        ),
    )

    snake_count: int = argutils.ArgSpec(
        name="--snake-count",
        type=argutils.PositiveInt.type_parser,
        default=4,
        metavar=argutils.PositiveInt.METAVAR,
        help="Maximum number of snakes. The effective count is limited by the number of input characters.",
    )  # pyright: ignore[reportAssignmentType]

    snake_colors: tuple[Color, ...] = argutils.ArgSpec(
        name="--snake-colors",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=(Color("#22c55e"), Color("#84cc16"), Color("#a3e635")),
        metavar=argutils.ColorArg.METAVAR,
        help="Colors assigned to snakes in sequence.",
    )  # pyright: ignore[reportAssignmentType]

    movement_speed: float = argutils.ArgSpec(
        name="--movement-speed",
        type=argutils.PositiveFloat.type_parser,
        default=1.0,
        metavar=argutils.PositiveFloat.METAVAR,
        help="Speed of snake head movement along the grid.",
    )  # pyright: ignore[reportAssignmentType]

    spawn_delay: int = argutils.ArgSpec(
        name="--spawn-delay",
        type=argutils.NonNegativeInt.type_parser,
        default=3,
        metavar=argutils.NonNegativeInt.METAVAR,
        help="Number of frames between snake spawns.",
    )  # pyright: ignore[reportAssignmentType]

    head_symbol: str = argutils.ArgSpec(
        name="--head-symbol",
        type=argutils.Symbol.type_parser,
        default="●",
        metavar=argutils.Symbol.METAVAR,
        help="Symbol used for each snake head.",
    )  # pyright: ignore[reportAssignmentType]

    final_gradient_stops: tuple[Color, ...] = FinalGradientStopsArg(
        default=(Color("#22c55e"), Color("#84cc16"), Color("#fde047")),
    )  # pyright: ignore[reportAssignmentType]

    final_gradient_steps: tuple[int, ...] | int = FinalGradientStepsArg(
        default=12,
    )  # pyright: ignore[reportAssignmentType]

    final_gradient_direction: Gradient.Direction = FinalGradientDirectionArg(
        default=Gradient.Direction.HORIZONTAL,
    )  # pyright: ignore[reportAssignmentType]


@dataclass
class _SnakeState:
    head: EffectCharacter
    carried: deque[EffectCharacter]
    entry_edge: str
    trail: deque[Coord]
    arrived: bool = False
    horizontal_first: bool = True
    route_number: int = 0


class SnakeIterator(BaseEffectIterator[SnakeConfig]):
    """Iterator for the Snake effect."""

    DYNAMIC_NEUTRAL_GRAY = Color("#808080")

    def __init__(self, effect: Snake) -> None:
        """Initialize Snake state for the effect."""
        super().__init__(effect)
        self.snakes: list[_SnakeState] = []
        self.character_final_color_map: dict[EffectCharacter, ColorPair] = {}
        self.build()
        self.pending_snakes = deque(self.snakes)
        self.active_snakes: list[_SnakeState] = []
        self.spawn_countdown = 0
        self.final_frame_provided = False

    @staticmethod
    def _orthogonal_waypoints(start: Coord, target: Coord, *, horizontal_first: bool) -> list[Coord]:
        """Return a direct grid route from start to target with at most one corner."""
        if start.column == target.column or start.row == target.row:
            return [target]
        corner = Coord(target.column, start.row) if horizontal_first else Coord(start.column, target.row)
        return [corner, target]

    @staticmethod
    def _update_trail(snake: _SnakeState) -> None:
        """Record each crossed grid cell and place body characters along the trail."""
        previous = snake.trail[0]
        current = snake.head.motion.current_coord
        if current != previous:
            next_column = previous.column
            column_step = 1 if current.column > previous.column else -1
            while next_column != current.column:
                next_column += column_step
                snake.trail.appendleft(Coord(next_column, previous.row))
            next_row = previous.row
            row_step = 1 if current.row > previous.row else -1
            while next_row != current.row:
                next_row += row_step
                snake.trail.appendleft(Coord(current.column, next_row))
        while len(snake.trail) > max(len(snake.carried), 1):
            snake.trail.pop()
        for index, character in enumerate(snake.carried):
            trail_index = min(index, len(snake.trail) - 1)
            character.motion.set_coordinate(snake.trail[trail_index])

    @staticmethod
    def _mark_arrived(_head: EffectCharacter, snake: _SnakeState) -> None:
        snake.arrived = True

    def _activate_route(self, snake: _SnakeState) -> None:
        target = snake.carried[0].input_coord
        path = snake.head.motion.new_path(
            speed=self.config.movement_speed,
            path_id=f"route_{snake.route_number}",
        )
        snake.route_number += 1
        for waypoint in self._orthogonal_waypoints(
            snake.head.motion.current_coord,
            target,
            horizontal_first=snake.horizontal_first,
        ):
            path.new_waypoint(waypoint)
        snake.horizontal_first = not snake.horizontal_first
        snake.head.event_handler.register_event(
            EventHandler.Event.PATH_COMPLETE,
            path,
            EventHandler.Action.CALLBACK,
            EventHandler.Callback(self._mark_arrived, snake),
        )
        snake.head.motion.activate_path(path)
        self.active_characters.add(snake.head)

    def _spawn_snake(self, snake: _SnakeState) -> None:
        self.terminal.set_character_visibility(snake.head, is_visible=True)
        for character in snake.carried:
            self.terminal.set_character_visibility(character, is_visible=True)
        self._activate_route(snake)
        self.active_snakes.append(snake)

    def _build_settle_scene(
        self,
        character: EffectCharacter,
        snake_color: Color,
        final_colors: ColorPair,
    ) -> None:
        settle_scene = character.animation.new_scene(scene_id="settle")
        final_fg = final_colors.fg_color
        final_bg = final_colors.bg_color
        if self.terminal.config.existing_color_handling == "dynamic":
            if final_fg or final_bg:
                settle_scene.apply_gradient_to_symbols(
                    character.input_symbol,
                    2,
                    fg_gradient=Gradient(snake_color, final_fg, steps=6) if final_fg else None,
                    bg_gradient=(
                        Gradient(self.terminal.config.terminal_background_color, final_bg, steps=6)
                        if final_bg
                        else None
                    ),
                )
            else:
                settle_scene.apply_gradient_to_symbols(
                    character.input_symbol,
                    2,
                    fg_gradient=Gradient(snake_color, self.DYNAMIC_NEUTRAL_GRAY, steps=4),
                )
                settle_scene.add_frame(character.input_symbol, 2, colors=ColorPair())
        else:
            final_fg = cast("Color", final_fg)
            settle_scene.apply_gradient_to_symbols(
                character.input_symbol,
                2,
                fg_gradient=Gradient(snake_color, final_fg, steps=6),
            )

    def _deposit_character(self, snake: _SnakeState) -> None:
        character = snake.carried.popleft()
        character.motion.set_coordinate(character.input_coord)
        character.layer = 0
        character.animation.activate_scene("settle")
        self.active_characters.add(character)
        snake.arrived = False
        if snake.carried:
            self._update_trail(snake)
            self._activate_route(snake)
        else:
            self.terminal.set_character_visibility(snake.head, is_visible=False)

    def _distance_to_edge(self, character: EffectCharacter, entry_edge: str) -> int:
        """Return a character's grid distance from an assigned canvas edge."""
        if entry_edge == "left":
            return character.input_coord.column - self.terminal.canvas.left
        if entry_edge == "right":
            return self.terminal.canvas.right - character.input_coord.column
        if entry_edge == "top":
            return self.terminal.canvas.top - character.input_coord.row
        return character.input_coord.row - self.terminal.canvas.bottom

    def build(self) -> None:
        """Assign every input character to one effective snake."""
        rows: dict[int, list[EffectCharacter]] = {}
        for character in self.terminal.get_characters():
            rows.setdefault(character.input_coord.row, []).append(character)
        characters: list[EffectCharacter] = []
        for row_index, row in enumerate(sorted(rows, reverse=True)):
            row_characters = sorted(rows[row], key=lambda character: character.input_coord.column)
            if row_index % 2:
                row_characters.reverse()
            characters.extend(row_characters)
        snake_count = min(self.config.snake_count, len(characters))
        if not snake_count:
            return
        final_gradient = Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.canvas.text_bottom,
            self.terminal.canvas.text_top,
            self.terminal.canvas.text_left,
            self.terminal.canvas.text_right,
            self.config.final_gradient_direction,
        )
        for character in characters:
            if self.terminal.config.existing_color_handling == "dynamic":
                self.character_final_color_map[character] = ColorPair(
                    fg=character.animation.input_fg_color,
                    bg=character.animation.input_bg_color,
                )
            else:
                self.character_final_color_map[character] = ColorPair(
                    fg=final_gradient_mapping[character.input_coord],
                )
        group_size, remainder = divmod(len(characters), snake_count)
        start = 0
        edges = ("left", "right", "top", "bottom")
        for snake_index in range(snake_count):
            size = group_size + (1 if snake_index < remainder else 0)
            entry_edge = edges[snake_index % len(edges)]
            carried_group = characters[start : start + size]
            if self._distance_to_edge(carried_group[-1], entry_edge) < self._distance_to_edge(
                carried_group[0],
                entry_edge,
            ):
                carried_group.reverse()
            carried = deque(carried_group)
            target = carried[0].input_coord
            if entry_edge == "left":
                spawn_coord = Coord(self.terminal.canvas.left - 1, target.row)
            elif entry_edge == "right":
                spawn_coord = Coord(self.terminal.canvas.right + 1, target.row)
            elif entry_edge == "top":
                spawn_coord = Coord(target.column, self.terminal.canvas.top + 1)
            else:
                spawn_coord = Coord(target.column, self.terminal.canvas.bottom - 1)
            color = self.config.snake_colors[snake_index % len(self.config.snake_colors)]
            head = self.terminal.add_character(self.config.head_symbol, spawn_coord)
            head.motion.set_coordinate(spawn_coord)
            head.animation.set_appearance(self.config.head_symbol, ColorPair(fg=color))
            head.layer = 2 + snake_index * 2
            for character in carried:
                character.motion.set_coordinate(spawn_coord)
                character.animation.set_appearance(character.input_symbol, ColorPair(fg=color))
                character.layer = head.layer - 1
                self._build_settle_scene(character, color, self.character_final_color_map[character])
            self.snakes.append(_SnakeState(head, carried, entry_edge, deque((spawn_coord,))))
            start += size

    def __next__(self) -> str:
        """Advance snake movement, deposition, and settling by one frame."""
        if self.pending_snakes or self.active_snakes or self.active_characters:
            self.update()
            completed_snakes: list[_SnakeState] = []
            for snake in self.active_snakes:
                self._update_trail(snake)
                if snake.arrived:
                    self._deposit_character(snake)
                    if not snake.carried:
                        completed_snakes.append(snake)
            for snake in completed_snakes:
                self.active_snakes.remove(snake)
            if self.spawn_countdown:
                self.spawn_countdown -= 1
            elif self.pending_snakes:
                if self.config.spawn_delay == 0:
                    while self.pending_snakes:
                        self._spawn_snake(self.pending_snakes.popleft())
                else:
                    self._spawn_snake(self.pending_snakes.popleft())
                    self.spawn_countdown = self.config.spawn_delay
            return self.frame
        if not self.final_frame_provided:
            self.final_frame_provided = True
            return self.frame
        raise StopIteration


class Snake(BaseEffect[SnakeConfig]):
    """Snakes carry characters through the canvas and assemble the input text."""

    @property
    def _config_cls(self) -> type[SnakeConfig]:
        return SnakeConfig

    @property
    def _iterator_cls(self) -> type[SnakeIterator]:
        return SnakeIterator
