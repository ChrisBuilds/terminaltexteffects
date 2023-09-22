"""EffectCharacter class and supporting classes to initialize and manage the state of a single character from the input data."""

import typing
from enum import Enum, auto
from terminaltexteffects.utils import graphics, motion

if typing.TYPE_CHECKING:
    from terminaltexteffects.utils.terminal import Terminal


class EventHandler:
    """Handles events for the EffectCharacter."""

    def __init__(self, character: "EffectCharacter"):
        self.character = character
        self.registered_events: dict[tuple[EventHandler.Event, str], list[tuple[EventHandler.Action, str]]] = {}

    class Event(Enum):
        """Events that can be registered with the EventHandler."""

        WAYPOINT_REACHED = auto()
        "A waypoint has been reached."
        SCENE_COMPLETE = auto()
        "An animation scene has completed."

    class Action(Enum):
        """Actions that can be taken when an event is triggered."""

        ACTIVATE_WAYPOINT = auto()
        "Activates a waypoint. The action target is the waypoint ID."
        ACTIVATE_SCENE = auto()
        "Activates an animation scene. The action target is the scene ID."

    def register_event(self, event: Event, caller: str, action: Action, action_target: str) -> None:
        """Registers an event to be handled by the EventHandler.

        Args:
            event (Event): The event to register.
            caller (str): The ID of the caller.
            action (Action): The action to take when the event is triggered.
            action_target (str): The ID of the action target.
        """
        new_event = (event, caller)
        new_action = (action, action_target)
        if new_event not in self.registered_events:
            self.registered_events[new_event] = list()
        self.registered_events[new_event].append(new_action)

    def handle_event(self, event: Event, caller: str) -> None:
        """Handles an event.

        Args:
            event (Event): An event to handle. If the event is not registered, nothing happens.
            caller (str): The ID of the caller.
        """
        action_map = {
            EventHandler.Action.ACTIVATE_WAYPOINT: self.character.motion.activate_waypoint,
            EventHandler.Action.ACTIVATE_SCENE: self.character.animator.activate_scene,
        }

        if (event, caller) not in self.registered_events:
            return
        for event_action in self.registered_events[(event, caller)]:
            action, action_target = event_action
            action_map[action](action_target)


class EffectCharacter:
    """A single character from the input data. Contains the state of the character.

    An EffectCharacter object contains the symbol, animation units, graphical modes, waypoints, and coordinates for a single
    character from the input data. The EffectCharacter object is used by the Effect class to animate the character.

    Attributes:
        symbol (str): the current symbol used in place of the character.
        is_active (bool): active characters are printed to the terminal.
        input_symbol (str): the symbol for the character in the input data.
    """

    def __init__(self, symbol: str, input_column: int, input_row: int, terminal: "Terminal"):
        """Initializes the EffectCharacter class.

        Args:
            symbol (str): the character symbol.
            input_column (int): the final column position of the character.
            input_row (int): the final row position of the character.
        """
        self.input_symbol: str = symbol
        "The symbol for the character in the input data."
        self.input_coord: motion.Coord = motion.Coord(input_column, input_row)
        "The coordinate of the character in the input data."
        self.symbol: str = symbol
        "The current symbol for the character, determined by the animation units."
        self.terminal: Terminal = terminal
        self.animator: graphics.Animator = graphics.Animator(self)
        self.motion: motion.Motion = motion.Motion(self)
        self.event_handler: EventHandler = EventHandler(self)
        self.is_active: bool = False
        "Active characters are printed to the terminal."
