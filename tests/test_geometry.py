import math

from language_nav.geometry import relation_holds


def test_relations_match_hand_computed_east_facing_fixture() -> None:
    anchor = (2.0, 2.0)
    assert relation_holds("after", (3.0, 2.0), anchor, reference_heading_rad=0.0)
    assert relation_holds("before", (1.0, 2.0), anchor, reference_heading_rad=0.0)
    assert relation_holds("left_of", (2.0, 3.0), anchor, reference_heading_rad=0.0)
    assert relation_holds("right_of", (2.0, 1.0), anchor, reference_heading_rad=0.0)
    assert relation_holds("near", (2.3, 2.4), anchor, near_tolerance=0.5)


def test_relations_rotate_with_reference_frame() -> None:
    anchor = (0.0, 0.0)
    assert relation_holds("after", (0.0, 2.0), anchor, reference_heading_rad=math.pi / 2)
    assert relation_holds("right_of", (2.0, 0.0), anchor, reference_heading_rad=math.pi / 2)

