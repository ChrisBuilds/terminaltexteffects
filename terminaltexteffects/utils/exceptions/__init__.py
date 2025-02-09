"""TerminalTextEffects exceptions module."""

from terminaltexteffects.utils.exceptions.animation_exceptions import (
    ActivateEmptySceneError,
    ApplyGradientToSymbolsEmptyGradientsError,
    ApplyGradientToSymbolsInvalidSymbolError,
    ApplyGradientToSymbolsNoGradientsError,
    FrameDurationError,
    SceneNotFoundError,
)
from terminaltexteffects.utils.exceptions.base_character_exceptions import (
    EventRegistrationCallerError,
    EventRegistrationTargetError,
)
from terminaltexteffects.utils.exceptions.motion_exceptions import (
    ActivateEmptyPathError,
    DuplicatePathIDError,
    DuplicateWaypointIDError,
    PathInvalidSpeedError,
    PathNotFoundError,
    WaypointNotFoundError,
)
from terminaltexteffects.utils.exceptions.terminal_exceptions import (
    InvalidCharacterGroupError,
    InvalidCharacterSortError,
    InvalidColorSortError,
)
