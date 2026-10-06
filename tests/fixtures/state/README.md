# Test fixture state

Synthetic articles for CI's site build and `tests/browser-smoke.cjs`.
The real article and learning data moved to the private `newsroom-themes`
repository (docs/migration-handoff.md, Gate 3), so CI builds the reader
from these instead:

    NEWSROOM_CONFIG_DIR=themes/example NEWSROOM_STATE_DIR=tests/fixtures/state python scripts/build_site.py

Every article here is made up. URLs use the reserved `.test` domain.
