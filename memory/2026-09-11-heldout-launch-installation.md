# New launch-file installation check

The three-package R3 overlay build exposed an installed colcon `symlink_data.py`
edge case: the force branch checked an existing destination directory and attempted
to remove a new launch-file target that did not yet exist. No system tool, Research 1
or Research 2 source was edited.

A temporary, task-owned generated placeholder was tried. A later nominally successful
build retained that placeholder because of its newer timestamp. Independent source
and installed-file SHA checks caught this; nominal build success was not accepted
as deployment verification. Making the placeholder older then exposed the existing
regular-file/symlink conflict. Only our placeholder was deleted, and rebuilding the
bringup package in the settled symlink installation mode succeeded.

The final installed `heldout_adapters.launch.py` and its source both hashed to
`f6b5d5a0031b1408ba6e42ed9e69439f76bb5bf9ceba5bebc36b5bcf5f85a368`.
ROS package tests reported seven tests with zero errors, failures, or skips. This
verifies installation and non-live package checks; it is not a held-out experiment.

Subsequent checks should again verify actual installed bytes, not infer freshness
from the build command's exit status alone.
