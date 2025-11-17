"""Tests for the Path, Segment, Waypoint and Motion classes."""

import pytest

from terminaltexteffects.engine.base_character import EffectCharacter, EventHandler
from terminaltexteffects.engine.motion import Path, Segment, Waypoint
from terminaltexteffects.utils import easing
from terminaltexteffects.utils.exceptions import (
    ActivateEmptyPathError,
    DuplicatePathIDError,
    DuplicateWaypointIDError,
    PathInvalidSpeedError,
    PathNotFoundError,
    WaypointNotFoundError,
)
from terminaltexteffects.utils.geometry import Coord, find_length_of_bezier_curve, find_length_of_line

pytestmark = [pytest.mark.engine, pytest.mark.motion, pytest.mark.smoke]


@pytest.fixture
def character() -> EffectCharacter:
    """Fixture for creating an EffectCharacter instance."""
    return EffectCharacter(0, "a", 0, 0)


@pytest.fixture
def waypoint() -> Waypoint:
    """Fixture for creating a Waypoint instance."""
    return Waypoint(waypoint_id="waypoint_0", coord=Coord(0, 0), bezier_control=(Coord(0, 10),))


def test_waypoint_init(waypoint: Waypoint) -> None:
    """Test the initialization of a Waypoint."""
    assert waypoint.waypoint_id == "waypoint_0"
    assert waypoint.coord == Coord(0, 0)
    assert waypoint.bezier_control == (Coord(0, 10),)


def test_waypoint_equal_waypoint(waypoint: Waypoint) -> None:
    """Test equality of waypoints with the same ID and coordinates."""
    assert waypoint == Waypoint(waypoint_id="waypoint_0", coord=Coord(0, 0), bezier_control=(Coord(0, 10),))


def test_waypoint_equal_unqual_waypoint(waypoint: Waypoint) -> None:
    """Test inequality of waypoints with different IDs and coordinates."""
    assert waypoint != Waypoint(waypoint_id="waypoint_1", coord=Coord(1, 0), bezier_control=(Coord(0, 10),))


def test_waypoint_equal_different_type(waypoint: Waypoint) -> None:
    """Test inequality of waypoint with a different type."""
    assert waypoint != "waypoint_0"


def test_segment_length_no_bezier() -> None:
    """Test segment length calculation without bezier control points."""
    waypoint_0 = Waypoint(waypoint_id="waypoint_0", coord=Coord(0, 0))
    waypoint_1 = Waypoint(waypoint_id="waypoint_1", coord=Coord(10, 0))
    segment = Segment(waypoint_0, waypoint_1, find_length_of_line(waypoint_0.coord, waypoint_1.coord))
    line_length = 10
    assert segment.distance == line_length


def test_segment_length_bezier() -> None:
    """Test segment length calculation with bezier control points."""
    waypoint_0 = Waypoint(waypoint_id="waypoint_0", coord=Coord(0, 0), bezier_control=(Coord(5, 5),))
    waypoint_1 = Waypoint(waypoint_id="waypoint_1", coord=Coord(10, 0), bezier_control=(Coord(10, 10),))
    segment = Segment(
        waypoint_0,
        waypoint_1,
        find_length_of_bezier_curve(waypoint_0.coord, waypoint_0.bezier_control, waypoint_1.coord),  # type: ignore[arg-type]
    )
    bezier_length = 12.70820393249937
    assert segment.distance == bezier_length


def test_segment_is_hashable() -> None:
    """Test that a Segment instance is hashable."""
    waypoint_0 = Waypoint(waypoint_id="waypoint_0", coord=Coord(0, 0))
    waypoint_1 = Waypoint(waypoint_id="waypoint_1", coord=Coord(10, 0))
    segment = Segment(waypoint_0, waypoint_1, find_length_of_line(waypoint_0.coord, waypoint_1.coord))
    assert hash(segment) == hash((waypoint_0, waypoint_1))


def test_segment_equal_segment() -> None:
    """Test equality of segments with the same waypoints and distance."""
    waypoint_0 = Waypoint(waypoint_id="waypoint_0", coord=Coord(0, 0))
    waypoint_1 = Waypoint(waypoint_id="waypoint_1", coord=Coord(10, 0))
    segment = Segment(waypoint_0, waypoint_1, find_length_of_line(waypoint_0.coord, waypoint_1.coord))
    assert segment == Segment(waypoint_0, waypoint_1, find_length_of_line(waypoint_0.coord, waypoint_1.coord))


