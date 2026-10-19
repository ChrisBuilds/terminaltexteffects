"""Check the visual claims made by the camera lessons, beyond merely reaching their last frame."""

from __future__ import annotations

import importlib.util
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast

import pytest

from terminaltexteffects.utils.geometry3d import Vec3

if TYPE_CHECKING:
    from collections.abc import Iterator
    from types import ModuleType

    from terminaltexteffects.engine.space3d import Space3D


class GuideIterator(Protocol):
    """The public scene exposed by each standalone camera guide iterator."""

    space: Space3D

    def __next__(self) -> str:
        """Produce one recorded frame."""
        ...

    def __iter__(self) -> Iterator[str]:
        """Iterate the effect to its final input-text frame."""
        ...


@pytest.fixture(scope="module")
def camera_modules() -> Iterator[dict[str, ModuleType]]:
    """Load standalone guide files with real module identities for their dataclasses."""
    root = Path(__file__).resolve().parents[1] / "docs" / "effectguide" / "examples" / "3d"
    modules = {}
    for name in ("cameralab", "cameraorbit"):
        alias = f"_guide_test_{name}"
        spec = importlib.util.spec_from_file_location(alias, root / name / f"{name}.py")
        assert spec is not None
        assert isinstance(spec.loader, SourceFileLoader)
        module = importlib.util.module_from_spec(spec)
        sys.modules[alias] = module
        spec.loader.exec_module(module)
        modules[name] = module
    yield modules
    for module in modules.values():
        sys.modules.pop(module.__name__)


def make_iterator(camera_modules: dict[str, ModuleType], lesson: str) -> GuideIterator:
    """Use the same input, canvas and anchor as the committed recordings."""
    name = "cameraorbit" if lesson == "orbit" else "cameralab"
    effect_class = camera_modules[name].get_effect_resources()[1]
    text = (Path(__file__).resolve().parents[1] / "docs/effectguide/examples/concept_input.txt").read_text()
    effect = effect_class(text)
    effect.terminal_config.frame_rate = 0
    effect.terminal_config.canvas_width, effect.terminal_config.canvas_height = 80, 32
    effect.terminal_config.anchor_text = "c"
    if lesson != "orbit":
        effect.effect_config.lesson = lesson
    return cast("GuideIterator", iter(effect))


@pytest.mark.parametrize("lesson", ["orbit", "travel", "turns", "orthographic", "sequence"])
def test_camera_lessons_keep_the_scene_in_frame(camera_modules: dict[str, ModuleType], lesson: str) -> None:
    """Unintended viewport crops cannot masquerade as camera perspective or near-plane behavior."""
    iterator = make_iterator(camera_modules, lesson)
    for _ in iterator:
        camera = iterator.space.camera
        for body in iterator.space.bodies:
            if body.mesh is None:
                continue
            for vertex in body.mesh.vertices:
                projected = camera.project(body.world_point(vertex))
                assert projected is not None
                assert 0.5 <= projected.column <= 80.5
                assert 0.5 <= projected.row <= 31.5  # The top row is reserved for the caption.


def test_dolly_and_zoom_match_foreground_framing(camera_modules: dict[str, ModuleType]) -> None:
    """The comparison matches F's end size, with B revealing the different perspective ratios."""
    widths = {}
    for lesson in ("dolly", "zoom"):
        iterator = make_iterator(camera_modules, lesson)
        final_widths = []
        for _ in iterator:
            if not iterator.space.bodies:
                break
            final_widths = []
            for body in iterator.space.bodies[:2]:
                # Both 16-column cubes have their front faces at local z=8.
                left = iterator.space.camera.project(body.world_point(Vec3(-8, 0, 8)))
                right = iterator.space.camera.project(body.world_point(Vec3(8, 0, 8)))
                assert left is not None
                assert right is not None
                final_widths.append(right.column - left.column)
        widths[lesson] = final_widths
    assert widths["dolly"][0] == pytest.approx(widths["zoom"][0])
    assert widths["dolly"][1] < widths["zoom"][1]


def test_sampled_aim_and_explicit_tracking_are_visibly_different(camera_modules: dict[str, ModuleType]) -> None:
    """Tracking centers this frame's target; the sampled shot lets it move away from the center."""
    errors = {}
    for lesson in ("sampled", "follow"):
        iterator = make_iterator(camera_modules, lesson)
        errors[lesson] = []
        for _ in iterator:
            if not iterator.space.bodies:
                break
            camera = iterator.space.camera
            projected = camera.project(iterator.space.bodies[0].position)
            assert projected is not None
            errors[lesson].append(abs(projected.column - camera.center_column))
    assert max(errors["follow"]) < 1e-8
    assert max(errors["sampled"]) > 20


def test_clip_lesson_hides_anchor_without_moving_the_body(camera_modules: dict[str, ModuleType]) -> None:
    """The disappearing marker is caused by the moving near plane, not by body motion."""
    iterator = make_iterator(camera_modules, "clip")
    body = iterator.space.bodies[0]
    start = (body.position, body.rotation)
    projected_states = set()
    for _ in iterator:
        if not iterator.space.bodies:
            break
        assert (body.position, body.rotation) == start
        projected_states.update(mount.projected for mount in iterator.space.mounts.values())
    assert projected_states == {False, True}


def test_restore_lesson_releases_text_at_the_home_view(camera_modules: dict[str, ModuleType]) -> None:
    """The return shot releases before cleanup, only once the camera and text are back home."""
    iterator = make_iterator(camera_modules, "restore")
    home = iterator.space.camera.position
    released = False
    for _ in iterator:
        if iterator.space.bodies and not iterator.space.mounts:
            camera = iterator.space.camera
            assert camera.position.x == pytest.approx(home.x)
            assert camera.position.y == pytest.approx(home.y)
            assert camera.position.z == pytest.approx(home.z)
            assert camera.rotation.matrix() == pytest.approx((1, 0, 0, 0, 1, 0, 0, 0, 1))
            for character in iterator.space.terminal.get_characters():
                assert character.motion.current_coord == character.input_coord
            released = True
    assert released
