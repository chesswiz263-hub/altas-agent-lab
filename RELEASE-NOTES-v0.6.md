# ATLAS v0.6.0 — Public Demo + Private Browser Workspace

An integrated release: **all v0.5 browser-workspace features, plus a public, no-signup interactive research demo** that runs on GitHub Pages.

## Public demonstration

- Beautiful static dashboard (`docs/index.html`) with three functional sections.
- Real JavaScript BM25 ranking on 12 verbatim passages from the project's three published sample guides.
- Source-linked, exact-excerpt responses; four deterministic processing stages; transparent abstention.
- Six hand-authored retrieval smoke checks, with clear disclosure that these do not measure factual truth.
- No external network calls, third-party APIs, authentication, private data, API keys or incurred model costs.

## Retained from v0.5

- GitHub Codespaces browser-based private developer environment.
- FastAPI dashboard, signed-session operator login, CSRF protections, and login throttling in hosted mode.
- Optional paid Render hosting with persistent storage.
- Full v0.4 queue, memory, multi-agent orchestration, provider adapters and semantic-index options.

## Test coverage

- Python pytest regression suite (including v0.5 security checks).
- Node.js browser-search and evidence checks integrated into CI on Python 3.11/3.12/3.13 jobs.
- No live cloud deployment performed as part of building the package. Enable GitHub Pages in repository Settings to publish the site.

See [docs/PUBLIC_DEMO_DEPLOYMENT.md](docs/PUBLIC_DEMO_DEPLOYMENT.md) for step-by-step GitHub upload and Pages instructions.