def test_segment_equal_incorrect_type() -> None:
    """Test inequality of segment with a different type."""
    waypoint_0 = Waypoint(waypoint_id="waypoint_0", coord=Coord(0, 0))
    waypoint_1 = Waypoint(waypoint_id="waypoint_1", coord=Coord(10, 0))
    segment = Segment(waypoint_0, waypoint_1, find_length_of_line(waypoint_0.coord, waypoint_1.coord))
    assert segment != "segment"


def test_path_init() -> None:
    """Test the initialization of a Path."""
    p = Path("path_0")
    assert p.path_id == "path_0"
    assert p.speed == 1
    assert p.ease is None
    assert p.layer is None
    assert p.hold_time == 0
    assert p.loop is False
    assert p.segments == []
    assert p.waypoints == []
    assert p.waypoint_lookup == {}
    assert p.total_distance == 0
    assert p.current_step == 0
    assert p.max_steps == 0
    assert p.hold_time_remaining == 0
    assert p.last_distance_reached == 0
    assert p.origin_segment is None


def test_path_init_invalid_speed() -> None:
    """Test initialization of a Path with invalid speed."""
    with pytest.raises(PathInvalidSpeedError):
        Path("path_0", speed=-1)


def test_path_new_waypoint_auto_id_generation() -> None:
    """Test auto ID generation for new waypoints.

    ID's should start at 0 and increment by 1 for each new waypoint.
    """
    p = Path("p")
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0))
    assert p.waypoints[0].waypoint_id == "0"
    assert p.waypoints[1].waypoint_id == "1"


def test_path_new_waypoint_auto_id_deleted_waypoints() -> None:
    """Test auto ID generation for new waypoints after deletion.

    ID's should start at 0 and increment by 1 for each new waypoint, even if waypoints have been deleted.
    """
    # waypoint auto ID's start at 0
    p = Path("p")
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0))
    p.new_waypoint(Coord(20, 0))
    p.waypoints.pop(-1)
    new_waypoint = p.new_waypoint(Coord(30, 0))
    assert new_waypoint.waypoint_id == "3"


def test_path_new_waypoint_duplicate_waypoint_id() -> None:
    """Test that creating a waypoint with a duplicate ID raises an error."""
    p = Path("p")
    p.new_waypoint(Coord(0, 0), waypoint_id="0")
    with pytest.raises(DuplicateWaypointIDError):
        p.new_waypoint(Coord(10, 0), waypoint_id="0")


def test_path_new_waypoint_bezier_as_single_coord() -> None:
    """Test that a single coordinate can be used as a bezier control point."""
    p = Path("p")
    p.new_waypoint(Coord(0, 0), bezier_control=Coord(0, 10))
    assert p.waypoints[0].bezier_control == (Coord(0, 10),)


def test_path_new_waypoint_bezier_as_tuple() -> None:
    """Test that a tuple can be used as bezier control points."""
    p = Path("p")
    p.new_waypoint(Coord(0, 0), bezier_control=(Coord(0, 10),))
    assert p.waypoints[0].bezier_control == (Coord(0, 10),)


def test_path_new_waypoint_multiple_waypoints_with_bezier_segment() -> None:
    """Test multiple waypoints with bezier segments."""
    p = Path("p")
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0), bezier_control=Coord(10, 10))
    assert p.segments[0].distance == find_length_of_bezier_curve(Coord(0, 0), Coord(10, 10), Coord(10, 0))


def test_path_query_waypoint_valid_waypoint() -> None:
    """Test querying an existing waypoint ID in a path."""
    p = Path("p")
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0))
    assert p.query_waypoint("0") == p.waypoints[0]


def test_path_query_waypoint_invalid_waypoint() -> None:
    """Test querying a non-existing waypoint ID in a path."""
    p = Path("p")
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0))
    with pytest.raises(WaypointNotFoundError):
        p.query_waypoint("2")


def test_path_step_zero_distance(character: EffectCharacter) -> None:
    """Test stepping through a path with zero distance."""
    p = Path("p")
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(0, 0))
    assert p.step(character.event_handler) == Coord(0, 0)


def test_path_step_single_segment(character: EffectCharacter) -> None:
    """Test stepping through a single segment path."""
    p = Path("p")
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0))
    current_point = p.step(character.event_handler)
    while current_point != Coord(10, 0):
        current_point = p.step(character.event_handler)


def test_path_step_single_segment_eased(character: EffectCharacter) -> None:
    """Test stepping through a single segment path with easing."""
    p = Path("p", ease=easing.in_out_sine)
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0))
    current_point = p.step(character.event_handler)
    while current_point != Coord(10, 0):
        current_point = p.step(character.event_handler)


