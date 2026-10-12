# ATLAS v0.5: use the dashboard in your browser

ATLAS provides **two distinct cloud workflows**. Neither is activated merely by uploading source code to GitHub.

## Option A — GitHub Codespaces (recommended first)

Best for developing ATLAS *and* viewing its dashboard without installing Python locally. This is a private development workspace, not a permanent public demo.

1. Push the full v0.5 repository to GitHub, including `.devcontainer/devcontainer.json` and `.devcontainer/start-atlas.sh`.
2. Open the repo on GitHub → **Code → Codespaces → Create codespace on main**.
3. Wait for **postCreateCommand** to install dependencies and seed sample knowledge. The **postStartCommand** starts the Uvicorn server in the cloud with one worker.
4. Open the **PORTS** tab in the browser editor. Select the forwarded **8000** URL to open the dashboard in a new browser tab. If asked, authenticate with your GitHub account.
5. Keep port 8000 **Private**. Never change it to Public unless you have explicitly enabled hosted-mode protection and reviewed the risks.
6. Codespaces may automatically stop after inactivity and may incur usage/storage charges above any included allowance. Restart from GitHub as needed. Project data is associated with the Codespace and is lost if the Codespace itself is deleted unless backed up.

To troubleshoot, open the Codespaces terminal:

```bash
cat /tmp/atlas-codespace.log
python -m pytest -q
atlas seed
```

You can edit code and commit/push from VS Code in the browser. The browser dashboard reflects changes after restarting the Uvicorn process (Codespaces' hosted dev launcher does *not* use `--reload`).

**Important:** Browser port forwarding is a *development* solution, not an always-on application deployment. GitHub Codespaces ports are private by default; keep them private. Read GitHub's [port forwarding docs](https://docs.github.com/en/codespaces/developing-in-a-codespace/forwarding-ports-in-your-codespace).

## Option B — Render private operator workspace (paid)

Best for a persistent HTTPS website that you can open from multiple devices. The URL will look like `https://your-service.onrender.com`.

**Costs:** This Blueprint requests a paid **0.5c-512mb** web service with a persistent disk. **Check Render's current plan and disk pricing before creating it.** Render does not offer persistent disks on Free web services. Do not use a free ephemeral instance if you need notes, indexed documents, jobs, and history to persist.

1. Push `render.yaml`, the Dockerfile, frontend and source files to GitHub.
2. Create a Render account and connect your GitHub repository.
3. In Render, choose **New → Blueprint** and select the repo; Render reads `render.yaml`.
4. Review the **Starter-class paid service and persistent disk costs**. When prompted, set `ATLAS_ADMIN_PASSWORD` to a unique, randomly generated password at least 16 characters long. Keep it in a password manager. The Blueprint automatically generates a separate random `ATLAS_SESSION_SECRET` (never commit it).
5. Click **Apply/Deploy**. Wait until the service's deployment and `/api/health` check pass. Render provides the actual HTTPS URL. **The user must complete the hosting-provider setup; ATLAS cannot deploy itself just by being on GitHub.**
6. Open the HTTPS URL, enter your password on the ATLAS sign-in page, and access the protected dashboard. Once signed in, unsafe requests require an anti-CSRF token.
7. Initially, keep `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and `GEMINI_API_KEY` unset. The offline `demo` model works without tokens or billable requests. Add API keys as Render secrets only if desired.
8. On deploys, the single worker may interrupt an in-flight job. Persistent queued jobs remain; interrupted jobs are **not replayed automatically** to avoid duplicate provider charges.

If you use a custom domain, set `ATLAS_PUBLIC_ORIGIN` to its exact HTTPS origin (such as `https://atlas.example.com`) in Render's Environment settings. Render's default public host is automatically inferred from `RENDER_EXTERNAL_HOSTNAME` if this variable is otherwise unset.

### Hosted-mode environment variables

| Variable | Meaning |
|---|---|
| `ATLAS_HOSTED_MODE=1` | Fail-closed, authenticated browser mode |
| `ATLAS_ADMIN_PASSWORD` | Secret operator password, minimum 16 characters |
| `ATLAS_SESSION_SECRET` | Different signing secret, at least 32 characters |
| `ATLAS_PUBLIC_ORIGIN` | Optional exact HTTPS origin; recommend for custom domains |
| `ATLAS_DB_PATH=/app/data/atlas.db` | Persistent SQLite path on Render disk |
| `PORT=10000` | Public-facing Uvicorn port for Render |
| `ATLAS_API_TOKEN` | Leave unset with hosted mode unless you need *both* cookie and API-token gates |

All passwords and provider keys must be provided through server-side Render environment secrets—**never in files committed to GitHub**, `.env.example`, frontend JavaScript, release notes or screenshots.

### Security model / limitations

- The login form protects dashboard assets, docs and `/api/*` except public health probes. Eight-hour signed secure `HttpOnly`, `SameSite=Strict` cookies and CSRF headers protect the owner workspace.
- Failed login attempts are rate limited **in memory per application instance**; this is not a WAF, OAuth, MFA, enterprise SSO, per-user authorization or a distributed security service. It does not defend against all brute force or DoS attacks.
- This is **one shared operator account**, one SQLite database and one application worker. Do not allow other users to sign in; no separate accounts, organization membership, RBAC, quota management, tenant isolation or audit retention policies are included.
- Logging out clears the browser cookie but does not revoke a stolen cookie server-side. A valid stolen session can remain usable for up to eight hours. Change `ATLAS_SESSION_SECRET` to revoke all existing signed sessions.
- Existing saved notes, jobs and documents are stored in plaintext SQLite on the disk; the disk provider handles disk encryption at rest, but ATLAS does not implement application-layer encryption.
- Paid provider calls are not capped by a guaranteed prepaid budget; cancellation cannot unsend a request. Use a vendor-side quota and be mindful of cost.
- Provider adapters and download-on-demand neural model inference were not verified against live vendor services by the offline release test suite.
- A browser-accessible **password-protected personal development workspace** is not equivalent to a secure, audited, production-ready public multi-user SaaS.

## Local development still works

Without `ATLAS_HOSTED_MODE`, ATLAS remains local-first and does **not** require a password. Bind `127.0.0.1` on your own computer or rely on **private** Codespaces forwarding. If you explicitly set hosted mode locally, serve it behind HTTPS to use secure cookies.
