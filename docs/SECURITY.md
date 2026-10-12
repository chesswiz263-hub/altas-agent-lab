# Security posture (v0.5)

**v0.5 supports a private hosted single-operator browser login, not a public multi-user SaaS.** When `ATLAS_HOSTED_MODE=1`, the server fails startup unless two strong independent secrets are configured, protects dashboard, API docs and API endpoints except health checks, issues eight-hour signed `Secure`/`HttpOnly`/`SameSite=Strict` cookies, and requires same-origin requests plus explicit CSRF tokens for API mutations. Failed logins are throttled in memory. A logout clears the browser cookie; a stolen signed session can remain usable until expiration or signing-key rotation. The service also sets CSP, clickjacking and MIME-sniffing response protections.

The original v0.4 notes below describe **legacy local API bearer-token mode** and should not be interpreted as a description of the v0.5 hosted login. For current deployment guidance see [Browser Workspace](BROWSER_WORKSPACE.md). Continue to use **one worker**, server-side environment secrets and a persistent disk if remote data should survive deploys. We have not undertaken a penetration test, a full privacy review, independent hosted deployment validation or enterprise authentication hardening.

---

# Security posture (v0.4)

**ATLAS is local-first engineering software, not a hardened hosted SaaS.** The default Compose file binds to `127.0.0.1`. Do not expose port 8000 to untrusted networks. A **single-operator API token** can be enabled using `ATLAS_API_TOKEN`; it is checked against `Authorization: Bearer <value>` or `X-Atlas-Token` with a constant-time comparison. `/api/health` stays unauthenticated for health probes. Static HTML and `/docs` are public when the host is exposed. Authentication is **disabled** unless a token is configured.

## Implemented safeguards

- Model keys remain server-side. The dashboard's optional API access token is stored only in volatile page memory; the API does not set authentication cookies.
- Input lengths, models, provider types and agent step counts are validated. Tools are allowlisted to document search/listing and bounded arithmetic. No shell, arbitrary subprocess or OS file access is given to agents.
- SQL is parameterized and FTS query tokens quoted. Frontend escapes generated content before inserting markup. Errors surfaced to users omit raw provider response bodies.
- Run data is persisted in SQLite; records of in-flight jobs are marked interrupted on startup **without automatic paid-call replay**.
- Saved notes are created/deleted explicitly, returned only through API, and sent to a model only when an operator opts in for a queued run.

## Remaining risks

- **Single token is not authorization**: no OAuth/OIDC, tenant isolation, MFA, credential rotation workflow, login rate limiting or abuse protection. An operator must configure ingress TLS, secure transport and protected deployment infrastructure before any remote use.
- Dashboard and OpenAPI docs remain readable without a token. API commands are protected when a token exists; memory and document data are otherwise single-workspace plaintext in SQLite and should not contain secrets.
- **Cancellation is best effort.** A sent request may be billed even if ATLAS cancels its local await. `max_cost_usd` is a post-hoc estimate, not a vendor billing ceiling. Backups, log retention and legal compliance remain operator responsibilities.
- **Prompt injection** is possible in user-authored notes, retrieved documents, intermediary agents and tools, despite explicit untrusted-context labels. Permissions must be enforced by tools, not promises from a prompt.
- Neural checkpoint downloads, NLI models, local MCP operation and model vendor protocols require trusted-source review and independent test coverage.
- Queue worker is one process only. Do not use multiple Uvicorn workers or horizontally scale without a shared leasing and recovery architecture.

## Public deployment prerequisites

Add TLS, real operator authentication and authorization, per-user resource controls, rate limiting, provider budget and quotas, tenant scoping, data retention, encrypted secrets, egress policy, auditing, automated security testing, and a distributed queue/database design. Reassess the client CSP and threat model before embedding untrusted content or adding user-upload formats.


## v0.6 public site trust boundary

The static `docs/` GitHub Pages site is public and **does not** use `/api/*`, the private Python process, saved notes, LLM provider keys, or operator cookies. Never add credentials or private documents to `docs/` or its demo corpus. The demo uses fixed public example passages, deterministic BM25 and exact text quotation checks only. It must not be described as a production public API or actual autonomous multi-agent execution.