def test_path_step_multiple_segments(character: EffectCharacter) -> None:
    """Test stepping through a path with multiple segments."""
    p = Path("p")
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0))
    p.new_waypoint(Coord(10, 10))
    p.new_waypoint(Coord(0, 10))
    current_point = p.step(character.event_handler)
    while current_point != Coord(0, 10):
        current_point = p.step(character.event_handler)


def test_path_step_multiple_segments_eased(character: EffectCharacter) -> None:
    """Test stepping through a path with multiple segments and easing."""
    p = Path("p", ease=easing.in_out_elastic)
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0))
    p.new_waypoint(Coord(10, 10))
    p.new_waypoint(Coord(0, 10))
    current_point = p.step(character.event_handler)
    while current_point != Coord(0, 10):
        current_point = p.step(character.event_handler)


def test_path_step_multiple_segments_zero_distance(character: EffectCharacter) -> None:
    """Test stepping through a path with multiple segments and zero distance."""
    p = Path("p")
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(0, 0))
    current_point = p.step(character.event_handler)
    while current_point != Coord(0, 0):
        current_point = p.step(character.event_handler)


def test_path_step_multiple_segments_mutiple_bezier(character: EffectCharacter) -> None:
    """Test stepping through a path with multiple segments and multiple bezier control points."""
    p = Path("p")
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0), bezier_control=Coord(10, 10))
    p.new_waypoint(Coord(10, 10), bezier_control=Coord(0, 10))
    p.new_waypoint(Coord(0, 10), bezier_control=Coord(0, 0))
    current_point = p.step(character.event_handler)
    while current_point != Coord(0, 10):
        current_point = p.step(character.event_handler)


def test_path_equality() -> None:
    """Test equality of paths with the same waypoints."""
    p1 = Path("p")
    p1.new_waypoint(Coord(0, 0))
    p1.new_waypoint(Coord(10, 0))
    p1.new_waypoint(Coord(10, 10))
    p1.new_waypoint(Coord(0, 10))

    p2 = Path("p")
    p2.new_waypoint(Coord(0, 0))
    p2.new_waypoint(Coord(10, 0))
    p2.new_waypoint(Coord(10, 10))
    p2.new_waypoint(Coord(0, 10))

    assert p1 == p2


def test_path_equality_invalid_type() -> None:
    """Test inequality of path with a different type."""
    p = Path("p")
    assert p != "p"


def test_motion_set_coordinate(character: EffectCharacter) -> None:
    """Test setting the coordinate of a character."""
    character.motion.set_coordinate(Coord(10, 10))
    assert character.motion.current_coord == Coord(10, 10)


def test_motion_new_path_duplicate_path_id(character: EffectCharacter) -> None:
    """Test creating a new path with a duplicate ID raises an error."""
    character.motion.new_path(path_id="0")
    with pytest.raises(DuplicatePathIDError):
        character.motion.new_path(path_id="0")


def test_motion_new_path_auto_id_avoid_duplicate(character: EffectCharacter) -> None:
    """Test auto ID generation for new paths avoiding duplicates."""
    character.motion.new_path(path_id="1")
    character.motion.new_path(path_id="2")
    character.motion.new_path(path_id="3")
    new_path = character.motion.new_path()
    assert new_path.path_id == "4"


def test_motion_query_path_valid_path(character: EffectCharacter) -> None:
    """Test querying an existing path ID."""
    character.motion.new_path(path_id="0")
    character.motion.new_path(path_id="1")
    assert character.motion.query_path("0").path_id == "0"


def test_motion_query_path_invalid_path(character: EffectCharacter) -> None:
    """Test querying a non-existing path ID raises an error."""
    character.motion.new_path(path_id="0")
    character.motion.new_path(path_id="1")
    with pytest.raises(PathNotFoundError):
        character.motion.query_path("2")


def test_motion_movement_is_complete_no_active_paths(character: EffectCharacter) -> None:
    """Test checking if movement is complete with no active paths."""
    assert character.motion.movement_is_complete() is True


def test_motion_movement_is_complete_active_path_complete(character: EffectCharacter) -> None:
    """Test checking if movement is complete with an active path that is complete."""
    p = character.motion.new_path(path_id="0")
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0))
    character.motion.activate_path(p)
    while character.motion.active_path:
        character.motion.move()

    assert character.motion.movement_is_complete() is True


def test_motion_movement_is_complete_active_path_incomplete(character: EffectCharacter) -> None:
    """Test checking if movement is complete with an active path that is incomplete."""
    p = character.motion.new_path(path_id="0")
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0))
    character.motion.activate_path(p)

    assert character.motion.movement_is_complete() is False


