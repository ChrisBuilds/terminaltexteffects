"""Custom exceptions for handling errors related to motion in the terminaltexteffects package."""

from __future__ import annotations

from terminaltexteffects.utils.exceptions.base_terminaltexteffects_exception import TerminalTextEffectsError


class PathInvalidSpeedError(TerminalTextEffectsError):
    """Raised when a Path is initialized with an invalid speed.

    A Path must be initialized with a speed that is a positive float. This error is raised when a Path is initialized
    with a speed that is not a positive float.

    """

    def __init__(self, speed: float) -> None:
        """Initialize a PathInvalidSpeedError.

        Args:
            speed (float): The speed provided to the Path.

        """
        self.speed = speed
        self.message = f"Path speed must be a positive float. Received: `{speed}`."
        super().__init__(self.message)


class WaypointNotFoundError(TerminalTextEffectsError):
    """Raised when a Waypoint is not found in a Path.

    A WaypointNotFoundError is raised when a Waypoint with the given ID is not found in a Path.

    """

    def __init__(self, waypoint_id: str) -> None:
        """Initialize a WaypointNotFoundError.

        Args:
            waypoint_id (str): The waypoint ID queried.

        """
        self.waypoint_id = waypoint_id
        self.message = f"Waypoint `{waypoint_id}` not found in Path."
        super().__init__(self.message)


class PathNotFoundError(TerminalTextEffectsError):
    """Raised when a Path is not found.

    A PathNotFoundError is raised when a Path with the given ID is not found.

    """

    def __init__(self, path_id: str) -> None:
        """Initialize a PathNotFoundError.

        Args:
            path_id (str): The path ID queried.

        """
        self.path_id = path_id
        self.message = f"Path `{path_id}` not found."
        super().__init__(self.message)


class ActivateEmptyPathError(TerminalTextEffectsError):
    """Raised when attempting to activate an empty Path.

    An ActivateEmptyPathError is raised when attempting to activate a Path that has no Waypoints.

    """

    def __init__(self, path_id: str) -> None:
        """Initialize an ActivateEmptyPathError.

        Args:
            path_id (str): The ID of the Path that is empty.

        """
        self.path_id = path_id
        self.message = f"Cannot activate an empty Path `{path_id}`."
        super().__init__(self.message)


class DuplicatePathIDError(TerminalTextEffectsError):
    """Raised when a Path is initialized with a duplicate ID.

    A DuplicatePathIDError is raised when a Path is initialized with an ID that has already been used.

    """

    def __init__(self, path_id: str) -> None:
        """Initialize a DuplicatePathIDError.

        Args:
            path_id (str): The ID provided to the Path.

        """
        self.path_id = path_id
        self.message = f"Path ID `{path_id}` has already been used."
        super().__init__(self.message)


class DuplicateWaypointIDError(TerminalTextEffectsError):
    """Raised when a Waypoint is initialized with a duplicate ID.

    A DuplicateWaypointIDError is raised when a Waypoint is initialized with an ID that has already been used
    in the Path.

    """

    def __init__(self, waypoint_id: str) -> None:
        """Initialize a DuplicateWaypointIDError.

        Args:
            waypoint_id (str): The ID provided to the Waypoint.

        """
        self.waypoint_id = waypoint_id
        self.message = f"Waypoint ID `{waypoint_id}` has already been used."
        super().__init__(self.message)
