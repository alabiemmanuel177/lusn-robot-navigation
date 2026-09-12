# Research 3 portable reviewer kit v1

Download `research3_reviewer_kit_v1.zip`, extract it, and follow the included
`README.md`. Do not use GitHub's automatically generated source-code ZIP as the
review kit. The attached kit is self-contained; its bundled source/evidence
manifest identifies its contents independently of the release tag's Git commit.

The kit contains 60 review targets from 46 nonprotected captures, proposed rules
and an accept/revise/reject form, a localhost review application, and a command
to create a small return ZIP. Python 3.10+, Pillow and PyYAML are required; ROS,
Gazebo, GPUs and the Research 1/2 repositories are not required.

An authorized human must approve or revise the rules before saving observation
judgments. No human approvals or labels have been generated. This prerelease is
review preparation, not a completed study or approved calibration. Existing 60
targets may not satisfy the proposed coverage requirements.

Return the generated review ZIP to the researcher through the agreed private
channel. It contains reviewer names, dates, notes and judgments. Do not post it
publicly. Hash checks detect changes, not impersonation.

SHA-256 of the reviewer ZIP:
`8146bdfac814a382e696af53b15130554cd74a6cb164fd0b23bcfa76b89d83bd`

Verification: 793 Python tests passed, one sandbox socket skip; extracted-kit
relocation and actual localhost HTTP checks passed on Linux. Windows/macOS and
a clean dependency installation have not been tested.

This repository remains private. Reviewers must sign in to GitHub with an account
that has access to this repository to download the assets.