def test_motion_chain_paths_single_path(character: EffectCharacter) -> None:
    """Test chaining a single path."""
    p = character.motion.new_path(path_id="0")
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0))
    character.motion.chain_paths(
        [
            p,
        ],
    )


def test_motion_chain_paths_multiple_paths(character: EffectCharacter) -> None:
    """Test chaining multiple paths."""
    p1 = character.motion.new_path(path_id="0")
    p1.new_waypoint(Coord(0, 0))
    p1.new_waypoint(Coord(10, 0))

    p2 = character.motion.new_path(path_id="1")
    p2.new_waypoint(Coord(10, 0))
    p2.new_waypoint(Coord(10, 10))

    character.motion.chain_paths([p1, p2])
    assert (EventHandler.Event.PATH_COMPLETE, p1) in character.event_handler.registered_events
    assert character.event_handler.registered_events[(EventHandler.Event.PATH_COMPLETE, p1)] == [
        (EventHandler.Action.ACTIVATE_PATH, p2),
    ]


def test_motion_chain_paths_multiple_paths_looping(character: EffectCharacter) -> None:
    """Test chaining multiple paths with looping."""
    p1 = character.motion.new_path(path_id="0")
    p1.new_waypoint(Coord(0, 0))
    p1.new_waypoint(Coord(10, 0))

    p2 = character.motion.new_path(path_id="1")
    p2.new_waypoint(Coord(10, 0))
    p2.new_waypoint(Coord(10, 10))

    character.motion.chain_paths([p1, p2], loop=True)
    assert (EventHandler.Event.PATH_COMPLETE, p1) in character.event_handler.registered_events
    assert character.event_handler.registered_events[(EventHandler.Event.PATH_COMPLETE, p1)] == [
        (EventHandler.Action.ACTIVATE_PATH, p2),
    ]
    assert (EventHandler.Event.PATH_COMPLETE, p2) in character.event_handler.registered_events
    assert character.event_handler.registered_events[(EventHandler.Event.PATH_COMPLETE, p2)] == [
        (EventHandler.Action.ACTIVATE_PATH, p1),
    ]


def test_motion_activate_path_first_waypoint_bezier(character: EffectCharacter) -> None:
    """Test activating a path with the first waypoint having a bezier control point."""
    p = character.motion.new_path(path_id="0")
    p.new_waypoint(Coord(0, 0), bezier_control=Coord(0, 10))
    p.new_waypoint(Coord(10, 0))
    character.motion.activate_path(p)
    assert character.motion.active_path == p


def test_motion_activate_path_no_waypoints(character: EffectCharacter) -> None:
    """Test activating a path with no waypoints raises an error."""
    p = character.motion.new_path(path_id="0")
    with pytest.raises(ActivateEmptyPathError):
        character.motion.activate_path(p)


def test_motion_active_path_with_layer(character: EffectCharacter) -> None:
    """Test activating a path with a layer."""
    p = character.motion.new_path(path_id="0", layer=1)
    p.new_waypoint(Coord(0, 0), bezier_control=Coord(0, 10))
    p.new_waypoint(Coord(10, 0))
    character.motion.activate_path(p)
    assert character.motion.active_path == p
    assert character.layer == 1


def test_motion_activate_path_previously_deactivated(character: EffectCharacter) -> None:
    """Test reactivating a path that was previously deactivated."""
    character.motion.set_coordinate(Coord(5, 5))
    p = character.motion.new_path(path_id="0")
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0))
    character.motion.activate_path(p)
    first_origin_distance = p.origin_segment.distance if p.origin_segment else 0
    character.motion.deactivate_path(p)
    character.motion.set_coordinate(Coord(2, 2))
    character.motion.activate_path(p)
    second_origin_distance = p.origin_segment.distance if p.origin_segment else 0
    assert character.motion.active_path == p
    assert second_origin_distance < first_origin_distance


def test_motion_move_no_active_path(character: EffectCharacter) -> None:
    """Test moving a character with no active path."""
    assert character.motion.active_path is None
    character.motion.move()


def test_motion_move_path_hold_time(character: EffectCharacter) -> None:
    """Test moving a character along a path with hold time."""
    p = character.motion.new_path(path_id="0", hold_time=5)
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0))
    character.motion.activate_path(p)
    character.motion.move()
    while character.motion.active_path:
        character.motion.move()
    assert character.motion.active_path is None


def test_motion_move_path_looping(character: EffectCharacter) -> None:
    """Test moving a character along a looping path."""
    p = character.motion.new_path(path_id="0", loop=True)
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0))
    p.new_waypoint(Coord(10, 10))
    character.motion.activate_path(p)
    for _ in range(100):
        character.motion.move()
