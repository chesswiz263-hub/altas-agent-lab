# ATLAS v0.4.0 — Release summary

This milestone adds a durable local job queue with cancellation and restart recovery, optional single-operator API token access, explicit saved notes with opt-in agent context, and isolated hand-labeled citation-audit calibration. The existing model gateway, four-role pipeline, FTS5 retrieval, optional neural semantic index, rule-based router, dashboard and evidence inspector remain available.

**Verification:** 55 automated offline tests passed with Python 3.11 in the build environment; frontend `node --check` and Python `compileall` completed successfully. A fresh extracted ZIP is regression-tested before delivery. GitHub Actions is configured for Python 3.11–3.13, but those remote CI runs have not been executed here. Ruff could not be installed in this environment due to unavailable package-network access; the repository includes a narrowly scoped static check in CI.

**Scope:** The worker uses one in-process background task and SQLite, not a distributed job system. In-flight jobs are marked interrupted on restart and are never automatically replayed. Cancellation is best effort and does not guarantee provider billing stops. Optional API token authorization is single-operator protection, not production authentication/tenancy. Memory notes are plaintext locally and sent to live models only when opted in. Calibration covers only 10 simple citation surface-classification cases, not real-world correctness.

**Next:** Publish through your authenticated GitHub account once you authorize it, run CI, then prioritize v0.5 reliability and a larger independently annotated benchmark.
