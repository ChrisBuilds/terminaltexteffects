"""Controlled camera lessons: choose one changing variable and watch a fixed scene.

Each lesson is an ordinary effect, with captions drawn as 2D characters above the scene.
Save this whole file as `cameralab.py` in your community effects directory.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from terminaltexteffects import Color, ColorPair, EffectCharacter, Gradient, easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.camera import Camera
from terminaltexteffects.engine.drawing import Solid
from terminaltexteffects.engine.shapes import Cube
from terminaltexteffects.engine.tweens import rotation_about
from terminaltexteffects.engine.world import Body
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.geometry import Coord

LESSONS = (
    "travel",
    "turns",
    "orthographic",
    "dolly",
    "zoom",
    "sampled",
    "follow",
    "world-light",
    "camera-light",
    "sequence",
    "restore",
    "clip",
)


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the example's command, effect and configuration classes."""
    return "cameralab", CameraLab, CameraLabConfig


@dataclass
class CameraLabConfig(BaseConfig):
    """Choose one camera lesson; these options belong only to this guide example."""

    parser_spec = argutils.ParserSpec(
        name="cameralab",
        help="Controlled camera movement, framing, timing and lighting lessons.",
        description="cameralab | Controlled camera movement, framing, timing and lighting lessons.",
        epilog="Example: tte --canvas-width 80 --canvas-height 32 --anchor-text c cameralab --lesson travel",
    )
    lesson: str = argutils.ArgSpec(
        name="--lesson",
        default="travel",
        choices=list(LESSONS),
        help="Choose the camera operation or comparison to demonstrate.",
    )  # pyright: ignore[reportAssignmentType]
    "str : The camera lesson to play."


