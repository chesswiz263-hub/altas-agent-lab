# Publish ATLAS to your GitHub account

ATLAS is packaged locally as a **GitHub-ready source repository**. It is **not** uploaded to your GitHub account until you authorize and complete the publishing step.

## Local GitHub CLI workflow

1. Extract the release ZIP and open your terminal in the `atlas-agent-lab/` folder (the folder containing `pyproject.toml`).
2. Sign in using GitHub CLI (`gh auth login`) or authenticate via a GitHub app you have explicitly connected.
3. Verify your `.env` and secrets are **not** tracked. The repository's `.gitignore` excludes `.env`, local databases, caches and venvs. Consider running a secrets scanner before a public push.
4. Publish:

```bash
git init
git branch -M main
git add .
git status --short
git commit -m "feat: ATLAS v0.4 durable agent lab"
gh repo create atlas-agent-lab --public --source=. --remote=origin --push
```

For a private repository, replace `--public` with `--private`.

## After publishing

- Confirm the **Actions** workflow passes its Python 3.11, 3.12 and 3.13 matrix.
- Confirm the README and MIT license display correctly.
- Add repository description and topics such as `ai-agents`, `fastapi`, `rag`, `multi-agent`, `python`, `sqlite`, and `llm-evaluation`.
- Open issues for the v0.5 limitations listed in `docs/ROADMAP.md`.
- Avoid adding real production API keys, customer documents, or local SQLite volumes to the public repository.

The included GitHub workflow uses offline fixtures; it does not perform billable model calls or download neural models.
