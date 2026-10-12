## [0.6.0] - 2026-10-11

- Added free, fully static GitHub Pages demo at `docs/index.html`: public research console, local BM25 retrieval, 4-step trace, exact quotation auditing, sample corpus inspector, six-case evaluation.
- Reuses verbatim passages from the three existing example knowledge documents; no paid provider, server calls, login, memory, or private backend exposed by the demo.
- Preserved all v0.5 Codespaces and authenticated workspace support in the same repository.
- Added Node browser-engine tests and integrated them into the Python-version CI matrix.
- Added public demo deployment and security documentation; bumped package/API version to 0.6.0.

# Changelog

## v0.5.0 — Browser workspace and hosted operator access

- **GitHub Codespaces:** Devcontainer auto-installs ATLAS, seeds example knowledge, launches a cloud development server and forwards port 8000 privately.
- **Hosted browser auth:** Optional fail-closed single-operator password login, signed eight-hour Secure/HttpOnly/SameSite cookies, CSRF header validation, same-origin checks, logout and rate-limited login attempts.
- **Protected surfaces:** Hosted auth gates dashboard assets, API documentation and all non-health API routes. API keys remain server-side.
- **Render Blueprint:** Paid Docker web service with persistent disk, TLS via Render, 1-worker queue and generated session signing secret.
- **Security:** CSP and browser security headers, non-default secret requirements and hosted-mode security tests.
- **Testing:** Expanded offline test suite (63 checks at the first integration pass); live hosted-provider integration and operational security audit remain outstanding.
- **Scope:** Codespaces is a private development environment; Render is a single-operator prototype deployment, not a public multi-user SaaS.


## v0.4.0 — Durable jobs, operator controls & calibration

- **New:** Persistent SQLite job queue, single async lifespan worker, run IDs shared between jobs/traces, pollable event cursors and best-effort cancellation.
- **New:** Restart recovery marks running jobs interrupted to avoid silently replaying charged model calls; queued jobs remain eligible.
- **New:** Optional `ATLAS_API_TOKEN` with constant-time bearer-token checks on protected APIs and dashboard volatile credential entry.
- **New:** Explicit memory note creation, retrieval, deletion, and opt-in inclusion in queued agent runs only. Notes are untrusted and stored locally in plaintext.
- **New:** Human-labeled citation surface-classification fixture suite with isolated temporary database, per-class precision/recall and confusion matrix; calibration UI.
- **UI:** Switch for queued vs original SSE execution, active cancellation, opt-in notes, token field and calibration controls.
- **Tests:** Regression suite extended from 45 to 55 tests, including queue restarts, mock slow-call cancellation, API auth and calibration. Live model adapters and downloaded embedding weights are not exercised by these offline tests.
- **Boundaries:** Local single-worker architecture, no public SaaS readiness, no guarantees of prepaid billing protection or truthfulness.


## v0.3.0 — Neural retrieval & evidence review

- **New:** Explicit optional SentenceTransformer encoder with lazy imports/model download; versioned/dimension-checked SQLite embeddings and bounded indexing batches.
- **New:** Pure semantic cosine and BM25 + true neural cosine RRF fusion search. Lexical hybrid from v0.2 remains distinct.
- **New:** Explainable, deterministic task routing (`/api/route` and streamed `/api/auto/stream`), including enforcement of the planned tool retrieval strategy.
- **New:** Per-claim citation validation, lexical evidence overlap, numeric mismatch flags, optional pluggable NLI and an Evidence inspector panel.
- **New:** Conditional semantic recall@5 and claim surface-alignment aggregate reporting in golden evaluations.
- **New:** Knowledge base model status, opt-in indexing control, semantic search selections, Auto execution, route trace display.
- **Testing:** Existing 37 v0.2 tests retained, new v0.3 contract tests added.
- **Scope:** Offline tests inject a fake encoder; no real model download or paid model integration was run. Model downloads are opt-in and initial load can be slow. No public SaaS hardening included.

## v0.2.0 — Multi-agent laboratory

- Four sequential role workflow with trace streaming and deterministic offline role simulations.
- Lexical hashed character n-gram hybrid retrieval (not neural embeddings).
- Operator-configurable cost estimates, retrieval/citation comparisons, and a dashboard run-mode selector.

## v0.1.0 — Foundation

- Local SQLite/FTS5 knowledge system, bounded agent loop, model adapters, FastAPI SSE dashboard, tests and Docker.
