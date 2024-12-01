"""TerminalTextEffects exceptions module."""

from terminaltexteffects.utils.exceptions.animation_exceptions import (
    ActivateEmptySceneError,
    ApplyGradientToSymbolsEmptyGradientsError,
    ApplyGradientToSymbolsNoGradientsError,
    FrameDurationError,
    SceneNotFoundError,
)
from terminaltexteffects.utils.exceptions.base_character_exceptions import (
    EventRegistrationCallerError,
    EventRegistrationTargetError,
)
