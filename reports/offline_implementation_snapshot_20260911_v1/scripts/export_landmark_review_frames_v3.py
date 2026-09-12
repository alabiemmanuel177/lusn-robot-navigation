#!/usr/bin/env python3
"""Export exact RGB frames for the v3 validation challenge queue."""
from export_landmark_review_frames_v2 import export_version


if __name__ == "__main__":
    export_version("v3")
