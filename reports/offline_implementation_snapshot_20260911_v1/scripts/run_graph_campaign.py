from __future__ import annotations

import argparse
import json
from pathlib import Path

from language_nav.benchmark import CorruptionEngine, build_corpus
from language_nav.evaluation.campaign import summarize_campaign
from language_nav.runner import ImmutableJsonlWriter, PairedCampaign
from language_nav.systems import build_central_variants


def main() -> None:
    parser = argparse.ArgumentParser(description="Run paired Protocol 1.0 graph-world episodes")
    parser.add_argument("--partition", choices=("development", "validation", "held_out"), default="development")
    parser.add_argument("--routes", type=int, default=2)
    parser.add_argument("--seeds", type=int, default=2)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--allow-protected",
        action="store_true",
        help="explicitly authorize held-out execution after all confirmatory gates pass",
    )
    args = parser.parse_args()
    if args.routes < 1 or args.seeds < 1:
        parser.error("--routes and --seeds must be positive")
    if args.partition == "held_out" and not args.allow_protected:
        parser.error("held_out is protected; pass --allow-protected only after confirmatory gates")

    routes = tuple(route for route in build_corpus() if route.partition == args.partition)[: args.routes]
    generated = tuple(
        variant
        for route in routes
        for variant in CorruptionEngine().generate_all(route, seed=0)
    )
    records = PairedCampaign().run(routes, generated, build_central_variants(), tuple(range(args.seeds)))
    with ImmutableJsonlWriter(args.output) as writer:
        for record in records:
            writer.write(record)
    summary_path = args.output.with_suffix(".summary.json")
    with summary_path.open("x", encoding="utf-8") as handle:
        json.dump(summarize_campaign(records), handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({"episodes": len(records), "log": str(args.output), "summary": str(summary_path)}))


if __name__ == "__main__":
    main()
