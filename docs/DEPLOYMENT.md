# Local deployment and reproducibility

```sh
docker compose up --build
docker compose exec atlas atlas seed
curl http://127.0.0.1:8000/api/health
```

Docker Compose publishes only `127.0.0.1:8000`, persists SQLite to a named volume, and runs under non-root UID 10001. Set `ATLAS_API_TOKEN` in the local `.env` to enable API token checks. **Do not commit `.env`.** The UI allows you to enter the same token into a non-persistent password field.

The base Docker image omits neural model weights, SentenceTransformer and NLI dependencies. To enable those, build a custom optional-extras image with trusted model checkpoints and a persistent cache.

**One web worker is mandatory.** v0.4 runs a single queue worker in FastAPI's application lifespan. Do not run Uvicorn with `--workers 2` or start multiple app instances on one SQLite database. A recovered `running` job becomes `interrupted` and is not retried automatically; you must consciously resubmit it to avoid duplicate paid requests. Queued jobs persist and can run on restart.

## Test and release checklist

```sh
python -m pip install -e '.[dev]'
pytest -q
ruff check src tests --select E9,F821,F822,F823
node --check static/app.js
```

CI uses Python 3.11/3.12/3.13 with offline fixtures. Live provider integration and actual downloadable neural model weights are **not included** in these smoke tests.

## Before public deployment

The bearer token is only minimal single-operator access control. You still need TLS, a secure gateway, authorization, rate limiting, safe data retention, encrypted secrets, abuse controls, separated workers, tenancy, backups, idempotent job recovery, resource budgeting and egress restrictions. **Do not publish this reference instance as a public SaaS.**
