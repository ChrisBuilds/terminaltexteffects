import pytest

from terminaltexteffects.engine.base_character import EffectCharacter, EventHandler
from terminaltexteffects.engine.motion import Path, Segment, Waypoint
from terminaltexteffects.utils import easing
from terminaltexteffects.utils.geometry import Coord, find_length_of_bezier_curve, find_length_of_line

pytestmark = [pytest.mark.engine, pytest.mark.motion, pytest.mark.smoke]


@pytest.fixture
def character() -> EffectCharacter:
    return EffectCharacter(0, "a", 0, 0)


@pytest.fixture
def waypoint() -> Waypoint:
    return Waypoint(waypoint_id="waypoint_0", coord=Coord(0, 0), bezier_control=(Coord(0, 10),))


def test_waypoint_init(waypoint: Waypoint) -> None:
    assert waypoint.waypoint_id == "waypoint_0"
    assert waypoint.coord == Coord(0, 0)
    assert waypoint.bezier_control == (Coord(0, 10),)


def test_waypoint_equal_waypoint(waypoint: Waypoint) -> None:
    assert waypoint == Waypoint(waypoint_id="waypoint_0", coord=Coord(0, 0), bezier_control=(Coord(0, 10),))


def test_waypoint_equal_unqual_waypoint(waypoint: Waypoint) -> None:
    assert waypoint != Waypoint(waypoint_id="waypoint_1", coord=Coord(1, 0), bezier_control=(Coord(0, 10),))


def test_waypoint_equal_different_type(waypoint: Waypoint) -> None:
    assert waypoint != "waypoint_0"


def test_segment_length_no_bezier() -> None:
    waypoint_0 = Waypoint(waypoint_id="waypoint_0", coord=Coord(0, 0))
    waypoint_1 = Waypoint(waypoint_id="waypoint_1", coord=Coord(10, 0))
    segment = Segment(waypoint_0, waypoint_1, find_length_of_line(waypoint_0.coord, waypoint_1.coord))
    assert segment.distance == 10


def test_segment_length_bezier() -> None:
    waypoint_0 = Waypoint(waypoint_id="waypoint_0", coord=Coord(0, 0), bezier_control=(Coord(5, 5),))
    waypoint_1 = Waypoint(waypoint_id="waypoint_1", coord=Coord(10, 0), bezier_control=(Coord(10, 10),))
    segment = Segment(
        waypoint_0,
        waypoint_1,
        find_length_of_bezier_curve(waypoint_0.coord, waypoint_0.bezier_control, waypoint_1.coord),  # type: ignore
    )
    assert segment.distance == 10.242640687119286


def test_segment_is_hashable() -> None:
    waypoint_0 = Waypoint(waypoint_id="waypoint_0", coord=Coord(0, 0))
    waypoint_1 = Waypoint(waypoint_id="waypoint_1", coord=Coord(10, 0))
    segment = Segment(waypoint_0, waypoint_1, find_length_of_line(waypoint_0.coord, waypoint_1.coord))
    assert hash(segment) == hash((waypoint_0, waypoint_1))


def test_segment_equal_segment() -> None:
    waypoint_0 = Waypoint(waypoint_id="waypoint_0", coord=Coord(0, 0))
    waypoint_1 = Waypoint(waypoint_id="waypoint_1", coord=Coord(10, 0))
    segment = Segment(waypoint_0, waypoint_1, find_length_of_line(waypoint_0.coord, waypoint_1.coord))
    assert segment == Segment(waypoint_0, waypoint_1, find_length_of_line(waypoint_0.coord, waypoint_1.coord))


def test_segment_equal_incorrect_type() -> None:
    waypoint_0 = Waypoint(waypoint_id="waypoint_0", coord=Coord(0, 0))
    waypoint_1 = Waypoint(waypoint_id="waypoint_1", coord=Coord(10, 0))
    segment = Segment(waypoint_0, waypoint_1, find_length_of_line(waypoint_0.coord, waypoint_1.coord))
    assert segment != "segment"


def test_path_init() -> None:
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
    with pytest.raises(ValueError):
        Path("path_0", speed=-1)


def test_path_new_waypoint_auto_id_generation() -> None:
    p = Path("p")
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0))
    assert p.waypoints[0].waypoint_id == "0"
    assert p.waypoints[1].waypoint_id == "1"


def test_path_new_waypoint_auto_id_deleted_waypoints() -> None:
    # waypoint auto ID's start at 0
    p = Path("p")
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0))
    p.new_waypoint(Coord(20, 0))
    p.waypoints.pop(-1)
    new_waypoint = p.new_waypoint(Coord(30, 0))
    assert new_waypoint.waypoint_id == "3"


