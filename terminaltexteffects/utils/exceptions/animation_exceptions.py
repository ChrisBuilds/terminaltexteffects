"""Custom exceptions for handling errors related to animations in the terminaltexteffects package.

Classes:
    FrameDurationError: Raised when a frame is added to a Scene with an invalid duration.
    ActivateEmptySceneError: Raised when a Scene without any frames is activated.
    AnimationSceneError: Generic Scene/animation error with a provided message.

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from terminaltexteffects.utils.exceptions.base_terminaltexteffects_exception import TerminalTextEffectsError

if TYPE_CHECKING:
    from terminaltexteffects import Scene


class FrameDurationError(TerminalTextEffectsError):
    """Raised when a frame is added to a Scene with an invalid duration.

    A frame duration must be a positive integer. This error is raised when a frame is added to a Scene with a duration
    that is not a positive integer.

    """

    def __init__(self, duration: int) -> None:
        """Initialize a FrameDurationError.

        Args:
            duration (int): The duration provided to the frame.

        """
        self.duration = duration
        self.message = f"Frame duration must be a positive integer. Received: `{duration}`."
        super().__init__(self.message)


class ActivateEmptySceneError(TerminalTextEffectsError):
    """Raised when a Scene is without any frames is activated.

    A Scene must have at least one frame to be activated.

    """

    def __init__(self, scene: Scene) -> None:
        """Initialize an ActivateEmptySceneError.

        Args:
            scene (Scene): The Scene that was activated.

        """
        self.scene = scene
        self.message = f"Scene `{scene.scene_id}` has no frames. A Scene must have at least one frame to be activated."
        super().__init__(self.message)


class AnimationSceneError(TerminalTextEffectsError):
    """Generic Scene/animation error with a provided message."""

    def __init__(self, message: str) -> None:
        """Initialize an AnimationSceneError.

        Args:
            message (str): The message to display.

        """
        self.message = message
        super().__init__(message)


class SceneNotFoundError(TerminalTextEffectsError):
    """Raised when `query_scene` is called with a scene_id that does not exist."""

    def __init__(self, scene_id: str) -> None:
        """Initialize a SceneNotFoundError.

        Args:
            scene_id (str): The scene_id that was not found.

        """
        self.scene_id = scene_id
        self.message = f"Scene with scene_id `{scene_id}` not found."
        super().__init__(self.message)
