"""The world's camera: projection onto the canvas, plus controls that move it now or over frames.

    camera = terminal.world.camera
    camera.set_perspective(1.5)                 # exaggerate depth
    camera.orbit("y", 90, around=cube, frames=120)
    camera.look_at(character)                   # every frame, to follow it

Distances are in units (one unit is a cell's width), angles in degrees, and turns are about the camera's own axes.

Classes:
    Camera: The world's camera.
"""

from __future__ import annotations

import math
import typing

from terminaltexteffects.engine.tweens import AXES, Axis, Tween, TweenQueue, direction
from terminaltexteffects.utils import geometry3d as g3

if typing.TYPE_CHECKING:
    from collections.abc import Callable

    from terminaltexteffects.engine.world import SpatialNode
    from terminaltexteffects.utils.easing import EasingFunction

__all__ = ["Camera"]

_EPSILON = 1e-9


class Camera(g3.Camera, TweenQueue):
    """The world's camera: where the eye is, how it projects, and controls that move it now or over frames.

    Every world has one, `terminal.world.camera`, centered on the canvas. Identity orientation looks along local -z;
    +x is right and +y is up. Pan, tilt and roll use degrees about the camera's local +y, +x and +z axes. Positive
    dolly moves forward, truck right and pedestal up. Methods return the camera, so calls chain.

    `look_at` and `orbit` apply now unless `frames` is given. A target is a point or any node, a body or a
    character, sampled when the tween begins; call `look_at(node)` every frame to follow a moving node. Queued
    movements apply deltas, so changes made now compose with them. `zoom_to` takes an absolute focal length. The
    world plays queued movements inside `update()`, before nodes move.
    """

    def __post_init__(self) -> None:
        """Validate settings and remember the initial view for `reset`."""
        super().__post_init__()
        self._home = (
            self.center_column,
            self.center_row,
            self.distance,
            self.focal,
            self.orthographic,
            self.near,
            self.row_scale,
        )
        self._init_queue()

    def set_perspective(self, strength: float = 1.0) -> Camera:
        """Set how strongly depth shrinks things, now: 1 is natural, larger exaggerates depth, 0 is orthographic.

        The eye's reference distance becomes `120 / strength` (120 when orthographic) and focal length follows it, so
        the z = 0 plane keeps its size at any strength. An explicitly positioned eye stays where it is. `reset`
        keeps the perspective set here.

        Args:
            strength (float): Perspective strength; 0 or more, and less than 120 divided by `near`.

        Returns:
            Camera: This camera, for chaining.

        Raises:
            ValueError: If `strength` is negative or puts the eye at or inside the near plane.

        """
        super().set_perspective(strength)
        center_column, center_row, _, _, _, near, row_scale = self._home
        self._home = (center_column, center_row, self.distance, self.focal, self.orthographic, near, row_scale)
        return self

    def set_position(self, x: float | g3.Point3 = 0, y: float | None = None, z: float | None = None) -> Camera:
        """Set the eye's world position, now, without changing distance or focal length.

        Do not combine a complete point with y or z; mixed forms raise `TypeError`.

        Args:
            x (float | g3.Point3): Absolute world position as a `Vec3` or `(x, y, z)` tuple in units, or scalar x.
            y (float | None): Scalar y in units; omit for a complete point. Omitted/`None` means zero.
            z (float | None): Scalar z in units; omit for a complete point. Omitted/`None` means zero.

        Returns:
            Camera: This camera, for chaining.

        Raises:
            TypeError: If a point is not a `Vec3` or a numeric `(x, y, z)` tuple. Coordinates cannot be mixed with a
                complete point.

        """
        super().set_position(x, y, z)
        return self

    def set_rotation(self, rotation: g3.Rotation | None = None) -> Camera:
        """Set the world orientation, now; `None` restores the -z view direction.

        Args:
            rotation (g3.Rotation | None): Target world orientation; `None`, when accepted, restores the
                default orientation.

        Returns:
            Camera: This camera, for chaining.

        """
        super().set_rotation(rotation)
        return self

    def move_by(self, x: float | g3.Point3 = 0, y: float | None = None, z: float | None = None) -> Camera:
        """Move by world displacement `(x, y, z)`, now.

        Do not combine a complete point with y or z; mixed forms raise `TypeError`.

        Args:
            x (float | g3.Point3): World displacement as a `Vec3` or `(x, y, z)` tuple in units, or scalar x.
            y (float | None): Scalar y in units; omit for a complete point. Omitted/`None` means zero.
            z (float | None): Scalar z in units; omit for a complete point. Omitted/`None` means zero.

        Returns:
            Camera: This camera, for chaining.

        Raises:
            TypeError: If a point is not a `Vec3` or a numeric `(x, y, z)` tuple. Coordinates cannot be mixed with a
                complete point.

        """
        point = self.position + g3._coordinates(x, y, z)
        return self.set_position(point.x, point.y, point.z)

    def _travel(self, axis: g3.Vec3, amount: float) -> Camera:
        point = self.rotation.apply(axis) * amount
        return self.move_by(point.x, point.y, point.z)

    def dolly(self, amount: float) -> Camera:
        """Move forward `amount` columns, now; negative amounts move backward.

        Args:
            amount (float): Signed travel in units along the named camera-local direction.

        Returns:
            Camera: This camera, for chaining.

        """
        return self._travel(-g3.Z_AXIS, amount)

    def truck(
        self, amount: float, *, frames: int | None = None, ease: EasingFunction | None = None, together: bool = False
    ) -> Camera:
        """Move right `amount` columns, now or over `frames`, along the starting local axis.

        Args:
            amount (float): Signed travel in units along the named camera-local direction.
            frames (int | None): `None` applies now; otherwise queue this many frames. Zero preserves queue ordering.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Play alongside the last queued group instead of after it.

        Returns:
            Camera: This camera, for chaining.

        Raises:
            ValueError: If `frames` is negative.

        """
        return (
            self._travel(g3.X_AXIS, amount)
            if frames is None
            else self._travel_by(g3.X_AXIS, amount, frames, ease, together=together)
        )

    def pedestal(
        self, amount: float, *, frames: int | None = None, ease: EasingFunction | None = None, together: bool = False
    ) -> Camera:
        """Move up `amount` columns, now or over `frames`, along the starting local axis.

        Args:
            amount (float): Signed travel in units along the named camera-local direction.
            frames (int | None): `None` applies now; otherwise queue this many frames. Zero preserves queue ordering.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Play alongside the last queued group instead of after it.

        Returns:
            Camera: This camera, for chaining.

        Raises:
            ValueError: If `frames` is negative.

        """
        return (
            self._travel(g3.Y_AXIS, amount)
            if frames is None
            else self._travel_by(g3.Y_AXIS, amount, frames, ease, together=together)
        )

    def _turn(
        self, axis: Axis, degrees: float, frames: int | None, ease: EasingFunction | None, *, together: bool
    ) -> Camera:
        unit = direction(axis, AXES, "axis")
        angle = math.radians(degrees)
        if frames is None:
            return self.set_rotation(self.rotation * g3.Rotation.about_axis(unit, angle))

        def apply(previous: float, current: float) -> None:
            self.set_rotation(self.rotation * g3.Rotation.about_axis(unit, angle * (current - previous)))

        return self._queue_tween(Tween(frames, apply, ease), together=together)

    def pan(
        self, degrees: float, *, frames: int | None = None, ease: EasingFunction | None = None, together: bool = False
    ) -> Camera:
        """Yaw about local +y, now or over `frames`; positive angles turn the view left.

        Args:
            degrees (float): Signed angle in degrees.
            frames (int | None): `None` applies now; otherwise queue this many frames. Zero preserves queue ordering.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Play alongside the last queued group instead of after it.

        Returns:
            Camera: This camera, for chaining.

        Raises:
            ValueError: If `frames` is negative.

        """
        return self._turn("y", degrees, frames, ease, together=together)

    def tilt(
        self, degrees: float, *, frames: int | None = None, ease: EasingFunction | None = None, together: bool = False
    ) -> Camera:
        """Pitch about local +x, now or over `frames`; positive angles look upward.

        Args:
            degrees (float): Signed angle in degrees.
            frames (int | None): `None` applies now; otherwise queue this many frames. Zero preserves queue ordering.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Play alongside the last queued group instead of after it.

        Returns:
            Camera: This camera, for chaining.

        Raises:
            ValueError: If `frames` is negative.

        """
        return self._turn("x", degrees, frames, ease, together=together)

    def roll(
        self, degrees: float, *, frames: int | None = None, ease: EasingFunction | None = None, together: bool = False
    ) -> Camera:
        """Turn about local +z, now or over `frames`; positive angles rotate the camera counterclockwise.

        Args:
            degrees (float): Signed angle in degrees.
            frames (int | None): `None` applies now; otherwise queue this many frames. Zero preserves queue ordering.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Play alongside the last queued group instead of after it.

        Returns:
            Camera: This camera, for chaining.

        Raises:
            ValueError: If `frames` is negative.

        """
        return self._turn("z", degrees, frames, ease, together=together)

    def zoom(self, factor: float) -> Camera:
        """Multiply focal length by positive `factor`, now; orthographic size is unaffected.

        Args:
            factor (float): Positive multiplier of the current focal length.

        Returns:
            Camera: This camera, for chaining.

        Raises:
            ValueError: If `factor` is not positive.

        """
        if factor <= 0:
            msg = "A zoom factor must be positive."
            raise ValueError(msg)
        self.focal = (self.focal or self.distance) * factor
        return self

    @staticmethod
    def _point(target: SpatialNode | g3.Vec3 | tuple[float, float, float]) -> g3.Vec3:
        if isinstance(target, (g3.Vec3, tuple)):
            return g3._vec3(target)
        return target.world_position

    def _aim(self, point: g3.Vec3, up: g3.Vec3, *, eye: g3.Vec3 | None = None) -> g3.Rotation:
        """Build an orthonormal camera basis, with a stable fallback when up follows the view."""
        back = ((self.position if eye is None else eye) - point).normalized()
        right = up.cross(back)
        if right.length() < _EPSILON:
            previous = self.rotation.apply(g3.X_AXIS)
            right = previous - back * previous.dot(back)
            if right.length() < _EPSILON:
                fallback = g3.Y_AXIS if abs(back.y) < 0.9 else g3.Z_AXIS
                right = fallback.cross(back)
        right = right.normalized()
        vertical = back.cross(right)
        # Convert the basis columns to a quaternion, choosing the largest stable component.
        m = (right.x, vertical.x, back.x, right.y, vertical.y, back.y, right.z, vertical.z, back.z)
        trace = m[0] + m[4] + m[8]
        if trace > 0:
            size = math.sqrt(trace + 1) * 2
            return g3.Rotation(size / 4, (m[7] - m[5]) / size, (m[2] - m[6]) / size, (m[3] - m[1]) / size)
        index = max(range(3), key=lambda i: m[4 * i])
        i, j, k = index, (index + 1) % 3, (index + 2) % 3
        size = math.sqrt(1 + m[3 * i + i] - m[3 * j + j] - m[3 * k + k]) * 2
        parts = [0.0, 0.0, 0.0]
        parts[i] = size / 4
        parts[j] = (m[3 * j + i] + m[3 * i + j]) / size
        parts[k] = (m[3 * k + i] + m[3 * i + k]) / size
        return g3.Rotation((m[3 * k + j] - m[3 * j + k]) / size, *parts)

    def look_at(
        self,
        x: float | SpatialNode | g3.Vec3 | tuple[float, float, float],
        y: float | None = None,
        z: float | None = None,
        *,
        up: Axis = "y",
        frames: int | None = None,
        ease: EasingFunction | None = None,
        together: bool = False,
    ) -> Camera:
        """Aim at world `(x, y, z)` or a node, now or over `frames` along the shortest turn.

        `up` is a nonzero world direction. At a pole, the previous right axis supplies the roll.
        Raises `ValueError` if the target is at the eye, up is zero, or frames is negative.

        Args:
            x (float | SpatialNode | g3.Vec3 | tuple[float, float, float]): Target world x, a `Vec3`, an `(x,
                y, z)` tuple in units or a node to aim at.
            y (float | None): World y in units when x is numeric; omitted/`None` means zero. Omit for a target.
            z (float | None): World z in units when x is numeric; omitted/`None` means zero. Omit for a target.
            up (Axis): Nonzero world `(x, y, z)` up direction (unitless) or axis name; defaults to +y.
            frames (int | None): `None` applies now; otherwise queue this many frames. Zero preserves queue ordering.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Play alongside the last queued group instead of after it.

        Returns:
            Camera: This camera, for chaining.

        Raises:
            TypeError: If a point is malformed, or y/z is combined with a point or node target.
            ValueError: If frames is negative, up is unknown or zero, or the target is at the eye
                when aiming begins.

        """
        if not isinstance(x, (int, float, g3.Vec3, tuple)):
            if y is not None or z is not None:
                msg = "A node target cannot be combined with y or z arguments."
                raise TypeError(msg)
            target: SpatialNode | g3.Vec3 = x
        else:
            target = g3._coordinates(x, y, z)
        vertical = direction(up, AXES, "up")
        if frames is None:
            return self.set_rotation(self._aim(self._point(target), vertical))
        return self._turn_to(lambda: self._aim(self._point(target), vertical), frames, ease, together=together)

    def orbit(
        self,
        axis: Axis = "y",
        degrees: float | None = None,
        *,
        around: SpatialNode | g3.Vec3 | tuple[float, float, float] = g3.ORIGIN,
        turns: float | None = None,
        up: Axis = "y",
        frames: int | None = None,
        ease: EasingFunction | None = None,
        together: bool = False,
    ) -> Camera:
        """Turn the eye around a world axis through `around`, keeping it aimed there.

        Supply `degrees` or `turns` (default one turn), and `frames` to queue it. The target
        is sampled at the start. Without concurrent edits, the radius stays constant.
        `up` sets the aiming roll; at poles the previous right axis supplies it.
        Raises `ValueError` for both angle forms, invalid directions, negative frames or zero radius.

        Args:
            axis (Axis): World axis name or nonzero `(x, y, z)` direction components (unitless).
            degrees (float | None): Signed angle in degrees.
            around (SpatialNode | g3.Vec3 | tuple[float, float, float]): World `(x, y, z)` point in units, or a node
                whose position is sampled when the orbit starts.
            turns (float | None): Signed full turns, as an alternative to degrees. Defaults to one turn
                if neither is supplied.
            up (Axis): Nonzero world `(x, y, z)` up direction (unitless) or axis name; defaults to +y.
            frames (int | None): `None` applies now; otherwise queue this many frames. Zero preserves queue ordering.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Play alongside the last queued group instead of after it.

        Returns:
            Camera: This camera, for chaining.

        Raises:
            ValueError: If both angle forms are supplied, an axis or up direction is invalid, frames is negative,
                or the sampled target is at the eye when the action begins.

        """
        if degrees is not None and turns is not None:
            msg = "Supply degrees or turns, not both."
            raise ValueError(msg)
        angle = math.radians(degrees if degrees is not None else 360 * (turns if turns is not None else 1))
        unit = direction(axis, AXES, "axis")
        vertical = direction(up, AXES, "up")
        if frames is None:
            center = self._point(around)
            point = center + g3.Rotation.about_axis(unit, angle).apply(self.position - center)
            if (point - center).length() < _EPSILON:
                msg = "An orbit needs a nonzero radius."
                raise ValueError(msg)
            self.set_position(point.x, point.y, point.z)
            return self.set_rotation(self._aim(center, vertical))
        points: dict[str, g3.Vec3] = {}
        rotations: dict[str, g3.Rotation] = {}

        def begin() -> None:
            center = points["center"] = self._point(around)
            points["offset"] = self.position - center
            points["last"] = self.position
            if points["offset"].length() < _EPSILON:
                msg = "An orbit needs a nonzero radius."
                raise ValueError(msg)
            rotations["last"] = self.rotation

        def apply(_previous: float, current: float) -> None:
            point = points["center"] + g3.Rotation.about_axis(unit, angle * current).apply(points["offset"])
            delta = point - points["last"]
            self.move_by(delta.x, delta.y, delta.z)
            aimed = self._aim(points["center"], vertical, eye=point)
            pose = aimed
            self.set_rotation(pose * rotations["last"].inverse() * self.rotation)
            points["last"], rotations["last"] = point, pose

        return self._queue_tween(Tween(frames, apply, ease, begin), together=together)

    def move_to(
        self,
        x: float | g3.Point3 = 0,
        y: float | None = None,
        z: float | None = None,
        frames: int = 60,
        ease: EasingFunction | None = None,
        *,
        together: bool = False,
    ) -> Camera:
        """Queue an absolute world position, applying deltas that preserve concurrent nudges.

        Do not combine a complete point with y or z; mixed forms raise `TypeError`.

        Args:
            x (float | g3.Point3): Absolute world position as a `Vec3` or `(x, y, z)` tuple in units, or scalar x.
            y (float | None): Scalar y in units; omit for a complete point. Omitted/`None` means zero.
            z (float | None): Scalar z in units; omit for a complete point. Omitted/`None` means zero.
            frames (int): Duration in frames. Zero applies immediately only when no earlier tween is queued.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Play alongside the last queued group instead of after it.

        Returns:
            Camera: This camera, for chaining.

        Raises:
            TypeError: If a point is not a `Vec3` or a numeric `(x, y, z)` tuple. Coordinates cannot be mixed with a
                complete point.
            ValueError: If `frames` is negative.

        """
        target = g3._coordinates(x, y, z)
        state: dict[str, g3.Vec3] = {}

        def begin() -> None:
            state["start"] = state["last"] = self.position

        def apply(_previous: float, current: float) -> None:
            point = state["start"].lerp(target, current)
            delta = point - state["last"]
            self.move_by(delta.x, delta.y, delta.z)
            state["last"] = point

        return self._queue_tween(Tween(frames, apply, ease, begin), together=together)

    def _travel_by(
        self, axis: g3.Vec3, amount: float, frames: int, ease: EasingFunction | None, *, together: bool
    ) -> Camera:
        state: dict[str, g3.Vec3] = {}

        def begin() -> None:
            state["delta"] = self.rotation.apply(axis) * amount

        def apply(previous: float, current: float) -> None:
            delta = state["delta"] * (current - previous)
            self.move_by(delta.x, delta.y, delta.z)

        return self._queue_tween(Tween(frames, apply, ease, begin), together=together)

    def dolly_by(
        self, amount: float, frames: int = 60, ease: EasingFunction | None = None, *, together: bool = False
    ) -> Camera:
        """Queue relative forward travel; capture the forward axis when the tween begins.

        Args:
            amount (float): Signed travel in units along the named camera-local direction.
            frames (int): Duration in frames. Zero applies immediately only when no earlier tween is queued.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Play alongside the last queued group instead of after it.

        Returns:
            Camera: This camera, for chaining.

        Raises:
            ValueError: If `frames` is negative.

        """
        return self._travel_by(-g3.Z_AXIS, amount, frames, ease, together=together)

    def _turn_to(
        self, target: Callable[[], g3.Rotation], frames: int, ease: EasingFunction | None, *, together: bool
    ) -> Camera:
        state: dict[str, g3.Rotation] = {}

        def begin() -> None:
            state["start"] = state["last"] = self.rotation
            state["target"] = target()

        def apply(_previous: float, current: float) -> None:
            pose = state["start"].slerp(state["target"], current)
            self.set_rotation(pose * state["last"].inverse() * self.rotation)
            state["last"] = pose

        return self._queue_tween(Tween(frames, apply, ease, begin), together=together)

    def turn_to(
        self, rotation: g3.Rotation, frames: int = 60, ease: EasingFunction | None = None, *, together: bool = False
    ) -> Camera:
        """Queue the shortest turn to a world orientation, preserving concurrent rotation deltas.

        Args:
            rotation (g3.Rotation): Target world orientation as a `Rotation`.
            frames (int): Duration in frames. Zero applies immediately only when no earlier tween is queued.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Play alongside the last queued group instead of after it.

        Returns:
            Camera: This camera, for chaining.

        Raises:
            ValueError: If `frames` is negative.

        """
        return self._turn_to(rotation.normalized, frames, ease, together=together)

    def zoom_to(
        self, focal: float, frames: int = 60, ease: EasingFunction | None = None, *, together: bool = False
    ) -> Camera:
        """Queue a positive absolute focal length, composing multiplicatively with immediate zooms.

        Args:
            focal (float): Positive target focal length in units.
            frames (int): Duration in frames. Zero applies immediately only when no earlier tween is queued.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Play alongside the last queued group instead of after it.

        Returns:
            Camera: This camera, for chaining.

        Raises:
            ValueError: If `focal` is not positive or `frames` is negative.

        """
        if focal <= 0:
            msg = "Camera focal length must be positive."
            raise ValueError(msg)
        state: dict[str, float] = {}

        def begin() -> None:
            state["start"] = state["last"] = self.focal or self.distance

        def apply(_previous: float, current: float) -> None:
            value = max(state["start"] + (focal - state["start"]) * current, _EPSILON)
            self.zoom(value / state["last"])
            state["last"] = value

        return self._queue_tween(Tween(frames, apply, ease, begin), together=together)

    def reset(self) -> Camera:
        """Cancel animations and restore the settings and pose the world created the camera with.

        The perspective stays as `set_perspective` last set it.

        Returns:
            Camera: This camera, for chaining.

        """
        self.cancel()
        (
            self.center_column,
            self.center_row,
            self.distance,
            self.focal,
            self.orthographic,
            self.near,
            self.row_scale,
        ) = self._home
        self._position = None
        return self.set_rotation()
