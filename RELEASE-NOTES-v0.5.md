# ATLAS v0.5.0 — Browser Workspace Release

ATLAS can now run **in your browser**, without installing Python on your computer, using a GitHub Codespaces development workspace. An optional hosted deployment configuration supports a password-protected personal workspace through Render with HTTPS and persistent SQLite storage.

## New in 0.5.0

- **GitHub Codespaces:** Browser IDE, dependency install, demo document seeding, automatic server startup and privately forwarded port 8000.
- **Operator login:** Private hosted dashboard and API protection, strong credential validation and dedicated sign-in page.
- **Session security:** Eight-hour signed, Secure/HttpOnly/SameSite cookies, CSRF validation, same-origin checks, basic in-process login throttling and security headers.
- **Render Blueprint:** Optional paid single-operator service with persistent disk, generated signing key, dashboard password configuration and CI-gated redeploys.
- **UI:** Hosted logout action, private-workspace labeling and automatic CSRF handling for background jobs, evaluations, documents and streaming.
- **Tests:** Expanded offline regression suite including login, session tampering, expirations, private route blocking and mutations.

## Start in the browser (recommended)

1. Upload the source to GitHub, **including hidden `.devcontainer` and `.github` folders**, and let Actions go green.
2. Choose **Code → Codespaces → Create codespace on main**.
3. Wait for the automated setup, then open the forwarded **port 8000** from the **PORTS** tab. **Keep it Private**.
4. Select the offline demo model and try an agent query in the dashboard.

For an always-on URL, review [Browser Workspace and hosting guide](docs/BROWSER_WORKSPACE.md) and the explicit paid Render configuration. **No live hosting service is created by this source release.**

## Known limits

ATLAS is a single-operator engineering prototype, not a publicly usable multi-tenant service. Codespaces may incur usage charges. Render's persistent disk requires paid hosting. No full penetration test, browser automation, production deployment validation, real-provider integration test, or paid-model execution was performed for this release. The included offline evaluation cases are deliberately small and do not validate real-world model accuracy.
