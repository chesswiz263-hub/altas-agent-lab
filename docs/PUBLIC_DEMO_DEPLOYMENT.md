# ATLAS v0.6 — Publish the public demo on GitHub Pages

This is the exact sequence for the existing `chesswiz263-hub/atlas-agent-lab` repository (adjust if renamed). **The v1.0 archive is already a single complete repository containing every v0.5 file plus the public demo and updated tests. Do not upload a ZIP as the only repository file.**

## One combined update

1. Download `ATLAS-Agent-Intelligence-Lab-v0.6-COMBINED.zip` and use **Extract All** on Windows.
2. The inner folder is `atlas-agent-lab`. The repository root is the folder containing `README.md`, `pyproject.toml`, `.devcontainer`, `.github`, `src`, `static`, `tests`, and `docs`.
3. Update your **existing** GitHub repository with the *contents* of that inner folder. Because v0.4 files already exist, a normal GitHub web upload may reject duplicate filenames. Prefer GitHub Desktop's file-copy and commit workflow, or use VS Code in the browser (`github.dev`) to upload the extracted directories and replace existing files. Do not create a second repository.
4. Include the hidden directories `.github` and `.devcontainer`, and the dotfiles `.gitignore`, `.env.example`, `.dockerignore` and `docs/.nojekyll`. Do **not** upload a real `.env` file or API credentials.
5. Commit with `feat: ATLAS v0.6 public demo and v0.5 browser workspace` and push to `main`. Let **Actions → CI** finish green. The revised CI runs Python tests plus Node tests of the public demo.

### If you use GitHub Desktop (reliable update workflow)

1. Install GitHub Desktop and sign in to GitHub.
2. Use **File → Clone repository**, select `chesswiz263-hub/atlas-agent-lab`, and clone to a folder you choose.
3. In File Explorer, open the **extracted** `atlas-agent-lab` directory, select all its contents (including hidden dot-directories), and copy them into the **cloned repo folder**. Choose **Replace files in destination** when asked.
4. In GitHub Desktop, review the **Changes** tab. You should see new public-demo files and updates to existing v0.4 files. Commit to `main`, then **Push origin**.
5. Confirm the CI workflow is green on GitHub. This preserves your existing `v0.4.0` tag and history; it does not automatically create a `v0.6.0` release.

## Publish the public visitor site

1. Open the repository on GitHub, then click **Settings**.
2. In the left sidebar, choose **Pages**.
3. Under **Build and deployment**, choose **Source → Deploy from a branch**.
4. Set **Branch → main** and **Folder → /docs**, and click **Save**.
5. In **Actions**, wait for the GitHub Pages build/deployment to finish. Under Settings → Pages, GitHub will show the published URL.
6. For a project repository under `chesswiz263-hub`, the URL should be **`https://chesswiz263-hub.github.io/atlas-agent-lab/`** if the repository name remains `atlas-agent-lab`. If you rename to `atlas-agent-lab`, the URL path also changes.
7. Open the published URL in a private/incognito browser window and try: **Agent safeguards**, **MCP integration**, **Citation validity**, Knowledge base, and Evaluation lab.
8. In the repo sidebar **About**, add the actual deployed address to the **Website** field, after verifying it works.

**Important:** Enabling Pages does not publish or expose the authenticated v0.5 Python API; it hosts only the static files from `/docs` and its subfolders. Never store private documents, `.env` secrets, or private databases in the public Pages directory. GitHub Pages serves static HTML/CSS/JS; it cannot run Python/FastAPI server code.

## What public visitors can and cannot do

| Feature | Public Pages demo | v0.5 private Codespaces workspace |
| --- | --- | --- |
| Click link and try without setup | Yes, after Pages deployment | No, requires repository access / Codespaces |
| Sample document BM25 retrieval | Yes, in browser | Yes, via backend |
| Source excerpts and audit trace | Yes, deterministic | Yes, backend tools |
| Real OpenAI/Claude/Gemini calls | **No** | Optional, with your own credentials |
| Saved memory, custom documents | **No** | Yes, private/local |
| No API billing | Yes, static | Offline mode only |

## Security and trust boundaries

- No live LLM access or arbitrary tool execution from the public demo.
- No fetch, login, cookies, or data persistence in the demo scripts. The user's input is processed in local JS and rendered using text nodes.
- Public documents are **copied from `examples/knowledge`** during release preparation and validated byte-for-byte by the Node tests. Changing those source Markdown files later should be accompanied by regenerating `docs/demo/corpus.js`.
- Citation audit checks **exact substrings only**. Even if a quote exists, external factual validity is **not established**.
- There is no artificial rate limit because calculations happen entirely on each visitor's own browser and do not consume server or paid-model resources.
- The embedded links to GitHub source currently point to `chesswiz263-hub/atlas-agent-lab`. Update the URL in `docs/index.html` and `docs/demo/app.js` if renaming your repository, and update this guide.

## Troubleshooting

- **404:** Confirm `docs/index.html` exists on `main`, Pages source is `main /docs`, Pages deployment is green, and you used the correct repository spelling.
- **Page loads but buttons don't respond:** Confirm all three files `docs/demo/corpus.js`, `docs/demo/engine.js`, and `docs/demo/app.js` exist, plus `styles.css`.
- **CI fails in Node tests:** Run `node --test tests/browser/*.test.cjs` locally or inspect the `Browser demo tests (Node.js)` step in GitHub Actions.
- **The app doesn't answer arbitrary questions:** Expected. The public demo is limited to 12 sample passages and abstains without lexical evidence. Use the v0.5 private workspace for real configured model providers.

After Pages works, optionally create a GitHub **v0.6.0** release from `main`. Do not overwrite the earlier `v0.4.0` release.
