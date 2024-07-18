from __future__ import annotations

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
    effect_synthgrid,
    effect_unstable,
    effect_vhstape,
    effect_waves,
    effect_wipe,
)
from terminaltexteffects.engine.base_effect import BaseEffect
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.graphics import Color

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

TEST_INPUTS = {
    "empty": INPUT_EMPTY,
    "single_char": INPUT_SINGLE_CHAR,
    "single_column": INPUT_SINGLE_COLUMN,
    "single_row": INPUT_SINGLE_ROW,
    "medium": INPUT_MEDIUM,
    "tabs": INPUT_TABS,
    "large": INPUT_LARGE,
    "canvas": CANVAS_TEST_INPUT,
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
    effect_synthgrid.SynthGrid,
    effect_unstable.Unstable,
    effect_vhstape.VHSTape,
    effect_waves.Waves,
    effect_wipe.Wipe,
]

ANCHORS = ["sw", "s", "se", "e", "ne", "n", "nw", "w", "c"]


@pytest.fixture(params=EFFECTS)
def effect(request: pytest.FixtureRequest) -> BaseEffect:
    return request.param


@pytest.fixture(params=[True, False])
def no_color(request: pytest.FixtureRequest) -> bool:
    return request.param


@pytest.fixture(params=[True, False])
def xterm_colors(request: pytest.FixtureRequest) -> bool:
    return request.param


@pytest.fixture(params=ANCHORS)
def canvas_anchor(request: pytest.FixtureRequest) -> str:
    return request.param


@pytest.fixture(params=ANCHORS)
def text_anchor(request: pytest.FixtureRequest) -> str:
    return request.param


@pytest.fixture(params=[(60, 30), (25, 8)], ids=["60x30", "25x8"])
def canvas_dimensions(request: pytest.FixtureRequest) -> tuple[int, int]:
    return request.param


@pytest.fixture()
def terminal_config_with_color_options(xterm_colors, no_color) -> TerminalConfig:
    terminal_config = TerminalConfig()
    terminal_config.xterm_colors = xterm_colors
    terminal_config.no_color = no_color
    terminal_config.frame_rate = 0
    return terminal_config


@pytest.fixture()
def terminal_config_default() -> TerminalConfig:
    terminal_config = TerminalConfig()
    terminal_config.frame_rate = 0
    return terminal_config


@pytest.fixture()
def terminal_config_with_anchoring(canvas_dimensions, canvas_anchor, text_anchor) -> TerminalConfig:
    terminal_config = TerminalConfig()
    terminal_config.frame_rate = 0
    terminal_config.canvas_width = canvas_dimensions[0]
    terminal_config.canvas_height = canvas_dimensions[1]
    terminal_config.anchor_canvas = canvas_anchor
    terminal_config.anchor_text = text_anchor
    return terminal_config


@pytest.fixture()
def input_data(request: pytest.FixtureRequest) -> str:
    return TEST_INPUTS[request.param]


@pytest.fixture(params=[(Color("000000"), Color("ff00ff"), Color("0ffff0")), Color("ff0fff")])
def gradient_stops(request: pytest.FixtureRequest) -> Color | tuple[Color, ...]:
    return request.param


@pytest.fixture(params=[1, 5, 10, (1, 3)])
def gradient_steps(request: pytest.FixtureRequest) -> int | tuple[int, ...]:
    return request.param


@pytest.fixture(params=[1, 5])
def gradient_frames(request: pytest.FixtureRequest) -> int:
    return request.param


@pytest.fixture(params=[True, False])
def bool_arg(request: pytest.FixtureRequest) -> bool:
    return request.param
