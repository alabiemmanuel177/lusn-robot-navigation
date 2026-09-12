#!/usr/bin/env python3
"""Create a camera-palette-adapted runtime landmark catalogue."""
from __future__ import annotations

import argparse
from pathlib import Path

from language_nav.adapters.landmark_palette import adapt_scene_palette


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    count = adapt_scene_palette(args.scene, args.output, args.profile)
    print(f"prepared {args.output} with {count} camera-space landmark codes")


if __name__ == "__main__":
    main()
