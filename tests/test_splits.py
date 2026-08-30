import pytest

from language_nav.benchmark.splits import SplitRecord, assert_split_integrity


def _record(partition: str, suffix: str, author: str) -> SplitRecord:
    return SplitRecord(partition, f"map-{suffix}", f"route-{suffix}", f"base-{suffix}", author, f"template-{suffix}")


def test_disjoint_split_manifest_passes() -> None:
    assert_split_integrity([_record("development", "d", "authors-d"), _record("test", "t", "authors-t")])


def test_author_style_leakage_fails() -> None:
    with pytest.raises(ValueError, match="author_group"):
        assert_split_integrity([_record("development", "d", "shared"), _record("test", "t", "shared")])

