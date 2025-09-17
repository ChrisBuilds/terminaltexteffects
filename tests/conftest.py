"""Pytest fixtures and constants for terminaltexteffects package."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

import pytest

from terminaltexteffects.effects import (
    effect_beams,
    effect_binarypath,
    effect_blackhole,
    effect_bouncyballs,
    effect_bubbles,
    effect_burn,
    effect_colorshift,
    effect_crumble,
    effect_decrypt,
    effect_errorcorrect,
    effect_expand,
    effect_fireworks,
    effect_highlight,
    effect_laseretch,
    effect_matrix,
    effect_middleout,
    effect_orbittingvolley,
    effect_overflow,
    effect_pour,
    effect_print,
    effect_rain,
    effect_random_sequence,
    effect_rings,
    effect_scattered,
    effect_slice,
    effect_slide,
    effect_spotlights,
    effect_spray,
    effect_swarm,
    effect_sweep,
    effect_synthgrid,
    effect_unstable,
    effect_vhstape,
    effect_waves,
    effect_wipe,
)
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils import geometry
from terminaltexteffects.utils.easing import (
    EasingFunction,
    in_back,
    in_bounce,
    in_circ,
    in_cubic,
    in_elastic,
    in_expo,
    in_out_back,
    in_out_bounce,
    in_out_circ,
    in_out_cubic,
    in_out_elastic,
    in_out_expo,
    in_out_quad,
    in_out_quart,
    in_out_quint,
    in_out_sine,
    in_quad,
    in_quart,
    in_quint,
    in_sine,
    out_back,
    out_bounce,
    out_circ,
    out_cubic,
    out_elastic,
    out_expo,
    out_quad,
    out_quart,
    out_quint,
    out_sine,
)
from terminaltexteffects.utils.graphics import Color, Gradient

if TYPE_CHECKING:
    from collections.abc import Generator

    from terminaltexteffects.engine.base_effect import BaseEffect

INPUT_EMPTY = ""
INPUT_SINGLE_CHAR = "a"
INPUT_SINGLE_COLUMN = """
a
b
c
d
e
f"""
INPUT_SINGLE_ROW = "abcdefg"
INPUT_LARGE = """
0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ
123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0
23456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ01
3456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ012
456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123
56789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ01234
6789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ012345
789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456
89abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ01234567
9abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ012345678
"""
INPUT_MEDIUM = """
0123456789abcdefg
123456789abcdefgh
23456789abcdefghi
3456789abcdefghij
456789abcdefghijk"""
INPUT_TABS = """Tabs\tTabs\t\tTabs\t\t\tTabs"""
CANVAS_TEST_INPUT = """TL!!!!!!!!!!!!!!!!!!!!!TOP*********************TR
+                 <----50---->                  #
+                       |                       #
+                       |                       #
L        ^              |                       R
E        |              |                       I
F MID 13 |            CENTER                MID G
T        |              |                       H
-        v              |                       T
-                       |                       @
-                       |                       @
-                       |                       @
BL--------------------BOTTOM...................BR"""

COLOR_SEQUENCES = (
    "\x1b[38;5;231m....\x1b[39m....| \x1b[38;5;95m\x1b[48;5;128mggggggg\x1b[0m \x1b[38;5;180mggggggg "
    "\x1b[38;5;146m:gggggg; \x1b[38;5;64mggggggg \x1b[38;5;182mggggggg \x1b[38;5;195m:gggggg; "
    "\x1b[38;5;214mggggggg \x1b[38;5;146m;gggggg  \x1b[38;5;174mggggggg \x1b[0m"
)

TEST_INPUTS = {
    "empty": INPUT_EMPTY,
    "single_char": INPUT_SINGLE_CHAR,
    "single_column": INPUT_SINGLE_COLUMN,
    "single_row": INPUT_SINGLE_ROW,
    "medium": INPUT_MEDIUM,
    "tabs": INPUT_TABS,
    "large": INPUT_LARGE,
    "canvas": CANVAS_TEST_INPUT,
    "color_sequences": COLOR_SEQUENCES,
}

EFFECTS = [
    effect_beams.Beams,
    effect_binarypath.BinaryPath,
    effect_blackhole.Blackhole,
    effect_bouncyballs.BouncyBalls,
    effect_bubbles.Bubbles,
    effect_burn.Burn,
    effect_colorshift.ColorShift,
    effect_crumble.Crumble,
    effect_decrypt.Decrypt,
    effect_errorcorrect.ErrorCorrect,
    effect_expand.Expand,
    effect_fireworks.Fireworks,
    effect_highlight.Highlight,
    effect_laseretch.LaserEtch,
    effect_matrix.Matrix,
    effect_middleout.MiddleOut,
    effect_orbittingvolley.OrbittingVolley,
    effect_overflow.Overflow,
    effect_pour.Pour,
    effect_print.Print,
    effect_rain.Rain,
    effect_random_sequence.RandomSequence,
    effect_rings.Rings,
    effect_scattered.Scattered,
    effect_slice.Slice,
    effect_slide.Slide,
    effect_spotlights.Spotlights,
    effect_spray.Spray,
    effect_swarm.Swarm,
    effect_sweep.Sweep,
    effect_synthgrid.SynthGrid,
    effect_unstable.Unstable,
    effect_vhstape.VHSTape,
    effect_waves.Waves,
    effect_wipe.Wipe,
]

EASING_FUNCTIONS = [
    in_sine,
    out_sine,
    in_out_sine,
    in_quad,
    out_quad,
    in_out_quad,
    in_cubic,
    out_cubic,
    in_out_cubic,
    in_quart,
    out_quart,
    in_out_quart,
    in_quint,
    out_quint,
    in_out_quint,
    in_expo,
    out_expo,
    in_out_expo,
    in_circ,
    out_circ,
    in_out_circ,
    in_elastic,
    out_elastic,
    in_out_elastic,
    in_back,
    out_back,
    in_out_back,
    in_bounce,
    out_bounce,
    in_out_bounce,
]

ANCHORS = ["sw", "s", "se", "e", "ne", "n", "nw", "w", "c"]


@pytest.fixture(autouse=True)
def clear_lru_cache() -> Generator[None, Any, None]:
    """Fixture to clear the LRU caches for geometry functions."""
    yield
    geometry.find_coords_on_circle.cache_clear()  # type: ignore[attr-defined]
    geometry.find_coords_in_circle.cache_clear()  # type: ignore[attr-defined]
    geometry.find_coords_in_rect.cache_clear()  # type: ignore[attr-defined]
    geometry.find_coord_at_distance.cache_clear()  # type: ignore[attr-defined]
    geometry.find_coord_on_bezier_curve.cache_clear()  # type: ignore[attr-defined]
    geometry.find_coord_on_line.cache_clear()  # type: ignore[attr-defined]
    geometry.find_length_of_bezier_curve.cache_clear()  # type: ignore[attr-defined]
    geometry.find_length_of_line.cache_clear()  # type: ignore[attr-defined]
    geometry.find_normalized_distance_from_center.cache_clear()  # type: ignore[attr-defined]


@pytest.fixture
def input_data(request: pytest.FixtureRequest) -> str:
    """Fixture to provide input data for tests."""
    return TEST_INPUTS[request.param]


@pytest.fixture(params=EFFECTS)
def effect(request: pytest.FixtureRequest) -> BaseEffect:
    """Fixture to provide effect instances for tests."""
    return request.param


@pytest.fixture(params=EASING_FUNCTIONS)
def easing_function_1(request: pytest.FixtureRequest) -> EasingFunction:
    """Fixture to provide the first easing function for tests."""
    return request.param


@pytest.fixture(params=EASING_FUNCTIONS)
def easing_function_2(request: pytest.FixtureRequest) -> EasingFunction:
    """Fixture to provide the second easing function for tests."""
    return request.param


@pytest.fixture(params=[True, False])
def no_color(request: pytest.FixtureRequest) -> bool:
    """Fixture to provide a boolean indicating whether to disable color."""
    return request.param


@pytest.fixture(params=[True, False])
def xterm_colors(request: pytest.FixtureRequest) -> bool:
    """Fixture to provide a boolean indicating whether to use xterm colors."""
    return request.param


@pytest.fixture(params=ANCHORS)
def canvas_anchor(request: pytest.FixtureRequest) -> str:
    """Fixture to provide canvas anchor positions for tests."""
    return request.param


@pytest.fixture(params=ANCHORS)
def text_anchor(request: pytest.FixtureRequest) -> str:
    """Fixture to provide text anchor positions for tests."""
    return request.param


@pytest.fixture(params=[(60, 30), (25, 8)], ids=["60x30", "25x8"])
def canvas_dimensions(request: pytest.FixtureRequest) -> tuple[int, int]:
    """Fixture to provide canvas dimensions for tests."""
    return request.param


@pytest.fixture
def terminal_config_with_color_options(xterm_colors: bool, no_color: bool) -> TerminalConfig:  # noqa: FBT001
    """Fixture to provide terminal configuration with color options."""
    terminal_config = TerminalConfig._build_config()
    terminal_config.xterm_colors = xterm_colors
    terminal_config.no_color = no_color
    terminal_config.frame_rate = 0
    return terminal_config


@pytest.fixture
def terminal_config_default_no_framerate() -> TerminalConfig:
    """Fixture to provide terminal configuration with default settings and no frame rate."""
    terminal_config = TerminalConfig._build_config()
    terminal_config.frame_rate = 0
    return terminal_config


@pytest.fixture
def terminal_config_with_anchoring(
    canvas_dimensions: tuple[int, int],
    canvas_anchor: Literal["sw", "s", "se", "e", "ne", "n", "nw", "w", "c"],
    text_anchor: Literal["sw", "s", "se", "e", "ne", "n", "nw", "w", "c"],
) -> TerminalConfig:
    """Fixture to provide terminal configuration with anchoring options."""
    terminal_config = TerminalConfig._build_config()
    terminal_config.frame_rate = 0
    terminal_config.canvas_width = canvas_dimensions[0]
    terminal_config.canvas_height = canvas_dimensions[1]
    terminal_config.anchor_canvas = canvas_anchor
    terminal_config.anchor_text = text_anchor
    return terminal_config


@pytest.fixture(params=[(Color("#000000"), Color("#ff00ff"), Color("#0ffff0")), (Color("#ff0fff"),)])
def gradient_stops(request: pytest.FixtureRequest) -> Color | tuple[Color, ...]:
    """Fixture to provide gradient stops for tests."""
    return request.param


@pytest.fixture(params=[(1,), (4,), (1, 3)])
def gradient_steps(request: pytest.FixtureRequest) -> tuple[int, ...]:
    """Fixture to provide gradient steps for tests."""
    return request.param


@pytest.fixture(params=[1, 4])
def gradient_frames(request: pytest.FixtureRequest) -> int:
    """Fixture to provide gradient frames for tests."""
    return request.param


@pytest.fixture(
    params=[
        Gradient.Direction.DIAGONAL,
        Gradient.Direction.HORIZONTAL,
        Gradient.Direction.VERTICAL,
        Gradient.Direction.RADIAL,
    ],
)
def gradient_direction(request: pytest.FixtureRequest) -> Gradient.Direction:
    """Fixture to provide gradient direction for tests."""
    return request.param


@pytest.fixture(params=[True, False])
def bool_arg(request: pytest.FixtureRequest) -> bool:
    """Fixture to provide boolean arguments for tests."""
    return request.param
