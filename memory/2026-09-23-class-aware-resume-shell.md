# Resume shell must be explicit

The workspace default exec shell is Zsh. Sourcing ROS `.bash` setup from it can
print missing setup-file warnings and leave stale AMENT paths while still
continuing. That caused two retained class-aware pilot infrastructure failures
after a GPU-only pre-dispatch pause. Do not repeat them or classify as nondetection.

Use `bash scripts/launch_class_aware_pilot.sh`, not inline source commands in the
default shell. The new wrapper exits on setup errors, imports the live module,
checks both actual launch paths and verifies unchanged source bindings before
dispatch. The correct overlay is `ros_ws/install/setup.bash`, never the stale
root `install/setup.bash`. All raw failures and the additional wrapper binding
remain in `reports/class_aware_acquisition_pilot_20260923_v1/`.
