"""This module contains the EffectCharacter class and EventHandler class used to manage the state of a single character from the input data.
"""

import typing
from enum import Enum, auto
from terminaltexteffects.utils import graphics, motion

if typing.TYPE_CHECKING:
    from terminaltexteffects.utils.terminal import Terminal


class EventHandler:
    """Register and handle events related to a character.

    Events related to character state changes (e.g. waypoint reached) can be registered with the EventHandler.
    When an event is triggered, the EventHandler will take the specified action (e.g. activate a waypoint).
    The EventHandler is used by the EffectCharacter class to handle events related to the character.

    Attributes:
        character (EffectCharacter): The character that the EventHandler is handling events for.
        registered_events (dict[tuple[Event, str], list[tuple[Action, str]]]): A dictionary of registered events.
            The key is a tuple of the event and the subject_id (waypoint id/scene id).
            The value is a list of tuples of the action and the action target (waypoint id/scene id).
    """

    def __init__(self, character: "EffectCharacter"):
        """Initializes the instance with the EffectCharacter object.

        Args:
            character (EffectCharacter): The character that the EventHandler is handling events for.
        """
        self.character = character
        self.registered_events: dict[tuple[EventHandler.Event, str], list[tuple[EventHandler.Action, str]]] = {}

    class Event(Enum):
        """An Event that can be registered with the EventHandler.

        An Event is triggered when a character reaches a waypoint or an animation scene is activated. Register
        Events with the EventHandler using the register_event method of the EventHandler class.

        Attributes:
            WAYPOINT_ACTIVATED (Event): A waypoint has been activated.
            WAYPOINT_REACHED (Event): A waypoint has been reached.
            SCENE_ACTIVATED (Event): An animation scene has been activated.
            SCENE_COMPLETE (Event): An animation scene has completed.
        """

        WAYPOINT_ACTIVATED = auto()
        WAYPOINT_REACHED = auto()
        SCENE_ACTIVATED = auto()
        SCENE_COMPLETE = auto()

    class Action(Enum):
        """Actions that can be taken when an event is triggered.

        An Action is taken when an Event is triggered. Register Actions with the EventHandler using the
        register_event method of the EventHandler class.

        Attributes:
            ACTIVATE_WAYPOINT (Action): Activates a waypoint. The action target is the waypoint ID.
            ACTIVATE_SCENE (Action): Activates an animation scene. The action target is the scene ID.
            DEACTIVATE_WAYPOINT (Action): Deactivates a waypoint. The action target is the waypoint ID.
            DEACTIVATE_SCENE (Action): Deactivates an animation scene. The action target is the scene ID.
        """

        ACTIVATE_WAYPOINT = auto()
        ACTIVATE_SCENE = auto()
        DEACTIVATE_WAYPOINT = auto()
        DEACTIVATE_SCENE = auto()

    def register_event(self, event: Event, subject_id: str, action: Action, action_target: str) -> None:
        """Registers an event to be handled by the EventHandler.

        Examples:
            >>> character.event_handler.register_event(EventHandler.Event.WAYPOINT_REACHED, "waypoint_1", EventHandler.Action.ACTIVATE_WAYPOINT, "waypoint_2")

        Args:
            event (Event): The event to register.
            subject_id (str): The ID of the event subject (waypoint id/scene id).
            action (Action): The action to take when the event is triggered.
            action_target (str): The ID of the action target.
        """
        new_event = (event, subject_id)
        new_action = (action, action_target)
        if new_event not in self.registered_events:
            self.registered_events[new_event] = list()
        self.registered_events[new_event].append(new_action)

    def handle_event(self, event: Event, subject_id: str) -> None:
        """Handles an event by taking the specified action.

        Examples:
            >>> character.event_handler.handle_event(EventHandler.Event.WAYPOINT_REACHED, "waypoint_1")

        Args:
            event (Event): An event to handle. If the event is not registered, nothing happens.
            subject_id (str): The subject_id of the event subject (waypoint id/scene id).
        """
        action_map = {
            EventHandler.Action.ACTIVATE_WAYPOINT: self.character.motion.activate_waypoint,
            EventHandler.Action.ACTIVATE_SCENE: self.character.animation.activate_scene,
            EventHandler.Action.DEACTIVATE_WAYPOINT: self.character.motion.deactivate_waypoint,
            EventHandler.Action.DEACTIVATE_SCENE: self.character.animation.deactivate_scene,
        }

        if (event, subject_id) not in self.registered_events:
            return
        for event_action in self.registered_events[(event, subject_id)]:
            action, action_target = event_action
            action_map[action](action_target)


class EffectCharacter:
    """
    A class representing a single character from the input data.

    Attributes:
        input_symbol (str): The symbol for the character in the input data.
        input_coord (motion.Coord): The coordinate of the character in the input data.
        symbol (str): The current symbol for the character, determined by the animation units.
        terminal (Terminal): The terminal object where the character will be printed.
        animation (graphics.Animation): The animation object that controls the character's appearance.
        motion (motion.Motion): The motion object that controls the character's movement.
        event_handler (EventHandler): The event handler object that handles events related to the character.
        is_active (bool): Whether the character is currently active and should be printed to the terminal.
    """

    def __init__(self, symbol: str, input_column: int, input_row: int, terminal: "Terminal"):
        """Initializes the instance with the input values and the Terminal object.

        Args:
            symbol (str): The symbol for the character in the input data.
            input_column (int): The column of the character in the input data.
            input_row (int): The row of the character in the input data.
            terminal (Terminal): The terminal object where the character will be printed.
        """
        self.input_symbol: str = symbol
        self.input_coord: motion.Coord = motion.Coord(input_column, input_row)
        self.symbol: str = symbol
        self.terminal: Terminal = terminal
        self.animation: graphics.Animation = graphics.Animation(self)
        self.motion: motion.Motion = motion.Motion(self)
        self.event_handler: EventHandler = EventHandler(self)
        self.is_active: bool = False

    def __hash__(self) -> int:
        return hash(self.input_coord)

    def __eq__(self, other: typing.Any) -> bool:
        if not isinstance(other, EffectCharacter):
            return NotImplemented
        return self.input_coord == other.input_coord
