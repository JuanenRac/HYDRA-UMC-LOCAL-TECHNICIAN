# Bench tests

Every test below is **not executed**. The default configuration of the orchestrator (`default_config()` in `orchestrator/allowlist.py`) describes a Compute Module 5 installation; it has been checked against files and tests, never against a real installation. Write a result only after a person ran the step.

## What the software already covers (no board needed)

- The unit tests check the allow-list rules, the evidence bundle, the signed outbox and the runbooks against temporary folders.

## Setup

- A Compute Module 5 installed with the HYDRA-UMC programs in their default places, and a shell on it as the user that will run the technician.

## Steps

| # | Step | Expected result | Result |
|---|------|-----------------|--------|
| 1 | Print the default configuration and compare every path, unit name and command with what exists on the board. | Each entry exists; list the ones that do not. | not executed |
| 2 | Run one allowed action for each entry of the allow-list in dry-run mode. | Each is accepted and nothing changes. | not executed |
| 3 | Try an action outside the list and a path outside the allowed folders. | Both refused. | not executed |
| 4 | Collect an evidence bundle on the board and verify it on another machine. | The checksum verifies and no secret is inside. | not executed |

## What this bench cannot show

Installations that differ from the default layout; run step 1 again on each.
