# ATLAS engineering roadmap

## Completed: v0.1–v0.3

- Model-agnostic gateway and deterministic offline demo, bounded ReAct execution, tools and persistent traces.
- Sequential four-role team, FTS5 search, hashed n-gram lexical hybrid, operator-defined price estimates.
- Optional genuine neural embeddings with a small-corpus exact cosine scan (not ANN), semantic-hybrid fusion.
- Explainable rule-based router, per-claim citation checks and numeric mismatch warnings.

## Completed: v0.4

- Durable SQLite queued jobs with a single async worker, event-cursor polling and cancellation.
- Restart resilience: queued items persist, in-flight items are marked interrupted without replaying paid requests.
- Optional single-operator API bearer token (not production identity/authorization).
- User-authored, local notes with explicit opt-in retrieval during queued jobs.
- Isolated, ten-case human-labeled evidence-surface calibration confusion matrix.
- Queue, memory and calibration UI with regression and contract tests.

## v0.5 candidates

- Explicit per-run deadlines, jittered retry classification for known safe/idempotent actions, provider quota/backoff.
- Queue maintenance endpoints, retention/compaction, exportable telemetry, resource and concurrency guards.
- Human review dataset with independently labeled entailment/counterexample cases; abstention calibration.
- Live model compatibility smoke tests behind explicit spending ceilings.

## v1.0 requirements before open deployment

- Real OAuth/OIDC authentication, RBAC, rate limiting, tenant boundaries and separated data storage.
- PostgreSQL + dedicated external worker service, leases, recovery policy, distributed coordination.
- ANN-backed vector search with measured recall/latency and embedding-cache reindex strategy.
- Timeouts, structured redacted tracing, egress policies, secret rotation, abuse controls and documented backups.
- TLS/secure proxy, environment hardening, request admission budgets, audit retention and privacy controls.


## Public demo (v0.6 shipped)
- [x] Browser-only sample-retrieval and deterministic audit UI
- [x] GitHub Pages deploy-from-branch `/docs` layout
- [x] Sample-only corpus; no API credentials, user uploads, or private data
- [x] Documented distinction between illustrative flow and real model-based reasoning
- [ ] Independent visitor testing after the user enables Pages
- [ ] Hosted general-purpose AI mode with isolated per-user backend (future milestone, not part of v0.6)
