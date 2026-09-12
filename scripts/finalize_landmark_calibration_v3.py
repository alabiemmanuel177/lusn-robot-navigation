#!/usr/bin/env python3
"""Rejected v3 finalizer retained only to fail closed."""


def main() -> None:
    raise SystemExit(
        "v3 review is excluded: cuboid landmarks and rectangular distractors made "
        "semantic identity ambiguous; use finalize_landmark_calibration_v5.py"
    )


if __name__ == "__main__":
    main()
