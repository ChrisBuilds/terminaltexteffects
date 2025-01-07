"""EffectCharacter class and EventHandler class used to manage the state of a single character from the input data."""

from __future__ import annotations

import typing
from dataclasses import dataclass
from enum import Enum, auto

from terminaltexteffects.engine import animation, motion
from terminaltexteffects.utils.exceptions import (
    EventRegistrationCallerError,
    EventRegistrationTargetError,
)
from terminaltexteffects.utils.geometry import Coord


class EventHandler:
    """Register and handle events related to a character.

    Events related to character state changes (e.g. scene complete) can be registered with the EventHandler.
    When an event is triggered, the EventHandler will take the specified action (e.g. activate a Path).
    The EventHandler is used by the EffectCharacter class to handle events related to the character.

    Attributes:
        character (EffectCharacter): The character that the EventHandler is handling events for.
        registered_events (dict[tuple[Event, str], list[tuple[Action, str]]]): A dictionary of registered events.
            The key is a tuple of the event and the caller ID (waypoint id/scene id).
            The value is a list of tuples of the action and the action target (path id/scene id).
        layer (int): The layer of the character. The layer determines the order in which characters are printed.

    Note:
        SEGMENT_ENTERED/EXITED events will trigger the first time the character enters or exits a segment.
        If looping, each loop will trigger the event, but not backwards motion as is possible with
        the bounce easing functions.

    """

    def __init__(self, character: EffectCharacter) -> None:
        """Initialize the instance with the EffectCharacter object.

        Args:
            character (EffectCharacter): The character for which the EventHandler is handling events.

        """
        self.character = character
        self.registered_events: dict[
            tuple[EventHandler.Event, animation.Scene | motion.Waypoint | motion.Path],
            list[
                tuple[
                    EventHandler.Action,
                    animation.Scene | motion.Waypoint | motion.Path | int | Coord | EventHandler.Callback | None,
                ]
            ],
        ] = {}

    class Event(Enum):
        """An Event that can be registered with the EventHandler.

        Register Events with the EventHandler using the register_event method of the EventHandler class.

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
            RESET_APPEARANCE (Action): Resets the appearance of the character to the input symbol and color.
            SET_LAYER (Action): Sets the layer of the character. The action target is the layer number.
            SET_COORDINATE (Action): Sets the coordinate of the character. The action target is the coordinate.
            CALLBACK (Action): Calls a callback function. The action target is an EventHandler.Callback object.

        """

        ACTIVATE_PATH = auto()
        ACTIVATE_SCENE = auto()
        DEACTIVATE_PATH = auto()
        DEACTIVATE_SCENE = auto()
        RESET_APPEARANCE = auto()
        SET_LAYER = auto()
        SET_COORDINATE = auto()
        CALLBACK = auto()

    @dataclass(init=False)
    class Callback:
        """A callback action target that can be taken when an event is triggered.

        Register callback actions with the EventHandler using the register_event method of the EventHandler class.

        The callback function will be called with the character and any additional arguments when the event
        is triggered. The character will be the first argument passed to the callback function followed by any
        additional arguments in the order they were passed to the Callback object.

        Example:
            Create a callback to set the character's visibility to False. The following code would be
            used within an effect where 'self' is the EffectIterator instance:

                cb = EventHandler.Callback(lambda c: self.terminal.set_character_visibility(c, is_visible=False))

        """

        callback: typing.Callable
        args: tuple[typing.Any, ...]

        def __init__(self, callback: typing.Callable, *args: typing.Any) -> None:
            """Initialize the instance with the callback function and arguments.

            Args:
                callback (typing.Callable): The callback function to call.
                args (tuple[typing.Any,...]): A tuple of arguments to pass to the callback function. The first argument
                    will be the character, followed by any additional arguments.

            """
            self.callback = callback
            self.args = args

    @typing.overload
    def register_event(
        self,
        event: Event,
        caller: animation.Scene | motion.Waypoint | motion.Path,
        action: typing.Literal[Action.ACTIVATE_SCENE, Action.DEACTIVATE_SCENE],
        target: animation.Scene,
    ) -> None: ...

    @typing.overload
    def register_event(
        self,
        event: Event,
        caller: animation.Scene | motion.Waypoint | motion.Path,
        action: typing.Literal[Action.ACTIVATE_PATH, Action.DEACTIVATE_PATH],
        target: motion.Path,
    ) -> None: ...

    @typing.overload
    def register_event(
        self,
        event: Event,
        caller: animation.Scene | motion.Waypoint | motion.Path,
        action: typing.Literal[Action.SET_COORDINATE],
        target: Coord,
    ) -> None: ...

    @typing.overload
    def register_event(
        self,
        event: Event,
        caller: animation.Scene | motion.Waypoint | motion.Path,
        action: typing.Literal[Action.SET_LAYER],
        target: int,
    ) -> None: ...

    @typing.overload
    def register_event(
        self,
        event: Event,
        caller: animation.Scene | motion.Waypoint | motion.Path,
        action: typing.Literal[Action.CALLBACK],
        target: Callback,
    ) -> None: ...

    @typing.overload
    def register_event(
        self,
        event: Event,
        caller: animation.Scene | motion.Waypoint | motion.Path,
        action: typing.Literal[Action.RESET_APPEARANCE],
    ) -> None: ...

    def register_event(
        self,
        event: Event,
        caller: animation.Scene | motion.Waypoint | motion.Path,
        action: Action,
        target: animation.Scene | motion.Path | int | Coord | Callback | None = None,
    ) -> None:
        """Register an event to be handled by the EventHandler.

        Args:
            event (Event): The event to register.
            caller (animation.Scene | motion.Waypoint | motion.Path): The object that triggers the event.
            action (Action): The action to take when the event is triggered.
            target (animation.Scene | motion.Path | int | Coord | Callback): The target of the action.

        Raises:
            ValueError: If the caller or target object is not the correct type for the event or action.

        Example:
            Register an event to activate a scene when a Path is complete:
            `event_handler.register_event(EventHandler.Event.PATH_COMPLETE, some_path,
                EventHandler.Action.ACTIVATE_SCENE, some_scene)`

        """
        event_caller_map = {
            EventHandler.Event.SEGMENT_ENTERED: motion.Waypoint,
            EventHandler.Event.SEGMENT_EXITED: motion.Waypoint,
            EventHandler.Event.PATH_ACTIVATED: motion.Path,
            EventHandler.Event.PATH_COMPLETE: motion.Path,
            EventHandler.Event.PATH_HOLDING: motion.Path,
            EventHandler.Event.SCENE_ACTIVATED: animation.Scene,
            EventHandler.Event.SCENE_COMPLETE: animation.Scene,
        }

        action_target_map = {
            EventHandler.Action.ACTIVATE_PATH: motion.Path,
            EventHandler.Action.ACTIVATE_SCENE: animation.Scene,
            EventHandler.Action.DEACTIVATE_PATH: motion.Path,
            EventHandler.Action.DEACTIVATE_SCENE: animation.Scene,
            EventHandler.Action.RESET_APPEARANCE: type(None),
            EventHandler.Action.SET_LAYER: int,
            EventHandler.Action.SET_COORDINATE: Coord,
            EventHandler.Action.CALLBACK: EventHandler.Callback,
        }

        if event_caller_map[event] != caller.__class__:
            raise EventRegistrationCallerError(event, caller, event_caller_map[event])

        if (action is EventHandler.Action.RESET_APPEARANCE and target is not None) or (
            action_target_map[action] != target.__class__
        ):
            raise EventRegistrationTargetError(action, target, action_target_map[action])

        new_event = (event, caller)
        new_action = (action, target)
        if new_event not in self.registered_events:
            self.registered_events[new_event] = []
        self.registered_events[new_event].append(new_action)

    def _handle_event(self, event: Event, caller: animation.Scene | motion.Waypoint | motion.Path) -> None:
        """Handle an event by taking the specified action.

        Args:
            event (Event): An event to handle. If the event is not registered, nothing happens.
            caller (animation.Scene | motion.Waypoint | motion.Path): The object triggering the call.

        """
        action_map = {
            EventHandler.Action.ACTIVATE_PATH: self.character.motion.activate_path,
            EventHandler.Action.ACTIVATE_SCENE: self.character.animation.activate_scene,
            EventHandler.Action.DEACTIVATE_PATH: self.character.motion.deactivate_path,
            EventHandler.Action.DEACTIVATE_SCENE: self.character.animation.deactivate_scene,
            EventHandler.Action.RESET_APPEARANCE: lambda _: self.character.animation.set_appearance(
                self.character.input_symbol,
            ),
            EventHandler.Action.SET_LAYER: lambda layer: setattr(self.character, "layer", layer),
            EventHandler.Action.SET_COORDINATE: lambda coord: setattr(self.character.motion, "current_coord", coord),
            EventHandler.Action.CALLBACK: lambda callback: callback.callback(self.character, *callback.args),
        }

        if (event, caller) not in self.registered_events:
            return
        for event_action in self.registered_events[(event, caller)]:
            action, target = event_action
            action_map[action](target)  # type: ignore[operator]


