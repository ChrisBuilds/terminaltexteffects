"""Custom exceptions for handling errors related to animations in the terminaltexteffects package.

Classes:
    FrameDurationError: Raised when a frame is added to a Scene with an invalid duration.
    ActivateEmptySceneError: Raised when a Scene without any frames is activated.
    ApplyGradientToSymbolsNoGradientsError: Raised when calling `apply_gradient_to_symbols` without gradients.
    ApplyGradientToSymbolsEmptyGradientsError: Raised when calling `apply_gradient_to_symbols` with empty gradients.

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


class ApplyGradientToSymbolsNoGradientsError(TerminalTextEffectsError):
    """Raised when calling `apply_gradient_to_symbols` without gradients.

    At least one gradient must be provided, either a foreground gradient or a
    background gradient when calling `apply_gradient_to_symbols`.

    """

    def __init__(self) -> None:
        """Initialize an ApplyGradientToSymbolsNoGradientsError."""
        self.message = "Foreground and background gradient are None. At least one gradient must be provided."
        super().__init__(self.message)


class ApplyGradientToSymbolsEmptyGradientsError(TerminalTextEffectsError):
    """Raised when calling `apply_gradient_to_symbols` with empty gradients.

    At least one gradient must be provided, either a foreground gradient or a
    background gradient when calling `apply_gradient_to_symbols`. In addition,
    at least one of the gradients must have at least one color.

    """

    def __init__(self) -> None:
        """Initialize an ApplyGradientToSymbolsEmptyGradientsError."""
        self.message = (
            "Foreground and background gradient are empty. At least one gradient must have at least "
            "one color in the spectrum."
        )
        super().__init__(self.message)


class ApplyGradientToSymbolsInvalidSymbolError(TerminalTextEffectsError):
    """Raised when calling `apply_gradient_to_symbols` with an invalid symbol.

    The symbol provided to `apply_gradient_to_symbols` must be a string with a length of 1.

    """

    def __init__(self, symbol: str) -> None:
        """Initialize an ApplyGradientToSymbolsInvalidSymbolError.

        Args:
            symbol (str): The symbol provided to `apply_gradient_to_symbols`.

        """
        self.symbol = symbol
        self.message = f"Symbol must be a string with a length of 1. Received: `{symbol}`."
        super().__init__(self.message)


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
