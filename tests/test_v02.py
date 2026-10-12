"""v0.2 migration, role separation, lexical-hybrid retrieval and cost guardrails."""
import pytest
from fastapi.testclient import TestClient

from atlas.agent import Agent
from atlas.api import create_app
from atlas.costs import estimate_usd, token_rates
from atlas.schemas import ModelReply
from atlas.store import Store
from atlas.team import Team


def test_hybrid_retrieval_cites_real_chunks(store):
    result = store.add_document("Routing", "An orchestration engine delegates tasks to specialist agents.")
    store.add_document("Other", "The botanical garden contains colorful flowering plants.")
    hits = store.search_hybrid("orchestraton specialist", 5)
    assert hits
    assert any(hit["doc_id"] == result["id"] for hit in hits)
    for hit in hits:
        assert hit["citation"] == f"doc:{hit['doc_id']}#chunk:{hit['chunk_id']}"
        assert hit["retrieval"] == "hybrid_lexical"
    with store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM chunk_vectors").fetchone()[0] == 2
    assert store.delete_document(result["id"])
    with store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM chunk_vectors").fetchone()[0] == 1


def test_vector_migration_backfills_existing_chunks(tmp_path):
    path = tmp_path / "db.sqlite"
    store = Store(path)
    d = store.add_document("Migrate", "Versioned data migration keeps stable citation identifiers.")
    with store.connect() as db:
        db.execute("DELETE FROM chunk_vectors")
    upgraded = Store(path)
    assert upgraded.search_hybrid("migration data")
    assert upgraded.list_documents()[0]["id"] == d["id"]


def test_prices_are_operator_supplied(monkeypatch):
    assert token_rates("demo", "atlas-demo-v1") == (0, 0)
    monkeypatch.delenv("ATLAS_PRICING_JSON", raising=False)
    assert estimate_usd("openai", "my-model", 1000, 250) is None
    monkeypatch.setenv("ATLAS_PRICING_JSON", '{"openai/my-model":[3,12]}')
    assert estimate_usd("openai", "my-model", 1000, 250) == 0.006
    monkeypatch.setenv("ATLAS_PRICING_JSON", '{"openai/my-model":[-10,12]}')
    assert token_rates("openai", "my-model") is None
    monkeypatch.setenv("ATLAS_PRICING_JSON", '{malformed')
    assert token_rates("openai", "my-model") is None


class ExpensiveProvider:
    async def complete(self, messages, tools, model):
        return ModelReply(content="Would have finished", input_tokens=4000, output_tokens=500)


@pytest.mark.asyncio
async def test_agent_soft_cost_stop_does_not_fabricate(monkeypatch, store):
    monkeypatch.setenv("ATLAS_PRICING_JSON", '{"openai/test-model":[1,1]}')
    events = [e async for e in Agent(store, ExpensiveProvider()).stream(
        "explain this", "openai", "test-model", 3, max_cost_usd=0.001)]
    assert events[-1]["budget_exhausted"]
    assert events[-1]["estimated_cost_usd"] > 0.001
    assert not any(e["type"] == "tool_call" for e in events)


@pytest.mark.asyncio
async def test_team_offline_roles_and_provenance(store):
    store.add_document("Safety rules", "Tool allowlists and execution budgets are useful safeguards.")
    events = [e async for e in Team(store).stream(
        "What safeguards are useful for tool agents?", "demo", "atlas-demo-v1", 3)]
    assert [e["role"] for e in events if e["type"] == "role_start"] == [
        "researcher", "analyst", "critic", "synthesizer"]
    assert "doc:" in events[-1]["answer"]
    assert "simulated" in events[-1]["answer"].lower()
    assert events[-1]["estimated_cost_usd"] == 0.0
    assert events[-1]["type"] == "final"


def test_team_api_and_cost_validation(store):
    store.add_document("Agent basics", "An agent can use tool allowlists for safer execution.")
    with TestClient(create_app(store)) as client:
        resp = client.post("/api/team/stream", json={"prompt": "What are tool allowlists?", "provider": "demo"})
        assert resp.status_code == 200
        assert "event: role_start" in resp.text
        assert "event: role_result" in resp.text
        assert "event: final" in resp.text
        runs = client.get("/api/runs").json()
        assert runs[0]["mode"] == "team"
        assert runs[0]["estimated_cost_usd"] == 0.0
        assert len(client.get("/api/runs/"+runs[0]["id"]).json()["events"]) >= 12
        assert client.get("/api/search", params={"q": "allowlst", "mode": "hybrid"}).status_code == 200
        assert client.get("/api/search", params={"q": "foo", "mode": "unknown"}).status_code == 400
        assert client.post("/api/team/stream", json={"prompt": "answer question", "provider": "demo", "max_cost_usd": 0.001}).status_code == 200
        # Cannot request a financial budget when costs cannot be estimated.
        assert client.post("/api/team/stream", json={"prompt": "answer question", "provider": "openai", "max_cost_usd": 0.001}).status_code == 400


def test_cross_model_comparison_api_validates_distinct_models(store):
    with TestClient(create_app(store)) as client:
        target = {"provider": "demo", "model": "atlas-demo-v1"}
        resp = client.post("/api/evaluations/compare", json={"models": [target, target]})
        assert resp.status_code == 400
        resp = client.post("/api/evaluations/compare", json={"models": [
            target, {"provider": "demo", "model": "another-demo-model"}]})
        assert resp.status_code == 200
        obj = resp.json()
        assert len(obj["comparisons"]) == 2
        assert "hybrid_recall_at_5" in obj["comparisons"][0]
        assert obj["comparisons"][0]["estimated_cost_usd"] == 0.0


def test_team_rejects_oversized_role_budget_and_hybrid_no_spurious_hits(store):
    store.add_document("Plain", "This document describes oranges and carrots.")
    assert store.search_hybrid("zzzzzxzxzxq") == []
    with TestClient(create_app(store)) as client:
        assert client.post("/api/team/stream", json={
            "prompt": "A research question", "max_steps": 8}).status_code == 400