class CameraLabIterator(BaseEffectIterator[CameraLabConfig]):
    """Produce finite lessons and then restore the ordinary input text."""

    def __init__(self, effect: CameraLab) -> None:
        """Build the fixed scene and queue any actions that can be described in advance."""
        super().__init__(effect)
        self.inputs = self.terminal.get_characters()
        self.extras: list[EffectCharacter] = []
        self.frame_number = 0
        self.duration = 360
        self.finished = False
        self.title = ""
        self.event = ""
        self.subject: Body
        self.world = self.terminal.world
        self.world.camera.set_perspective(0 if self.config.lesson in ("orthographic", "clip") else 1)
        self.world.set_light(
            "front" if self.config.lesson.endswith("light") else "upper left",
            "camera" if self.config.lesson == "camera-light" else "world",
        )
        self.hud = [self.make_line(self.terminal.canvas.top), self.make_line(self.terminal.canvas.bottom)]
        lesson = self.config.lesson
        if lesson == "restore":
            self.setup_restore()
        elif lesson == "clip":
            self.setup_clip()
        elif lesson.endswith("light"):
            self.setup_light()
        else:
            self.setup_scene()
            if lesson in ("dolly", "zoom"):
                self.setup_lens()
            elif lesson in ("sampled", "follow"):
                self.setup_aim()
            elif lesson == "sequence":
                self.setup_sequence()

    def make_line(self, row: int) -> list[EffectCharacter]:
        """Allocate a caption row on the screen, so it stays put while the camera moves, and above the scene."""
        line = []
        for column in range(self.terminal.canvas.left + 1, self.terminal.canvas.right):
            coord = Coord(column, row)
            character = self.terminal.add_character(" ", coord)
            character.attach(self.world.screen, at=coord)
            character.layer = 10_000
            self.terminal.set_character_visibility(character, is_visible=True)
            line.append(character)
        self.extras.extend(line)
        return line

    def caption(self, line: list[EffectCharacter], text: str) -> None:
        """Write a caption without making its position depend on the camera."""
        for character, symbol in zip(line, text.ljust(len(line))):
            character.animation.set_appearance_if_changed(symbol, ColorPair(fg=Color("d9e5ef")))

    def solid(self, color: str) -> Solid:
        """Return a readable colored surface with a visible dark side."""
        return Solid(gradient=Gradient(Color("172330"), Color(color), steps=16))

    def mark(self, body: Body, symbol: str, point: tuple[float, float, float] = (0, 0, 8)) -> EffectCharacter:
        """Put one white identifying letter at a point on the body's surface, hidden while it faces away."""
        character = self.terminal.add_character(symbol, self.terminal.canvas.center)
        character.animation.set_appearance(symbol, ColorPair(fg=Color("ffffff")))
        self.terminal.set_character_visibility(character, is_visible=True)
        self.active_characters.add(character)
        # locate() turns a point in the body's axes into a surface position, between cells if need be.
        character.attach(body, at=body.surface.locate(point))
        body.hide_facing_away = True
        self.extras.append(character)
        return character

    def setup_scene(self) -> None:
        """Put cyan F's front face at z=0 and purple B's at z=-60."""
        self.subject = self.world.body(Cube(16), at=(-16, 0, -8)).draw(self.solid("26c6da"))
        background = self.world.body(Cube(16), at=(20, 0, -68)).draw(self.solid("b279e5"))
        self.mark(self.subject, "F")
        self.mark(background, "B")
        for x in (-20, 0, 20):
            self.world.body(Cube(2), at=(x, -10, -25)).draw(self.solid("8294a6"))

    def travel(self) -> None:
        """Show one local translation at a time, always starting from the same view."""
        phase, within = divmod(self.frame_number, 120)
        if within:
            return
        camera = self.world.camera.reset()
        # --8<-- [start:travel]
        if phase == 0:
            camera.dolly_by(24, frames=60, ease=easing.in_out_sine)
            self.title = "DOLLY +24: move forward; F grows faster than B"
        elif phase == 1:
            camera.truck(10, frames=60, ease=easing.in_out_sine)
            self.title = "TRUCK +10: move right; the scene slides left"
        else:
            camera.pedestal(10, frames=60, ease=easing.in_out_sine)
            self.title = "PEDESTAL +10: move up; the scene slides down"
        # --8<-- [end:travel]

    def turns(self) -> None:
        """Isolate yaw, pitch and roll without moving the eye."""
        phase, within = divmod(self.frame_number, 120)
        if within:
            return
        camera = self.world.camera.reset()
        # --8<-- [start:turns]
        if phase == 0:
            camera.pan(8, frames=60, ease=easing.in_out_sine)
            self.title = "PAN +8 deg: look left; the eye stays still"
        elif phase == 1:
            camera.tilt(8, frames=60, ease=easing.in_out_sine)
            self.title = "TILT +8 deg: look up; the eye stays still"
        else:
            camera.roll(20, frames=60, ease=easing.in_out_sine)
            self.title = "ROLL +20 deg: turn the camera; the image turns clockwise"
        # --8<-- [end:turns]

    def orthographic(self) -> None:
        """Make unchanged apparent size explicit instead of presenting an unexplained still frame."""
        phase, within = divmod(self.frame_number, 90)
        if within:
            return
        camera = self.world.camera.reset()
        if phase == 0:
            camera.dolly_by(24, frames=60)
            self.title = "ORTHOGRAPHIC DOLLY: depth changes; size stays the same"
        elif phase == 1:
            camera.zoom_to(168, frames=60)
            self.title = "ORTHOGRAPHIC ZOOM: focal changes; size stays the same"
        elif phase == 2:
            camera.truck(10, frames=60)
            self.title = "ORTHOGRAPHIC TRUCK: position still changes the image"
        else:
            camera.pan(2.5, frames=60)
            self.title = "ORTHOGRAPHIC PAN: orientation still changes the image"

    def setup_lens(self) -> None:
        """Match F's final front-face size in the two recordings, leaving B to reveal the difference."""
        self.duration = 180
        camera = self.world.camera
        camera.hold(24)
        # --8<-- [start:lens]
        if self.config.lesson == "dolly":
            camera.dolly_by(30, frames=120, ease=easing.in_out_sine)
            self.title = "DOLLY: eye 120 -> 90; focal stays 120"
        else:
            camera.zoom_to(160, frames=120, ease=easing.in_out_sine)
            self.title = "ZOOM: focal 120 -> 160; eye stays at 120"
        camera.hold(36)
        # --8<-- [end:lens]

    def setup_aim(self) -> None:
        """Keep target motion identical for the sampled and following views."""
        self.duration = 240
        self.subject.position = (-14, 0, -8)
        self.crosshair = self.terminal.add_character("+", self.terminal.canvas.center)
        self.crosshair.attach(self.world.screen, at=self.terminal.canvas.center)
        self.crosshair.layer = 10_001
        self.crosshair.animation.set_appearance("+", ColorPair(fg=Color("ffcc66")))
        self.terminal.set_character_visibility(self.crosshair, is_visible=True)
        self.extras.append(self.crosshair)
        # --8<-- [start:sampled]
        if self.config.lesson == "sampled":
            self.world.camera.look_at(self.subject, frames=60, ease=easing.in_out_sine)
            self.title = "SAMPLED AIM: one tween aims at F's starting position"
        else:
            self.title = "FOLLOW: move F, aim at F, then update"
        # --8<-- [end:sampled]

    def aim(self) -> None:
        """Move the target directly before aiming, so the tracking call sees this frame's position."""
        # --8<-- [start:follow]
        x = -14 * math.cos(2 * math.pi * self.frame_number / self.duration)
        self.subject.position = (x, 0, -8)
        if self.config.lesson == "follow":
            self.world.camera.look_at(self.subject)
        # `__next__` calls update() after these immediate changes.
        # --8<-- [end:follow]

    def setup_light(self) -> None:
        """Use the same fixed cube and orbit in both lighting modes."""
        self.duration = 240
        self.subject = self.world.body(Cube(22)).draw(self.solid("47d6cf"))
        self.mark(self.subject, "F", (0, 0, 11))
        camera = self.world.camera
        camera.set_position(0, 8, 100).look_at(self.subject)
        camera.orbit("y", turns=1, around=self.subject, frames=self.duration)
        self.title = (
            "WORLD LIGHT: +z stays fixed"
            if self.config.lesson == "world-light"
            else "CAMERA LIGHT: front follows the eye"
        )

    def pan_done(self, _camera: Camera) -> None:
        """Mark individual completion while the longer parallel truck is still playing."""
        self.event = "pan complete; truck still moving"

    def group_done(self, _camera: Camera) -> None:
        """Mark the end of the parallel group."""
        self.event = "group complete; zoom follows"

    def setup_sequence(self) -> None:
        """Run a short camera script alongside an independent body queue."""
        self.duration = 270
        self.title = "QUEUED SHOT: body and camera have independent queues"
        camera = self.world.camera
        # --8<-- [start:sequence]
        self.subject.spin("y", turns=0.25, frames=120, ease=easing.in_out_sine)
        camera.hold(24).truck(10, frames=90, ease=easing.in_out_sine)
        camera.pan(5, frames=45, ease=easing.in_out_sine, together=True).on_complete(self.pan_done)
        camera.on_group_complete(self.group_done)
        camera.hold(24).zoom_to(150, frames=60, ease=easing.in_out_sine).hold(24)
        # --8<-- [end:sequence]

    def setup_restore(self) -> None:
        """Show the input text on the text plane, which stays where it is in the world while the camera moves."""
        self.duration = 300
        self.subject = self.world.text_plane
        for character in self.inputs:
            self.terminal.set_character_visibility(character, is_visible=True)
            self.active_characters.add(character)
        self.home_position = self.world.camera.position
        self.home_rotation = self.world.camera.rotation
        self.home_focal = self.world.camera.focal or self.world.camera.distance

    def release_home(self, _camera: Camera) -> None:
        """Note when every part of the returning camera group reaches home."""
        self.title = "HOME: the whole camera group completed; the text is flat again"

    def restore(self) -> None:
        """Contrast holding a cancelled view, an immediate reset and an eased return."""
        camera = self.world.camera
        # --8<-- [start:restore]
        if self.frame_number == 0:
            self.title = "START: the text plane stays fixed in world space"
        elif self.frame_number == 30:
            camera.truck(20, frames=120)
            self.title = "TRUCK: camera moves; the text layout is unchanged"
        elif self.frame_number == 90:
            camera.cancel()
            self.title = "CANCEL: stop here and keep the current view"
        elif self.frame_number == 120:
            camera.reset()
            self.title = "RESET: jump to the initial position, aim and focal length"
        elif self.frame_number == 180:
            camera.set_position(10, 6, 100).pan(6).zoom(1.15)
            self.title = "SMOOTH RETURN: position, orientation and focal together"
            camera.move_to(
                self.home_position.x, self.home_position.y, self.home_position.z, frames=90, ease=easing.in_out_sine
            )
            camera.turn_to(self.home_rotation, frames=90, ease=easing.in_out_sine, together=True)
            camera.zoom_to(self.home_focal, frames=90, ease=easing.in_out_sine, together=True)
            camera.on_group_complete(self.release_home)
        # --8<-- [end:restore]

    def setup_clip(self) -> None:
        """Move a side-view orthographic camera to isolate near-plane clipping from magnification."""
        self.duration = 240
        self.subject = self.world.body(Cube(16)).draw(self.solid("26c6da"))
        self.subject.rotation = rotation_about("y", 25) * rotation_about("z", 20)
        self.clip_marker = self.mark(self.subject, "A", (8, 0, 0))
        # --8<-- [start:clip]
        camera = self.world.camera
        camera.set_position(22, 0, 0).look_at(self.subject)
        camera.near = 3
        camera.hold(24).dolly_by(14, frames=150, ease=easing.in_out_sine).hold(66)
        # --8<-- [end:clip]
        self.title = "NEAR PLANE: camera looks along world -x; cube stays still"

    def finish(self) -> None:
        """Remove the teaching scene, put the camera back and leave only the original input."""
        for body in self.world.bodies:
            self.world.remove(body)
        self.world.camera.cancel().reset()
        for character in self.extras:
            self.terminal.set_character_visibility(character, is_visible=False)
        for character in self.inputs:
            character.attach(self.world.text_plane, at=character.input_coord)
            self.terminal.set_character_visibility(character, is_visible=True)
        self.finished = True

    def __next__(self) -> str:
        """Change the lesson's one variable, play one frame with update(), then caption what it shows."""
        if self.frame_number >= self.duration:
            if self.finished:
                raise StopIteration
            self.finish()
            self.update()
            return self.frame
        lesson = self.config.lesson
        if lesson == "travel":
            self.travel()
        elif lesson == "turns":
            self.turns()
        elif lesson == "orthographic":
            self.orthographic()
        elif lesson in ("sampled", "follow"):
            self.aim()
        elif lesson == "restore":
            self.restore()
        self.update()
        # Captions are written after update(), so they describe the frame the camera has just stepped to.
        self.caption(self.hud[0], self.title)
        camera = self.world.camera
        position = camera.position
        detail = (
            f"eye ({position.x:5.1f},{position.y:5.1f},{position.z:5.1f})  focal {camera.focal or camera.distance:5.1f}"
        )
        if lesson == "sequence":
            detail = (
                f"camera {'playing' if camera.animating else 'idle'} | "
                f"body {'playing' if self.subject.animating else 'idle'} | {self.event}"
            )
        elif lesson == "clip":
            detail = f"near 3 | A projected: {self.clip_marker.view.projected} | eye x {position.x:4.1f}"
        self.caption(self.hud[1], detail)
        self.frame_number += 1
        return self.frame


class CameraLab(BaseEffect[CameraLabConfig]):
    """Controlled lessons for camera position, aim, projection and timing."""

    @property
    def _config_cls(self) -> type[CameraLabConfig]:
        return CameraLabConfig

    @property
    def _iterator_cls(self) -> type[CameraLabIterator]:
        return CameraLabIterator