def test_path_new_waypoint_bezier_as_single_coord() -> None:
    p = Path("p")
    p.new_waypoint(Coord(0, 0), bezier_control=Coord(0, 10))
    assert p.waypoints[0].bezier_control == (Coord(0, 10),)


def test_path_new_waypoint_bezier_as_tuple() -> None:
    p = Path("p")
    p.new_waypoint(Coord(0, 0), bezier_control=(Coord(0, 10),))
    assert p.waypoints[0].bezier_control == (Coord(0, 10),)


def test_path_new_waypoint_multiple_waypoints_with_bezier_segment() -> None:
    p = Path("p")
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0), bezier_control=Coord(10, 10))
    assert p.segments[0].distance == find_length_of_bezier_curve(Coord(0, 0), Coord(10, 10), Coord(10, 0))


def test_path_query_waypoint_valid_waypoint() -> None:
    p = Path("p")
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0))
    assert p.query_waypoint("0") == p.waypoints[0]


def test_path_query_waypoint_invalid_waypoint() -> None:
    p = Path("p")
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0))
    with pytest.raises(ValueError):
        p.query_waypoint("2")


def test_path_step_zero_distance(character: EffectCharacter) -> None:
    p = Path("p")
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(0, 0))
    assert p.step(character.event_handler) == Coord(0, 0)


def test_path_step_single_segment(character: EffectCharacter) -> None:
    p = Path("p")
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0))
    current_point = p.step(character.event_handler)
    while current_point != Coord(10, 0):
        current_point = p.step(character.event_handler)


def test_path_step_single_segment_eased(character: EffectCharacter) -> None:
    p = Path("p", ease=easing.in_out_sine)
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0))
    current_point = p.step(character.event_handler)
    while current_point != Coord(10, 0):
        current_point = p.step(character.event_handler)


def test_path_step_multiple_segments(character: EffectCharacter) -> None:
    p = Path("p")
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0))
    p.new_waypoint(Coord(10, 10))
    p.new_waypoint(Coord(0, 10))
    current_point = p.step(character.event_handler)
    while current_point != Coord(0, 10):
        current_point = p.step(character.event_handler)


def test_path_step_multiple_segments_eased(character: EffectCharacter) -> None:
    p = Path("p", ease=easing.in_out_elastic)
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0))
    p.new_waypoint(Coord(10, 10))
    p.new_waypoint(Coord(0, 10))
    current_point = p.step(character.event_handler)
    while current_point != Coord(0, 10):
        current_point = p.step(character.event_handler)


def test_path_step_multiple_segments_zero_distance(character: EffectCharacter) -> None:
    p = Path("p")
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(0, 0))
    current_point = p.step(character.event_handler)
    while current_point != Coord(0, 0):
        current_point = p.step(character.event_handler)


def test_path_step_multiple_segments_mutiple_bezier(character: EffectCharacter) -> None:
    p = Path("p")
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0), bezier_control=Coord(10, 10))
    p.new_waypoint(Coord(10, 10), bezier_control=Coord(0, 10))
    p.new_waypoint(Coord(0, 10), bezier_control=Coord(0, 0))
    current_point = p.step(character.event_handler)
    while current_point != Coord(0, 10):
        current_point = p.step(character.event_handler)


def test_path_equality() -> None:
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
    p = Path("p")
    assert p != "p"


def test_motion_set_coordinate(character: EffectCharacter) -> None:
    character.motion.set_coordinate(Coord(10, 10))
    assert character.motion.current_coord == Coord(10, 10)


def test_motion_new_path_duplicate_path_id(character: EffectCharacter) -> None:
    character.motion.new_path(id="0")
    with pytest.raises(ValueError):
        character.motion.new_path(id="0")


def test_motion_new_path_auto_id_avoid_duplicate(character: EffectCharacter) -> None:
    character.motion.new_path(id="1")
    character.motion.new_path(id="2")
    character.motion.new_path(id="3")
    new_path = character.motion.new_path()
    assert new_path.path_id == "4"


def test_motion_query_path_valid_path(character: EffectCharacter) -> None:
    character.motion.new_path(id="0")
    character.motion.new_path(id="1")
    assert character.motion.query_path("0").path_id == "0"


def test_motion_query_path_invalid_path(character: EffectCharacter) -> None:
    character.motion.new_path(id="0")
    character.motion.new_path(id="1")
    with pytest.raises(ValueError):
        character.motion.query_path("2")


def test_motion_movement_is_complete_no_active_paths(character: EffectCharacter) -> None:
    assert character.motion.movement_is_complete() is True


def test_motion_movement_is_complete_active_path_complete(character: EffectCharacter) -> None:
    p = character.motion.new_path(id="0")
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0))
    character.motion.activate_path(p)
    while character.motion.active_path:
        character.motion.move()

    assert character.motion.movement_is_complete() is True


