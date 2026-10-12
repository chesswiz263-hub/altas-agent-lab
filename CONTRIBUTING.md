# Contributing to ATLAS

1. Fork and create a feature branch.
2. Install `pip install -e '.[dev]'`.
3. Add or update focused unit/integration tests for each behavioral change.
4. Run `ruff check src tests` and `pytest -q` locally.
5. Keep provider credentials out of commits, logs, fixtures and screenshots.
6. Explain tradeoffs and tests in your pull request. If proposing a new tool, document why its permissions and limits are safe.

For major changes, open a design issue describing motivation, impact on the canonical provider interface, backwards compatibility, and evaluation method.
