"""Fireflies drift, blink, gather, and illuminate the input text."""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

from terminaltexteffects import (
    Animation,
    Color,
    ColorPair,
    Coord,
    EffectCharacter,
    EventHandler,
    Gradient,
    ParticlePool,
    ParticleReset,
    Scene,
    easing,
)
from terminaltexteffects.engine.base_config import (
    BaseConfig,
    FinalGradientDirectionArg,
    FinalGradientStepsArg,
    FinalGradientStopsArg,
)
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the Fireflies CLI command and its effect resources."""
    return "fireflies", Fireflies, FirefliesConfig


class FireflyState(Enum):
    """Lifecycle states used by primary and auxiliary fireflies."""

    DORMANT = auto()
    ENTERING = auto()
    WANDERING = auto()
    GATHERING = auto()
    ORBITING = auto()
    APPROACHING = auto()
    ILLUMINATING = auto()
    SETTLED = auto()
    DEPARTING = auto()


class FirefliesPhase(Enum):
    """Top-level phases for reveal, final pulse, and completion."""

    REVEAL = auto()
    PULSE = auto()
    COMPLETE = auto()


@dataclass
class Firefly:
    """Precomputed state and choreography for one input character."""

    character: EffectCharacter
    target_coord: Coord
    start_coord: Coord
    cluster_id: int
    activation_frame: int
    release_frame: int
    blink_signature: tuple[int, int, int, int]
    state: FireflyState = FireflyState.DORMANT
    attraction_strength: float = 0.0
    arrival_radius: int = 1
    group_leader: Firefly | None = None
    settled_frame: int | None = None


@dataclass
class FirefliesConfig(BaseConfig):
    """Configuration for the Fireflies effect."""

    parser_spec: argutils.ParserSpec = argutils.ParserSpec(
        name="fireflies",
        help="Fireflies drift through the night and gradually illuminate the text.",
        description="fireflies | Fireflies drift, gather, and gradually illuminate the text.",
        epilog=(
            "Example: terminaltexteffects fireflies --firefly-colors 6b5c20 d4a72c fff2a1 "
            "--firefly-symbols . '*' o '*' --movement-speed 0.18 --wander-cycles 3 --auxiliary-count 6 "
            "--final-gradient-stops 3f4f24 d6a928 ffe680 --final-gradient-steps 12 "
            "--final-gradient-direction horizontal"
        ),
    )

    firefly_colors: tuple[Color, ...] = argutils.ArgSpec(
        name="--firefly-colors",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=(Color("#6b5c20"), Color("#d4a72c"), Color("#fff2a1")),
        metavar=argutils.ColorArg.METAVAR,
        help="Colors used from dimmest to brightest while fireflies blink.",
    )  # pyright: ignore[reportAssignmentType]

    firefly_symbols: tuple[str, ...] = argutils.ArgSpec(
        name="--firefly-symbols",
        type=argutils.Symbol.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=(".", "*", "o", "*"),
        metavar=argutils.Symbol.METAVAR,
        help="One-cell symbols used in sequence while fireflies blink.",
    )  # pyright: ignore[reportAssignmentType]

    movement_speed: float = argutils.ArgSpec(
        name="--movement-speed",
        type=argutils.PositiveFloat.type_parser,
        default=0.18,
        metavar=argutils.PositiveFloat.METAVAR,
        help="Base movement speed for fireflies. Individual speeds vary around this value.",
    )  # pyright: ignore[reportAssignmentType]

    wander_cycles: int = argutils.ArgSpec(
        name="--wander-cycles",
        type=argutils.PositiveInt.type_parser,
        default=3,
        metavar=argutils.PositiveInt.METAVAR,
        help="Maximum number of wandering waypoints before a firefly gathers near the text.",
    )  # pyright: ignore[reportAssignmentType]

    auxiliary_count: int = argutils.ArgSpec(
        name="--auxiliary-count",
        type=argutils.NonNegativeInt.type_parser,
        default=6,
        metavar=argutils.NonNegativeInt.METAVAR,
        help="Maximum number of atmospheric fireflies. Tiny canvases automatically use fewer.",
    )  # pyright: ignore[reportAssignmentType]

    final_gradient_stops: tuple[Color, ...] = FinalGradientStopsArg(
        default=(Color("#3f4f24"), Color("#d6a928"), Color("#ffe680")),
    )  # pyright: ignore[reportAssignmentType]

    final_gradient_steps: tuple[int, ...] | int = FinalGradientStepsArg(
        default=12,
    )  # pyright: ignore[reportAssignmentType]

    final_gradient_direction: Gradient.Direction = FinalGradientDirectionArg(
        default=Gradient.Direction.HORIZONTAL,
    )  # pyright: ignore[reportAssignmentType]


class FirefliesIterator(BaseEffectIterator[FirefliesConfig]):
    """Iterator for the Fireflies effect."""

    CLUSTER_WIDTH = 4
    CLUSTER_HEIGHT = 2

    def __init__(self, effect: Fireflies) -> None:
        """Initialize and precompute the Fireflies choreography."""
        super().__init__(effect)
        self.fireflies: list[Firefly] = []
        self.clusters: dict[int, list[Firefly]] = {}
        self.character_final_color_map: dict[EffectCharacter, ColorPair] = {}
        self.frame_count = 0
        self.phase = FirefliesPhase.REVEAL
        self.final_frame_shown = False
        self.pulse_queue: list[list[Firefly]] = []
        self.pulse_activation_frames: list[int] = []
        self._pulse_delay = 0
        self.auxiliary_states: dict[EffectCharacter, FireflyState] = {}
        self.auxiliary_activation_frames: list[int] = []
        self.auxiliary_departure_frame: int | None = None
        self.halo_emissions = 0
        self.build()
        if not self.fireflies:
            self.phase = FirefliesPhase.COMPLETE

    def _clamp_coord(self, column: int, row: int) -> Coord:
        """Clamp a coordinate to the current canvas."""
        canvas = self.terminal.canvas
        return Coord(
            min(max(column, canvas.left), canvas.right),
            min(max(row, canvas.bottom), canvas.top),
        )

    def _perimeter_coords(self) -> list[Coord]:
        """Return every unique coordinate on the canvas perimeter."""
        canvas = self.terminal.canvas
        coords = {
            Coord(column, row) for column in range(canvas.left, canvas.right + 1) for row in (canvas.bottom, canvas.top)
        }
        coords.update(
            Coord(column, row) for row in range(canvas.bottom, canvas.top + 1) for column in (canvas.left, canvas.right)
        )
        return sorted(coords, key=lambda coord: (coord.row, coord.column))

    def _curve_control(self, start: Coord, end: Coord) -> Coord:
        """Create a gently offset, in-canvas control point between two coordinates."""
        midpoint_column = round((start.column + end.column) / 2)
        midpoint_row = round((start.row + end.row) / 2)
        horizontal_room = max(self.terminal.canvas.width // 6, 1)
        vertical_room = max(self.terminal.canvas.height // 6, 1)
        return self._clamp_coord(
            midpoint_column + random.randint(-horizontal_room, horizontal_room),
            midpoint_row + random.randint(-vertical_room, vertical_room),
        )

    def _blink_palette(self) -> tuple[Color, Color, Color]:
        """Return dim, warm, and peak colors even when only one color is configured."""
        if len(self.config.firefly_colors) == 1:
            base_color = self.config.firefly_colors[0]
            return (
                Animation.adjust_color_brightness(base_color, 0.35),
                Animation.adjust_color_brightness(base_color, 0.7),
                base_color,
            )
        spectrum = list(Gradient(*self.config.firefly_colors, steps=3))
        return spectrum[0], spectrum[len(spectrum) // 2], spectrum[-1]

    def _make_blink_scene(self, firefly: Firefly) -> None:
        """Create an independently phased looping blink scene."""
        phase, period, peak_hold, symbol_offset = firefly.blink_signature
        colors = list(self._blink_palette())
        levels = colors + colors[-2:0:-1]
        phase %= len(levels)
        levels = levels[phase:] + levels[:phase]
        blink_scene = firefly.character.animation.new_scene(scene_id="blink", is_looping=True)
        for index, color in enumerate(levels):
            symbol = self.config.firefly_symbols[(index + symbol_offset) % len(self.config.firefly_symbols)]
            duration = peak_hold if color == colors[-1] else period
            blink_scene.add_frame(symbol, duration, colors=ColorPair(fg=color))

    def _make_paths(self, firefly: Firefly, focus: Coord, cluster_index: int) -> None:
        """Build bounded entry, wander, optional orbit, and approach paths."""
        character = firefly.character
        canvas = self.terminal.canvas
        speed = max(self.config.movement_speed * random.uniform(0.75, 1.25), 0.01)

        inward_column = firefly.start_coord.column
        inward_row = firefly.start_coord.row
        if firefly.start_coord.column == canvas.left:
            inward_column += min(2, canvas.width - 1)
        elif firefly.start_coord.column == canvas.right:
            inward_column -= min(2, canvas.width - 1)
        if firefly.start_coord.row == canvas.bottom:
            inward_row += min(1, canvas.height - 1)
        elif firefly.start_coord.row == canvas.top:
            inward_row -= min(1, canvas.height - 1)
        entry_coord = self._clamp_coord(inward_column, inward_row)
        enter_path = character.motion.new_path(path_id="enter", speed=speed, ease=easing.in_out_sine, layer=2)
        enter_path.new_waypoint(
            entry_coord,
            bezier_control=self._curve_control(firefly.start_coord, entry_coord),
        )

        wander_path = character.motion.new_path(
            path_id="wander",
            speed=max(speed * 0.75, 0.01),
            ease=easing.in_out_sine,
            layer=2,
        )
        last_coord = entry_coord
        horizontal_radius = max(min(canvas.width // 4, 3), 1)
        vertical_radius = max(min(canvas.height // 4, 2), 1)
        for _ in range(self.config.wander_cycles):
            next_coord = self._clamp_coord(
                focus.column + random.randint(-horizontal_radius, horizontal_radius),
                focus.row + random.randint(-vertical_radius, vertical_radius),
            )
            wander_path.new_waypoint(next_coord, bezier_control=self._curve_control(last_coord, next_coord))
            last_coord = next_coord

        if canvas.width >= 3 and canvas.height >= 2 and cluster_index % 3 == 1:
            orbit_path = character.motion.new_path(
                path_id="orbit",
                speed=max(speed * 0.7, 0.01),
                ease=easing.in_out_sine,
                layer=2,
            )
            first_orbit = self._clamp_coord(focus.column - 1, focus.row + 1)
            second_orbit = self._clamp_coord(focus.column + 1, focus.row - 1)
            orbit_path.new_waypoint(first_orbit, bezier_control=self._curve_control(last_coord, first_orbit))
            orbit_path.new_waypoint(second_orbit, bezier_control=self._curve_control(first_orbit, second_orbit))
            last_coord = second_orbit

        approach_path = character.motion.new_path(
            path_id="approach",
            speed=max(speed * 1.1, 0.01),
            ease=easing.in_out_quad,
            layer=2,
        )
        column_direction = 1 if firefly.target_coord.column >= focus.column else -1
        row_direction = 1 if firefly.target_coord.row >= focus.row else -1
        overshoot = self._clamp_coord(
            firefly.target_coord.column + column_direction,
            firefly.target_coord.row + row_direction,
        )
        approach_path.new_waypoint(overshoot, bezier_control=self._curve_control(last_coord, overshoot))
        approach_path.new_waypoint(
            firefly.target_coord,
            bezier_control=self._curve_control(overshoot, firefly.target_coord),
        )

    def _make_landing_scene(self, firefly: Firefly) -> None:
        """Build the finite symbol-restoration scene for a landing firefly."""
        character = firefly.character
        final_colors = self.character_final_color_map[character]
        peak_color = self._blink_palette()[-1]
        landing_scene = character.animation.new_scene(scene_id="landing")
        landing_scene.add_frame(
            self.config.firefly_symbols[-1],
            2,
            colors=ColorPair(fg=peak_color, bg=final_colors.bg_color),
        )
        landing_scene.add_frame(
            character.input_symbol,
            2,
            colors=ColorPair(fg=peak_color, bg=final_colors.bg_color),
        )
        if final_colors.fg_color is not None:
            for color in Gradient(peak_color, final_colors.fg_color, steps=4):
                landing_scene.add_frame(
                    character.input_symbol,
                    2,
                    colors=ColorPair(fg=color, bg=final_colors.bg_color),
                )
        else:
            landing_scene.add_frame(
                character.input_symbol,
                2,
                colors=ColorPair(
                    fg=Animation.adjust_color_brightness(peak_color, 0.55),
                    bg=final_colors.bg_color,
                ),
            )
        landing_scene.add_frame(character.input_symbol, 2, colors=final_colors)

        pulse_scene = character.animation.new_scene(scene_id="pulse")
        pulse_scene.add_frame(character.input_symbol, 2, colors=final_colors)
        pulse_scene.add_frame(
            character.input_symbol,
            2,
            colors=ColorPair(fg=peak_color, bg=final_colors.bg_color),
        )
        pulse_scene.add_frame(
            character.input_symbol,
            2,
            colors=ColorPair(fg=self.config.firefly_colors[-1], bg=final_colors.bg_color),
        )
        pulse_scene.add_frame(character.input_symbol, 2, colors=final_colors)

        character.event_handler.register_event(
            EventHandler.Event.SCENE_COMPLETE,
            landing_scene,
            EventHandler.Action.CALLBACK,
            EventHandler.Callback(self._settle_firefly, firefly),
        )

    def _register_path_events(self, firefly: Firefly) -> None:
        """Connect bounded motion paths to explicit state transitions."""
        character = firefly.character
        character.event_handler.register_event(
            EventHandler.Event.PATH_COMPLETE,
            "enter",
            EventHandler.Action.CALLBACK,
            EventHandler.Callback(self._finish_entry, firefly),
        )
        character.event_handler.register_event(
            EventHandler.Event.PATH_COMPLETE,
            "wander",
            EventHandler.Action.CALLBACK,
            EventHandler.Callback(self._finish_wander, firefly),
        )
        if "orbit" in character.motion.paths:
            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE,
                "orbit",
                EventHandler.Action.CALLBACK,
                EventHandler.Callback(self._finish_orbit, firefly),
            )
        character.event_handler.register_event(
            EventHandler.Event.PATH_COMPLETE,
            "approach",
            EventHandler.Action.CALLBACK,
            EventHandler.Callback(self._land_firefly, firefly),
        )

    def _finish_entry(self, character: EffectCharacter, firefly: Firefly) -> None:
        """Advance an entering firefly into its curved wander path."""
        firefly.state = FireflyState.WANDERING
        firefly.attraction_strength = 0.25
        character.motion.activate_path("wander")

    def _finish_wander(self, _: EffectCharacter, firefly: Firefly) -> None:
        """Hold a wandering firefly near its cluster until its release frame."""
        firefly.state = FireflyState.GATHERING
        firefly.attraction_strength = 0.6

    def _finish_orbit(self, character: EffectCharacter, firefly: Firefly) -> None:
        """Move an orbiting firefly into its final angled approach."""
        firefly.state = FireflyState.APPROACHING
        firefly.attraction_strength = 0.9
        character.motion.activate_path("approach")

    def _land_firefly(self, character: EffectCharacter, firefly: Firefly) -> None:
        """Restore the input coordinate and begin finite illumination."""
        character.motion.set_coordinate(firefly.target_coord)
        firefly.state = FireflyState.ILLUMINATING
        firefly.attraction_strength = 1.0
        character.animation.activate_scene("landing")

    def _settle_firefly(self, character: EffectCharacter, firefly: Firefly) -> None:
        """Mark a completed landing and leave its exact final appearance stable."""
        character.motion.set_coordinate(character.input_coord)
        character.animation.set_appearance(character.input_symbol, self.character_final_color_map[character])
        character.layer = 0
        firefly.state = FireflyState.SETTLED
        firefly.settled_frame = self.frame_count
        self._emit_halo(character.input_coord)

    def _activate_approach(self, firefly: Firefly) -> None:
        """Release one gathered firefly through an optional orbit and approach."""
        character = firefly.character
        if "orbit" in character.motion.paths:
            firefly.state = FireflyState.ORBITING
            firefly.attraction_strength = 0.75
            character.motion.activate_path("orbit")
        else:
            firefly.state = FireflyState.APPROACHING
            firefly.attraction_strength = 0.9
            character.motion.activate_path("approach")
        self.active_characters.add(character)

    def _prepare_pulse(self) -> None:
        """Group settled fireflies into a diagonal warm-light wave."""
        pulse_groups: dict[int, list[Firefly]] = {}
        for firefly in self.fireflies:
            diagonal = firefly.target_coord.column + firefly.target_coord.row
            pulse_groups.setdefault(diagonal, []).append(firefly)
        self.pulse_queue = [pulse_groups[key] for key in sorted(pulse_groups)]
        self._pulse_delay = 0
        self.phase = FirefliesPhase.PULSE

    def _initialize_auxiliary(self, particle: EffectCharacter) -> None:
        """Create reusable blink and halo scenes for one pooled helper."""
        colors = self._blink_palette()
        blink_scene = particle.animation.new_scene(scene_id="blink", is_looping=True)
        phase = random.randrange(len(colors))
        ordered_colors = list(colors[phase:] + colors[:phase])
        for index, color in enumerate(ordered_colors):
            blink_scene.add_frame(
                self.config.firefly_symbols[index % len(self.config.firefly_symbols)],
                random.randint(2, 5),
                colors=ColorPair(fg=color),
            )
        for index, color in enumerate(reversed(ordered_colors[:-1])):
            blink_scene.add_frame(
                self.config.firefly_symbols[(index + 1) % len(self.config.firefly_symbols)],
                random.randint(2, 5),
                colors=ColorPair(fg=color),
            )

        halo_scene = particle.animation.new_scene(scene_id="halo")
        halo_scene.add_frame("*", 2, colors=ColorPair(fg=colors[-1]))
        halo_scene.add_frame(".", 2, colors=ColorPair(fg=colors[1]))
        halo_scene.add_frame(".", 1, colors=ColorPair(fg=colors[0]))
        particle.layer = 1
        self.auxiliary_states[particle] = FireflyState.DORMANT

    def _build_auxiliary_pool(self) -> None:
        """Create a canvas-scaled, strictly capped pool of atmospheric helpers."""
        canvas_area = self.terminal.canvas.width * self.terminal.canvas.height
        effective_count = min(self.config.auxiliary_count, 12, canvas_area // 8)
        self.auxiliary_pool = ParticlePool(
            self.terminal,
            self.active_characters,
            self.config.firefly_symbols,
            initial_count=effective_count,
            max_size=effective_count,
            initializer=self._initialize_auxiliary,
        )
        self.auxiliary_activation_frames = sorted(random.randint(1, 6) for _ in range(effective_count))
        earliest_release = min((firefly.release_frame for firefly in self.fireflies), default=18)
        self._auxiliary_departure_deadline = max(12, earliest_release - 6)

    def _setup_atmospheric_path(self, particle: EffectCharacter) -> None:
        """Prepare one finite, gently curved atmospheric wander."""
        wander_path = particle.motion.new_path(
            path_id="atmosphere",
            speed=max(self.config.movement_speed * random.uniform(0.7, 1.1), 0.01),
            ease=easing.in_out_sine,
            layer=1,
        )
        last_coord = particle.motion.current_coord
        for _ in range(self.config.wander_cycles + 2):
            next_coord = self.terminal.canvas.random_coord()
            wander_path.new_waypoint(next_coord, bezier_control=self._curve_control(last_coord, next_coord))
            last_coord = next_coord
        blink_scene = particle.animation.query_scene("blink")
        blink_scene.reset_scene()
        particle.animation.activate_scene(blink_scene)
        particle.motion.activate_path(wander_path)
        self.auxiliary_states[particle] = FireflyState.WANDERING

    def _emit_due_auxiliaries(self) -> None:
        """Emit scheduled atmospheric particles from perimeter coordinates."""
        perimeter = self._perimeter_coords()
        while self.auxiliary_activation_frames and self.frame_count >= self.auxiliary_activation_frames[0]:
            self.auxiliary_activation_frames.pop(0)
            self.auxiliary_pool.emit(
                random.choice(perimeter),
                self._setup_atmospheric_path,
                reset=ParticleReset(clear_paths=True, clear_scenes=False, clear_events=True),
            )

    def _mark_auxiliary_reclaimed(self, character: EffectCharacter, *_: object) -> None:
        """Record that a helper is hidden and available for reuse."""
        self.auxiliary_states[character] = FireflyState.DORMANT

    def _depart_auxiliaries(self) -> None:
        """Send every emitted atmospheric helper beyond a canvas edge and reclaim it."""
        if self.auxiliary_departure_frame is not None:
            return
        self.auxiliary_departure_frame = self.frame_count
        self.auxiliary_activation_frames.clear()
        available_particles = set(self.auxiliary_pool.available)
        for particle in self.auxiliary_pool.particles:
            if particle in available_particles:
                continue
            depart_path = particle.motion.new_path(
                path_id="depart",
                speed=max(self.config.movement_speed * 1.4, 0.01),
                ease=easing.in_sine,
                layer=1,
            )
            target = self.terminal.canvas.random_coord(outside_scope=True)
            depart_path.new_waypoint(target, bezier_control=self._curve_control(particle.motion.current_coord, target))
            depart_scene = particle.animation.new_scene(scene_id="depart", sync=Scene.SyncMetric.DISTANCE)
            for color in reversed(self._blink_palette()):
                depart_scene.add_frame(particle.input_symbol, 2, colors=ColorPair(fg=color))
            self.auxiliary_pool.reclaim_on_event(
                particle,
                depart_path,
                event=EventHandler.Event.PATH_COMPLETE,
            )
            particle.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE,
                depart_path,
                EventHandler.Action.CALLBACK,
                EventHandler.Callback(self._mark_auxiliary_reclaimed),
            )
            self.auxiliary_states[particle] = FireflyState.DEPARTING
            particle.animation.activate_scene(depart_scene)
            particle.motion.activate_path(depart_path)
            self.active_characters.add(particle)

    def _emit_halo(self, origin: Coord) -> None:
        """Reuse one available atmospheric helper as a prompt landing halo."""
        if not hasattr(self, "auxiliary_pool") or not self.auxiliary_pool.available:
            return

        def setup_halo(particle: EffectCharacter) -> None:
            halo_scene = particle.animation.query_scene("halo")
            halo_scene.reset_scene()
            self.auxiliary_pool.reclaim_on_event(particle, halo_scene)
            particle.event_handler.register_event(
                EventHandler.Event.SCENE_COMPLETE,
                halo_scene,
                EventHandler.Action.CALLBACK,
                EventHandler.Callback(self._mark_auxiliary_reclaimed),
            )
            self.auxiliary_states[particle] = FireflyState.ILLUMINATING
            particle.animation.activate_scene(halo_scene)

        emitted = self.auxiliary_pool.emit(
            origin,
            setup_halo,
            symbol="*",
            reset=ParticleReset(clear_paths=True, clear_scenes=False, clear_events=True),
        )
        if emitted is not None:
            self.halo_emissions += 1

    def _step_auxiliaries(self) -> None:
        """Advance scheduled emissions and enforce bounded atmospheric departure."""
        if not self.auxiliary_pool.particles:
            return
        if self.auxiliary_departure_frame is None:
            self._emit_due_auxiliaries()
            settled_count = sum(firefly.state is FireflyState.SETTLED for firefly in self.fireflies)
            settlement_ratio = settled_count / len(self.fireflies) if self.fireflies else 1
            if self.frame_count >= self._auxiliary_departure_deadline or settlement_ratio >= 0.75:
                self._depart_auxiliaries()
        available_particles = set(self.auxiliary_pool.available)
        for particle in self.auxiliary_pool.particles:
            if particle not in available_particles and particle.is_visible:
                self.active_characters.add(particle)

    def _step_reveal(self) -> None:
        """Activate, release, and tick primary fireflies for one reveal frame."""
        self._step_auxiliaries()
        for firefly in self.fireflies:
            character = firefly.character
            if firefly.state is FireflyState.DORMANT and self.frame_count >= firefly.activation_frame:
                firefly.state = FireflyState.ENTERING
                firefly.attraction_strength = 0.1
                self.terminal.set_character_visibility(character, is_visible=True)
                character.animation.activate_scene("blink")
                character.motion.activate_path("enter")
            if firefly.state is FireflyState.GATHERING and self.frame_count >= firefly.release_frame:
                self._activate_approach(firefly)
            if firefly.state is not FireflyState.DORMANT and firefly.state is not FireflyState.SETTLED:
                self.active_characters.add(character)
        self.update()
        auxiliaries_reclaimed = len(self.auxiliary_pool.available) == len(self.auxiliary_pool)
        if (
            self.fireflies
            and all(firefly.state is FireflyState.SETTLED for firefly in self.fireflies)
            and auxiliaries_reclaimed
        ):
            self._prepare_pulse()

    def _step_pulse(self) -> None:
        """Activate and tick the next diagonal group in the final warm pulse."""
        if self.pulse_queue and self._pulse_delay == 0:
            group = self.pulse_queue.pop(0)
            self.pulse_activation_frames.append(self.frame_count)
            for firefly in group:
                pulse_scene = firefly.character.animation.query_scene("pulse")
                pulse_scene.reset_scene()
                firefly.character.animation.activate_scene(pulse_scene)
                self.active_characters.add(firefly.character)
            self._pulse_delay = 2
        elif self._pulse_delay:
            self._pulse_delay -= 1
        self.update()
        if not self.pulse_queue and not self.active_characters:
            self.phase = FirefliesPhase.COMPLETE

    def build(self) -> None:
        """Precompute clusters, blink schedules, paths, and final colors."""
        characters = self.terminal.get_characters()
        final_gradient = Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.canvas.text_bottom,
            self.terminal.canvas.text_top,
            self.terminal.canvas.text_left,
            self.terminal.canvas.text_right,
            self.config.final_gradient_direction,
        )
        for character in characters:
            if self.terminal.config.existing_color_handling in ("dynamic", "always"):
                self.character_final_color_map[character] = ColorPair(
                    fg=character.animation.input_fg_color,
                    bg=character.animation.input_bg_color,
                )
            else:
                self.character_final_color_map[character] = ColorPair(fg=final_mapping[character.input_coord])

        bucketed_characters: dict[tuple[int, int], list[EffectCharacter]] = {}
        for character in characters:
            bucket = (
                (character.input_coord.column - self.terminal.canvas.text_left) // self.CLUSTER_WIDTH,
                (character.input_coord.row - self.terminal.canvas.text_bottom) // self.CLUSTER_HEIGHT,
            )
            bucketed_characters.setdefault(bucket, []).append(character)
        bucket_order = list(bucketed_characters)
        random.shuffle(bucket_order)

        blink_signatures = [
            (phase, period, peak_hold, symbol_offset)
            for phase in range(4)
            for period in range(2, 6)
            for peak_hold in range(1, 3)
            for symbol_offset in range(4)
        ]
        random.shuffle(blink_signatures)
        perimeter = self._perimeter_coords()

        for cluster_id, bucket in enumerate(bucket_order):
            cluster_characters = bucketed_characters[bucket]
            random.shuffle(cluster_characters)
            focus = self._clamp_coord(
                round(sum(character.input_coord.column for character in cluster_characters) / len(cluster_characters)),
                round(sum(character.input_coord.row for character in cluster_characters) / len(cluster_characters)),
            )
            release_frame = 28 + cluster_id * 9 + random.randint(0, 6)
            cluster: list[Firefly] = []
            for character_index, character in enumerate(cluster_characters):
                overall_index = len(self.fireflies)
                start_coord = random.choice(perimeter)
                firefly = Firefly(
                    character=character,
                    target_coord=character.input_coord,
                    start_coord=start_coord,
                    cluster_id=cluster_id,
                    activation_frame=cluster_id * 2 + random.randint(1, 8),
                    release_frame=release_frame + random.randint(0, 3),
                    blink_signature=blink_signatures[overall_index % len(blink_signatures)],
                    arrival_radius=max(1, min(self.terminal.canvas.width, self.terminal.canvas.height) // 8),
                )
                character.motion.set_coordinate(start_coord)
                self._make_blink_scene(firefly)
                self._make_paths(firefly, focus, character_index)
                self._make_landing_scene(firefly)
                self._register_path_events(firefly)
                cluster.append(firefly)
                self.fireflies.append(firefly)
            for firefly in cluster[1:]:
                firefly.group_leader = cluster[0]
            self.clusters[cluster_id] = cluster
        self._build_auxiliary_pool()

    def __next__(self) -> str:
        """Advance the reveal, final pulse, or stable completion frame."""
        if self.phase is FirefliesPhase.COMPLETE:
            if not self.final_frame_shown:
                self.final_frame_shown = True
                return self.frame
            raise StopIteration

        self.frame_count += 1
        if self.phase is FirefliesPhase.REVEAL:
            self._step_reveal()
        elif self.phase is FirefliesPhase.PULSE:
            self._step_pulse()
        return self.frame


class Fireflies(BaseEffect[FirefliesConfig]):
    """Fireflies drift through the canvas and illuminate the input text."""

    @property
    def _config_cls(self) -> type[FirefliesConfig]:
        return FirefliesConfig

    @property
    def _iterator_cls(self) -> type[FirefliesIterator]:
        return FirefliesIterator
