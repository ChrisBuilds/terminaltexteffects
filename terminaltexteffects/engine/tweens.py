"""Queued animations for bodies and the camera, played one frame at a time by the world.

A tween applies its change as a delta each frame, so tweens compose with immediate changes and with each other: a
spin keeps turning a body the effect is also nudging. Tweens queue one after another, or play alongside the last
group with `together=True`. A tween with `frames=0` applies at once if nothing is queued ahead of it.

Functions:
    rotation_about: Returns a rotation of some degrees about a named axis or direction.
"""

from __future__ import annotations

import math
import typing
from dataclasses import dataclass, field

from terminaltexteffects.utils import geometry3d as g3

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from terminaltexteffects.utils.easing import EasingFunction

__all__ = ["Axis", "rotation_about"]

Axis = typing.Union[str, tuple[float, float, float], g3.Vec3]
"""An axis name (`"x"`, `"y"`, `"z"`, `"diagonal"`) or an `(x, y, z)` direction."""

AXES: Mapping[str, g3.Vec3] = {
    "x": g3.X_AXIS,
    "y": g3.Y_AXIS,
    "z": g3.Z_AXIS,
    "diagonal": g3.Vec3(1.0, 1.0, 1.0).normalized(),
}

_EPSILON = 1e-9


def direction(value: Axis, names: Mapping[str, g3.Vec3], kind: str) -> g3.Vec3:
    """Return `value` as a unit vector, looking names up in `names`.

    Raises:
        ValueError: If `value` is an unknown name or a zero vector.

    """
    if isinstance(value, str):
        if value not in names:
            msg = f"Unknown {kind} {value!r}. Use one of {', '.join(repr(name) for name in names)} or (x, y, z)."
            raise ValueError(msg)
        return names[value].normalized()
    vector = value if isinstance(value, g3.Vec3) else g3.Vec3(*value)
    try:
        return vector.normalized()
    except ValueError:
        msg = f"A {kind} direction must not be (0, 0, 0)."
        raise ValueError(msg) from None


def rotation_about(axis: Axis, degrees: float) -> g3.Rotation:
    """Return a rotation of `degrees` about `axis`, counterclockwise when looking down the axis toward the origin.

    Args:
        axis (Axis): `"x"`, `"y"`, `"z"`, `"diagonal"` or unitless `(x, y, z)` direction components.
        degrees (float): Angle of the rotation.

    Returns:
        g3.Rotation: The rotation.

    Raises:
        ValueError: If `axis` is an unknown name or a zero vector.

    """
    return g3.Rotation.about_axis(direction(axis, AXES, "axis"), math.radians(degrees))


_Owner = typing.TypeVar("_Owner")


@dataclass
class Tween(typing.Generic[_Owner]):
    """One queued animation. `apply` receives the previous and current eased progress.

    A tween with `follow` takes its progress from it instead of counting frames: `follow()` returns the fraction
    played so far, or `None` once the tween should end, and its first call happens after `begin`.
    """

    frames: int
    apply: Callable[[float, float], None]
    ease: EasingFunction | None = None
    begin: Callable[[], None] | None = None
    callbacks: list[Callable[[_Owner], None]] = field(default_factory=list)
    follow: Callable[[], float | None] | None = None
    frame: int = 0
    progress: float = 0.0
    started: bool = False

    @property
    def done(self) -> bool:
        return self.started and self.frame >= self.frames

    def start(self) -> None:
        if not self.started:
            self.started = True
            if self.begin is not None:
                self.begin()

    def advance(self) -> None:
        """Play one frame, or the whole tween when it has no frames."""
        self.start()
        if self.follow is not None:
            followed = self.follow()
            if followed is None:
                fraction = 1.0
                self.frame = self.frames
            else:
                fraction = followed
        elif self.frames == 0:
            self.apply(0.0, 1.0)
            return
        else:
            self.frame += 1
            fraction = self.frame / self.frames
        eased = self.ease(fraction) if self.ease is not None else fraction
        self.apply(self.progress, eased)
        self.progress = eased


