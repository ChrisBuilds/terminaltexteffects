"""Custom exceptions for handling errors related to EffectCharacters in the terminaltexteffects package."""

from __future__ import annotations

from typing import TYPE_CHECKING

from terminaltexteffects.utils.exceptions.base_terminaltexteffects_exception import TerminalTextEffectsError

if TYPE_CHECKING:
    from terminaltexteffects import Coord, EventHandler, Path, Scene, Waypoint


class EventRegistrationCallerError(TerminalTextEffectsError):
    """Raised when an event is registered with an invalid event -> caller relationship.

    Each event can only be registered with a related caller type. This error is raised when an event is registered with
    a caller that is not of the required type. For example, a Scene will never trigger a Path related event,
    and vice versa.

    The following are the valid caller types for each event:

    Event -> Caller

        - SEGMENT_* -> Path
        - PATH_*    -> Path
        - SCENE_*   -> Scene
    """

    def __init__(
        self,
        event: EventHandler.Event,
        caller: Scene | Waypoint | Path,
        required: type[Scene | Waypoint | Path],
    ) -> None:
        """Initialize an EventRegistrationCallerError.

        Args:
            event (EventHandler.Event): The event that was registered.
            caller (Scene | Waypoint | Path): The object provided to trigger the event.
            required (Scene | Waypoint | Path): The valid caller types for the event.

        """
        self.event = event
        self.caller = caller
        self.required = required
        self.message = (
            f"Event `{event.name}` registered with caller type `{caller.__class__.__name__}`. Event `{event.name}` "
            f"requires caller type `{required.__name__}`."
        )
        super().__init__(self.message)


class EventRegistrationTargetError(TerminalTextEffectsError):
    """Raised when an event is registered with an invalid action -> target relationship.

    Each event action can only be registered with a related target type. This error is raised when an event action
    is registered with a target that is not of the required type. For example, an ACTIVATE_SCENE action
    will can not activate on a Path target.

    The following are the valid target types for each action:

    Action -> Target

        - *_SCENE          -> Scene
        - *_PATH           -> Path
        - SET_LAYER        -> Int
        - SET_COORDINATE   -> Coord
        - CALLBACK         -> EventHandler.Callback
        - RESET_APPEARANCE -> None
    """

    def __init__(
        self,
        action: EventHandler.Action,
        target: Scene | Path | int | Coord | EventHandler.Callback | None,
        required: type[Scene | Path | int | Coord | EventHandler.Callback | None],
    ) -> None:
        """Initialize an EventRegistrationTargetError.

        Args:
            action (EventHandler.Action): The action that was registered.
            target (Scene | Path | int | Coord | EventHandler.Callback | None): The target provided to the action.
            required (type[Scene  |  Path  |  int  |  Coord  |  EventHandler.Callback  |  None]): The valid target
                types.

        """
        self.action = action
        self.target = target
        self.required = required
        self.message = (
            f"Event action `{action.name}` registered with target type `{target.__class__.__name__}`. "
            f"Action `{action.name}` requires target type `{required.__name__}`."
        )
        super().__init__(self.message)
