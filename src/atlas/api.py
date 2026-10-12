"""Single-origin FastAPI app serving an observable agent and no-build frontend."""
import hmac
import json
import os
import time
import uuid
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from atlas.agent import Agent
from atlas.jobs import Jobs, LocalWorker
from atlas.calibration import calibrate
from atlas.config import DEFAULT_MODELS, available_providers
from atlas.costs import token_rates
from atlas.embeddings import EmbeddingUnavailable
from atlas.evaluation import evaluate
from atlas.nli import judge
from atlas.router import plan
from atlas.schemas import (
    ComparisonRequest,
    JobRequest,
    MemoryRequest,
    DocumentRequest,
    EvaluationRequest,
    RouteRequest,
    RunRequest,
    SemanticIndexRequest,
    VerifyRequest,
)
from atlas.store import Store
from atlas.team import Team
from atlas.verification import review
from atlas.web_auth import WebAuth, SESSION_COOKIE

ROOT = Path(os.getenv("ATLAS_PROJECT_ROOT", str(Path(__file__).resolve().parents[2])))


def create_app(store: Store | None = None) -> FastAPI:
    db = store or Store()
    auth = WebAuth.from_environment()
    jobs = Jobs(db)
    worker = LocalWorker(jobs)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        await worker.start()
        try:
            yield
        finally:
            await worker.stop()

    app = FastAPI(title="ATLAS Agent Lab", version="0.6.0",
                  description="Auditable agents, local durable job queue, opt-in memory, and calibrated evals",
                  lifespan=lifespan)
    app.state.store = db
    app.state.auth = auth
    app.state.jobs = jobs
    app.state.worker = worker

    @app.middleware('http')
    async def optional_bearer_auth(request: Request, call_next):
        token = os.getenv('ATLAS_API_TOKEN', '')
        if token and request.url.path.startswith('/api/') and request.url.path != '/api/health':
            supplied = request.headers.get('Authorization', '')
            bearer = supplied[7:] if supplied.startswith('Bearer ') else ''
            candidate = bearer or request.headers.get('X-Atlas-Token', '')
            if not hmac.compare_digest(candidate.encode('utf-8'), token.encode('utf-8')):
                return JSONResponse({'detail': 'Authentication required'}, status_code=401,
                                    headers={'WWW-Authenticate': 'Bearer'})
        response = await call_next(request)
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response
    @app.middleware("http")
    async def hosted_browser_guard(request: Request, call_next):
        path = request.url.path
        if auth.enabled:
            public = {"/login", "/auth/login", "/auth/login.js", "/auth/login.css", "/api/health"}
            cookie = request.cookies.get(SESSION_COOKIE, "")
            signed_in = auth.valid_session(cookie)
            if path not in public and not signed_in:
                response = auth.reject(request)
            elif path == "/login" and signed_in:
                response = RedirectResponse("/", status_code=303)
            elif path.startswith("/api/") and request.method not in {"GET", "HEAD", "OPTIONS"} and (
                not auth.same_origin(request) or not auth.verify_csrf(request, cookie)
            ):
                response = JSONResponse({"detail": "Invalid CSRF or request origin"}, status_code=403)
            elif path == "/auth/logout" and (not auth.same_origin(request) or not auth.verify_csrf(request, cookie)):
                response = JSONResponse({"detail": "Invalid CSRF or request origin"}, status_code=403)
            elif path == "/auth/login" and not auth.same_origin(request):
                response = JSONResponse({"detail": "Invalid request origin"}, status_code=403)
            else:
                response = await call_next(request)
        else:
            response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
            "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        )
        if auth.enabled:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["Cache-Control"] = "no-store"
        return response

    static_dir = ROOT / "static"
    if static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/")
    def index():
        return FileResponse(static_dir / "index.html")

    @app.get("/login", include_in_schema=False)
    def login_page():
        return FileResponse(static_dir / "login.html")

    @app.get("/auth/login.js", include_in_schema=False)
    def login_script():
        return FileResponse(static_dir / "login.js", media_type="text/javascript")

    @app.get("/auth/login.css", include_in_schema=False)
    def login_style():
        return FileResponse(static_dir / "login.css", media_type="text/css")

    @app.post("/auth/login", include_in_schema=False)
    async def web_login(request: Request):
        if not auth.enabled:
            raise HTTPException(404, "Not configured")
        # Limit request size before JSON decoding and rate limit unsuccessful attempts.
        if int(request.headers.get("content-length", "0") or "0") > 4096:
            raise HTTPException(413, "Request too large")
        if not auth.login_allowed(request.client.host if request.client else "unknown"):
            return JSONResponse({"detail": "Too many attempts. Try again later."}, status_code=429)
        try:
            data = await request.json()
            password = data.get("password", "")
        except (ValueError, AttributeError, TypeError):
            password = ""
        if not isinstance(password, str) or not auth.verify_password(password):
            return JSONResponse({"detail": "Incorrect password"}, status_code=401)
        auth.login_success(request.client.host if request.client else "unknown")
        session = auth.session()
        result = JSONResponse({"ok": True, "csrf": auth.csrf(session)})
        auth.set_cookie(result, session)
        return result

    @app.get("/auth/session", include_in_schema=False)
    def web_session(request: Request):
        if not auth.enabled:
            return {"authenticated": True, "hosted": False, "csrf": None}
        return {"authenticated": True, "hosted": True,
                "csrf": auth.csrf(request.cookies.get(SESSION_COOKIE, ""))}

    @app.post("/auth/logout", include_in_schema=False)
    def web_logout():
        response = JSONResponse({"ok": True})
        response.delete_cookie(SESSION_COOKIE, path="/", secure=auth.secure, httponly=True, samesite="strict")
        return response

    @app.get("/api/health")
    def health():
        return {"ok": True, "service": "atlas", "version": "0.6.0"}

    @app.get("/api/status")
    def status():
        docs = app.state.store.list_documents()
        runs = app.state.store.list_runs(100)
        return {"providers": available_providers(), "default_models": DEFAULT_MODELS,
                "documents": len(docs), "runs": len(runs),
                "successful_runs": sum(r["status"] == "completed" for r in runs),
                "total_tool_steps": sum(r["steps"] for r in runs),
                "known_estimated_cost_usd": round(sum(r["estimated_cost_usd"] or 0 for r in runs), 6),
                "semantic_index": app.state.store.semantic_status(),
                "jobs": jobs.stats(),
                "auth_enabled": bool(os.getenv("ATLAS_API_TOKEN")) or auth.enabled,
                "hosted_mode": auth.enabled,
                "legacy_api_token_enabled": bool(os.getenv("ATLAS_API_TOKEN"))}

    @app.get("/api/documents")
    def documents():
        return app.state.store.list_documents()

    @app.post("/api/documents", status_code=201)
    def add_document(request: DocumentRequest):
        return app.state.store.add_document(request.title, request.content)

    @app.delete("/api/documents/{doc_id}")
    def delete_document(doc_id: int):
        if not app.state.store.delete_document(doc_id):
            raise HTTPException(404, "Document not found")
        return {"deleted": True}

    @app.get("/api/search")
    def search(q: str, mode: str = "bm25"):
        if len(q) > 400:
            raise HTTPException(400, "Query too long")
        methods = {"bm25": app.state.store.search, "hybrid": app.state.store.search_hybrid,
                   "semantic": app.state.store.search_semantic,
                   "semantic_hybrid": app.state.store.search_semantic_hybrid}
        if mode not in methods:
            raise HTTPException(400, "Unknown retrieval mode")
        try:
            return {"mode": mode, "results": methods[mode](q)}
        except EmbeddingUnavailable as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/api/embeddings/status")
    def embedding_status():
        return app.state.store.semantic_status()

    @app.get('/api/jobs')
    def list_jobs():
        return jobs.list()

    @app.post('/api/jobs', status_code=202)
    def create_job(request: JobRequest):
        try:
            return jobs.enqueue(request.model_dump(exclude={'mode'}), request.mode)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get('/api/jobs/{job_id}')
    def get_job(job_id: str):
        result = jobs.get(job_id)
        if result is None:
            raise HTTPException(404, 'Job not found')
        return result

    @app.post('/api/jobs/{job_id}/cancel')
    def cancel_job(job_id: str):
        result = jobs.cancel(job_id)
        if result is None:
            raise HTTPException(404, 'Job not found')
        return result

    @app.get('/api/jobs/{job_id}/events')
    def job_events(job_id: str, after: int = 0, limit: int = 100):
        if jobs.get(job_id) is None:
            raise HTTPException(404, 'Job not found')
        return {'job_id': job_id, 'events': jobs.events(job_id, after, limit)}

    @app.get('/api/memories')
    def list_memories():
        return app.state.store.list_memories()

    @app.post('/api/memories', status_code=201)
    def save_memory(request: MemoryRequest):
        try:
            return app.state.store.add_memory(request.title, request.content)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.delete('/api/memories/{memory_id}')
    def delete_memory(memory_id: int):
        if not app.state.store.delete_memory(memory_id):
            raise HTTPException(404, 'Note not found')
        return {'deleted': True}

    @app.get('/api/evaluations/calibration')
    def get_calibration():
        return calibrate()

    @app.post("/api/embeddings/index")
    def index_embeddings(request: SemanticIndexRequest):
        try:
            return app.state.store.index_semantic(request.batch_size, request.max_chunks)
        except (EmbeddingUnavailable, ValueError) as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.post("/api/route")
    def explain_route(request: RouteRequest):
        return plan(request.prompt, semantic_ready=app.state.store.semantic_status()["ready"]).as_dict()

    @app.post("/api/verify")
    def verify(request: VerifyRequest):
        if request.method == "nli" and not os.environ.get("ATLAS_NLI_MODEL"):
            raise HTTPException(409, "NLI audit requires ATLAS_NLI_MODEL and the nli optional extra")
        try:
            return review(request.answer, app.state.store, nli=judge if request.method == "nli" else None)
        except (RuntimeError, ValueError) as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.post("/api/runs/{run_id}/verify")
    def verify_run(run_id: str):
        run = app.state.store.get_run(run_id)
        if run is None:
            raise HTTPException(404, "Run not found")
        if not run.get("answer"):
            raise HTTPException(409, "Run does not have a final answer")
        return review(run["answer"], app.state.store)

    @app.get("/api/runs")
    def list_runs():
        return app.state.store.list_runs()

    @app.get("/api/runs/{run_id}")
    def run_details(run_id: str):
        result = app.state.store.get_run(run_id)
        if result is None:
            raise HTTPException(404, "Run not found")
        return result

    def create_stream(request: RunRequest, mode: str):
        if not available_providers().get(request.provider, False):
            raise HTTPException(400, "Provider not configured. Set its server-side API key.")
        model = request.model or DEFAULT_MODELS[request.provider]
        import re
        if not re.fullmatch(r"[a-zA-Z0-9._:-]{1,100}", model):
            raise HTTPException(400, "Invalid model identifier")
        if mode in ("team", "auto") and request.max_steps > 5:
            raise HTTPException(400, "Team runs support at most five steps per role")
        if request.max_cost_usd is not None and token_rates(request.provider, model) is None:
            raise HTTPException(400, "Cost budget requires operator-configured ATLAS_PRICING_JSON rates for this provider/model")
        store: Store = app.state.store
        routing = plan(request.prompt, semantic_ready=store.semantic_status()["ready"]) if mode == "auto" else None
        execution = routing.execution if routing else mode
        search_mode = routing.retrieval if routing else None
        run_id = uuid.uuid4().hex
        store.start_run(run_id, request.prompt, request.provider, model, mode=mode)

        async def events():
            start = time.perf_counter()
            latest = {"answer": "", "steps": 0, "input_tokens": 0,
                      "output_tokens": 0, "estimated_cost_usd": None, "duration_ms": 0}
            try:
                if routing is not None:
                    route_event = {"type": "route", "run_id": run_id, "plan": routing.as_dict()}
                    store.append_event(run_id, route_event)
                    yield f"event: route\ndata: {json.dumps(route_event)}\n\n"
                iterator = (Team(store, search_mode=search_mode).stream(request.prompt, request.provider, model,
                                                request.max_steps, request.max_cost_usd)
                            if execution == "team" else
                            Agent(store, search_mode=search_mode).stream(request.prompt, request.provider, model,
                                                request.max_steps, request.max_cost_usd))
                async for event in iterator:
                    event["run_id"] = run_id
                    store.append_event(run_id, event)
                    if event["type"] == "final":
                        latest.update(event)
                    yield f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
                store.end_run(run_id, answer=latest["answer"],
                              status="budget_exhausted" if latest.get("budget_exhausted") else "completed",
                              steps=latest["steps"], input_tokens=latest["input_tokens"],
                              output_tokens=latest["output_tokens"],
                              estimated_cost_usd=latest.get("estimated_cost_usd"),
                              duration_ms=int((time.perf_counter() - start) * 1000))
            except Exception as exc:
                # Never echo secrets, provider HTTP response bodies, or stack traces.
                error = {"type": "error", "run_id": run_id,
                         "message": f"Agent run failed ({type(exc).__name__}). Check server logs and provider configuration."}
                store.append_event(run_id, error)
                store.end_run(run_id, answer="", status="failed", steps=0,
                              input_tokens=0, output_tokens=0,
                              duration_ms=int((time.perf_counter() - start) * 1000))
                yield f"event: error\ndata: {json.dumps(error)}\n\n"

        return StreamingResponse(events(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.post("/api/agent/stream")
    async def stream_agent(request: RunRequest):
        return create_stream(request, "single")

    @app.post("/api/team/stream")
    async def stream_team(request: RunRequest):
        return create_stream(request, "team")

    @app.post("/api/auto/stream")
    async def stream_auto(request: RunRequest):
        return create_stream(request, "auto")

    @app.post("/api/evaluations/run")
    async def run_evals(request: EvaluationRequest):
        if not available_providers().get(request.provider, False):
            raise HTTPException(400, "Provider not configured")
        return await evaluate(app.state.store, request.provider,
                              request.model or DEFAULT_MODELS[request.provider])

    @app.post("/api/evaluations/compare")
    async def compare_evals(request: ComparisonRequest):
        import re
        targets = []
        for target in request.models:
            if not available_providers().get(target.provider, False):
                raise HTTPException(400, f"Provider '{target.provider}' is not configured")
            model = target.model or DEFAULT_MODELS[target.provider]
            if not re.fullmatch(r"[a-zA-Z0-9._:-]{1,100}", model):
                raise HTTPException(400, "Invalid model identifier")
            if (target.provider, model) in targets:
                raise HTTPException(400, "Comparison targets must be distinct")
            targets.append((target.provider, model))
        scores = [await evaluate(app.state.store, provider, model) for provider, model in targets]
        return {"comparisons": scores, "note": "Metrics measure retrieval hits and citation presence only. Live provider usage may be billed."}

    return app


app = create_app()
