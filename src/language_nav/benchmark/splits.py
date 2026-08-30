from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class SplitRecord:
    partition: str
    map_id: str
    route_id: str
    base_instruction_id: str
    author_group: str
    template_family: str


def assert_split_integrity(records: list[SplitRecord]) -> None:
    """Reject forbidden map/route/instruction/style families crossing splits."""
    if not records:
        raise ValueError("split manifest must not be empty")
    dimensions = ("map_id", "route_id", "base_instruction_id", "author_group", "template_family")
    violations: list[str] = []
    for dimension in dimensions:
        partitions_by_value: dict[str, set[str]] = defaultdict(set)
        for record in records:
            partitions_by_value[getattr(record, dimension)].add(record.partition)
        for value, partitions in partitions_by_value.items():
            if len(partitions) > 1:
                violations.append(f"{dimension}={value!r} crosses {sorted(partitions)}")
    if violations:
        raise ValueError("split leakage: " + "; ".join(violations))