def test_motion_movement_is_complete_active_path_incomplete(character: EffectCharacter) -> None:
    p = character.motion.new_path(id="0")
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0))
    character.motion.activate_path(p)

    assert character.motion.movement_is_complete() is False


def test_motion_chain_paths_single_path(character: EffectCharacter) -> None:
    p = character.motion.new_path(id="0")
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0))
    character.motion.chain_paths(
        [
            p,
        ]
    )


def test_motion_chain_paths_multiple_paths(character: EffectCharacter) -> None:
    p1 = character.motion.new_path(id="0")
    p1.new_waypoint(Coord(0, 0))
    p1.new_waypoint(Coord(10, 0))

    p2 = character.motion.new_path(id="1")
    p2.new_waypoint(Coord(10, 0))
    p2.new_waypoint(Coord(10, 10))

    character.motion.chain_paths([p1, p2])
    assert (EventHandler.Event.PATH_COMPLETE, p1) in character.event_handler.registered_events
    assert character.event_handler.registered_events[(EventHandler.Event.PATH_COMPLETE, p1)] == [
        (EventHandler.Action.ACTIVATE_PATH, p2)
    ]


def test_motion_chain_paths_multiple_paths_looping(character: EffectCharacter) -> None:
    p1 = character.motion.new_path(id="0")
    p1.new_waypoint(Coord(0, 0))
    p1.new_waypoint(Coord(10, 0))

    p2 = character.motion.new_path(id="1")
    p2.new_waypoint(Coord(10, 0))
    p2.new_waypoint(Coord(10, 10))

    character.motion.chain_paths([p1, p2], loop=True)
    assert (EventHandler.Event.PATH_COMPLETE, p1) in character.event_handler.registered_events
    assert character.event_handler.registered_events[(EventHandler.Event.PATH_COMPLETE, p1)] == [
        (EventHandler.Action.ACTIVATE_PATH, p2)
    ]
    assert (EventHandler.Event.PATH_COMPLETE, p2) in character.event_handler.registered_events
    assert character.event_handler.registered_events[(EventHandler.Event.PATH_COMPLETE, p2)] == [
        (EventHandler.Action.ACTIVATE_PATH, p1)
    ]


def test_motion_activate_path_first_waypoint_bezier(character: EffectCharacter) -> None:
    p = character.motion.new_path(id="0")
    p.new_waypoint(Coord(0, 0), bezier_control=Coord(0, 10))
    p.new_waypoint(Coord(10, 0))
    character.motion.activate_path(p)
    assert character.motion.active_path == p


def test_motion_activate_path_no_waypoints(character: EffectCharacter) -> None:
    p = character.motion.new_path(id="0")
    with pytest.raises(ValueError):
        character.motion.activate_path(p)


def test_motion_active_path_with_layer(character: EffectCharacter) -> None:
    p = character.motion.new_path(id="0", layer=1)
    p.new_waypoint(Coord(0, 0), bezier_control=Coord(0, 10))
    p.new_waypoint(Coord(10, 0))
    character.motion.activate_path(p)
    assert character.motion.active_path == p
    assert character.layer == 1


def test_motion_activate_path_previously_deactivated(character: EffectCharacter) -> None:
    character.motion.set_coordinate(Coord(5, 5))
    p = character.motion.new_path(id="0")
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0))
    character.motion.activate_path(p)
    if p.origin_segment:
        first_origin_distance = p.origin_segment.distance
    else:
        first_origin_distance = 0
    character.motion.deactivate_path(p)
    character.motion.set_coordinate(Coord(2, 2))
    character.motion.activate_path(p)
    if p.origin_segment:
        second_origin_distance = p.origin_segment.distance
    else:
        second_origin_distance = 0
    assert character.motion.active_path == p
    assert second_origin_distance < first_origin_distance


def test_motion_move_no_active_path(character: EffectCharacter) -> None:
    assert character.motion.active_path is None
    character.motion.move()


def test_motion_move_path_hold_time(character: EffectCharacter) -> None:
    p = character.motion.new_path(id="0", hold_time=5)
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0))
    character.motion.activate_path(p)
    character.motion.move()
    while character.motion.active_path:
        character.motion.move()
    assert character.motion.active_path is None


def test_motion_move_path_looping(character: EffectCharacter) -> None:
    p = character.motion.new_path(id="0", loop=True)
    p.new_waypoint(Coord(0, 0))
    p.new_waypoint(Coord(10, 0))
    p.new_waypoint(Coord(10, 10))
    character.motion.activate_path(p)
    for _ in range(100):
        character.motion.move()
