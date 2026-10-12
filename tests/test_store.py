from atlas.store import chunk_text


def test_chunking_bounds_and_overlap():
    chunks = chunk_text("one two three " * 200, size=100, overlap=20)
    assert len(chunks) > 1
    assert max(map(len, chunks)) <= 100
    assert all(chunks)


def test_document_ingestion_retrieval_duplicate_and_delete(store):
    doc = store.add_document("Reliable Agents", "Agents need explicit tool allowlists and step budgets.")
    assert doc["chunks"] == 1
    assert not doc["duplicate"]
    assert store.add_document("Reliable Agents", "Agents need explicit tool allowlists and step budgets.")["duplicate"]
    results = store.search("tool allowlists")
    assert results
    assert results[0]["title"] == "Reliable Agents"
    assert results[0]["citation"].startswith(f"doc:{doc['id']}#chunk:")
    assert store.delete_document(doc["id"])
    assert store.search("tool allowlists") == []
    assert not store.delete_document(doc["id"])


def test_search_query_fences(store):
    store.add_document("Injection", "quote magic syntax and odd tokens")
    for q in ['" OR * - ^', ')](:"', "", "*", "syntax"]:
        assert isinstance(store.search(q), list)


def test_run_persistence_and_trace(store):
    store.start_run("run_1", "What is RAG?", "demo", "demo")
    event = {"type": "tool_call", "tool": "search_documents", "arguments": {"query": "RAG"}}
    store.append_event("run_1", event)
    store.end_run("run_1", answer="Grounded", status="completed", steps=2,
                  input_tokens=1, output_tokens=2, duration_ms=30)
    detail = store.get_run("run_1")
    assert detail["status"] == "completed"
    assert detail["events"] == [event]
    assert store.list_runs()[0]["answer"] == "Grounded"
