"""This module contains the EffectCharacter class and EventHandler class used to manage the state of a single character from the input data.
"""

import typing
from dataclasses import dataclass
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
            tuple[EventHandler.Event, graphics.Scene | motion.Waypoint | motion.Path],
            list[
                tuple[
                    EventHandler.Action,
                    graphics.Scene | motion.Waypoint | motion.Path | int | motion.Coord | EventHandler.Callback,
                ]
            ],
        ] = {}

    class Event(Enum):
        """An Event that can be registered with the EventHandler.

        An Event is triggered when a character reaches a waypoint or an animation scene is activated. Register
        Events with the EventHandler using the register_event method of the EventHandler class.

        Attributes:
            SEGMENT_ENTERED (Event): A path segment has been entered.
            SEGMENT_EXITED (Event): A path segment has been exited.
            PATH_ACTIVATED (Event): A path has been activated.
            PATH_COMPLETE (Event): A path has been completed.
            PATH_HOLDING (Event): A path has entered the holding state.
            SCENE_ACTIVATED (Event): An animation scene has been activated.
            SCENE_COMPLETE (Event): An animation scene has completed.
        """

        SEGMENT_ENTERED = auto()
        SEGMENT_EXITED = auto()
        PATH_ACTIVATED = auto()
        PATH_COMPLETE = auto()
        PATH_HOLDING = auto()
        SCENE_ACTIVATED = auto()
        SCENE_COMPLETE = auto()

    class Action(Enum):
        """Actions that can be taken when an event is triggered.

        An Action is taken when an Event is triggered. Register Actions with the EventHandler using the
        register_event method of the EventHandler class.

        Attributes:
            ACTIVATE_PATH (Action): Activates a path. The action target is the path ID.
            ACTIVATE_SCENE (Action): Activates an animation scene. The action target is the scene ID.
            DEACTIVATE_PATH (Action): Deactivates a path. The action target is the path ID.
            DEACTIVATE_SCENE (Action): Deactivates an animation scene. The action target is the scene ID.
            SET_CHARACTER_ACTIVATION_STATE (Action): Sets the activation state of the character. The action target is the activation state (True/False).
            SET_LAYER (Action): Sets the layer of the character. The action target is the layer number.
            SET_COORDINATE (Action): Sets the coordinate of the character. The action target is the coordinate.
        """

        ACTIVATE_PATH = auto()
        ACTIVATE_SCENE = auto()
        DEACTIVATE_PATH = auto()
        DEACTIVATE_SCENE = auto()
        SET_CHARACTER_VISIBILITY_STATE = auto()
        SET_LAYER = auto()
        SET_COORDINATE = auto()
        CALLBACK = auto()

    @dataclass(init=False)
    class Callback:
        """A callback action target that can be taken when an event is triggered.

        Register callback actions with the EventHandler using the register_event method of the EventHandler class.

        Attributes:
            callback (typing.Callable): The callback function to call.
            args (tuple[typing.Any,...]): A tuple of arguments to pass to the callback function.
        """

        callback: typing.Callable
        args: tuple[typing.Any, ...]

        def __init__(self, callback: typing.Callable, *args: typing.Any):
            self.callback = callback
            self.args = args

    def register_event(
        self,
        event: Event,
        caller: graphics.Scene | motion.Waypoint | motion.Path,
        action: Action,
        target: graphics.Scene | motion.Waypoint | motion.Path | int | motion.Coord | Callback,
    ) -> None:
        """Registers an event to be handled by the EventHandler.

        Args:
            event (Event): The event to register.
            subject_id (str): The ID of the event subject (path id/scene id).
            action (Action): The action to take when the event is triggered.
            action_target (str): The ID of the action target.
        """
        new_event = (event, caller)
        new_action = (action, target)
        if new_event not in self.registered_events:
            self.registered_events[new_event] = list()
        self.registered_events[new_event].append(new_action)

    def handle_event(self, event: Event, caller: graphics.Scene | motion.Waypoint | motion.Path) -> None:
        """Handles an event by taking the specified action.

        Args:
            event (Event): An event to handle. If the event is not registered, nothing happens.
            caller (graphics.Scene | motion.Waypoint | motion.Path): The object triggering the call.
        """
        action_map = {
            EventHandler.Action.ACTIVATE_PATH: self.character.motion.activate_path,
            EventHandler.Action.ACTIVATE_SCENE: self.character.animation.activate_scene,
            EventHandler.Action.DEACTIVATE_PATH: self.character.motion.deactivate_path,
            EventHandler.Action.DEACTIVATE_SCENE: self.character.animation.deactivate_scene,
            EventHandler.Action.SET_LAYER: lambda layer: setattr(self.character, "layer", layer),
            EventHandler.Action.SET_CHARACTER_VISIBILITY_STATE: lambda state: setattr(
                self.character, "is_visible", state
            ),
            EventHandler.Action.SET_COORDINATE: lambda coord: setattr(self.character.motion, "current_coord", coord),
            EventHandler.Action.CALLBACK: lambda callback: callback.callback(self.character, *callback.args),
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
        is_visible (bool): Whether the character is currently visible and should be printed to the terminal.
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
        self.is_visible: bool = False
        self.layer: int = 0

    def tick(self) -> None:
        """Progress the character's animation and motion by one step."""
        self.motion.move()
        self.animation.step_animation()

    def is_active(self) -> bool:
        """Returns whether the character is currently active. A character is active if its animation or motion is not complete.

        Returns:
            bool: True if the character is active, False if not.
        """
        if not self.animation.active_scene_is_complete() or not self.motion.movement_is_complete():
            return True
        return False

    def __hash__(self) -> int:
        return hash(self.input_coord)

    def __eq__(self, other: typing.Any) -> bool:
        if not isinstance(other, EffectCharacter):
            return NotImplemented
        return self.input_coord == other.input_coord
