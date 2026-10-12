from fastapi.testclient import TestClient

from atlas.api import create_app


def test_api_document_flow_and_dashboard(store):
    with TestClient(create_app(store)) as client:
        assert client.get("/api/health").json()["ok"]
        assert client.get("/").status_code == 200
        response = client.post("/api/documents", json={"title": "RAG", "content": "Retrieval augmented generation uses search tools to ground a response."})
        assert response.status_code == 201
        assert client.get("/api/status").json()["documents"] == 1
        assert client.get("/api/search", params={"q": "retrieval"}).json()["results"]
        assert client.delete(f"/api/documents/{response.json()['id']}").status_code == 200
        assert client.delete(f"/api/documents/{response.json()['id']}").status_code == 404


def test_stream_and_history(store):
    store.add_document("Reliable agents", "Tool allowlists and step budgets protect agents.")
    with TestClient(create_app(store)) as client:
        r = client.post("/api/agent/stream", json={"prompt": "What protects agents?", "provider": "demo"})
        assert r.status_code == 200
        assert "event: final" in r.text
        assert "event: tool_call" in r.text
        runs = client.get("/api/runs").json()
        assert len(runs) == 1
        assert runs[0]["status"] == "completed"
        assert len(client.get(f"/api/runs/{runs[0]['id']}").json()["events"]) >= 3


def test_rejects_invalid_provider_and_short_prompts(store):
    with TestClient(create_app(store)) as client:
        assert client.post("/api/agent/stream", json={"prompt": "x"}).status_code == 422
        assert client.post("/api/agent/stream", json={"prompt": "Anything", "provider": "unknown"}).status_code == 422
        assert client.get('/api/search', params={'q':'x'*401}).status_code == 400
