"""This module contains the EffectCharacter class and EventHandler class used to manage the state of a single character from the input data.
"""

import typing
from enum import Enum, auto
from terminaltexteffects.utils import graphics, motion


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
        layer (int): The layer of the character. The layer determines the order in which characters are printed.
    """

    def __init__(self, character: "EffectCharacter"):
        """Initializes the instance with the EffectCharacter object.

        Args:
            character (EffectCharacter): The character that the EventHandler is handling events for.
        """
        self.character = character
        self.layer: int = 0
        self.registered_events: dict[
            tuple[EventHandler.Event, graphics.Scene | motion.Waypoint],
            list[tuple[EventHandler.Action, graphics.Scene | motion.Waypoint | int]],
        ] = {}

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
            SET_LAYER (Action): Sets the layer of the character. The action target is the layer number.
        """

        ACTIVATE_WAYPOINT = auto()
        ACTIVATE_SCENE = auto()
        DEACTIVATE_WAYPOINT = auto()
        DEACTIVATE_SCENE = auto()
        SET_LAYER = auto()

    def register_event(
        self,
        event: Event,
        caller: graphics.Scene | motion.Waypoint,
        action: Action,
        target: graphics.Scene | motion.Waypoint | int,
    ) -> None:
        """Registers an event to be handled by the EventHandler.

        Examples:
            >>> character.event_handler.register_event(EventHandler.Event.WAYPOINT_REACHED, "waypoint_1", EventHandler.Action.ACTIVATE_WAYPOINT, "waypoint_2")

        Args:
            event (Event): The event to register.
            subject_id (str): The ID of the event subject (waypoint id/scene id).
            action (Action): The action to take when the event is triggered.
            action_target (str): The ID of the action target.
        """
        new_event = (event, caller)
        new_action = (action, target)
        if new_event not in self.registered_events:
            self.registered_events[new_event] = list()
        self.registered_events[new_event].append(new_action)

    def handle_event(self, event: Event, caller: graphics.Scene | motion.Waypoint) -> None:
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
            EventHandler.Action.SET_LAYER: lambda layer: setattr(self.character, "layer", layer),
        }

        if (event, caller) not in self.registered_events:
            return
        for event_action in self.registered_events[(event, caller)]:
            action, target = event_action
            action_map[action](target)  # type: ignore


class EffectCharacter:
    """
    A class representing a single character from the input data.

    Attributes:
        input_symbol (str): The symbol for the character in the input data.
        input_coord (motion.Coord): The coordinate of the character in the input data.
        symbol (str): The current symbol for the character, determined by the animation units.
        animation (graphics.Animation): The animation object that controls the character's appearance.
        motion (motion.Motion): The motion object that controls the character's movement.
        event_handler (EventHandler): The event handler object that handles events related to the character.
        is_active (bool): Whether the character is currently active and should be printed to the terminal.
    """

    def __init__(self, symbol: str, input_column: int, input_row: int):
        """Initializes the instance with the input values and the Terminal object.

        Args:
            symbol (str): The symbol for the character in the input data.
            input_column (int): The column of the character in the input data.
            input_row (int): The row of the character in the input data.
        """
        self.input_symbol: str = symbol
        self.input_coord: motion.Coord = motion.Coord(input_column, input_row)
        self.symbol: str = symbol
        self.animation: graphics.Animation = graphics.Animation(self)
        self.motion: motion.Motion = motion.Motion(self)
        self.event_handler: EventHandler = EventHandler(self)
        self.is_active: bool = False
        self.layer: int = 0

    def __hash__(self) -> int:
        return hash(self.input_coord)

    def __eq__(self, other: typing.Any) -> bool:
        if not isinstance(other, EffectCharacter):
            return NotImplemented
        return self.input_coord == other.input_coord
