#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from language_nav.benchmark import load_semantic_route_catalog


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a semantic catalogue against Research 1")
    parser.add_argument("catalog", type=Path)
    parser.add_argument("--research1", type=Path, default=Path("/home/eao/risk-calibrated-nav"))
    parser.add_argument("--allow-protected", action="store_true")
    args = parser.parse_args()
    catalog = load_semantic_route_catalog(
        args.catalog, args.research1, allow_protected=args.allow_protected
    )
    print(json.dumps({
        "schema_version": catalog.schema_version,
        "map_id": catalog.map_id,
        "partition": catalog.partition,
        "routes": len(catalog.routes),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