class EffectCharacter:
    """A class representing a single character from the input data.

    EffectCharacters are managed by the Terminal and are used to apply animations and effects to individual characters.
    Add an EffectCharacter to the Terminal using the add_character method of the Terminal class.

    Methods:
        tick: Progress the character's animation and motion by one step.

    Attributes:
        character_id (int): The unique ID of the character, generated by the Terminal.
        input_symbol (str): The symbol for the character in the input data.
        input_coord (Coord): The coordinate of the character in the input data.
        is_visible (bool): Whether the character is currently visible and should be printed to the terminal.
        animation (graphics.Animation): The animation object that controls the character's appearance.
        motion (motion.Motion): The motion object that controls the character's movement.
        event_handler (EventHandler): The event handler object that handles events related to the character.
        layer (int): The layer of the character. The layer determines the order in which characters are printed.
        is_fill_character (bool): Whether the character is a fill character. Fill characters are used to fill
            the empty cells of the Canvas.

    """

    def __init__(self, character_id: int, symbol: str, input_column: int, input_row: int) -> None:
        """Initialize the character instance with the character ID, symbol, and input coordinates.

        Args:
            character_id (int): The unique ID of the character, generated by the Terminal.
            symbol (str): The symbol for the character in the input data.
            input_column (int): The column of the character in the input data.
            input_row (int): The row of the character in the input data.

        """
        self._character_id: int = character_id
        self._input_symbol: str = symbol
        self._input_coord: Coord = Coord(input_column, input_row)
        self._input_ansi_sequences: dict[str, str | None] = {"fg_color": None, "bg_color": None}
        self._is_visible: bool = False
        self.animation: animation.Animation = animation.Animation(self)
        self.motion: motion.Motion = motion.Motion(self)
        self.event_handler: EventHandler = EventHandler(self)
        self.layer: int = 0
        self.is_fill_character = False

    @property
    def input_symbol(self) -> str:
        """The symbol for the character in the input data."""
        return self._input_symbol

    @property
    def input_coord(self) -> Coord:
        """The coordinate of the character in the input data."""
        return self._input_coord

    @property
    def is_visible(self) -> bool:
        """Whether the character is currently visible and should be printed to the terminal."""
        return self._is_visible

    @property
    def character_id(self) -> int:
        """The unique ID of the character, generated by the Terminal."""
        return self._character_id

    @property
    def is_active(self) -> bool:
        """Returns whether the character is currently active.

        A character is active if its animation or motion is not complete.

        Returns:
            bool: True if the character is active, False if not.

        """
        return bool(not self.animation.active_scene_is_complete() or not self.motion.movement_is_complete())

    def tick(self) -> None:
        """Progress the character's animation and motion by one step."""
        self.motion.move()
        self.animation.step_animation()

    def __hash__(self) -> int:
        """Return the hash value of the character."""
        return hash(self.character_id)

    def __eq__(self, other: object) -> bool:
        """Check if two EffectCharacter instances are equal based on their character_id."""
        if not isinstance(other, EffectCharacter):
            return NotImplemented
        return self.character_id == other.character_id

    def __repr__(self) -> str:
        """Return a string representation of the EffectCharacter instance."""
        return (
            f"EffectCharacter(character_id={self.character_id}, symbol='{self.input_symbol}', "
            f"input_column={self.input_coord.column}, input_row={self.input_coord.row})"
        )
