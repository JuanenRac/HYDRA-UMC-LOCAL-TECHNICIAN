<!-- =============================================================================
HYDRA-UMC-LOCAL-TECHNICIAN - Maturity exit criteria
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

# Maturity criteria

This project is labelled `functional` as a read-only diagnostic CLI. The items
below are the criteria for the next level; an item is checked only when it is
true and verifiable in the repository (a test, a CI check or a reproducible
command) - not when the code merely exists. The outbox and the diagnostic mode
exist as code but nothing is wired to them yet, so they stay unchecked.

- [x] An incident contract defines the minimum evidence, the human approval step and the allowed actions.
- [ ] Patching or updating is refused without an approved, signed policy - covered by a test.
- [ ] A local queue survives a network outage and replays without duplicating actions.
- [ ] A diagnostics-only mode exists and provably takes no action.

Verified on real hardware or services is a separate, later step: a passing
software check does not certify physical behaviour.
