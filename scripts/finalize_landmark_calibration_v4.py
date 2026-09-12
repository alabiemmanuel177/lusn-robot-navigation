#!/usr/bin/env python3
"""Rejected v4 pilot finalizer retained only to fail closed."""


def main() -> None:
    raise SystemExit(
        "v4 was rejected by pre-review visual audit because the sign sphere was clipped; "
        "use finalize_landmark_calibration_v5.py"
    )


if __name__ == "__main__":
    main()