@dataclass
class _Group(typing.Generic[_Owner]):
    """Tweens played together, and callbacks owned by their shared lifetime."""

    tweens: list[Tween[_Owner]]
    callbacks: list[Callable[[_Owner], None]] = field(default_factory=list)
    follows: bool = False


_Queue = typing.TypeVar("_Queue", bound="TweenQueue")


class TweenQueue:
    """The queue of tweens a body or the camera plays, one frame per world step."""

    def _init_queue(self) -> None:
        self._queue: list[_Group[typing.Any]] = []
        self._callback_generation = 0

    @property
    def animating(self) -> bool:
        """Whether tweens are queued or playing."""
        return bool(self._queue)

    def hold(self: _Queue, frames: int) -> _Queue:
        """Queue a pause of `frames` frames.

        Args:
            frames (int): Number of frames to pause; must not be negative.

        Returns:
            TweenQueue: This object, for chaining.

        Raises:
            ValueError: If `frames` is negative.

        """
        return self._queue_tween(Tween(frames, lambda _previous, _current: None), together=False)

    def on_complete(self: _Queue, callback: Callable[[_Queue], None]) -> _Queue:
        """Call `callback(self)` when the most recently queued tween finishes, or now if nothing is queued.

        In the world's step, callbacks run once every body and the camera have moved, so a callback that changes
        what characters do sees the final pose.

        Args:
            callback (Callable): Called with this object when the tween finishes.

        Returns:
            TweenQueue: This object, for chaining.

        """
        if not self._queue:
            callback(self)
        else:
            self._queue[-1].tweens[-1].callbacks.append(callback)
        return self

    def on_group_complete(self: _Queue, callback: Callable[[_Queue], None]) -> _Queue:
        """Call `callback(self)` when the last queued group finishes, or now if none is queued.

        Groups added after this call don't delay it.

        Args:
            callback (Callable): Called with this object when the group finishes.

        Returns:
            TweenQueue: This object, for chaining.

        """
        if not self._queue:
            callback(self)
        else:
            self._queue[-1].callbacks.append(callback)
        return self

    def cancel(self: _Queue) -> _Queue:
        """Discard queued tweens and their callbacks, keeping the current pose.

        Returns:
            TweenQueue: This object, for chaining.

        """
        self._queue.clear()
        self._callback_generation += 1
        self._group_ended()
        return self

    def _group_ended(self) -> None:
        """Handle the end of a group: finished, cancelled, or a tween applied at once. Subclasses may extend it."""

    def _queue_tween(self: _Queue, tween: Tween[typing.Any], *, together: bool) -> _Queue:
        if tween.frames < 0:
            msg = "A tween's frames must not be negative."
            raise ValueError(msg)
        if tween.frames == 0 and not self._queue:
            tween.advance()
            self._group_ended()
            for callback in tween.callbacks:
                callback(self)
            return self
        if together and self._queue:
            group = self._queue[-1]
            group.tweens.append(tween)
        else:
            group = _Group([tween])
            self._queue.append(group)
        group.follows = group.follows or tween.follow is not None
        return self

    def _advance(self) -> list[Callable[[typing.Any], None]]:
        """Play one frame of the group at the front of the queue and return the callbacks of what finished.

        Every tween in the group starts before any of them changes anything, so tweens played together share one
        starting pose.
        """
        if not self._queue:
            return []
        group = self._queue[0]
        finished: list[Callable[[typing.Any], None]] = []
        pending = [tween for tween in group.tweens if not tween.done]
        for tween in pending:
            tween.start()
        for tween in pending:
            tween.advance()
            if tween.done:
                finished.extend(tween.callbacks)
        if all(tween.done for tween in group.tweens):
            self._queue.pop(0)
            self._group_ended()
            finished.extend(group.callbacks)
        return finished
